# modules/comparador.py
"""
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.amortizacion import (
    calcular_cuota_francesa, 
    calcular_cuota_alemana,
    calcular_totales, 
    generar_tabla_francesa,
    generar_tabla_alemana
)
from modules.utilities import formatear_moneda
from modules.interes import calcular_tcea_completa

# Importar API de tasas
try:
    from modules.api_tasas import (
        APITasas,
        cargar_datos_api,
        obtener_bancos,
        obtener_tea,
        obtener_promedio
    )
    API_DISPONIBLE = True
except ImportError:
    API_DISPONIBLE = False

CATEGORIAS_CREDITO = {
    "Corporativos": {
        "descripcion": "Créditos para grandes corporaciones con ventas anuales > S/ 200 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Grandes Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales > S/ 20 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Medianas Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales entre S/ 1.7 y S/ 20 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Pequeñas Empresas": {
        "descripcion": "Créditos para empresas con ventas anuales entre S/ 150 mil y S/ 1.7 millones",
        "opciones": {
            "Descuentos": "Descuentos",
            "Préstamos hasta 30 días": "Préstamos hasta 30 días",
            "Préstamos de 31 a 90 días": "Préstamos de 31 a 90 días",
            "Préstamos de 91 a 180 días": "Préstamos de 91 a 180 días",
            "Préstamos de 181 a 360 días": "Préstamos de 181 a 360 días",
            "Préstamos a más de 360 días": "Préstamos a más de 360 días",
        }
    },
    "Microempresas": {
        "descripcion": "Créditos para negocios con ventas anuales < S/ 150 mil",
        "opciones": {
            "Tarjetas de Crédito": "Tarjetas de Crédito",
            "Descuentos": "Descuentos",
            "Préstamos Revolventes": "Préstamos Revolventes",
            "Préstamos a cuota fija hasta 30 días": "Préstamos a cuota fija hasta 30 días",
            "Préstamos a cuota fija de 31 a 90 días": "Préstamos  a cuota fija de 31 a 90 días",
            "Préstamos a cuota fija de 91 a 180 días": "Préstamos  a cuota fija de 91 a 180 días",
            "Préstamos a cuota fija de 181 a 360 días": "Préstamos a cuota fija de 181 a 360 días",
            "Préstamos a cuota fija a más de 360 días": "Préstamos a cuota fija a más de 360 días",
        }
    },
    "Consumo": {
        "descripcion": "Créditos para personas naturales (uso personal)",
        "opciones": {
            "Tarjetas de Crédito": "Tarjetas de Crédito",
            "Préstamos Revolventes": "Préstamos Revolventes",
            "Préstamos para Automóviles": "Préstamos no  Revolventes para automóviles",
            "Libre Disponibilidad (hasta 360 días)": "Préstamos no  Revolventes para libre disponibilidad hasta 360 días",
            "Libre Disponibilidad (más de 360 días)": "Préstamos no  Revolventes para libre disponibilidad a más de 360 días",
            "Créditos Pignoraticios": "Créditos pignoraticios",
        }
    },
    "Hipotecarios": {
        "descripcion": "Créditos con garantía hipotecaria para vivienda",
        "opciones": {
            "Préstamos para Vivienda": "Préstamos hipotecarios para vivienda",
        }
    },
}


def mostrar_comparador_creditos():
    """
    Muestra la interfaz del comparador de créditos con datos reales de SBS.
    CORREGIDO: Maneja correctamente filas con nombres repetidos pasando la categoría.
    """
    st.title("📊 Comparador de Créditos")
    st.write("Compara múltiples opciones de financiamiento y elige la mejor")
    
    st.divider()
    
    # ========== PASO 1: CONFIGURACIÓN ==========
    st.subheader("🔧 Configuración General")
    
    # Cargar datos de la API (con cache)
    api_conectada = False
    api_tasas = None
    
    if API_DISPONIBLE:
        with st.spinner("Conectando con la API de tasas SBS..."):
            df_tasas, df_bancos, api_conectada = cargar_datos_api()
            
            if api_conectada:
                api_tasas = APITasas()
                api_tasas._tasas_activas = df_tasas
                api_tasas._bancos = df_bancos
                api_tasas._cache_cargado = True
                # IMPORTANTE: Construir el índice de categorías
                api_tasas._construir_indice_categorias()
    
    # Mostrar estado de conexión
    if api_conectada:
        st.success("✅ Conectado a la API - Usando tasas reales de la SBS")
    else:
        st.warning("⚠️ API no disponible - Usando tasas de referencia")
    
    col_config1, col_config2, col_config3 = st.columns(3)
    
    with col_config1:
        sistema_amortizacion = st.selectbox(
            "📐 Sistema de Amortización",
            ["Francés (Cuota Fija)", "Alemán (Amortización Fija)"],
            help="Francés: cuota mensual constante | Alemán: cuota mensual decreciente"
        )
    
    with col_config2:
        # PRIMER SELECTOR: Categoría de crédito
        categoria_credito = st.selectbox(
            "🏢 Categoría de Crédito",
            list(CATEGORIAS_CREDITO.keys()),
            help="Selecciona según el tipo de cliente o empresa"
        )
        st.caption(f"ℹ️ {CATEGORIAS_CREDITO[categoria_credito]['descripcion']}")
    
    with col_config3:
        # SEGUNDO SELECTOR: Tipo específico (depende del primero)
        opciones_disponibles = list(CATEGORIAS_CREDITO[categoria_credito]["opciones"].keys())
        
        tipo_credito_especifico = st.selectbox(
            "💳 Tipo de Producto",
            opciones_disponibles,
            help="Selecciona el producto crediticio específico"
        )

    # Obtener el nombre de la fila en la tabla SBS
    fila_tabla_sbs = CATEGORIAS_CREDITO[categoria_credito]["opciones"][tipo_credito_especifico]
    
    # Variable para nombres de archivo (sin caracteres especiales)
    nombre_archivo_base = f"{categoria_credito}_{tipo_credito_especifico}".replace(" ", "_").replace("(", "").replace(")", "")
    
    # Determinar sistema
    if sistema_amortizacion == "Francés (Cuota Fija)":
        sistema = "frances"
    else:
        sistema = "aleman"
    
    # ========== OBTENER DATOS DE LA API ==========
    if api_conectada and api_tasas:
        # Obtener bancos con tasas válidas para esta CATEGORÍA + TIPO
        bancos_disponibles = api_tasas.get_bancos(
            tipo_credito=tipo_credito_especifico, 
            categoria=categoria_credito
        )
        
        # Obtener promedio del mercado
        promedio_mercado = api_tasas.get_promedio(
            tipo_credito=tipo_credito_especifico, 
            categoria=categoria_credito
        )
        
        # Obtener mejor tasa
        mejor_banco, mejor_tasa = api_tasas.get_mejor_tasa(
            tipo_credito=tipo_credito_especifico, 
            categoria=categoria_credito
        )
        
        # Obtener todas las tasas (para debug)
        tasas_por_tipo = api_tasas.get_tasas_por_tipo(
            tipo_credito=tipo_credito_especifico, 
            categoria=categoria_credito
        )
        
        # Mostrar info del mercado
        st.divider()
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📈 Promedio del Mercado", f"{promedio_mercado:.2f}%")
        with col_info2:
            st.metric("🏆 Mejor Tasa", f"{mejor_tasa:.2f}%", mejor_banco)
        with col_info3:
            st.metric("🏦 Bancos Disponibles", f"{len(bancos_disponibles)}")
        
        # Debug expandible
        with st.expander("🔍 Debug: Información de filtrado"):
            st.write(f"**Categoría:** `{categoria_credito}`")
            st.write(f"**Tipo específico:** `{tipo_credito_especifico}`")
            st.write(f"**Fila en tabla SBS:** `{fila_tabla_sbs}`")
            st.write(f"**Bancos encontrados:** {len(bancos_disponibles)}")
            st.write(f"**Lista:** `{bancos_disponibles}`")
            
            if tasas_por_tipo:
                st.write("**Tasas por banco:**")
                for banco, tasa in sorted(tasas_por_tipo.items(), key=lambda x: x[1]):
                    st.write(f"  - {banco}: {tasa}%")
            
            # Mostrar índices de categorías
            indices = api_tasas.get_indices_categorias()
            if indices:
                st.write("**Índices de categorías en DataFrame:**")
                for cat, idx in indices.items():
                    marker = "👉" if cat == categoria_credito.lower() else "  "
                    st.write(f"  {marker} {cat}: índice {idx}")
    else:
        bancos_disponibles = ["BBVA", "Crédito", "Interbank", "Scotiabank", "Pichincha", "BIF"]
        promedio_mercado = 15.0
    
    # Mostrar información del sistema seleccionado
    if sistema == "frances":
        st.info("ℹ️ **Sistema Francés:** La cuota mensual es constante. Al inicio pagas más intereses y menos capital.")
    else:
        st.info("ℹ️ **Sistema Alemán:** La amortización del capital es constante. La cuota mensual disminuye mes a mes.")
    
    st.divider()
    
    # ========== PASO 2: NÚMERO DE CRÉDITOS ==========
    num_creditos = st.slider(
        "¿Cuántos créditos quieres comparar?", 
        2, 5, 2,
        help="Selecciona entre 2 y 5 opciones de crédito para comparar"
    )
    
    st.divider()
    
    # ========== PASO 3: FORMULARIOS DE CADA CRÉDITO ==========
    st.subheader("💳 Datos de los Créditos")
    
    creditos = []
    cols = st.columns(num_creditos)
    
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"### Crédito {chr(65 + i)}")
            
            # Selector de banco
            banco = st.selectbox(
                "Banco",
                bancos_disponibles,
                key=f"banco_{i}",
                help="Selecciona la entidad financiera"
            )
            
            # Obtener TEA sugerida según banco
            if api_conectada and api_tasas:
                tea_sugerida = api_tasas.get_tea(
                    banco=banco, 
                    tipo_credito=tipo_credito_especifico, 
                    categoria=categoria_credito
                )
                if tea_sugerida <= 0:
                    tea_sugerida = 15.0 + (i * 2)
            else:
                tea_sugerida = 15.0 + (i * 2)
            
            st.markdown("**Datos Principales:**")
            
            monto = st.number_input(
                "Monto (S/)",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
                key=f"monto_{i}",
            )
            
            plazo = st.number_input(
                "Plazo (meses)",
                min_value=1,
                max_value=360,
                value=12,
                step=1,
                key=f"plazo_{i}",
            )
            
            tea = st.slider(
                "TEA %",
                min_value=0.0,
                max_value=100.0,
                value=float(tea_sugerida),
                step=0.1,
                key=f"tea_{i}",
                help=f"Tasa sugerida para {banco}: {tea_sugerida:.2f}%"
            )
            
            # Indicador vs promedio
            if api_conectada:
                diferencia = tea - promedio_mercado
                if diferencia < -0.5:
                    st.success(f"✅ {abs(diferencia):.2f}% menor al promedio")
                elif diferencia > 0.5:
                    st.warning(f"⚠️ {diferencia:.2f}% mayor al promedio")
                else:
                    st.info("📊 Cercana al promedio")
            
            st.markdown("---")
            st.markdown("**💰 Costos Adicionales:**")
            
            with st.expander("Ver costos detallados"):
                comision_desembolso = st.number_input(
                    "Comisión de desembolso (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.1,
                    key=f"com_desemb_{i}",
                )
                
                comision_mensual = st.number_input(
                    "Comisión mensual (S/)",
                    min_value=0.0,
                    value=0.0,
                    step=5.0,
                    key=f"com_mens_{i}",
                )
                
                seguro_desgravamen = st.number_input(
                    "Seguro de desgravamen (% mensual)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.01,
                    key=f"seguro_{i}",
                )
                
                portes = st.number_input(
                    "Portes y gastos (S/)",
                    min_value=0.0,
                    value=0.0,
                    step=5.0,
                    key=f"portes_{i}",
                )
            
            creditos.append({
                'banco': banco,
                'monto': monto,
                'tea': tea / 100,
                'plazo': plazo,
                'comision_desembolso': comision_desembolso / 100,
                'comision_mensual': comision_mensual,
                'seguro_desgravamen': seguro_desgravamen / 100,
                'portes': portes
            })
    
    st.divider()
    
    # ========== BOTÓN DE COMPARACIÓN ==========
    if st.button("🔍 Comparar Créditos", type="primary", use_container_width=True):
        
        with st.spinner("Calculando y comparando créditos..."):
            resultados = []
            
            for i, credito in enumerate(creditos):
                
                if sistema == "frances":
                    cuota_base = calcular_cuota_francesa(credito['monto'], credito['tea'], credito['plazo'])
                    tabla = generar_tabla_francesa(credito['monto'], credito['tea'], credito['plazo'])
                else:
                    tabla = generar_tabla_alemana(credito['monto'], credito['tea'], credito['plazo'])
                    cuota_base = tabla.loc[0, 'cuota']
                
                totales = calcular_totales(tabla)
                
                # Costos adicionales
                monto_comision_desembolso = credito['monto'] * credito['comision_desembolso']
                costo_mensual_adicional = credito['comision_mensual'] + credito['portes']
                saldo_promedio = credito['monto'] / 2
                seguro_total = saldo_promedio * credito['seguro_desgravamen'] * credito['plazo']
                
                if sistema == "frances":
                    cuota_total_inicial = cuota_base + costo_mensual_adicional + (seguro_total / credito['plazo'])
                else:
                    cuota_primera = tabla.loc[0, 'cuota']
                    cuota_ultima = tabla.loc[credito['plazo']-1, 'cuota']
                    cuota_total_inicial = cuota_primera + costo_mensual_adicional + (seguro_total / credito['plazo'])
                    cuota_total_final = cuota_ultima + costo_mensual_adicional + (seguro_total / credito['plazo'])
                
                costo_total = (
                    totales['total_pagado'] + 
                    monto_comision_desembolso + 
                    (costo_mensual_adicional * credito['plazo']) + 
                    seguro_total
                )
                
                try:
                    tcea = calcular_tcea_completa(
                        credito['monto'],
                        credito['tea'],
                        credito['plazo'],
                        credito['comision_desembolso'],
                        credito['comision_mensual'],
                        credito['seguro_desgravamen'],
                        credito['portes']
                    )
                except Exception:
                    tcea = None
                
                resultado = {
                    'Crédito': credito['banco'],
                    'Sistema': sistema_amortizacion,
                    'TEA (%)': credito['tea'] * 100,
                    'TCEA (%)': tcea if tcea else "N/A",
                    'Total Intereses': totales['total_intereses'],
                    'Costos Adicionales': monto_comision_desembolso + (costo_mensual_adicional * credito['plazo']) + seguro_total,
                    'Costo Total': costo_total
                }
                
                if sistema == "frances":
                    resultado['Cuota Mensual'] = cuota_total_inicial
                else:
                    resultado['Primera Cuota'] = cuota_total_inicial
                    resultado['Última Cuota'] = cuota_total_final
                
                resultados.append(resultado)
            
            df_resultados = pd.DataFrame(resultados)

            # ========== RESUMEN EJECUTIVO ==========
            st.subheader("🏆 Resumen Ejecutivo")
            
            idx_ganador = df_resultados['Costo Total'].idxmin()
            idx_perdedor = df_resultados['Costo Total'].idxmax()
            
            ganador = df_resultados.loc[idx_ganador]
            perdedor = df_resultados.loc[idx_perdedor]
            
            ahorro_vs_peor = perdedor['Costo Total'] - ganador['Costo Total']
            ahorro_porcentual_vs_peor = (ahorro_vs_peor / perdedor['Costo Total']) * 100
            
            st.success(f"""
            ### 🥇 Mejor Opción: {ganador['Crédito']}
            
            **Por qué es la mejor opción:**
            - ✅ **Ahorro vs peor opción:** {formatear_moneda(ahorro_vs_peor)} ({ahorro_porcentual_vs_peor:.1f}% menos)
            - ✅ **Costo total:** {formatear_moneda(ganador['Costo Total'])}
            - ✅ **TCEA:** {ganador['TCEA (%)']}{'%' if isinstance(ganador['TCEA (%)'], (int, float)) else ''}
            - ✅ **Total intereses:** {formatear_moneda(ganador['Total Intereses'])}
            """)
            
            # Métricas comparativas
            col_res1, col_res2, col_res3 = st.columns(3)
            
            with col_res1:
                if sistema == "frances":
                    diferencia_cuota = perdedor['Cuota Mensual'] - ganador['Cuota Mensual']
                    st.metric(
                        "Cuota Mensual",
                        formatear_moneda(ganador['Cuota Mensual']),
                        f"-{formatear_moneda(diferencia_cuota)}" if diferencia_cuota > 0 else f"+{formatear_moneda(abs(diferencia_cuota))}"
                    )
                else:
                    st.metric(
                        "Primera Cuota",
                        formatear_moneda(ganador['Primera Cuota']),
                        "Cuota decreciente"
                    )
            
            with col_res2:
                promedio_intereses = df_resultados['Total Intereses'].mean()
                diferencia_vs_promedio = ganador['Total Intereses'] - promedio_intereses
                st.metric(
                    "Total Intereses",
                    formatear_moneda(ganador['Total Intereses']),
                    f"{formatear_moneda(abs(diferencia_vs_promedio))} {'por debajo' if diferencia_vs_promedio < 0 else 'por encima'}"
                )
            
            with col_res3:
                st.metric(
                    "Ranking",
                    f"1° de {len(df_resultados)}",
                    "Mejor opción"
                )
            
            if ganador['Costos Adicionales'] > ganador['Total Intereses'] * 0.2:
                st.warning(f"""
                ⚠️ **Atención:** Este crédito tiene costos adicionales significativos 
                ({formatear_moneda(ganador['Costos Adicionales'])}). 
                """)
            
            st.divider()

            # ========== TABLA COMPARATIVA ==========
            st.subheader("📋 Tabla Comparativa Detallada")
            
            df_mostrar = df_resultados.copy()
            df_mostrar['TEA (%)'] = df_mostrar['TEA (%)'].apply(lambda x: f"{x:.2f}%")
            if df_mostrar['TCEA (%)'].iloc[0] != "N/A":
                df_mostrar['TCEA (%)'] = df_mostrar['TCEA (%)'].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
            
            if sistema == "frances":
                df_mostrar['Cuota Mensual'] = df_mostrar['Cuota Mensual'].apply(formatear_moneda)
            else:
                df_mostrar['Primera Cuota'] = df_mostrar['Primera Cuota'].apply(formatear_moneda)
                df_mostrar['Última Cuota'] = df_mostrar['Última Cuota'].apply(formatear_moneda)
            
            df_mostrar['Total Intereses'] = df_mostrar['Total Intereses'].apply(formatear_moneda)
            df_mostrar['Costos Adicionales'] = df_mostrar['Costos Adicionales'].apply(formatear_moneda)
            df_mostrar['Costo Total'] = df_mostrar['Costo Total'].apply(formatear_moneda)
            
            st.dataframe(df_mostrar, use_container_width=True)
            
            st.divider()
            
            # ========== MÉTRICAS DESTACADAS ==========
            st.subheader("🎯 Métricas Clave")
            
            if sistema == "frances":
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    idx_mejor_cuota = df_resultados['Cuota Mensual'].idxmin()
                    st.metric(
                        "Menor Cuota",
                        formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Cuota Mensual']),
                        df_resultados.loc[idx_mejor_cuota, 'Crédito']
                    )
            else:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    idx_mejor_cuota = df_resultados['Primera Cuota'].idxmin()
                    st.metric(
                        "Menor Primera Cuota",
                        formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Primera Cuota']),
                        df_resultados.loc[idx_mejor_cuota, 'Crédito']
                    )
            
            with col2:
                idx_mejor_costo = df_resultados['Costo Total'].idxmin()
                st.metric(
                    "Menor Costo Total",
                    formatear_moneda(df_resultados.loc[idx_mejor_costo, 'Costo Total']),
                    df_resultados.loc[idx_mejor_costo, 'Crédito']
                )
            
            with col3:
                idx_menos_interes = df_resultados['Total Intereses'].idxmin()
                st.metric(
                    "Menos Intereses",
                    formatear_moneda(df_resultados.loc[idx_menos_interes, 'Total Intereses']),
                    df_resultados.loc[idx_menos_interes, 'Crédito']
                )
            
            with col4:
                if df_resultados['TCEA (%)'].iloc[0] != "N/A":
                    idx_mejor_tcea = df_resultados['TCEA (%)'].idxmin()
                    st.metric(
                        "Menor TCEA",
                        f"{df_resultados.loc[idx_mejor_tcea, 'TCEA (%)']:.2f}%",
                        df_resultados.loc[idx_mejor_tcea, 'Crédito']
                    )
            
            st.divider()
            
            # ========== GRÁFICOS ==========
            st.subheader("📊 Comparación Visual")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = go.Figure()
                
                if sistema == "frances":
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Cuota Mensual'],
                        marker_color='#667eea',
                        text=df_resultados['Cuota Mensual'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Cuota'
                    ))
                    titulo_cuota = 'Cuota Mensual por Crédito'
                else:
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Primera Cuota'],
                        marker_color='#667eea',
                        text=df_resultados['Primera Cuota'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Primera Cuota'
                    ))
                    fig1.add_trace(go.Bar(
                        x=df_resultados['Crédito'],
                        y=df_resultados['Última Cuota'],
                        marker_color='#95a5f6',
                        text=df_resultados['Última Cuota'].apply(lambda x: f"S/ {x:,.2f}"),
                        textposition='auto',
                        name='Última Cuota'
                    ))
                    titulo_cuota = 'Primera vs Última Cuota por Crédito'
                
                fig1.update_layout(
                    title=titulo_cuota,
                    xaxis_title='Crédito',
                    yaxis_title='Cuota (S/)',
                    showlegend=(sistema == "aleman")
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=df_resultados['Crédito'],
                    y=df_resultados['Costo Total'],
                    marker_color='#f5576c',
                    text=df_resultados['Costo Total'].apply(lambda x: f"S/ {x:,.2f}"),
                    textposition='auto',
                    name='Costo Total'
                ))
                fig2.update_layout(
                    title='Costo Total del Crédito',
                    xaxis_title='Crédito',
                    yaxis_title='Costo Total (S/)',
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico de barras apiladas - Desglose de costos
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                name='Intereses',
                x=df_resultados['Crédito'],
                y=df_resultados['Total Intereses'],
                marker_color='#FF6B6B'
            ))
            fig3.add_trace(go.Bar(
                name='Costos Adicionales',
                x=df_resultados['Crédito'],
                y=df_resultados['Costos Adicionales'],
                marker_color='#FFA500'
            ))
            fig3.update_layout(
                title='Desglose de Costos por Crédito',
                xaxis_title='Crédito',
                yaxis_title='Monto (S/)',
                barmode='stack'
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            st.divider()
            
            # ========== RECOMENDACIÓN FINAL ==========
            st.subheader("🎯 Recomendación Final")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if sistema == "frances":
                    st.success(f"""
                    **💰 Mejor para pago mensual:**
                    
                    {df_resultados.loc[idx_mejor_cuota, 'Crédito']}
                    
                    Cuota: {formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Cuota Mensual'])}
                    """)
                else:
                    st.success(f"""
                    **💰 Menor cuota inicial:**
                    
                    {df_resultados.loc[idx_mejor_cuota, 'Crédito']}
                    
                    Primera cuota: {formatear_moneda(df_resultados.loc[idx_mejor_cuota, 'Primera Cuota'])}
                    """)
            
            with col2:
                st.success(f"""
                **💵 Mejor costo total:**
                
                {df_resultados.loc[idx_mejor_costo, 'Crédito']}
                
                Total: {formatear_moneda(df_resultados.loc[idx_mejor_costo, 'Costo Total'])}
                """)
            
            with col3:
                st.success(f"""
                **📉 Menos intereses:**
                
                {df_resultados.loc[idx_menos_interes, 'Crédito']}
                
                Intereses: {formatear_moneda(df_resultados.loc[idx_menos_interes, 'Total Intereses'])}
                """)
            
            st.divider()
            
            # ========== EXPORTAR RESULTADOS ==========
            st.subheader("💾 Exportar Resultados")
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                # Exportar a CSV
                csv = df_resultados.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name=f"comparacion_{nombre_archivo_base}_{sistema}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_csv"
                )
            
            with col_exp2:
                # Exportar a Excel
                try:
                    from modules.exportador import exportar_a_excel
                    
                    # Pasar el tipo de crédito completo para el Excel
                    tipo_credito_completo = f"{categoria_credito} - {tipo_credito_especifico}"
                    excel_file = exportar_a_excel(df_resultados, creditos, sistema, tipo_credito_completo)
                    
                    st.download_button(
                        label="📊 Descargar Excel",
                        data=excel_file,
                        file_name=f"comparacion_{nombre_archivo_base}_{sistema}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="btn_excel"
                    )
                except Exception as e:
                    st.error(f"Error al generar Excel: {e}")
            
            with col_exp3:
                # Exportar a PDF
                try:
                    from modules.exportador import exportar_a_pdf
                    
                    tipo_credito_completo = f"{categoria_credito} - {tipo_credito_especifico}"
                    pdf_file = exportar_a_pdf(df_resultados, creditos, sistema, tipo_credito_completo)
                    
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=pdf_file,
                        file_name=f"comparacion_{nombre_archivo_base}_{sistema}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_pdf"
                    )
                except Exception as e:
                    st.error(f"Error al generar PDF: {e}")

    # ========== COMPARACIÓN FRANCÉS VS ALEMÁN ==========
    st.subheader("🔄 Comparador: Sistema Francés vs Alemán")
    
    comparar_sistemas = st.checkbox(
        "Comparar ambos sistemas de amortización para los créditos ingresados",
        help="Muestra cómo cambiaría el costo usando el sistema contrario"
    )
    
    if comparar_sistemas:
        st.info("📊 Comparación entre Sistema Francés (cuota fija) y Sistema Alemán (cuota decreciente)")
        
        # Seleccionar cuál crédito comparar
        bancos_lista = [c['banco'] for c in creditos]
        banco_a_comparar = st.selectbox(
            "Selecciona el crédito a analizar con ambos sistemas:",
            bancos_lista
        )
        
        # Obtener datos del crédito seleccionado
        credito_seleccionado = next(c for c in creditos if c['banco'] == banco_a_comparar)
        
        with st.spinner("Calculando ambos sistemas..."):
            # ===== CALCULAR SISTEMA FRANCÉS =====
            tabla_francesa = generar_tabla_francesa(
                credito_seleccionado['monto'], 
                credito_seleccionado['tea'], 
                credito_seleccionado['plazo']
            )
            totales_frances = calcular_totales(tabla_francesa)
            cuota_francesa = calcular_cuota_francesa(
                credito_seleccionado['monto'], 
                credito_seleccionado['tea'], 
                credito_seleccionado['plazo']
            )
            
            # ===== CALCULAR SISTEMA ALEMÁN =====
            tabla_alemana = generar_tabla_alemana(
                credito_seleccionado['monto'], 
                credito_seleccionado['tea'], 
                credito_seleccionado['plazo']
            )
            totales_aleman = calcular_totales(tabla_alemana)
            cuota_alemana_primera = tabla_alemana.loc[0, 'cuota']
            cuota_alemana_ultima = tabla_alemana.loc[credito_seleccionado['plazo']-1, 'cuota']
            
            # ===== COMPARACIÓN DE MÉTRICAS =====
            st.subheader("📊 Métricas Comparativas")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Cuota - Francés",
                    formatear_moneda(cuota_francesa),
                    "Constante"
                )
                st.metric(
                    "Cuota - Alemán",
                    f"{formatear_moneda(cuota_alemana_primera)} → {formatear_moneda(cuota_alemana_ultima)}",
                    "Decreciente"
                )
            
            with col2:
                diferencia_interes = totales_frances['total_intereses'] - totales_aleman['total_intereses']
                st.metric(
                    "Interés Total - Francés",
                    formatear_moneda(totales_frances['total_intereses'])
                )
                st.metric(
                    "Interés Total - Alemán",
                    formatear_moneda(totales_aleman['total_intereses']),
                    f"-{formatear_moneda(diferencia_interes)}" if diferencia_interes > 0 else formatear_moneda(abs(diferencia_interes))
                )
            
            with col3:
                st.metric(
                    "Total Pagado - Francés",
                    formatear_moneda(totales_frances['total_pagado'])
                )
                st.metric(
                    "Total Pagado - Alemán",
                    formatear_moneda(totales_aleman['total_pagado'])
                )
            
            with col4:
                ahorro_porcentual = (diferencia_interes / totales_frances['total_intereses']) * 100 if totales_frances['total_intereses'] > 0 else 0
                st.metric(
                    "Ahorro con Alemán",
                    formatear_moneda(abs(diferencia_interes)),
                    f"{ahorro_porcentual:.2f}%"
                )
            
            # ===== GRÁFICO COMPARATIVO DE EVOLUCIÓN =====
            st.subheader("📈 Evolución de Cuotas")
            
            fig_evolucion = go.Figure()
            
            # Línea del sistema francés (plana)
            fig_evolucion.add_trace(go.Scatter(
                x=tabla_francesa['mes'],
                y=tabla_francesa['cuota'],
                mode='lines',
                name='Sistema Francés',
                line=dict(color='#667eea', width=3),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.2)'
            ))
            
            # Línea del sistema alemán (decreciente)
            fig_evolucion.add_trace(go.Scatter(
                x=tabla_alemana['mes'],
                y=tabla_alemana['cuota'],
                mode='lines',
                name='Sistema Alemán',
                line=dict(color='#f5576c', width=3),
                fill='tozeroy',
                fillcolor='rgba(245, 87, 108, 0.2)'
            ))
            
            fig_evolucion.update_layout(
                title='Comparación de Cuotas Mensuales: Francés vs Alemán',
                xaxis_title='Mes',
                yaxis_title='Cuota (S/)',
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig_evolucion, use_container_width=True)
            
            # ===== GRÁFICO DE COMPOSICIÓN (INTERÉS VS AMORTIZACIÓN) =====
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown("**Sistema Francés: Composición de Pagos**")
                fig_comp_frances = go.Figure()
                fig_comp_frances.add_trace(go.Bar(
                    x=tabla_francesa['mes'],
                    y=tabla_francesa['interes'],
                    name='Interés',
                    marker_color='#FF6B6B'
                ))
                fig_comp_frances.add_trace(go.Bar(
                    x=tabla_francesa['mes'],
                    y=tabla_francesa['amortizacion'],
                    name='Amortización',
                    marker_color='#4ECDC4'
                ))
                fig_comp_frances.update_layout(
                    barmode='stack',
                    height=350,
                    showlegend=True,
                    xaxis_title='Mes',
                    yaxis_title='Monto (S/)'
                )
                st.plotly_chart(fig_comp_frances, use_container_width=True)
            
            with col_graf2:
                st.markdown("**Sistema Alemán: Composición de Pagos**")
                fig_comp_aleman = go.Figure()
                fig_comp_aleman.add_trace(go.Bar(
                    x=tabla_alemana['mes'],
                    y=tabla_alemana['interes'],
                    name='Interés',
                    marker_color='#FF6B6B'
                ))
                fig_comp_aleman.add_trace(go.Bar(
                    x=tabla_alemana['mes'],
                    y=tabla_alemana['amortizacion'],
                    name='Amortización',
                    marker_color='#4ECDC4'
                ))
                fig_comp_aleman.update_layout(
                    barmode='stack',
                    height=350,
                    showlegend=True,
                    xaxis_title='Mes',
                    yaxis_title='Monto (S/)'
                )
                st.plotly_chart(fig_comp_aleman, use_container_width=True)
            
            # ===== TABLA COMPARATIVA LADO A LADO (primeros 6 meses) =====
            st.subheader("📋 Comparación Detallada (Primeros 6 Meses)")
            
            # Crear DataFrame comparativo
            comparacion_df = pd.DataFrame({
                'Mes': tabla_francesa['mes'].head(6),
                'Cuota Francés': tabla_francesa['cuota'].head(6).apply(formatear_moneda),
                'Interés Francés': tabla_francesa['interes'].head(6).apply(formatear_moneda),
                'Amortización Francés': tabla_francesa['amortizacion'].head(6).apply(formatear_moneda),
                'Cuota Alemán': tabla_alemana['cuota'].head(6).apply(formatear_moneda),
                'Interés Alemán': tabla_alemana['interes'].head(6).apply(formatear_moneda),
                'Amortización Alemán': tabla_alemana['amortizacion'].head(6).apply(formatear_moneda),
            })
            
            st.dataframe(comparacion_df, use_container_width=True)
            
            # ===== RECOMENDACIÓN =====
            st.subheader("🎯 Recomendación")
            
            if diferencia_interes > 0:
                st.success(f"""
                **💡 El Sistema Alemán es más conveniente**
                
                - Ahorras **{formatear_moneda(diferencia_interes)}** en intereses
                - Representa un **{ahorro_porcentual:.2f}%** menos de interés total
                - Aunque la cuota inicial es más alta ({formatear_moneda(cuota_alemana_primera)}), 
                  va disminuyendo mes a mes hasta {formatear_moneda(cuota_alemana_ultima)}
                
                **Ideal si:** Tienes mayor capacidad de pago al inicio o esperas que tus ingresos disminuyan con el tiempo.
                """)
            else:
                st.info(f"""
                **💡 Análisis del Sistema Francés**
                
                - Cuota constante de {formatear_moneda(cuota_francesa)} durante todo el plazo
                - Mayor previsibilidad en tu presupuesto mensual
                - Interés total: {formatear_moneda(totales_frances['total_intereses'])}
                
                **Ideal si:** Prefieres tener una cuota fija y predecible todos los meses.
                """)