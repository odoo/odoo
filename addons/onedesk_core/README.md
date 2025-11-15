# OneDesk Core - Système de Gestion Immobilière

Module Odoo pour la gestion de propriétés, réservations et intégrations avec les plateformes de réservation (Airbnb, Booking.com, VRBO).

## Fonctionnalités

- **Gestion de propriétés et unités locatives**
- **Système de réservations** avec intégration calendrier
- **Gestion automatique de tâches** (check-in, ménage, maintenance)
- **Intégrations multi-plateformes** :
  - OAuth 2.0 (API complète)
  - iCal (synchronisation calendrier)
  - CSV (import manuel)

## Installation

### 1. Dépendances Python

Installez les bibliothèques Python requises :

```bash
pip3 install cryptography requests icalendar
```

**Note :** `cryptography` est fortement recommandé pour la sécurité des tokens OAuth.

### 2. Configuration de la clé de chiffrement (IMPORTANT)

Pour sécuriser les tokens OAuth, vous devez configurer une clé de chiffrement dans votre fichier de configuration Odoo.

#### Générer une clé de chiffrement

Exécutez ce script Python pour générer une clé sécurisée :

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

Vous obtiendrez une clé similaire à : `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx=`

#### Ajouter la clé dans odoo.conf

Ouvrez votre fichier `odoo.conf` (généralement dans `/etc/odoo/` ou `~/.odoorc`) et ajoutez :

```ini
[options]
# ... autres paramètres ...

# Clé de chiffrement pour OneDesk
onedesk_encryption_key = VOTRE_CLE_GENEREE_ICI
```

**⚠️ IMPORTANT :**
- **Gardez cette clé secrète** - Ne la commitez jamais dans Git
- **Sauvegardez la clé** - Sans elle, vous perdrez l'accès aux tokens existants
- **Utilisez une clé unique par environnement** (dev/staging/production)
- **Permissions fichier** : `chmod 600 odoo.conf` pour protéger le fichier

#### Que se passe-t-il sans clé de chiffrement ?

Le module fonctionnera mais avec un **avertissement de sécurité** :
- Les tokens OAuth seront stockés **en clair** dans la base de données
- Un warning sera affiché dans les logs
- **Non recommandé pour la production**

### 3. Installation du module

```bash
# Mettre à jour la liste des modules
odoo-bin -u onedesk_core -d votre_database

# Ou via l'interface Odoo :
# Apps > Mettre à jour la liste des apps > Chercher "OneDesk" > Installer
```

## Configuration

### 1. Créer des propriétés et unités

1. Aller dans **OneDesk > Configuration > Propriétés**
2. Créer vos propriétés
3. Ajouter des unités à chaque propriété

### 2. Configurer les intégrations

#### Méthode OAuth (Recommandée)

1. Aller dans **OneDesk > Intégrations > Créer**
2. Sélectionner la plateforme (Airbnb, Booking.com)
3. Choisir "OAuth 2.0"
4. Suivre les instructions pour obtenir Client ID et Secret
5. Cliquer sur "Connecter" et autoriser l'accès
6. La synchronisation démarre automatiquement

#### Méthode iCal (Rapide)

1. Créer une intégration
2. Choisir "iCal URL"
3. Copier l'URL iCal depuis votre plateforme
4. Coller dans le champ "URL iCal"
5. Cliquer sur "Synchroniser maintenant"

#### Méthode CSV

1. Exporter vos réservations en CSV depuis la plateforme
2. Créer une intégration avec méthode "CSV Import"
3. Importer le fichier CSV

### 3. Synchronisation automatique

- Par défaut, synchronisation toutes les **15 minutes**
- Configurable par intégration (champ "Fréquence de sync")
- Désactivable avec le flag "Auto-sync"

## Utilisation

### Gestion des réservations

Les réservations apparaissent automatiquement :
- Dans **OneDesk > Réservations**
- Dans le **Calendrier Odoo**
- Avec création automatique de tâches (check-in, ménage)

### Gestion des tâches

Les tâches sont créées automatiquement et assignables :
- Check-in (à la date de début)
- Ménage (après check-out)
- Maintenance (manuel)

### Suivi des synchronisations

Consultez les logs :
- **OneDesk > Intégrations > [Sélectionner] > Onglet Historique**
- Affiche succès, erreurs, nombres d'enregistrements

## Sécurité

### Permissions par défaut

- **Utilisateurs** : Lecture/Écriture sur propriétés, unités, réservations, tâches
- **Administrateurs** : Gestion complète des intégrations et fournisseurs

### Recommandations

1. **Production** :
   - Toujours utiliser le chiffrement (clé dans odoo.conf)
   - Restreindre l'accès aux intégrations (groupe système)
   - Sauvegarder régulièrement la clé de chiffrement
   - Utiliser HTTPS pour Odoo

2. **OAuth** :
   - Vérifier les scopes demandés
   - Révoquer les accès inutilisés
   - Surveiller les logs d'intégration

3. **Données** :
   - Vérifier les RGPD pour données clients
   - Limiter la rétention des logs
   - Anonymiser les données de test

## Dépannage

### Erreur : "encryption key not configured"

**Problème :** Clé de chiffrement manquante

**Solution :**
1. Générer une clé (voir section Installation)
2. Ajouter dans odoo.conf
3. Redémarrer Odoo

### Erreur : "with_delay not found"

**Problème :** Module queue_job non installé

**Solution :** Le module gère automatiquement cette situation (sync directe). Si vous voulez la sync asynchrone, installez `queue_job` :
```bash
pip3 install odoo-queue-job
```

### Conflit de réservation

**Message :** "⚠️ Conflit de réservation détecté!"

**Cause :** Une réservation existe déjà pour cette unité pendant cette période

**Solutions :**
- Vérifier le calendrier
- Modifier les dates
- Choisir une autre unité

### OAuth expired

**Problème :** Token expiré

**Solution :** Le module rafraîchit automatiquement les tokens. Si ça échoue :
1. Aller dans l'intégration
2. Cliquer "Reconnecter"
3. Réautoriser l'accès

### iCal non synchronisé

**Vérifications :**
- URL iCal correcte et accessible
- Fréquence de mise à jour de la plateforme (peut prendre 24h)
- Logs d'erreur dans l'onglet Historique

## Architecture technique

### Modèles principaux

- `onedesk.property` - Propriétés
- `onedesk.unit` - Unités locatives
- `onedesk.reservation` - Réservations
- `onedesk.task` - Tâches
- `onedesk.integration` - Intégrations plateformes
- `onedesk.integration.provider` - Fournisseurs
- `onedesk.integration.log` - Logs de sync

### Chiffrement

Utilise **Fernet** (cryptographie symétrique) :
- Algorithme AES-128-CBC
- Clé stockée dans odoo.conf
- Tokens chiffrés au repos dans PostgreSQL

### Détection de conflits

Algorithme de chevauchement de dates :
```python
overlap = (start1 < end2) AND (end1 > start2)
```

Vérifie toutes les réservations de l'unité avant création/modification.

## Développement

### Ajouter un nouveau fournisseur

1. Créer une entrée dans `data/integration_providers.xml`
2. Configurer OAuth endpoints et scopes
3. Adapter `_parse_provider_response()` si nécessaire
4. Tester avec sandbox de la plateforme

### Personnaliser les tâches

Modifier `onedesk_task.py` > `create_task_from_reservation()` pour :
- Ajouter types de tâches
- Personnaliser délais
- Ajouter logique métier

## Support

Pour des questions ou bugs :
1. Vérifier les logs Odoo
2. Consulter l'onglet Historique des intégrations
3. Contacter : Merveilles (auteur du module)

## Licence

LGPL-3

## Changelog

### Version 1.0.0
- Gestion propriétés et unités
- Système de réservations
- Intégrations Airbnb, Booking.com, VRBO
- OAuth 2.0 avec chiffrement
- Synchronisation iCal
- Gestion automatique des tâches
- Détection de conflits de réservation
- Intégration calendrier Odoo
