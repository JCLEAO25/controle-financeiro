import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client

# ===== PDF =====
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Controle Financeiro", layout="centered")

# ===== ICONES / PWA =====
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="https://raw.githubusercontent.com/JCLEAO25/controle-financeiro/main/static/icon-512.png">
<link rel="icon" type="image/png" href="https://raw.githubusercontent.com/JCLEAO25/controle-financeiro/main/static/icon-192.png">
""", unsafe_allow_html=True)

# ===== SUPABASE =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== MESES =====
MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===== PDF PREMIUM =====
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

# ===== AUTO LOGIN =====
if "user" not in st.session_state:

    session = supabase.auth.get_session()

    if session and session.user:
        st.session_state["user"] = session.user
    else:
        st.title("🔐 Login")

        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Entrar"):
                if email and senha:
                    res = supabase.auth.sign_in_with_password(
                        email=email,
                        password=senha
                    )
                    if res.user:
                        st.session_state["user"] = res.user
                        st.rerun()
                    else:
                        st.error("Erro no login")

        with col2:
            if st.button("Criar conta"):
                supabase.auth.sign_up(
                    email=email,
                    password=senha
                )
                st.success("Conta criada!")

        st.stop()

# ===== LOGOUT =====
if st.button("🚪 Sair"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# ===== CARREGAR DADOS =====
res = supabase.table("movimentacoes") \
    .select("*") \
    .eq("user_id", st.session_state["user"].id) \
    .execute()

df = pd.DataFrame(res.data)

if df.empty:
    df = pd.DataFrame(columns=["id","data","tipo","categoria","descricao","valor","mes","ano"])

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

# ===== EXPORT PDF =====
pdf_file = gerar_pdf_estilizado(df_mes, mes, ano, ganhos, gastos, saldo)

st.download_button(
    label="📄 Exportar PDF Premium",
    data=pdf_file,
    file_name=f"resumo_{mes}_{ano}.pdf",
    mime="application/pdf"
)

# ===== CONTROLE ESTADO =====
if "show_ganho" not in st.session_state:
    st.session_state.show_ganho = False
if "show_gasto" not in st.session_state:
    st.session_state.show_gasto = False

# ===== BOTÕES =====
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

        col1, col2 = st.columns(2)
        salvar = col1.form_submit_button("Salvar")
        cancelar = col2.form_submit_button("❌ Cancelar")

        if salvar:
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

        if cancelar:
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

        col1, col2 = st.columns(2)
        salvar = col1.form_submit_button("Salvar")
        cancelar = col2.form_submit_button("❌ Cancelar")

        if salvar:
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

        if cancelar:
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

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✏️", key=f"edit_{row['id']}"):
                st.session_state["edit_id"] = row["id"]

        with col2:
            if st.button("🗑️", key=f"del_{row['id']}"):
                supabase.table("movimentacoes").delete().eq("id", row["id"]).execute()
                st.rerun()

# ===== EDITAR =====
if "edit_id" in st.session_state:
    linha = df[df["id"] == st.session_state["edit_id"]].iloc[0]

    st.divider()
    st.subheader("✏️ Editar lançamento")

    with st.form("edit_form"):
        data = st.date_input("Data", linha["data"].date())
        tipo = st.selectbox("Tipo", ["Ganho","Gasto"], index=0 if linha["tipo"]=="Ganho" else 1)
        categoria = st.text_input("Categoria", linha["categoria"])
        descricao = st.text_input("Descrição", linha["descricao"])
        valor = st.number_input("Valor", value=float(linha["valor"]))

        if st.form_submit_button("Atualizar"):
            supabase.table("movimentacoes").update({
                "data": str(data),
                "tipo": tipo,
                "categoria": categoria,
                "descricao": descricao,
                "valor": valor,
                "mes": MESES_PT[data.month],
                "ano": data.year
            }).eq("id", linha["id"]).execute()

            del st.session_state["edit_id"]
            st.rerun()