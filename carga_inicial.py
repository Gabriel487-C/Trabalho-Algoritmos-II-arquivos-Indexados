import csv
import glob
import heapq
import os
import shutil
import struct

# ==========================================
# FORMATOS BINÁRIOS
# ==========================================
PROD_FMT = ">Q32s20sdc1s"
PROD_SIZE = struct.calcsize(PROD_FMT)  # 70 bytes

EVENT_FMT = ">Q12sQQc1s"
EVENT_SIZE = struct.calcsize(EVENT_FMT)  # 38 bytes

IDX_FMT = ">QQ"
IDX_SIZE = struct.calcsize(IDX_FMT)  # 16 bytes

BLOCK_FACTOR = 100  # Indexa 1 a cada 100 registros
CHUNK_SIZE = 300_000  # Limite de registros na RAM por lote (~25 MB)


def pack_produto(p_id, cat, brand, price, is_del=b"0"):
    cat_bytes = cat.strip().ljust(32)[:32].encode("utf-8", errors="ignore")
    brand_bytes = brand.strip().ljust(20)[:20].encode("utf-8", errors="ignore")
    return struct.pack(
        PROD_FMT, p_id, cat_bytes, brand_bytes, price, is_del, b"\n"
    )


def pack_evento(ev_id, ev_type, u_id, p_id, is_del=b"0"):
    type_bytes = (
        ev_type.strip().ljust(12)[:12].encode("utf-8", errors="ignore")
    )
    return struct.pack(
        EVENT_FMT, ev_id, type_bytes, u_id, p_id, is_del, b"\n"
    )


# ==========================================
# FASE 1: LEITURA E GERAÇÃO DE RUNS
# ==========================================
def processar_csv(
    csv_path, eventos_dat, eventos_idx, pasta_temp_prod="temp_runs_prod"
):
    os.makedirs(pasta_temp_prod, exist_ok=True)

    event_id = 1
    total_eventos_idx = 0
    buffer_produtos = []
    run_idx = 0

    print("Iniciando leitura e extração contínua...")

    with open(csv_path, "r", encoding="utf-8") as f_csv, open(
        eventos_dat, "wb"
    ) as f_ev_dat, open(eventos_idx, "wb") as f_ev_idx:

        reader = csv.reader(f_csv)
        header = next(reader)  # Pula o cabeçalho

        for row in reader:
            if not row or len(row) < 8:
                continue

            try:
                ev_type = row[1]
                prod_id = int(row[2])
                cat_code = row[4] if row[4] else "sem_categoria"
                brand = row[5] if row[5] else "generico"
                price = float(row[6]) if row[6] else 0.0
                user_id = int(row[7])

                # 1. Grava eventos.dat e eventos.idx imediatamente
                offset_ev = f_ev_dat.tell()
                if (event_id - 1) % BLOCK_FACTOR == 0:
                    f_ev_idx.write(struct.pack(IDX_FMT, event_id, offset_ev))
                    total_eventos_idx += 1

                f_ev_dat.write(
                    pack_evento(event_id, ev_type, user_id, prod_id)
                )
                event_id += 1

                # 2. Acumula produtos no buffer para ordenação em lote
                buffer_produtos.append((prod_id, cat_code, brand, price))

                if len(buffer_produtos) >= CHUNK_SIZE:
                    salvar_run_produto(buffer_produtos, pasta_temp_prod, run_idx)
                    run_idx += 1
                    buffer_produtos.clear()

            except (ValueError, IndexError):
                continue

        if buffer_produtos:
            salvar_run_produto(buffer_produtos, pasta_temp_prod, run_idx)
            run_idx += 1
            buffer_produtos.clear()

    print(f"eventos.dat e eventos.idx concluídos: {event_id - 1:,} eventos.")
    print(f"{run_idx} partições temporárias de produtos criadas.")
    return pasta_temp_prod


def salvar_run_produto(lote, temp_dir, idx):
    lote.sort(key=lambda x: x[0])  # Ordena pela chave (prod_id)
    caminho = os.path.join(temp_dir, f"run_{idx:04d}.tmp")
    with open(caminho, "wb") as f_out:
        for p_id, cat, brand, price in lote:
            f_out.write(pack_produto(p_id, cat, brand, price))


# ==========================================
# FASE 2: MERGE DOS PRODUTOS COM DEDUPLICAÇÃO
# ==========================================
class LeitorRun:

    def __init__(self, filepath):
        self.file = open(filepath, "rb")
        self.buffer = None
        self.key = None
        self.avancar()

    def avancar(self):
        self.buffer = self.file.read(PROD_SIZE)
        if self.buffer:
            self.key = struct.unpack_from(">Q", self.buffer, 0)[0]
        else:
            self.file.close()
            self.buffer = None
            self.key = None

    def __lt__(self, other):
        return self.key < other.key


def intercalar_produtos(pasta_temp, prod_dat, prod_idx):
    print("Iniciando intercalação externa dos produtos...")
    arquivos = sorted(glob.glob(os.path.join(pasta_temp, "run_*.tmp")))

    heap = [LeitorRun(path) for path in arquivos if os.path.getsize(path) > 0]
    heapq.heapify(heap)

    ultimo_id = None
    produtos_gravados = 0

    with open(prod_dat, "wb") as f_dat, open(prod_idx, "wb") as f_idx:
        while heap:
            menor = heapq.heappop(heap)

            # Deduplicação em disco: descarta chaves repetidas consecutivas
            if menor.key != ultimo_id:
                ultimo_id = menor.key
                offset = f_dat.tell()

                if produtos_gravados % BLOCK_FACTOR == 0:
                    f_idx.write(struct.pack(IDX_FMT, menor.key, offset))

                f_dat.write(menor.buffer)
                produtos_gravados += 1

            menor.avancar()
            if menor.buffer:
                heapq.heappush(heap, menor)

    shutil.rmtree(pasta_temp)
    print(
        f"produtos.dat e produtos.idx concluídos com sucesso: {produtos_gravados:,} produtos únicos."
    )


# ==========================================
# EXECUÇÃO DO PIPELINE
# ==========================================
if __name__ == "__main__":
    CSV_ORIGINAL = "2019-Oct.csv"  # Ajuste para o caminho do arquivo do Kaggle

    # Gera ambos os arquivos e ambos os índices em streaming
    temp_dir = processar_csv(
        CSV_ORIGINAL, "eventos.dat", "eventos.idx"
    )
    intercalar_produtos(temp_dir, "produtos.dat", "produtos.idx")