#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
    echo "Uso: $0 <db_name> <model_name> <output_dir> [config_path]"
    echo "Ejemplo: $0 mydb_v18 res.partner ./tmp/import_maps debian/odoo.conf"
  exit 1
fi

DB_NAME="$1"
MODEL_NAME="$2"
OUTPUT_DIR="$3"
CONFIG_PATH="${4:-debian/odoo.conf}"

mkdir -p "$OUTPUT_DIR"

if [[ ! -d .venv ]]; then
  echo "No existe .venv en el directorio actual. Ejecuta este script desde /home/pablo/odoo"
  exit 1
fi

source .venv/bin/activate

export MODEL_NAME
export OUTPUT_DIR

./odoo-bin shell -c "$CONFIG_PATH" -d "$DB_NAME" <<'PY'
import csv
import os

model_name = os.environ["MODEL_NAME"]
out_dir = os.environ["OUTPUT_DIR"]
os.makedirs(out_dir, exist_ok=True)
model_safe = model_name.replace('.', '_')

model = env[model_name]
fields = model.fields_get()

main_records = model.search([])
main_xmlids = {rec_id: xmlid for rec_id, xmlid in main_records.get_external_id().items()}
master_csv = os.path.join(out_dir, f"{model_safe}_import_master_map.csv")
with open(master_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "row_type",
        "model",
        "field",
        "field_label",
        "field_type",
        "required",
        "readonly",
        "related_model",
        "id",
        "xml_id",
        "display_name",
    ])

    # 1) Definición de campos importables (para saber nombres técnicos)
    for fname in sorted(fields):
        fdef = fields[fname]
        w.writerow([
            "FIELD",
            model_name,
            fname,
            fdef.get("string", ""),
            fdef.get("type", ""),
            bool(fdef.get("required", False)),
            bool(fdef.get("readonly", False)),
            fdef.get("relation", ""),
            "",
            "",
            "",
        ])

    # 2) Registros del modelo principal + xml_id
    for rec in main_records:
        w.writerow([
            "MAIN_RECORD",
            model_name,
            "",
            "",
            "",
            "",
            "",
            "",
            rec.id,
            main_xmlids.get(rec.id, ""),
            rec.display_name,
        ])

    # 3) Para cada campo relacional, equivalencias id -> xml_id
    rel_fields = []
    for fname, fdef in fields.items():
        if fdef.get("type") in ("many2one", "many2many") and fdef.get("relation"):
            rel_fields.append((fname, fdef["relation"]))

    for fname, rel_model_name in sorted(rel_fields):
        rel_ids = set(main_records.mapped(fname).ids)
        if not rel_ids:
            continue

        rel_model = env[rel_model_name]
        rel_recs = rel_model.browse(list(rel_ids)).exists()
        rel_xmlids = {rec_id: xmlid for rec_id, xmlid in rel_recs.get_external_id().items()}

        for rec in rel_recs:
            w.writerow([
                "RELATION_VALUE",
                model_name,
                fname,
                "",
                "",
                "",
                "",
                rel_model_name,
                rec.id,
                rel_xmlids.get(rec.id, ""),
                rec.display_name,
            ])

print(f"OK: generado archivo maestro para importación de {model_name}")
print(f" - Archivo: {master_csv}")
print(" - Usa filas RELATION_VALUE para convertir IDs de relaciones a campo/id con xml_id")
PY
