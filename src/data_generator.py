"""
Générateur de données pour la gestion de portefeuille
Contexte : marché financier africain (BRVM, BEAC, obligations d'État)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


# =====================================================================
# CONFIGURATION
# =====================================================================
ACTIONS_BRVM = {
    'SGBC': {'nom': 'Société Générale CI', 'prix_init': 14500, 'volatilite': 0.018, 'rendement': 0.0004},
    'SNTS': {'nom': 'Sonatel',            'prix_init': 18000, 'volatilite': 0.015, 'rendement': 0.0005},
    'ETIT': {'nom': 'Ecobank Transnational', 'prix_init': 18,  'volatilite': 0.022, 'rendement': 0.0002},
    'ORAC': {'nom': 'Orange CI',          'prix_init': 12000, 'volatilite': 0.014, 'rendement': 0.0004},
    'BOAC': {'nom': 'Bank of Africa CI',  'prix_init': 4500,  'volatilite': 0.020, 'rendement': 0.0003},
    'ONTF': {'nom': 'Onatel BF',          'prix_init': 3200,  'volatilite': 0.017, 'rendement': 0.0004},
    'TTLC': {'nom': 'Total CI',           'prix_init': 2800,  'volatilite': 0.016, 'rendement': 0.0003},
    'CBIBF': {'nom': 'Coris Bank BF',     'prix_init': 8500,  'volatilite': 0.021, 'rendement': 0.0005},
    'SIBC': {'nom': 'SIB CI',             'prix_init': 5200,  'volatilite': 0.019, 'rendement': 0.0003},
    'UNXC': {'nom': 'Uniwax CI',          'prix_init': 1200,  'volatilite': 0.023, 'rendement': 0.0002},
}

OBLIGATIONS = [
    {'code': 'BTA-GAB-2025', 'nom': 'BTA Gabon 2025', 'type': 'BTA', 'maturite_annees': 1, 'rendement_pct': 4.5, 'risque': 'Faible'},
    {'code': 'OTA-GAB-2027', 'nom': 'OTA Gabon 2027', 'type': 'OTA', 'maturite_annees': 2, 'rendement_pct': 5.5, 'risque': 'Faible'},
    {'code': 'OTA-GAB-2030', 'nom': 'OTA Gabon 2030', 'type': 'OTA', 'maturite_annees': 5, 'rendement_pct': 6.5, 'risque': 'Modéré'},
    {'code': 'BEAC-2026',    'nom': 'Obligation BEAC 2026', 'type': 'BEAC', 'maturite_annees': 1, 'rendement_pct': 3.8, 'risque': 'Très faible'},
    {'code': 'TRESOR-CEMAC', 'nom': 'Titre CEMAC 2028', 'type': 'CEMAC', 'maturite_annees': 3, 'rendement_pct': 5.0, 'risque': 'Faible'},
    {'code': 'OTA-CI-2030',  'nom': 'OTA Côte d\'Ivoire 2030', 'type': 'OTA', 'maturite_annees': 5, 'rendement_pct': 6.8, 'risque': 'Modéré'},
]

PROFILS_CLIENTS = {
    'Prudent':    {'actions': 0.20, 'obligations': 0.80, 'nb_clients': 10},
    'Équilibré':  {'actions': 0.50, 'obligations': 0.50, 'nb_clients': 12},
    'Dynamique':  {'actions': 0.80, 'obligations': 0.20, 'nb_clients': 8},
}

NOMS_CLIENTS = [
    'BGFI Invest', 'Sogafin', 'Caisse des Dépôts', 'CNSS Gabon',
    'Fonds Souverain Gabon', 'Assurance OGAR', 'NSIA Gabon',
    'BICIG Assurances', 'Total Gabon Retraite', 'Comilog Pension',
    'Client Privé 001', 'Client Privé 002', 'Client Privé 003',
    'Client Privé 004', 'Client Privé 005', 'Client Privé 006',
    'Client Privé 007', 'Client Privé 008', 'Client Privé 009',
    'Client Privé 010', 'Client Privé 011', 'Client Privé 012',
    'Client Privé 013', 'Client Privé 014', 'Client Privé 015',
    'Client Privé 016', 'Client Privé 017', 'Client Privé 018',
    'Client Privé 019', 'Client Privé 020'
]


# =====================================================================
# GÉNÉRATION DES PRIX D'ACTIONS (mouvement brownien géométrique)
# =====================================================================
def generer_prix_actions(n_jours=1825, seed=42):
    """
    Génère 5 ans de prix journaliers pour 10 actions BRVM.
    Version CORRIGÉE : performances bornées à des niveaux réalistes.
    """
    np.random.seed(seed)
    dates = pd.date_range('2020-01-01', periods=n_jours, freq='B')
    
    # Performance cible sur 5 ans par action (réaliste)
    perf_cibles = {
        'SGBC':  +95,   # +95 % sur 5 ans (~14 %/an)
        'SNTS':  +65,   # +65 %
        'ETIT':  -25,   # -25 % (action en difficulté)
        'ORAC':  +35,   # +35 %
        'BOAC':  +85,   # +85 %
        'ONTF':  -15,   # -15 %
        'TTLC':  +45,   # +45 %
        'CBIBF': +110,  # +110 %
        'SIBC':  +50,   # +50 %
        'UNXC':  +20,   # +20 %
    }
    
    all_data = []
    for ticker, info in ACTIONS_BRVM.items():
        prix_init = info['prix_init']
        perf_totale = perf_cibles[ticker] / 100
        prix_final_cible = prix_init * (1 + perf_totale)
        
        # Rendement journalier moyen pour atteindre la cible
        rendement_moyen = (prix_final_cible / prix_init) ** (1 / n_jours) - 1
        
        # Générer avec volatilité MAIS en corrigeant la dérive
        prix = [prix_init]
        volatilite = info['volatilite']
        
        for i in range(n_jours - 1):
            # Rendement avec drift corrigé + bruit
            bruit = np.random.normal(0, volatilite)
            # Ajouter un "retour à la moyenne" pour ne pas dériver
            ecart_cible = np.log(prix_final_cible / prix[-1]) / (n_jours - i)
            rendement = rendement_moyen + bruit * 0.5 + ecart_cible * 0.3
            nouveau_prix = prix[-1] * np.exp(rendement)
            prix.append(nouveau_prix)
        
        # Ajustement final pour atteindre exactement la cible
        ajustement = prix_final_cible / prix[-1]
        prix = [p * (1 + (ajustement - 1) * (i / n_jours)) for i, p in enumerate(prix)]
        
        for i, date in enumerate(dates):
            all_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'ticker': ticker,
                'nom': info['nom'],
                'prix': round(prix[i], 2),
            })
    
    df = pd.DataFrame(all_data)
    print(f"✅ Prix d'actions générés : {len(df):,} lignes "
          f"({n_jours} jours × {len(ACTIONS_BRVM)} actions)")
    return df


# =====================================================================
# GÉNÉRATION DES OBLIGATIONS
# =====================================================================
def generer_obligations():
    """Génère les caractéristiques des obligations"""
    df = pd.DataFrame(OBLIGATIONS)
    print(f"✅ Obligations générées : {len(df)} obligations")
    return df


# =====================================================================
# GÉNÉRATION DES CLIENTS
# =====================================================================
def generer_clients(seed=43):
    """Génère 30 clients avec leur profil d'investisseur"""
    np.random.seed(seed)
    
    clients = []
    idx = 0
    
    for profil, config in PROFILS_CLIENTS.items():
        for _ in range(config['nb_clients']):
            if idx >= len(NOMS_CLIENTS):
                break
            
            # Capital investi selon le profil
            if profil == 'Prudent':
                capital = np.random.uniform(5_000_000, 50_000_000)
            elif profil == 'Équilibré':
                capital = np.random.uniform(10_000_000, 100_000_000)
            else:  # Dynamique
                capital = np.random.uniform(20_000_000, 200_000_000)
            
            clients.append({
                'client_id': f'CLI-{idx+1:03d}',
                'nom': NOMS_CLIENTS[idx],
                'profil': profil,
                'capital_investi_fcfa': round(capital, 0),
                'horizon_annees': np.random.choice([1, 3, 5, 10]),
                'tolerance_risque': {'Prudent': 1, 'Équilibré': 2, 'Dynamique': 3}[profil],
                'allocation_actions_pct': int(config['actions'] * 100),
                'allocation_obligations_pct': int(config['obligations'] * 100),
            })
            idx += 1
    
    df = pd.DataFrame(clients)
    print(f"✅ Clients générés : {len(df)} clients")
    return df


# =====================================================================
# GÉNÉRATION DES PORTEFEUILLES
# =====================================================================
def generer_portefeuilles(df_clients, df_actions, seed=44):
    """
    Génère l'allocation de chaque client sur les actifs.
    Répartition selon son profil + diversification aléatoire.
    """
    np.random.seed(seed)
    
    portefeuilles = []
    tickers = list(ACTIONS_BRVM.keys())
    
    for _, client in df_clients.iterrows():
        capital = client['capital_investi_fcfa']
        pct_actions = client['allocation_actions_pct'] / 100
        pct_oblig = client['allocation_obligations_pct'] / 100
        
        capital_actions = capital * pct_actions
        capital_oblig = capital * pct_oblig
        
        # Répartir sur 5 actions (diversification)
        nb_actions = 5 if pct_actions > 0.3 else 3
        actions_selectionnees = np.random.choice(tickers, size=nb_actions, replace=False)
        poids_actions = np.random.dirichlet(np.ones(nb_actions))
        
        for ticker, poids in zip(actions_selectionnees, poids_actions):
            portefeuilles.append({
                'client_id': client['client_id'],
                'client_nom': client['nom'],
                'profil': client['profil'],
                'type_actif': 'Action',
                'actif': ticker,
                'montant_fcfa': round(capital_actions * poids, 0),
                'poids_pct': round(poids * pct_actions * 100, 2),
            })
        
        # Répartir sur 2-3 obligations
        nb_oblig = 2 if pct_oblig < 0.4 else 3
        oblig_selectionnees = np.random.choice(
            [o['code'] for o in OBLIGATIONS], size=nb_oblig, replace=False
        )
        poids_oblig = np.random.dirichlet(np.ones(nb_oblig))
        
        for code in oblig_selectionnees:
            portefeuilles.append({
                'client_id': client['client_id'],
                'client_nom': client['nom'],
                'profil': client['profil'],
                'type_actif': 'Obligation',
                'actif': code,
                'montant_fcfa': round(capital_oblig * poids_oblig[list(oblig_selectionnees).index(code)], 0),
                'poids_pct': round(poids_oblig[list(oblig_selectionnees).index(code)] * pct_oblig * 100, 2),
            })
    
    df = pd.DataFrame(portefeuilles)
    print(f"✅ Portefeuilles générés : {len(df)} lignes d'allocation")
    return df


# =====================================================================
# SAUVEGARDE
# =====================================================================
def sauvegarder(df, chemin):
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin, index=False, encoding='utf-8')
    print(f"   💾 {chemin} ({len(df)} lignes)")


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("=" * 75)
    print("📈 GÉNÉRATION DES DONNÉES — GESTION DE PORTEFEUILLE")
    print("=" * 75)
    print(f"\n📊 Marché : BRVM (actions) + BEAC/État (obligations)")
    print(f"📅 Période : Janvier 2020 → Décembre 2025 (5 ans)")
    print(f"💰 Devise : FCFA\n")
    
    # 1. Prix d'actions
    print("1️⃣ Génération des prix d'actions BRVM...")
    df_actions = generer_prix_actions()
    sauvegarder(df_actions, 'data/raw/prix_actions.csv')
    
    # 2. Obligations
    print("\n2️⃣ Génération des obligations...")
    df_obligations = generer_obligations()
    sauvegarder(df_obligations, 'data/raw/obligations.csv')
    
    # 3. Clients
    print("\n3️⃣ Génération des clients...")
    df_clients = generer_clients()
    sauvegarder(df_clients, 'data/raw/clients.csv')
    
    # 4. Portefeuilles
    print("\n4️⃣ Génération des portefeuilles clients...")
    df_portefeuilles = generer_portefeuilles(df_clients, df_actions)
    sauvegarder(df_portefeuilles, 'data/raw/portefeuilles.csv')
    
    # ---- Statistiques ----
    print("\n" + "=" * 75)
    print("📊 APERÇU DES DONNÉES GÉNÉRÉES")
    print("=" * 75)
    
    print(f"\n📈 ACTIONS BRVM :")
    for ticker, info in ACTIONS_BRVM.items():
        prix_final = df_actions[df_actions['ticker'] == ticker].iloc[-1]['prix']
        perf = (prix_final / info['prix_init'] - 1) * 100
        print(f"   • {ticker:6s} ({info['nom']:25s}) : {info['prix_init']:>7,} → {prix_final:>8,} FCFA ({perf:+6.1f} %)")
    
    print(f"\n📄 OBLIGATIONS :")
    for _, obl in df_obligations.iterrows():
        print(f"   • {obl['code']:15s} | Rendement {obl['rendement_pct']:>4.1f} % | Maturité {obl['maturite_annees']} an(s) | Risque {obl['risque']}")
    
    print(f"\n👥 CLIENTS :")
    for profil in ['Prudent', 'Équilibré', 'Dynamique']:
        subset = df_clients[df_clients['profil'] == profil]
        capital_total = subset['capital_investi_fcfa'].sum()
        print(f"   • {profil:12s} : {len(subset):>2} clients | Capital total : {capital_total/1e9:>6.2f} Mds FCFA")
    
    capital_global = df_clients['capital_investi_fcfa'].sum()
    print(f"\n💰 CAPITAL TOTAL SOUS GESTION : {capital_global/1e9:.2f} Mds FCFA")
    
    print("\n" + "=" * 75)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 75)
    print("\n📁 Fichiers créés :")
    print("   • data/raw/prix_actions.csv")
    print("   • data/raw/obligations.csv")
    print("   • data/raw/clients.csv")
    print("   • data/raw/portefeuilles.csv")