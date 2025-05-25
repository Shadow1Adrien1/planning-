
import pyomo.environ as pyo
import pandas as pd
import json
from datetime import datetime
import os
# Création du modèle Pyomo
model = pyo.ConcreteModel()

model.Taille_Jours = 7       # Taille de l'ensemble E1, le nombre de jours
model.Taille_Horaires = 8    # Taille de l'ensemble E2, le nombre de plages horaires
model.Taille_Salles = 16      # Taille de l'ensemble E3, le nombre de salles
model.Taille_Activites =35 # Taille de l'ensemble E4, le nombre d'activité
model.Taille_Groupes =10       # Taille de l'ensemble E5, le nombre de groupe d'étudiant
model.Taille_Responsables = 10 # Taille de l'ensemble E6, le nombre de responsable
model.Capacite_Salles = pyo.Param(range(model.Taille_Salles), initialize={i: 25 for i in range(model.Taille_Salles)}, mutable=True)
model.Taille_Groupes_Etudiants = pyo.Param(range(model.Taille_Groupes), initialize={i:25 for i in range(model.Taille_Groupes)}, mutable=True)
# Enseignant responsable de l'activité (1 si i_6 enseigne i_4, sinon 0)
def init_enseignant_activite(model):
    return {(i_4, i_6): 1 for i_4 in range(model.Taille_Activites)
                              for i_6 in range(model.Taille_Responsables)}
model.Enseignant_Activite = pyo.Param(
    range(model.Taille_Activites),
    range(model.Taille_Responsables),
    initialize=init_enseignant_activite,
    mutable=True
)

GA = [str((i_4, i_5)) for i_4 in range(model.Taille_Activites) 
                          for i_5 in range(model.Taille_Groupes)]
#GA[1]
# Heure du (heures dues)
model.D = pyo.Param(GA, initialize={i: 20 for i in GA}, mutable=True)
# Heure faite (heures effectuées)
model.d = pyo.Param(GA, initialize={i: 2 for i in GA}, mutable=True)# unité de plage horaire
# Exemple : Indisponibilité des responsables (modifiable)
model.Indisponibilite = pyo.Param(range(model.Taille_Jours), range(model.Taille_Horaires), range(model.Taille_Responsables),
                                               initialize={(i_1, i_2, i_6): 0 for i_1 in range(model.Taille_Jours) 
                                                          for i_2 in range(model.Taille_Horaires) for i_6 in range(model.Taille_Responsables)}, mutable=True)
# Enseignant responsable de l'activité (1 si i_6 enseigne i_4, sinon 0)
model.Enseignant_Activite = pyo.Param(
    range(model.Taille_Activites),
    range(model.Taille_Responsables),
    initialize={(i_4, i_6): 1  for i_4 in range(model.Taille_Activites) for i_6 in range(model.Taille_Responsables)  },  # Exemple simple
    mutable=True
)


# Exemple : Jours fériés (modifiable)
model.Jours_Feries = pyo.Param(range(model.Taille_Jours), initialize={}, mutable=True)

indices = []
for i_1 in range(model.Taille_Jours):  # Jours E1
    for i_2 in range(model.Taille_Horaires):  # Plages horaires E2
        for i_3 in range(model.Taille_Salles):  # Salles E3
            for i_4 in range(model.Taille_Activites):  # Activités E4
                for i_5 in range(model.Taille_Groupes):  # Groupes d’étudiants E5
                    for i_6 in range(model.Taille_Responsables):  # Responsables E6
                        indices.append(str((i_1, i_2, i_3, i_4, i_5, i_6)))

# Définition des indices dans le modèle
model.idx = pyo.Set(initialize=indices)  # Utilisation de la liste 'indices'
model.X = pyo.Var(model.idx, domain=pyo.Binary)
# Nouvelle variable : responsable choisi pour chaque activité-groupe
model.Y = pyo.Var(
    range(model.Taille_Activites),
    range(model.Taille_Groupes),
    range(model.Taille_Responsables),
    domain=pyo.Binary
)

# Lien entre X et Y : si une activité-groupe est affectée à un responsable, alors Y doit être activé
model.Lien_XY = pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_3 in range(model.Taille_Salles):
            for i_4 in range(model.Taille_Activites):
                for i_5 in range(model.Taille_Groupes):
                    for i_6 in range(model.Taille_Responsables):
                        model.Lien_XY.add(
                            model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))] <= model.Y[i_4, i_5, i_6]
                        )

# Un seul responsable par activité-groupe
model.Unicite_Responsable = pyo.ConstraintList()
for i_4 in range(model.Taille_Activites):
    for i_5 in range(model.Taille_Groupes):
        model.Unicite_Responsable.add(
            sum(model.Y[i_4, i_5, i_6] for i_6 in range(model.Taille_Responsables)) == 1
        )


def constraint_non_chevauchement(model, i_1, i_2, i_3, i_5):
    return sum([sum([model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))] for i_4 in range(model.Taille_Activites)]) for i_6 in range(model.Taille_Responsables)]) <= 1


model.Non_Chevauchement = pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_3 in range(model.Taille_Salles):
            for i_5 in range(model.Taille_Groupes):
                model.Non_Chevauchement.add(constraint_non_chevauchement(model, i_1, i_2, i_3, i_5))

def constraint_capacite_salles(model, i_1, i_2, i_3):
    temp=0
    for i_4 in range(model.Taille_Activites):
        for i_5 in range(model.Taille_Groupes):
            for i_6 in range(model.Taille_Responsables):
                temp=temp+model.Taille_Groupes_Etudiants[i_5] * model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
    return temp <= model.Capacite_Salles[i_3]
model.Capacite_Salles_Constraint = pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_3 in range(model.Taille_Salles):
            model.Capacite_Salles_Constraint.add(constraint_capacite_salles(model, i_1, i_2, i_3))

# contrainte de non omniprésence pour responsable
def constraint_non_omnipresence_resp(model,i_1,i_2,i_6):
    t=0
    for i_3 in range(model.Taille_Salles):
        for i_4 in range(model.Taille_Activites):
            for i_5 in range(model.Taille_Groupes):
                t= t + model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
    return t <= 1  
model.Non_Omnipresence_Resp= pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_6 in range(model.Taille_Responsables):
            model.Non_Omnipresence_Resp.add(constraint_non_omnipresence_resp(model,i_1,i_2,i_6))

# contrainte de nom omniprésence pour un groupe d'étudiant
def constraint_non_omnipresence_etud(model,i_1,i_2,i_5):
    t_1=0
    for i_3 in range(model.Taille_Salles):
        for i_4 in range(model.Taille_Activites):
            for i_6 in range(model.Taille_Responsables):
                t_1= t_1 + model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
    return t_1 <= 1 
model.Non_Omnipresence_Etud= pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_5 in range(model.Taille_Groupes):
            model.Non_Omnipresence_Etud.add(constraint_non_omnipresence_etud(model,i_1,i_2,i_5))

# # Contrainte d'indisponibilité des responsables
def constraint_indisponibilite(model, i_1, i_2, i_6):
    # Vérifiez d'abord si l'indice est valide
    if (i_1, i_2, i_6) in model.Indisponibilite:
        if model.Indisponibilite[i_1, i_2, i_6] == 1:  # Si responsable indisponible
            return sum(
                sum(
                    sum(
                        model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                        for i_5 in range(model.Taille_Groupes)
                    )
                    for i_4 in range(model.Taille_Activites)
                )
                for i_3 in range(model.Taille_Salles)
            ) == 0
    else:
        return pyo.Constraint.Skip  # Ignore la contrainte si l'indice n'existe pas

 
model.Indisponibilite = pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    for i_2 in range(model.Taille_Horaires):
        for i_6 in range(model.Taille_Responsables):
            model.Indisponibilite.add(constraint_indisponibilite(model, i_1, i_2, i_6))                  
def constraint_enseignant_activite(model, i_4, i_6):
    # Tu dois convertir la valeur symbolique Pyomo en valeur Python avec pyo.value
    if pyo.value(model.Enseignant_Activite[i_4, i_6]) == 0:
        return sum(
            sum(
                sum(
                    sum(
                        model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                          for i_1 in range(model.Taille_Jours))
                  for i_2 in range(model.Taille_Horaires))
                for i_3 in range(model.Taille_Salles))
            for i_5 in range(model.Taille_Groupes))
    else:
        return pyo.Constraint.Skip

model.Enseignants_Activite_Constraint = pyo.ConstraintList()
for i_4 in range(model.Taille_Activites):
    for i_6 in range(model.Taille_Responsables):
            model.Enseignants_Activite_Constraint.add(constraint_enseignant_activite(model, i_4, i_6))
                   
# Contrainte des jours fériés
def constraint_jours_feries(model, i_1):
    if i_1 in model.Jours_Feries:  # Vérifie si c'est un jour férié
        return sum(
            sum(
                sum(
                    sum(
                        sum(
                            model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                            for i_6 in range(model.Taille_Responsables)  # Responsables
                        )
                        for i_5 in range(model.Taille_Groupes)  # Groupes d'étudiants
                    )
                    for i_4 in range(model.Taille_Activites)  # Activités
                )
                for i_3 in range(model.Taille_Salles)  # Salles
            )
            for i_2 in range(model.Taille_Horaires)  # Plages horaires
        ) == 0  # La somme des activités doit être égale à zéro pendant les jours fériés
    else:
        return pyo.Constraint.Skip  # Ignore la contrainte si ce n'est pas un jour férié

# Ajout de la contrainte pour chaque jour
model.Jours_Feries = pyo.ConstraintList()
for i_1 in range(model.Taille_Jours):
    model.Jours_Feries.add(constraint_jours_feries(model, i_1))



# Fonction objectif 1 : Minimiser la différence entre les heures prévues et les heures effectuées

def objectif1(model):
    GA = [(i_4, i_5) for i_4 in range(model.Taille_Activites) for i_5 in range(model.Taille_Groupes)]
    Z1 = sum(
        [
          pow(1-(model.d[str((i_4, i_5))]/model.D[str((i_4, i_5))])*sum(
              model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
              for i_1 in range(model.Taille_Jours) 
              for i_2 in range(model.Taille_Horaires) 
              for i_3 in range(model.Taille_Salles) 
              for i_6 in range(model.Taille_Responsables)
              ),2)
          for (i_4, i_5) in GA
        ] 
    )
    
    return Z1  

# Fonction objectif 2: minimiser les écarts horaires pour les étudiant
def objectif2(model):
    Z2=sum(
        sum((1/model.Taille_Horaires)
            *sum(pow(i_2,2)*model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                                             for i_2 in range(model.Taille_Horaires) 
                                             for i_3 in range(model.Taille_Salles)
                                             for i_6 in range(model.Taille_Responsables)
                                             )-pow((1/model.Taille_Horaires)
                                                   *sum(i_2*model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                                                                                 for i_2 in range(model.Taille_Horaires) 
                                                                                 for i_3 in range(model.Taille_Salles)
                                                                                 for i_6 in range(model.Taille_Responsables)),2
                                                   )
             for i_5 in range(model.Taille_Groupes))
        for i_1 in range(model.Taille_Jours) )
    return Z2   


# Fonction objectif 3: Minimiser la non-occupation des salles   
def objectif3(model):    
    Z3= sum(pow((model.Capacite_Salles[i_3]/model.Taille_Groupes_Etudiants[i_5])-sum(model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                                                                         for i_1 in range(model.Taille_Jours)
                                                                         for i_2 in range(model.Taille_Horaires)  # Plages horaires E2
                                                                         for i_3 in range(model.Taille_Salles)  # Salles E3
                                                                         for i_4 in range(model.Taille_Activites)  # Activités E4
                                                                         for i_5 in range(model.Taille_Groupes)  # Groupes d’étudiants E5
                                                                         for i_6 in range(model.Taille_Responsables)),2)
           for i_1 in range(model.Taille_Jours)
           for i_4 in range(model.Taille_Activites)
           for i_5 in range(model.Taille_Groupes))                                                                    
    return Z3



 # Fonction objectif 4 : Maximiser l'occupation des groupes
def objectif4(model):
    Ni1i5= sum(model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
               for i_4 in range(model.Taille_Activites)
               for i_2 in range(model.Taille_Horaires)  
               for i_3 in range(model.Taille_Salles)
               for i_5 in range(model.Taille_Groupes)
               for i_6 in range(model.Taille_Responsables))
    Z4= sum((1/Ni1i5)*sum(pow(i_4,2)*model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                          for i_4 in range(model.Taille_Activites)
                          for i_2 in range(model.Taille_Horaires)  
                          for i_3 in range(model.Taille_Salles)
                          for i_6 in range(model.Taille_Responsables)) 
            - pow((1/Ni1i5)*sum((i_4*model.X[str((i_1, i_2, i_3, i_4, i_5, i_6))]
                                  for i_4 in range(model.Taille_Activites)
                                  for i_2 in range(model.Taille_Horaires)  
                                  for i_3 in range(model.Taille_Salles)
                                  for i_6 in range(model.Taille_Responsables)) ),2)
            for i_4 in range(model.Taille_Activites)
            for i_2 in range(model.Taille_Horaires)  
            for i_3 in range(model.Taille_Salles)
            for i_6 in range(model.Taille_Responsables))
    return Z4

# Objectifs combinés (multitâches)
model.objectif1 = pyo.Objective(rule=objectif1, sense=pyo.minimize)
model.objectif2 = pyo.Objective(rule=objectif2, sense=pyo.minimize)
model.objectif3 = pyo.Objective(rule=objectif3, sense=pyo.minimize)
model.objectif4 = pyo.Objective(rule=objectif4, sense=pyo.maximize)


# Résolution
# solver = pyo.SolverFactory('minotaur', executable="C:/Users/Adrien/Downloads/minotaur-0.4.1-win64/minotaur-0.4.1-win64/bin/mbnb.exe")
# res=solver.solve(model,tee=True)
# solver =  pyo.SolverFactory('Cbc', executable="C:/Users/Adrien/Downloads/Cbc-releases.2.10.12-w64-msvc17-md/bin/cbc.exe")
# res=solver.solve(model,tee=True)


solver = pyo.SolverFactory('minotaur', executable="C:/Users/Adrien/Downloads/minotaur-0.4.1-win64/minotaur-0.4.1-win64/bin/mbnb.exe")
res=solver.solve(model, tee=True)

TT = {"Jours":[],"Plages_horaires":[],"Salles":[],"Activites":[],"Groupes_etudiants":[],"Responsables":[]}
for i_1 in range(model.Taille_Jours):  # Jours
    for i_2 in range(model.Taille_Horaires):  # Plages horaires
        for i_3 in range(model.Taille_Salles):  # Salles
            for i_4 in range(model.Taille_Activites):  # Activités
                for i_5 in range(model.Taille_Groupes):  # Groupes d’étudiants
                    for i_6 in range(model.Taille_Responsables):  # Responsables
                        noms = str((i_1, i_2, i_3, i_4, i_5, i_6))
                        if(model.X[noms].value==1):
                            TT["Jours"].append(i_1)
                            TT["Plages_horaires"].append(i_2)
                            TT["Salles"].append(i_3)
                            TT["Activites"].append(i_4)
                            TT["Groupes_etudiants"].append(i_5)
                            TT["Responsables"].append(i_6)
df_1=pd.DataFrame(TT)
pd.set_option("display.max_columns",None) 
pd.set_option("display.max_row",None)
print(df_1.to_string(index=False))

#AD=df_1.to_dict()
#print(AD)
#type(AD)

# json_output = []

# for i in range(len(df_1)):
#     record = {
#         "salle": int(df_1.loc[i, "Salles"]),
#         "encadreur": int(df_1.loc[i, "Responsables"]),
#         "activite": int(df_1.loc[i, "Activites"]),
#         "horaire": int(df_1.loc[i, "Plages_horaires"]),
#         "groupe": int(df_1.loc[i, "Groupes_etudiants"]),
#         "date": int(df_1.loc[i, "Jours"])
#     }
#     json_output.append(record)



# # Création du nom de fichier avec horodatage à la seconde près
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# filename = f"emploi_du_temps_{timestamp}.json"

# # Dossier courant du script
# current_dir = os.getcwd()

# # Chemin complet du fichier
# filepath = os.path.join(current_dir, filename)

# # Écriture du JSON
# with open(filepath, "w") as f:
#     json.dump(json_output, f, indent=2)

# # Afficher l'emplacement du fichier
# print(f"Fichier JSON enregistré ici : {filepath}")

   