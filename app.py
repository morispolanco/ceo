import streamlit as st
import google.generativeai as genai
import random
import json

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

# Function to generate initial company profile using Gemini API
def generate_company_profile():
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
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text.strip("```json\n").strip("```"))
    except json.JSONDecodeError:
        st.error("Error al procesar la respuesta del API. Intenta de nuevo.")
        return None

# Function to format company profile as plain text
def format_company_profile(company):
    # Handle missing or differently named 'personnel' key
    personnel_list = company.get("personnel", [])
    if not personnel_list:
        personnel_text = "- No se proporcionó información de personal clave."
    else:
        personnel_text = "\n".join([f"- {person['name']}: {person['role']}" for person in personnel_list])
    
    return f"""
    **Productos o Servicios**: {company.get('products', 'No disponible')}
    **Inventario**: {company.get('inventory', 'No disponible')}
    **Capital Inicial**: ${company.get('capital', 0)}
    **Número de Empleados**: {company.get('employees', 0)}
    **Satisfacción de Empleados**: {company.get('satisfaction', 0)}%
    **Personal Clave**:
    {personnel_text}
    """

# Function to generate a challenge using Gemini API
def generate_challenge(company):
    prompt = f"""
    Eres un simulador de negocios. Basándote en la siguiente empresa:
    - Productos: {company.get('products', 'No disponible')}
    - Inventario: {company.get('inventory', 'No disponible')}
    - Capital: ${company.get('capital', 0)}
    - Empleados: {company.get('employees', 0)}
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
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text.strip("```json\n").strip("```"))
    except json.JSONDecodeError:
        st.error("Error al procesar el desafío del API. Intenta de nuevo.")
        return None

# Function to update company state based on decision
def update_company_state(company, choice, challenge):
    correct = challenge["correct_option"]
    impacts = {
        "A": {"capital": 0, "employees": 0, "satisfaction": 0},
        "B": {"capital": 0, "employees": 0, "satisfaction": 0},
        "C": {"capital": 0, "employees": 0, "satisfaction": 0},
        "D": {"capital": 0, "employees": 0, "satisfaction": 0},
    }
    if choice == correct:
        impacts[choice] = {"capital": random.randint(5000, 20000), "employees": random.randint(0, 2), "satisfaction": random.randint(5, 10)}
    else:
        impacts[choice] = {"capital": -random.randint(5000, 20000), "employees": -random.randint(0, 2), "satisfaction": -random.randint(5, 15)}
    
    company["capital"] = company.get("capital", 0) + impacts[choice]["capital"]
    company["employees"] = max(0, company.get("employees", 0) + impacts[choice]["employees"])
    company["satisfaction"] = max(0, min(100, company.get("satisfaction", 0) + impacts[choice]["satisfaction"]))
    
    if company["capital"] <= 0 or company["employees"] <= 0 or company["satisfaction"] <= 10:
        st.session_state.game_over = True
        return "bancarrota"
    return company

# Function to evaluate final state
def evaluate_final_state(initial_company, final_company):
    prompt = f"""
    Compara el estado inicial y final de una empresa:
    Inicial: Capital ${initial_company.get('capital', 0)}, {initial_company.get('employees', 0)} empleados, satisfacción {initial_company.get('satisfaction', 0)}%
    Final: Capital ${final_company.get('capital', 0)}, {final_company.get('employees', 0)} empleados, satisfacción {final_company.get('satisfaction', 0)}%
    Determina si la empresa mejoró, empeoró o quebró. Explica por qué en español.
    """
    response = model.generate_content(prompt)
    return response.text

# Streamlit app
st.title("Simulación de Negocios")

# Sidebar for navigation
st.sidebar.header("Navegación")
page = st.sidebar.radio("Ir a", ["Inicio", "Simulación", "Resultados"])

if page == "Inicio":
    st.header("Bienvenido a la Simulación de Negocios")
    st.write("En esta simulación, tomarás el rol de CEO de una empresa mediana. Tu objetivo es tomar decisiones estratégicas para mejorar la empresa a lo largo de 20 rondas.")
    
    if st.button("Iniciar Simulación"):
        # Generate company profile
        company = generate_company_profile()
        if company:
            company["satisfaction"] = 70  # Initial employee satisfaction
            st.session_state.company = company
            st.session_state.initial_company = company.copy()
            st.session_state.round = 0
            st.session_state.history = []
            st.session_state.game_over = False
            st.rerun()
    
    if st.session_state.company:
        st.subheader("Perfil Inicial de la Empresa")
        st.markdown(format_company_profile(st.session_state.company))

elif page == "Simulación":
    if not st.session_state.company:
        st.warning("Por favor, inicia la simulación desde la página de Inicio.")
    else:
        st.subheader(f"Ronda {st.session_state.round + 1}/20")
        company = st.session_state.company
        
        # Display current company state
        st.write(f"**Estado Actual**")
        st.write(f"- Capital: ${company.get('capital', 0)}")
        st.write(f"- Empleados: {company.get('employees', 0)}")
        st.write(f"- Satisfacción: {company.get('satisfaction', 0)}%")
        
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
            
            if st.button("Confirmar Decisión"):
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
                    "satisfaction": company["satisfaction"]
                })
                
                # Display results
                st.write("**Resultado de tu decisión**:")
                st.write(challenge["explanation"])
                
                if result == "bancarrota":
                    st.error("¡La empresa ha quebrado!")
                    st.session_state.game_over = True
                else:
                    st.session_state.round += 1
                    del st.session_state.current_challenge  # Clear current challenge
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
        st.write(f"- Capital: ${company.get('capital', 0)}")
        st.write(f"- Empleados: {company.get('employees', 0)}")
        st.write(f"- Satisfacción: {company.get('satisfaction', 0)}%")
        
        # Evaluate final state
        evaluation = evaluate_final_state(st.session_state.initial_company, company)
        st.write("**Análisis Final**:")
        st.write(evaluation)
        
        # Display decision history
        st.subheader("Historial de Decisiones")
        for record in st.session_state.history:
            st.write(f"**Ronda {record['round']}**: {record['challenge']}")
            st.write(f"- Decisión: {record['choice']}")
            st.write(f"- Explicación: {record['explanation']}")
            st.write(f"- Estado: Capital ${record['capital']}, Empleados {record['employees']}, Satisfacción {record['satisfaction']}%")
            st.write("---")
