import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

st.set_page_config(page_title="Controle Financeiro", layout="centered")

arquivo = "dados.csv"

MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===== LOAD =====
if os.path.exists(arquivo):
    df = pd.read_csv(arquivo)
else:
    df = pd.DataFrame(columns=["ID","Data","Tipo","Categoria","Descricao","Valor","Mes","Ano"])
    df.to_csv(arquivo, index=False)

df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# ===== HEADER =====
st.markdown("<h2 style='text-align:center;'>💰 Controle Financeiro</h2>", unsafe_allow_html=True)

# ===== FILTRO =====
col1, col2 = st.columns(2)

with col1:
    meses = list(MESES_PT.values())
    mes = st.selectbox("Mês", meses, index=datetime.now().month - 1)

with col2:
    anos = sorted(df["Ano"].dropna().unique())
    ano = st.selectbox("Ano", anos, index=len(anos)-1 if len(anos)>0 else 0)

df_mes = df[(df["Mes"] == mes) & (df["Ano"] == ano)]

# ===== CALCULOS =====
ganhos = df_mes[df_mes["Tipo"] == "Ganho"]["Valor"].sum()
gastos = df_mes[df_mes["Tipo"] == "Gasto"]["Valor"].sum()
saldo = ganhos - gastos

# ===== CARD PRINCIPAL (SALDO + RESUMO JUNTO) =====
st.markdown(f"""
<div style="background: linear-gradient(135deg,#1e1e2f,#3a3a5f);
padding:20px;border-radius:15px;color:white;text-align:center;margin-bottom:15px;">
<h3>Saldo</h3>
<h1>{formatar_moeda(saldo)}</h1>
<p style="margin-top:10px;">
Entrada: {formatar_moeda(ganhos)} <br>
Gastos: {formatar_moeda(gastos)}
</p>
</div>
""", unsafe_allow_html=True)

# ===== CONTROLE DE ESTADO =====
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
        st.subheader("💰 Novo Ganho")
        data = st.date_input("Data", value=date.today())
        categoria = st.selectbox("Categoria", ["SALARIO","VALE"])
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)

        col1, col2 = st.columns(2)

        with col1:
            salvar = st.form_submit_button("Salvar")

        with col2:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            novo_id = int(df["ID"].max()) + 1 if len(df) > 0 else 1

            df = pd.concat([df, pd.DataFrame([{
                "ID": novo_id,
                "Data": pd.to_datetime(data),
                "Tipo": "Ganho",
                "Categoria": categoria,
                "Descricao": descricao,
                "Valor": valor,
                "Mes": MESES_PT[data.month],
                "Ano": data.year
            }])], ignore_index=True)

            df.to_csv(arquivo, index=False)
            st.session_state.show_ganho = False
            st.rerun()

        if cancelar:
            st.session_state.show_ganho = False
            st.rerun()

# ===== FORM GASTO =====
if st.session_state.show_gasto:
    with st.form("form_gasto", clear_on_submit=True):
        st.subheader("💸 Novo Gasto")
        data = st.date_input("Data", value=date.today())
        categoria = st.selectbox("Categoria", [
            "CARTAO DE CREDITO","ALIMENTAÇÃO","LAZER","VEICULO","DESPESAS FIXAS","OUTROS"
        ])
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)

        col1, col2 = st.columns(2)

        with col1:
            salvar = st.form_submit_button("Salvar")

        with col2:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            novo_id = int(df["ID"].max()) + 1 if len(df) > 0 else 1

            df = pd.concat([df, pd.DataFrame([{
                "ID": novo_id,
                "Data": pd.to_datetime(data),
                "Tipo": "Gasto",
                "Categoria": categoria,
                "Descricao": descricao,
                "Valor": valor,
                "Mes": MESES_PT[data.month],
                "Ano": data.year
            }])], ignore_index=True)

            df.to_csv(arquivo, index=False)
            st.session_state.show_gasto = False
            st.rerun()

        if cancelar:
            st.session_state.show_gasto = False
            st.rerun()

# ===== HISTÓRICO (OPCIONAL: RECOLHIDO) =====
st.divider()

with st.expander("📊 Histórico"):
    df_sorted = df_mes.sort_values(["Data"], ascending=False)

    for _, row in df_sorted.iterrows():

        cor = "green" if row["Tipo"] == "Ganho" else "red"
        descricao = row["Descricao"] if pd.notnull(row["Descricao"]) else ""
        data_formatada = row["Data"].strftime("%d/%m/%Y") if pd.notnull(row["Data"]) else "-"

        st.markdown(f"""
        <div style="padding:10px;border-radius:10px;background:#f5f5f7;margin-bottom:8px;">
            <b>{row['Categoria']}</b> {descricao}<br>
            <span style="color:{cor};font-weight:bold;">
                {formatar_moeda(row['Valor'])}
            </span><br>
            <small>{data_formatada}</small>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✏️", key=f"edit_{row['ID']}"):
                st.session_state["edit_id"] = row["ID"]

        with col2:
            if st.button("🗑️", key=f"del_{row['ID']}"):
                df = df[df["ID"] != row["ID"]]
                df.to_csv(arquivo, index=False)
                st.rerun()