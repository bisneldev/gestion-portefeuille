"""
Génération des rapports clients PDF
Rapport de gestion de portefeuille personnalisé
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


# =====================================================================
# CONFIGURATION
# =====================================================================
TAUX_SANS_RISQUE = 0.038
JOURS_TRADING = 252

COLORS_PDF = {
    'primaire': '#1f3a5f',
    'accent': '#e63946',
    'success': '#2a9d8f',
    'warning': '#f4a261',
}

# Allocation optimale par profil
ALLOCATIONS_PROFILS = {
    'Prudent': {
        'rendement': 5.72, 'volatilite': 4.67, 'sharpe': 0.410,
        'allocation': {
            'ORAC': 13.8, 'SNTS': 13.3, 'TTLC': 12.8, 'ONTF': 12.3,
            'SGBC': 10.3, 'SIBC': 9.3, 'BOAC': 8.7, 'CBIBF': 7.5,
            'ETIT': 7.2, 'UNXC': 4.8,
        }
    },
    'Équilibré': {
        'rendement': 7.33, 'volatilite': 5.12, 'sharpe': 0.689,
        'allocation': {
            'SGBC': 15.0, 'CBIBF': 14.0, 'SNTS': 14.0, 'BOAC': 12.0,
            'SIBC': 10.0, 'TTLC': 9.0, 'ORAC': 8.0, 'UNXC': 7.0,
            'ONTF': 6.0, 'ETIT': 5.0,
        }
    },
    'Dynamique': {
        'rendement': 8.94, 'volatilite': 6.19, 'sharpe': 0.831,
        'allocation': {
            'SGBC': 21.3, 'CBIBF': 19.2, 'SNTS': 18.8, 'BOAC': 16.9,
            'SIBC': 9.6, 'TTLC': 7.7, 'ORAC': 6.3,
        }
    },
}


# =====================================================================
# CHARGEMENT DES CLIENTS
# =====================================================================
def charger_clients(path='data/raw/clients.csv'):
    return pd.read_csv(path)


def charger_portefeuilles(path='data/raw/portefeuilles.csv'):
    return pd.read_csv(path)


# =====================================================================
# GÉNÉRATION PDF
# =====================================================================
def generer_rapport_client(client, portefeuille_client, output):
    """Génère un rapport PDF personnalisé pour un client"""
    
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    titre = ParagraphStyle(
        'T', parent=styles['Title'],
        fontSize=20, textColor=colors.HexColor(COLORS_PDF['primaire']),
        spaceAfter=6, alignment=TA_CENTER
    )
    h1 = ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontSize=13, textColor=colors.HexColor(COLORS_PDF['primaire']),
        spaceBefore=15, spaceAfter=8
    )
    normal = ParagraphStyle(
        'N', parent=styles['Normal'],
        fontSize=10, alignment=TA_JUSTIFY, leading=14
    )
    small = ParagraphStyle(
        'S', parent=styles['Normal'],
        fontSize=8, textColor=colors.grey
    )
    
    elements = []
    profil = client['profil']
    alloc = ALLOCATIONS_PROFILS[profil]
    
    # ---- EN-TÊTE ----
    elements.append(Paragraph("RAPPORT DE GESTION DE PORTEFEUILLE", titre))
    elements.append(Paragraph(
        f"Client : {client['nom']}",
        ParagraphStyle('sub', parent=styles['Normal'], fontSize=12,
                       textColor=colors.HexColor('#666'), alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Édité le {datetime.now().strftime('%d/%m/%Y')}",
        ParagraphStyle('d', parent=small, alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 15))
    
    # ---- SECTION 1 : FICHE CLIENT ----
    elements.append(Paragraph("1. Fiche client", h1))
    
    data_client = [
        ['Client ID', client['client_id']],
        ['Nom', client['nom']],
        ['Profil investisseur', profil],
        ['Capital investi', f"{client['capital_investi_fcfa']:,.0f} FCFA"],
        ['Horizon de placement', f"{client['horizon_annees']} an(s)"],
        ['Tolérance au risque', f"{client['tolerance_risque']}/3"],
    ]
    
    t_client = Table(data_client, colWidths=[6*cm, 10*cm])
    t_client.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f4f8')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_client)
    
    # ---- SECTION 2 : PERFORMANCE ----
    elements.append(Paragraph("2. Performance du portefeuille", h1))
    
    data_perf = [
        ['Indicateur', 'Valeur'],
        ['Rendement annualisé', f"{alloc['rendement']:.2f} %"],
        ['Volatilité annualisée', f"{alloc['volatilite']:.2f} %"],
        ['Ratio de Sharpe', f"{alloc['sharpe']:.3f}"],
        ['Taux sans risque (BEAC)', f"{TAUX_SANS_RISQUE*100:.1f} %"],
        ['Prime de risque', f"{alloc['rendement'] - TAUX_SANS_RISQUE*100:.2f} %"],
    ]
    
    t_perf = Table(data_perf, colWidths=[8*cm, 8*cm])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS_PDF['primaire'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_perf)
    
    # ---- SECTION 3 : ALLOCATION ----
    elements.append(Paragraph("3. Allocation recommandée", h1))
    
    data_alloc = [['Actif', 'Poids (%)', 'Montant (FCFA)']]
    capital = client['capital_investi_fcfa']
    
    for actif, poids in sorted(alloc['allocation'].items(), 
                                 key=lambda x: -x[1]):
        montant = capital * poids / 100
        data_alloc.append([actif, f"{poids:.1f} %", f"{montant:,.0f}"])
    
    # Ligne total
    total_poids = sum(alloc['allocation'].values())
    data_alloc.append([
        Paragraph('<b>TOTAL</b>', normal),
        Paragraph(f'<b>{total_poids:.1f} %</b>', normal),
        Paragraph(f'<b>{capital:,.0f}</b>', normal)
    ])
    
    t_alloc = Table(data_alloc, colWidths=[4*cm, 4*cm, 8*cm])
    t_alloc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS_PDF['primaire'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_alloc)
    
    # ---- SECTION 4 : RISQUE ----
    elements.append(PageBreak())
    elements.append(Paragraph("4. Analyse de risque", h1))
    
    # VaR selon profil
    var_factor = {'Prudent': 0.5, 'Équilibré': 0.7, 'Dynamique': 1.0}[profil]
    var_95 = 0.483 * var_factor
    var_99 = 0.723 * var_factor
    
    data_risque = [
        ['Indicateur', 'Valeur', 'Impact (FCFA)'],
        ['VaR 95 % (1 jour)', f"{var_95:.3f} %", f"{capital * var_95/100:,.0f}"],
        ['VaR 99 % (1 jour)', f"{var_99:.3f} %", f"{capital * var_99/100:,.0f}"],
        ['VaR 99 % (10 jours)', f"{var_99 * np.sqrt(10):.3f} %", 
         f"{capital * var_99 * np.sqrt(10)/100:,.0f}"],
    ]
    
    t_risque = Table(data_risque, colWidths=[5*cm, 5*cm, 6*cm])
    t_risque.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS_PDF['accent'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_risque)
    
    # ---- SECTION 5 : STRESS TESTS ----
    elements.append(Paragraph("5. Stress tests — scénarios extrêmes", h1))
    
    data_stress = [
        ['Scénario', 'Choc marché', 'Impact portefeuille', 'Perte (FCFA)'],
        ['Crise 2008', '-40 %', f"{-32*var_factor:.2f} %", 
         f"{-capital * 0.32 * var_factor:,.0f}"],
        ['COVID-19', '-30 %', f"{-24*var_factor:.2f} %", 
         f"{-capital * 0.24 * var_factor:,.0f}"],
        ['Krach boursier', '-25 %', f"{-20*var_factor:.2f} %", 
         f"{-capital * 0.20 * var_factor:,.0f}"],
        ['Choc pétrolier', '-20 %', f"{-16*var_factor:.2f} %", 
         f"{-capital * 0.16 * var_factor:,.0f}"],
    ]
    
    t_stress = Table(data_stress, colWidths=[4*cm, 3*cm, 4*cm, 5*cm])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS_PDF['warning'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_stress)
    
    # ---- SECTION 6 : RECOMMANDATIONS ----
    elements.append(Paragraph("6. Recommandations", h1))
    
    recos = {
        'Prudent': [
            f"<b>Maintenir l'allocation actuelle</b> qui privilégie la sécurité "
            f"avec une volatilité limitée à {alloc['volatilite']:.2f} %.",
            f"<b>Réviser annuellement</b> la répartition pour s'adapter aux "
            f"conditions de marché.",
            f"<b>Envisager des obligations BEAC</b> (rendement 3.8-6.8 %) "
            f"pour la poche défensive.",
        ],
        'Équilibré': [
            f"<b>Conserver l'équilibre</b> entre actions performantes (SGBC, CBIBF) "
            f"et valeurs défensives.",
            f"<b>Renforcer SNTS et BOAC</b> qui offrent un bon compromis "
            f"rendement/risque.",
            f"<b>Surveiller le drawdown</b> qui peut atteindre -30 % en cas de crise.",
        ],
        'Dynamique': [
            f"<b>Maintenir la concentration</b> sur les meilleures actions "
            f"(SGBC, CBIBF, SNTS, BOAC).",
            f"<b>Exclure ETIT et ONTF</b> qui affichent un Sharpe négatif.",
            f"<b>Anticiper la volatilité</b> plus élevée ({alloc['volatilite']:.2f} %) "
            f"pour un horizon de {client['horizon_annees']} an(s).",
        ],
    }
    
    for i, reco in enumerate(recos[profil], 1):
        elements.append(Paragraph(f"{i}. {reco}", normal))
        elements.append(Spacer(1, 6))
    
    # ---- FOOTER ----
    elements.append(Spacer(1, 25))
    elements.append(Paragraph(
        "Document généré automatiquement — Système de Gestion de Portefeuille",
        small
    ))
    elements.append(Paragraph(
        "Les performances passées ne préjugent pas des performances futures.",
        small
    ))
    
    doc.build(elements)
    return output


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("=" * 75)
    print("📄 GÉNÉRATION DES RAPPORTS CLIENTS")
    print("=" * 75)
    
    # Chargement
    df_clients = charger_clients()
    df_portefeuilles = charger_portefeuilles()
    
    print(f"\n📊 {len(df_clients)} clients à traiter")
    
    # Créer le dossier
    Path('reports/rapports_clients').mkdir(parents=True, exist_ok=True)
    
    # Générer 3 rapports (1 par profil)
    rapports_generes = []
    
    for profil in ['Prudent', 'Équilibré', 'Dynamique']:
        client = df_clients[df_clients['profil'] == profil].iloc[0]
        pf_client = df_portefeuilles[df_portefeuilles['client_id'] == client['client_id']]
        
        output = f"reports/rapports_clients/rapport_{client['client_id']}.pdf"
        generer_rapport_client(client, pf_client, output)
        rapports_generes.append(output)
        print(f"   ✅ {output}")
    
    # Rapport global (3 profils)
    print(f"\n📄 Génération du rapport global...")
    rapport_global = "reports/rapport_portefeuille_global.pdf"
    
    doc = SimpleDocTemplate(rapport_global, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    titre = ParagraphStyle('T', parent=styles['Title'],
                           fontSize=22, textColor=colors.HexColor(COLORS_PDF['primaire']),
                           spaceAfter=6, alignment=TA_CENTER)
    h1 = ParagraphStyle('H1', parent=styles['Heading1'],
                        fontSize=14, textColor=colors.HexColor(COLORS_PDF['primaire']),
                        spaceBefore=20, spaceAfter=10)
    normal = ParagraphStyle('N', parent=styles['Normal'],
                            fontSize=10, alignment=TA_JUSTIFY, leading=14)
    
    elements = []
    elements.append(Paragraph("RAPPORT GLOBAL — GESTION DE PORTEFEUILLE", titre))
    elements.append(Paragraph("Exercice 2025 — Marché BRVM",
                              ParagraphStyle('sub', parent=styles['Normal'], 
                                           fontSize=11, textColor=colors.HexColor('#666'),
                                           alignment=TA_CENTER)))
    elements.append(Spacer(1, 20))
    
    # Synthèse
    elements.append(Paragraph("1. Synthèse", h1))
    capital_total = df_clients['capital_investi_fcfa'].sum()
    elements.append(Paragraph(
        f"Le portefeuille global comprend <b>{len(df_clients)} clients</b> "
        f"pour un capital total sous gestion de <b>{capital_total/1e9:.2f} Mds FCFA</b>. "
        f"La répartition par profil est la suivante :",
        normal
    ))
    
    data_profils = [['Profil', 'Nb clients', 'Capital (FCFA)', 'Rendement cible']]
    for profil in ['Prudent', 'Équilibré', 'Dynamique']:
        subset = df_clients[df_clients['profil'] == profil]
        cap = subset['capital_investi_fcfa'].sum()
        alloc = ALLOCATIONS_PROFILS[profil]
        data_profils.append([
            profil, f"{len(subset)}",
            f"{cap:,.0f}", f"{alloc['rendement']:.2f} %"
        ])
    data_profils.append(['TOTAL', f"{len(df_clients)}", 
                        f"{capital_total:,.0f}", '—'])
    
    t = Table(data_profils, colWidths=[4*cm, 3*cm, 6*cm, 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS_PDF['primaire'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    
    # Recommandations globales
    elements.append(Paragraph("2. Recommandations globales", h1))
    recos = [
        f"<b>Diversification optimale</b> : la frontière efficiente montre qu'un "
        f"portefeuille bien diversifié atteint un Sharpe de 0,83 — presque le double "
        f"de la meilleure action individuelle.",
        
        f"<b>Exclusion des actifs déficitaires</b> : ETIT (-2.46 %) et ONTF (-1.39 %) "
        f"affichent un Sharpe négatif. Les exclure est une décision évidente.",
        
        f"<b>Suivi trimestriel recommandé</b> : rééquilibrage selon l'évolution des "
        f"marchés et des profils clients.",
        
        f"<b>Reporting personnalisé</b> : chaque client reçoit son rapport détaillé "
        f"avec allocation, performance et analyse de risque.",
    ]
    
    for i, r in enumerate(recos, 1):
        elements.append(Paragraph(f"{i}. {r}", normal))
        elements.append(Spacer(1, 6))
    
    doc.build(elements)
    rapports_generes.append(rapport_global)
    print(f"   ✅ {rapport_global}")
    
    print("\n" + "=" * 75)
    print("✅ RAPPORTS GÉNÉRÉS")
    print("=" * 75)
    print(f"\n📁 {len(rapports_generes)} rapports dans reports/rapports_clients/")
    print("   • 3 rapports individuels (Prudent, Équilibré, Dynamique)")
    print("   • 1 rapport global de synthèse")