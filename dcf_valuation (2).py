

 MODÈLE DE VALORISATION DCF (Discounted Cash Flow)
 Auteur : Aymane El Adlouni
----------------------------------------------------------------------\\
 Ce programme estime la VALEUR INTRINSÈQUE d'une entreprise à partir de ses
 flux de trésorerie futurs, actualisés à leur valeur d'aujourd'hui.

 Principe : 1 dirham demain vaut moins qu'1 dirham aujourd'hui (valeur temps
 de l'argent). On "actualise" donc les flux futurs avec le WACC.

 Étapes du modèle :
   1. Projeter le Free Cash Flow (FCF) sur N années
   2. Actualiser chaque FCF à sa valeur présente
   3. Calculer la valeur terminale (tout ce qui vient après l'année N)
   4. Additionner le tout = Valeur d'Entreprise (Enterprise Value)
   5. En déduire la valeur des capitaux propres et le prix par action


import numpy as np
import matplotlib.pyplot as plt



# 1. HYPOTHÈSES DU MODÈLE  (les seules choses à modifier pour tester)

# Toutes les valeurs monétaires sont en millions (peu importe la devise).

fcf_initial       = 1000.0   # Free Cash Flow de la dernière année connue
croissance_fcf    = 0.08     # Taux de croissance annuel du FCF (8%)
annees_projection = 5        # Nombre d'années projetées explicitement
wacc              = 0.10     # Coût moyen pondéré du capital (10%) = taux d'actualisation
croissance_perpet = 0.025    # Croissance perpétuelle après l'année N (2.5%)

dette_nette       = 1500.0   # Dette - trésorerie (pour passer de EV à Equity Value)
nombre_actions    = 500.0    # Nombre d'actions en circulation (millions)



# 2. PROJECTION DES FLUX DE TRÉSORERIE FUTURS

def projeter_fcf(fcf_base, taux_croissance, n_annees):
    """
    Projette le Free Cash Flow année par année.
    Chaque année = année précédente * (1 + taux de croissance).
    Retourne une liste de N flux.
    """
    flux = []
    fcf_courant = fcf_base
    for annee in range(1, n_annees + 1):
        fcf_courant = fcf_courant * (1 + taux_croissance)
        flux.append(fcf_courant)
    return flux



# 3. ACTUALISATION : ramener un flux futur à sa valeur d'aujourd'hui

def actualiser(flux_futur, taux, annee):
    """
    Valeur présente = flux_futur / (1 + taux) ^ annee
    Plus l'année est lointaine, plus le flux est "réduit".
    """
    return flux_futur / ((1 + taux) ** annee)



# 4. VALEUR TERMINALE (méthode de Gordon-Shapiro)

def valeur_terminale(dernier_fcf, taux_actualisation, croissance_long_terme):
    """
    Estime la valeur de TOUS les flux au-delà de l'année N, en supposant
    une croissance constante à l'infini.

    Formule de Gordon :
        VT = FCF_(N+1) / (WACC - g)
    où FCF_(N+1) = dernier FCF projeté * (1 + g)
    """
    fcf_apres = dernier_fcf * (1 + croissance_long_terme)
    return fcf_apres / (taux_actualisation - croissance_long_terme)



# 5. CALCUL PRINCIPAL DU DCF

def calculer_dcf():
    # --- Étape 1 : projeter les FCF ---
    flux_projetes = projeter_fcf(fcf_initial, croissance_fcf, annees_projection)

    # --- Étape 2 : actualiser chaque FCF ---
    flux_actualises = []
    for i, flux in enumerate(flux_projetes, start=1):
        va = actualiser(flux, wacc, i)
        flux_actualises.append(va)

    somme_flux_actualises = sum(flux_actualises)

    # --- Étape 3 : valeur terminale, puis on l'actualise elle aussi ---
    vt = valeur_terminale(flux_projetes[-1], wacc, croissance_perpet)
    vt_actualisee = actualiser(vt, wacc, annees_projection)

    # --- Étape 4 : Enterprise Value = flux actualisés + VT actualisée ---
    enterprise_value = somme_flux_actualises + vt_actualisee

    # --- Étape 5 : Equity Value et prix par action ---
    equity_value = enterprise_value - dette_nette
    prix_par_action = equity_value / nombre_actions

    # --- Affichage détaillé ---
    print("=" * 60)
    print("           RÉSULTATS DE LA VALORISATION DCF")
    print("=" * 60)
    print("\nFlux de trésorerie projetés et actualisés :")
    print("-" * 60)
    print(f"{'Année':<8}{'FCF projeté':>18}{'FCF actualisé':>20}")
    print("-" * 60)
    for i in range(annees_projection):
        print(f"{i+1:<8}{flux_projetes[i]:>18,.1f}{flux_actualises[i]:>20,.1f}")
    print("-" * 60)
    print(f"{'Somme des FCF actualisés':<40}{somme_flux_actualises:>18,.1f}")
    print(f"{'Valeur terminale (actualisée)':<40}{vt_actualisee:>18,.1f}")
    print("=" * 60)
    print(f"{'VALEUR D''ENTREPRISE (EV)':<40}{enterprise_value:>18,.1f}")
    print(f"{'- Dette nette':<40}{dette_nette:>18,.1f}")
    print(f"{'= VALEUR DES CAPITAUX PROPRES':<40}{equity_value:>18,.1f}")
    print("=" * 60)
    print(f"{'PRIX PAR ACTION':<40}{prix_par_action:>18,.2f}")
    print("=" * 60)

    return flux_projetes, flux_actualises, prix_par_action



# 6. ANALYSE DE SENSIBILITÉ : et si le WACC ou la croissance changeaient ?

def analyse_sensibilite():
    """
    Recalcule le prix par action pour différentes combinaisons de WACC et
    de croissance perpétuelle. C'est LE tableau que les analystes montrent :
    il révèle à quel point la valorisation dépend des hypothèses.
    """
    liste_wacc = [0.08, 0.09, 0.10, 0.11, 0.12]
    liste_g    = [0.015, 0.020, 0.025, 0.030, 0.035]

    print("\n\nANALYSE DE SENSIBILITÉ — Prix par action")
    print("(lignes = WACC, colonnes = croissance perpétuelle)")
    print("-" * 60)

    # En-tête colonnes
    entete = "WACC \\ g  " + "".join(f"{g*100:>9.1f}%" for g in liste_g)
    print(entete)
    print("-" * 60)

    for w in liste_wacc:
        ligne = f"{w*100:>6.1f}%  "
        for g in liste_g:
            flux = projeter_fcf(fcf_initial, croissance_fcf, annees_projection)
            flux_act = sum(actualiser(f, w, i+1) for i, f in enumerate(flux))
            vt = valeur_terminale(flux[-1], w, g)
            vt_act = actualiser(vt, w, annees_projection)
            ev = flux_act + vt_act
            prix = (ev - dette_nette) / nombre_actions
            ligne += f"{prix:>10.2f}"
        print(ligne)
    print("-" * 60)



# 7. GRAPHIQUE : FCF projeté vs FCF actualisé

def tracer_graphique(flux_projetes, flux_actualises):
    annees = list(range(1, annees_projection + 1))
    largeur = 0.35

    x = np.arange(len(annees))
    plt.figure(figsize=(9, 5))
    plt.bar(x - largeur/2, flux_projetes, largeur, label="FCF projeté", color="#4C72B0")
    plt.bar(x + largeur/2, flux_actualises, largeur, label="FCF actualisé", color="#DD8452")

    plt.xlabel("Année")
    plt.ylabel("Flux (millions)")
    plt.title("FCF projeté vs FCF actualisé — Effet de l'actualisation")
    plt.xticks(x, [f"Année {a}" for a in annees])
    plt.legend()
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("dcf_graphique.png", dpi=120)
    print("\nGraphique enregistré : dcf_graphique.png")



# POINT D'ENTRÉE DU PROGRAMME

if __name__ == "__main__":
    flux_proj, flux_act, prix = calculer_dcf()
    analyse_sensibilite()
    tracer_graphique(flux_proj, flux_act)
