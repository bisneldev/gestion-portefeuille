"""
Analyse de risque du portefeuille
Calcul de la VaR, CVaR, stress tests et backtesting
Conforme aux principes de Bâle III
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from scipy import stats


# =====================================================================
# CONFIGURATION
# =====================================================================
JOURS_TRADING = 252
NIVEAUX_CONFIANCE = [0.90, 0.95, 0.99]
HORIZON_JOURS = [1, 10]  # VaR à 1 jour et 10 jours (Bâle III)

COLORS = {
    'primaire': '#1f3a5f',
    'accent': '#e63946',
    'success': '#2a9d8f',
    'warning': '#f4a261',
    'light': '#f5f7fa',
}


# =====================================================================
# CHARGEMENT
# =====================================================================
def charger_prix(path='data/raw/prix_actions.csv'):
    df = pd.read_csv(path, parse_dates=['date'])
    df_wide = df.pivot(index='date', columns='ticker', values='prix').sort_index()
    return df_wide


# =====================================================================
# VaR ET CVaR
# =====================================================================
def calculer_var(rendements, niveau=0.95):
    """
    VaR historique (méthode non-paramétrique).
    Retourne la perte maximale au niveau de confiance donné.
    """
    return -np.percentile(rendements, (1 - niveau) * 100)


def calculer_cvar(rendements, niveau=0.95):
    """
    CVaR (Expected Shortfall) = perte moyenne au-delà de la VaR.
    """
    var = calculer_var(rendements, niveau)
    return -rendements[rendements <= -var].mean()


def calculer_var_10j(rendements, niveau=0.95):
    """
    VaR à 10 jours (réglementaire Bâle III).
    Formule : VaR_10j = VaR_1j × √10
    """
    var_1j = calculer_var(rendements, niveau)
    return var_1j * np.sqrt(10)


def metriques_risque_par_action(prix):
    """Calcule les métriques de risque pour chaque action"""
    rendements = prix.pct_change().dropna()
    
    metriques = []
    for ticker in prix.columns:
        r = rendements[ticker].dropna()
        prix_actuel = prix[ticker].iloc[-1]
        
        row = {'ticker': ticker}
        
        for niveau in NIVEAUX_CONFIANCE:
            var = calculer_var(r, niveau)
            cvar = calculer_cvar(r, niveau)
            row[f'var_{int(niveau*100)}_pct'] = round(var * 100, 3)
            row[f'cvar_{int(niveau*100)}_pct'] = round(cvar * 100, 3)
            # VaR en FCFA pour 1 million investi
            row[f'var_{int(niveau*100)}_fcfa_1M'] = round(var * 1_000_000, 0)
        
        # VaR 10 jours réglementaire
        row['var_10j_pct'] = round(calculer_var_10j(r, 0.99) * 100, 2)
        
        metriques.append(row)
    
    return pd.DataFrame(metriques)


# =====================================================================
# STRESS TESTS
# =====================================================================
SCENARIOS_STRESS = {
    'Crise 2008': {
        'description': 'Crise financière mondiale',
        'choc_marche': -0.40,
        'duree_jours': 20
    },
    'COVID-19': {
        'description': 'Pandémie mondiale',
        'choc_marche': -0.30,
        'duree_jours': 15
    },
    'Choc pétrolier': {
        'description': 'Effondrement du prix du pétrole',
        'choc_marche': -0.20,
        'duree_jours': 10
    },
    'Crise monétaire CEMAC': {
        'description': 'Dévaluation FCFA',
        'choc_marche': -0.15,
        'duree_jours': 5
    },
    'Krach boursier': {
        'description': 'Correction brutale des marchés',
        'choc_marche': -0.25,
        'duree_jours': 10
    },
}


def stress_test_portefeuille(prix, capital=1_000_000_000):
    """Applique des scénarios de stress au portefeuille"""
    rendements = prix.pct_change().dropna()
    poids = np.ones(len(prix.columns)) / len(prix.columns)
    
    # Portefeuille équipondéré
    r_portefeuille = rendements.dot(poids)
    volatilite_quotidienne = r_portefeuille.std()
    
    resultats = []
    for nom, scenario in SCENARIOS_STRESS.items():
        # Impact = choc de marché × sensibilité du portefeuille
        # Hypothèse : le portefeuille subit 80 % du choc de marché
        impact_pct = scenario['choc_marche'] * 0.80
        impact_fcfa = capital * impact_pct
        
        # Pire journée (basé sur la volatilité du portefeuille)
        pire_jour = -volatilite_quotidienne * 3  # 3 sigma
        
        resultats.append({
            'scenario': nom,
            'description': scenario['description'],
            'choc_marche_pct': round(scenario['choc_marche'] * 100, 1),
            'impact_portefeuille_pct': round(impact_pct * 100, 2),
            'impact_fcfa': round(impact_fcfa, 0),
            'capital_apres_fcfa': round(capital + impact_fcfa, 0),
            'perte_pct_capital': round(abs(impact_pct) * 100, 2),
        })
    
    return pd.DataFrame(resultats)


# =====================================================================
# BACKTESTING
# =====================================================================
def backtesting_var(prix, niveau=0.95):
    """
    Backtesting de la VaR : combien de fois la VaR a-t-elle été dépassée ?
    Une VaR 95 % doit être dépassée ~5 % du temps.
    """
    rendements = prix.pct_change().dropna()
    poids = np.ones(len(prix.columns)) / len(prix.columns)
    r_portefeuille = rendements.dot(poids)
    
    # VaR glissante sur 250 jours (1 an)
    fenetre = 250
    var_glissante = []
    depassements = []
    
    for i in range(fenetre, len(r_portefeuille)):
        r_hist = r_portefeuille.iloc[i-fenetre:i]
        var = -np.percentile(r_hist, (1 - niveau) * 100)
        var_glissante.append(var)
        depassements.append(r_portefeuille.iloc[i] < -var)
    
    var_glissante = pd.Series(var_glissante, index=r_portefeuille.index[fenetre:])
    depassements = pd.Series(depassements, index=r_portefeuille.index[fenetre:])
    
    taux_depassement = depassements.mean() * 100
    taux_attendu = (1 - niveau) * 100
    
    return {
        'taux_depassement_pct': round(taux_depassement, 2),
        'taux_attendu_pct': taux_attendu,
        'nb_depassements': int(depassements.sum()),
        'nb_observations': len(depassements),
        'conforme': abs(taux_depassement - taux_attendu) < 2,  # tolérance 2 %
        'var_glissante': var_glissante,
        'rendements': r_portefeuille.iloc[fenetre:],
        'depassements': depassements,
    }


# =====================================================================
# GRAPHIQUES
# =====================================================================
def graphique_distribution_var(prix):
    """Distribution des rendements avec VaR marquée"""
    rendements = prix.pct_change().dropna()
    poids = np.ones(len(prix.columns)) / len(prix.columns)
    r_portefeuille = rendements.dot(poids) * 100
    
    fig = go.Figure()
    
    # Histogramme
    fig.add_trace(go.Histogram(
        x=r_portefeuille, nbinsx=100,
        name='Rendements',
        marker_color=COLORS['primaire'],
        opacity=0.7
    ))
    
    # VaR 95 %
    var_95 = -calculer_var(rendements.dot(poids), 0.95) * 100
    var_99 = -calculer_var(rendements.dot(poids), 0.99) * 100
    cvar_95 = -calculer_cvar(rendements.dot(poids), 0.95) * 100
    
    fig.add_vline(x=var_95, line_dash="dash", line_color=COLORS['warning'],
                  annotation_text=f"VaR 95% = {var_95:.2f}%",
                  annotation_position="top")
    fig.add_vline(x=var_99, line_dash="dash", line_color=COLORS['accent'],
                  annotation_text=f"VaR 99% = {var_99:.2f}%",
                  annotation_position="top right")
    fig.add_vline(x=cvar_95, line_dash="dot", line_color='purple',
                  annotation_text=f"CVaR 95% = {cvar_95:.2f}%",
                  annotation_position="bottom right")
    
    fig.update_layout(
        title="📊 Distribution des rendements du portefeuille et VaR",
        template='plotly_white',
        height=500,
        xaxis_title="Rendement journalier (%)",
        yaxis_title="Fréquence",
        showlegend=False
    )
    return fig


def graphique_var_par_action(metriques):
    """Comparaison des VaR par action"""
    df = metriques.sort_values('var_95_pct', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df['ticker'], x=df['var_90_pct'],
        name='VaR 90%', orientation='h',
        marker_color='#8ecae6'
    ))
    fig.add_trace(go.Bar(
        y=df['ticker'], x=df['var_95_pct'],
        name='VaR 95%', orientation='h',
        marker_color=COLORS['warning']
    ))
    fig.add_trace(go.Bar(
        y=df['ticker'], x=df['var_99_pct'],
        name='VaR 99%', orientation='h',
        marker_color=COLORS['accent']
    ))
    
    fig.update_layout(
        title="⚠️ VaR par action (perte journalière en %)",
        barmode='group',
        template='plotly_white',
        height=500,
        xaxis_title="VaR (%)"
    )
    return fig


def graphique_backtesting(bt):
    """Backtesting de la VaR"""
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=('Rendements du portefeuille vs VaR glissante',
                        'Dépassements de la VaR')
    )
    
    # Rendements
    fig.add_trace(go.Scatter(
        x=bt['rendements'].index, y=bt['rendements'] * 100,
        name='Rendements', mode='lines',
        line=dict(color=COLORS['primaire'], width=1)
    ), row=1, col=1)
    
    # VaR 95 %
    fig.add_trace(go.Scatter(
        x=bt['var_glissante'].index, y=-bt['var_glissante'] * 100,
        name='VaR 95%', mode='lines',
        line=dict(color=COLORS['accent'], width=2, dash='dash')
    ), row=1, col=1)
    
    # Dépassements
    depassements_vals = bt['rendements'] * bt['depassements'].astype(int) * 100
    fig.add_trace(go.Bar(
        x=depassements_vals.index, y=depassements_vals,
        name='Dépassements', marker_color=COLORS['accent']
    ), row=2, col=1)
    
    fig.update_layout(
        title=f"📊 Backtesting VaR 95% — {bt['taux_depassement_pct']:.2f}% de dépassements "
              f"(attendu : {bt['taux_attendu_pct']:.1f}%)",
        template='plotly_white',
        height=700,
        showlegend=True
    )
    return fig


def graphique_stress_tests(df_stress):
    """Graphique des stress tests"""
    df_sorted = df_stress.sort_values('impact_portefeuille_pct')
    
    colors = [COLORS['accent'] if x < -0.20 else COLORS['warning'] 
              for x in df_sorted['impact_portefeuille_pct']]
    
    fig = go.Figure(go.Bar(
        y=df_sorted['scenario'],
        x=df_sorted['impact_portefeuille_pct'] * 100,
        orientation='h',
        marker_color=colors,
        text=[f"{x*100:.1f}%" for x in df_sorted['impact_portefeuille_pct']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="🔥 Stress tests — Impact sur le portefeuille (%)",
        template='plotly_white',
        height=450,
        xaxis_title="Impact (%)",
        yaxis_title=""
    )
    return fig


# =====================================================================
# RAPPORT COMPLET
# =====================================================================
def generer_rapport(prix, capital=1_000_000_000, output_dir='reports/risque'):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 75)
    print("⚠️  ANALYSE DE RISQUE DU PORTEFEUILLE")
    print("=" * 75)
    print(f"\n💼 Capital analysé : {capital/1e9:.2f} Md FCFA")
    
    # ---- VaR par action ----
    metriques = metriques_risque_par_action(prix)
    print(f"\n📊 VaR ET CVaR PAR ACTION")
    print("─" * 100)
    print(metriques[['ticker', 'var_90_pct', 'var_95_pct', 'var_99_pct',
                     'cvar_95_pct', 'var_10j_pct']].to_string(index=False))
    
    # ---- VaR portefeuille ----
    rendements = prix.pct_change().dropna()
    poids = np.ones(len(prix.columns)) / len(prix.columns)
    r_portefeuille = rendements.dot(poids)
    
    print(f"\n📊 VaR DU PORTEFEUILLE ÉQUIPONDÉRÉ")
    print("─" * 75)
    for niveau in NIVEAUX_CONFIANCE:
        var = calculer_var(r_portefeuille, niveau)
        cvar = calculer_cvar(r_portefeuille, niveau)
        print(f"   • VaR {int(niveau*100)}% (1 jour)  : {var*100:>6.3f} %  "
              f"({var*capital:>15,.0f} FCFA)")
        print(f"     CVaR {int(niveau*100)}%           : {cvar*100:>6.3f} %  "
              f"({cvar*capital:>15,.0f} FCFA)")
    
    var_10j = calculer_var_10j(r_portefeuille, 0.99)
    print(f"\n   • VaR 99% (10 jours, Bâle III) : {var_10j*100:>6.3f} %  "
          f"({var_10j*capital:>15,.0f} FCFA)")
    
    # ---- Stress tests ----
    df_stress = stress_test_portefeuille(prix, capital)
    print(f"\n🔥 STRESS TESTS — SCÉNARIOS EXTRÊMES")
    print("─" * 100)
    print(df_stress[['scenario', 'description', 'choc_marche_pct',
                     'impact_portefeuille_pct', 'impact_fcfa']].to_string(index=False))
    
    # ---- Backtesting ----
    bt = backtesting_var(prix)
    print(f"\n📊 BACKTESTING DE LA VaR 95%")
    print("─" * 75)
    print(f"   • Nombre d'observations   : {bt['nb_observations']:,}")
    print(f"   • Nombre de dépassements  : {bt['nb_depassements']}")
    print(f"   • Taux de dépassement     : {bt['taux_depassement_pct']:.2f} %")
    print(f"   • Taux attendu (théorique): {bt['taux_attendu_pct']:.2f} %")
    statut = "✅ CONFORME" if bt['conforme'] else "⚠️ À REVOIR"
    print(f"   • Statut                  : {statut}")
    
    # ---- Graphiques ----
    print(f"\n📈 Génération des graphiques...")
    graphiques = {}
    
    graphiques['01_distribution_var'] = graphique_distribution_var(prix)
    graphiques['02_var_par_action'] = graphique_var_par_action(metriques)
    graphiques['03_backtesting'] = graphique_backtesting(bt)
    graphiques['04_stress_tests'] = graphique_stress_tests(df_stress)
    
    for nom, fig in graphiques.items():
        chemin = f"{output_dir}/{nom}.html"
        fig.write_html(chemin)
        print(f"   ✅ {nom}.html")
    
    # ---- Sauvegarde CSV ----
    metriques.to_csv(f"{output_dir}/var_par_action.csv", index=False)
    df_stress.to_csv(f"{output_dir}/stress_tests.csv", index=False)
    
    print(f"\n💾 CSV sauvegardés dans {output_dir}/")
    
    return metriques, df_stress, bt


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("🔄 Chargement des prix...")
    prix = charger_prix()
    
    # Analyse risque
    metriques, df_stress, bt = generer_rapport(prix, capital=1_000_000_000)
    
    print("\n" + "=" * 75)
    print("✅ ANALYSE DE RISQUE TERMINÉE")
    print("=" * 75)