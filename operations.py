import os
import struct
from indexer import construir_indice_parcial

PROD_REC_FORMAT = ">Q32s20sdc1s"
PROD_REC_SIZE = struct.calcsize(PROD_REC_FORMAT)  # 70 bytes

IDX_FORMAT = ">QQ"
IDX_REC_SIZE = struct.calcsize(IDX_FORMAT)  # 16 bytes

BLOCK_FACTOR = 100
OFFSET_FLAG_DELETE_PROD = 68  # Deslocamento em bytes do campo is_deleted


def buscar_bloco_no_indice(idx_file, target_key, total_entries):
    low = 0
    high = total_entries - 1
    offset_candidato = 0

    while low <= high:
        mid = (low + high) // 2
        idx_file.seek(mid * IDX_REC_SIZE, os.SEEK_SET)
        key, offset = struct.unpack(IDX_FORMAT, idx_file.read(IDX_REC_SIZE))

        if key <= target_key:
            offset_candidato = offset
            low = mid + 1
        else:
            high = mid - 1

    return offset_candidato


# ==========================================
# 1) REMOÇÃO LÓGICA (Soft Delete)
# ==========================================
def remover_produto(prod_id, dat_path="produtos.dat", idx_path="produtos.idx"):
    """
    Localiza o registro via índice parcial e sobrescreve
    apenas o byte is_deleted (de b'0' para b'1') in-place.
    """
    total_idx = os.path.getsize(idx_path) // IDX_REC_SIZE

    with open(idx_path, "rb") as f_idx, open(dat_path, "r+b") as f_dat:
        offset_bloco = buscar_bloco_no_indice(f_idx, prod_id, total_idx)
        f_dat.seek(offset_bloco, os.SEEK_SET)

        for _ in range(BLOCK_FACTOR):
            pos_registro = f_dat.tell()
            buffer = f_dat.read(PROD_REC_SIZE)
            if not buffer:
                break

            p_id, _, _, _, is_del, _ = struct.unpack(PROD_REC_FORMAT, buffer)

            if p_id == prod_id:
                if is_del == b"1":
                    print(f"Produto {prod_id} já se encontra removido.")
                    return False

                # Posiciona exatamente sobre o byte do is_deleted
                f_dat.seek(pos_registro + OFFSET_FLAG_DELETE_PROD, os.SEEK_SET)
                f_dat.write(b"1")
                print(f"Produto {prod_id} removido logicamente com sucesso!")
                return True

            if p_id > prod_id:
                break

    print(f"Produto {prod_id} não encontrado.")
    return False


# ==========================================
# 2) INSERÇÃO E RECONSTRUÇÃO
# ==========================================
def inserir_produto(
    prod_id,
    categoria,
    marca,
    preco,
    dat_path="produtos.dat",
    idx_path="produtos.idx",
):
    """
    Insere o registro no final e dispara a reorganização
    para restaurar a ordenação física e reconstruir o índice.
    """
    cat_padded = (
        categoria.strip().ljust(32)[:32].encode("utf-8", errors="ignore")
    )
    brand_padded = marca.strip().ljust(20)[:20].encode("utf-8", errors="ignore")
    novo_reg = struct.pack(
        PROD_REC_FORMAT, prod_id, cat_padded, brand_padded, preco, b"0", b"\n"
    )

    with open(dat_path, "ab") as f_dat:
        f_dat.write(novo_reg)

    print(
        f"Registro {prod_id} inserido. Iniciando reorganização e rebuild do índice..."
    )
    reconstruir_arquivo_produtos(dat_path, idx_path)
    print("Base e índice reorganizados com sucesso.")


def reconstruir_arquivo_produtos(
    dat_path="produtos.dat", idx_path="produtos.idx"
):
    """
    Purga registros marcados como excluídos (is_deleted = 1),
    reordena os dados e recria o índice parcial.
    """
    temp_dat = dat_path + ".rebuild.tmp"
    temp_idx = idx_path + ".rebuild.tmp"

    registros = []
    with open(dat_path, "rb") as f_in:
        while chunk := f_in.read(PROD_REC_SIZE):
            p_id, cat, brand, price, is_del, _ = struct.unpack(
                PROD_REC_FORMAT, chunk
            )
            if is_del != b"1":
                registros.append((p_id, cat, brand, price))

    # Reordena em memória os registros consolidados
    registros.sort(key=lambda x: x[0])

    with open(temp_dat, "wb") as f_out:
        for p_id, cat, brand, price in registros:
            f_out.write(
                struct.pack(
                    PROD_REC_FORMAT, p_id, cat, brand, price, b"0", b"\n"
                )
            )

    # Reconstrói o índice parcial a partir do arquivo reorganizado
    construir_indice_parcial(temp_dat, temp_idx, PROD_REC_SIZE)

    os.replace(temp_dat, dat_path)
    os.replace(temp_idx, idx_path)