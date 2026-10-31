# Trabalho-Algoritmos-II-arquivos-Indexados

Sistema de Arquivos Indexado-Sequencial (eCommerce Behavior)

Este projeto implementa uma organização de arquivos indexado-sequencial em modo binário para manipulação e consulta de grandes volumes de dados (base de dados de comportamento de e-commerce do Kaggle), operando sob restrição estrita de consumo de memória RAM.
1. Estrutura dos Arquivos de Dados e Índices

Os registros possuem tamanho estritamente fixo e são terminados com o caractere \n, viabilizando o cálculo exato de deslocamento em bytes (offsets) via comando seek().

    produtos.dat (70 bytes por registro):

        product_id (8 bytes, uint64) - Chave primária única, fisicamente ordenada.

        category_code (32 bytes, texto fixo).

        brand (20 bytes, texto fixo).

        price (8 bytes, double).

        is_deleted (1 byte, char) - Flag de controle para remoção lógica.

        \n (1 byte, char) - Delimitador de fim de linha.

    eventos.dat (38 bytes por registro):

        event_id (8 bytes, uint64) - Chave primária sequencial única.

        event_type (12 bytes, texto fixo).

        user_id (8 bytes, uint64).

        product_id (8 bytes, uint64) - Chave estrangeira para junção.

        is_deleted (1 byte, char).

        \n (1 byte, char).

    Arquivos de Índice (produtos.idx e eventos.idx - 16 bytes por registro):

        Estruturados como índices parciais (esparsos) de 1 único nível.

        Cada entrada armazena o par (chave, offset) a cada bloco de 100 registros (BLOCK_FACTOR = 100), reduzindo drasticamente o tamanho do índice em disco.

2. Processamento e Carga Inicial (External Merge Sort)

Para ordenar e deduplicar os dados brutos sem estourar a memória RAM da máquina:

    Particionamento em Runs: O arquivo de origem foi processado em blocos fixos na memória, ordenado e despejado em 142 arquivos temporários binários.

    K-Way Merge via Min-Heap: Os arquivos temporários foram intercalados simultaneamente com leitura sob demanda (1 registro por arquivo no heap), eliminando duplicatas de produtos consecutivos e gravando os índices parciais na mesma passada.

3. Funcionalidades Implementadas

    Visualização Parcial: Leitura sequencial de blocos de registros respeitando os limites de bytes fixos para listagem em terminal.

    Busca por Índice Parcial + seek(): Realiza busca binária dentro do arquivo .idx para identificar o bloco candidato e, em seguida, posiciona a cabeça de leitura no arquivo .dat via seek(offset) para uma varredura sequencial curta de no máximo 100 registros.

    Consulta Relacional (Join): Localiza o registro de acesso em eventos.dat, extrai o product_id e executa a busca indexada em produtos.dat para exibir os detalhes do produto associado ao evento.

    Remoção Lógica (Soft Delete): Localiza o registro via índice e altera diretamente em disco (r+b) a flag is_deleted de b'0' para b'1', preservando a integridade física dos offsets sem a necessidade de reescrever o arquivo.

    Inserção e Reconstrução: Novos registros são gravados no arquivo de dados, disparando a rotina de purga dos itens removidos, reordenação e regravação do arquivo .idx.

4. Estrutura dos Módulos

    carga_inicial.py: Script executado uma única vez para extração em streaming, particionamento externo e geração dos arquivos .dat e .idx.

    indexer.py: Módulo com a lógica de varredura e geração de índices parciais esparsos.

    search.py: Módulo contendo busca binária no índice, navegação com seek() e junções de tabelas.

    operations.py: Funções de inserção de registros, alteração in-place da flag de remoção e rotinas de reconstrução.

    main.py: Ponto de entrada com menu interativo em linha de comando para execução de todas as operações do sistema.

5. Como Executar

Com os arquivos de dados e índices gerados no diretório do projeto, inicie a interface de linha de comando:
