import os
import sys
import json
import pandas as pd
from openai import OpenAI
from database_handler import SchoolDatabase
from dotenv import load_dotenv

load_dotenv()
# --- Configuration ---
API_KEY = os.getenv("api_key")
client = OpenAI(api_key=API_KEY)
db = SchoolDatabase()

def print_bot(text):
    print(f"\n[Assistant École]: {text}")

# --- Cerveau de l'IA : Le "Découpeur" ---
def analyze_intent(user_input, context_data=None, mode="general"):
    """
    Cette fonction envoie ce que dit l'utilisateur à GPT pour qu'il le traduise
    en données compréhensibles par le code Python (JSON).
    """
    try:
        if mode == "extract_start":
            # Essaie de trouver le nom et le prof dès la première phrase
            prompt = (
                f"L'utilisateur dit : '{user_input}'. "
                "Extrait le nom de l'élève et le sujet ou nom du prof si mentionnés. "
                "Réponds UNIQUEMENT au format JSON : {\"student\": \"...\", \"teacher\": \"...\"}. "
                "Si une info est manquante, mets null."
            )
        
        elif mode == "match_teacher":
            # Trouve quel prof correspond à la description (ex: 'celui de maths' -> ID 1)
            teachers_str = context_data.to_string(index=False)
            prompt = (
                f"Voici la liste des professeurs :\n{teachers_str}\n"
                f"L'utilisateur dit : '{user_input}'. "
                "Quel est l'ID (id prof) du professeur qui correspond le mieux ? "
                "Réponds UNIQUEMENT l'ID (ex: 1). Si aucun ne correspond, réponds 0."
            )

        elif mode == "match_slot":
            # Trouve quel créneau correspond (ex: 'mardi vers 16h')
            # On simplifie les dates pour l'IA
            slots_str = ""
            for i, row in context_data.iterrows():
                slots_str += f"ID: {row['slot_id']} | Date: {row['date']} | Heure: {row['temp_depart']}\n"
            
            prompt = (
                f"Voici les créneaux disponibles :\n{slots_str}\n"
                f"L'utilisateur dit : '{user_input}'. "
                "Quel est l'ID du créneau qui correspond le mieux ? "
                "Réponds UNIQUEMENT l'ID (ex: 15). Si aucun ne correspond, réponds 0."
            )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Tu es un extracteur de données strict."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"(Debug IA) Erreur : {e}")
        return None

# --- Logique Principale ---
def booking_protocol():
    print_bot("Bonjour ! Je suis votre assistant de réservation. Dites-moi ce que vous voulez faire.")
    print_bot("(Exemple : 'Je veux un rendez-vous pour Alek avec le prof de maths')")
    
    # 1. ÉCOUTE INITIALE ET DÉCOUPAGE
    first_input = input("\nVous: ").strip()
    if first_input.lower() in ['quitter', 'exit']: return

    print("... Analyse de votre demande ...")
    
    # L'IA essaie de comprendre tout de suite
    initial_data = json.loads(analyze_intent(first_input, mode="extract_start"))
    
    student_name = initial_data.get("student")
    teacher_hint = initial_data.get("teacher") # ex: "maths" ou "Sarhani"

    # ---------------------------------------------------------
    # ÉTAPE 1 : VALIDATION DE L'ÉLÈVE
    # ---------------------------------------------------------
    student_row = None
    
    # Si l'IA n'a pas trouvé de nom, on demande manuellement
    if not student_name:
        print_bot("Quel est le nom de l'élève ?")
        student_name = input("Vous: ").strip()

    # Boucle de recherche sécurisée (Python)
    while student_row is None:
        found, result = db.find_student(student_name)
        if found:
            student_row = result
            print_bot(f"C'est noté pour {student_row['prenom eleve']} {student_row['nom eleve']}.")
        else:
            if result:
                print_bot(f"Je ne suis pas sûr. Voulez-vous dire : {', '.join(result)} ?")
            else:
                print_bot("Je ne trouve pas cet élève. Réessayez le nom :")
            student_name = input("Vous: ").strip()

    # ---------------------------------------------------------
    # ÉTAPE 2 : CHOIX DU PROF (INTELLIGENT)
    # ---------------------------------------------------------
    teachers = db.get_student_teachers(student_row['id'])
    
    teacher_id = None
    
    # Si l'IA avait déjà deviné un prof (ex: "maths"), on essaie de le trouver direct
    if teacher_hint:
        print(f"... Recherche du prof correspondant à '{teacher_hint}' ...")
        ai_guess_id = analyze_intent(teacher_hint, context_data=teachers, mode="match_teacher")
        if ai_guess_id and ai_guess_id != "0":
            # Vérification technique
            if ai_guess_id in teachers['id prof'].values:
                teacher_id = ai_guess_id
                t_name = teachers[teachers['id prof'] == teacher_id].iloc[0]['nom du prof']
                print_bot(f"J'ai compris que vous vouliez voir M./Mme {t_name}.")

    # Si pas trouvé ou pas précisé, on demande
    while teacher_id is None:
        print("\n--- Professeurs ---")
        print(teachers[['nom du prof', 'sujet']].to_string(index=False))
        
        print_bot("Quel professeur voulez-vous voir ? (Vous pouvez dire 'celui de maths' ou le nom)")
        user_choice = input("Vous: ").strip()
        
        # L'IA traduit "celui de maths" en ID "1"
        found_id = analyze_intent(user_choice, context_data=teachers, mode="match_teacher")
        
        if found_id and found_id in teachers['id prof'].values:
            teacher_id = found_id
        else:
            print_bot("Je n'ai pas bien compris quel professeur choisir. Essayons encore.")

    # ---------------------------------------------------------
    # ÉTAPE 3 : CHOIX DE LA DATE (NATUREL)
    # ---------------------------------------------------------
    slots = db.get_available_slots(teacher_id)
    if slots.empty:
        print_bot("Aucune disponibilité pour ce professeur.")
        return

    print_bot("Voici les créneaux disponibles :")
    # Affichage propre pour l'humain
    for index, row in slots.iterrows():
        print(f"- Le {row['date']} de {row['temp_depart']} à {row['temp_fin']}")

    selected_slot_id = None
    while selected_slot_id is None:
        print_bot("Lequel préférez-vous ? (Dites par exemple 'mardi à 16h' ou 'le premier')")
        user_date_choice = input("Vous: ").strip()
        
        # L'IA traduit "Mardi 16h" en "slot_id: 15"
        found_slot_id = analyze_intent(user_date_choice, context_data=slots, mode="match_slot")
        
        # Nettoyage de la réponse de l'IA (parfois elle met des guillemets)
        found_slot_id = str(found_slot_id).replace("'", "").replace('"', "")

        # Vérification technique que l'ID existe bien dans les slots affichés
        # Note : on convertit tout en string pour comparer
        if found_slot_id in slots['slot_id'].astype(str).values:
            selected_slot_id = found_slot_id
        else:
            print_bot("Je n'ai pas réussi à faire correspondre votre demande à une date précise. Réessayez.")

    # ---------------------------------------------------------
    # ÉTAPE 4 : CONFIRMATION
    # ---------------------------------------------------------
    print_bot("Validation en cours...")
    success, link = db.book_slot(selected_slot_id, student_row['id'])
    
    if success:
        t_info = teachers[teachers['id prof'] == teacher_id].iloc[0]
        slot_info = slots[slots['slot_id'].astype(str) == str(selected_slot_id)].iloc[0]
        
        print_bot("--------------------------------------------------")
        print_bot(f"✅ C'est réservé !")
        print_bot(f"Élève : {student_row['prenom eleve']} {student_row['nom eleve']}")
        print_bot(f"Prof : {t_info['nom du prof']} ({t_info['sujet']})")
        print_bot(f"Quand : {slot_info['date']} à {slot_info['temp_depart']}")
        print_bot(f"Lien : {link}")
        print_bot("--------------------------------------------------")
    else:
        print_bot(f"Erreur : {link}")

def main():
    print("------------------------------------------")
    print("   INTERFACE INTELLIGENTE (HYBRIDE)       ")
    print("------------------------------------------")
    while True:
        try:
            booking_protocol()
            res = input("\nUne autre réservation ? (oui/non) : ")
            if "n" in res.lower(): break
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erreur système : {e}")

if __name__ == "__main__":
    main()