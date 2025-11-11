import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# ----------------------------
# CONFIGURAÇÃO DO APP
# ----------------------------
st.set_page_config(
    page_title="Lucra+ | Controle de Margem e Lucro",
    page_icon="💰",
    layout="wide"
)

# ----------------------------
# BLOQUEIO POR SENHA
# ----------------------------
senha_correta = "lucra1235"

senha = st.text_input("Digite a senha para acessar o app:", type="password")

if senha != senha_correta:
    st.error("Acesso restrito. App temporariamente em manutenção.")
    st.stop()

# ----------------------------
# FUNÇÕES DE CÁLCULO
# ----------------------------
def calcular_resultados(df, margem_desejada, custos_fixos):
    df = df.copy()
    for col in ["Taxa_pct", "OutrosCustos"]:
        if col not in df.columns:
            df[col] = 0.0

    df["Custo"] = pd.to_numeric(df["Custo"], errors="coerce").fillna(0)
    df["Preco"] = pd.to_numeric(df["Preco"], errors="coerce").fillna(0)
    df["Taxa_pct"] = pd.to_numeric(df["Taxa_pct"], errors="coerce").fillna(0)
    df["OutrosCustos"] = pd.to_numeric(df["OutrosCustos"], errors="coerce").fillna(0)

    df["Taxa_R$"] = (df["Preco"] * df["Taxa_pct"]) / 100
    df["Lucro_Líquido (R$)"] = df["Preco"] - df["Custo"] - df["Taxa_R$"] - df["OutrosCustos"]
    df["Margem (%)"] = (df["Lucro_Líquido (R$)"] / df["Preco"]).replace([float("inf"), -float("inf")], 0).fillna(0) * 100

    m = margem_desejada / 100
    df["Preço Ideal (R$)"] = (df["Custo"] + df["OutrosCustos"]) / (1 - m) if (1 - m) > 0 else df["Preco"]

    df["Ponto de Equilíbrio (unid)"] = df.apply(
        lambda r: custos_fixos / r["Lucro_Líquido (R$)"] if r["Lucro_Líquido (R$)"] > 0 else None, axis=1
    )

    df = df.round(2)
    return df


def exportar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Lucra+ Resultados")
    return buffer.getvalue()


# ----------------------------
# FUNÇÃO PARA GERAR MODELO EXCEL
# ----------------------------
def gerar_modelo_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Modelo Lucra+"

    # Cabeçalhos
    ws.append(["Produto", "Custo", "Preco", "Taxa_pct", "OutrosCustos"])
    ws.append(["Camiseta Azul", 25.0, 50.0, 2.5, 0.0])
    ws.append(["Caneca Logo", 18.0, 35.0, 3.0, 0.0])
    ws.append(["Bolo Pequeno", 12.0, 30.0, 5.0, 1.5])

    # Estilo do cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    # Ajuste automático da largura das colunas
    for col in ws.columns:
        max_len = max(len(str(cell.value)) for cell in col if cell.value)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

# ----------------------------
# ESTADO DE SESSÃO
# ----------------------------
if "dados" not in st.session_state:
    st.session_state.dados = pd.DataFrame(columns=["Produto", "Custo", "Preco", "Taxa_pct", "OutrosCustos"])

# ----------------------------
# SIDEBAR - CONFIGURAÇÕES
# ----------------------------
st.sidebar.title("⚙️ Configurações")
margem_desejada = st.sidebar.number_input("Margem desejada (%)", 0.0, 99.0, 30.0, step=1.0)
custos_fixos = st.sidebar.number_input("Custos fixos mensais (R$)", 0.0, 100000.0, 0.0, step=100.0)
st.sidebar.markdown("---")

menu = st.sidebar.radio("📋 Navegação", ["📥 Importar / Adicionar", "📊 Resultados", "💾 Exportar", "ℹ️ Sobre"])

# ----------------------------
# PÁGINA: IMPORTAR / ADICIONAR
# ----------------------------
if menu == "📥 Importar / Adicionar":
    st.title("📥 Importar produtos ou adicionar manualmente")

    col1, col2 = st.columns(2)

    # UPLOAD DE PLANILHA
    with col1:
        st.subheader("⬆️ Upload de Planilha Excel")
        st.caption("Use colunas: Produto, Custo, Preco, Taxa_pct, OutrosCustos")

        arquivo = st.file_uploader("Selecione o arquivo Excel (.xlsx ou .xls)", type=["xlsx", "xls"])
        if arquivo:
            try:
                df = pd.read_excel(arquivo)
                colunas_necessarias = ["Produto", "Custo", "Preco"]
                faltando = [c for c in colunas_necessarias if c not in df.columns]
                if faltando:
                    st.error(f"❌ Colunas faltando: {', '.join(faltando)}. Use o modelo padrão para garantir compatibilidade.")
                else:
                    st.session_state.dados = pd.concat([st.session_state.dados, df], ignore_index=True)
                    st.success(f"✅ {len(df)} produtos importados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

        modelo_excel = gerar_modelo_excel()
        st.download_button(
            "📘 Baixar modelo Excel (.xlsx)",
            data=modelo_excel,
            file_name="Modelo_Lucra_Plus.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ADIÇÃO MANUAL DE PRODUTOS
    with col2:
        st.subheader("📝 Adicionar Produto Manualmente")
        with st.form("novo_produto", clear_on_submit=True):
            nome = st.text_input("Produto")
            custo = st.number_input("Custo (R$)", min_value=0.0, step=0.5)
            preco = st.number_input("Preço (R$)", min_value=0.0, step=0.5)
            taxa = st.number_input("Taxa (%)", min_value=0.0, step=0.5)
            outros = st.number_input("Outros custos (R$)", min_value=0.0, step=0.5)
            add = st.form_submit_button("Adicionar ➕")

            if add and nome:
                novo = pd.DataFrame([{
                    "Produto": nome,
                    "Custo": custo,
                    "Preco": preco,
                    "Taxa_pct": taxa,
                    "OutrosCustos": outros
                }])
                st.session_state.dados = pd.concat([st.session_state.dados, novo], ignore_index=True)
                st.success(f"Produto '{nome}' adicionado.")

    if not st.session_state.dados.empty:
        st.markdown("---")
        st.subheader("📋 Produtos cadastrados")
        st.dataframe(st.session_state.dados, use_container_width=True)

    if st.button("🗑️ Limpar todos os produtos"):
        st.session_state.dados = pd.DataFrame(columns=["Produto", "Custo", "Preco", "Taxa_pct", "OutrosCustos"])
        st.warning("Todos os produtos foram apagados da sessão.")

# ----------------------------
# PÁGINA: RESULTADOS
# ----------------------------
elif menu == "📊 Resultados":
    st.title("📊 Resultados e análises")
    if st.session_state.dados.empty:
        st.info("Nenhum produto cadastrado. Adicione ou importe primeiro.")
    else:
        df = calcular_resultados(st.session_state.dados, margem_desejada, custos_fixos)

        lucro_total = df["Lucro_Líquido (R$)"].sum()
        margem_media = df["Margem (%)"].mean()
        produtos_negativos = (df["Lucro_Líquido (R$)"] < 0).sum()
        total_produtos = len(df)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🧾 Produtos", total_produtos)
        col2.metric("📉 Margem Média", f"{margem_media:.2f}%")
        col3.metric("🚨 Lucro Negativo", produtos_negativos)
        col4.metric("💰 Lucro Total", f"R$ {lucro_total:.2f}")

        st.markdown("---")
        st.subheader("📈 Detalhamento por produto")
        st.dataframe(df, use_container_width=True)

        st.markdown("### Gráfico: Margem por Produto")
        fig, ax = plt.subplots(figsize=(8, max(3, 0.25 * len(df))))
        ax.barh(df["Produto"], df["Margem (%)"])
        ax.set_xlabel("Margem (%)")
        ax.set_ylabel("Produto")
        ax.grid(axis="x", linestyle="--", alpha=0.5)
        st.pyplot(fig)

# ----------------------------
# PÁGINA: EXPORTAR
# ----------------------------
elif menu == "💾 Exportar":
    st.title("💾 Exportar resultados")
    if st.session_state.dados.empty:
        st.info("Nenhum produto disponível para exportação.")
    else:
        df = calcular_resultados(st.session_state.dados, margem_desejada, custos_fixos)
        excel_data = exportar_excel(df)

        st.success("✅ Resultados prontos para exportação.")
        st.download_button(
            "📊 Baixar Excel (.xlsx)",
            data=excel_data,
            file_name=f"Lucra_Resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

# ----------------------------
# PÁGINA: SOBRE
# ----------------------------
elif menu == "ℹ️ Sobre":
    st.title("ℹ️ Sobre o Lucra+")
    st.markdown("""
    **Lucra+** é um app criado para ajudar pequenos empreendedores e autônomos a **descobrir se estão realmente lucrando**.

    ### 💡 Funcionalidades:
    - Cálculo automático de margem, lucro e preço ideal  
    - Inserção manual ou importação via planilha  
    - Relatórios e gráficos intuitivos  
    - Exportação de resultados  

    ### 🚀 Próximos passos:
    - Login e histórico de usuários  
    - Planos Free / Pro com Stripe  
    - Recomendação inteligente de precificação  
    """)

    st.caption("Versão 0.6 — by Daniel Siqueira, 2025")
