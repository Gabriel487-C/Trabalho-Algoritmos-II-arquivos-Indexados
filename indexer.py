import os
import struct

# ========================================================
# CONFIGURAÇÕES E CONSTANTES
# ========================================================
IDX_FORMAT = ">QQ"
IDX_REC_SIZE = struct.calcsize(IDX_FORMAT)  # 16 bytes: 8B chave + 8B offset

BLOCK_FACTOR = 100         # 1 entrada no índice a cada 100 registros
IO_BUFFER_RECORDS = 50_000 # Lê em lotes de 50.000 registros para não usar RAM


def construir_indice_parcial(dat_path, idx_path, rec_size, key_offset=0, key_format=">Q"):
    """
    Lê o arquivo de dados .dat (que deve estar ordenado) em blocos de memória
    e gera o arquivo de índice parcial esparso .idx.
    """
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {dat_path}")

    bytes_por_lote = IO_BUFFER_RECORDS * rec_size
    contador_registros = 0
    entradas_indice = 0

    with open(dat_path, "rb") as f_dat, open(idx_path, "wb") as f_idx:
        offset_global = 0

        while True:
            bloco_bytes = f_dat.read(bytes_por_lote)
            if not bloco_bytes:
                break

            total_lidos = len(bloco_bytes) - (len(bloco_bytes) % rec_size)

            for i in range(0, total_lidos, rec_size):
                if contador_registros % BLOCK_FACTOR == 0:
                    # Extrai apenas os bytes da chave primária
                    registro_buffer = bloco_bytes[i : i + rec_size]
                    chave = struct.unpack_from(key_format, registro_buffer, key_offset)[0]

                    offset_registro = offset_global + i

                    # Grava no índice: (chave_primária, offset_no_dat)
                    f_idx.write(struct.pack(IDX_FORMAT, chave, offset_registro))
                    entradas_indice += 1

                contador_registros += 1

            offset_global += total_lidos

    print(f"Índice {idx_path} gerado com sucesso: {entradas_indice:,} entradas.")