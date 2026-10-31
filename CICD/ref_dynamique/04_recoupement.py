"""Étape 4 — RECOUPEMENT Git × Fabric × parameter.yml du dépôt UCS Reporting Fees & WIP.

Compare :
  - l'inventaire Git (01 : inventaire_ucs.json) ;
  - le ou les inventaires Fabric (02 : fabric_<ENV>.json, ITG en priorité) ;
  - les règles key_value_replace de CICD/deployment/parameter.yml (ou --parameter) ;
et classe chaque constat :
  COUVERTE              référence d'activité (workspaceId / pipelineId / notebookId) couverte par une règle ;
  NON_COUVERTE          GUID d'activité sans règle : il resterait pointé sur l'environnement source ;
  GUID_INCONNU          GUID du dépôt absent des inventaires Fabric et du registre du socle ;
  REGLE_INUTILE         règle sans activité correspondante dans le dépôt (sans effet) ;
  REFERENCE_OBSOLETE    règle vers un item absent du dépôt, ou ID appelé absent de Fabric ;
  INCOHERENCE_WORKSPACE référence vers un autre workspace (interdite au déploiement pour UCS, R5) ;
  INCOHERENCE_TYPE      item_type de la règle ou type de l'item appelé incohérent.

Sorties (HORS du dépôt) : recoupement_ucs.csv, rapport_recoupement_ucs.md
Usage : python 04_recoupement.py [--out <dossier>] [--parameter <parameter.yml>]
Code retour : 0 = aucun constat bloquant ; 1 = constats bloquants ; 2 = entrée manquante.
Pré-requis : PyYAML (présent dans l'environnement du socle : pip install pyyaml).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO_NAME = "its-dp-fab-ucs-reporting-fees-et-wip-managed"
LABEL = "ucs"
ENVIRONMENTS = ("DEV", "ITG", "PPR", "PRD")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PARAMETER = REPO_ROOT / "CICD" / "deployment" / "parameter.yml"
GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
ITEM_VAR = re.compile(r"^\$items\.([^.]+)\.(.+)\.\$id$")
TYPE_ATTENDU = {"pipelineId": "DataPipeline", "notebookId": "Notebook"}
BLOQUANTS = {"NON_COUVERTE", "REGLE_INUTILE", "REFERENCE_OBSOLETE", "INCOHERENCE_WORKSPACE", "INCOHERENCE_TYPE"}
ORDRE = ["COUVERTE", "NON_COUVERTE", "GUID_INCONNU", "REGLE_INUTILE", "REFERENCE_OBSOLETE",
         "INCOHERENCE_WORKSPACE", "INCOHERENCE_TYPE"]


def dossier_sortie(arg: str | None) -> Path:
    brut = arg or os.environ.get("REF_DYN_OUT") or str(Path(tempfile.gettempdir()) / "ref_dynamique" / REPO_NAME)
    out = Path(brut).expanduser().resolve()
    try:
        out.relative_to(REPO_ROOT.resolve())
    except ValueError:
        out.mkdir(parents=True, exist_ok=True)
        return out
    sys.exit(f"Dossier de sortie {out} situé DANS le dépôt : refusé (choisir --out hors du dépôt).")


def lire_regles(chemin: Path) -> list[dict]:
    try:
        import yaml
    except ImportError:
        print("PyYAML requis : pip install pyyaml", file=sys.stderr)
        sys.exit(2)
    if not chemin.is_file():
        print(f"{chemin} introuvable.", file=sys.stderr)
        sys.exit(2)
    data = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    regles = []
    for r in data.get("key_value_replace") or []:
        fk = str(r.get("find_key", ""))
        noms = re.findall(r'@\.name\s*==\s*"([^"]+)"', fk)
        # chemin de l'activité = find_key sans la dernière propriété (.typeProperties.<prop>)
        m = re.match(r"^(.*)\.typeProperties\.([A-Za-z]+)$", fk)
        regles.append({"find_key": fk, "item_type": r.get("item_type"), "item_name": r.get("item_name"),
                       "activite": noms[-1] if noms else None, "chemin": m.group(1) if m else None,
                       "propriete": m.group(2) if m else fk.rsplit(".", 1)[-1],
                       "valeurs": r.get("replace_value") or {}})
    return regles


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", help="dossier des sorties 01/02 (hors dépôt)")
    p.add_argument("--parameter", default=str(PARAMETER), help="parameter.yml à recouper (défaut : CICD/deployment)")
    args = p.parse_args()
    out = dossier_sortie(args.out)

    inv_path = out / f"inventaire_{LABEL}.json"
    if not inv_path.is_file():
        print(f"{inv_path} manquant : lancer d'abord 01_inventaire_github.py.", file=sys.stderr)
        sys.exit(2)
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    fabric = {env: json.loads((out / f"fabric_{env}.json").read_text(encoding="utf-8"))
              for env in ENVIRONMENTS if (out / f"fabric_{env}.json").is_file()}
    regles = lire_regles(Path(args.parameter).expanduser())

    git_types = {}
    for it in inv.get("items", []):
        git_types.setdefault(it["nom"], set()).add(it["type"])
    ws_ucs = {d["workspace"]["id"]: env for env, d in fabric.items()}
    ids_fabric = {it["id"]: (it["type"], it["nom"], env) for env, d in fabric.items() for it in d.get("items", [])}
    ids_connus = set(ids_fabric) | set(ws_ucs) | {c["id"] for d in fabric.values() for c in d.get("connexions", []) if c.get("id")}

    constats: list[list[str]] = []

    def ajouter(cat, item="", activite="", prop="", guid="", detail=""):
        constats.append([cat, item or "", activite or "", prop or "", guid or "", detail])

    # 1) Règles : effet, cible, workspace, type.
    for r in regles:
        lieu = f"{r['item_type']} {r['item_name']} / {r['find_key']}"
        types_appelant = git_types.get(r["item_name"])
        if not types_appelant:
            ajouter("REFERENCE_OBSOLETE", r["item_name"], r["activite"], r["propriete"], "",
                    f"item appelant absent du dépôt ({lieu})")
        elif r["item_type"] not in types_appelant:
            ajouter("INCOHERENCE_TYPE", r["item_name"], r["activite"], r["propriete"], "",
                    f"item_type {r['item_type']} ≠ type Git {', '.join(sorted(types_appelant))}")
        acts = [a for a in inv.get("activites_ref", [])
                if a["item"] == r["item_name"] and (a["chemin"] == r["chemin"] or a["activite"] == r["activite"])]
        if types_appelant and not acts:
            ajouter("REGLE_INUTILE", r["item_name"], r["activite"], r["propriete"], "",
                    "aucune activité correspondante dans le dépôt : règle sans effet")
        for env_cle, valeur in r["valeurs"].items():
            v = str(valeur)
            if GUID.match(v):
                ajouter("INCOHERENCE_WORKSPACE", r["item_name"], r["activite"], r["propriete"], v,
                        f"{env_cle} : GUID littéral (RULE_LITERAL_GUID)")
            elif v.startswith("$workspace.") and v != "$workspace.$id":
                ajouter("INCOHERENCE_WORKSPACE", r["item_name"], r["activite"], r["propriete"], "",
                        f"{env_cle} : {v} — référence inter-workspace interdite pour UCS (R5)")
            elif r["propriete"] == "workspaceId" and v != "$workspace.$id":
                ajouter("INCOHERENCE_WORKSPACE", r["item_name"], r["activite"], r["propriete"], "",
                        f"{env_cle} : workspaceId doit valoir $workspace.$id (trouvé {v})")
            m = ITEM_VAR.match(v)
            if m:
                ctype, cnom = m.group(1), m.group(2)
                attendu = TYPE_ATTENDU.get(r["propriete"])
                if attendu and ctype != attendu:
                    ajouter("INCOHERENCE_TYPE", r["item_name"], r["activite"], r["propriete"], "",
                            f"{r['propriete']} attend un {attendu}, la règle vise {ctype} {cnom}")
                if ctype not in git_types.get(cnom, set()):
                    detail = (f"{cnom} existe sous un autre type ({', '.join(sorted(git_types[cnom]))})"
                              if cnom in git_types else f"item appelé {ctype} {cnom} absent du dépôt")
                    ajouter("INCOHERENCE_TYPE" if cnom in git_types else "REFERENCE_OBSOLETE",
                            r["item_name"], r["activite"], r["propriete"], "", detail)

    # 2) Références d'activités du dépôt : couverture et cohérence avec Fabric.
    for a in inv.get("activites_ref", []):
        for prop in ("workspaceId", a["propriete_cible"]):
            guid = a.get("workspaceId") if prop == "workspaceId" else a.get("cibleId")
            if not guid:
                continue
            couverte = any(r["item_name"] == a["item"] and r["propriete"] == prop
                           and (r["chemin"] == a["chemin"] or r["activite"] == a["activite"]) for r in regles)
            ajouter("COUVERTE" if couverte else "NON_COUVERTE", a["item"], a["activite"], prop, guid,
                    "" if couverte else "aucune règle parameter.yml")
        hors_ucs = bool(a.get("workspaceId")) and a["workspaceId"] not in ws_ucs
        if fabric and a.get("cibleId") and not (hors_ucs and a["cibleId"] not in ids_fabric):
            cible = ids_fabric.get(a["cibleId"])
            if not cible:
                ajouter("REFERENCE_OBSOLETE", a["item"], a["activite"], a["propriete_cible"], a["cibleId"],
                        f"ID appelé introuvable dans les inventaires Fabric ({', '.join(fabric)})")
            else:
                ws_cible = fabric[cible[2]]["workspace"]["id"]
                if a.get("workspaceId") and a["workspaceId"] != ws_cible:
                    ajouter("INCOHERENCE_WORKSPACE", a["item"], a["activite"], "workspaceId", a["workspaceId"],
                            f"workspaceId ≠ workspace de l'item appelé ({cible[1]}, {cible[2]})")
                if cible[0] != TYPE_ATTENDU.get(a["propriete_cible"]):
                    ajouter("INCOHERENCE_TYPE", a["item"], a["activite"], a["propriete_cible"], a["cibleId"],
                            f"{a['propriete_cible']} pointe vers un {cible[0]} ({cible[1]})")
        if fabric and hors_ucs and a.get("cibleId") not in ids_fabric:
            ajouter("INCOHERENCE_WORKSPACE", a["item"], a["activite"], "workspaceId", a["workspaceId"],
                    "workspace non UCS : référence croisée, à résoudre à l'exécution (R5, data_dependencies)")

    # 3) GUID du dépôt inconnus de Fabric et du registre du socle.
    vus = set()
    for ref in inv.get("toutes_refs_guid", []):
        g = ref["guid"].lower()
        if g in vus:
            continue
        vus.add(g)
        if g not in {i.lower() for i in ids_connus} and ref.get("classe", "non classé") == "non classé":
            ajouter("GUID_INCONNU", ref["item"], "", ref["cle"], ref["guid"], f"{ref['fichier']}")

    with open(out / f"recoupement_{LABEL}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["categorie", "item", "activite", "propriete", "guid", "detail"])
        w.writerows(sorted(constats, key=lambda c: (ORDRE.index(c[0]), c[1], c[2], c[3])))
    total = Counter(c[0] for c in constats)
    sources = ", ".join(f"{e} ({d['workspace']['nom']})" for e, d in fabric.items()) or "aucun"
    lignes = [f"# Recoupement {REPO_NAME}", "",
              f"- Inventaire Git : `{inv.get('branche')}` @ `{str(inv.get('commit', ''))[:8]}` — "
              f"{len(inv.get('items', []))} items, {len(inv.get('activites_ref', []))} activités",
              f"- Inventaires Fabric : {sources}",
              f"- parameter.yml : `{args.parameter}` — {len(regles)} règle(s)", "",
              "| Catégorie | Nombre | Bloquant |", "|---|---|---|"]
    lignes += [f"| {c} | {total.get(c, 0)} | {'oui' if c in BLOQUANTS else 'non'} |" for c in ORDRE]
    if not inv.get("items"):
        lignes += ["", "Aucun item Fabric dans le dépôt : rien à recouper."]
    (out / f"rapport_recoupement_{LABEL}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")

    print(f"[{LABEL}] {len(regles)} règles | " + " | ".join(f"{c}={total.get(c, 0)}" for c in ORDRE))
    print(f"          -> {out / f'recoupement_{LABEL}.csv'} , rapport_recoupement_{LABEL}.md")
    bloquants = sum(total.get(c, 0) for c in BLOQUANTS)
    if bloquants:
        print(f"{bloquants} constat(s) bloquant(s) à traiter avant de passer inventory_status à validated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
