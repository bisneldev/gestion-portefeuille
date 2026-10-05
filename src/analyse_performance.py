"""
Analyse de performance des actions BRVM
Calcul des métriques clés : rendement, volatilité, Sharpe, drawdown
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path


# =====================================================================
# CONFIGURATION
# =====================================================================
TAUX_SANS_RISQUE = 0.038  # Taux BEAC 2025 (%)
JOURS_TRADING = 252       # Jours de trading par an

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
    """Charge les prix et les pivote en format wide (colonnes = tickers)"""
    df = pd.read_csv(path, parse_dates=['date'])
    
    # Pivot : 1 ligne par date, 1 colonne par ticker
    df_wide = df.pivot(index='date', columns='ticker', values='prix')
    
    # Trier par date
    df_wide = df_wide.sort_index()
    
    print(f"✅ Prix chargés : {df_wide.shape[0]} jours × {df_wide.shape[1]} actions")
    print(f"   Période : {df_wide.index[0].date()} → {df_wide.index[-1].date()}")
    return df_wide


# =====================================================================
# MÉTRIQUES DE PERFORMANCE
# =====================================================================
def calculer_rendements(prix):
    """Calcule les rendements journaliers"""
    return prix.pct_change().dropna()


def metriques_par_action(prix):
    """
    Calcule les métriques de performance pour chaque action.
    """
    rendements = calculer_rendements(prix)
    
    metriques = []
    for ticker in prix.columns:
        serie = prix[ticker].dropna()
        r = rendements[ticker].dropna()
        
        # Performance cumulée
        perf_cumulee = (serie.iloc[-1] / serie.iloc[0] - 1) * 100
        
        # Rendement annualisé (moyenne géométrique)
        n_annees = len(serie) / JOURS_TRADING
        rendement_annuel = ((serie.iloc[-1] / serie.iloc[0]) ** (1/n_annees) - 1) * 100
        
        # Volatilité annualisée
        volatilite_annuelle = r.std() * np.sqrt(JOURS_TRADING) * 100
        
        # Ratio de Sharpe
        rendement_annuel_dec = rendement_annuel / 100
        volatilite_dec = volatilite_annuelle / 100
        sharpe = (rendement_annuel_dec - TAUX_SANS_RISQUE) / volatilite_dec if volatilite_dec > 0 else 0
        
        # Maximum Drawdown
        cummax = serie.cummax()
        drawdown = (serie / cummax - 1) * 100
        max_dd = drawdown.min()
        
        # Volatilité journalière moyenne
        vol_journaliere = r.std() * 100
        
        metriques.append({
            'ticker': ticker,
            'perf_cumulee_pct': round(perf_cumulee, 2),
            'rendement_annuel_pct': round(rendement_annuel, 2),
            'volatilite_annuelle_pct': round(volatilite_annuelle, 2),
            'volatilite_journaliere_pct': round(vol_journaliere, 3),
            'ratio_sharpe': round(sharpe, 3),
            'max_drawdown_pct': round(max_dd, 2),
        })
    
    return pd.DataFrame(metriques).sort_values('ratio_sharpe', ascending=False)


def matrice_correlation(prix):
    """Calcule la matrice de corrélation des rendements"""
    rendements = calculer_rendements(prix)
    return rendements.corr().round(3)


def metriques_portefeuille_global(prix):
    """Métriques d'un portefeuille équipondéré (référence)"""
    rendements = calculer_rendements(prix)
    
    # Portefeuille équipondéré (recalcul propre)
    poids = np.ones(len(prix.columns)) / len(prix.columns)
    rendement_portefeuille = rendements.dot(poids)  # Plus propre
    
    # Métriques
    n_annees = len(rendement_portefeuille) / JOURS_TRADING
    rendement_total = (1 + rendement_portefeuille).prod() - 1
    rendement_annuel = ((1 + rendement_total) ** (1/n_annees) - 1) * 100
    
    volatilite_annuelle = rendement_portefeuille.std() * np.sqrt(JOURS_TRADING) * 100
    sharpe = (rendement_annuel/100 - TAUX_SANS_RISQUE) / (volatilite_annuelle/100)
    
    # Drawdown
    cumul = (1 + rendement_portefeuille).cumprod()
    cummax = cumul.cummax()
    drawdown = (cumul / cummax - 1) * 100
    max_dd = drawdown.min()
    
    return {
        'rendement_annuel_pct': round(rendement_annuel, 2),
        'volatilite_annuelle_pct': round(volatilite_annuelle, 2),
        'ratio_sharpe': round(sharpe, 3),
        'max_drawdown_pct': round(max_dd, 2),
        'rendement_cumule_pct': round(rendement_total * 100, 2),
    }


# =====================================================================
# GRAPHIQUES
# =====================================================================
def graphique_evolution_prix(prix, base_100=True):
    """Évolution des prix (base 100 pour comparer)"""
    if base_100:
        df = prix / prix.iloc[0] * 100
        titre = "📈 Évolution des actions BRVM (base 100)"
        y_title = "Indice base 100"
    else:
        df = prix
        titre = "📈 Évolution des prix des actions BRVM"
        y_title = "Prix (FCFA)"
    
    fig = go.Figure()
    for ticker in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ticker],
            name=ticker,
            mode='lines',
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title=titre,
        template='plotly_white',
        height=500,
        yaxis_title=y_title,
        xaxis_title="",
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.15)
    )
    return fig


def graphique_performance_vs_risque(metriques):
    """Scatter : Rendement vs Volatilité (avec taille = Sharpe)"""
    fig = px.scatter(
        metriques,
        x='volatilite_annuelle_pct',
        y='rendement_annuel_pct',
        size=metriques['ratio_sharpe'].clip(lower=0.1) * 50,
        color='ratio_sharpe',
        text='ticker',
        color_continuous_scale='RdYlGn',
        title="🎯 Rendement vs Risque (taille = Sharpe)",
        labels={
            'volatilite_annuelle_pct': 'Volatilité annualisée (%)',
            'rendement_annuel_pct': 'Rendement annualisé (%)',
            'ratio_sharpe': 'Sharpe'
        }
    )
    fig.update_traces(textposition='top center', textfont_size=12)
    fig.add_hline(y=TAUX_SANS_RISQUE * 100, line_dash="dash", 
                  line_color="gray", 
                  annotation_text=f"Taux sans risque ({TAUX_SANS_RISQUE*100:.1f} %)")
    fig.update_layout(template='plotly_white', height=500)
    return fig


def graphique_correlation(prix):
    """Heatmap de corrélation"""
    corr = matrice_correlation(prix)
    
    fig = px.imshow(
        corr,
        text_auto='.2f',
        aspect='auto',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        title="📊 Matrice de corrélation des rendements"
    )
    fig.update_layout(template='plotly_white', height=550)
    return fig


def graphique_drawdowns(prix):
    """Évolution des drawdowns"""
    fig = go.Figure()
    for ticker in prix.columns:
        serie = prix[ticker].dropna()
        cummax = serie.cummax()
        drawdown = (serie / cummax - 1) * 100
        fig.add_trace(go.Scatter(
            x=drawdown.index, y=drawdown,
            name=ticker, mode='lines', line=dict(width=1.5)
        ))
    
    fig.update_layout(
        title="📉 Évolution des drawdowns (%, depuis le pic)",
        template='plotly_white',
        height=450,
        yaxis_title="Drawdown (%)",
        xaxis_title="",
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.15)
    )
    return fig


def graphique_metriques_barres(metriques):
    """Bar chart des métriques clés"""
    metriques_sorted = metriques.sort_values('ratio_sharpe', ascending=True)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Rendement annualisé (%)', 'Volatilité annualisée (%)'),
        horizontal_spacing=0.15
    )
    
    # Rendement
    colors_rend = [COLORS['success'] if x > 0 else COLORS['accent'] 
                   for x in metriques_sorted['rendement_annuel_pct']]
    fig.add_trace(
        go.Bar(
            y=metriques_sorted['ticker'],
            x=metriques_sorted['rendement_annuel_pct'],
            orientation='h',
            marker_color=colors_rend,
            text=metriques_sorted['rendement_annuel_pct'].apply(lambda x: f"{x:+.1f}%"),
            textposition='outside',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Volatilité
    fig.add_trace(
        go.Bar(
            y=metriques_sorted['ticker'],
            x=metriques_sorted['volatilite_annuelle_pct'],
            orientation='h',
            marker_color=COLORS['warning'],
            text=metriques_sorted['volatilite_annuelle_pct'].apply(lambda x: f"{x:.1f}%"),
            textposition='outside',
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title="📊 Comparaison des métriques par action",
        template='plotly_white',
        height=500
    )
    return fig


# =====================================================================
# RAPPORT COMPLET
# =====================================================================
def generer_rapport(prix, output_dir='reports/performance'):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 75)
    print("📈 ANALYSE DE PERFORMANCE")
    print("=" * 75)
    
    # Métriques par action
    metriques = metriques_par_action(prix)
    
    print("\n📊 MÉTRIQUES PAR ACTION (triées par Sharpe)")
    print("─" * 95)
    print(metriques.to_string(index=False))
    
    # Portefeuille global
    portef = metriques_portefeuille_global(prix)
    print(f"\n📊 PORTEFEUILLE ÉQUIPONDÉRÉ (référence)")
    print("─" * 75)
    print(f"   • Rendement annualisé   : {portef['rendement_annuel_pct']:>8.2f} %")
    print(f"   • Volatilité annualisée : {portef['volatilite_annuelle_pct']:>8.2f} %")
    print(f"   • Ratio de Sharpe       : {portef['ratio_sharpe']:>8.3f}")
    print(f"   • Max Drawdown          : {portef['max_drawdown_pct']:>8.2f} %")
    print(f"   • Rendement cumulé      : {portef['rendement_cumule_pct']:>8.2f} %")
    
    # Top performers
    print(f"\n🏆 TOP 3 ACTIONS (par Sharpe)")
    print("─" * 75)
    top3 = metriques.head(3)
    for i, (_, row) in enumerate(top3.iterrows(), 1):
        print(f"   {i}. {row['ticker']:6s} | Rendement {row['rendement_annuel_pct']:>6.2f} % | "
              f"Volatilité {row['volatilite_annuelle_pct']:>5.2f} % | Sharpe {row['ratio_sharpe']:.3f}")
    
    # Flop performers
    print(f"\n🔻 FLOP 3 ACTIONS (par Sharpe)")
    print("─" * 75)
    flop3 = metriques.tail(3)
    for i, (_, row) in enumerate(flop3.iterrows(), 1):
        print(f"   {i}. {row['ticker']:6s} | Rendement {row['rendement_annuel_pct']:>6.2f} % | "
              f"Volatilité {row['volatilite_annuelle_pct']:>5.2f} % | Sharpe {row['ratio_sharpe']:.3f}")
    
    # Graphiques
    print(f"\n📈 Génération des graphiques...")
    graphiques = {}
    
    graphiques['01_evolution_prix'] = graphique_evolution_prix(prix)
    graphiques['02_rendement_vs_risque'] = graphique_performance_vs_risque(metriques)
    graphiques['03_correlation'] = graphique_correlation(prix)
    graphiques['04_drawdowns'] = graphique_drawdowns(prix)
    graphiques['05_metriques_barres'] = graphique_metriques_barres(metriques)
    
    for nom, fig in graphiques.items():
        chemin = f"{output_dir}/{nom}.html"
        fig.write_html(chemin)
        print(f"   ✅ {nom}.html")
    
    # Sauvegarde CSV
    metriques.to_csv(f"{output_dir}/metriques_actions.csv", index=False)
    matrice_correlation(prix).to_csv(f"{output_dir}/correlations.csv")
    pd.DataFrame([portef]).to_csv(f"{output_dir}/portefeuille_global.csv", index=False)
    
    print(f"\n💾 CSV sauvegardés dans {output_dir}/")
    
    return metriques, portef


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("🔄 Chargement des prix...")
    prix = charger_prix()
    
    # Analyse
    metriques, portef = generer_rapport(prix)
    
    print("\n" + "=" * 75)
    print("✅ ANALYSE DE PERFORMANCE TERMINÉE")
    print("=" * 75)