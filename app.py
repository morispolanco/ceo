import streamlit as st
import google.generativeai as genai
import random
import json
import time
import copy
import pandas as pd
import io

# Configure Google Gemini API
genai.configure(api_key=st.secrets["gemini"]["api_key"])
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize session state
if "company" not in st.session_state:
    st.session_state.company = None
if "round" not in st.session_state:
    st.session_state.round = 0
if "history" not in st.session_state:
    st.session_state.history = []
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "decision_made" not in st.session_state:
    st.session_state.decision_made = False
if "decision_result" not in st.session_state:
    st.session_state.decision_result = None
if "initial_company" not in st.session_state:
    st.session_state.initial_company = None
if "difficulty" not in st.session_state:
    st.session_state.difficulty = "Medium"

# Function to reset the game
def reset_game():
    keys = ["company", "round", "history", "game_over", "decision_made", "decision_result", "initial_company", "current_challenge", "difficulty"]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Function to generate initial company profile using Gemini API with retries
def generate_company_profile(max_retries=3):
    prompt = """
    Genera un perfil detallado en español de una empresa mediana estable. Incluye exactamente los siguientes campos en formato JSON:
    - "products": Descripción de productos o servicios ofrecidos (texto).
    - "inventory": Descripción general del inventario (texto).
    - "capital": Capital inicial en USD (número entero).
    - "employees": Número de empleados (número entero).
    - "personnel": Lista de objetos con "name" (nombre completo) y "role" (rol en la empresa). Incluye al menos: gerente comercial, gerente financiero, gerente de recursos humanos, gerente de relaciones públicas, gerente de marketing, gerente de operaciones, y otros puestos relevantes.
    Ejemplo:
    {
      "products": "Software de gestión empresarial",
      "inventory": "Licencias de software y servidores",
      "capital": 500000,
      "employees": 50,
      "personnel": [
        {"name": "Ana López", "role": "Gerente Comercial"},
        {"name": "Carlos Pérez", "role": "Gerente Financiero"},
        ...
      ]
    }
    Devuelve solo el JSON, sin texto adicional.
    """
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return json.loads(response.text.strip("```json\n").strip("```"))
        except (json.JSONDecodeError, Exception) as e:
            if attempt == max_retries - 1:
                st.error("No se pudo generar el perfil de la empresa. Usando datos predeterminados.")
                return {
                    "products": "Productos genéricos",
                    "inventory": "Inventario estándar",
                    "capital": 500000,
                    "employees": 50,
                    "personnel": [
                        {"name": "Juan García", "role": "Gerente General"},
                        {"name": "María Rodríguez", "role": "Gerente Comercial"},
                        {"name": "Luis Fernández", "role": "Gerente Financiero"}
                    ]
                }
            time.sleep(2 ** attempt)
    return None

# Function to format company profile as plain text
def format_company_profile(company):
    personnel_list = company.get("personnel", [])
    personnel_text = "\n".join([f"- {person['name']}: {person['role']}" for person in personnel_list]) if personnel_list else "- No se proporcionó información de personal clave."
    
    return f"""
    **Productos o Servicios**: {company.get('products', 'No disponible')}
    **Inventario**: {company.get('inventory', 'No disponible')}
    **Capital**: ${company.get('capital', 0):,}
    **Número de Empleados**: {company.get('employees', 0)}
    **Satisfacción de Empleados**: {company.get('satisfaction', 0)}%
    **Satisfacción de Clientes**: {company.get('customer_satisfaction', 0)}%
    **Cuota de Mercado**: {company.get('market_share', 0)}%
    **Personal Clave**:
    {personnel_text}
    """

# Function to generate a challenge using Gemini API with retries
def generate_challenge(company, max_retries=3):
    prompt = f"""
    Eres un simulador de negocios. Basándote en la siguiente empresa:
    - Productos: {company.get('products', 'No disponible')}
    - Inventario: {company.get('inventory', 'No disponible')}
    - Capital: ${company.get('capital', 0)}
    - Empleados: {company.get('employees', 0)}
    - Satisfacción de Clientes: {company.get('customer_satisfaction', 0)}%
    - Cuota de Mercado: {company.get('market_share', 0)}%
    Genera un desafío realista en español que enfrente el CEO, con 4 opciones de respuesta (una claramente mejor, una neutral, dos negativas). Incluye:
    - Descripción del desafío
    - 4 opciones de respuesta (etiquetadas A, B, C, D)
    - La opción correcta (letra)
    - Explicación de por qué la opción correcta es la mejor y las consecuencias de cada opción
    Devuelve la respuesta en formato JSON.
    Ejemplo:
    {{
      "description": "Un cliente importante está insatisfecho...",
      "options": {{
        "A": "Ofrecer un descuento...",
        "B": "Ignorar el problema...",
        "C": "Aumentar precios...",
        "D": "Cambiar el producto..."
      }},
      "correct_option": "A",
      "explanation": "A es la mejor opción porque..."
    }}
    """
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return json.loads(response.text.strip("```json\n").strip("```"))
        except (json.JSONDecodeError, Exception) as e:
            if attempt == max_retries - 1:
                st.error("No se pudo generar el desafío. Usando desafío predeterminado.")
                return {
                    "description": "Un competidor ha lanzado un producto similar a menor precio.",
                    "options": {
                        "A": "Invertir en marketing para destacar la calidad.",
                        "B": "Mantener precios y observar el mercado.",
                        "C": "Reducir calidad para bajar costos.",
                        "D": "Aumentar precios para parecer premium."
                    },
                    "correct_option": "A",
                    "explanation": "A es la mejor opción porque refuerza la propuesta de valor. B es neutral pero arriesgado. C daña la reputación. D aleja clientes."
                }
            time.sleep(2 ** attempt)
    return None

# Function to update company state based on decision with difficulty-based impacts
def update_company_state(company, choice, challenge):
    correct = challenge["correct_option"]
    difficulty_multipliers = {
        "Easy": {"capital": 0.5, "satisfaction": 0.5, "customer_satisfaction": 0.5, "market_share": 0.5},
        "Medium": {"capital": 1.0, "satisfaction": 1.0, "customer_satisfaction": 1.0, "market_share": 1.0},
        "Hard": {"capital": 1.5, "satisfaction": 1.5, "customer_satisfaction": 1.5, "market_share": 1.5}
    }
    multiplier = difficulty_multipliers[st.session_state.difficulty]
    
    impacts = {
        "A": {"capital": 0, "employees": 0, "satisfaction": 0, "customer_satisfaction": 0, "market_share": 0},
        "B": {"capital": 0, "employees": 0, "satisfaction": 0, "customer_satisfaction": 0, "market_share": 0},
        "C": {"capital": 0, "employees": 0, "satisfaction": 0, "customer_satisfaction": 0, "market_share": 0},
        "D": {"capital": 0, "employees": 0, "satisfaction": 0, "customer_satisfaction": 0, "market_share": 0},
    }
    if choice == correct:
        impacts[choice] = {
            "capital": int(company["capital"] * random.uniform(0.01, 0.05) * multiplier["capital"]),
            "employees": random.randint(0, 1),
            "satisfaction": random.randint(3, 8) * multiplier["satisfaction"],
            "customer_satisfaction": random.randint(3, 8) * multiplier["customer_satisfaction"],
            "market_share": random.uniform(0.5, 2.0) * multiplier["market_share"]
        }
    else:
        impacts[choice] = {
            "capital": -int(company["capital"] * random.uniform(0.01, 0.05) * multiplier["capital"]),
            "employees": -random.randint(0, 1),
            "satisfaction": -random.randint(5, 10) * multiplier["satisfaction"],
            "customer_satisfaction": -random.randint(5, 10) * multiplier["customer_satisfaction"],
            "market_share": -random.uniform(0.5, 2.0) * multiplier["market_share"]
        }
    
    company["capital"] = max(1000, company.get("capital", 0) + impacts[choice]["capital"])
    company["employees"] = max(1, company.get("employees", 0) + impacts[choice]["employees"])
    company["satisfaction"] = max(0, min(100, company.get("satisfaction", 0) + impacts[choice]["satisfaction"]))
    company["customer_satisfaction"] = max(0, min(100, company.get("customer_satisfaction", 0) + impacts[choice]["customer_satisfaction"]))
    company["market_share"] = max(0, min(100, company.get("market_share", 0) + impacts[choice]["market_share"]))
    
    if (company["capital"] <= 10000 and company["satisfaction"] <= 20) or company["customer_satisfaction"] <= 10 or company["market_share"] <= 5:
        st.session_state.game_over = True
        return "bancarrota"
    return company

# Function to evaluate final state
def evaluate_final_state(initial_company, final_company):
    prompt = f"""
    Compara el estado inicial y final de una empresa:
    Inicial: Capital ${initial_company.get('capital', 0)}, {initial_company.get('employees', 0)} empleados, satisfacción {initial_company.get('satisfaction', 0)}%, satisfacción de clientes {initial_company.get('customer_satisfaction', 0)}%, cuota de mercado {initial_company.get('market_share', 0)}%
    Final: Capital ${final_company.get('capital', 0)}, {final_company.get('employees', 0)} empleados, satisfacción {final_company.get('satisfaction', 0)}%, satisfacción de clientes {final_company.get('customer_satisfaction', 0)}%, cuota de mercado {final_company.get('market_share', 0)}%
    Determina si la empresa mejoró, empeoró o quebró. Explica por qué en español.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "No se pudo evaluar el estado final. Por favor, revisa los datos."

# Function to save game state
def save_game_state():
    state = {
        "company": st.session_state.company,
        "round": st.session_state.round,
        "history": st.session_state.history,
        "game_over": st.session_state.game_over,
        "initial_company": st.session_state.initial_company,
        "difficulty": st.session_state.difficulty
    }
    buffer = io.BytesIO()
    buffer.write(json.dumps(state, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)
    return buffer

# Function to load game state
def load_game_state(uploaded_file):
    try:
        state = json.loads(uploaded_file.read().decode('utf-8'))
        st.session_state.company = state["company"]
        st.session_state.round = state["round"]
        st.session_state.history = state["history"]
        st.session_state.game_over = state["game_over"]
        st.session_state.initial_company = state["initial_company"]
        st.session_state.difficulty = state.get("difficulty", "Medium")
        st.session_state.decision_made = False
        st.session_state.decision_result = None
        if "current_challenge" in st.session_state:
            del st.session_state.current_challenge
        st.rerun()
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")

# Streamlit app
st.title("Simulación de Negocios")

# Sidebar for navigation
st.sidebar.header("Navegación")
page = st.sidebar.radio("Ir a", ["Inicio", "Simulación", "Resultados"])
st.sidebar.button("Reiniciar Simulación", on_click=reset_game)

# Save/Load in sidebar
st.sidebar.header("Guardar/Cargar")
if st.session_state.company:
    st.sidebar.download_button(
        label="Guardar Juego",
        data=save_game_state(),
        file_name="business_simulation.json",
        mime="application/json"
    )
uploaded_file = st.sidebar.file_uploader("Cargar Juego", type=["json"])
if uploaded_file:
    load_game_state(uploaded_file)

if page == "Inicio":
    st.header("Bienvenido a la Simulación de Negocios")
    st.write("Toma el rol de CEO de una empresa mediana. Tu objetivo es tomar decisiones estratégicas para mejorar la empresa a lo largo de 20 rondas.")
    
    # Difficulty selection
    st.session_state.difficulty = st.selectbox(
        "Selecciona la dificultad",
        ["Easy", "Medium", "Hard"],
        index=["Easy", "Medium", "Hard"].index(st.session_state.difficulty)
    )
    
    if st.button("Iniciar Simulación"):
        # Generate company profile
        company = generate_company_profile()
        if company:
            company["satisfaction"] = 70
            company["customer_satisfaction"] = 70
            company["market_share"] = 20
            st.session_state.company = company
            st.session_state.initial_company = copy.deepcopy(company)
            st.session_state.round = 0
            st.session_state.history = []
            st.session_state.game_over = False
            st.session_state.decision_made = False
            st.session_state.decision_result = None
            st.rerun()
    
    if st.session_state.company:
        st.subheader("Perfil Inicial de la Empresa")
        st.markdown(format_company_profile(st.session_state.company))

elif page == "Simulación":
    if not st.session_state.company:
        st.warning("Por favor, inicia la simulación desde la página de Inicio.")
    else:
        st.subheader(f"Ronda {st.session_state.round + 1}/20 (Dificultad: {st.session_state.difficulty})")
        company = st.session_state.company
        
        # Display progress bar
        st.progress(st.session_state.round / 20.0)
        
        # Display current company state
        st.write(f"**Estado Actual**")
        st.write(f"- Capital: ${company.get('capital', 0):,}")
        st.write(f"- Empleados: {company.get('employees', 0)}")
        st.write(f"- Satisfacción de Empleados: {company.get('satisfaction', 0)}%")
        st.write(f"- Satisfacción de Clientes: {company.get('customer_satisfaction', 0)}%")
        st.write(f"- Cuota de Mercado: {company.get('market_share', 0)}%")
        
        # Display charts
        if st.session_state.history:
            history_df = pd.DataFrame(st.session_state.history)
            chart_data = pd.DataFrame({
                "Ronda": [0] + list(history_df["round"]),
                "Capital": [st.session_state.initial_company["capital"]] + list(history_df["capital"]),
                "Satisfacción de Empleados": [st.session_state.initial_company["satisfaction"]] + list(history_df["satisfaction"]),
                "Satisfacción de Clientes": [st.session_state.initial_company["customer_satisfaction"]] + list(history_df["customer_satisfaction"]),
                "Cuota de Mercado": [st.session_state.initial_company["market_share"]] + list(history_df["market_share"])
            })
            st.subheader("Tendencias")
            st.line_chart(chart_data.set_index("Ronda")[["Capital"]], height=200)
            st.line_chart(chart_data.set_index("Ronda")[["Satisfacción de Empleados", "Satisfacción de Clientes"]], height=200)
            st.line_chart(chart_data.set_index("Ronda")[["Cuota de Mercado"]], height=200)
        
        if st.session_state.round < 20 and not st.session_state.game_over:
            # Generate challenge
            if "current_challenge" not in st.session_state:
                challenge = generate_challenge(company)
                if challenge:
                    st.session_state.current_challenge = challenge
                else:
                    st.stop()
            
            challenge = st.session_state.current_challenge
            st.write(f"**Desafío**: {challenge['description']}")
            st.write("**Opciones**:")
            for opt in ["A", "B", "C", "D"]:
                st.write(f"{opt}. {challenge['options'][opt]}")
            
            # User input
            choice = st.radio("Selecciona una opción", ["A", "B", "C", "D"], key=f"choice_{st.session_state.round}")
            
            if st.button("Confirmar Decisión") and not st.session_state.decision_made:
                # Update company state
                result = update_company_state(company, choice, challenge)
                
                # Store history
                st.session_state.history.append({
                    "round": st.session_state.round + 1,
                    "challenge": challenge["description"],
                    "choice": choice,
                    "explanation": challenge["explanation"],
                    "correct_option": challenge["correct_option"],
                    "capital": company["capital"],
                    "employees": company["employees"],
                    "satisfaction": company["satisfaction"],
                    "customer_satisfaction": company["customer_satisfaction"],
                    "market_share": company["market_share"]
                })
                
                # Store decision result
                st.session_state.decision_result = {
                    "explanation": challenge["explanation"],
                    "bancarrota": result == "bancarrota",
                    "correct": choice == challenge["correct_option"]
                }
                st.session_state.decision_made = True
                st.rerun()
            
            # Display decision result if available
            if st.session_state.decision_made and st.session_state.decision_result:
                st.write("**Resultado de tu decisión**:")
                if st.session_state.decision_result["bancarrota"]:
                    st.error("¡La empresa ha quebrado!")
                elif st.session_state.decision_result["correct"]:
                    st.success(st.session_state.decision_result["explanation"])
                else:
                    st.warning(st.session_state.decision_result["explanation"])
            
            # Continue to next round
            if st.session_state.decision_made and not st.session_state.game_over:
                if st.button("Continuar"):
                    st.session_state.round += 1
                    st.session_state.decision_made = False
                    st.session_state.decision_result = None
                    if "current_challenge" in st.session_state:
                        del st.session_state.current_challenge
                    st.rerun()
        else:
            st.info("La simulación ha terminado. Ve a la página de Resultados.")

elif page == "Resultados":
    if not st.session_state.company or st.session_state.round == 0:
        st.warning("No hay resultados disponibles. Por favor, completa la simulación.")
    else:
        st.header("Resultados Finales")
        company = st.session_state.company
        st.write(f"**Estado Final de la Empresa**")
        st.write(f"- Capital: ${company.get('capital', 0):,}")
        st.write(f"- Empleados: {company.get('employees', 0)}")
        st.write(f"- Satisfacción de Empleados: {company.get('satisfaction', 0)}%")
        st.write(f"- Satisfacción de Clientes: {company.get('customer_satisfaction', 0)}%")
        st.write(f"- Cuota de Mercado: {company.get('market_share', 0)}%")
        
        # Display charts
        if st.session_state.history:
            history_df = pd.DataFrame(st.session_state.history)
            chart_data = pd.DataFrame({
                "Ronda": [0] + list(history_df["round"]),
                "Capital": [st.session_state.initial_company["capital"]] + list(history_df["capital"]),
                "Satisfacción de Empleados": [st.session_state.initial_company["satisfaction"]] + list(history_df["satisfaction"]),
                "Satisfacción de Clientes": [st.session_state.initial_company["customer_satisfaction"]] + list(history_df["customer_satisfaction"]),
                "Cuota de Mercado": [st.session_state.initial_company["market_share"]] + list(history_df["market_share"])
            })
            st.subheader("Tendencias Finales")
            st.line_chart(chart_data.set_index("Ronda")[["Capital"]], height=200)
            st.line_chart(chart_data.set_index("Ronda")[["Satisfacción de Empleados", "Satisfacción de Clientes"]], height=200)
            st.line_chart(chart_data.set_index("Ronda")[["Cuota de Mercado"]], height=200)
        
        # Evaluate final state
        evaluation = evaluate_final_state(st.session_state.initial_company, company)
        st.write("**Análisis Final**:")
        st.markdown(evaluation)
        
        # Display decision history with expanders
        st.subheader("Historial de Decisiones")
        for record in st.session_state.history:
            with st.expander(f"Ronda {record['round']}: {record['challenge'][:50]}..."):
                st.write(f"**Desafío**: {record['challenge']}")
                st.write(f"- Decisión: {record['choice']}")
                st.write(f"- Explicación: {record['explanation']}")
                st.write(f"- Estado: Capital ${record['capital']:,}, Empleados {record['employees']}, Satisfacción {record['satisfaction']}%, Clientes {record['customer_satisfaction']}%, Mercado {record['market_share']}%")
