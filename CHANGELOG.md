# Changelog

Toutes les évolutions notables du dépôt `its-dp-fab-ucs-reporting-fees-et-wip-managed` (configuration de déploiement,
pipelines, outillage, documentation) sont consignées ici, de la plus récente à la plus ancienne.

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Ce dépôt n'est pas versionné
par tag : chaque entrée est datée (`## AAAA-MM-JJ`). Les évolutions du socle commun sont décrites
dans le `CHANGELOG.md` de `its-dp-fab-cicd-common`, versionné par tag `vX.Y.Z`.

## 2026-10-31

### Changed

- Fichiers issus d'une copie du dépôt Framework (commit `244ac58`), réécrits pour UCS Reporting
  Fees & WIP (socle `its-dp-fab-cicd-common`, tag `v1.5.0`, catégorie `ucs`, référence de forme :
  dépôt Alexandrie) :
  - `CICD/pipelines/CI.yml` : template KPMG conservé (le socle n'a pas de template CI pour les
    consommateurs) ; SonarQube UCS repris de l'ancienne CI UCS ; déclencheurs `develop`,
    `release/*`, `main` ; filtre d'artefact `"!/*.json"` (l'ancien `!**/*.json` non quoté est écarté).
  - `CICD/pipelines/CD.yml` : `repository: its-dp-fab-ucs-reporting-fees-et-wip-managed`,
    `role: consumer`, source CI `its-dp-fab-ucs-reporting-fees-et-wip-managed-ci`,
    `frameworkGate: "off"` (aucune dépendance de déploiement, R5), coffre `frfrkvdevdp0001`.
  - `CICD/pipelines/PR-Validation.yml` : en-tête UCS, contenu inchangé.
  - `CICD/deployment/config.yml` : workspace ITG `FR - DP - ITG - FAB - UCS - Reporting Fees & WIP - Managed` ;
    DEV, PPR, PRD en marqueurs `__A_RELEVER__` ; `item_types_in_scope` vide ; clé `core.parameter`,
    `folder_exclude_regex` et `features` retirés.
  - `CICD/deployment/dependencies.yml` : `role: consumer`, `category: ucs`, `framework.required: false` ;
    connexion `DP-Fabric-Global-APR`, Variable Library `vl_core_config` et `guid_policy` du Framework retirés.
  - `CICD/deployment/parameter.yml` : 56 règles Framework retirées ; aucune règle.
  - `CICD/ref_dynamique/01_inventaire_github.py` à `04_recoupement.py` : détection Framework / MDS et
    union de branches retirées ; dépôt UCS seul, une branche, workspace ITG UCS par défaut ; sorties
    hors du dépôt (plus de dossier `sortie/`) ; activités imbriquées et références croisées relevées ;
    `03` ne propose plus de GUID mais des règles `$workspace.$id` / `$items.<Type>.<nom>.$id` ;
    `04` classe les constats (couvertes, non couvertes, GUID inconnus, règles inutiles, références
    obsolètes, incohérences de workspace et de type).
  - `CICD/ref_dynamique/templates/config.yml` et `parameter.yml` : modèles UCS au format du socle
    (noms de workspaces, aucun GUID, aucune clé en minuscules).
  - `.gitignore` : remplacé par celui des dépôts MDS et Alexandrie, à l'identique (`.gitattributes`
    était déjà identique).
  - README réécrit pour UCS ; ce journal remplace celui du Framework, copié par erreur.
  - `CICD/deployment/config.yml` : workspaces `FR - DP - <ENV> - FAB - UCS - Reporting Fees & WIP - Managed`
    pour DEV, ITG, PPR et PRD (confirmés le 31/10/2026, tiret simple).
  - `CICD/pipelines/CD.yml` : commentaire de la décision du 31/10/2026 (3 service connections ARM
    distinctes ITG, PPR, PRD ; noms à renseigner).

### Removed

- `fabric/test.md` (contenu « test », référencé par aucun pipeline ni script ; suppression validée).

### Added

- `fabric/.gitkeep` : dossier des items suivi par Git avant la première synchronisation.

### Vérifié

- `yamllint` (règles du socle) sur `CICD/deployment` et `CICD/pipelines` : sans erreur.
- `python -m compileall CICD/ref_dynamique` : sans erreur ; syntaxe compatible Python 3.9.
- `deploy.py validate` (socle `v1.5.0`) : code 4 attendu (« Aucun item Fabric »). Sur une copie de
  travail munie d'un item fictif : 0 erreur, `repository_directory` résolu vers `fabric/`, matrice
  `ucs` acceptée.
- Scripts 01 à 04 exécutés sur le dépôt (vide) et sur un jeu d'essai hors dépôt : règles proposées
  acceptées par `deploy.py validate`, aucune écriture dans le dépôt.

### À confirmer

- Organisation et service connection GitHub ; noms des 3 service connections ARM ITG, PPR et PRD (création prévue).
- Casse exacte du pipeline CI dans Azure DevOps.
- Types d'items, règles, connexions Fabric, Variable Libraries, `guid_policy` et `data_dependencies`,
  après synchronisation Git Integration.
- Point V-01 : le filtre `contents: "!/*.json"` de l'artefact CI ne doit pas exclure les fichiers d'items.
