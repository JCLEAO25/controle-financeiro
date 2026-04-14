import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client

# ===== PDF =====
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ===== COOKIE =====
from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(page_title="Controle Financeiro", layout="centered")

# ===== ICONES =====
st.markdown("""
<link rel="apple-touch-icon" href="https://raw.githubusercontent.com/JCLEAO25/controle-financeiro/main/static/icon-512.png">
<link rel="icon" type="image/png" href="https://raw.githubusercontent.com/JCLEAO25/controle-financeiro/main/static/icon-192.png">
""", unsafe_allow_html=True)

# ===== SUPABASE =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== COOKIE INIT =====
cookies = EncryptedCookieManager(
    prefix="finance_app",
    password="finance_app_2026_secure"
)

if not cookies.ready():
    st.stop()

# ===== MESES =====
MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===== PDF =====
def gerar_pdf_estilizado(df, mes, ano, ganhos, gastos, saldo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("<b>💰 Controle Financeiro</b>", styles['Title']))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(f"<b>Mês:</b> {mes}/{ano}", styles['Normal']))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph(f"<b>Entrada:</b> R$ {ganhos:,.2f}", styles['Normal']))
    elementos.append(Paragraph(f"<b>Gastos:</b> R$ {gastos:,.2f}", styles['Normal']))
    elementos.append(Paragraph(f"<b>Saldo:</b> R$ {saldo:,.2f}", styles['Normal']))
    elementos.append(Spacer(1, 15))

    dados = [["Data", "Tipo", "Categoria", "Descrição", "Valor"]]

    for _, row in df.iterrows():
        dados.append([
            row["data"].strftime("%d/%m/%Y") if pd.notnull(row["data"]) else "",
            row["tipo"],
            row["categoria"],
            row["descricao"],
            f"R$ {row['valor']:,.2f}"
        ])

    tabela = Table(dados)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3a3a5f")),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ===== LOGIN PERSISTENTE =====
if "user" not in st.session_state:

    iif cookies.get("user_id") and not st.session_state.get("logout"):
        st.session_state["user"] = {"id": cookies.get("user_id")}
    else:
        st.title("🔐 Login")

        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Entrar"):
                if email and senha:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": senha
                    })
                    if res.user:
                        st.session_state["user"] = {"id": res.user.id}
                        cookies["user_id"] = res.user.id
                        cookies.save()
                        st.rerun()
                    else:
                        st.error("Erro no login")

        with col2:
            if st.button("Criar conta"):
                supabase.auth.sign_up({
                    "email": email,
                    "password": senha
                })
                st.success("Conta criada!")

        st.stop()

# ===== LOGOUT =====
if st.button("🚪 Sair"):

    # marca logout
    st.session_state["logout"] = True

    # remove cookie
    if "user_id" in cookies:
        del cookies["user_id"]

    cookies.save()

    # remove user
    if "user" in st.session_state:
        del st.session_state["user"]

    st.rerun()

# ===== DADOS =====
res = supabase.table("movimentacoes") \
    .select("*") \
    .eq("user_id", st.session_state["user"]["id"]) \
    .execute()

df = pd.DataFrame(res.data)

if df.empty:
    df = pd.DataFrame(columns=["id","data","tipo","categoria","descricao","valor","mes","ano"])

df["data"] = pd.to_datetime(df["data"], errors="coerce")

# ===== UI =====
st.markdown("<h2 style='text-align:center;'>💰 Controle Financeiro</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    meses = list(MESES_PT.values())
    mes = st.selectbox("Mês", meses, index=datetime.now().month - 1)

with col2:
    anos = sorted(df["ano"].dropna().unique())
    if len(anos) == 0:
        anos = [datetime.now().year]
    ano = st.selectbox("Ano", anos)

df_mes = df[(df["mes"] == mes) & (df["ano"] == ano)]

ganhos = df_mes[df_mes["tipo"] == "Ganho"]["valor"].sum()
gastos = df_mes[df_mes["tipo"] == "Gasto"]["valor"].sum()
saldo = ganhos - gastos

st.markdown(f"""
<div style="background: linear-gradient(135deg,#1e1e2f,#3a3a5f);
padding:20px;border-radius:15px;color:white;text-align:center;margin-bottom:15px;">
<h3>Saldo</h3>
<h1>{formatar_moeda(saldo)}</h1>
<p>Entrada: {formatar_moeda(ganhos)}<br>Gastos: {formatar_moeda(gastos)}</p>
</div>
""", unsafe_allow_html=True)

# ===== PDF =====
pdf_file = gerar_pdf_estilizado(df_mes, mes, ano, ganhos, gastos, saldo)

st.download_button(
    label="📄 Exportar PDF Premium",
    data=pdf_file,
    file_name=f"resumo_{mes}_{ano}.pdf",
    mime="application/pdf"
)