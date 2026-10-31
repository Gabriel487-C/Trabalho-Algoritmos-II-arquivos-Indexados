import os
import struct


# produtos.dat (70 bytes):
# Q (8B) + 32s (32B) + 20s (20B) + d (8B) + c (1B) + 1s (1B '\n')
PROD_REC_FORMAT = ">Q32s20sdc1s"
PROD_REC_SIZE = struct.calcsize(PROD_REC_FORMAT)

# eventos.dat (38 bytes):
# Q (8B) + 12s (12B) + Q (8B) + Q (8B) + c (1B) + 1s (1B '\n')
EVENT_REC_FORMAT = ">Q12sQQc1s"
EVENT_REC_SIZE = struct.calcsize(EVENT_REC_FORMAT)

# Arquivos de índice parcial (16 bytes):
# Q (chave 8B) + Q (offset 8B)
IDX_FORMAT = ">QQ"
IDX_REC_SIZE = struct.calcsize(IDX_FORMAT)

BLOCK_FACTOR = 100


# ==========================================
# BUSCA BINÁRIA NO ÍNDICE PARCIAL
# ==========================================
def buscar_bloco_no_indice(idx_file_handle, target_key, total_idx_entries):
    """Localiza o offset do bloco candidato via busca binária no arquivo .idx."""
    low = 0
    high = total_idx_entries - 1
    offset_candidato = 0

    while low <= high:
        mid = (low + high) // 2
        idx_file_handle.seek(mid * IDX_REC_SIZE, os.SEEK_SET)
        key, offset = struct.unpack(
            IDX_FORMAT, idx_file_handle.read(IDX_REC_SIZE)
        )

        if key <= target_key:
            offset_candidato = offset
            low = mid + 1
        else:
            high = mid - 1

    return offset_candidato


# ==========================================
# BUSCA DE PRODUTO (ÍNDICE + SEEK)
# ==========================================
def buscar_produto(
    target_prod_id, dat_path="produtos.dat", idx_path="produtos.idx"
):
    """Consulta um produto utilizando o índice parcial e varredura curta no .dat."""
    if not os.path.exists(idx_path) or not os.path.exists(dat_path):
        return None

    total_idx_entries = os.path.getsize(idx_path) // IDX_REC_SIZE

    with open(idx_path, "rb") as f_idx, open(dat_path, "rb") as f_dat:
        offset_bloco = buscar_bloco_no_indice(
            f_idx, target_prod_id, total_idx_entries
        )
        f_dat.seek(offset_bloco, os.SEEK_SET)

        for _ in range(BLOCK_FACTOR):
            buffer = f_dat.read(PROD_REC_SIZE)
            if not buffer:
                break

            prod_id, cat, brand, price, is_del, _ = struct.unpack(
                PROD_REC_FORMAT, buffer
            )

            if prod_id == target_prod_id:
                if is_del == b"1":
                    return None
                return {
                    "product_id": prod_id,
                    "category": cat.decode("utf-8", errors="ignore").strip(),
                    "brand": brand.decode("utf-8", errors="ignore").strip(),
                    "price": round(price, 2),
                }

            if prod_id > target_prod_id:
                break

    return None


# ==========================================
# BUSCA DE EVENTO + JOIN COM PRODUTO
# ==========================================
def buscar_evento_com_produto(
    target_event_id,
    events_dat="eventos.dat",
    events_idx="eventos.idx",
    prod_dat="produtos.dat",
    prod_idx="produtos.idx",
):
    """Consulta um evento e faz a junção dos dados do produto via índice."""
    if not os.path.exists(events_idx) or not os.path.exists(events_dat):
        return None

    total_idx_entries = os.path.getsize(events_idx) // IDX_REC_SIZE

    with open(events_idx, "rb") as f_idx, open(events_dat, "rb") as f_dat:
        offset_bloco = buscar_bloco_no_indice(
            f_idx, target_event_id, total_idx_entries
        )
        f_dat.seek(offset_bloco, os.SEEK_SET)

        evento = None
        for _ in range(BLOCK_FACTOR):
            buffer = f_dat.read(EVENT_REC_SIZE)
            if not buffer:
                break

            ev_id, ev_type, user_id, prod_id, is_del, _ = struct.unpack(
                EVENT_REC_FORMAT, buffer
            )

            if ev_id == target_event_id:
                if is_del != b"1":
                    evento = {
                        "event_id": ev_id,
                        "event_type": ev_type.decode(
                            "utf-8", errors="ignore"
                        ).strip(),
                        "user_id": user_id,
                        "product_id": prod_id,
                    }
                break

            if ev_id > target_event_id:
                break

    if not evento:
        return None

    # Join com catálogo de produtos
    evento["produto"] = buscar_produto(
        evento["product_id"], dat_path=prod_dat, idx_path=prod_idx
    )
    return evento


# ==========================================
# VISUALIZAÇÃO PARCIAL DE DADOS
# ==========================================
def mostrar_produtos_parcial(dat_path="produtos.dat", limit=10):
    """Lê sequencialmente os primeiros registros ativos do arquivo de produtos."""
    if not os.path.exists(dat_path):
        print("Arquivo de dados não encontrado.")
        return

    print("\n" + "-" * 75)
    print(f"{'ID':<12} | {'Categoria':<30} | {'Marca':<15} | {'Preço':<10}")
    print("-" * 75)

    with open(dat_path, "rb") as f_dat:
        count = 0
        while buffer := f_dat.read(PROD_REC_SIZE):
            p_id, cat, brand, price, is_del, _ = struct.unpack(
                PROD_REC_FORMAT, buffer
            )
            if is_del != b"1":
                categoria = cat.decode("utf-8", errors="ignore").strip()
                marca = brand.decode("utf-8", errors="ignore").strip()
                print(
                    f"{p_id:<12} | {categoria:<30} | {marca:<15} | ${price:<9.2f}"
                )
                count += 1
                if limit and count >= limit:
                    break
    print("-" * 75)
    
    import os
import struct
from collections import Counter

# Importa as constantes e a busca por índice já existentes em search.py
from search import (
    EVENT_REC_FORMAT,
    EVENT_REC_SIZE,
    buscar_produto,
)


def relatorio_top_vendas_e_marcas(
    top_n=10,
    events_dat="eventos.dat",
    prod_dat="produtos.dat",
    prod_idx="produtos.idx",
):
    """Analisa os eventos de compra ('purchase') e identifica os produtos

    mais vendidos e as marcas (empresas) com maior volume de vendas.
    """
    if not os.path.exists(events_dat):
        print(f"Arquivo '{events_dat}' não encontrado.")
        return

    # Contadores leves de frequência (inteiro -> contagem)
    contador_produtos = Counter()
    contador_marcas = Counter()
    total_compras = 0

    print("\nProcessando eventos de compra...")

    # Leitura sequencial em blocos (buffer de 64 KB para acelerar o I/O em disco)
    CHUNK_BYTES = EVENT_REC_SIZE * 2000  # lê 2.000 registros por passada

    with open(events_dat, "rb") as f_ev:
        while buffer := f_ev.read(CHUNK_BYTES):
            total_lidos = len(buffer) // EVENT_REC_SIZE

            for i in range(total_lidos):
                slice_reg = buffer[i * EVENT_REC_SIZE : (i + 1) * EVENT_REC_SIZE]
                (
                    ev_id,
                    ev_type_raw,
                    user_id,
                    prod_id,
                    is_del,
                    _,
                ) = struct.unpack(EVENT_REC_FORMAT, slice_reg)

                if is_del == b"1":
                    continue

                # Normaliza o tipo de evento (remove bytes nulos ou espaços)
                ev_type = (
                    ev_type_raw.decode("utf-8", errors="ignore")
                    .strip()
                    .lower()
                )

                if ev_type == "purchase":
                    contador_produtos[prod_id] += 1
                    total_compras += 1

    if total_compras == 0:
        print("Nenhum evento do tipo 'purchase' foi encontrado.")
        return

    print(f"Total de compras registradas: {total_compras:,}")

   
    print("\n" + "=" * 80)
    print(f"TOP {top_n} PRODUTOS MAIS VENDIDOS")
    print("=" * 80)
    print(
        f"{'Pos.':<5} | {'ID Produto':<12} | {'Vendas':<8} | {'Marca':<16} | {'Preço':<10} | {'Categoria':<20}"
    )
    print("-" * 80)

    top_produtos = contador_produtos.most_common(top_n)

    for rank, (prod_id, qtd) in enumerate(top_produtos, 1):
        # Busca no produtos.dat usando o índice parcial existente (seek logarítmico)
        info_prod = buscar_produto(
            prod_id, dat_path=prod_dat, idx_path=prod_idx
        )

        marca = info_prod["brand"] if info_prod and info_prod["brand"] else "N/D"
        categoria = (
            info_prod["category"]
            if info_prod and info_prod["category"]
            else "N/D"
        )
        preco = f"${info_prod['price']:.2f}" if info_prod else "N/D"

        # Abrevia campos longos para manter alinhamento
        categoria_curta = (
            (categoria[:18] + "..") if len(categoria) > 20 else categoria
        )
        marca_curta = (marca[:14] + "..") if len(marca) > 16 else marca

        print(
            f"{rank:<5} | {prod_id:<12} | {qtd:<8} | {marca_curta:<16} | {preco:<10} | {categoria_curta:<20}"
        )

        if marca != "N/D":
            contador_marcas[marca] += qtd

    
    print("\n" + "=" * 50)
    print(f"TOP MARCAS MAIS VENDIDAS (Entre os produtos líderes)")
    print("=" * 50)
    print(f"{'Pos.':<5} | {'Marca / Empresa':<25} | {'Unidades':<10}")
    print("-" * 50)

    for rank, (marca, total_unidades) in enumerate(
        contador_marcas.most_common(top_n), 1
    ):
        print(f"{rank:<5} | {marca:<25} | {total_unidades:<10}")
    print("=" * 50 + "\n")