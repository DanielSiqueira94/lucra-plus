import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# -----------------------------
# CONFIGURAÇÃO DO APP
# -----------------------------
st.set_page_config(
    page_title="Lucra+ | Controle de Margem e Lucro",
    page_icon="💰",
    layout="wide"
)

# ----------------------------
# BLOQUEIO POR SENHA
# ----------------------------
senha_correta = "lucra12345"
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    senha = st.text_input("🔒 Digite a senha para acessar o app:", type="password")
    if senha == senha_correta:
        st.session_state.autenticado = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta. Tente novamente.")
    st.stop()

# ----------------------------
# FUNÇÃO DE CÁLCULO
# ----------------------------
def calcular_resultados(df_input, margem_desejada, custos_fixos, incluir_fixos=False):
    df = df_input.copy()
    df = df.rename(columns={
        "Taxa_pct": "Taxa (%)",
        "OutrosCustos": "Outros Custos (R$)"
    })

    for col in ["Taxa (%)", "Outros Custos (R$)"]:
        if col not in df.columns:
            df[col] = 0.0

    df["Custo"] = pd.to_numeric(df["Custo"], errors="coerce").fillna(0.0)
    df["Preco"] = pd.to_numeric(df["Preco"], errors="coerce").fillna(0.0)
    df["Taxa (%)"] = pd.to_numeric(df["Taxa (%)"], errors="coerce").fillna(0.0)
    df["Outros Custos (R$)"] = pd.to_numeric(df["Outros Custos (R$)"], errors="coerce").fillna(0.0)

    t = df["Taxa (%)"] / 100
    m = margem_desejada / 100

    df["Taxa (R$)"] = df["Preco"] * t
    df["Lucro Líquido (R$)"] = df["Preco"] - df["Custo"] - df["Taxa (R$)"] - df["Outros Custos (R$)"]
    df["Margem Atual (%)"] = np.where(df["Preco"] != 0, (df["Lucro Líquido (R$)"] / df["Preco"]) * 100, 0)
    df["Margem Desejada (%)"] = margem_desejada
    df["Preço Ideal (R$)"] = np.where(1 - t - m > 0, (df["Custo"] + df["Outros Custos (R$)"]) / (1 - t - m), np.nan)
    df["Diferença Preço Ideal (%)"] = np.where(df["Preco"] != 0, ((df["Preço Ideal (R$)"] - df["Preco"]) / df["Preco"]) * 100, np.nan)
    df["Ponto de Equilíbrio (unid)"] = np.where(df["Lucro Líquido (R$)"] > 0, custos_fixos / df["Lucro Líquido (R$)"], np.nan)

    if incluir_fixos:
        total_receita = df["Preco"].sum()
        if total_receita == 0:
            df["Custo Fixo Rateado (R$)"] = custos_fixos / max(len(df), 1)
        else:
            df["Custo Fixo Rateado (R$)"] = (df["Preco"] / total_receita) * custos_fixos

        df["Lucro Líquido (com fixos) (R$)"] = df["Lucro Líquido (R$)"] - df["Custo Fixo Rateado (R$)"]
        df["Margem Líquida (%)"] = np.where(
            df["Preco"] != 0,
            (df["Lucro Líquido (com fixos) (R$)"] / df["Preco"]) * 100,
            0
        )
        df["Preço Ideal c/ Fixos (R$)"] = np.where(
            1 - t - m > 0,
            (df["Custo"] + df["Outros Custos (R$)"] + df["Custo Fixo Rateado (R$)"]) / (1 - t - m),
            np.nan
        )
        df["Diferença Preço Ideal c/ Fixos (%)"] = np.where(
            df["Preco"] != 0,
            ((df["Preço Ideal c/ Fixos (R$)"] - df["Preco"]) / df["Preco"]) * 100,
            np.nan
        )

    return df.round(2)

# ----------------------------
# EXPORTAÇÃO
# ----------------------------
def exportar_excel(df_sem, df_com=None):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_sem.to_excel(writer, index=False, sheet_name="Resultados_Sem_Fixos")
        if df_com is not None:
            df_com.to_excel(writer, index=False, sheet_name="Resultados_Com_Fixos")
    return buffer.getvalue()

# ----------------------------
# MODELO EXCEL
# ----------------------------
def gerar_modelo_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Modelo Lucra+"
    ws.append(["Produto", "Custo", "Preco", "Taxa (%)", "Outros Custos (R$)"])
    ws.append(["Camiseta Azul", 25.0, 50.0, 2.5, 0.0])
    ws.append(["Caneca Logo", 18.0, 35.0, 3.0, 0.0])
    ws.append(["Bolo Pequeno", 12.0, 30.0, 5.0, 1.5])
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
    for col in ws.columns:
        max_len = max(len(str(c.value)) for c in col if c.value)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

# ----------------------------
# SIDEBAR CONFIG
# ----------------------------
st.sidebar.title("⚙️ Configurações")
margem_desejada = st.sidebar.number_input("Margem desejada (%)", 0.0, 99.0, 30.0)
custos_fixos = st.sidebar.number_input("Custos fixos mensais (R$)", 0.0, 1_000_000.0, 0.0, step=100.0)
incluir_fixos = st.sidebar.checkbox("Incluir custos fixos nos cálculos unitários", value=False)
menu = st.sidebar.radio("📋 Navegação", ["📥 Importar / Adicionar", "📊 Resultados", "💾 Exportar", "ℹ️ Sobre"])

# ----------------------------
# RESULTADOS
# ----------------------------
if menu == "📊 Resultados":
    st.title("📊 Resultados e análises")

    if "dados" not in st.session_state or st.session_state.dados.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        df_base = st.session_state.dados
        df_sem = calcular_resultados(df_base, margem_desejada, custos_fixos, incluir_fixos=False)
        df_com = calcular_resultados(df_base, margem_desejada, custos_fixos, incluir_fixos=True)
        df_full = df_com if incluir_fixos else df_sem

        lucro_col = "Lucro Líquido (com fixos) (R$)" if incluir_fixos and "Lucro Líquido (com fixos) (R$)" in df_full.columns else "Lucro Líquido (R$)"
        margem_col = "Margem Líquida (%)" if incluir_fixos and "Margem Líquida (%)" in df_full.columns else "Margem Atual (%)"

        ph1, ph2, ph3 = st.columns(3)
        place_lucro = ph1.empty()
        place_margem = ph2.empty()
        place_prod = ph3.empty()

        st.markdown("### 🔍 Filtrar produtos")
        filtro_produto = st.multiselect(
            "Selecione produtos para análise:",
            options=df_full["Produto"].unique(),
            default=[]
        )

        if filtro_produto:
            df = df_full[df_full["Produto"].isin(filtro_produto)]
            st.success(f"Filtro ativo: {', '.join(filtro_produto)}")
        else:
            df = df_full.copy()

        lucro_total = pd.to_numeric(df[lucro_col], errors="coerce").sum(min_count=1)
        margem_media = pd.to_numeric(df[margem_col], errors="coerce").mean()
        total_produtos = len(df)

        place_lucro.metric("💰 Lucro Total", f"R$ {0.0 if pd.isna(lucro_total) else lucro_total:.2f}")
        place_margem.metric("📉 Margem Média", f"{0.0 if pd.isna(margem_media) else margem_media:.2f}%")
        place_prod.metric("📦 Produtos", total_produtos)

        st.markdown("---")
        st.markdown("### 📋 Tabela de produtos")

        st.data_editor(
            df,
            use_container_width=True,
            height=420,
            hide_index=True,
            key="tabela_produtos",
            column_config={
                "Produto": st.column_config.TextColumn("Produto", required=True),
                "Preco": st.column_config.NumberColumn("Preço (R$)", format="%.2f"),
                "Custo": st.column_config.NumberColumn("Custo (R$)", format="%.2f"),
            },
        )

        st.markdown("---")
        st.markdown("### 📈 Gráfico de Margem por Produto")

        if df.empty:
            st.warning("Nenhum produto disponível para o gráfico.")
        else:
            fig, ax = plt.subplots(figsize=(8, max(3, 0.25 * len(df))))
            ax.barh(
                df["Produto"],
                df[margem_col],
                color=["green" if x >= margem_desejada else "red" for x in df[margem_col]]
            )
            ax.set_xlabel(margem_col)
            ax.set_ylabel("Produto")
            ax.grid(axis="x", linestyle="--", alpha=0.5)
            st.pyplot(fig)

# ----------------------------
# IMPORTAR / ADICIONAR
# ----------------------------
elif menu == "📥 Importar / Adicionar":
    st.title("📥 Importar produtos ou adicionar manualmente")
    col1, col2 = st.columns(2)
    with col1:
        arquivo = st.file_uploader("Selecione o arquivo Excel (.xlsx ou .xls)", type=["xlsx", "xls"])
        if arquivo:
            df = pd.read_excel(arquivo)
            st.session_state.dados = pd.concat([st.session_state.get("dados", pd.DataFrame()), df], ignore_index=True)
            st.success(f"{len(df)} produtos importados com sucesso!")
        modelo_excel = gerar_modelo_excel()
        st.download_button("📘 Baixar modelo Excel (.xlsx)", modelo_excel, "Modelo_Lucra_Plus.xlsx")
    with col2:
        st.subheader("📝 Adicionar Produto Manualmente")
        with st.form("novo_produto", clear_on_submit=True):
            nome = st.text_input("Produto")
            custo = st.number_input("Custo (R$)", 0.0)
            preco = st.number_input("Preço (R$)", 0.0)
            taxa = st.number_input("Taxa (%)", 0.0)
            outros = st.number_input("Outros custos (R$)", 0.0)
            add = st.form_submit_button("Adicionar ➕")
            if add and nome:
                novo = pd.DataFrame([{"Produto": nome, "Custo": custo, "Preco": preco, "Taxa (%)": taxa, "Outros Custos (R$)": outros}])
                st.session_state.dados = pd.concat([st.session_state.get("dados", pd.DataFrame()), novo], ignore_index=True)
                st.success(f"Produto '{nome}' adicionado.")

# ----------------------------
# EXPORTAR
# ----------------------------
elif menu == "💾 Exportar":
    st.title("💾 Exportar resultados")
    if "dados" not in st.session_state or st.session_state.dados.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        df_sem = calcular_resultados(st.session_state.dados, margem_desejada, custos_fixos, incluir_fixos=False)
        df_com = calcular_resultados(st.session_state.dados, margem_desejada, custos_fixos, incluir_fixos=True)
        excel = exportar_excel(df_sem, df_com)
        st.success("✅ Arquivo Excel gerado com abas de comparação.")
        st.download_button("📊 Baixar Excel (.xlsx)", excel, f"Lucra_Resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

# ----------------------------
# SOBRE
# ----------------------------
# ----------------------------
# SOBRE
# ----------------------------
elif menu == "ℹ️ Sobre":
    st.title("💰 Sobre o Lucra+")

    st.markdown("""
    ### 💼 **Lucra+ v0.21**
    O **Lucra+** é uma aplicação desenvolvida para ajudar **empreendedores e gestores** 
    a entender e otimizar a **margem de lucro dos seus produtos**, com base em custos,
    taxas e metas de rentabilidade.

    ---
    #### ⚙️ **Como o Lucra+ funciona**
    1. Você importa ou cadastra seus produtos com preço, custo e taxas.  
    2. O sistema calcula automaticamente:
       - Lucro líquido (com e sem custos fixos)  
       - Margem atual e ideal  
       - Preço ideal para atingir a margem desejada  
       - Ponto de equilíbrio  
    3. Você visualiza os resultados em tabelas, gráficos e indicadores dinâmicos.

    ---
    #### 🚀 **Principais recursos**
    - Upload de planilhas Excel (.xlsx / .xls)  
    - Adição manual de produtos  
    - Cálculos automáticos de lucro e margem  
    - Filtro de produtos com atualização imediata  
    - Exportação dos resultados para Excel  
    - Gráfico visual de desempenho por produto  

    ---
    #### 🧩 **Tecnologias utilizadas**
    - [Streamlit](https://streamlit.io) – Interface interativa e responsiva  
    - [Pandas](https://pandas.pydata.org) – Processamento de dados  
    - [Matplotlib](https://matplotlib.org) – Geração de gráficos  
    - [OpenPyXL](https://openpyxl.readthedocs.io) – Criação e leitura de planilhas Excel  

    ---
    #### 💬 **Agradecimento**
    Este projeto foi criado com o objetivo de **tornar o controle de margens simples e acessível**.  
    Caso tenha sugestões de melhorias ou novas funcionalidades, fique à vontade para compartilhar!

    ---
    🏷️ **Versão:** 0.21  
    📅 **Última atualização:** Novembro/2025  
    """)



