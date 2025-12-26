# modulos/recomendador.py
"""
Función para mostrar el recomendador inteligente con IA (Gemini)
"""
import streamlit as st
import google.generativeai as genai
import json
import re


def configurar_gemini():
    """
    Configura la API de Google Gemini usando secrets de Streamlit
    Returns:
        bool: True si la configuración fue exitosa, False en caso contrario
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except KeyError:
        st.error("⚠️ No se encontró la clave de API de Gemini en los secrets.")
        st.info("""
        **Para configurar la API de Gemini:**
        
        📍 **Local (desarrollo):**
        1. Crea un archivo `.streamlit/secrets.toml` en la raíz del proyecto
        2. Agrega: `GEMINI_API_KEY = "tu-api-key-aqui"`
        3. Obtén tu API key en: https://makersuite.google.com/app/apikey
        
        ☁️ **Streamlit Cloud (producción):**
        1. Ve a tu app en: https://share.streamlit.io/
        2. Click en tu app → ⚙️ Settings → Secrets
        3. Agrega en el editor:
           ```
           GEMINI_API_KEY = "tu-api-key-aqui"
           ```
        4. Click en "Save"
        5. La app se reiniciará automáticamente
        
        🔑 **Obtener API Key:** https://makersuite.google.com/app/apikey
        """)
        return False
    except Exception as e:
        st.error(f"Error al configurar Gemini: {str(e)}")
        return False


def validar_datos_entrada(datos_credito: dict, perfil_usuario: dict) -> tuple[bool, str]:
    """
    Valida los datos de entrada antes de realizar análisis
    """
    errores = []
    
    if datos_credito['monto'] <= 0:
        errores.append("El monto del crédito debe ser mayor a cero")
    
    if datos_credito['monto'] > 10000000:
        errores.append("El monto del crédito es irreal (máximo S/ 10,000,000)")
    
    if datos_credito['plazo'] <= 0:
        errores.append("El plazo debe ser mayor a cero")
    
    if datos_credito['plazo'] > 480:
        errores.append("El plazo es irreal (máximo 480 meses / 40 años)")
    
    if datos_credito['tea'] < 0 or datos_credito['tea'] > 300:
        errores.append("La TEA debe estar entre 0% y 300%")
    
    if datos_credito['tcea'] < 0 or datos_credito['tcea'] > 400:
        errores.append("La TCEA debe estar entre 0% y 400%")
    
    if datos_credito['tcea'] < datos_credito['tea']:
        errores.append("La TCEA no puede ser menor que la TEA")
    
    if perfil_usuario['edad'] < 18:
        errores.append("Debes ser mayor de edad (18 años)")
    
    if perfil_usuario['edad'] > 100:
        errores.append("La edad ingresada no es válida")
    
    if perfil_usuario['ingresos'] <= 0:
        errores.append("Los ingresos deben ser mayores a cero")
    
    if perfil_usuario['ingresos'] > 1000000:
        errores.append("Los ingresos mensuales parecen irreales (máximo S/ 1,000,000)")
    
    if perfil_usuario['gastos'] < 0:
        errores.append("Los gastos no pueden ser negativos")
    
    if perfil_usuario['gastos'] > perfil_usuario['ingresos'] * 1.5:
        errores.append("Los gastos no pueden superar 1.5 veces los ingresos")
    
    if perfil_usuario['deudas'] < 0:
        errores.append("Las deudas no pueden ser negativas")
    
    if perfil_usuario['deudas'] > perfil_usuario['ingresos'] * 2:
        errores.append("Las deudas mensuales parecen irreales (máximo 2x ingresos)")
    
    disponible_actual = perfil_usuario['ingresos'] - perfil_usuario['gastos'] - perfil_usuario['deudas']
    if disponible_actual < 0:
        errores.append("⚠️ Advertencia: Actualmente tus gastos y deudas superan tus ingresos")
    
    if datos_credito['cuota_mensual'] > perfil_usuario['ingresos']:
        errores.append("La cuota del crédito supera tus ingresos totales")
    
    if datos_credito['plazo'] < 3 and datos_credito['monto'] > 5000:
        errores.append("Plazo muy corto para el monto solicitado")
    
    if datos_credito['plazo'] > 360 and datos_credito['monto'] < 50000:
        errores.append("Plazo excesivo para un monto pequeño (pagarás demasiados intereses)")
    
    if errores:
        return False, "\n".join(f"• {error}" for error in errores)
    
    return True, ""


def obtener_recomendacion_gemini(datos_credito: dict, perfil_usuario: dict) -> dict:
    """
    Envía los datos a Gemini y obtiene una recomendación personalizada
    
    Args:
        datos_credito: Diccionario con información del crédito
        perfil_usuario: Diccionario con el perfil financiero del usuario
    
    Returns:
        dict: Diccionario con la recomendación, advertencias, consejos y nivel de riesgo
    """
    prompt = f"""
    Eres un asesor financiero experto. Analiza la siguiente información y proporciona una recomendación 
    personalizada sobre si el usuario debería tomar este crédito.

    **INFORMACIÓN DEL CRÉDITO:**
    - Monto solicitado: S/ {datos_credito['monto']:,.2f}
    - Plazo: {datos_credito['plazo']} meses
    - TEA (Tasa Efectiva Anual): {datos_credito['tea']}%
    - TCEA (Tasa de Costo Efectivo Anual): {datos_credito['tcea']}%
    - Cuota mensual estimada: S/ {datos_credito['cuota_mensual']:,.2f}

    **PERFIL DEL USUARIO:**
    - Edad: {perfil_usuario['edad']} años
    - Ingresos mensuales: S/ {perfil_usuario['ingresos']:,.2f}
    - Gastos fijos mensuales: S/ {perfil_usuario['gastos']:,.2f}
    - Deudas actuales (cuota mensual total): S/ {perfil_usuario['deudas']:,.2f}
    - Historial crediticio: {perfil_usuario['historial']}
    - Propósito del crédito: {perfil_usuario['proposito']}

    **CÁLCULOS ADICIONALES:**
    - Ingreso disponible después de gastos y deudas: S/ {perfil_usuario['ingresos'] - perfil_usuario['gastos'] - perfil_usuario['deudas']:,.2f}
    - Ratio de endeudamiento actual: {((perfil_usuario['deudas'] / perfil_usuario['ingresos']) * 100) if perfil_usuario['ingresos'] > 0 else 0:.1f}%
    - Ratio de endeudamiento con nuevo crédito: {(((perfil_usuario['deudas'] + datos_credito['cuota_mensual']) / perfil_usuario['ingresos']) * 100) if perfil_usuario['ingresos'] > 0 else 0:.1f}%

    Responde SOLO con este JSON (sin markdown, sin texto adicional, sin ```json):
    {{
        "recomendacion": "Tu recomendación clara sobre si debe o no tomar el crédito, con justificación",
        "nivel_riesgo": "BAJO o MEDIO o ALTO o MUY ALTO",
        "advertencias": ["advertencia 1", "advertencia 2", "advertencia 3"],
        "consejos": ["consejo 1", "consejo 2", "consejo 3"],
        "resumen": "Un párrafo breve con el resumen final"
    }}
    """

    try:
        # Usar modelos disponibles actualizados (Gemini 2.5 y superiores)
        modelos_disponibles = [
            'models/gemini-3-flash',  # Modelo más rápido y eficiente
            'models/gemini-2.5-flash'
        ]
        
        ultima_excepcion = None
        
        for nombre_modelo in modelos_disponibles:
            try:
                model = genai.GenerativeModel(nombre_modelo)
                response = model.generate_content(prompt)
                
                texto_respuesta = response.text.strip()
                
                resultado = parsear_respuesta_json(texto_respuesta)
                resultado['respuesta_completa'] = texto_respuesta
                resultado['exito'] = True
                resultado['modelo_usado'] = nombre_modelo
                
                return resultado
            except Exception as e:
                ultima_excepcion = e
                continue
        
        # Si ningún modelo funcionó, retornar el último error
        raise ultima_excepcion
        
    except Exception as e:
        return {
            'exito': False,
            'error': str(e),
            'recomendacion': '',
            'nivel_riesgo': '',
            'advertencias': [],
            'consejos': [],
            'resumen': ''
        }


def parsear_respuesta_gemini(texto: str) -> dict:
    """
    Parsea la respuesta de Gemini para extraer las secciones
    
    Args:
        texto: Texto de respuesta de Gemini
    
    Returns:
        dict: Diccionario con las secciones parseadas
    """
    resultado = {
        'recomendacion': '',
        'nivel_riesgo': 'NO DETERMINADO',
        'advertencias': [],
        'consejos': [],
        'resumen': ''
    }
    
    secciones = {
        'RECOMENDACIÓN:': 'recomendacion',
        'NIVEL DE RIESGO:': 'nivel_riesgo',
        'ADVERTENCIAS:': 'advertencias',
        'CONSEJOS FINANCIEROS:': 'consejos',
        'RESUMEN:': 'resumen'
    }
    
    texto_upper = texto.upper()
    posiciones = []
    
    for encabezado in secciones.keys():
        pos = texto_upper.find(encabezado.upper())
        if pos != -1:
            posiciones.append((pos, encabezado))
    
    posiciones.sort(key=lambda x: x[0])
    
    for i, (pos, encabezado) in enumerate(posiciones):
        inicio = pos + len(encabezado)
        if i + 1 < len(posiciones):
            fin = posiciones[i + 1][0]
        else:
            fin = len(texto)
        
        contenido = texto[inicio:fin].strip()
        campo = secciones[encabezado]
        
        if campo in ['advertencias', 'consejos']:
            lineas = [l.strip().lstrip('-•*').strip() for l in contenido.split('\n') if l.strip() and l.strip() not in ['', '-']]
            resultado[campo] = [l for l in lineas if l]
        else:
            resultado[campo] = contenido
    
    return resultado


def parsear_respuesta_json(texto: str) -> dict:
    """
    Parsea la respuesta JSON de Gemini con fallback robusto
    """
    resultado_default = {
        'recomendacion': '',
        'nivel_riesgo': 'NO DETERMINADO',
        'advertencias': [],
        'consejos': [],
        'resumen': ''
    }
    
    try:
        texto_limpio = texto.strip()
        texto_limpio = re.sub(r'```json\s*', '', texto_limpio)
        texto_limpio = re.sub(r'```\s*', '', texto_limpio)
        texto_limpio = texto_limpio.strip()
        
        datos = json.loads(texto_limpio)
        
        resultado_default['recomendacion'] = datos.get('recomendacion', '')
        resultado_default['nivel_riesgo'] = datos.get('nivel_riesgo', 'NO DETERMINADO')
        resultado_default['advertencias'] = datos.get('advertencias', [])
        resultado_default['consejos'] = datos.get('consejos', [])
        resultado_default['resumen'] = datos.get('resumen', '')
        
        if not isinstance(resultado_default['advertencias'], list):
            resultado_default['advertencias'] = [str(resultado_default['advertencias'])]
        if not isinstance(resultado_default['consejos'], list):
            resultado_default['consejos'] = [str(resultado_default['consejos'])]
        
        return resultado_default
        
    except json.JSONDecodeError:
        try:
            match = re.search(r'\{[\s\S]*\}', texto)
            if match:
                datos = json.loads(match.group(0))
                resultado_default['recomendacion'] = datos.get('recomendacion', '')
                resultado_default['nivel_riesgo'] = datos.get('nivel_riesgo', 'NO DETERMINADO')
                resultado_default['advertencias'] = datos.get('advertencias', [])
                resultado_default['consejos'] = datos.get('consejos', [])
                resultado_default['resumen'] = datos.get('resumen', '')
                
                if not isinstance(resultado_default['advertencias'], list):
                    resultado_default['advertencias'] = [str(resultado_default['advertencias'])]
                if not isinstance(resultado_default['consejos'], list):
                    resultado_default['consejos'] = [str(resultado_default['consejos'])]
                
                return resultado_default
        except:
            pass
        
        try:
            resultado_default['recomendacion'] = texto[:500] if texto else "No se pudo generar recomendación"
            resultado_default['consejos'] = ["Revisa tu capacidad de pago", "Compara opciones de crédito"]
            resultado_default['advertencias'] = ["Consulta con un asesor financiero profesional"]
            resultado_default['resumen'] = "Análisis no disponible por error en el parsing"
            return resultado_default
        except:
            return resultado_default


def calcular_cuota_mensual(monto: float, tea: float, plazo: int) -> float:
    """
    Calcula la cuota mensual aproximada usando el sistema francés
    
    Args:
        monto: Monto del préstamo
        tea: Tasa efectiva anual en porcentaje
        plazo: Plazo en meses
    
    Returns:
        float: Cuota mensual estimada
    """
    if tea <= 0 or plazo <= 0:
        return monto / plazo if plazo > 0 else 0
    
    tem = (1 + tea / 100) ** (1/12) - 1
    
    cuota = monto * (tem * (1 + tem) ** plazo) / ((1 + tem) ** plazo - 1)
    
    return cuota


def obtener_color_riesgo(nivel: str) -> str:
    """
    Retorna el color asociado al nivel de riesgo
    """
    nivel_upper = nivel.upper()
    if 'BAJO' in nivel_upper:
        return 'green'
    elif 'MEDIO' in nivel_upper:
        return 'orange'
    elif 'MUY ALTO' in nivel_upper:
        return 'red'
    elif 'ALTO' in nivel_upper:
        return 'red'
    return 'gray'


def mostrar_recomendador_inteligente():
    """
    Muestra la interfaz del recomendador inteligente con IA
    """
    st.title("🎯 Recomendador Inteligente")
    st.write("Encuentra el crédito perfecto según tus necesidades usando Inteligencia Artificial")
    
    st.divider()
    
    if not configurar_gemini():
        return
    
    st.success("✅ API de Gemini configurada correctamente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("� Información del Crédito")
        
        monto = st.number_input(
            "Monto del crédito (S/)",
            min_value=100.0,
            max_value=1000000.0,
            value=10000.0,
            step=500.0,
            help="Monto total del préstamo que deseas solicitar"
        )
        
        plazo = st.number_input(
            "Plazo (meses)",
            min_value=1,
            max_value=360,
            value=12,
            step=1,
            help="Duración del préstamo en meses"
        )
        
        tea = st.number_input(
            "TEA - Tasa Efectiva Anual (%)",
            min_value=0.0,
            max_value=200.0,
            value=15.0,
            step=0.5,
            help="Tasa de interés efectiva anual"
        )
        
        tcea = st.number_input(
            "TCEA - Tasa de Costo Efectivo Anual (%)",
            min_value=0.0,
            max_value=250.0,
            value=18.0,
            step=0.5,
            help="Incluye todos los costos asociados al crédito"
        )
        
        cuota_mensual = calcular_cuota_mensual(monto, tea, plazo)
        st.info(f"📊 **Cuota mensual estimada:** S/ {cuota_mensual:,.2f}")
    
    with col2:
        st.subheader("👤 Perfil Financiero")
        
        edad = st.number_input(
            "Edad",
            min_value=18,
            max_value=100,
            value=30,
            step=1
        )
        
        ingresos = st.number_input(
            "Ingresos mensuales (S/)",
            min_value=0.0,
            max_value=500000.0,
            value=3000.0,
            step=100.0,
            help="Ingresos netos mensuales"
        )
        
        gastos = st.number_input(
            "Gastos fijos mensuales (S/)",
            min_value=0.0,
            max_value=500000.0,
            value=1500.0,
            step=100.0,
            help="Gastos fijos como vivienda, alimentación, servicios, etc."
        )
        
        deudas = st.number_input(
            "Deudas actuales - cuota mensual total (S/)",
            min_value=0.0,
            max_value=500000.0,
            value=0.0,
            step=50.0,
            help="Suma de cuotas mensuales de deudas existentes"
        )
        
        historial = st.selectbox(
            "Historial crediticio",
            options=[
                "Excelente - Sin morosidad, buen pagador",
                "Bueno - Pagos puntuales en general",
                "Regular - Algunos atrasos menores",
                "Malo - Morosidad frecuente",
                "Sin historial - Primera vez solicitando crédito"
            ],
            help="Tu historial de pagos de créditos anteriores"
        )
        
        proposito = st.selectbox(
            "Propósito del crédito",
            options=[
                "Negocio o emprendimiento",
                "Compra de vehículo",
                "Mejoras del hogar",
                "Educación",
                "Consolidación de deudas",
                "Gastos médicos",
                "Viaje o vacaciones",
                "Compras personales",
                "Emergencia",
                "Otro"
            ]
        )
    
    st.divider()
    
    disponible = ingresos - gastos - deudas
    ratio_endeudamiento = (deudas / ingresos * 100) if ingresos > 0 else 0
    ratio_con_credito = ((deudas + cuota_mensual) / ingresos * 100) if ingresos > 0 else 0
    
    st.subheader("📈 Resumen de tu Situación Financiera")
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.metric("Disponible mensual", f"S/ {disponible:,.2f}")
    with col_b:
        st.metric("Ratio endeudamiento actual", f"{ratio_endeudamiento:.1f}%")
    with col_c:
        st.metric("Ratio con nuevo crédito", f"{ratio_con_credito:.1f}%", 
                  delta=f"+{ratio_con_credito - ratio_endeudamiento:.1f}%")
    
    st.divider()
    
    if st.button("🤖 Obtener Recomendación con IA", type="primary", use_container_width=True):
        
        datos_credito = {
            'monto': monto,
            'plazo': plazo,
            'tea': tea,
            'tcea': tcea,
            'cuota_mensual': cuota_mensual
        }
        
        perfil_usuario = {
            'edad': edad,
            'ingresos': ingresos,
            'gastos': gastos,
            'deudas': deudas,
            'historial': historial,
            'proposito': proposito
        }
        
        # Validar datos antes de llamar a Gemini
        es_valido, mensaje_error = validar_datos_entrada(datos_credito, perfil_usuario)
        
        if not es_valido:
            st.error("❌ **Datos inválidos detectados:**")
            st.warning(mensaje_error)
            st.info("💡 Por favor, revisa los datos ingresados y asegúrate de que sean realistas y coherentes.")
        else:
            with st.spinner("🔄 Analizando tu perfil con Inteligencia Artificial..."):
                resultado = obtener_recomendacion_gemini(datos_credito, perfil_usuario)
            
            if resultado['exito']:
                st.success(f"✅ Análisis completado (Modelo: {resultado.get('modelo_usado', 'N/A')})")
                
                st.subheader("📋 Resultado del Análisis")
                
                color_riesgo = obtener_color_riesgo(resultado['nivel_riesgo'])
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; border-left: 5px solid {color_riesgo}; background-color: rgba(0,0,0,0.05);">
                    <h3>Nivel de Riesgo: <span style="color: {color_riesgo};">{resultado['nivel_riesgo']}</span></h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 💡 Recomendación")
                st.write(resultado['recomendacion'])
                
                col_adv, col_cons = st.columns(2)
                
                with col_adv:
                    st.markdown("### ⚠️ Advertencias")
                    if resultado['advertencias']:
                        for adv in resultado['advertencias']:
                            st.warning(f"• {adv}")
                    else:
                        st.info("No se identificaron advertencias específicas.")
                
                with col_cons:
                    st.markdown("### 📚 Consejos Financieros")
                    if resultado['consejos']:
                        for consejo in resultado['consejos']:
                            st.info(f"• {consejo}")
                    else:
                        st.info("No hay consejos adicionales.")
                
                st.markdown("### 📝 Resumen")
                st.write(resultado['resumen'])
            
            else:
                st.error(f"❌ Error al obtener la recomendación: {resultado.get('error', 'Error desconocido')}")
                st.info("Por favor, verifica tu conexión a internet y la configuración de la API de Gemini.")
    
    st.divider()
    st.caption("⚠️ **Disclaimer:** Esta herramienta utiliza Inteligencia Artificial para proporcionar recomendaciones generales. No constituye asesoría financiera profesional. Consulta con un experto financiero antes de tomar decisiones importantes.")