from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from datetime import datetime
from models import db, User
import os

app = Flask(__name__)
app.secret_key = "segredo_super_forte"

# Configuração do banco SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///simulador.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Carregar fatores
ARQUIVO_FATORES = os.path.join(os.path.dirname(__file__), "fatores.xlsx")

# Cor primária
COR_PRIMARIA = "#2c3e50"

# --- Funções ---
def calcula_idade(data_nascimento_str):
    try:
        nascimento = datetime.strptime(data_nascimento_str, "%d/%m/%Y")
        hoje = datetime.now()
        idade = hoje.year - nascimento.year
        if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
            idade -= 1
        return idade
    except:
        return None

# --- Rotas ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        user = User.query.filter_by(username=usuario).first()
        if user and user.check_password(senha):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("simulador"))
        else:
            return render_template("login.html", erro="Usuário ou senha inválidos")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/simulador", methods=["GET", "POST"])
def simulador():
    if "user_id" not in session:
        return redirect(url_for("login"))

    resultados = []
    erro = None

    # Carregar todas as abas do Excel
    try:
        raw = pd.read_excel(ARQUIVO_FATORES, sheet_name=None)
        dfs = {}
        for sheet_name, df in raw.items():
            df2 = df.copy()
            col_data = df2.columns[0]
            df2['Data Base'] = pd.to_datetime(df2[col_data], dayfirst=True, errors='coerce')
            prazo_map = {}
            for c in df2.columns:
                s = str(c).strip().lower().replace(" ","")
                if s.endswith("x") and s[:-1].isdigit():
                    prazo_map[s] = c
            for key, orig in prazo_map.items():
                df2[key] = pd.to_numeric(df2[orig], errors='coerce')
            dfs[sheet_name.strip()] = df2
    except Exception as e:
        erro = f"Erro ao ler Excel: {e}"
        dfs = {}

    if request.method == "POST":
        try:
            parcela = float(request.form.get("parcela").replace(",", "."))
            data_base = datetime.strptime(request.form.get("data_base"), "%d/%m/%Y")
            prazo_text = request.form.get("prazo")
            prazo_escolhido = int(prazo_text.replace("x", ""))
            data_nasc = request.form.get("data_nascimento")
            idade_cliente = calcula_idade(data_nasc)
        except Exception as e:
            erro = f"Preencha todos os campos corretamente: {e}"
        else:
            # Simulação simples: percorre abas
            for banco, df in dfs.items():
                row = df[df["Data Base"].dt.date == data_base.date()]
                col_prazo = f"{prazo_escolhido}x"
                if row.empty or col_prazo not in row.columns:
                    resultados.append([banco, "Fator não encontrado", "-", "-", "-", "-"])
                else:
                    fator = pd.to_numeric(row[col_prazo].values[0], errors='coerce')
                    if pd.isna(fator):
                        resultados.append([banco, "Fator não encontrado", "-", "-", "-", "-"])
                    else:
                        valor_sem_seguro = parcela / fator
                        resultados.append([banco, "OK", f"{parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                           f"{prazo_escolhido}x",
                                           f"{valor_sem_seguro:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                           "-"])
    return render_template("simulador.html", username=session.get("username"), resultados=resultados, erro=erro, cor_primaria=COR_PRIMARIA)
