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

## Passo a passo para instalação

> Esse guia é pra quem nunca mexeu com isso antes. Se você só vai **usar**
> o programa (não vai mexer no código), pule direto pro **Passo 5**.

**Passo 1: Baixar o programa**
No GitHub, clique no botão verde **Code** → **Download ZIP**, e extraia a
pasta em qualquer lugar do computador (ex: `Documentos\FreqControl`).

**Passo 2: Instalar o Python**
Baixe em [python.org/downloads](https://www.python.org/downloads/) e
instale. Na primeira tela do instalador, marque a caixinha **"Add
python.exe to PATH"** antes de clicar em Install — isso é importante, sem
isso os comandos abaixo não funcionam.

**Passo 3: Instalar a peça que falta (reportlab)**
Abra o PowerShell dentro da pasta onde você extraiu o programa (clique com
o botão direito numa área vazia da pasta e escolha "Abrir no Terminal" ou
"Abrir janela do PowerShell aqui") e rode:

```powershell
pip install reportlab
```

**Passo 4: Gerar o programa (.exe)**
Ainda no PowerShell, na mesma pasta, rode estes dois comandos, um de cada
vez:

```powershell
pip install pyinstaller reportlab
pyinstaller --onefile --windowed --name FreqControl --add-data "assets/brasao_para.png;assets" freqcontrol.py
```

Isso pode demorar um minutinho. Quando terminar, vai aparecer uma pasta
nova chamada `dist` dentro da pasta do projeto.

**Passo 5: Usar o programa**
Dentro da pasta `dist`, tem um arquivo chamado `FreqControl.exe` — é só dar
dois cliques nele pra abrir. Esse é o único arquivo que importa: pode
copiar só ele (pendrive, e-mail, pasta de rede) pra qualquer outro
computador Windows e usar lá, sem precisar instalar Python nem nada do que
foi feito nos passos 2 a 4 de novo.

**Passo 6: Primeira vez que abrir**
Na primeira vez que o FreqControl abrir em um computador, ele vai pedir pra
escolher a pasta compartilhada do RH onde os dados ficam salvos — escolha a
pasta certa (a mesma que todo mundo do setor vai usar) e pronto, já pode
usar.

> Atenção: o FreqControl só funciona em Windows (os passos 2 a 4 também só
> funcionam gerando o `.exe` num Windows de verdade, não em Mac/Linux).

## Requisitos

- Windows (usa a API `WNetGetUniversalName` do Windows para resolver caminhos de rede)
- Python 3.9+ apenas para rodar a partir do código-fonte ou gerar o `.exe` — quem só for **usar** o `.exe` já empacotado não precisa de Python instalado
- Biblioteca padrão (`tkinter`, `sqlite3`, `ctypes`, `csv`, `json`, `os`, `sys`,
  `zipfile`, `xml.etree`, `calendar`) para tudo, **exceto** a aba "Gerar
  Frequência": gerar o PDF da frequência precisa de `reportlab` (e, por
  consequência, `Pillow`) — a única dependência externa do projeto.

```powershell
pip install reportlab
```

## Como executar a partir do código-fonte

```powershell
python freqcontrol.py
```

## Como gerar o executável (.exe) com PyInstaller

1. Instale o PyInstaller e o reportlab uma única vez (precisa de internet):

```powershell
pip install pyinstaller reportlab
```

2. Na pasta do projeto, gere o executável único (o `--add-data` inclui o
   brasão usado no cabeçalho do PDF de frequência):

```powershell
pyinstaller --onefile --windowed --name FreqControl --add-data "assets/brasao_para.png;assets" freqcontrol.py
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
- O `.exe` fica maior (~20 MB em vez de ~11 MB) por causa do reportlab/Pillow
  — ainda assim não precisa de nada instalado no computador de destino.

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

### Aba "Gerar Frequência"

Gera o PDF da folha de frequência em branco (pronta pra imprimir e
distribuir), a partir de uma **planilha externa do RH** (`.ods`, mantida por
outra pessoa, fora do FreqControl) — o programa só lê essa planilha a cada
geração, nunca importa nem duplica esses dados no banco do FreqControl.

1. Na primeira vez, clique em **Recarregar Planilha** e selecione o arquivo
   `.ods` (o caminho fica salvo; para trocar depois, use
   **Arquivo → Configurar planilha de dados do RH (.ods)...**). Da próxima
   vez que o programa abrir, a planilha já carrega sozinha — **Recarregar
   Planilha** só é necessário se o arquivo for atualizado enquanto o
   programa já está aberto. Se o carregamento automático falhar (rede fora
   do ar, por exemplo), aparece um aviso no lugar do "planilha carregada",
   com o botão disponível pra tentar de novo.
2. Escolha **Mês**, **Ano** e o **Setor (lotação)** — a lista de setores vem
   direto da coluna `LOTAÇÃO` da planilha (não dos setores cadastrados no
   FreqControl), então aparece exatamente como está escrito lá, inclusive
   variações/erros de digitação da própria planilha.
3. Escolha o modo, logo abaixo dos filtros:
   - **Frequência por Setor** (padrão): gera um único PDF com um bloco por
     funcionário de todo o setor escolhido — igual ao comportamento de
     sempre.
   - **Frequência Individual**: mostra um terceiro campo, **Funcionário**
     (lista só quem está naquele setor, na própria planilha), e gera um PDF
     com o bloco só daquela pessoa. O nome do arquivo sugerido inclui o
     nome do funcionário, ex: `Frequencia_ASCOM_FULANO_DE_TAL_ABRIL_2026.pdf`.
4. Clique em **Gerar PDF...**. A tabela de dias traz os sábados e domingos
   já calculados e marcados corretamente pelo calendário real, nunca por um
   padrão fixo. Feriados de data certa também são marcados, como
   `FERIADO - <NOME>`: nacionais fixos (Confraternização Universal,
   Tiradentes, Dia do Trabalho, Independência, Nossa Senhora Aparecida,
   Finados, Proclamação da República, Natal, e o Dia Nacional de Zumbi e da
   Consciência Negra a partir de 2024), a Sexta-feira Santa (móvel,
   calculada a partir da Páscoa daquele ano) e os feriados estadual do
   Pará (Adesão do Grão-Pará) e municipal de Belém (Aniversário de
   Belém). **Pontos facultativos** (Carnaval, Corpus Christi, Recírio,
   Dia do Servidor Público etc.) não entram, pois são decretados ano a
   ano sem data fixa. Se um feriado cair num sábado ou domingo, a célula
   continua mostrando só "SÁBADO"/"DOMINGO" (sem duplicar o aviso).
5. Se alguma matrícula da planilha tiver cara de corrompida (um número
   decimal longo, tipo `2952891.5`, efeito colateral do Excel/Calc — não o
   valor real), o programa avisa antes de gerar e deixa você cancelar pra
   corrigir na planilha primeiro, em vez de imprimir uma matrícula errada.

### Janela "Gerenciar Funcionários" (menu Arquivo → Gerenciar Funcionários...)

Marca quem está ativo ou inativo — usado pra esconder quem já não trabalha
mais das consultas do ano corrente, sem apagar nada do histórico.

- **Buscar** (por nome) e **Status** (Todos/Ativos/Inativos) filtram a lista.
  Acima da dica no rodapé, um resumo mostra quantos aparecem no filtro atual,
  ex: `3 funcionários — 1 ativo, 2 inativos`.
- **Alternar Ativo/Inativo**: selecione um funcionário na lista e clique no
  botão (ou dê duplo clique na linha) para trocar o status.
- **Atualizar pela Planilha de Dados...**: lê a **mesma planilha externa do
  RH (`.ods`)** já usada na aba "Gerar Frequência", com a mesma lógica de
  leitura de lá: uma aba por setor, `GERAL` ignorada, `CEDIDOS` (sem coluna
  LOTAÇÃO própria) tratada como lotação fixa `"CEDIDOS"`, linhas sem nome ou
  sem lotação puladas. Se já existe uma planilha configurada, mostra o
  caminho completo e pergunta **Continuar** (usa esse arquivo) ou **Escolher
  outro arquivo...** (abre o seletor, troca o arquivo configurado daqui pra
  frente — mesmo efeito de usar o menu **Arquivo → Configurar planilha de
  dados do RH (.ods)...**); se ainda não tem nenhuma planilha configurada,
  abre o seletor de arquivo direto. Quem está ativo no banco mas não aparece
  na planilha vira candidato a **inativar**; quem está inativo no banco e
  aparece na planilha vira candidato a **reativar**. Nada é aplicado na hora
  — abre a mesma **tela de revisão** com os candidatos já pré-marcados
  (desmarque o que não quiser aplicar) e só grava no banco depois de clicar
  em **Confirmar**. Comparação pelo nome, tolerante a acento/maiúsculas (não
  usa matrícula). Essa tela nunca cria funcionário ou setor novo — só ajusta
  o status de quem já foi catalogado.
- **Exportar CSV**: gera uma relação (`Nome;Setor`) só dos funcionários
  **ativos** — serve de conferência ou backup de quem está ativo no momento.

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
