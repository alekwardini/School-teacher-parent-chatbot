import pandas as pd
import difflib
import os

class SchoolDatabase:
    def __init__(self):
        # Nom exact de votre fichier Excel
        excel_file = "conference_parent_prof_updated.xlsx"
        
        # Vérification que le fichier existe
        if not os.path.exists(excel_file):
            print(f"ERREUR : Le fichier '{excel_file}' est introuvable.")
            print("Vérifiez qu'il est bien dans le même dossier que appFinale.py")
            raise FileNotFoundError(f"Fichier manquant : {excel_file}")

        print("--- Chargement des données Excel... ---")
        
        # Chargement des feuilles (Sheets)
        # Note: On utilise 'dtype=str' pour éviter que les numéros de téléphone ou ID soient déformés
        self.df_students = pd.read_excel(excel_file, sheet_name="Feuille 1", dtype=str)
        self.df_teachers = pd.read_excel(excel_file, sheet_name="Feuille 2", dtype=str)
        self.df_links = pd.read_excel(excel_file, sheet_name="Feuille 3", dtype=str)
        self.df_slots = pd.read_excel(excel_file, sheet_name="Feuille 4") # On garde les dates en format auto
        
        # --- NETTOYAGE CRITIQUE ---
        # Cette étape enlève les espaces invisibles dans les titres (ex: "classe " devient "classe")
        self.df_students.columns = self.df_students.columns.str.strip()
        self.df_teachers.columns = self.df_teachers.columns.str.strip()
        self.df_links.columns = self.df_links.columns.str.strip()
        self.df_slots.columns = self.df_slots.columns.str.strip()
        
        # Création d'une colonne "Nom Complet" pour faciliter la recherche (ex: "alek wardini")
        # On combine Prénom + Nom en minuscules
        self.df_students['full_name'] = (
            self.df_students['prenom eleve'].str.strip() + " " + self.df_students['nom eleve'].str.strip()
        ).str.lower()

    def find_student(self, name_input):
        """
        Cherche un élève par prénom, nom ou nom complet.
        Gère les fautes de frappe.
        """
        if not name_input: return False, []
        
        search_term = name_input.strip().lower()
        all_full_names = self.df_students['full_name'].tolist()
        all_first_names = self.df_students['prenom eleve'].str.strip().str.lower().tolist()
        
        # 1. Recherche Exacte (Prénom seul OU Nom complet)
        if search_term in all_full_names:
            idx = all_full_names.index(search_term)
            return True, self.df_students.iloc[idx]
        
        if search_term in all_first_names:
            idx = all_first_names.index(search_term)
            return True, self.df_students.iloc[idx]
            
        # 2. Recherche Approximative (Fuzzy Logic)
        # On cherche des ressemblances dans les noms complets
        matches = difflib.get_close_matches(search_term, all_full_names, n=3, cutoff=0.4)
        
        # Si pas de match en nom complet, on essaye juste sur le prénom
        if not matches:
            first_name_matches = difflib.get_close_matches(search_term, all_first_names, n=3, cutoff=0.5)
            # On retrouve les noms complets associés à ces prénoms
            for fname in first_name_matches:
                # On prend le premier étudiant qui a ce prénom
                row = self.df_students[self.df_students['prenom eleve'].str.strip().str.lower() == fname].iloc[0]
                matches.append(f"{row['prenom eleve']} {row['nom eleve']}")
        
        return False, matches

    def get_student_teachers(self, student_id):
        # Convertir l'ID en string pour être sûr de la comparaison
        student_id = str(student_id)
        
        # Trouver les liens dans Feuille 3
        relationships = self.df_links[self.df_links['id student'] == student_id]
        teacher_ids = relationships['id prof'].tolist()
        
        # Trouver les infos profs dans Feuille 2
        teachers = self.df_teachers[self.df_teachers['id prof'].isin(teacher_ids)]
        return teachers

    def get_available_slots(self, teacher_id):
        teacher_id = str(teacher_id) # Comparaison en string
        
        # On filtre Feuille 4
        # On s'assure que teacher_id dans slots est aussi un string
        self.df_slots['teacher_id'] = self.df_slots['teacher_id'].astype(str)
        
        return self.df_slots[
            (self.df_slots['teacher_id'] == teacher_id) & 
            (self.df_slots['etat'] == 'available')
        ]

    def book_slot(self, slot_id, student_id):
        if slot_id not in self.df_slots['slot_id'].values:
            return False, "ID du créneau (slot) introuvable."
            
        idx = self.df_slots.index[self.df_slots['slot_id'] == slot_id].tolist()[0]
        
        # Mise à jour
        self.df_slots.at[idx, 'etat'] = 'booked'
        self.df_slots.at[idx, 'student_id'] = student_id
        
        # Sauvegarde sécurisée
        try:
            with pd.ExcelWriter("conference parent prof-3.xlsx", engine='openpyxl', mode='w') as writer:
                self.df_students.to_excel(writer, sheet_name='Feuille 1', index=False)
                self.df_teachers.to_excel(writer, sheet_name='Feuille 2', index=False)
                self.df_links.to_excel(writer, sheet_name='Feuille 3', index=False)
                self.df_slots.to_excel(writer, sheet_name='Feuille 4', index=False)
        except PermissionError:
            return False, "ERREUR : Veuillez fermer le fichier Excel avant de réserver !"

        # Récupérer le lien Zoom
        t_id = self.df_slots.at[idx, 'teacher_id']
        teacher_info = self.df_teachers[self.df_teachers['id prof'] == t_id].iloc[0]
        
        return True, teacher_info['zoom lien']