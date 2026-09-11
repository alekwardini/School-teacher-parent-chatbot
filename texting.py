import pandas as pd
import random

# 1. SETUP DATA FOR STUDENTS (FEUILLE 1)
# Original students + Requested names + 4 Generated to reach 15 total
students_data = [
    [1, 'wardini', 'alek', '1A', 'a_wardini@hotmail.com', 'alek wardini'],
    [2, 'wardini', 'alfred', '4e', 'a_wardini@hotmail.com', 'alfred wardini'],
    [3, 'shamsedine', 'yasmina', '2A', 'y.shamsedine@gmail.com', 'yasmina shamsedine'],
    [4, 'hammoud', 'serena', '3B', 's_hammoud@yahoo.com', 'serena hammoud'],
    [5, 'katrib', 'kian', '1A', 'k.katrib@hotmail.com', 'kian katrib'],
    [6, 'nassim', 'maxime', '4e', 'm_nassim@gmail.com', 'maxime nassim'],
    [7, 'alamedine', 'zane', '2B', 'z.alamedine@hotmail.com', 'zane alamedine'],
    [8, 'boujema', 'sami', '5e', 's_boujema@yahoo.com', 'sami boujema'],
    [9, 'senem', 'talin', '3A', 't.senem@gmail.com', 'talin senem'],
    [10, 'kassas', 'mohamad', '1B', 'm.kassas@hotmail.com', 'mohamad kassas'],
    [11, 'kassas', 'lana', '2A', 'l.kassas@hotmail.com', 'lana kassas'],
    [12, 'khoury', 'jad', '4e', 'j_khoury@gmail.com', 'jad khoury'], # Generated
    [13, 'mroueh', 'layla', '3B', 'l_mroueh@yahoo.com', 'layla mroueh'], # Generated
    [14, 'nader', 'rami', '5e', 'r_nader@hotmail.com', 'rami nader'], # Generated
    [15, 'tabet', 'sarah', '1A', 's_tabet@gmail.com', 'sarah tabet'] # Generated
]
df_students = pd.DataFrame(students_data, columns=['id', 'nom eleve', 'prenom eleve', 'classe', 'parent_email', 'full_name'])

# 2. SETUP DATA FOR TEACHERS (FEUILLE 2)
# Ensuring >1 teacher per subject
teachers_data = [
    [1, 'sarhani', 'maths', 'exemple.com'],
    [2, 'fguiri', 'sciences', 'exemple.com'],
    [3, 'amara', 'french', 'exemple.com'],
    [4, 'zajac', 'ps', 'exemple.com'],       # Original Zajac (PS)
    [5, 'gallois', 'eps', 'exemple.com'],
    [6, 'khan', 'maths', 'exemple.com'],     # New: Khan for Maths
    [7, 'zajac', 'sciences', 'exemple.com'],  # New: Zajac for Science
    [8, 'akarsu', 'english', 'exemple.com'],  # New: Akarsu for English
    [9, 'dubois', 'french', 'exemple.com'],   # Filler to have 2 French
    [10, 'martin', 'ps', 'exemple.com'],      # Filler to have 2 PS
    [11, 'leroy', 'eps', 'exemple.com'],      # Filler to have 2 EPS
    [12, 'smith', 'english', 'exemple.com']    # Filler to have 2 English
]
df_teachers = pd.DataFrame(teachers_data, columns=['id prof', 'nom du prof', 'sujet', 'zoom lien'])

# 3. GENERATE MAPPINGS (FEUILLE 3)
# Logic: Each student gets 1 teacher per subject, chosen randomly from available teachers of that subject.

# Group teachers by subject
teachers_by_subject = {}
for item in teachers_data:
    t_id = item[0]
    subject = item[2]
    if subject not in teachers_by_subject:
        teachers_by_subject[subject] = []
    teachers_by_subject[subject].append(t_id)

mapping_data = []

# Loop through every student
for s in students_data:
    student_id = s[0]
    # Loop through every subject available
    for subject, t_ids in teachers_by_subject.items():
        # Pick ONE random teacher for this subject
        selected_teacher = random.choice(t_ids)
        mapping_data.append([student_id, selected_teacher])

df_mapping = pd.DataFrame(mapping_data, columns=['id student', 'id prof'])

# 4. SETUP SLOTS (FEUILLE 4)
# Keep original slots and add a dummy slot for new teachers so they appear in system
slots_data = [
    [1, 1, '2025-05-10 00:00:00', '16:00:00', '16:10:00', 'available', ''],
    [2, 1, '2025-05-10 00:00:00', '16:10:00', '16:20:00', 'available', ''],
    [3, 1, '2025-05-10 00:00:00', '17:00:00', '17:10:00', 'available', ''],
    # Add dummy slots for new teachers (Khan, Zajac-Science, Akarsu) to ensure validity
    [4, 6, '2025-05-10 00:00:00', '16:00:00', '16:10:00', 'available', ''],
    [5, 7, '2025-05-10 00:00:00', '16:00:00', '16:10:00', 'available', ''],
    [6, 8, '2025-05-10 00:00:00', '16:00:00', '16:10:00', 'available', '']
]
df_slots = pd.DataFrame(slots_data, columns=['slot_id', 'teacher_id', 'date', 'temp_depart', 'temp_fin', 'etat', 'student_id'])

# 5. WRITE TO EXCEL
file_name = 'conference_parent_prof_updated.xlsx'
with pd.ExcelWriter(file_name) as writer:
    df_students.to_excel(writer, sheet_name='Feuille 1', index=False)
    df_teachers.to_excel(writer, sheet_name='Feuille 2', index=False)
    df_mapping.to_excel(writer, sheet_name='Feuille 3', index=False)
    df_slots.to_excel(writer, sheet_name='Feuille 4', index=False)

print(f"File '{file_name}' has been created successfully.")