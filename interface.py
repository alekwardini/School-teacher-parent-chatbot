import streamlit as st
import time

# --- IMPORT YOUR EXISTING CODE ---
try:
    # We import 'db' and 'analyze_intent' from your original appFinale.py
    from appFinale import db, analyze_intent
except ImportError:
    st.error("ERREUR : Je ne trouve pas 'appFinale.py'. Assurez-vous que ce fichier est dans le même dossier.")
    st.stop()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Réservations École", page_icon="🎓", layout="centered")

# --- CSS CORRECTION (THEME FIX) ---
# This section forces the text to be BLACK and background WHITE
# regardless of your computer's Light/Dark mode settings.
st.markdown("""
<style>
    /* 1. Force main background to White */
    .stApp {
        background-color: #ffffff;
    }

    /* 2. Force all general text (headers, paragraphs) to Black */
    h1, h2, h3, p, li, span, div {
        color: #000000 !important;
    }

    /* 3. Style the Chat Bubbles (Light Gray background, Black text) */
    .stChatMessage {
        background-color: #f0f2f6 !important; 
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        color: #000000 !important;
    }

    /* 4. Fix User Input Box (White background, Black text) */
    .stTextInput input {
        color: #000000 !important;
        background-color: #ffffff !important;
        border: 1px solid #cccccc !important;
    }
    
    /* 5. Fix Buttons */
    .stButton button {
        width: 100%;
        border-radius: 5px;
        background-color: #ff4b4b; /* Streamlit Red */
        color: white !important; /* White text on red button */
        border: none;
    }
    .stButton button:hover {
        background-color: #ff3333;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Portail Parents")

# --- GESTION DE LA MÉMOIRE (SESSION STATE) ---
if "step" not in st.session_state:
    st.session_state.step = 1  
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Bonjour ! Je suis l'assistant de l'école. Pour quel enfant voulez-vous un rendez-vous ?"}]
if "student" not in st.session_state:
    st.session_state.student = None
if "teacher" not in st.session_state:
    st.session_state.teacher = None
if "teacher_hint" not in st.session_state:
    st.session_state.teacher_hint = None

# --- AFFICHAGE DE LA CONVERSATION ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- FONCTION LOGIQUE (PROCESSUS) ---
def process_input():
    user_text = st.session_state.user_input
    if not user_text: return

    # 1. Afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": user_text})
    
    # 2. Logique par étape
    # --- ETAPE 1 : TROUVER L'ÉLÈVE ---
    if st.session_state.step == 1:
        import json
        try:
            # Extraction IA
            raw_json = analyze_intent(user_text, mode="extract_start")
            # Nettoyage préventif du JSON (au cas où l'IA bavarde)
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(raw_json)
            name_to_search = data.get("student") if data.get("student") else user_text
            
            # Sauvegarde indice prof
            if data.get("teacher"):
                st.session_state.teacher_hint = data.get("teacher")
            
            # Recherche DB
            found, result = db.find_student(name_to_search)
            
            if found:
                st.session_state.student = result
                st.session_state.step = 2
                response = f"C'est noté pour **{result['prenom eleve']} {result['nom eleve']}**. Quel professeur souhaitez-vous voir ?"
                
                # Auto-detect prof si mentionné
                if st.session_state.teacher_hint:
                    teachers = db.get_student_teachers(result['id'])
                    t_id = analyze_intent(st.session_state.teacher_hint, context_data=teachers, mode="match_teacher")
                    # Nettoyage ID
                    t_id = str(t_id).strip()
                    
                    if t_id and t_id != "0" and t_id in teachers['id prof'].astype(str).values:
                        t_row = teachers[teachers['id prof'].astype(str) == t_id].iloc[0]
                        st.session_state.teacher = t_row
                        st.session_state.step = 3
                        response += f"\n\n(J'ai compris que vous vouliez **{t_row['nom du prof']}**.)"
            else:
                if isinstance(result, list) and result:
                    response = f"Je ne suis pas sûr. Voulez-vous dire : {', '.join(result)} ?"
                else:
                    response = "Je ne trouve pas cet élève. Essayez de réécrire le nom :"
        except Exception as e:
            print(f"Erreur IA Step 1: {e}")
            response = "Désolé, je n'ai pas compris le nom. Pouvez-vous répéter ?"

    # --- ETAPE 2 : CHOISIR LE PROF ---
    elif st.session_state.step == 2:
        teachers = db.get_student_teachers(st.session_state.student['id'])
        
        found_id = analyze_intent(user_text, context_data=teachers, mode="match_teacher")
        found_id = str(found_id).strip() # Sécurité string
        
        if found_id and found_id != "0" and found_id in teachers['id prof'].astype(str).values:
            t_row = teachers[teachers['id prof'].astype(str) == found_id].iloc[0]
            st.session_state.teacher = t_row
            st.session_state.step = 3
            response = f"Très bien, regardons les disponibilités pour **{t_row['nom du prof']}**."
        else:
            # Liste formatée
            list_profs = "\n".join([f"- {row['nom du prof']} ({row['sujet']})" for i, row in teachers.iterrows()])
            response = f"Je n'ai pas compris quel prof. Voici la liste :\n{list_profs}\n\nÉcrivez le nom ou la matière :"

    # --- ETAPE 3 : CHOISIR LA DATE (TEXTE) ---
    elif st.session_state.step == 3:
        t_id = st.session_state.teacher['id prof']
        slots = db.get_available_slots(t_id)
        
        # IA Match Slot
        slot_id = analyze_intent(user_text, context_data=slots, mode="match_slot")
        slot_id = str(slot_id).replace("'", "").replace('"', "").strip()

        if slot_id in slots['slot_id'].astype(str).values:
            success, link = db.book_slot(slot_id, st.session_state.student['id'])
            if success:
                booked_slot = slots[slots['slot_id'].astype(str) == slot_id].iloc[0]
                response = f"✅ **Confirmé !**\n\n📅 **Date :** {booked_slot['date']} à {booked_slot['temp_depart']}\n🔗 **Lien Visio :** {link}"
                st.session_state.step = 4
            else:
                response = f"Erreur lors de la réservation : {link}"
        else:
            response = "Je n'ai pas trouvé ce créneau exact. Utilisez les boutons ci-dessous ou précisez (ex: 'Mardi 16h')."

    # --- ENVOI RÉPONSE ---
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.user_input = "" # Reset input

# --- ZONE DE SAISIE ---
if st.session_state.step < 4:
    st.text_input("Votre réponse :", key="user_input", on_change=process_input)

# --- BOUTONS INTELLIGENTS (POUR ÉVITER D'ÉCRIRE) ---
if st.session_state.step == 3 and st.session_state.teacher is not None:
    st.write("---")
    st.caption("Ou cliquez sur un horaire :")
    
    # On recharge les slots pour être sûr d'avoir les données à jour
    slots = db.get_available_slots(st.session_state.teacher['id prof'])
    
    if slots.empty:
        st.warning("Aucune disponibilité pour ce professeur.")
    else:
        # Création d'une grille de boutons
        cols = st.columns(3)
        for index, row in slots.iterrows():
            label = f"{row['date']}\n{row['temp_depart']}"
            # On place le bouton dans une colonne
            if cols[index % 3].button(label, key=row['slot_id']):
                # Action quand on clique
                success, msg = db.book_slot(row['slot_id'], st.session_state.student['id'])
                if success:
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"🎉 **Réservé (via bouton) !**\n\n📅 {row['date']} à {row['temp_depart']}\n🔗 {msg}"
                    })
                    st.session_state.step = 4
                    st.rerun() # Rafraîchir la page immédiatement

# --- BOUTON RESET ---
if st.session_state.step == 4:
    if st.button("Nouvelle Réservation"):
        st.session_state.step = 1
        st.session_state.student = None
        st.session_state.teacher = None
        st.session_state.messages = [{"role": "assistant", "content": "C'est reparti ! Pour quel élève ?"}]
        st.rerun()