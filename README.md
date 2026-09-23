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

A janela principal mostra as abas de consulta ("Consultar por Mês" e "Consulta
Detalhada"). A tela de catalogação fica separada, aberta pelo menu
**Arquivo → Catalogar PDFs...** — assim ela pode ficar aberta numa janela à
parte enquanto você continua navegando/consultando na janela principal. Ao
fechá-la, as duas abas de consulta são atualizadas automaticamente com o que
foi cadastrado.

O menu **Ajuda → Como usar** abre um resumo rápido de todas as telas direto
dentro do programa, sem precisar consultar este arquivo.

## Guia de uso

### Janela "Catalogar PDFs" (menu Arquivo → Catalogar PDFs...)

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

### Aba "Consulta Detalhada"

1. Escolha o setor e o ano.
2. **Funcionário é opcional**:
   - Deixe em branco e clique em **Consultar** para ver **todos os
     funcionários do setor** de uma vez, em formato de grade: uma linha por
     funcionário, uma coluna para cada mês (Jan a Dez), ordenados por nome.
   - Escolha um funcionário específico para ver só a linha dele.
3. Cada célula de mês mostra ✔ (entregue) ou ✘ (faltando). Funcionários com
   pelo menos um mês entregue no ano ficam com a linha toda num verde bem
   claro, para destacar de relance quem já tem algo registrado.
4. Dê duplo clique numa célula ✔ para abrir o PDF daquele mês.

**Funcionários inativos "somem" só no ano corrente:** quando o Ano escolhido
é o ano atual, quem está marcado como inativo (veja a janela "Gerenciar
Funcionários" abaixo) não aparece na consulta do setor inteiro (nem em
"Consultar por Mês"), pra não poluir a lista com quem já não trabalha mais
ali. Anos anteriores sempre mostram todo mundo, ativo ou não — o histórico de
quem já entregou frequência naquele ano não desaparece. Escolher um
funcionário específico no combobox sempre funciona, mesmo que ele esteja
inativo e seja o ano corrente.

### Janela "Gerenciar Funcionários" (menu Arquivo → Gerenciar Funcionários...)

Marca quem está ativo ou inativo — usado pra esconder quem já não trabalha
mais das consultas do ano corrente, sem apagar nada do histórico.

- **Buscar** (por nome) e **Status** (Todos/Ativos/Inativos) filtram a lista.
  Acima da dica no rodapé, um resumo mostra quantos aparecem no filtro atual,
  ex: `3 funcionários — 1 ativo, 2 inativos`.
- **Alternar Ativo/Inativo**: selecione um funcionário na lista e clique no
  botão (ou dê duplo clique na linha) para trocar o status.
- **Importar CSV...**: lê uma **relação de quem está ativo hoje** — arquivo
  `Nome;Setor` (uma linha por pessoa, com ou sem cabeçalho; a coluna Setor é
  só informativa, a comparação é pelo nome). Quem está ativo no banco mas não
  aparece nessa lista vira candidato a **inativar**; quem está inativo no
  banco e aparece na lista vira candidato a **reativar**. Nada é aplicado na
  hora — abre uma **tela de revisão** com os candidatos já pré-marcados
  (desmarque o que não quiser aplicar) e só grava no banco depois de clicar
  em **Confirmar**. Comparação tolerante a acento/maiúsculas. Essa tela nunca
  cria funcionário ou setor novo — só ajusta o status de quem já foi
  catalogado.
- **Exportar CSV**: gera a mesma relação (`Nome;Setor`) só dos funcionários
  **ativos** — serve de ponto de partida ou conferência para a próxima
  importação.

Como sempre: nenhum PDF, funcionário, setor ou frequência é apagado por essa
tela — "inativo" é só uma marca reversível.

> O programa é usado por várias pessoas no mesmo banco de dados
> compartilhado no servidor do RH, por isso não existe (propositalmente)
> nenhuma tela para **excluir** funcionário, setor ou frequência — um clique
> errado apagaria cadastro de outra pessoa. Correções (nome digitado errado,
> setor duplicado, etc.) exigem edição direta do arquivo `freqcontrol.db`
> (por exemplo, com o [DB Browser for SQLite](https://sqlitebrowser.org/)).

## Estrutura do banco de dados (SQLite)

- `setores` — id, nome (único)
- `funcionarios` — id, nome, setor_id (único por nome + setor)
- `frequencias` — id, funcionario_id, mes (1–12), ano, caminho_arquivo
  (caminho UNC resolvido), data_cadastro (único por funcionário + mês + ano)
