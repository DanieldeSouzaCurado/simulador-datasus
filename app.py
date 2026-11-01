import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulador Farmacoeconômico DataSUS",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. DADOS DO DATASUS EMBUTIDOS DIRETAMENTE NO CÓDIGO-FONTE (HARDCODED)
# -----------------------------------------------------------------------------
# Coeficientes estaduais oficiais consolidados (Proporção de AIHs e APACs por UF no SUS)
PARTICIPACAO_SUS_UF = {
    'SP': 0.224, 'MG': 0.106, 'RJ': 0.082, 'BA': 0.068, 'PR': 0.058,
    'RS': 0.057, 'PE': 0.046, 'CE': 0.042, 'PA': 0.036, 'SC': 0.038,
    'GO': 0.033, 'MA': 0.030, 'PB': 0.019, 'ES': 0.019, 'AM': 0.017,
    'RN': 0.016, 'MT': 0.016, 'PI': 0.016, 'AL': 0.015, 'DF': 0.014,
    'MS': 0.014, 'SE': 0.010, 'RO': 0.008, 'TO': 0.007, 'AC': 0.004,
    'AP': 0.003, 'RR': 0.002
}

# Parâmetros Nacionais Consolidados extraídos do SIH-SUS (AIH) e SIA-SUS (APAC/CEAF/TRS)
PARAMETROS_NACIONAIS_DATASUS = {
    'Diabetes Mellitus': {
        'pac_precoce_br': 2_816_000,          # Acompanhamento UBS / Farmácia Popular
        'pac_tardio_br': 384_000,             # Internações complexas, pé diabético e hemodiálise (TRS)
        'custo_precoce_per_capita': 680.0,
        'custo_sih_per_capita_tardio': 4_850.0,
        'custo_apac_per_capita_tardio': 9_400.0,
        'prop_uti': 0.26,
        'aih_por_pac_tardio': 0.39,
        'media_dias_leito': 6.8
    },
    'Doenças Cardiopulmonares': {
        'pac_precoce_br': 5_525_000,          # Controle ambulatorial HAS, IC inicial, Asma e DPOC
        'pac_tardio_br': 975_000,             # IAM, AVC, IC descompensada, DPOC exacerbada / Oxigenoterapia
        'custo_precoce_per_capita': 720.0,
        'custo_sih_per_capita_tardio': 8_150.0,
        'custo_apac_per_capita_tardio': 2_850.0,
        'prop_uti': 0.36,
        'aih_por_pac_tardio': 0.48,
        'media_dias_leito': 7.4
    },
    'Psoríase': {
        'pac_precoce_br': 387_000,            # Tópicos, fototerapia e metotrexato (Atenção Básica/Especializada)
        'pac_tardio_br': 63_000,              # Psoríase moderada/grave em Imunobiológicos (APAC/CEAF)
        'custo_precoce_per_capita': 940.0,
        'custo_sih_per_capita_tardio': 1_180.0,
        'custo_apac_per_capita_tardio': 24_200.0,
        'prop_uti': 0.05,
        'aih_por_pac_tardio': 0.04,
        'media_dias_leito': 4.5
    },
    'Artrite Psoriásica': {
        'pac_precoce_br': 64_600,             # MMCDs sintéticos (Metotrexato, Leflunomida, Sulfassalazina)
        'pac_tardio_br': 30_400,              # Erosão articular, Imunobiológicos/JAKi (CEAF) e artroplastias
        'custo_precoce_per_capita': 1_650.0,
        'custo_sih_per_capita_tardio': 3_100.0,
        'custo_apac_per_capita_tardio': 30_800.0,
        'prop_uti': 0.08,
        'aih_por_pac_tardio': 0.09,
        'media_dias_leito': 5.8
    }
    'Esclerodermia (Esclerose Sistêmica)': {
        'pac_precoce_br': 8_200,              # Pacientes em manejo precoce no SUS (vasodilatadores / MTX)
        'pac_tardio_br': 5_800,               # Pacientes em estágio tardio no SUS (Fibrose Pulmonar, HAP, úlceras graves)
        'custo_precoce_per_capita': 1_850.0,  # Nifedipina, metotrexato, monitoramento capilaroscópico e função pulmonar
        'custo_sih_per_capita_tardio': 6_400.0,   # Internações por crise renal, infecção de úlceras e descompensação cardiopulmonar
        'custo_apac_per_capita_tardio': 38_500.0, # Bosentana, ambrisentana, iloprosta, micofenolato, rituximabe / antifibróticos
        'prop_uti': 0.32,
        'aih_por_pac_tardio': 0.35,
        'media_dias_leito': 9.2
    }
}

@st.cache_data
def carregar_base_embutida() -> pd.DataFrame:
    """
    Constrói o DataFrame diretamente a partir das constantes embutidas no código-fonte,
    sem depender de leitura de arquivos externos ou botões de upload.
    """
    registros = []
    for uf, peso in PARTICIPACAO_SUS_UF.items():
        for doenca, p in PARAMETROS_NACIONAIS_DATASUS.items():
            pac_precoce = max(1, int(round(p['pac_precoce_br'] * peso)))
            pac_tardio = max(1, int(round(p['pac_tardio_br'] * peso)))

            custo_precoce_tot = pac_precoce * p['custo_precoce_per_capita']
            custo_sih_tot = pac_tardio * p['custo_sih_per_capita_tardio']
            custo_apac_tot = pac_tardio * p['custo_apac_per_capita_tardio']
            custo_uti_tot = custo_sih_tot * p['prop_uti']

            qtd_internacoes = max(1, int(round(pac_tardio * p['aih_por_pac_tardio'])))
            dias_leito = int(round(qtd_internacoes * p['media_dias_leito']))

            registros.append({
                'UF': uf,
                'DOENCA': doenca,
                'PACIENTES_PRECOCE': pac_precoce,
                'PACIENTES_TARDIO': pac_tardio,
                'Precoce_Monitoramento_Basico': round(custo_precoce_tot, 2),
                'CUSTO_HOSPITALAR_TOTAL': round(custo_sih_tot, 2),
                'CUSTO_UTI': round(custo_uti_tot, 2),
                'Tardio_Ambulatorial_Alto_Custo': round(custo_apac_tot, 2),
                'QTD_INTERNACOES': qtd_internacoes,
                'DIAS_LEITO_TOTAIS': dias_leito
            })

    return pd.DataFrame(registros)


# -----------------------------------------------------------------------------
# 3. MOTOR DE CÁLCULO FARMACOECONÔMICO
# -----------------------------------------------------------------------------
def simular_impacto_orcamentario(
    df: pd.DataFrame,
    taxas_conversao: dict,
    fator_defasagem_sih: float,
    horizonte_anos: int
) -> pd.DataFrame:
    df_sim = df.copy()

    df_sim['CUSTO_HOSP_AJUSTADO'] = df_sim['CUSTO_HOSPITALAR_TOTAL'] * fator_defasagem_sih
    df_sim['CUSTO_UTI_AJUSTADO'] = df_sim['CUSTO_UTI'] * fator_defasagem_sih

    df_sim['CUSTO_TARDIO_ANUAL'] = (
        df_sim['CUSTO_HOSP_AJUSTADO'] + df_sim['Tardio_Ambulatorial_Alto_Custo']
    )
    df_sim['CUSTO_ATUAL_ANUAL'] = (
        df_sim['Precoce_Monitoramento_Basico'] + df_sim['CUSTO_TARDIO_ANUAL']
    )

    df_sim['TICKET_PRECOCE'] = (
        df_sim['Precoce_Monitoramento_Basico'] / df_sim['PACIENTES_PRECOCE'].replace(0, 1)
    )
    df_sim['TICKET_TARDIO'] = (
        df_sim['CUSTO_TARDIO_ANUAL'] / df_sim['PACIENTES_TARDIO'].replace(0, 1)
    )

    df_sim['ALPHA'] = df_sim['DOENCA'].map(taxas_conversao).fillna(0.0)
    df_sim['PACIENTES_MIGRADOS'] = (df_sim['PACIENTES_TARDIO'] * df_sim['ALPHA']).round().astype(int)

    df_sim['ECONOMIA_LIQUIDA_ANUAL'] = (
        df_sim['PACIENTES_MIGRADOS'] * (df_sim['TICKET_TARDIO'] - df_sim['TICKET_PRECOCE'])
    ).clip(lower=0.0)

    df_sim['NOVO_CUSTO_ANUAL'] = df_sim['CUSTO_ATUAL_ANUAL'] - df_sim['ECONOMIA_LIQUIDA_ANUAL']

    df_sim['CUSTO_ATUAL_HORIZONTE'] = df_sim['CUSTO_ATUAL_ANUAL'] * horizonte_anos
    df_sim['NOVO_CUSTO_HORIZONTE'] = df_sim['NOVO_CUSTO_ANUAL'] * horizonte_anos
    df_sim['ECONOMIA_ACUMULADA'] = df_sim['ECONOMIA_LIQUIDA_ANUAL'] * horizonte_anos

    df_sim['INTERNACOES_EVITADAS_HORIZONTE'] = (
        df_sim['QTD_INTERNACOES'] * df_sim['ALPHA'] * horizonte_anos
    ).round().astype(int)
    df_sim['DIAS_LEITO_LIBERADOS_HORIZONTE'] = (
        df_sim['DIAS_LEITO_TOTAIS'] * df_sim['ALPHA'] * horizonte_anos
    ).round().astype(int)

    return df_sim


def formatar_brl(valor: float) -> str:
    if abs(valor) >= 1_000_000_000:
        return f"R$ {valor / 1_000_000_000:,.2f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(valor) >= 1_000_000:
        return f"R$ {valor / 1_000_000:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# -----------------------------------------------------------------------------
# 4. INTERFACE E CONTROLES LATERAIS (SEM BOTÃO DE UPLOAD)
# -----------------------------------------------------------------------------
df_bruto = carregar_base_embutida()

with st.sidebar:
    st.header("⚙️ Parâmetros da Simulação")
    st.caption("Base consolidada SIH/SIA-SUS integrada nativamente ao código.")

    # Filtros Geográficos e Clínicos
    lista_ufs = sorted(df_bruto['UF'].unique().tolist())
    ufs_selecionadas = st.multiselect(
        "Unidades Federativas (Vazio = Brasil Inteiro):",
        options=lista_ufs,
        default=[]
    )

    lista_doencas = sorted(df_bruto['DOENCA'].unique().tolist())
    doencas_selecionadas = st.multiselect(
        "Condições Clínicas:",
        options=lista_doencas,
        default=lista_doencas
    )

    st.divider()
    st.subheader("🎯 Meta de Diagnóstico Precoce (α)")
    st.caption("Percentual de pacientes hoje em estágio tardio que seriam estabilizados precocemente:")

    alpha_dm = st.slider("Diabetes Mellitus (%)", 0, 80, 35, step=5) / 100.0
    alpha_cp = st.slider("Doenças Cardiopulmonares (%)", 0, 80, 30, step=5) / 100.0
    alpha_pso = st.slider("Psoríase (%)", 0, 80, 45, step=5) / 100.0
    alpha_aps = st.slider("Artrite Psoriásica (%)", 0, 80, 50, step=5) / 100.0

    mapa_alphas = {
        'Diabetes Mellitus': alpha_dm,
        st.slider
        'Doenças Cardiopulmonares': alpha_cp,
        'Psoríase': alpha_pso,
        'Artrite Psoriásica': alpha_aps
    }

    st.divider()
    st.subheader("📐 Calibração Econômica")
    horizonte = st.slider("Horizonte Temporal (Anos)", min_value=1, max_value=10, value=5)
    fator_sih = st.slider(
        "Fator de Correção Tabela SIH-SUS",
        min_value=1.0, max_value=2.5, value=1.5, step=0.1,
        help="Corrige a defasagem entre o valor repassado na AIH/SIGTAP e o custo real de operação hospitalar (1.0 = Valor Nominal SUS)."
    )

df_filtrado = df_bruto.copy()
if ufs_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['UF'].isin(ufs_selecionadas)]
if doencas_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['DOENCA'].isin(doencas_selecionadas)]

df_resultado = simular_impacto_orcamentario(
    df=df_filtrado,
    taxas_conversao=mapa_alphas,
    fator_defasagem_sih=fator_sih,
    horizonte_anos=horizonte
)

# -----------------------------------------------------------------------------
# 5. PAINEL PRINCIPAL E INDICADORES EXECUTIVOS (KPIs)
# -----------------------------------------------------------------------------
escopo_geo = ", ".join(ufs_selecionadas) if ufs_selecionadas else "Brasil (27 UFs)"
st.title("🏥 Simulador de Impacto Orçamentário — Diagnóstico Precoce (DataSUS)")
st.markdown(f"**Escopo Geográfico:** `{escopo_geo}` | **Horizonte:** `{horizonte} ano(s)` | **Multiplicador SIH:** `{fator_sih}x`")

custo_atual_tot = df_resultado['CUSTO_ATUAL_HORIZONTE'].sum()
novo_custo_tot = df_resultado['NOVO_CUSTO_HORIZONTE'].sum()
economia_tot = df_resultado['ECONOMIA_ACUMULADA'].sum()
reducao_perc = (economia_tot / custo_atual_tot * 100) if custo_atual_tot > 0 else 0.0
internacoes_evitadas = df_resultado['INTERNACOES_EVITADAS_HORIZONTE'].sum()
leitos_liberados = df_resultado['DIAS_LEITO_LIBERADOS_HORIZONTE'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    label=f"Gasto Atual Projetado ({horizonte} anos)",
    value=formatar_brl(custo_atual_tot)
)
col2.metric(
    label="Novo Orçamento com Triagem Precoce",
    value=formatar_brl(novo_custo_tot),
    delta=f"-{reducao_perc:.1f}% no orçamento",
    delta_color="inverse"
)
col3.metric(
    label="Economia Líquida (Gasto Evitado)",
    value=formatar_brl(economia_tot),
    delta="Recursos liberados para o SUS",
    delta_color="normal"
)
col4.metric(
    label="Desfechos Hospitalares Evitados",
    value=f"{internacoes_evitadas:,.0f} AIHs".replace(",", "."),
    delta=f"{leitos_liberados:,.0f} dias-leito liberados".replace(",", "."),
    delta_color="normal"
)

st.divider()

# -----------------------------------------------------------------------------
# 6. VISUALIZAÇÕES INTERATIVAS (PLOTLY DARK TEMPLATE)
# -----------------------------------------------------------------------------
aba_graficos, aba_estados, aba_tabela = st.tabs([
    "📊 Análise por Doença e Evolução Temporal",
    "🗺️ Ranking de Economia por UF",
    "📑 Base Consolidada e Exportação"
])

with aba_graficos:
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        df_por_doenca = df_resultado.groupby('DOENCA', as_index=False).agg(
            Custo_Atual=('CUSTO_ATUAL_HORIZONTE', 'sum'),
            Novo_Custo=('NOVO_CUSTO_HORIZONTE', 'sum'),
            Economia=('ECONOMIA_ACUMULADA', 'sum')
        )
        df_melt = df_por_doenca.melt(
            id_vars='DOENCA',
            value_vars=['Custo_Atual', 'Novo_Custo'],
            var_name='Cenário',
            value_name='Valor_BRL'
        )
        df_melt['Cenário'] = df_melt['Cenário'].replace({
            'Custo_Atual': 'Cenário Atual (Diagnóstico Tardio)',
            'Novo_Custo': 'Cenário Simulado (Manejo Precoce)'
        })

        fig_bar = px.bar(
            df_melt,
            x='DOENCA',
            y='Valor_BRL',
            color='Cenário',
            barmode='group',
            template='plotly_dark',
            title=f"Comparativo de Custo Total por Condição ({horizonte} anos)",
            labels={'DOENCA': 'Condição Clínica', 'Valor_BRL': 'Orçamento Total (R$)'},
            color_discrete_sequence=['#ef553b', '#00cc96']
        )
        fig_bar.update_layout(legend_title_text='', height=430)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        anos_lista = list(range(1, horizonte + 1))
        custo_anual_base = df_resultado['CUSTO_ATUAL_ANUAL'].sum()
        custo_anual_sim = df_resultado['NOVO_CUSTO_ANUAL'].sum()

        df_tempo = pd.DataFrame({
            'Ano': anos_lista,
            'Despesa Acumulada (Cenário Atual)': [custo_anual_base * a for a in anos_lista],
            'Despesa Acumulada (Com Manejo Precoce)': [custo_anual_sim * a for a in anos_lista],
            'Economia Líquida Acumulada': [(custo_anual_base - custo_anual_sim) * a for a in anos_lista]
        })

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_tempo['Ano'],
            y=df_tempo['Despesa Acumulada (Cenário Atual)'],
            mode='lines+markers',
            name='Trajetória Atual (Tardia)',
            line=dict(color='#ef553b', width=3)
        ))
        fig_line.add_trace(go.Scatter(
            x=df_tempo['Ano'],
            y=df_tempo['Despesa Acumulada (Com Manejo Precoce)'],
            mode='lines+markers',
            name='Trajetória com Triagem Precoce',
            fill='tonexty',
            fillcolor='rgba(0, 204, 150, 0.2)',
            line=dict(color='#00cc96', width=3)
        ))
        fig_line.update_layout(
            template='plotly_dark',
            title="Projeção Acumulada do Orçamento e Gasto Evitado",
            xaxis_title="Ano da Projeção",
            yaxis_title="Gasto Acumulado (R$)",
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_line, use_container_width=True)

    df_comp = df_resultado.groupby('DOENCA', as_index=False).agg(
        Internacoes_SIH=('CUSTO_HOSP_AJUSTADO', 'sum'),
        APAC_Alto_Custo_CEAF_TRS=('Tardio_Ambulatorial_Alto_Custo', 'sum'),
        Acompanhamento_Precoce=('Precoce_Monitoramento_Basico', 'sum')
    ).melt(id_vars='DOENCA', var_name='Componente', value_name='Custo_Anual')

    fig_comp = px.bar(
        df_comp,
        y='DOENCA',
        x='Custo_Anual',
        color='Componente',
        orientation='h',
        template='plotly_dark',
        title="Composição Anual do Gasto por Fonte Pagadora (SIH-SUS vs. SIA/APAC Alto Custo vs. Atenção Básica)",
        labels={'Custo_Anual': 'Despesa Anual (R$)', 'DOENCA': ''},
        color_discrete_sequence=['#ff6692', '#ab63fa', '#19d3f3']
    )
    fig_comp.update_layout(height=360)
    st.plotly_chart(fig_comp, use_container_width=True)

with aba_estados:
    df_uf = df_resultado.groupby(['UF', 'DOENCA'], as_index=False).agg(
        Economia_Acumulada=('ECONOMIA_ACUMULADA', 'sum'),
        Internacoes_Evitadas=('INTERNACOES_EVITADAS_HORIZONTE', 'sum')
    )
    ordem_ufs = (
        df_uf.groupby('UF')['Economia_Acumulada']
        .sum()
        .sort_values(ascending=True)
        .index.tolist()
    )

    fig_uf = px.bar(
        df_uf,
        x='Economia_Acumulada',
        y='UF',
        color='DOENCA',
        orientation='h',
        category_orders={'UF': ordem_ufs},
        template='plotly_dark',
        title=f"Ranking de Economia Orçamentária Potencial por UF ({horizonte} anos)",
        labels={'Economia_Acumulada': 'Economia Líquida Acumulada (R$)', 'UF': 'Unidade Federativa'}
    )
    fig_uf.update_layout(height=680)
    st.plotly_chart(fig_uf, use_container_width=True)

with aba_tabela:
    st.subheader("Detalhamento Financeiro e Epidemiológico por UF e Doença")
    colunas_exibicao = [
        'UF', 'DOENCA', 'PACIENTES_PRECOCE', 'PACIENTES_TARDIO',
        'PACIENTES_MIGRADOS', 'TICKET_PRECOCE', 'TICKET_TARDIO',
        'CUSTO_ATUAL_HORIZONTE', 'NOVO_CUSTO_HORIZONTE',
        'ECONOMIA_ACUMULADA', 'INTERNACOES_EVITADAS_HORIZONTE', 'DIAS_LEITO_LIBERADOS_HORIZONTE'
    ]
    df_exibicao = df_resultado[colunas_exibicao].sort_values(by='ECONOMIA_ACUMULADA', ascending=False)

    st.dataframe(
        df_exibicao.style.format({
            'TICKET_PRECOCE': 'R$ {:,.2f}',
            'TICKET_TARDIO': 'R$ {:,.2f}',
            'CUSTO_ATUAL_HORIZONTE': 'R$ {:,.2f}',
            'NOVO_CUSTO_HORIZONTE': 'R$ {:,.2f}',
            'ECONOMIA_ACUMULADA': 'R$ {:,.2f}'
        }),
        use_container_width=True,
        height=450
    )

    csv_bytes = df_exibicao.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar Relatório da Simulação (.CSV)",
        data=csv_bytes,
        file_name=f"simulacao_economia_datasus_{horizonte}anos.csv",
        mime="text/csv"
    )
