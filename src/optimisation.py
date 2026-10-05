"""
Optimisation de portefeuille - Modèle de Markowitz
Frontière efficiente, portefeuille tangent, allocation optimale
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from scipy.optimize import minimize


# =====================================================================
# CONFIGURATION
# =====================================================================
TAUX_SANS_RISQUE = 0.038
JOURS_TRADING = 252
N_SIMULATIONS = 10000

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
def charger_donnees(path='data/raw/prix_actions.csv'):
    df = pd.read_csv(path, parse_dates=['date'])
    df_wide = df.pivot(index='date', columns='ticker', values='prix').sort_index()
    rendements = df_wide.pct_change().dropna()
    return df_wide, rendements


# =====================================================================
# STATISTIQUES DES ACTIFS
# =====================================================================
def stats_actifs(rendements):
    """Rendements et volatilités annualisés par actif"""
    rendements_annuels = rendements.mean() * JOURS_TRADING
    volatilites_annuelles = rendements.std() * np.sqrt(JOURS_TRADING)
    
    df = pd.DataFrame({
        'rendement_annuel': rendements_annuels,
        'volatilite_annuelle': volatilites_annuelles,
    })
    df['ratio_sharpe'] = (df['rendement_annuel'] - TAUX_SANS_RISQUE) / df['volatilite_annuelle']
    df = df.sort_values('ratio_sharpe', ascending=False)
    
    return df


# =====================================================================
# SIMULATION DE PORTEFEUILLES ALÉATOIRES
# =====================================================================
def simuler_portefeuilles(rendements, n_sim=N_SIMULATIONS, seed=42):
    """
    Simule n_sim portefeuilles aléatoires.
    Calcule rendement, volatilité et Sharpe pour chacun.
    """
    np.random.seed(seed)
    
    n_actifs = rendements.shape[1]
    tickers = rendements.columns.tolist()
    
    # Rendements et covariance annualisés
    rendements_moyens = rendements.mean() * JOURS_TRADING
    cov_matrix = rendements.cov() * JOURS_TRADING
    
    resultats = np.zeros((n_sim, 4))
    poids_list = []
    
    for i in range(n_sim):
        # Génération de poids aléatoires (somme = 1)
        poids = np.random.random(n_actifs)
        poids /= poids.sum()
        
        # Rendement et volatilité du portefeuille
        rendement = np.dot(poids, rendements_moyens)
        volatilite = np.sqrt(np.dot(poids.T, np.dot(cov_matrix, poids)))
        sharpe = (rendement - TAUX_SANS_RISQUE) / volatilite
        
        resultats[i] = [rendement, volatilite, sharpe, i]
        poids_list.append(poids)
    
    df = pd.DataFrame(resultats, columns=['rendement', 'volatilite', 'sharpe', 'id'])
    df['poids'] = poids_list
    
    return df, rendements_moyens, cov_matrix


# =====================================================================
# OPTIMISATION
# =====================================================================
def optimiser_portefeuille(rendements, objectif='sharpe'):
    """
    Optimise le portefeuille selon l'objectif :
    - 'sharpe' : maximise le ratio de Sharpe (portefeuille tangent)
    - 'min_var' : minimise la volatilité
    """
    n_actifs = rendements.shape[1]
    tickers = rendements.columns.tolist()
    
    rendements_moyens = rendements.mean() * JOURS_TRADING
    cov_matrix = rendements.cov() * JOURS_TRADING
    
    # Contraintes : somme des poids = 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    # Bornes : poids entre 0 et 1 (pas de vente à découvert)
    bounds = tuple((0, 1) for _ in range(n_actifs))
    # Point de départ : équipondéré
    initial = np.array([1/n_actifs] * n_actifs)
    
    if objectif == 'sharpe':
        def neg_sharpe(w):
            r = np.dot(w, rendements_moyens)
            v = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            return -(r - TAUX_SANS_RISQUE) / v
        result = minimize(neg_sharpe, initial, method='SLSQP',
                         bounds=bounds, constraints=constraints)
    else:  # min_var
        def variance(w):
            return np.dot(w.T, np.dot(cov_matrix, w))
        result = minimize(variance, initial, method='SLSQP',
                         bounds=bounds, constraints=constraints)
    
    poids_opt = result.x
    rendement_opt = np.dot(poids_opt, rendements_moyens)
    volatilite_opt = np.sqrt(np.dot(poids_opt.T, np.dot(cov_matrix, poids_opt)))
    sharpe_opt = (rendement_opt - TAUX_SANS_RISQUE) / volatilite_opt
    
    return {
        'poids': dict(zip(tickers, poids_opt)),
        'rendement': rendement_opt,
        'volatilite': volatilite_opt,
        'sharpe': sharpe_opt,
    }


# =====================================================================
# PORTEFEUILLES PAR PROFIL
# =====================================================================
def portefeuille_par_profil(rendements, profil):
    """
    Construit un portefeuille adapté au profil d'investisseur.
    - Prudent : minimise la variance
    - Équilibré : équipondéré avec tilt
    - Dynamique : maximise le Sharpe
    """
    if profil == 'Prudent':
        # Minimise la variance
        result = optimiser_portefeuille(rendements, 'min_var')
    elif profil == 'Dynamique':
        # Maximise le Sharpe
        result = optimiser_portefeuille(rendements, 'sharpe')
    else:  # Équilibré
        # Mix 50/50 entre min_var et sharpe
        r1 = optimiser_portefeuille(rendements, 'min_var')
        r2 = optimiser_portefeuille(rendements, 'sharpe')
        
        poids_mix = {
            k: 0.5 * r1['poids'][k] + 0.5 * r2['poids'][k]
            for k in r1['poids']
        }
        
        rendements_moyens = rendements.mean() * JOURS_TRADING
        cov_matrix = rendements.cov() * JOURS_TRADING
        w = np.array(list(poids_mix.values()))
        
        result = {
            'poids': poids_mix,
            'rendement': np.dot(w, rendements_moyens),
            'volatilite': np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))),
        }
        result['sharpe'] = (result['rendement'] - TAUX_SANS_RISQUE) / result['volatilite']
    
    return result


# =====================================================================
# GRAPHIQUES
# =====================================================================
def graphique_frontiere(df_sim, portefeuille_tangent, portefeuille_min_var):
    """Frontière efficiente avec les portefeuilles optimaux"""
    fig = go.Figure()
    
    # Nuage de points (tous les portefeuilles simulés)
    fig.add_trace(go.Scatter(
        x=df_sim['volatilite'] * 100,
        y=df_sim['rendement'] * 100,
        mode='markers',
        marker=dict(
            size=5,
            color=df_sim['sharpe'],
            colorscale='RdYlGn',
            colorbar=dict(title="Sharpe"),
            showscale=True,
        ),
        name='Portefeuilles simulés',
        hovertemplate='Volatilité: %{x:.2f}%<br>Rendement: %{y:.2f}%<extra></extra>'
    ))
    
    # Portefeuille tangent (max Sharpe)
    fig.add_trace(go.Scatter(
        x=[portefeuille_tangent['volatilite'] * 100],
        y=[portefeuille_tangent['rendement'] * 100],
        mode='markers+text',
        marker=dict(size=20, color='red', symbol='star',
                    line=dict(color='white', width=2)),
        text=['⭐ Max Sharpe'],
        textposition='top center',
        name='Max Sharpe',
        hovertemplate='Sharpe: %{customdata:.3f}<extra></extra>',
        customdata=[portefeuille_tangent['sharpe']]
    ))
    
    # Portefeuille à variance minimale
    fig.add_trace(go.Scatter(
        x=[portefeuille_min_var['volatilite'] * 100],
        y=[portefeuille_min_var['rendement'] * 100],
        mode='markers+text',
        marker=dict(size=20, color='blue', symbol='diamond',
                    line=dict(color='white', width=2)),
        text=['💎 Min Variance'],
        textposition='top center',
        name='Min Variance'
    ))
    
    fig.update_layout(
        title="🎯 Frontière efficiente de Markowitz",
        template='plotly_white',
        height=600,
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)",
        hovermode='closest'
    )
    return fig


def graphique_allocation_optimale(portefeuille_tangent, portefeuille_min_var):
    """Comparaison des allocations optimales"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('⭐ Portefeuille Max Sharpe', '💎 Portefeuille Min Variance'),
        specs=[[{'type': 'pie'}, {'type': 'pie'}]]
    )
    
    # Max Sharpe
    poids_sharpe = portefeuille_tangent['poids']
    # Filtrer les poids > 1 % pour la lisibilité
    poids_sharpe_filtres = {k: v for k, v in poids_sharpe.items() if v > 0.01}
    
    fig.add_trace(go.Pie(
        labels=list(poids_sharpe_filtres.keys()),
        values=list(poids_sharpe_filtres.values()),
        hole=0.4,
        textinfo='label+percent',
        marker=dict(line=dict(color='white', width=2))
    ), row=1, col=1)
    
    # Min Variance
    poids_minvar = portefeuille_min_var['poids']
    poids_minvar_filtres = {k: v for k, v in poids_minvar.items() if v > 0.01}
    
    fig.add_trace(go.Pie(
        labels=list(poids_minvar_filtres.keys()),
        values=list(poids_minvar_filtres.values()),
        hole=0.4,
        textinfo='label+percent',
        marker=dict(line=dict(color='white', width=2))
    ), row=1, col=2)
    
    fig.update_layout(
        title_text="💼 Allocation optimale des portefeuilles",
        template='plotly_white',
        height=500
    )
    return fig


def graphique_profils(rendements, portefeuille_tangent, portefeuille_min_var):
    """Comparaison des 3 profils clients"""
    profils = ['Prudent', 'Équilibré', 'Dynamique']
    resultats = []
    
    for profil in profils:
        r = portefeuille_par_profil(rendements, profil)
        resultats.append({
            'profil': profil,
            'rendement': r['rendement'] * 100,
            'volatilite': r['volatilite'] * 100,
            'sharpe': r['sharpe'],
        })
    
    df = pd.DataFrame(resultats)
    
    fig = go.Figure()
    
    colors = {'Prudent': COLORS['success'], 
              'Équilibré': COLORS['warning'],
              'Dynamique': COLORS['accent']}
    
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['volatilite']],
            y=[row['rendement']],
            mode='markers+text',
            marker=dict(size=30, color=colors[row['profil']],
                        line=dict(color='white', width=2)),
            text=[f"{row['profil']}<br>Sharpe: {row['sharpe']:.2f}"],
            textposition='top center',
            name=row['profil'],
            showlegend=False
        ))
    
    fig.update_layout(
        title="👥 Portefeuilles recommandés par profil client",
        template='plotly_white',
        height=500,
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)"
    )
    
    return fig, df


# =====================================================================
# RAPPORT COMPLET
# =====================================================================
def generer_rapport(rendements, output_dir='reports/optimisation'):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 75)
    print("🎯 OPTIMISATION DE PORTEFEUILLE — MARKOWITZ")
    print("=" * 75)
    
    # ---- Stats des actifs ----
    stats = stats_actifs(rendements)
    print(f"\n📊 STATISTIQUES DES ACTIFS")
    print("─" * 75)
    print(stats.round(4).to_string())
    
    # ---- Simulation ----
    print(f"\n🎲 Simulation de {N_SIMULATIONS:,} portefeuilles...")
    df_sim, r_moyens, cov = simuler_portefeuilles(rendements)
    
    best_sharpe = df_sim.loc[df_sim['sharpe'].idxmax()]
    best_minvar = df_sim.loc[df_sim['volatilite'].idxmin()]
    
    print(f"✅ Simulation terminée")
    print(f"\n   Meilleur Sharpe simulé   : {best_sharpe['sharpe']:.4f}")
    print(f"   Rendement / Volatilité   : {best_sharpe['rendement']*100:.2f} % / {best_sharpe['volatilite']*100:.2f} %")
    print(f"   Min Variance simulée     : {best_minvar['volatilite']*100:.2f} %")
    
    # ---- Optimisation formelle ----
    print(f"\n🔬 OPTIMISATION FORMELLE")
    print("─" * 75)
    
    tangent = optimiser_portefeuille(rendements, 'sharpe')
    min_var = optimiser_portefeuille(rendements, 'min_var')
    
    print(f"\n⭐ Portefeuille MAX SHARPE (tangent)")
    print(f"   • Rendement annualisé  : {tangent['rendement']*100:>6.2f} %")
    print(f"   • Volatilité annualisée: {tangent['volatilite']*100:>6.2f} %")
    print(f"   • Ratio de Sharpe      : {tangent['sharpe']:>6.3f}")
    print(f"   • Allocation :")
    for ticker, poids in sorted(tangent['poids'].items(), key=lambda x: -x[1]):
        if poids > 0.01:
            print(f"      {ticker:6s} : {poids*100:>5.1f} %")
    
    print(f"\n💎 Portefeuille MIN VARIANCE")
    print(f"   • Rendement annualisé  : {min_var['rendement']*100:>6.2f} %")
    print(f"   • Volatilité annualisée: {min_var['volatilite']*100:>6.2f} %")
    print(f"   • Ratio de Sharpe      : {min_var['sharpe']:>6.3f}")
    print(f"   • Allocation :")
    for ticker, poids in sorted(min_var['poids'].items(), key=lambda x: -x[1]):
        if poids > 0.01:
            print(f"      {ticker:6s} : {poids*100:>5.1f} %")
    
    # ---- Profils clients ----
    print(f"\n👥 PORTEFEUILLES PAR PROFIL CLIENT")
    print("─" * 75)
    
    profils_data = []
    for profil in ['Prudent', 'Équilibré', 'Dynamique']:
        r = portefeuille_par_profil(rendements, profil)
        profils_data.append({
            'profil': profil,
            'rendement_pct': round(r['rendement']*100, 2),
            'volatilite_pct': round(r['volatilite']*100, 2),
            'sharpe': round(r['sharpe'], 3),
        })
        print(f"\n{profil}")
        print(f"   • Rendement : {r['rendement']*100:>6.2f} %")
        print(f"   • Volatilité: {r['volatilite']*100:>6.2f} %")
        print(f"   • Sharpe    : {r['sharpe']:>6.3f}")
    
    # ---- Graphiques ----
    print(f"\n📈 Génération des graphiques...")
    graphiques = {}
    
    graphiques['01_frontiere_efficiente'] = graphique_frontiere(df_sim, tangent, min_var)
    graphiques['02_allocation_optimale'] = graphique_allocation_optimale(tangent, min_var)
    fig_profils, df_profils = graphique_profils(rendements, tangent, min_var)
    graphiques['03_profils_clients'] = fig_profils
    
    for nom, fig in graphiques.items():
        chemin = f"{output_dir}/{nom}.html"
        fig.write_html(chemin)
        print(f"   ✅ {nom}.html")
    
    # ---- Sauvegarde ----
    stats.to_csv(f"{output_dir}/stats_actifs.csv")
    pd.DataFrame([{
        'portefeuille': 'Max Sharpe',
        'rendement_pct': round(tangent['rendement']*100, 2),
        'volatilite_pct': round(tangent['volatilite']*100, 2),
        'sharpe': round(tangent['sharpe'], 3),
        **{f'poids_{k}': round(v*100, 2) for k, v in tangent['poids'].items()}
    }]).to_csv(f"{output_dir}/portefeuille_tangent.csv", index=False)
    
    pd.DataFrame(profils_data).to_csv(f"{output_dir}/profils_clients.csv", index=False)
    
    print(f"\n💾 CSV sauvegardés dans {output_dir}/")
    
    return tangent, min_var, df_profils


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("🔄 Chargement des données...")
    prix, rendements = charger_donnees()
    print(f"✅ {rendements.shape[0]:,} jours × {rendements.shape[1]} actions")
    
    # Optimisation
    tangent, min_var, df_profils = generer_rapport(rendements)
    
    print("\n" + "=" * 75)
    print("✅ OPTIMISATION TERMINÉE")
    print("=" * 75)