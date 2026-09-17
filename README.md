# FreqControl

Programa desktop leve para o RH **catalogar e consultar** os PDFs de frequência
(folhas de ponto) já organizados manualmente no servidor, na seguinte estrutura
(que já vem pronta e não é criada nem alterada pelo programa):

```
<Pasta raiz no servidor>/
  <Setor>/
    <Funcionário>/
      <Ano>/
        Janeiro.pdf
        Fevereiro.pdf
        ...
```

**O programa nunca move, copia, renomeia ou apaga nenhum PDF.** Ele apenas lê e
grava o *caminho* de cada arquivo em um banco de dados (SQLite) compartilhado.

## Requisitos

- Windows (usa a API `WNetGetUniversalName` do Windows para resolver caminhos de rede)
- Python 3.9+ apenas para rodar a partir do código-fonte ou gerar o `.exe` — quem só for **usar** o `.exe` já empacotado não precisa de Python instalado
- Nenhuma biblioteca externa: usa apenas a biblioteca padrão (`tkinter`, `sqlite3`, `ctypes`, `csv`, `json`, `os`, `sys`)

## Como executar a partir do código-fonte

```powershell
python freqcontrol.py
```

## Como gerar o executável (.exe) com PyInstaller

1. Instale o PyInstaller uma única vez (precisa de internet):

```powershell
pip install pyinstaller
```

2. Na pasta do projeto, gere o executável único:

```powershell
pyinstaller --onefile --windowed --name FreqControl freqcontrol.py
```

3. O executável fica em `dist\FreqControl.exe`. Distribua apenas esse arquivo
   — ele não precisa de Python instalado no computador de destino.

Observações:

- `--onefile` gera um único `.exe`; `--windowed` evita abrir uma janela de
  console por trás da interface gráfica.
- Gere o `.exe` em um Windows de verdade (não em WSL/Linux/Mac), pois o
  PyInstaller empacota para a plataforma onde é executado.
- As pastas `build\` e o arquivo `FreqControl.spec` gerados pelo PyInstaller
  podem ser apagados depois — só o `dist\FreqControl.exe` importa.

## Primeira execução (configurar o banco de dados)

Na primeira vez que o programa abre em um computador, ele pede para selecionar
a **pasta compartilhada do RH** onde o arquivo `freqcontrol.db` deve ficar (ou
já está, se outro usuário já configurou). Essa deve ser a mesma pasta restrita
do RH para todos os usuários, para que todos compartilhem os mesmos dados.

O programa resolve automaticamente a pasta escolhida para o caminho de rede
completo (UNC, ex: `\\Servidor\RH\FreqControl`), mesmo que você tenha
selecionado por uma letra de unidade mapeada (ex: `Z:\FreqControl`). Isso
evita que o caminho quebre em outro computador com um mapeamento de unidade
diferente. Essa escolha fica salva em `%APPDATA%\FreqControl\config.json`,
específico de cada usuário/computador.

Se precisar trocar depois (por exemplo, o caminho do servidor mudou), use o
menu **Arquivo → Alterar pasta do banco de dados...**

## Guia de uso

### Aba "Catalogar PDFs"

1. Clique em **Selecionar Pasta Raiz...** e escolha a pasta que contém a
   estrutura `Setor/Funcionário/Ano/Mês.pdf`.
2. A lista mostra todos os PDFs encontrados que **ainda não** estão
   cadastrados no banco.
3. Clique em um arquivo da lista e depois em **Abrir PDF para Conferência**
   para visualizar o conteúdo antes de cadastrar (abre no leitor de PDF
   padrão do Windows).
4. Preencha manualmente **Setor**, **Funcionário** (pode digitar um nome novo
   para criar), **Mês** e **Ano** — o programa não tenta adivinhar esses
   valores pelo nome do arquivo ou da pasta.
5. Clique em **Salvar**. Se já existir uma frequência entregue para aquele
   funcionário no mesmo mês/ano, o programa pergunta se deseja **substituir o
   registro** (o arquivo em disco nunca é alterado, apenas o cadastro).
6. Use **Pular** para deixar o arquivo atual de lado e ir para o próximo sem
   cadastrar.

#### Cadastro em lote ("Cadastrar Todos os Pendentes")

Se a estrutura de pastas já está corretamente organizada como
`Setor/Funcionário/Ano/Mês.pdf`, o botão **Cadastrar Todos os Pendentes (usa
nome das pastas)...** cadastra de uma vez todos os PDFs pendentes, usando os
nomes das pastas como Setor/Funcionário/Ano e o nome do arquivo como Mês —
**sem conferência individual de cada PDF**.

- Reconhece nomes de mês com ou sem acento (ex: `Marco.pdf` e `Março.pdf`).
- Arquivos cuja pasta não tem exatamente 4 níveis (Setor/Funcionário/Ano/Mês),
  ano inválido, ou nome de mês não reconhecido **são pulados** e continuam na
  lista para cadastro manual depois.
- Não sobrescreve registros que já existem no banco (evita duplicar em uma
  segunda execução).
- Use com cuidado: como não há conferência visual do conteúdo de cada PDF,
  só use quando tiver certeza de que a organização das pastas está correta.

### Aba "Consultar por Mês"

1. Escolha o mês e o ano e clique em **Consultar**.
2. A tabela mostra todos os funcionários (agrupados por setor) com status
   verde (entregue) ou vermelho (faltando), e um resumo com a contagem.
3. Dê duplo clique em uma linha entregue para abrir o PDF correspondente.
4. Clique em **Exportar CSV** para salvar o resultado da consulta atual
   (separador `;`, codificação compatível com Excel em português).

### Aba "Consultar por Funcionário"

1. Escolha o setor, o funcionário e o ano, depois clique em **Consultar**.
2. A tabela mostra os 12 meses do ano com o status de cada um.
3. Dê duplo clique em um mês entregue para abrir o PDF.

### Aba "Funcionários e Setores"

- Lista todos os funcionários cadastrados com seus respectivos setores.
- **Excluir Funcionário Selecionado**: remove apenas o cadastro do
  funcionário (e seu histórico de frequências) do banco — os PDFs no
  servidor **não** são apagados.
- **Excluir Setor**: remove um setor inteiro (e todos os funcionários e
  frequências dele) do banco — os PDFs no servidor **não** são apagados.

## Estrutura do banco de dados (SQLite)

- `setores` — id, nome (único)
- `funcionarios` — id, nome, setor_id (único por nome + setor)
- `frequencias` — id, funcionario_id, mes (1–12), ano, caminho_arquivo
  (caminho UNC resolvido), data_cadastro (único por funcionário + mês + ano)
