import os
import sys

from operations import inserir_produto, remover_produto
from search import (
    buscar_evento_com_produto,
    buscar_produto,
    mostrar_produtos_parcial,
    relatorio_top_vendas_e_marcas,
)

ARQUIVOS_BASE = [
    "produtos.dat",
    "produtos.idx",
    "eventos.dat",
    "eventos.idx",
]


def validar_arquivos():
    faltantes = [f for f in ARQUIVOS_BASE if not os.path.exists(f)]
    if faltantes:
        print("Erro: Os seguintes arquivos necessários não foram encontrados:")
        for f in faltantes:
            print(f" - {f}")
        print("Aguarde a finalização do processo de extração/intercalação.")
        sys.exit(1)


def main():
    validar_arquivos()

    while True:
        print("\n" + "=" * 50)
        print("   SISTEMA DE ARQUIVOS INDEXADO-SEQUENCIAL")
        print("=" * 50)
        print("1. Listar produtos (visão parcial)")
        print("2. Buscar produto por ID (Índice Parcial + seek)")
        print("3. Buscar evento com Join em produto")
        print("4. Inserir novo produto")
        print("5. Remover produto (exclusão lógica)")
        print("6. Relatório: Produtos mais vendidos e maiores empresas")
        print("0. Sair")
        print("=" * 50)

        opcao = input("Selecione uma opção: ").strip()

        if opcao == "1":
            qtd = int(
                input("Quantos registros deseja exibir? (padrão: 10): ") or "10"
            )
            mostrar_produtos_parcial("produtos.dat", limit=qtd)

        elif opcao == "2":
            p_id = int(input("Informe o product_id: "))
            res = buscar_produto(p_id)
            if res:
                print(f"\n[Produto Encontrado]")
                print(f"ID:        {res['product_id']}")
                print(f"Categoria: {res['category']}")
                print(f"Marca:     {res['brand']}")
                print(f"Preço:     ${res['price']:.2f}")
            else:
                print("\nProduto não encontrado ou removido.")

        elif opcao == "3":
            ev_id = int(input("Informe o event_id: "))
            res = buscar_evento_com_produto(ev_id)
            if res:
                print(f"\n[Evento Encontrado]")
                print(f"ID do Evento:  {res['event_id']}")
                print(f"Tipo de Acesso:{res['event_type']}")
                print(f"ID do Usuário: {res['user_id']}")
                print(f"ID do Produto: {res['product_id']}")
                if res.get("produto"):
                    prod = res["produto"]
                    print(
                        f"Detalhes do Produto: {prod['brand']} | {prod['category']} | ${prod['price']:.2f}"
                    )
            else:
                print("\nEvento não encontrado.")

        elif opcao == "4":
            try:
                p_id = int(input("ID do novo produto: "))
                cat = input("Categoria: ")
                marca = input("Marca: ")
                preco = float(input("Preço: "))
                inserir_produto(p_id, cat, marca, preco)
            except ValueError:
                print("Entrada inválida. Operação cancelada.")

        elif opcao == "5":
            p_id = int(input("ID do produto a ser removido: "))
            remover_produto(p_id)
            
        elif opcao == "6":
            top = input("Quantos líderes deseja listar? (Padrão: 10): ").strip()
            limite = int(top) if top.isdigit() else 10
            relatorio_top_vendas_e_marcas(top_n=limite)    

        elif opcao == "0":
            print("Encerrando execução.")
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()