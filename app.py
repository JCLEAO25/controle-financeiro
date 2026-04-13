import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client

# ===== CONFIG =====
SUPABASE_URL = "https://uwzbdixrynlpqogohokp.supabase.co"
SUPABASE_KEY = "sb_publishable_pS1f-faF8q2wrrkkAi6VyA_fv4mmWS7"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Controle Financeiro", layout="centered")

MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===== LOGIN =====
if "user" not in st.session_state:
    st.title("🔐 Login")

    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Entrar"):
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            if res.user:
                st.session_state["user"] = res.user
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

# ===== CARREGAR DADOS =====
res = supabase.table("movimentacoes") \
    .select("*") \
    .eq("user_id", st.session_state["user"].id) \
    .execute()

df = pd.DataFrame(res.data)

if df.empty:
    df = pd.DataFrame(columns=["data","tipo","categoria","descricao","valor","mes","ano"])

df["data"] = pd.to_datetime(df["data"], errors="coerce")

# ===== HEADER =====
st.markdown("<h2 style='text-align:center;'>💰 Controle Financeiro</h2>", unsafe_allow_html=True)

# ===== FILTRO =====
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

# ===== CALCULOS =====
ganhos = df_mes[df_mes["tipo"] == "Ganho"]["valor"].sum()
gastos = df_mes[df_mes["tipo"] == "Gasto"]["valor"].sum()
saldo = ganhos - gastos

# ===== CARD =====
st.markdown(f"""
<div style="background: linear-gradient(135deg,#1e1e2f,#3a3a5f);
padding:20px;border-radius:15px;color:white;text-align:center;margin-bottom:15px;">
<h3>Saldo</h3>
<h1>{formatar_moeda(saldo)}</h1>
<p>Entrada: {formatar_moeda(ganhos)}<br>Gastos: {formatar_moeda(gastos)}</p>
</div>
""", unsafe_allow_html=True)

# ===== BOTÕES =====
if "show_ganho" not in st.session_state:
    st.session_state.show_ganho = False
if "show_gasto" not in st.session_state:
    st.session_state.show_gasto = False

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Ganho", use_container_width=True):
        st.session_state.show_ganho = True
        st.session_state.show_gasto = False

with col2:
    if st.button("➕ Gasto", use_container_width=True):
        st.session_state.show_gasto = True
        st.session_state.show_ganho = False

# ===== FORM GANHO =====
if st.session_state.show_ganho:
    with st.form("form_ganho", clear_on_submit=True):
        data = st.date_input("Data", value=date.today())
        categoria = st.selectbox("Categoria", ["SALARIO","VALE"])
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)

        if st.form_submit_button("Salvar"):
            supabase.table("movimentacoes").insert({
                "user_id": st.session_state["user"].id,
                "data": str(data),
                "tipo": "Ganho",
                "categoria": categoria,
                "descricao": descricao,
                "valor": valor,
                "mes": MESES_PT[data.month],
                "ano": data.year
            }).execute()

            st.session_state.show_ganho = False
            st.rerun()

# ===== FORM GASTO =====
if st.session_state.show_gasto:
    with st.form("form_gasto", clear_on_submit=True):
        data = st.date_input("Data", value=date.today())
        categoria = st.selectbox("Categoria", [
            "CARTAO DE CREDITO","ALIMENTAÇÃO","LAZER","VEICULO","DESPESAS FIXAS","OUTROS"
        ])
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)

        if st.form_submit_button("Salvar"):
            supabase.table("movimentacoes").insert({
                "user_id": st.session_state["user"].id,
                "data": str(data),
                "tipo": "Gasto",
                "categoria": categoria,
                "descricao": descricao,
                "valor": valor,
                "mes": MESES_PT[data.month],
                "ano": data.year
            }).execute()

            st.session_state.show_gasto = False
            st.rerun()

# ===== HISTÓRICO =====
st.divider()

with st.expander("📊 Histórico"):
    df_sorted = df_mes.sort_values(["data"], ascending=False)

    for _, row in df_sorted.iterrows():

        cor = "green" if row["tipo"] == "Ganho" else "red"
        data_formatada = row["data"].strftime("%d/%m/%Y") if pd.notnull(row["data"]) else "-"

        st.markdown(f"""
        <div style="padding:10px;border-radius:10px;background:#f5f5f7;margin-bottom:8px;">
            <b>{row['categoria']}</b> {row['descricao']}<br>
            <span style="color:{cor};font-weight:bold;">
                {formatar_moeda(row['valor'])}
            </span><br>
            <small>{data_formatada}</small>
        </div>
        """, unsafe_allow_html=True)