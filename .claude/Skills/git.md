# Convention Git — rebase + 1 PR par issue

Source de vérité appliquée à **tous** les projets. L'agent comme les humains s'y conforment.

## Principes

- **Issue-driven** : 1 issue = 1 branche = 1 PR. Pas de travail sans issue, pas de push direct sur `main`.
- **Historique linéaire** : aucun commit de merge (`Merge branch ...`). On rebasette, on ne merge pas.
- **Squash-merge** à la fin : la PR entière devient **un seul** commit conventionnel sur `main`.
- `main` est toujours déployable, toujours à jour avec la prod.

---

## Nomenclature des branches

```
<type>/<issue>-<description-courte>
```

- **type** (obligatoire) : `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `style`
- **issue** (obligatoire) : numéro de l'issue GitHub, sans le `#`
- **description-courte** : kebab-case, minuscules, sans accent, ~3-5 mots résumant l'issue

**Règles strictes**
- Minuscules partout, séparateur `-`, **pas** d'underscore, **pas** d'espace.
- Max 50 caractères.
- Préfixe du type + numéro d'issue obligatoires.

**Exemples valides**
```
feat/42-oauth-login
fix/107-api-rate-limit
docs/23-readme-install
refactor/58-db-connection-pool
chore/91-deps-bump-requests
```

**Exemples invalides**
```
Feature/42-login          # majuscule + type mal orthographié
fix_107_rate_limit        # underscore
42-oauth-login            # pas de type
feat/oauth-login          # pas de numéro d'issue
toto-truc                 # ni type ni issue
```

---

## Nomenclature des commits

Format **Conventional Commits** :

```
<type>(<scope>): <description>

<corps optionnel>

<footer optionnel>
```

**Règles strictes**
- **type** : identique à la liste des types de branches.
- **scope** : optionnel, entre parenthèses, sans espace.
- **description** : impératif présent, minuscule, **sans point final**, max 72 caractères.
  - ✅ `add oauth login flow` — ❌ `Added oauth login flow.` / `ajoute le login oauth`
- **corps** : explique le **pourquoi** (pas le quoi). Séparé du sujet par une ligne vide. Largeur max 100 caractères.
- **footer** : références d'issue (`Closes #42`), `BREAKING CHANGE: <desc>` pour les cassures, `Co-Authored-By:` pour les co-auteurs (agents notamment).
- Un commit = un changement logique cohérent. Les commits "wip" sont autorisés sur la branche (ils seront squashés), interdits sur `main`.

**Exemples**

Sujet seul :
```
fix(api): handle 429 rate limit with backoff
```

Avec corps et footer (référence l'issue) :
```
feat(auth): add oauth login flow

The previous session-based login did not support SSO providers.
OAuth2 authorization code flow is now the default, with a fallback
to sessions for local dev.

Closes #42
BREAKING CHANGE: LOGIN_STRATEGY env var is now required.
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

---

## Nomenclature des PR

### Titre

Le titre de la PR **devient le commit de squash** sur `main`. Il respecte donc **exactement** le format commit :

```
<type>(<scope>): <description>
```

Le squash-merge reprend ce titre (configuré via les règles de protection : *Squash merge* + *Default commit message = PR title*).

### Description (template obligatoire)

```markdown
Closes #<issue>

## Pourquoi
< contexte / problème décrit dans l'issue. pas de code ici. >

## Quoi
< liste à puces des changements utilisateur / API. >

## Comment
< choix technique en 2-3 lignes. seulement si non évident. >

## Tests
- [ ] tests unitaires ajoutés / mis à jour
- [ ] vérifié en local sur < scénario >

## Breaking
- [ ] aucune
- [ ] oui : < détail + migration >

## Checklist
- [ ] branche rebasée sur `main` à jour
- [ ] CI verte
- [ ] pas de commit de merge
- [ ] labels posés (`type:*`, `area:*`, `priority:*` si pertinent)
```

**Règles strictes**
- `Closes #<issue>` en première ligne — obligatoire (ferme l'issue au merge).
- Les sections `## Pourquoi`, `## Quoi` et `## Tests` sont **obligatoires**.
- Une PR sans description remplie n'est pas mergable.
- Une PR = une issue. Si elle résout 2 issues → splitter en 2 PR.

---

## Workflow pas-à-pas

```bash
# 0. L'issue #42 existe sur GitHub. On part de main à jour.
git checkout main
git pull --rebase

# 1. Créer la branche (nomenclature stricte : type/issue-description)
git switch -c feat/42-oauth-login

# 2. Coder, committer (conventionnel)
git add -p
git commit -m "feat(auth): add oauth login flow"

# 3. Avant d'ouvrir la PR : rebase sur main
git fetch origin
git rebase origin/main
# résoudre les conflits si besoin, puis :
git rebase --continue

# 4. Pousser et ouvrir la PR (titre = futur commit de squash)
git push -u origin feat/42-oauth-login
gh pr create --title "feat(auth): add oauth login flow" \
             --body "Closes #42

## Pourquoi
...
"

# 5. Après review + CI verte : SQUASH-MERGE (jamais "merge commit")
gh pr merge --squash --delete-branch
# l'issue #42 est automatiquement fermée par le "Closes #42"
```

### Mise à jour d'une PR en cours

Toujours rebase, jamais merge de main dans la branche :
```bash
git fetch origin
git rebase origin/main
git push --force-with-lease   # force-with-lease, JAMAIS --force brut
```

---

## Règles de protection de `main`

À configurer sur chaque repo (Settings → Branches → Branch protection) :

- ✅ Require a pull request before merging
- ✅ Require approvals (≥1)
- ✅ Require status checks to pass before merging (CI obligatoire)
- ✅ Require branches to be up to date before merging
- ✅ Require linear history (**interdit les merge commits**)
- ✅ Allow squash merging uniquement (désactiver *Create a merge commit* et *Rebase merge* dans les paramètres repo)
- ✅ Automatically delete head branches after merge

---

## Cas particuliers

### Issue de bug en prod (hotfix)
Issue créée sur GitHub, branche `fix/<issue>-<description>`. Branche depuis `main`, PR + squash-merge vers `main`, puis tag de release. Pas de branche `hotfix/` dédiée — on reste sur `fix/`.

### Release / versionning
Tag sur `main` après merge : `v<major>.<minor>.patch` (semver). Un footer `BREAKING CHANGE:` dans le commit de squash déclenche un bump major.

### Plusieurs commits sur une issue
Autorisé sur la branche (wip, fixes intermédiaires). Au squash-merge, ils sont fusionnés en **un seul** commit conventionnel dont le titre = titre de la PR. L'historique granulaire est conservé dans la PR fermée, pas sur `main`.
