"""
MODÈLE DE VALORISATION DCF (Discounted Cash Flow)
Auteur : Aymane Eladlouni, M2 Finance, ENCG Fès

Ce programme estime la valeur intrinsèque d'une entreprise à partir des flux
de trésorerie disponibles qu'elle générera, actualisés au coût moyen pondéré
du capital (WACC).

Étapes du modèle :
  1. Projeter le compte de résultat simplifié (CA, EBITDA, EBIT)
  2. En déduire le Free Cash Flow to Firm (FCFF) : NOPAT + D&A - Capex - ΔBFR
  3. Calculer le WACC (coût des fonds propres par le MEDAF, bêta réendetté)
  4. Calculer la valeur terminale par deux méthodes (Gordon et multiple de sortie)
  5. Additionner les flux actualisés : valeur d'entreprise (EV)
  6. Passer de l'EV à la valeur des fonds propres, puis au prix par action
  7. Analyses de sensibilité et graphiques

Les données sont simulées. Toutes les valeurs monétaires sont en millions de MAD.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# =============================================================================
# 1. HYPOTHÈSES (seule partie à modifier pour valoriser une autre entreprise)
# =============================================================================

HYP = {
    # --- Point de départ (dernier exercice réel, année 0) ---
    "ca_annee_0": 5_000.0,

    # --- Hypothèses opérationnelles, une valeur par année projetée ---
    "croissance_ca": [0.08, 0.07, 0.06, 0.05, 0.04],
    "marge_ebitda":  [0.20, 0.205, 0.21, 0.215, 0.22],
    "da_pct_ca":     0.040,   # dotations aux amortissements, en % du CA
    "capex_pct_ca":  0.050,   # investissements, en % du CA
    "bfr_pct_ca":    0.120,   # besoin en fonds de roulement, en % du CA
    "taux_is":       0.25,    # taux d'impôt sur les sociétés (hypothèse)

    # --- Coût du capital ---
    "taux_sans_risque":     0.035,  # rendement d'une obligation d'État longue
    "prime_risque_marche":  0.060,  # rendement attendu du marché - taux sans risque
    "beta_desendette":      0.90,   # bêta de l'activité, sans effet de la dette
    "cout_dette_avant_is":  0.055,  # taux auquel l'entreprise emprunte
    "dette_sur_capitaux":   0.25,   # D / (D + E), structure financière cible

    # --- Valeur terminale ---
    "croissance_perpet": 0.025,   # croissance à l'infini après l'année N
    "multiple_sortie":   8.0,     # EV / EBITDA de sortie (comparables)

    # --- Pont de la valeur d'entreprise aux fonds propres ---
    "dette_financiere":  1_800.0,
    "tresorerie":          300.0,
    "interets_minoritaires": 100.0,
    "participations":       50.0,   # sociétés mises en équivalence
    "nombre_actions":      500.0,   # en millions
    "cours_actuel":         17.0,   # pour calculer le potentiel de hausse

    # --- Convention d'actualisation ---
    # True : les flux sont supposés reçus en milieu d'année (pratique courante
    # en banque d'affaires), False : en fin d'année.
    "mi_annee": True,
}


# =============================================================================
# 2. PROJECTION DU COMPTE DE RÉSULTAT ET DU FREE CASH FLOW
# =============================================================================

def projeter_flux(h):
    """Construit le tableau des flux, année par année."""
    n = len(h["croissance_ca"])
    annees = list(range(1, n + 1))

    ca, ca_prec = [], h["ca_annee_0"]
    for g in h["croissance_ca"]:
        ca_prec = ca_prec * (1 + g)
        ca.append(ca_prec)
    ca = np.array(ca)

    ebitda = ca * np.array(h["marge_ebitda"])
    da = ca * h["da_pct_ca"]
    ebit = ebitda - da
    impot = ebit * h["taux_is"]
    nopat = ebit - impot                      # résultat opérationnel après impôt
    capex = ca * h["capex_pct_ca"]

    # Le BFR suit le CA : sa variation consomme (ou libère) de la trésorerie
    bfr = ca * h["bfr_pct_ca"]
    bfr_prec = np.concatenate(([h["ca_annee_0"] * h["bfr_pct_ca"]], bfr[:-1]))
    var_bfr = bfr - bfr_prec

    fcff = nopat + da - capex - var_bfr

    return pd.DataFrame({
        "CA": ca, "EBITDA": ebitda, "D&A": da, "EBIT": ebit,
        "Impôt sur EBIT": impot, "NOPAT": nopat, "Capex": capex,
        "Variation BFR": var_bfr, "FCFF": fcff,
    }, index=pd.Index(annees, name="Année"))


# =============================================================================
# 3. COÛT MOYEN PONDÉRÉ DU CAPITAL (WACC)
# =============================================================================

def calculer_wacc(h):
    """
    Le bêta observé intègre l'effet de la dette. On part du bêta désendetté
    (risque de l'activité seule) et on le réendette à la structure cible
    avec la formule de Hamada : bL = bU x (1 + (1 - t) x D/E).
    """
    d = h["dette_sur_capitaux"]
    e = 1 - d
    t = h["taux_is"]

    beta_reendette = h["beta_desendette"] * (1 + (1 - t) * d / e)
    cout_fp = h["taux_sans_risque"] + beta_reendette * h["prime_risque_marche"]  # MEDAF
    cout_dette_net = h["cout_dette_avant_is"] * (1 - t)  # les intérêts sont déductibles

    wacc = e * cout_fp + d * cout_dette_net
    return {"beta_reendette": beta_reendette, "cout_fp": cout_fp,
            "cout_dette_net": cout_dette_net, "wacc": wacc}


# =============================================================================
# 4. ACTUALISATION ET VALEUR D'ENTREPRISE
# =============================================================================

def periodes(n, mi_annee):
    """Années d'actualisation : 0,5 ; 1,5 ; ... en milieu d'année, sinon 1 ; 2 ; ..."""
    t = np.arange(1, n + 1, dtype=float)
    return t - 0.5 if mi_annee else t


def valoriser(h, flux, wacc, g=None, multiple=None):
    """
    Calcule l'EV avec les deux méthodes de valeur terminale.
    g et multiple peuvent être forcés pour les analyses de sensibilité.
    """
    g = h["croissance_perpet"] if g is None else g
    multiple = h["multiple_sortie"] if multiple is None else multiple
    if g >= wacc:
        raise ValueError("La croissance perpétuelle doit être inférieure au WACC.")

    n = len(flux)
    t = periodes(n, h["mi_annee"])
    facteurs = 1 / (1 + wacc) ** t
    va_flux = (flux["FCFF"].values * facteurs).sum()

    fcff_n = flux["FCFF"].iloc[-1]
    ebitda_n = flux["EBITDA"].iloc[-1]

    # Méthode de Gordon : VT = FCFF(N+1) / (WACC - g)
    vt_gordon = fcff_n * (1 + g) / (wacc - g)
    # Méthode des multiples : VT = EBITDA(N) x multiple de sortie
    vt_multiple = ebitda_n * multiple

    # Gordon prolonge la même convention que les flux ; le multiple correspond
    # à un prix de cession encaissé à la fin de l'année N.
    va_vt_gordon = vt_gordon / (1 + wacc) ** t[-1]
    va_vt_multiple = vt_multiple / (1 + wacc) ** n

    return {
        "va_flux": va_flux,
        "vt_gordon": vt_gordon, "va_vt_gordon": va_vt_gordon,
        "vt_multiple": vt_multiple, "va_vt_multiple": va_vt_multiple,
        "ev_gordon": va_flux + va_vt_gordon,
        "ev_multiple": va_flux + va_vt_multiple,
        # Contrôles de cohérence entre les deux méthodes
        "multiple_implicite": vt_gordon / ebitda_n,
        "g_implicite": (vt_multiple * wacc - fcff_n) / (vt_multiple + fcff_n),
        "facteurs": facteurs,
    }


def pont_fonds_propres(h, ev):
    """Valeur d'entreprise -> valeur des fonds propres -> prix par action."""
    dette_nette = h["dette_financiere"] - h["tresorerie"]
    equity = ev - dette_nette - h["interets_minoritaires"] + h["participations"]
    prix = equity / h["nombre_actions"]
    return {"dette_nette": dette_nette, "equity": equity, "prix": prix,
            "potentiel": prix / h["cours_actuel"] - 1}


# =============================================================================
# 5. ANALYSES DE SENSIBILITÉ
# =============================================================================

def sensibilite(h, flux, wacc_centre, axe, valeurs_axe, methode):
    """Prix par action selon le WACC (lignes) et g ou le multiple (colonnes)."""
    liste_wacc = [wacc_centre + d for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    tableau = {}
    for v in valeurs_axe:
        colonne = []
        for w in liste_wacc:
            if axe == "g":
                r = valoriser(h, flux, w, g=v)
            else:
                r = valoriser(h, flux, w, multiple=v)
            colonne.append(pont_fonds_propres(h, r[methode])["prix"])
        tableau[v] = colonne
    df = pd.DataFrame(tableau, index=[f"{w:.1%}" for w in liste_wacc])
    df.index.name = "WACC"
    df.columns = [f"{v:.1%}" if axe == "g" else f"{v:.1f}x" for v in valeurs_axe]
    return df.round(2)


# =============================================================================
# 6. AFFICHAGE ET GRAPHIQUES
# =============================================================================

def afficher(h, flux, w, r, pont_g, pont_m):
    fmt = lambda x: f"{x:,.1f}".replace(",", " ")
    print("=" * 72)
    print("VALORISATION DCF (données simulées, millions de MAD)")
    print("=" * 72)
    print("\n1. Projection des flux\n")
    print(flux.T.map(lambda x: fmt(x)).to_string())

    print("\n2. Coût du capital")
    print(f"   Bêta réendetté (Hamada)        {w['beta_reendette']:.2f}")
    print(f"   Coût des fonds propres (MEDAF) {w['cout_fp']:.2%}")
    print(f"   Coût de la dette après impôt   {w['cout_dette_net']:.2%}")
    print(f"   WACC                           {w['wacc']:.2%}")

    print("\n3. Valeur d'entreprise           Gordon      Multiple")
    print(f"   VA des flux explicites     {fmt(r['va_flux']):>10}  {fmt(r['va_flux']):>12}")
    print(f"   VA de la valeur terminale  {fmt(r['va_vt_gordon']):>10}  {fmt(r['va_vt_multiple']):>12}")
    print(f"   Valeur d'entreprise        {fmt(r['ev_gordon']):>10}  {fmt(r['ev_multiple']):>12}")
    print(f"   Poids de la VT dans l'EV   {r['va_vt_gordon']/r['ev_gordon']:>10.1%}  "
          f"{r['va_vt_multiple']/r['ev_multiple']:>12.1%}")

    print("\n4. Contrôles de cohérence")
    print(f"   Multiple EV/EBITDA implicite de Gordon : {r['multiple_implicite']:.1f}x "
          f"(hypothèse de sortie : {h['multiple_sortie']:.1f}x)")
    print(f"   Croissance implicite du multiple       : {r['g_implicite']:.2%} "
          f"(hypothèse : {h['croissance_perpet']:.2%})")

    print("\n5. Des fonds propres au prix par action   Gordon      Multiple")
    print(f"   - Dette nette               {fmt(pont_g['dette_nette']):>10}  {fmt(pont_m['dette_nette']):>12}")
    print(f"   - Intérêts minoritaires     {fmt(h['interets_minoritaires']):>10}  {fmt(h['interets_minoritaires']):>12}")
    print(f"   + Participations            {fmt(h['participations']):>10}  {fmt(h['participations']):>12}")
    print(f"   = Valeur des fonds propres  {fmt(pont_g['equity']):>10}  {fmt(pont_m['equity']):>12}")
    print(f"   Prix par action             {pont_g['prix']:>10.2f}  {pont_m['prix']:>12.2f}")
    print(f"   Potentiel vs cours ({h['cours_actuel']:.2f})   {pont_g['potentiel']:>10.1%}  {pont_m['potentiel']:>12.1%}")


def tracer(flux, r, sens_g):
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    # (a) Construction du FCFF
    ax = axes[0]
    x = flux.index.values
    ax.bar(x - 0.2, flux["NOPAT"], 0.4, label="NOPAT", color="#4C72B0")
    ax.bar(x + 0.2, flux["FCFF"], 0.4, label="FCFF", color="#DD8452")
    ax.plot(x, flux["FCFF"] * r["facteurs"], "o-", color="#2E7D32", label="FCFF actualisé")
    ax.set_title("Du résultat opérationnel au cash-flow disponible")
    ax.set_xlabel("Année")
    ax.set_ylabel("Millions de MAD")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # (b) Composition de la valeur d'entreprise
    ax = axes[1]
    methodes = ["Gordon", "Multiple"]
    va_flux = [r["va_flux"], r["va_flux"]]
    va_vt = [r["va_vt_gordon"], r["va_vt_multiple"]]
    ax.bar(methodes, va_flux, color="#4C72B0", label="Flux explicites")
    ax.bar(methodes, va_vt, bottom=va_flux, color="#8C8C8C", label="Valeur terminale")
    ax.set_title("Composition de la valeur d'entreprise")
    ax.set_ylabel("Millions de MAD")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # (c) Carte de sensibilité
    ax = axes[2]
    im = ax.imshow(sens_g.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(sens_g.columns)), sens_g.columns)
    ax.set_yticks(range(len(sens_g.index)), sens_g.index)
    for i in range(sens_g.shape[0]):
        for j in range(sens_g.shape[1]):
            ax.text(j, i, f"{sens_g.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
    ax.set_xlabel("Croissance perpétuelle g")
    ax.set_ylabel("WACC")
    ax.set_title("Prix par action (Gordon)")
    fig.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    plt.savefig("dcf_graphique.png", dpi=120)
    print("\nGraphique enregistré : dcf_graphique.png")


def exporter_excel(flux, w, r, pont_g, pont_m, sens_g, sens_m):
    """Exporte les résultats dans un classeur, format habituel des analystes."""
    with pd.ExcelWriter("dcf_resultats.xlsx") as xl:
        flux.T.round(1).to_excel(xl, sheet_name="Flux")
        pd.Series({
            "Bêta réendetté": round(w["beta_reendette"], 3),
            "Coût des fonds propres": round(w["cout_fp"], 4),
            "Coût de la dette après IS": round(w["cout_dette_net"], 4),
            "WACC": round(w["wacc"], 4),
            "EV (Gordon)": round(r["ev_gordon"], 1),
            "EV (multiple)": round(r["ev_multiple"], 1),
            "Prix par action (Gordon)": round(pont_g["prix"], 2),
            "Prix par action (multiple)": round(pont_m["prix"], 2),
        }, name="Valeur").to_excel(xl, sheet_name="Synthèse")
        sens_g.to_excel(xl, sheet_name="Sensibilité WACC x g")
        sens_m.to_excel(xl, sheet_name="Sensibilité WACC x multiple")
    print("Classeur enregistré : dcf_resultats.xlsx")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    flux = projeter_flux(HYP)
    w = calculer_wacc(HYP)
    r = valoriser(HYP, flux, w["wacc"])
    pont_g = pont_fonds_propres(HYP, r["ev_gordon"])
    pont_m = pont_fonds_propres(HYP, r["ev_multiple"])

    afficher(HYP, flux, w, r, pont_g, pont_m)

    sens_g = sensibilite(HYP, flux, w["wacc"], "g", [0.015, 0.02, 0.025, 0.03, 0.035], "ev_gordon")
    sens_m = sensibilite(HYP, flux, w["wacc"], "multiple", [6.0, 7.0, 8.0, 9.0, 10.0], "ev_multiple")
    print("\n6. Sensibilité du prix par action (Gordon) : WACC x g\n")
    print(sens_g.to_string())
    print("\n7. Sensibilité du prix par action (multiple) : WACC x multiple de sortie\n")
    print(sens_m.to_string())

    tracer(flux, r, sens_g)
    try:
        exporter_excel(flux, w, r, pont_g, pont_m, sens_g, sens_m)
    except ImportError:
        print("Export Excel ignoré (installer openpyxl pour l'activer).")
