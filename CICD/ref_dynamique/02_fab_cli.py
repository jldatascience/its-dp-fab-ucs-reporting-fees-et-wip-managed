"""Étape 2 — INVENTAIRE FABRIC du workspace UCS Reporting Fees & WIP via Fabric CLI (lecture seule).

Pour UN environnement (--env, ITG par défaut) :
  - vérifie l'authentification Fabric CLI (fab auth status) ;
  - retrouve le workspace UCS par son nom EXACT (ou par son ID avec --workspace-id) ;
  - relève ses items (type, nom, ID), les connexions et les gateways visibles ;
  - lit la définition de ses DataPipeline (getDefinition) et relève les activités
    InvokePipeline / TridentNotebook, en signalant celles qui visent un AUTRE workspace
    (référence croisée).

Nom du workspace, par ordre de priorité : --workspace, puis core.workspace.<ENV> de
CICD/deployment/config.yml s'il n'est pas un marqueur __A_RELEVER__ (les 4 noms y sont
renseignés, ex. « FR - DP - ITG - FAB - UCS - Reporting Fees & WIP - Managed »).
Aucun workspace Framework ou MDS n'est utilisé.
Les ID des workspaces UCS ITG/PPR/PRD de l'ancienne CD figurent dans le registre du socle
(CICD/registry/known_guids.yml) : --workspace-id permet d'en relever le nom exact.

Pré-requis : pip install ms-fabric-cli ; fab auth login
Sorties (HORS du dépôt, voir --out) : fabric_<ENV>.json, activites_fabric_<ENV>.csv
Usage :
    python 02_fab_cli.py                       # ITG
    python 02_fab_cli.py --env PPR --workspace-id <id relevé dans le registre du socle>
    python 02_fab_cli.py --env DEV             # workspace DEV UCS, source des GUID des items
Aucune écriture dans Fabric : uniquement des GET et des getDefinition (POST en lecture).
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_NAME = "its-dp-fab-ucs-reporting-fees-et-wip-managed"
ENVIRONMENTS = ("DEV", "ITG", "PPR", "PRD")
PLACEHOLDER_MARK = "__A_RELEVER__"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_FILE = REPO_ROOT / "CICD" / "deployment" / "config.yml"
REF_TYPES = {"InvokePipeline": "pipelineId", "TridentNotebook": "notebookId"}
NESTED_KEYS = ("activities", "ifTrueActivities", "ifFalseActivities", "defaultActivities")


def dossier_sortie(arg: str | None) -> Path:
    brut = arg or os.environ.get("REF_DYN_OUT") or str(Path(tempfile.gettempdir()) / "ref_dynamique" / REPO_NAME)
    out = Path(brut).expanduser().resolve()
    try:
        out.relative_to(REPO_ROOT.resolve())
    except ValueError:
        out.mkdir(parents=True, exist_ok=True)
        return out
    sys.exit(f"Dossier de sortie {out} situé DANS le dépôt : refusé (choisir --out hors du dépôt).")


def nom_config(env: str) -> str | None:
    """core.workspace.<ENV> de config.yml, sauf marqueur à relever."""
    if not CONFIG_FILE.is_file():
        return None
    texte = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        import yaml
        valeur = (((yaml.safe_load(texte) or {}).get("core") or {}).get("workspace") or {}).get(env)
    except ImportError:
        m = re.search(rf'^\s+{env}:\s*"([^"]+)"', texte, re.M)
        valeur = m.group(1) if m else None
    return None if not valeur or PLACEHOLDER_MARK in str(valeur) else str(valeur)


# --------------------------------------------------------------------------- Fabric CLI
def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["fab", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit("Fabric CLI introuvable : pip install ms-fabric-cli, puis `fab auth login`.")


def verifier_auth() -> None:
    r = _run(["auth", "status"])
    if r.returncode != 0:
        sys.exit(f"Fabric CLI non authentifiée (`fab auth status` : {(r.stderr or r.stdout).strip()[:300]}). "
                 "Lancer `fab auth login`.")


def _body(stdout: str, ctx: str):
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        sys.exit(f"Sortie `fab api {ctx}` non JSON (adapter à la version de fab) :\n{stdout[:400]}")
    if isinstance(data, dict) and isinstance(data.get("text"), (dict, list)):
        data = data["text"]
    return data


def fab_get(endpoint: str):
    r = _run(["api", "-X", "get", endpoint])
    if r.returncode != 0:
        raise RuntimeError(f"`fab api get {endpoint}` : {(r.stderr or r.stdout).strip()[:300]}")
    d = _body(r.stdout, endpoint)
    return d.get("value", d) if isinstance(d, dict) else d


def fab_post(endpoint: str):
    r = _run(["api", "-X", "post", endpoint])
    return r.returncode, (_body(r.stdout, endpoint) if r.stdout.strip() else {})


# --------------------------------------------------------------------------- inventaire
def parcourir(acts, pipeline: str, chemin: str, out: list[dict]) -> None:
    for a in acts or []:
        if not isinstance(a, dict):
            continue
        tp = a.get("typeProperties") or {}
        filtre = f'{chemin}[?(@.name=="{a.get("name")}")]'
        if a.get("type") in REF_TYPES:
            prop = REF_TYPES[a["type"]]
            connexion = None
            for v in (a.get("externalReferences") or tp.get("externalReferences") or {}).values():
                connexion = v if isinstance(v, str) else connexion
            out.append({"pipeline": pipeline, "activite": a.get("name"), "type": a.get("type"), "chemin": filtre,
                        "workspaceId": tp.get("workspaceId"), "propriete_cible": prop, "cibleId": tp.get(prop),
                        "connexion": connexion})
        for key in NESTED_KEYS:
            if isinstance(tp.get(key), list):
                parcourir(tp[key], pipeline, f"{filtre}.typeProperties.{key}", out)
        for i, case in enumerate(tp.get("cases") or []):
            if isinstance(case, dict):
                parcourir(case.get("activities"), pipeline, f"{filtre}.typeProperties.cases[{i}].activities", out)


def activites(ws_id: str, items: list[dict]) -> tuple[list[dict], list[str]]:
    out, indisponibles = [], []
    for it in items:
        if it.get("type") != "DataPipeline":
            continue
        _, body = fab_post(f"workspaces/{ws_id}/items/{it['id']}/getDefinition")
        parts = ((body or {}).get("definition") or {}).get("parts") or []
        if not parts:
            indisponibles.append(it["displayName"])  # 202 (opération longue) ou droits insuffisants
            continue
        for part in parts:
            if part.get("path", "").endswith("pipeline-content.json"):
                try:
                    doc = json.loads(base64.b64decode(part["payload"]).decode("utf-8"))
                except (ValueError, KeyError):
                    continue
                parcourir((doc.get("properties") or {}).get("activities"), it["displayName"],
                          "$.properties.activities", out)
    return out, indisponibles


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--env", default="ITG", choices=ENVIRONMENTS, help="environnement inventorié (défaut : ITG)")
    p.add_argument("--workspace", help="nom exact du workspace (prioritaire sur config.yml)")
    p.add_argument("--workspace-id", help="ID du workspace : le nom est relevé dans Fabric")
    p.add_argument("--out", help="dossier de sortie hors dépôt (défaut : dossier temporaire système)")
    p.add_argument("--sans-definitions", action="store_true", help="ne pas lire les définitions des pipelines")
    args = p.parse_args()

    out = dossier_sortie(args.out)
    verifier_auth()
    try:
        tous = fab_get("workspaces")
    except RuntimeError as exc:
        sys.exit(str(exc))
    noms_ws = {w.get("id"): w.get("displayName") for w in tous}

    if args.workspace_id:
        ws_id = args.workspace_id
        if ws_id not in noms_ws:
            sys.exit(f"Workspace {ws_id} absent de la liste visible par ce compte (ID ? droits ?).")
        ws_nom = noms_ws[ws_id]
    else:
        ws_nom = args.workspace or nom_config(args.env)
        if not ws_nom:
            sys.exit(f"{args.env} : nom du workspace UCS inconnu (marqueur __A_RELEVER__ dans config.yml). "
                     "Passer --workspace \"<nom exact>\" ou --workspace-id <id>.")
        ws_id = next((i for i, n in noms_ws.items() if (n or "").strip() == ws_nom.strip()), None)
        if not ws_id:
            sys.exit(f"Workspace introuvable (nom exact ? droits ?) : {ws_nom!r}")
    if "UCS" not in (ws_nom or "").upper():
        print(f"ATTENTION : « {ws_nom} » ne ressemble pas à un workspace UCS.", file=sys.stderr)

    try:
        items = fab_get(f"workspaces/{ws_id}/items")
    except RuntimeError as exc:
        sys.exit(str(exc))
    try:
        conns = [{"id": c.get("id"), "displayName": c.get("displayName"),
                  "connectivityType": c.get("connectivityType")} for c in fab_get("connections")]
    except RuntimeError as exc:
        print(f"   connexions non lues : {exc}", file=sys.stderr)
        conns = []
    try:
        gws = [{"id": g.get("id"), "displayName": g.get("displayName"), "type": g.get("type")}
               for g in fab_get("gateways")]
    except RuntimeError as exc:
        print(f"   gateways non lues : {exc}", file=sys.stderr)
        gws = []

    acts, indispo = ([], []) if args.sans_definitions else activites(ws_id, items)
    ids_items = {it["id"] for it in items}
    for a in acts:
        autre = a.get("workspaceId") and a["workspaceId"] != ws_id
        a["portee"] = "inter-workspace" if autre else ("workspace courant" if a.get("cibleId") in ids_items else "cible inconnue")
        a["workspace_cible"] = noms_ws.get(a.get("workspaceId"), "") if autre else ws_nom

    env = args.env
    (out / f"fabric_{env}.json").write_text(json.dumps({
        "depot": REPO_NAME, "env": env,
        "workspace": {"nom": ws_nom, "id": ws_id},
        "items": [{"type": it.get("type"), "nom": it.get("displayName"), "id": it.get("id")} for it in items],
        "connexions": conns, "gateways": gws,
        "definitions_indisponibles": indispo,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out / f"activites_fabric_{env}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        cols = ["pipeline", "activite", "type", "chemin", "workspaceId", "workspace_cible", "portee",
                "propriete_cible", "cibleId", "connexion"]
        w.writerow(cols)
        for a in acts:
            w.writerow([a.get(c) for c in cols])

    croisees = sum(1 for a in acts if a["portee"] == "inter-workspace")
    print(f"[{env}] {ws_nom} = {ws_id} | {len(items)} items | {len(acts)} activités ({croisees} inter-workspace) "
          f"| connexions={len(conns)} gateways={len(gws)}")
    if indispo:
        print(f"   définition indisponible pour {len(indispo)} pipeline(s) (getDefinition 202/droits) : {', '.join(indispo)}")
    print(f"   -> {out}")


if __name__ == "__main__":
    main()
