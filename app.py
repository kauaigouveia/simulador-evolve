from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from datetime import datetime
import os
import webbrowser

# --- Configurações ---
app = Flask(__name__)
app.secret_key = "segredo_super_forte"

# Banco de dados SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///simulador.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Caminho da planilha
ARQUIVO_FATORES = os.path.join(os.path.dirname(__file__), "fatores.xlsx")

# Cor primária
COR_PRIMARIA = "#2c3e50"

# --- Carregar fatores ---
try:
    dfs = pd.read_excel(ARQUIVO_FATORES, sheet_name=None)
    for k in dfs:
        # Converter coluna de datas para datetime
        df = dfs[k]
        col_data = df.columns[0]  # Assume primeira coluna
        df['Data Base'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        dfs[k] = df
except Exception as e:
    print("Erro ao carregar fatores:", e)
    dfs = {}

# --- Modelos de usuário ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# --- Rotas ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["username"] = username
            return redirect(url_for("simulador"))
        else:
            return render_template("login.html", erro="Usuário ou senha incorretos", cor_primaria=COR_PRIMARIA)
    return render_template("login.html", cor_primaria=COR_PRIMARIA)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/simulador", methods=["GET", "POST"])
def simulador():
    if "username" not in session:
        return redirect(url_for("login"))

    resultados = []
    erro = None
    prazos = ["12", "24", "36", "48", "60", "72", "84", "96"]

    if request.method == "POST":
        banco = request.form.get("banco")
        parcela = request.form.get("parcela")
        data_base = request.form.get("data_base")
        prazo = request.form.get("prazo")

        # Valida campos
        if not banco or not parcela or not data_base or not prazo:
            erro = "Preencha todos os campos."
        else:
            try:
                parcela = float(parcela.replace(",", "."))
                data_base_dt = datetime.strptime(data_base, "%d/%m/%Y")
                # Buscar fator
                if banco in dfs:
                    df = dfs[banco]
                    row = df[df["Data Base"].dt.date == data_base_dt.date()]
                    col_prazo = f"{prazo}x"
                    if row.empty or col_prazo not in row.columns:
                        resultados.append({"Banco": banco, "Status": "FATOR NÃO ENCONTRADO"})
                    else:
                        fator = pd.to_numeric(row[col_prazo].values[0], errors='coerce')
                        if pd.isna(fator):
                            resultados.append({"Banco": banco, "Status": "FATOR NÃO ENCONTRADO"})
                        else:
                            valor = parcela / fator
                            resultados.append({"Banco": banco, "Status": "OK", "Parcela": parcela,
                                               "Prazo": f"{prazo}x", "Valor Calculado": round(valor,2)})
                else:
                    resultados.append({"Banco": banco, "Status": "BANCO NÃO ENCONTRADO"})
            except Exception as e:
                erro = f"Erro no cálculo: {e}"

    return render_template("simulador.html",
                           username=session["username"],
                           resultados=resultados,
                           prazos=prazos,
                           erro=erro,
                           cor_primaria=COR_PRIMARIA)

# --- Executar ---
if __name__ == "__main__":
    # Se rodando localmente, abre o navegador
    if os.environ.get("RENDER") is None:
        webbrowser.open("http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
