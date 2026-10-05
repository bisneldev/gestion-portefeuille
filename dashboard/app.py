"""
Dashboard interactif de Gestion de Portefeuille
Analyse, risque et optimisation
"""
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path


# =====================================================================
# CHARGEMENT DES DONNÉES
# =====================================================================
print("🔄 Chargement des données...")

df_prix_long = pd.read_csv('data/raw/prix_actions.csv', parse_dates=['date'])
prix = df_prix_long.pivot(index='date', columns='ticker', values='prix').sort_index()
rendements = prix.pct_change().dropna()

# Métriques
TAUX_SANS_RISQUE = 0.038
JOURS_TRADING = 252

rendements_annuels = rendements.mean() * JOURS_TRADING
volatilites_annuelles = rendements.std() * np.sqrt(JOURS_TRADING)
sharpe = (rendements_annuels - TAUX_SANS_RISQUE) / volatilites_annuelles

df_metriques = pd.DataFrame({
    'ticker': rendements_annuels.index,
    'rendement': rendements_annuels.values * 100,
    'volatilite': volatilites_annuelles.values * 100,
    'sharpe': sharpe.values,
})

# Prix base 100
prix_base100 = prix / prix.iloc[0] * 100

# VaR portefeuille
poids = np.ones(len(prix.columns)) / len(prix.columns)
r_portefeuille = rendements.dot(poids)
var_95 = -np.percentile(r_portefeuille, 5) * 100
var_99 = -np.percentile(r_portefeuille, 1) * 100

# Portefeuille tangent (allocation fixe)
allocation_tangent = {
    'SGBC': 21.3, 'CBIBF': 19.2, 'SNTS': 18.8, 'BOAC': 16.9,
    'SIBC': 9.6, 'TTLC': 7.7, 'ORAC': 6.3
}

print(f"✅ {len(prix)} jours × {len(prix.columns)} actions chargés")


# =====================================================================
# PALETTE
# =====================================================================
COLORS = {
    'primaire': '#1f3a5f',
    'accent': '#e63946',
    'success': '#2a9d8f',
    'warning': '#f4a261',
    'light': '#f5f7fa',
}


# =====================================================================
# KPI CARD
# =====================================================================
def kpi_card(titre, valeur, sous_titre="", couleur=None):
    couleur = couleur or COLORS['primaire']
    return html.Div([
        html.P(titre, style={
            'margin': 0, 'color': '#7a8899', 'fontSize': '11px',
            'fontWeight': '600', 'letterSpacing': '0.5px',
            'textTransform': 'uppercase'
        }),
        html.H2(valeur, style={
            'margin': '8px 0 4px 0', 'color': couleur,
            'fontSize': '22px', 'fontWeight': '700'
        }),
        html.P(sous_titre, style={
            'margin': 0, 'color': '#a0aec0', 'fontSize': '11px'
        }),
    ], style={
        'background': 'white',
        'padding': '16px 18px',
        'borderRadius': '12px',
        'boxShadow': '0 2px 12px rgba(0,0,0,0.06)',
        'borderLeft': f'4px solid {couleur}',
        'flex': 1,
        'minWidth': '180px'
    })


# =====================================================================
# APPLICATION
# =====================================================================
app = dash.Dash(__name__, title="Gestion de Portefeuille")
server = app.server

app.layout = html.Div([

    # HEADER
    html.Div([
        html.Div([
            html.H1("📈 Gestion de Portefeuille",
                    style={'margin': 0, 'color': 'white',
                           'fontSize': '26px', 'fontWeight': '700'}),
            html.P("Analyse • Risque • Optimisation — Marché BRVM",
                   style={'margin': '5px 0 0 0', 'color': '#b8c5d6',
                          'fontSize': '14px'}),
        ], style={'flex': 1}),
        html.Div([
            html.P("📊 10 actions BRVM",
                   style={'color': 'white', 'margin': 0,
                          'fontSize': '14px', 'fontWeight': '600'}),
            html.P(f"📅 {prix.index[0].strftime('%Y-%m-%d')} → {prix.index[-1].strftime('%Y-%m-%d')}",
                   style={'color': '#b8c5d6', 'margin': '4px 0 0 0',
                          'fontSize': '13px'}),
        ], style={'textAlign': 'right'})
    ], style={
        'background': f'linear-gradient(90deg, {COLORS["primaire"]}, #2c5282)',
        'padding': '25px 40px',
        'display': 'flex',
        'alignItems': 'center'
    }),

    # KPIs
    html.Div([
        kpi_card("🏆 Meilleur Sharpe", f"{sharpe.max():.3f}",
                 f"{sharpe.idxmax()}", COLORS['success']),
        kpi_card("💰 Rendement moyen", f"{rendements_annuels.mean()*100:.2f} %",
                 "annualisé", COLORS['primaire']),
        kpi_card("⚠️ VaR 95% (1j)", f"{var_95:.3f} %",
                 f"VaR 99%: {var_99:.3f} %", COLORS['accent']),
        kpi_card("📊 Capital analysé", "1.00 Md",
                 "FCFA", COLORS['warning']),
        kpi_card("🎯 Actions", f"{len(prix.columns)}",
                 "BRVM", COLORS['primaire']),
    ], style={
        'display': 'flex', 'gap': '18px',
        'padding': '25px 40px', 'flexWrap': 'wrap'
    }),

    # LIGNE 1 : Évolution prix + Rendement vs Risque
    html.Div([
        html.Div(dcc.Graph(id='graph-evolution'),
                 style={'flex': 1, 'minWidth': '450px'}),
        html.Div(dcc.Graph(id='graph-scatter'),
                 style={'flex': 1, 'minWidth': '450px'}),
    ], style={
        'display': 'flex', 'gap': '20px',
        'padding': '0 40px 20px 40px', 'flexWrap': 'wrap'
    }),

    # LIGNE 2 : Allocation + Profils
    html.Div([
        html.Div(dcc.Graph(id='graph-allocation'),
                 style={'flex': 1, 'minWidth': '450px'}),
        html.Div(dcc.Graph(id='graph-profils'),
                 style={'flex': 1, 'minWidth': '450px'}),
    ], style={
        'display': 'flex', 'gap': '20px',
        'padding': '0 40px 20px 40px', 'flexWrap': 'wrap'
    }),

    # LIGNE 3 : Drawdowns + Backtesting VaR
    html.Div([
        html.Div(dcc.Graph(id='graph-drawdown'),
                 style={'flex': 1, 'minWidth': '450px'}),
        html.Div(dcc.Graph(id='graph-var-dist'),
                 style={'flex': 1, 'minWidth': '450px'}),
    ], style={
        'display': 'flex', 'gap': '20px',
        'padding': '0 40px 20px 40px', 'flexWrap': 'wrap'
    }),

    # TABLEAU TOP ACTIONS
    html.Div([
        html.H3("🏆 Classement des actions BRVM (par Sharpe)",
                style={'color': COLORS['primaire'],
                       'padding': '0 40px', 'margin': '20px 0 10px 0'}),
        html.Div(id='tableau-actions',
                 style={'padding': '0 40px 40px 40px'})
    ]),

    # FOOTER
    html.Div([
        html.P("📌 Dashboard Gestion de Portefeuille — Python, Plotly Dash",
               style={'color': '#718096', 'fontSize': '12px',
                      'textAlign': 'center', 'margin': 0}),
    ], style={'padding': '20px', 'background': '#e2e8f0'})

], style={
    'fontFamily': "'Segoe UI', Arial, sans-serif",
    'background': COLORS['light'],
    'minHeight': '100vh',
    'margin': 0
})


# =====================================================================
# CALLBACK
# =====================================================================
@app.callback(
    [Output('graph-evolution', 'figure'),
     Output('graph-scatter', 'figure'),
     Output('graph-allocation', 'figure'),
     Output('graph-profils', 'figure'),
     Output('graph-drawdown', 'figure'),
     Output('graph-var-dist', 'figure'),
     Output('tableau-actions', 'children')],
    [Input('graph-evolution', 'id')]
)
def update_dashboard(_):
    # ---- Graph 1 : Évolution des prix base 100 ----
    fig1 = go.Figure()
    colors_palette = px.colors.qualitative.Set2 + px.colors.qualitative.Set3
    for i, ticker in enumerate(prix_base100.columns):
        fig1.add_trace(go.Scatter(
            x=prix_base100.index, y=prix_base100[ticker],
            name=ticker, mode='lines',
            line=dict(width=2, color=colors_palette[i % len(colors_palette)])
        ))
    fig1.update_layout(
        title="📈 Évolution des actions BRVM (base 100)",
        template='plotly_white', height=420,
        yaxis_title="Indice base 100", xaxis_title="",
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.25, font=dict(size=10))
    )
    
    # ---- Graph 2 : Rendement vs Risque ----
    df_m = df_metriques.copy()
    df_m['couleur'] = df_m['sharpe'].apply(
        lambda x: COLORS['success'] if x > 0.3 else 
                  COLORS['warning'] if x > 0 else COLORS['accent']
    )
    
    fig2 = go.Figure()
    for _, row in df_m.iterrows():
        fig2.add_trace(go.Scatter(
            x=[row['volatilite']], y=[row['rendement']],
            mode='markers+text',
            marker=dict(
                size=abs(row['sharpe']) * 40 + 10,
                color=row['couleur'],
                line=dict(color='white', width=2)
            ),
            text=[row['ticker']],
            textposition='top center',
            name=row['ticker'],
            showlegend=False,
            hovertemplate=f"<b>{row['ticker']}</b><br>"
                          f"Rendement: {row['rendement']:.2f}%<br>"
                          f"Volatilité: {row['volatilite']:.2f}%<br>"
                          f"Sharpe: {row['sharpe']:.3f}<extra></extra>"
        ))
    
    fig2.add_hline(y=TAUX_SANS_RISQUE * 100, line_dash="dash",
                   line_color="gray",
                   annotation_text=f"Taux sans risque ({TAUX_SANS_RISQUE*100:.1f} %)")
    fig2.update_layout(
        title="🎯 Rendement vs Risque (taille = Sharpe)",
        template='plotly_white', height=420,
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)"
    )
    
    # ---- Graph 3 : Allocation portefeuille tangent ----
    fig3 = go.Figure(go.Pie(
        labels=list(allocation_tangent.keys()),
        values=list(allocation_tangent.values()),
        hole=0.5,
        textinfo='label+percent',
        marker=dict(line=dict(color='white', width=2),
                    colors=px.colors.qualitative.Set2)
    ))
    fig3.update_layout(
        title="💼 Allocation optimale (Max Sharpe)",
        template='plotly_white', height=420
    )
    
    # ---- Graph 4 : Profils clients ----
    profils = pd.DataFrame({
        'profil': ['Prudent', 'Équilibré', 'Dynamique'],
        'rendement': [5.72, 7.33, 8.94],
        'volatilite': [4.67, 5.12, 6.19],
        'sharpe': [0.410, 0.689, 0.831],
    })
    
    fig4 = go.Figure()
    colors_profils = [COLORS['success'], COLORS['warning'], COLORS['accent']]
    for i, row in profils.iterrows():
        fig4.add_trace(go.Scatter(
            x=[row['volatilite']], y=[row['rendement']],
            mode='markers+text',
            marker=dict(size=35, color=colors_profils[i],
                        line=dict(color='white', width=3)),
            text=[f"<b>{row['profil']}</b><br>Sharpe: {row['sharpe']:.2f}"],
            textposition='top center',
            name=row['profil'],
            hovertemplate=f"<b>{row['profil']}</b><br>"
                          f"Rendement: {row['rendement']:.2f}%<br>"
                          f"Volatilité: {row['volatilite']:.2f}%<br>"
                          f"Sharpe: {row['sharpe']:.3f}<extra></extra>"
        ))
    fig4.update_layout(
        title="👥 Portefeuilles par profil client",
        template='plotly_white', height=420,
        xaxis_title="Volatilité (%)", yaxis_title="Rendement (%)",
        showlegend=False
    )
    
    # ---- Graph 5 : Drawdowns ----
    fig5 = go.Figure()
    for i, ticker in enumerate(prix.columns):
        serie = prix[ticker]
        cummax = serie.cummax()
        dd = (serie / cummax - 1) * 100
        fig5.add_trace(go.Scatter(
            x=dd.index, y=dd,
            name=ticker, mode='lines',
            line=dict(width=1, color=colors_palette[i % len(colors_palette)])
        ))
    fig5.update_layout(
        title="📉 Drawdowns (%, depuis le pic)",
        template='plotly_white', height=420,
        yaxis_title="Drawdown (%)", xaxis_title="",
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.25, font=dict(size=10))
    )
    
    # ---- Graph 6 : Distribution VaR ----
    fig6 = go.Figure()
    fig6.add_trace(go.Histogram(
        x=r_portefeuille * 100, nbinsx=80,
        marker_color=COLORS['primaire'], opacity=0.75,
        name='Rendements'
    ))
    fig6.add_vline(x=-var_95, line_dash="dash", line_color=COLORS['warning'],
                   annotation_text=f"VaR 95% = {var_95:.2f}%",
                   annotation_position="top left")
    fig6.add_vline(x=-var_99, line_dash="dash", line_color=COLORS['accent'],
                   annotation_text=f"VaR 99% = {var_99:.2f}%",
                   annotation_position="top right")
    fig6.update_layout(
        title="⚠️ Distribution des rendements et VaR",
        template='plotly_white', height=420,
        xaxis_title="Rendement journalier (%)",
        yaxis_title="Fréquence",
        showlegend=False
    )
    
    # ---- Tableau actions ----
    df_t = df_metriques.sort_values('sharpe', ascending=False).copy()
    df_t['rendement'] = df_t['rendement'].apply(lambda x: f"{x:+.2f} %")
    df_t['volatilite'] = df_t['volatilite'].apply(lambda x: f"{x:.2f} %")
    df_t['sharpe'] = df_t['sharpe'].apply(lambda x: f"{x:.3f}")
    df_t = df_t.rename(columns={
        'ticker': 'Action',
        'rendement': 'Rendement annuel',
        'volatilite': 'Volatilité',
        'sharpe': 'Sharpe'
    })
    
    tableau = dash_table.DataTable(
        data=df_t.to_dict('records'),
        columns=[{'name': c, 'id': c} for c in df_t.columns],
        style_cell={
            'textAlign': 'left', 'padding': '12px 15px',
            'fontFamily': "'Segoe UI', Arial, sans-serif",
            'fontSize': '13px'
        },
        style_header={
            'backgroundColor': COLORS['primaire'],
            'color': 'white', 'fontWeight': 'bold',
            'fontSize': '12px', 'textTransform': 'uppercase'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
            {'if': {'filter_query': '{Sharpe} > "0.4"'}, 
             'backgroundColor': '#d4f4dd', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Sharpe} < "0"'},
             'backgroundColor': '#ffe5e5'},
        ],
        style_as_list_view=True,
    )
    
    return fig1, fig2, fig3, fig4, fig5, fig6, tableau


# =====================================================================
# LANCEMENT
# =====================================================================
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 Dashboard Gestion de Portefeuille démarré")
    print("=" * 70)
    print("👉 Ouvre ton navigateur : http://127.0.0.1:8053")
    print("⛔ Pour arrêter : Ctrl + C")
    print("=" * 70 + "\n")
    app.run(debug=True, port=8053)