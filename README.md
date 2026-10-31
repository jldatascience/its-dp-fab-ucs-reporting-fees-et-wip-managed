# its-dp-fab-ucs-reporting-fees-et-wip-managed — UCS Reporting Fees & WIP

Dépôt GitHub des items Microsoft Fabric du workspace **UCS Reporting Fees & WIP**, et de leur configuration de déploiement. UCS (*use case*) est un cas d'usage de restitution : il peut **consommer des données** produites par d'autres Data Products, mais ne dépend d'aucun d'eux pour être déployé.

Ce dépôt ne contient **aucun code de déploiement**. Il décrit *quoi* déployer et *où*. La logique (contrôles, publication, vérification, rapport) se trouve dans le dépôt socle commun `its-dp-fab-cicd-common`, appelé par le tag `v1.5.0`.

> **État au 31/10/2026 : le dépôt ne contient encore aucun item Fabric, et rien n'est déployable.**
> `fabric/` ne contient que `.gitkeep`. `deploy.py validate` s'arrête en code 4 (« Aucun item Fabric ») avant les contrôles statiques, et la CD refuserait de toute façon toute publication (`inventory_status: pending`, marqueurs à relever).

| Rubrique | Valeur |
|---|---|
| Catégorie | `ucs` ; rôle `consumer` dans le socle |
| Workspace DEV | `FR - DP - DEV - FAB - UCS - Reporting Fees & WIP - Managed` (confirmé le 31/10/2026 ; Git Integration, jamais déployé par la CD) |
| Workspace ITG | `FR - DP - ITG - FAB - UCS - Reporting Fees & WIP - Managed` (confirmé) |
| Workspace PPR | `FR - DP - PPR - FAB - UCS - Reporting Fees & WIP - Managed` (confirmé le 31/10/2026) |
| Workspace PRD | `FR - DP - PRD - FAB - UCS - Reporting Fees & WIP - Managed` (confirmé le 31/10/2026 ; tiret simple à vérifier dans le portail) |
| Branches | `develop` (par défaut) · `release/*` · `main` |
| Pipelines Azure DevOps | CI : `its-dp-fab-ucs-reporting-fees-et-wip-managed-ci` (nom repris de l'ancienne CD, casse à confirmer) · CD : à créer depuis `CICD/pipelines/CD.yml` · validation de PR : à créer depuis `CICD/pipelines/PR-Validation.yml` |
| Socle commun | `its-dp-fab-cicd-common`, tag `v1.5.0` |
| Statut d'inventaire | `pending` : la CD refuse toute publication tant que l'inventaire n'est pas validé sur la branche réelle |

## Dépendances

**Aucune dépendance de déploiement** (matrice v1.3 du socle, règle R5).

- UCS ne dépend **ni du Framework, ni d'un ADP, ni d'un BDP** pour être déployé : aucun pré-vol Framework, aucune porte Azure DevOps, aucun ordre de déploiement.
- `dependencies.yml` le traduit par `category: ucs` et `framework.required: false`, sans `workspace`, `items` ni `ado_gate` (sinon `DEPS_UCS_INDEPENDENT`).
- `CD.yml` passe `frameworkGate: "off"`. Le socle n'applique de toute façon la porte qu'aux catégories `adp` et `bdp` ; avec `ado`, le rapport indiquerait seulement `GATE_NOT_APPLICABLE`.
- Une **consommation de données** (lecture de tables d'un autre Data Product) se résout **à l'exécution** (shortcut, Variable Library) et se déclare dans `data_dependencies` (`kind: data | technical | execution`). Elle reste documentaire et **jamais bloquante** (R6).
- Conséquence pour `parameter.yml` : aucune référence résolue au déploiement vers un autre workspace, Framework compris (`DEPS_CROSS_WORKSPACE_FORBIDDEN`). Seules les références au workspace UCS courant sont admises.

| Nature de dépendance | Déclarée où | Bloquante | État au 31/10/2026 |
|---|---|---|---|
| Déploiement | — (interdite pour UCS) | — | Aucune |
| Données, technique, exécution | `data_dependencies` | Non | Aucune confirmée |
| Connexions Fabric | `connections` (vérifiées au pré-vol) | Oui, au pré-vol | À relever |
| Variable Libraries | `variable_libraries` | Oui, après publication | À relever |

## Arborescence

```text
its-dp-fab-ucs-reporting-fees-et-wip-managed/   branches develop (défaut) · release/* · main
│
├── .gitattributes                       # normalisation des fins de ligne (LF ; CRLF pour PowerShell/batch)
├── .gitignore                           # identique aux dépôts MDS et Alexandrie (caches Python, .env, sorties ref_dynamique)
├── CHANGELOG.md                         # journal des changements du dépôt (entrées datées)
├── README.md                            # ce fichier
│
│  ── Déploiement (lu par Azure DevOps, jamais publié dans Fabric) ──
├── CICD/
│   ├── deployment/
│   │   ├── config.yml                   # workspaces UCS DEV, ITG, PPR, PRD (confirmés),
│   │   │                                #   repository_directory: "../../fabric", types (vide)
│   │   ├── dependencies.yml             # category ucs : aucune dépendance de déploiement (R5)
│   │   └── parameter.yml                # aucune règle (en-tête : seule famille admise pour UCS)
│   ├── pipelines/
│   │   ├── CD.yml                       # pipeline ADO de CD → CICD/pipelines/templates/cd-pipeline.yml@cicd_common
│   │   ├── CI.yml                       # pipeline ADO de CI (template KPMG) : version, SonarQube, artefact « fabric »
│   │   └── PR-Validation.yml            # check obligatoire des PR → CICD/pipelines/templates/validate-pipeline.yml@cicd_common
│   └── ref_dynamique/                   # référencement dynamique : inventaire et proposition de règles
│       ├── templates/
│       │   ├── config.yml               #   modèle de config.yml (noms de workspaces, types)
│       │   └── parameter.yml            #   modèle de parameter.yml (règles workspace courant)
│       ├── 01_inventaire_github.py      # inventaire Git (une branche)
│       ├── 02_fab_cli.py                # inventaire Fabric d'un environnement (Fabric CLI)
│       ├── 03_remplir.py                # rendu des modèles, hors dépôt
│       └── 04_recoupement.py            # recoupement Git × Fabric × parameter.yml
│
│  ── Contenu du workspace UCS (Git Integration DEV + publication fabric-cicd) ──
└── fabric/
    └── .gitkeep                         # fichier vide de maintien du dossier (aucun item Fabric)
```

`CICD/pipelines/templates/` n'existe **pas** dans ce dépôt : les chemins `CICD/pipelines/templates/*.yml@cicd_common` désignent les templates du socle.

`repository_directory` est résolu **relativement au dossier de `config.yml`** (`CICD/deployment/`), par fabric-cicd 1.4.0 comme par le socle : `"../../fabric"` désigne le dossier `fabric/` à la racine du dépôt (vérifié avec `deploy.py validate` le 31/10/2026).

`fabric/.gitkeep` est un fichier vide qui maintient le dossier dans Git tant qu'aucun item n'est synchronisé (Git ne suit pas les dossiers vides). Il remplace `fabric/test.md` (contenu « test », référencé nulle part), avec validation le 31/10/2026. Il n'est pas un item Fabric : le socle et fabric-cicd ne découvrent que les dossiers munis d'un `.platform`. Il pourra être retiré une fois des items présents.

## Pipelines

### `CI.yml`

- Template KPMG `PipelineTemplate.yaml@CICD` (dépôt « Plateforme Technologique/CICD ») **conservé** : le socle v1.5.0 ne fournit aucun template CI pour les consommateurs.
- Déclencheurs : `develop`, `release/*`, `main` (et non plus la branche `feature/its/1_fabric_item_synchronization`).
- SonarQube : projet `Discovery_DP-FAB-UCS-Reporting-Fees-et-Wip-Managed`, repris de l'ancienne CI UCS.
- Artefact `fabric` : copie du dépôt (sous-dossier `binaries`, lu par la CD), filtre `contents: "!/*.json"` aligné sur les autres dépôts. L'ancien filtre `!**/*.json` non quoté était une étiquette YAML et, comme motif, aurait exclu tous les JSON des items. Point V-01 à vérifier au premier run.

### `CD.yml`

- `extends` du template `CICD/pipelines/templates/cd-pipeline.yml@cicd_common`, tag `v1.5.0`.
- `repository: its-dp-fab-ucs-reporting-fees-et-wip-managed`, `role: consumer` (le template n'accepte que `framework` ou `consumer`).
- `devMode: skip` : aucun stage DEV. `frameworkGate: "off"`.
- Un run ne déploie qu'**un seul environnement**, celui de la branche source de l'artefact CI : `develop` → ITG, `release/*` → PPR, `main` → PRD. Toute autre branche est refusée.
- Stages : `Validate_Artifact` (route, contrôles statiques rejoués, empreinte SHA-256), puis `Deploy_<ENV>` : intégrité de l'artefact, secrets lus dans le coffre, pré-vol Fabric, publication fabric-cicd, vérification après publication, rapport `deployment-report-<ENV>`.
- Approbations PPR et PRD : Environments ADO `fabric-ppr` et `fabric-prd` (Approvals and checks), pas dans le YAML.

### `PR-Validation.yml`

- `extends` du template `CICD/pipelines/templates/validate-pipeline.yml@cicd_common`, sans paramètre (`cicdRoot: CICD` par défaut).
- Contrôles bloquants, sans accès au tenant ni secret :
  - `yamllint` de `CICD/deployment` et `CICD/pipelines` ;
  - `deploy.py validate` : structure, JSON des items, `config.yml` et `parameter.yml` validés par fabric-cicd, règles sans effet, GUID en dur, secrets, matrice de dépendances.
- Les scripts de `CICD/ref_dynamique/` ne sont pas contrôlés par ce template.
- À déclarer comme *Required status check* sur `develop`, `release/*` et `main`. **Le check sera rouge tant que `fabric/` ne contient aucun item** (attendu).

## Configuration de déploiement

### `config.yml`

```yaml
core:
  workspace:
    DEV: "FR - DP - DEV - FAB - UCS - Reporting Fees & WIP - Managed"
    ITG: "FR - DP - ITG - FAB - UCS - Reporting Fees & WIP - Managed"
    PPR: "FR - DP - PPR - FAB - UCS - Reporting Fees & WIP - Managed"
    PRD: "FR - DP - PRD - FAB - UCS - Reporting Fees & WIP - Managed"
  repository_directory: "../../fabric"
  item_types_in_scope: []
```

- Workspaces désignés par leur **nom exact** (le socle refuse `workspace_id`). Un marqueur `__A_RELEVER__` est un avertissement tant que l'inventaire est `pending`, une erreur ensuite.
- `item_types_in_scope` est **vide** car aucun item n'existe : la liste se remplit uniquement avec les types relevés dans les `.platform` de `fabric/`. Vide, elle est bloquante (voulu) ; ne pas retirer la clé, sinon fabric-cicd publierait tous les types.
- Clé `parameter` absente tant que `parameter.yml` n'a aucune règle.
- `publish.skip` à `false` partout : DEV est exclu par la CD (`devMode: skip`), pas par fabric-cicd. `unpublish.skip` à `true` partout : aucune suppression automatique d'items orphelins.

### `dependencies.yml`

`schema_version: 1`, `role: consumer`, `category: ucs`, `inventory_status: pending`, `framework.required: false`. Les listes `data_dependencies`, `connections`, `variable_libraries` et `guid_policy` sont vides et à relever à l'inventaire. Aucune connexion du Framework n'est reprise sans preuve d'usage par un item UCS.

### `parameter.yml`

Aucune règle. Les 56 règles du Framework ne s'appliquent pas à UCS. Seule famille admise, pour chaque activité InvokePipeline ou TridentNotebook qui appelle un item UCS : une règle `workspaceId` → `$workspace.$id` et une règle `pipelineId` ou `notebookId` → `$items.<Type>.<nom>.$id`. Aucun GUID littéral.

## Référencement dynamique (`CICD/ref_dynamique/`)

Les items synchronisés par Git Integration contiennent les GUID de leur workspace d'origine. Les règles de `parameter.yml` les remplacent, au déploiement, par les ID du workspace cible. Les quatre scripts aident à établir ces règles. Ils sont **en lecture seule** : ils n'écrivent rien dans le dépôt ni dans Fabric.

| Script | Lit | Produit (hors dépôt) |
|---|---|---|
| `01_inventaire_github.py` | une branche Git (défaut `feature/its/411581_industrialisation_chaine_cicd`, sans checkout ni fusion de branches) | `inventaire_ucs.json`, `activites_ucs.csv`, `toutes_refs_ucs.csv` |
| `02_fab_cli.py` | un workspace UCS via Fabric CLI (`--env`, défaut ITG ; `--workspace` ou `--workspace-id`) | `fabric_<ENV>.json`, `activites_fabric_<ENV>.csv` |
| `03_remplir.py` | sorties 01 et 02, `templates/` | `config.rendu.yml`, `parameter.rendu.yml`, `diff_*.txt`, `references_non_converties_ucs.csv` |
| `04_recoupement.py` | sorties 01 et 02, `CICD/deployment/parameter.yml` (ou `--parameter`) | `recoupement_ucs.csv`, `rapport_recoupement_ucs.md` |

- **Dossier de sortie** : `--out`, sinon la variable `REF_DYN_OUT`, sinon `<dossier temporaire système>/ref_dynamique/its-dp-fab-ucs-reporting-fees-et-wip-managed`. Un dossier situé dans le dépôt est refusé. Aucun dossier `sortie/` n'est créé.
- Les scripts ne visent que ce dépôt (contrôle du remote `origin` ou du nom du dossier) et que des workspaces UCS : aucun nom de workspace Framework ou MDS n'est utilisé.
- `03_remplir.py` ne propose que des règles **justifiées** : activité relevée dans Git, item appelé identifié dans un inventaire Fabric UCS et présent sous `fabric/`. Les références inter-workspace ou non identifiées sont listées, jamais converties.
- `04_recoupement.py` classe les constats : `COUVERTE`, `NON_COUVERTE`, `GUID_INCONNU`, `REGLE_INUTILE`, `REFERENCE_OBSOLETE`, `INCOHERENCE_WORKSPACE`, `INCOHERENCE_TYPE` (code retour 1 s'il reste un constat bloquant).
- Les fichiers produits contiennent des ID Fabric, **jamais de secret**.

Enchaînement, depuis `CICD/ref_dynamique/` (environnement Python du socle, qui fournit PyYAML) :

```bash
fab auth login
python 01_inventaire_github.py
python 02_fab_cli.py --env DEV                                              # environnement source des GUID
python 02_fab_cli.py                                                        # ITG
python 03_remplir.py
python 04_recoupement.py
```

Le dossier `templates/` contient les **modèles** de `config.yml` et `parameter.yml` au format du socle v1.5.0 (noms de workspaces, aucun GUID). Leurs marqueurs `<<WS_UCS_<ENV>>>`, `<<ITEM_TYPES_IN_SCOPE>>` et `<<REGLES_WORKSPACE_COURANT>>` sont résolus par `03_remplir.py`. Le rendu se recopie à la main dans `CICD/deployment/`, dans une PR revue, puis `deploy.py validate` doit passer sans erreur.

Pour vérifier un nom exact (tirets compris) : les ID des workspaces UCS ITG, PPR et PRD de l'ancien `deploy.py` figurent dans le registre du socle (`CICD/registry/known_guids.yml`). `python 02_fab_cli.py --env PRD --workspace-id <id>` affiche le nom tel qu'il est dans Fabric.

## Environnements, branches et déploiement

| Branche | Rôle | Déploiement | Réglage |
|---|---|---|---|
| `feature/*` | Développement | Aucun | PR vers `develop` |
| `develop` | Branche par défaut ; intégration des features | DEV par Git Integration (si le workspace existe) ; ITG par la CD | Protégée ; workspace DEV connecté à `develop`, dossier Git `fabric` |
| `release/*` | Une branche par release, créée depuis `develop` au besoin | PPR par la CD, après approbation | Protégée (PR obligatoire, check PR-Validation) |
| `main` | Reflet de la production | PRD par la CD, après approbation | Protégée (PR obligatoire depuis `release/*`) |

La CD déploie des **définitions d'items** : elle n'exécute aucun pipeline et ne charge aucune donnée.

## Secrets et service connections

- Identité qui publie dans Fabric : le SPN de l'environnement. Ses trois secrets `<ENV>-AZURE-CLIENT-ID`, `-CLIENT-SECRET` et `-TENANT-ID` sont lus dans le **coffre unique `frfrkvdevdp0001`** (commun aux 11 dépôts, décision du 22/10/2026) par la tâche `AzureKeyVault@2` du template imposé.
- Accès au coffre : **une service connection Azure Resource Manager distincte par environnement**, créée par Ops en fédération d'identité. Trois sont prévues (ITG, PPR, PRD), aucune pour DEV. Le socle refuse à la compilation une service connection partagée entre deux environnements. Les marqueurs `__A_CONFIRMER_SERVICE_CONNECTION_ARM_<ENV>__` sont imposés par le socle : c'est la chaîne que détecte sa garde de compilation.
- Le groupe de variables `Fabric-CD-Secrets` de l'ancienne CD n'est plus utilisé. Il ne doit pas être supprimé tant que les anciennes CD ne sont pas désactivées (backlog B33).
- Aucun secret n'est versionné. L'ancien `deployment/deploy.py` UCS (ID de workspaces, capacités et SPN en dur) n'existe pas dans ce dépôt et ne doit pas y revenir : le socle le refuse (`STRUCT_LEGACY_DEPLOY_HARDCODED_IDS`).

## Contribuer

1. Travailler dans le workspace UCS DEV, puis enregistrer sur une branche `feature/*` (Source control de Fabric, dossier `fabric`).
2. Lancer les scripts de `CICD/ref_dynamique/`, puis reporter dans `CICD/deployment/` les types d'items et les règles retenues.
3. Ne jamais ajouter de référence résolue au déploiement vers un autre workspace : déclarer la consommation dans `data_dependencies`.
4. Ouvrir une PR vers `develop` et corriger jusqu'à ce que le check PR-Validation soit vert.

Pour contrôler le dépôt en local, à partir d'un clone du socle :

```bash
python ../its-dp-fab-cicd-common/CICD/tools/deploy.py validate --repo .
```

## Marqueurs à relever

| Fichier | Paramètre | Valeur attendue | Comment l'obtenir | Bloquant |
|---|---|---|---|---|
| `CICD/pipelines/CD.yml`, `PR-Validation.yml` | `endpoint` | Service connection GitHub du projet Data Platform | Azure DevOps → Project settings → Service connections | Oui (compilation) |
| `CICD/pipelines/CD.yml`, `PR-Validation.yml` | `name` (organisation) | Organisation GitHub du socle | GitHub / Plateforme Technologique | Oui (compilation) |
| `CICD/pipelines/CD.yml` | `serviceConnections.ITG/PPR/PRD` | Noms des 3 service connections ARM distinctes (création prévue, décision du 31/10/2026) | Ops (fédération d'identité) | Oui (stage concerné) |
| `CICD/pipelines/CD.yml` | `source` du pipeline CI | Nom exact du pipeline CI | Azure DevOps → Pipelines | Oui (déclenchement) |
| `CICD/deployment/config.yml` | `item_types_in_scope` | Types des items | `01_inventaire_github.py` | Oui |
| `CICD/deployment/dependencies.yml` | `connections`, `variable_libraries`, `guid_policy`, `data_dependencies` | Relevés d'inventaire | Scripts 01, 02 et 04 | Selon contenu |

## Avant le premier déploiement

- [x] `fabric/test.md` remplacé par `fabric/.gitkeep` (31/10/2026).
- [x] Nom du workspace UCS DEV confirmé (31/10/2026).
- [ ] Connecter la Git Integration du workspace DEV au dossier `fabric` de `develop`.
- [ ] Synchroniser les items, lancer les scripts 01 à 04, puis renseigner `item_types_in_scope`, `parameter.yml` et la clé `parameter`.
- [x] Nom du workspace PPR confirmé (31/10/2026).
- [x] Nom du workspace PRD confirmé (31/10/2026) ; tiret simple à vérifier au premier pré-vol PRD.
- [ ] Remplacer les marqueurs de `CD.yml` et `PR-Validation.yml`.
- [ ] Créer les pipelines ADO de CD et de validation de PR ; déclarer PR-Validation comme check obligatoire.
- [ ] Vérifier le point V-01 (contenu de l'artefact CI) au premier run.
- [ ] Faire passer `deploy.py validate` sans erreur, puis passer `inventory_status` à `validated` dans une PR revue.
- [ ] Désactiver l'ancienne CD UCS (groupe `Fabric-CD-Secrets`) une fois la nouvelle CD opérationnelle.
