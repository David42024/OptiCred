# modules/simulador.py
"""
Función para mostrar el simulador de pagos extraordinarios con tasas SBS
"""
import streamlit as st
import pandas as pd
import altair as alt
from modules.amortizacion import generar_tabla_francesa
from modules.simulaciones import (
    simular_pago_extraordinario, 
    simular_pagos_recurrentes, 
    comparar_estrategias_prepago
)

# Importar API de tasas 
try:
    from modules.api_tasas import (
        APITasas,
        cargar_datos_api,
        CATEGORIAS_CREDITO
    )
    API_DISPONIBLE = True
except ImportError:
    API_DISPONIBLE = False
    CATEGORIAS_CREDITO = {
        "Consumo": {
            "descripcion": "Créditos para personas naturales",
            "opciones": {"Libre Disponibilidad (más de 360 días)": "Préstamos no Revolventes"}
        }
    }

def mostrar_simulador_pagos():
    """
    Muestra la interfaz del simulador de pagos extraordinarios
    """
    st.title("🔄 Simulador de Pagos Extraordinarios")
    st.markdown("Descubre cuánto puedes ahorrar haciendo pagos adicionales a tu crédito.")
    
    # --- Inicializar Session State ---
    if 'credito_monto' not in st.session_state:
        st.session_state.credito_monto = 50000.0
    if 'credito_tea' not in st.session_state:
        st.session_state.credito_tea = 15.0
    if 'credito_plazo' not in st.session_state:
        st.session_state.credito_plazo = 24
    
    # ========== CARGAR DATOS DE LA API ==========
    api_conectada = False
    api_tasas = None
    
    if API_DISPONIBLE:
        with st.spinner("🔄 Conectando con tasas actualizadas de la SBS..."):
            df_tasas, df_bancos, api_conectada = cargar_datos_api()
            
            if api_conectada:
                api_tasas = APITasas()
                api_tasas._tasas_activas = df_tasas
                api_tasas._bancos = df_bancos
                api_tasas._cache_cargado = True
                api_tasas._construir_indice_categorias()
    
    # Estado de conexión
    if api_conectada:
        st.success("✅ **Conectado a la SBS** — Tasas actualizadas en tiempo real")
    else:
        st.warning("⚠️ **Modo offline** — Usando tasas de referencia")
    
    st.divider()
    
    # --- Configuración del Crédito Base ---
    with st.sidebar:
        st.header("1. Datos del Crédito")
        
        # Opción para cargar desde calculadora
        if st.checkbox("📋 Usar datos de sesión anterior", help="Carga automáticamente los datos si calculaste un crédito previamente"):
            st.info("✅ Usando datos guardados en sesión")
        
        st.divider()
        
        # Selector de tipo de crédito (si API está conectada)
        if api_conectada:
            st.subheader("📊 Tipo de Crédito")
            
            categoria_credito = st.selectbox(
                "🏢 **Tipo de Cliente**",
                list(CATEGORIAS_CREDITO.keys()),
                index=5 if "Consumo" in CATEGORIAS_CREDITO else 0,
                help="Selecciona según tu perfil"
            )
            
            if categoria_credito in CATEGORIAS_CREDITO:
                st.caption(f"ℹ️ {CATEGORIAS_CREDITO[categoria_credito]['descripcion']}")
            
            opciones_producto = list(CATEGORIAS_CREDITO[categoria_credito]["opciones"].keys())
            tipo_producto = st.selectbox(
                "💳 **Producto Crediticio**",
                opciones_producto,
                help="Tipo específico de préstamo"
            )
            
            # Obtener promedio del mercado
            promedio_mercado = api_tasas.get_promedio(tipo_producto, categoria_credito)
            mejor_banco, mejor_tasa = api_tasas.get_mejor_tasa(tipo_producto, categoria_credito)
            
            st.info(f"📊 TEA Promedio del mercado: **{promedio_mercado:.2f}%**")
            st.caption(f"🏆 Mejor tasa: {mejor_banco} ({mejor_tasa:.2f}%)")
            
            # Usar promedio como default
            st.session_state.credito_tea = promedio_mercado
            
            st.divider()
        
        monto = st.number_input(
            "Monto del Préstamo (S/)", 
            min_value=1000.0, 
            value=st.session_state.credito_monto, 
            step=1000.0,
            key="input_monto"
        )
        tea = st.number_input(
            "Tasa Efectiva Anual (TEA %)", 
            min_value=1.0, 
            max_value=200.0, 
            value=st.session_state.credito_tea, 
            step=0.1,
            key="input_tea"
        )
        plazo = st.number_input(
            "Plazo Original (meses)", 
            min_value=6, 
            max_value=360, 
            value=st.session_state.credito_plazo, 
            step=6,
            key="input_plazo"
        )
        
        # Actualizar session state
        st.session_state.credito_monto = monto
        st.session_state.credito_tea = tea
        st.session_state.credito_plazo = plazo
        
        st.info(f"Cuota aprox. original: S/ {generar_tabla_francesa(monto, tea/100, plazo).iloc[0]['cuota']:,.2f}")

    # Pestañas para los diferentes modos
    tab1, tab2, tab3 = st.tabs(["💰 Pago Único", "📅 Pagos Recurrentes", "📊 Comparar Estrategias"])
    
    # --- TAB 1: PAGO ÚNICO ---
    with tab1:
        st.subheader("Simulación de Pago Único (Prepago)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mes_prepago = st.number_input("¿En qué mes harás el pago?", min_value=1, max_value=plazo-1, value=6)
        with col2:
            monto_prepago = st.number_input("Monto del pago extra (S/)", min_value=100.0, value=5000.0, step=100.0)
        with col3:
            tipo_reduccion = st.selectbox(
                "Tipo de Reducción", 
                ["Plazo", "Cuota"], 
                help="Plazo: Terminas antes. Cuota: Pagas menos cada mes."
            )

        if st.button("Simular Pago Único", type="primary"):
            # Generar tabla base
            tabla_base = generar_tabla_francesa(monto, tea/100, plazo)
            
            # Simular
            resultado = simular_pago_extraordinario(tabla_base, mes_prepago, monto_prepago, tea/100, tipo_reduccion)
            
            if resultado:
                resumen = resultado['resumen']
                tabla_nueva = resultado['tabla_actualizada']
                
                # Métricas Clave - DINÁMICAS según tipo de reducción
                st.divider()
                
                if tipo_reduccion == "Plazo":
                    # Mostrar meses ahorrados
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Ahorro Intereses", f"S/ {resumen['ahorro_intereses']:,.2f}")
                    m2.metric("Meses Ahorrados", f"{resumen['meses_ahorrados']} meses", delta=f"-{resumen['meses_ahorrados']}")
                    m3.metric("Nuevo Plazo", f"{resumen['nuevo_plazo']} meses")
                    m4.metric("Total Intereses Nuevo", f"S/ {resumen['interes_nuevo']:,.2f}")
                else:
                    # Mostrar reducción de cuota
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Ahorro Intereses", f"S/ {resumen['ahorro_intereses']:,.2f}")
                    m2.metric("Cuota Original", f"S/ {resumen['cuota_original']:,.2f}")
                    m3.metric("Nueva Cuota", f"S/ {resumen['cuota_nueva']:,.2f}", delta=f"-{resumen['cuota_original'] - resumen['cuota_nueva']:.2f}")
                    m4.metric("Total Intereses Nuevo", f"S/ {resumen['interes_nuevo']:,.2f}")
                
                # Gráficos
                st.subheader("Visualización del Impacto")
                
                # Gráfico de Saldo Deudor
                chart_data = pd.DataFrame({
                    'Mes': range(1, len(tabla_base) + 1),
                    'Saldo Original': tabla_base['saldo_final'],
                })
                # Add new balance, padding with 0 if shorter
                new_balance = tabla_nueva['saldo_final'].tolist()
                new_balance += [0] * (len(chart_data) - len(new_balance))
                chart_data['Nuevo Saldo'] = new_balance[:len(chart_data)]
                
                chart_melted = chart_data.melt('Mes', var_name='Escenario', value_name='Saldo')
                
                c = alt.Chart(chart_melted).mark_line().encode(
                    x='Mes',
                    y='Saldo',
                    color='Escenario'
                ).interactive()
                
                st.altair_chart(c, use_container_width=True)
                
                with st.expander("Ver Nueva Tabla de Amortización"):
                    st.dataframe(tabla_nueva)
            else:
                st.error("Error en la simulación. Verifica el mes de pago.")

    # --- TAB 2: PAGOS RECURRENTES ---
    with tab2:
        st.subheader("Simulación de Pagos Mensuales Adicionales")
        col1, col2 = st.columns(2)
        with col1:
            mes_inicio = st.number_input("Empezar desde el mes:", min_value=1, max_value=plazo-1, value=1)
        with col2:
            extra_mensual = st.number_input("Monto extra mensual (S/)", min_value=50.0, value=200.0, step=50.0)
            
        if st.button("Simular Recurrente"):
            df_recurr = simular_pagos_recurrentes(monto, tea/100, plazo, extra_mensual, mes_inicio)
            
            # Comparar con Original
            tabla_base = generar_tabla_francesa(monto, tea/100, plazo)
            interes_orig = tabla_base['interes'].sum()
            interes_new = df_recurr['interes'].sum()
            ahorro = interes_orig - interes_new
            meses_ahorrados = len(tabla_base) - len(df_recurr)
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Ahorro Intereses", f"S/ {ahorro:,.2f}")
            c2.metric("Plazo Original", f"{len(tabla_base)} meses")
            c3.metric("Nuevo Plazo", f"{len(df_recurr)} meses", f"-{meses_ahorrados} meses")
            
            st.altair_chart(
                alt.Chart(df_recurr).mark_bar().encode(
                    x='mes',
                    y='saldo_final',
                    tooltip=['mes', 'saldo_final', 'interes', 'amortizacion']
                ).interactive(),
                use_container_width=True
            )

    # --- TAB 3: ESTRATEGIAS ---
    with tab3:
        st.subheader("Comparación de Estrategias")
        st.markdown("Si tienes un presupuesto anual extra (ej. gratificación, utilidades), ¿qué conviene más?")
        
        presupuesto = st.number_input("Presupuesto Anual Extra Disponible (S/)", min_value=1000.0, value=2400.0, step=100.0)
        
        if st.button("Comparar Estrategias"):
            resultados_est = comparar_estrategias_prepago(monto, tea/100, plazo, presupuesto)
            
            # Mejor opción
            mejor = resultados_est.sort_values('interes_total').iloc[0]
            st.success(f"🏆 La mejor estrategia es: **{mejor['nombre']}** con un ahorro de S/ {mejor['ahorro']:,.2f}")
            
            # Gráfico de Barras
            c = alt.Chart(resultados_est).mark_bar().encode(
                x=alt.X('nombre', sort=None, title="Estrategia"),
                y=alt.Y('interes_total', title="Intereses Totales (S/)"),
                color='nombre',
                tooltip=['nombre', 'interes_total', 'ahorro', 'plazo']
            )
            st.altair_chart(c, use_container_width=True)
            
            st.dataframe(resultados_est.style.format({
                'interes_total': "{:,.2f}",
                'ahorro': "{:,.2f}"
            }))