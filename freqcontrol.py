"""FreqControl - Catalogação e consulta de PDFs de frequência de funcionários.

O programa apenas cataloga (grava o caminho) e consulta PDFs de frequência já
organizados manualmente pelo usuário na estrutura:

    <Pasta raiz>/<Setor>/<Funcionário>/<Ano>/<Mês>.pdf

Ele nunca move, copia, renomeia ou apaga nenhum arquivo PDF.
"""

import csv
import ctypes
import json
import os
import sqlite3
import sys
import tkinter as tk
import unicodedata
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

APP_NOME = "FreqControl"
NOME_BANCO = "freqcontrol.db"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NOME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

COR_OK = "#dff0d8"
COR_FALTA = "#f2dede"

ERROR_MORE_DATA = 234
UNIVERSAL_NAME_INFO_LEVEL = 1


def normalizar_texto(texto):
    """Remove acentos e normaliza caixa, para comparar nomes de mês/pasta
    com tolerância a variações (ex: 'Março' e 'Marco' devem casar)."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return texto.strip().lower()


MESES_POR_NOME_NORMALIZADO = {
    normalizar_texto(nome_mes): numero for numero, nome_mes in enumerate(MESES, start=1)
}


# ---------------------------------------------------------------------------
# Resolução de caminho de rede (UNC)
# ---------------------------------------------------------------------------

def resolver_caminho_unc(caminho):
    """Resolve um caminho (inclusive letra de unidade mapeada) para o caminho
    de rede completo (UNC), usando a API do Windows WNetGetUniversalName.

    Se não for possível resolver (caminho local não mapeado, erro de API,
    plataforma diferente de Windows, etc.), retorna o caminho original sem
    quebrar o programa.
    """
    if not caminho:
        return caminho
    caminho = os.path.abspath(caminho)
    if sys.platform != "win32":
        return caminho
    try:
        mpr = ctypes.WinDLL("mpr")
        buffer = ctypes.create_unicode_buffer(1024)
        tamanho = ctypes.c_ulong(ctypes.sizeof(buffer))
        ret = mpr.WNetGetUniversalNameW(
            ctypes.c_wchar_p(caminho),
            ctypes.c_ulong(UNIVERSAL_NAME_INFO_LEVEL),
            buffer,
            ctypes.byref(tamanho),
        )
        if ret == ERROR_MORE_DATA:
            novo_tamanho_chars = (tamanho.value // ctypes.sizeof(ctypes.c_wchar)) + 1
            buffer = ctypes.create_unicode_buffer(novo_tamanho_chars)
            tamanho = ctypes.c_ulong(ctypes.sizeof(buffer))
            ret = mpr.WNetGetUniversalNameW(
                ctypes.c_wchar_p(caminho),
                ctypes.c_ulong(UNIVERSAL_NAME_INFO_LEVEL),
                buffer,
                ctypes.byref(tamanho),
            )
        if ret == 0:
            # A struct UNIVERSAL_NAME_INFOW começa com um único campo
            # LPWSTR lpUniversalName, que aponta para dentro do próprio buffer.
            ponteiro = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_wchar_p))
            nome_universal = ponteiro.contents.value
            if nome_universal:
                return nome_universal
        return caminho
    except Exception:
        return caminho


# ---------------------------------------------------------------------------
# Configuração local (aponta para o banco de dados compartilhado no servidor)
# ---------------------------------------------------------------------------

def carregar_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(config, arquivo, ensure_ascii=False, indent=2)


def escolher_pasta_banco(janela_pai):
    """Pede ao usuário a pasta compartilhada do RH e retorna o caminho UNC
    completo do arquivo de banco de dados dentro dela (ou None se cancelado)."""
    pasta = filedialog.askdirectory(
        title="Selecione a pasta compartilhada do banco de dados (RH)",
        parent=janela_pai,
    )
    if not pasta:
        return None
    pasta_unc = resolver_caminho_unc(pasta)
    return os.path.join(pasta_unc, NOME_BANCO)


def obter_caminho_banco(janela_pai):
    config = carregar_config()
    caminho_db = config.get("db_path")
    if caminho_db and os.path.isdir(os.path.dirname(caminho_db)):
        return caminho_db

    messagebox.showinfo(
        APP_NOME,
        "Selecione a pasta compartilhada do RH onde o banco de dados do "
        "FreqControl deve ficar (ou já está). Essa mesma pasta deve ser "
        "usada por todos os usuários do programa.",
        parent=janela_pai,
    )
    while True:
        caminho_db = escolher_pasta_banco(janela_pai)
        if caminho_db is None:
            continuar = messagebox.askretrycancel(
                APP_NOME,
                "É necessário selecionar uma pasta para continuar. Tentar novamente?",
                parent=janela_pai,
            )
            if continuar:
                continue
            sys.exit(0)
        config["db_path"] = caminho_db
        salvar_config(config)
        return caminho_db


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

class Banco:
    def __init__(self, caminho_db):
        self.caminho_db = caminho_db
        self.conn = sqlite3.connect(caminho_db)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._criar_esquema()

    def _criar_esquema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS setores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE COLLATE NOCASE
            );
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL COLLATE NOCASE,
                setor_id INTEGER NOT NULL,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE,
                UNIQUE(nome, setor_id)
            );
            CREATE TABLE IF NOT EXISTS frequencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                funcionario_id INTEGER NOT NULL,
                mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                ano INTEGER NOT NULL,
                caminho_arquivo TEXT NOT NULL,
                data_cadastro TEXT NOT NULL,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE CASCADE,
                UNIQUE(funcionario_id, mes, ano)
            );
            """
        )
        self.conn.commit()

    # ---- Setores ----
    def listar_setores(self):
        cur = self.conn.execute("SELECT id, nome FROM setores ORDER BY nome COLLATE NOCASE")
        return cur.fetchall()

    def obter_ou_criar_setor(self, nome):
        nome = nome.strip()
        cur = self.conn.execute("SELECT id FROM setores WHERE nome = ? COLLATE NOCASE", (nome,))
        linha = cur.fetchone()
        if linha:
            return linha["id"]
        cur = self.conn.execute("INSERT INTO setores (nome) VALUES (?)", (nome,))
        self.conn.commit()
        return cur.lastrowid

    def excluir_setor(self, setor_id):
        self.conn.execute("DELETE FROM setores WHERE id = ?", (setor_id,))
        self.conn.commit()

    # ---- Funcionários ----
    def listar_funcionarios(self, setor_id=None):
        if setor_id is None:
            cur = self.conn.execute(
                """
                SELECT f.id, f.nome, f.setor_id, s.nome AS setor_nome
                FROM funcionarios f JOIN setores s ON f.setor_id = s.id
                ORDER BY s.nome COLLATE NOCASE, f.nome COLLATE NOCASE
                """
            )
        else:
            cur = self.conn.execute(
                """
                SELECT f.id, f.nome, f.setor_id, s.nome AS setor_nome
                FROM funcionarios f JOIN setores s ON f.setor_id = s.id
                WHERE f.setor_id = ?
                ORDER BY f.nome COLLATE NOCASE
                """,
                (setor_id,),
            )
        return cur.fetchall()

    def obter_ou_criar_funcionario(self, nome, setor_id):
        nome = nome.strip()
        cur = self.conn.execute(
            "SELECT id FROM funcionarios WHERE nome = ? COLLATE NOCASE AND setor_id = ?",
            (nome, setor_id),
        )
        linha = cur.fetchone()
        if linha:
            return linha["id"]
        cur = self.conn.execute(
            "INSERT INTO funcionarios (nome, setor_id) VALUES (?, ?)", (nome, setor_id)
        )
        self.conn.commit()
        return cur.lastrowid

    def excluir_funcionario(self, funcionario_id):
        self.conn.execute("DELETE FROM funcionarios WHERE id = ?", (funcionario_id,))
        self.conn.commit()

    # ---- Frequências ----
    def obter_frequencia(self, funcionario_id, mes, ano):
        cur = self.conn.execute(
            "SELECT * FROM frequencias WHERE funcionario_id = ? AND mes = ? AND ano = ?",
            (funcionario_id, mes, ano),
        )
        return cur.fetchone()

    def salvar_frequencia(self, funcionario_id, mes, ano, caminho_arquivo):
        existente = self.obter_frequencia(funcionario_id, mes, ano)
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existente:
            self.conn.execute(
                "UPDATE frequencias SET caminho_arquivo = ?, data_cadastro = ? WHERE id = ?",
                (caminho_arquivo, agora, existente["id"]),
            )
        else:
            self.conn.execute(
                "INSERT INTO frequencias (funcionario_id, mes, ano, caminho_arquivo, data_cadastro) "
                "VALUES (?, ?, ?, ?, ?)",
                (funcionario_id, mes, ano, caminho_arquivo, agora),
            )
        self.conn.commit()

    def listar_todos_caminhos(self):
        cur = self.conn.execute("SELECT caminho_arquivo FROM frequencias")
        return {linha["caminho_arquivo"] for linha in cur.fetchall()}

    def status_mes(self, mes, ano):
        cur = self.conn.execute(
            """
            SELECT s.nome AS setor_nome, f.id AS funcionario_id, f.nome AS funcionario_nome,
                   fr.caminho_arquivo AS caminho
            FROM funcionarios f
            JOIN setores s ON f.setor_id = s.id
            LEFT JOIN frequencias fr ON fr.funcionario_id = f.id AND fr.mes = ? AND fr.ano = ?
            ORDER BY s.nome COLLATE NOCASE, f.nome COLLATE NOCASE
            """,
            (mes, ano),
        )
        return cur.fetchall()

    def status_ano(self, funcionario_id, ano):
        cur = self.conn.execute(
            "SELECT mes, caminho_arquivo FROM frequencias WHERE funcionario_id = ? AND ano = ?",
            (funcionario_id, ano),
        )
        return {linha["mes"]: linha["caminho_arquivo"] for linha in cur.fetchall()}

    def fechar(self):
        self.conn.close()


def buscar_setor_por_nome(banco, nome):
    nome = (nome or "").strip().lower()
    for setor in banco.listar_setores():
        if setor["nome"].lower() == nome:
            return setor
    return None


def buscar_funcionario_por_nome(banco, setor_id, nome):
    nome = (nome or "").strip().lower()
    for funcionario in banco.listar_funcionarios(setor_id):
        if funcionario["nome"].lower() == nome:
            return funcionario
    return None


def abrir_pdf(caminho, janela_pai=None):
    try:
        os.startfile(caminho)  # noqa: S606 - abertura no visualizador padrão do Windows
    except Exception as erro:
        messagebox.showerror(
            APP_NOME, f"Não foi possível abrir o arquivo:\n{caminho}\n\n{erro}", parent=janela_pai
        )


# ---------------------------------------------------------------------------
# Aba 1: Catalogar PDFs
# ---------------------------------------------------------------------------

class AbaCatalogar(ttk.Frame):
    def __init__(self, master, banco, app):
        super().__init__(master)
        self.banco = banco
        self.app = app
        self.pasta_raiz = None
        self.arquivos_pendentes = []
        self.indice_atual = None
        self._construir_interface()

    def _construir_interface(self):
        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(topo, text="Selecionar Pasta Raiz...", command=self._selecionar_pasta).pack(side=tk.LEFT)
        self.botao_cadastrar_todos = ttk.Button(
            topo,
            text="Cadastrar Todos os Pendentes (usa nome das pastas)...",
            command=self._cadastrar_todos_pendentes,
            state=tk.DISABLED,
        )
        self.botao_cadastrar_todos.pack(side=tk.LEFT, padx=(10, 0))
        self.label_pasta = ttk.Label(topo, text="Nenhuma pasta selecionada.")
        self.label_pasta.pack(side=tk.LEFT, padx=10)

        corpo = ttk.Frame(self)
        corpo.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        frame_lista = ttk.Frame(corpo)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL)
        self.lista = tk.Listbox(
            frame_lista, yscrollcommand=barra.set, exportselection=False, font=("Segoe UI", 9)
        )
        barra.config(command=self.lista.yview)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.lista.bind("<<ListboxSelect>>", self._ao_selecionar)

        frame_direita = ttk.Frame(corpo, width=320)
        frame_direita.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        frame_direita.pack_propagate(False)

        self.label_arquivo = ttk.Label(frame_direita, text="Nenhum arquivo selecionado.", wraplength=300)
        self.label_arquivo.pack(anchor=tk.W, pady=(0, 6))

        self.botao_abrir = ttk.Button(
            frame_direita, text="Abrir PDF para Conferência", command=self._abrir_pdf, state=tk.DISABLED
        )
        self.botao_abrir.pack(fill=tk.X, pady=(0, 12))

        ttk.Separator(frame_direita, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_direita, text="Setor:").pack(anchor=tk.W)
        self.combo_setor = ttk.Combobox(frame_direita)
        self.combo_setor.pack(fill=tk.X, pady=(0, 8))
        self.combo_setor.bind("<<ComboboxSelected>>", self._ao_mudar_setor)
        self.combo_setor.bind("<FocusOut>", self._ao_mudar_setor)

        ttk.Label(frame_direita, text="Funcionário:").pack(anchor=tk.W)
        self.combo_funcionario = ttk.Combobox(frame_direita)
        self.combo_funcionario.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame_direita, text="Mês:").pack(anchor=tk.W)
        self.combo_mes = ttk.Combobox(frame_direita, values=MESES, state="readonly")
        self.combo_mes.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame_direita, text="Ano:").pack(anchor=tk.W)
        self.entrada_ano = ttk.Entry(frame_direita)
        self.entrada_ano.insert(0, str(datetime.now().year))
        self.entrada_ano.pack(fill=tk.X, pady=(0, 12))

        self.botao_salvar = ttk.Button(frame_direita, text="Salvar", command=self._salvar, state=tk.DISABLED)
        self.botao_salvar.pack(fill=tk.X, pady=(0, 6))
        self.botao_pular = ttk.Button(frame_direita, text="Pular", command=self._pular, state=tk.DISABLED)
        self.botao_pular.pack(fill=tk.X)

    def atualizar_setores(self):
        self.combo_setor["values"] = [s["nome"] for s in self.banco.listar_setores()]

    def _selecionar_pasta(self):
        pasta = filedialog.askdirectory(
            title="Selecione a pasta raiz (Setor/Funcionário/Ano/Mês.pdf)"
        )
        if not pasta:
            return
        self.pasta_raiz = resolver_caminho_unc(pasta)
        self._carregar_pendentes()

    def _carregar_pendentes(self):
        self.lista.delete(0, tk.END)
        self.arquivos_pendentes = []
        cadastrados = self.banco.listar_todos_caminhos()
        for raiz, _dirs, arquivos in os.walk(self.pasta_raiz):
            for nome_arq in arquivos:
                if not nome_arq.lower().endswith(".pdf"):
                    continue
                caminho_completo = os.path.join(raiz, nome_arq)
                caminho_resolvido = resolver_caminho_unc(caminho_completo)
                if caminho_resolvido in cadastrados:
                    continue
                caminho_relativo = os.path.relpath(caminho_completo, self.pasta_raiz)
                self.arquivos_pendentes.append(
                    {"caminho": caminho_resolvido, "relativo": caminho_relativo}
                )
        self.arquivos_pendentes.sort(key=lambda item: item["relativo"].lower())
        for item in self.arquivos_pendentes:
            self.lista.insert(tk.END, item["relativo"])
        self.label_pasta.config(
            text=f"Pasta: {self.pasta_raiz}   |   {len(self.arquivos_pendentes)} arquivo(s) pendente(s)"
        )
        self.indice_atual = None
        self._ao_selecionar()
        self._atualizar_estado_botao_lote()

    def _atualizar_estado_botao_lote(self):
        estado = tk.NORMAL if self.arquivos_pendentes else tk.DISABLED
        self.botao_cadastrar_todos.config(state=estado)

    def _ao_selecionar(self, event=None):
        selecao = self.lista.curselection()
        if not selecao:
            self.indice_atual = None
            self.label_arquivo.config(text="Nenhum arquivo selecionado.")
            self.botao_abrir.config(state=tk.DISABLED)
            self.botao_salvar.config(state=tk.DISABLED)
            self.botao_pular.config(state=tk.DISABLED)
            return
        self.indice_atual = selecao[0]
        item = self.arquivos_pendentes[self.indice_atual]
        self.label_arquivo.config(text=f"Arquivo:\n{item['relativo']}")
        self.botao_abrir.config(state=tk.NORMAL)
        self.botao_salvar.config(state=tk.NORMAL)
        self.botao_pular.config(state=tk.NORMAL)

    def _abrir_pdf(self):
        if self.indice_atual is None:
            return
        abrir_pdf(self.arquivos_pendentes[self.indice_atual]["caminho"], self)

    def _ao_mudar_setor(self, event=None):
        setor = buscar_setor_por_nome(self.banco, self.combo_setor.get())
        if setor:
            funcionarios = self.banco.listar_funcionarios(setor["id"])
            self.combo_funcionario["values"] = [f["nome"] for f in funcionarios]
        else:
            self.combo_funcionario["values"] = []

    def _salvar(self):
        if self.indice_atual is None:
            return

        nome_setor = self.combo_setor.get().strip()
        nome_funcionario = self.combo_funcionario.get().strip()
        mes_nome = self.combo_mes.get().strip()
        ano_texto = self.entrada_ano.get().strip()

        if not nome_setor or not nome_funcionario or not mes_nome or not ano_texto:
            messagebox.showwarning(
                APP_NOME, "Preencha Setor, Funcionário, Mês e Ano antes de salvar.", parent=self
            )
            return
        if mes_nome not in MESES:
            messagebox.showwarning(APP_NOME, "Mês inválido.", parent=self)
            return
        try:
            ano = int(ano_texto)
            if ano < 2000 or ano > 2100:
                raise ValueError
        except ValueError:
            messagebox.showwarning(APP_NOME, "Ano inválido.", parent=self)
            return
        mes = MESES.index(mes_nome) + 1

        item = self.arquivos_pendentes[self.indice_atual]

        setor_id = self.banco.obter_ou_criar_setor(nome_setor)
        funcionario_id = self.banco.obter_ou_criar_funcionario(nome_funcionario, setor_id)

        existente = self.banco.obter_frequencia(funcionario_id, mes, ano)
        if existente:
            substituir = messagebox.askyesno(
                APP_NOME,
                f"Já existe uma frequência entregue para {nome_funcionario} em "
                f"{mes_nome}/{ano}:\n{existente['caminho_arquivo']}\n\n"
                "Deseja substituir o registro? (o arquivo original em disco NÃO será apagado)",
                parent=self,
            )
            if not substituir:
                return

        self.banco.salvar_frequencia(funcionario_id, mes, ano, item["caminho"])
        self._remover_pendente(self.indice_atual)
        self.app.atualizar_todas_abas()

    def _pular(self):
        if self.indice_atual is None:
            return
        total = len(self.arquivos_pendentes)
        proximo = self.indice_atual + 1
        if proximo >= total:
            proximo = 0
        self.lista.selection_clear(0, tk.END)
        self.lista.selection_set(proximo)
        self.lista.see(proximo)
        self._ao_selecionar()

    def _remover_pendente(self, indice):
        del self.arquivos_pendentes[indice]
        self.lista.delete(indice)
        total = len(self.arquivos_pendentes)
        if total:
            proximo = min(indice, total - 1)
            self.lista.selection_set(proximo)
            self.lista.see(proximo)
        self._ao_selecionar()
        self.label_pasta.config(
            text=f"Pasta: {self.pasta_raiz}   |   {total} arquivo(s) pendente(s)"
        )
        self._atualizar_estado_botao_lote()

    def _cadastrar_todos_pendentes(self):
        if not self.arquivos_pendentes:
            messagebox.showinfo(APP_NOME, "Não há arquivos pendentes para cadastrar.", parent=self)
            return

        total = len(self.arquivos_pendentes)
        confirmar = messagebox.askyesno(
            APP_NOME,
            f"Isso vai cadastrar automaticamente os {total} arquivo(s) pendente(s), usando a "
            "estrutura de pastas Setor\\Funcionário\\Ano\\Mês.pdf como referência, SEM "
            "conferência individual de cada PDF.\n\n"
            "Arquivos com estrutura de pasta inesperada, ano inválido ou nome de mês não "
            "reconhecido serão pulados e continuam na lista para cadastro manual depois.\n\n"
            "Deseja continuar?",
            parent=self,
        )
        if not confirmar:
            return

        cadastrados = 0
        ja_existentes = 0
        exemplos_erro = []
        indices_processados = []

        for indice, item in enumerate(self.arquivos_pendentes):
            partes = item["relativo"].split(os.sep)
            if len(partes) != 4:
                exemplos_erro.append(item["relativo"])
                continue
            nome_setor, nome_funcionario, ano_texto, nome_arquivo = partes
            if not ano_texto.isdigit():
                exemplos_erro.append(item["relativo"])
                continue
            nome_mes = os.path.splitext(nome_arquivo)[0]
            mes = MESES_POR_NOME_NORMALIZADO.get(normalizar_texto(nome_mes))
            if mes is None:
                exemplos_erro.append(item["relativo"])
                continue

            ano = int(ano_texto)
            setor_id = self.banco.obter_ou_criar_setor(nome_setor)
            funcionario_id = self.banco.obter_ou_criar_funcionario(nome_funcionario, setor_id)

            if self.banco.obter_frequencia(funcionario_id, mes, ano):
                ja_existentes += 1
                indices_processados.append(indice)
                continue

            self.banco.salvar_frequencia(funcionario_id, mes, ano, item["caminho"])
            cadastrados += 1
            indices_processados.append(indice)

        for indice in sorted(indices_processados, reverse=True):
            del self.arquivos_pendentes[indice]
            self.lista.delete(indice)

        self.indice_atual = None
        self._ao_selecionar()
        self.label_pasta.config(
            text=f"Pasta: {self.pasta_raiz}   |   {len(self.arquivos_pendentes)} arquivo(s) pendente(s)"
        )
        self._atualizar_estado_botao_lote()
        self.app.atualizar_todas_abas()

        resumo = (
            f"{cadastrados} arquivo(s) cadastrado(s).\n"
            f"{ja_existentes} já estavam cadastrados (ignorados).\n"
            f"{len(exemplos_erro)} arquivo(s) com estrutura de pasta/mês não reconhecida "
            "(continuam na lista para cadastro manual)."
        )
        if exemplos_erro:
            amostra = "\n".join(exemplos_erro[:10])
            if len(exemplos_erro) > 10:
                amostra += f"\n... e mais {len(exemplos_erro) - 10}."
            resumo += f"\n\nExemplos não reconhecidos:\n{amostra}"
        messagebox.showinfo(APP_NOME, resumo, parent=self)


# ---------------------------------------------------------------------------
# Aba 2: Consultar por mês
# ---------------------------------------------------------------------------

class AbaConsultaMes(ttk.Frame):
    def __init__(self, master, banco, app):
        super().__init__(master)
        self.banco = banco
        self.app = app
        self._resultado_atual = []
        self._mes_consultado = ""
        self._ano_consultado = ""
        self._construir_interface()

    def _construir_interface(self):
        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(topo, text="Mês:").pack(side=tk.LEFT)
        self.combo_mes = ttk.Combobox(topo, values=MESES, state="readonly", width=12)
        self.combo_mes.current(datetime.now().month - 1)
        self.combo_mes.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(topo, text="Ano:").pack(side=tk.LEFT)
        self.entrada_ano = ttk.Entry(topo, width=8)
        self.entrada_ano.insert(0, str(datetime.now().year))
        self.entrada_ano.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(topo, text="Consultar", command=self._consultar).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(topo, text="Exportar CSV", command=self._exportar_csv).pack(side=tk.LEFT)

        container_tabela = ttk.Frame(self)
        container_tabela.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        self.tree = ttk.Treeview(
            container_tabela,
            columns=("setor", "funcionario", "status", "caminho"),
            displaycolumns=("setor", "funcionario", "status"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("setor", text="Setor")
        self.tree.heading("funcionario", text="Funcionário")
        self.tree.heading("status", text="Status")
        self.tree.column("setor", width=140, anchor=tk.W, stretch=False)
        self.tree.column("funcionario", width=480, anchor=tk.W, stretch=True)
        self.tree.column("status", width=110, anchor=tk.CENTER, stretch=False)
        self.tree.tag_configure("ok", background=COR_OK)
        self.tree.tag_configure("falta", background=COR_FALTA)

        barra_vertical = ttk.Scrollbar(container_tabela, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra_vertical.set)
        barra_vertical.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._ao_dar_duplo_clique)

        self.label_resumo = ttk.Label(self, text="")
        self.label_resumo.pack(anchor=tk.W, padx=8, pady=(0, 8))

    def atualizar_setores(self):
        pass

    def _consultar(self):
        mes_nome = self.combo_mes.get().strip()
        ano_texto = self.entrada_ano.get().strip()
        if mes_nome not in MESES or not ano_texto.isdigit():
            messagebox.showwarning(APP_NOME, "Selecione um mês e informe um ano válido.", parent=self)
            return
        mes = MESES.index(mes_nome) + 1
        ano = int(ano_texto)

        self.tree.delete(*self.tree.get_children())
        linhas = self.banco.status_mes(mes, ano)
        total = len(linhas)
        cadastrados = 0
        self._resultado_atual = []
        for linha in linhas:
            cadastrado = bool(linha["caminho"])
            status = "Entregue" if cadastrado else "Faltando"
            tag = "ok" if cadastrado else "falta"
            if cadastrado:
                cadastrados += 1
            self.tree.insert(
                "", tk.END,
                values=(linha["setor_nome"], linha["funcionario_nome"], status, linha["caminho"] or ""),
                tags=(tag,),
            )
            self._resultado_atual.append((linha["setor_nome"], linha["funcionario_nome"], status))

        faltando = total - cadastrados
        self.label_resumo.config(
            text=f"{cadastrados} de {total} funcionários com frequência entregue em "
                 f"{mes_nome}/{ano}. Faltam: {faltando}."
        )
        self._mes_consultado, self._ano_consultado = mes_nome, ano

    def _ao_dar_duplo_clique(self, event=None):
        selecao = self.tree.selection()
        if not selecao:
            return
        valores = self.tree.item(selecao[0], "values")
        caminho = valores[3]
        if caminho:
            abrir_pdf(caminho, self)
        else:
            messagebox.showinfo(
                APP_NOME, "Não há frequência entregue para este funcionário neste mês.", parent=self
            )

    def _exportar_csv(self):
        if not self._resultado_atual:
            messagebox.showwarning(APP_NOME, "Realize uma consulta antes de exportar.", parent=self)
            return
        caminho = filedialog.asksaveasfilename(
            title="Exportar CSV",
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")],
            initialfile=f"frequencias_{self._mes_consultado}_{self._ano_consultado}.csv",
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow(["Setor", "Funcionário", "Status"])
                escritor.writerows(self._resultado_atual)
            messagebox.showinfo(APP_NOME, "CSV exportado com sucesso.", parent=self)
        except OSError as erro:
            messagebox.showerror(APP_NOME, f"Não foi possível exportar o CSV:\n{erro}", parent=self)


# ---------------------------------------------------------------------------
# Aba 3: Consultar por funcionário
# ---------------------------------------------------------------------------

class AbaConsultaFuncionario(ttk.Frame):
    def __init__(self, master, banco, app):
        super().__init__(master)
        self.banco = banco
        self.app = app
        self._construir_interface()

    def _construir_interface(self):
        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(topo, text="Setor:").pack(side=tk.LEFT)
        self.combo_setor = ttk.Combobox(topo, state="readonly", width=20)
        self.combo_setor.pack(side=tk.LEFT, padx=(4, 12))
        self.combo_setor.bind("<<ComboboxSelected>>", self._ao_mudar_setor)

        ttk.Label(topo, text="Funcionário:").pack(side=tk.LEFT)
        self.combo_funcionario = ttk.Combobox(topo, state="readonly", width=26)
        self.combo_funcionario.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(topo, text="Ano:").pack(side=tk.LEFT)
        self.entrada_ano = ttk.Entry(topo, width=8)
        self.entrada_ano.insert(0, str(datetime.now().year))
        self.entrada_ano.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(topo, text="Consultar", command=self._consultar).pack(side=tk.LEFT)

        self.tree = ttk.Treeview(
            self,
            columns=("mes", "status", "caminho"),
            displaycolumns=("mes", "status"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("mes", text="Mês")
        self.tree.heading("status", text="Status")
        self.tree.column("mes", width=160, anchor=tk.W, stretch=False)
        self.tree.column("status", width=140, anchor=tk.CENTER, stretch=False)
        self.tree.tag_configure("ok", background=COR_OK)
        self.tree.tag_configure("falta", background=COR_FALTA)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        self.tree.bind("<Double-1>", self._ao_dar_duplo_clique)

        ttk.Label(self, text="Dica: dê duplo clique em um mês entregue para abrir o PDF.").pack(
            anchor=tk.W, padx=8, pady=(0, 8)
        )

    def atualizar_setores(self):
        self.combo_setor["values"] = [s["nome"] for s in self.banco.listar_setores()]
        self.combo_funcionario.set("")
        self.combo_funcionario["values"] = []
        self.tree.delete(*self.tree.get_children())

    def _ao_mudar_setor(self, event=None):
        setor = buscar_setor_por_nome(self.banco, self.combo_setor.get())
        if setor:
            funcionarios = self.banco.listar_funcionarios(setor["id"])
            self.combo_funcionario["values"] = [f["nome"] for f in funcionarios]
        else:
            self.combo_funcionario["values"] = []
        self.combo_funcionario.set("")

    def _consultar(self):
        setor = buscar_setor_por_nome(self.banco, self.combo_setor.get())
        if not setor:
            messagebox.showwarning(APP_NOME, "Selecione um setor válido.", parent=self)
            return
        funcionario = buscar_funcionario_por_nome(self.banco, setor["id"], self.combo_funcionario.get())
        if not funcionario:
            messagebox.showwarning(APP_NOME, "Selecione um funcionário válido.", parent=self)
            return
        ano_texto = self.entrada_ano.get().strip()
        if not ano_texto.isdigit():
            messagebox.showwarning(APP_NOME, "Informe um ano válido.", parent=self)
            return
        ano = int(ano_texto)

        mapa = self.banco.status_ano(funcionario["id"], ano)
        self.tree.delete(*self.tree.get_children())
        for numero_mes, nome_mes in enumerate(MESES, start=1):
            caminho = mapa.get(numero_mes)
            status = "Entregue" if caminho else "Faltando"
            tag = "ok" if caminho else "falta"
            self.tree.insert("", tk.END, values=(nome_mes, status, caminho or ""), tags=(tag,))

    def _ao_dar_duplo_clique(self, event=None):
        selecao = self.tree.selection()
        if not selecao:
            return
        valores = self.tree.item(selecao[0], "values")
        caminho = valores[2]
        if caminho:
            abrir_pdf(caminho, self)
        else:
            messagebox.showinfo(APP_NOME, "Não há frequência entregue para este mês.", parent=self)


# ---------------------------------------------------------------------------
# Aba 4: Funcionários e setores
# ---------------------------------------------------------------------------

class AbaGerenciar(ttk.Frame):
    def __init__(self, master, banco, app):
        super().__init__(master)
        self.banco = banco
        self.app = app
        self._construir_interface()

    def _construir_interface(self):
        container_tabela = ttk.Frame(self)
        container_tabela.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(container_tabela, columns=("funcionario", "setor"), show="headings")
        self.tree.heading("funcionario", text="Funcionário")
        self.tree.heading("setor", text="Setor")
        self.tree.column("funcionario", width=480, anchor=tk.W, stretch=True)
        self.tree.column("setor", width=140, anchor=tk.W, stretch=False)

        barra_vertical = ttk.Scrollbar(container_tabela, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra_vertical.set)
        barra_vertical.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        botoes = ttk.Frame(self)
        botoes.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(
            botoes, text="Excluir Funcionário Selecionado", command=self._excluir_funcionario
        ).pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        frame_setor = ttk.Frame(self)
        frame_setor.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(frame_setor, text="Excluir setor inteiro:").pack(side=tk.LEFT)
        self.combo_setor = ttk.Combobox(frame_setor, state="readonly", width=30)
        self.combo_setor.pack(side=tk.LEFT, padx=6)
        ttk.Button(frame_setor, text="Excluir Setor", command=self._excluir_setor).pack(side=tk.LEFT)

    def atualizar(self):
        self.tree.delete(*self.tree.get_children())
        for funcionario in self.banco.listar_funcionarios():
            self.tree.insert(
                "", tk.END, iid=str(funcionario["id"]),
                values=(funcionario["nome"], funcionario["setor_nome"]),
            )
        self.combo_setor["values"] = [s["nome"] for s in self.banco.listar_setores()]

    def _excluir_funcionario(self):
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning(APP_NOME, "Selecione um funcionário na lista.", parent=self)
            return
        funcionario_id = int(selecao[0])
        valores = self.tree.item(selecao[0], "values")
        confirmar = messagebox.askyesno(
            APP_NOME,
            f"Excluir o cadastro de '{valores[0]}' ({valores[1]})?\n\n"
            "Isso remove apenas o cadastro e o histórico de frequências no banco de "
            "dados — os arquivos PDF no servidor NÃO serão apagados.",
            parent=self,
        )
        if not confirmar:
            return
        self.banco.excluir_funcionario(funcionario_id)
        self.app.atualizar_todas_abas()

    def _excluir_setor(self):
        nome_setor = self.combo_setor.get().strip()
        if not nome_setor:
            messagebox.showwarning(APP_NOME, "Selecione um setor.", parent=self)
            return
        setor = buscar_setor_por_nome(self.banco, nome_setor)
        if not setor:
            return
        confirmar = messagebox.askyesno(
            APP_NOME,
            f"Excluir o setor '{nome_setor}' inteiro?\n\n"
            "Isso remove o setor, todos os seus funcionários e o histórico de "
            "frequências cadastrados no banco de dados. Os arquivos PDF no "
            "servidor NÃO serão apagados.",
            parent=self,
        )
        if not confirmar:
            return
        self.banco.excluir_setor(setor["id"])
        self.app.atualizar_todas_abas()


# ---------------------------------------------------------------------------
# Aplicativo principal
# ---------------------------------------------------------------------------

class AplicativoFreqControl:
    def __init__(self, root, banco):
        self.root = root
        self.banco = banco
        root.title(APP_NOME)
        root.geometry("960x600")
        root.minsize(760, 480)

        estilo = ttk.Style()
        for nome_tema in ("vista", "winnative", "clam"):
            try:
                estilo.theme_use(nome_tema)
                break
            except tk.TclError:
                continue

        self._construir_menu()

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.aba_catalogar = AbaCatalogar(notebook, banco, self)
        self.aba_consulta_mes = AbaConsultaMes(notebook, banco, self)
        self.aba_consulta_funcionario = AbaConsultaFuncionario(notebook, banco, self)
        self.aba_gerenciar = AbaGerenciar(notebook, banco, self)

        notebook.add(self.aba_catalogar, text="Catalogar PDFs")
        notebook.add(self.aba_consulta_mes, text="Consultar por Mês")
        notebook.add(self.aba_consulta_funcionario, text="Consultar por Funcionário")
        notebook.add(self.aba_gerenciar, text="Funcionários e Setores")

        self.abas = (
            self.aba_catalogar,
            self.aba_consulta_mes,
            self.aba_consulta_funcionario,
            self.aba_gerenciar,
        )

        self.atualizar_todas_abas()

    def _construir_menu(self):
        barra_menu = tk.Menu(self.root)
        menu_arquivo = tk.Menu(barra_menu, tearoff=0)
        menu_arquivo.add_command(
            label="Alterar pasta do banco de dados...", command=self._alterar_pasta_banco
        )
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", command=self.root.destroy)
        barra_menu.add_cascade(label="Arquivo", menu=menu_arquivo)

        menu_ajuda = tk.Menu(barra_menu, tearoff=0)
        menu_ajuda.add_command(label="Sobre", command=self._mostrar_sobre)
        barra_menu.add_cascade(label="Ajuda", menu=menu_ajuda)

        self.root.config(menu=barra_menu)

    def _mostrar_sobre(self):
        messagebox.showinfo(
            APP_NOME,
            f"{APP_NOME}\n\n"
            "Catalogação e consulta de PDFs de frequência de funcionários.\n"
            f"Banco de dados atual:\n{self.banco.caminho_db}",
            parent=self.root,
        )

    def _alterar_pasta_banco(self):
        caminho_db = escolher_pasta_banco(self.root)
        if not caminho_db:
            return
        try:
            novo_banco = Banco(caminho_db)
        except sqlite3.Error as erro:
            messagebox.showerror(
                APP_NOME, f"Não foi possível abrir o banco em:\n{caminho_db}\n\n{erro}", parent=self.root
            )
            return

        self.banco.fechar()
        self.banco = novo_banco
        for aba in self.abas:
            aba.banco = novo_banco

        config = carregar_config()
        config["db_path"] = caminho_db
        salvar_config(config)

        self.atualizar_todas_abas()
        messagebox.showinfo(APP_NOME, "Pasta do banco de dados alterada com sucesso.", parent=self.root)

    def atualizar_todas_abas(self):
        for aba in self.abas:
            if hasattr(aba, "atualizar_setores"):
                aba.atualizar_setores()
        self.aba_gerenciar.atualizar()


def main():
    root = tk.Tk()
    root.withdraw()

    caminho_db = obter_caminho_banco(root)
    try:
        banco = Banco(caminho_db)
    except sqlite3.Error as erro:
        messagebox.showerror(APP_NOME, f"Não foi possível abrir o banco de dados:\n{erro}", parent=root)
        sys.exit(1)

    root.deiconify()
    app = AplicativoFreqControl(root, banco)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.banco.fechar(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
