#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Importador Dynamics -> Odoo (solo res.partner)

- scripts/accounts.csv: GUID = accountid  -> res.partner (empresa)
- scripts/contacts.csv: GUID = contactid  -> res.partner (contacto)
  y relación con empresa: contel_cuenta (GUID de account)

- Guarda TODO el row original en res.partner.comment como JSON (payload completo)
- Mantiene mapping DynamicsGUID->OdooID en SQLite para resolver parent_id

Notas de robustez:
- IBAN: Odoo valida IBAN en res.partner.bank. Este script SOLO crea bank accounts si el valor "parece" IBAN.
  Alternativamente puedes saltar bancos con --skip-bank-accounts.
- SEPA firmado: tu módulo valida que si billing_sepa_signed=True debe haber documento. Como este script no adjunta
  documentos, NO marcará billing_sepa_signed si no se puede cumplir. Se deja warning y la info queda en comment.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from xmlrpc import client as xmlrpclib


def norm_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def norm_email(v: Any) -> str:
    return norm_str(v).lower()


def norm_bool(v: Any) -> bool:
    """
    Dynamics suele traer booleanos como:
    - "" (vacío) => False
    - "True"/"False"
    - "1"/"0"
    - "si"/"no"
    """
    if v is None:
        return False
    s = str(v).strip().lower()
    if s in ("", "0", "false", "no", "n", "off", "none", "null"):
        return False
    if s in ("1", "true", "yes", "y", "on", "si", "sí", "s"):
        return True
    return True


def norm_selection_yes_no(v: Any) -> Optional[str]:
    """
    Para selections tipo 'no'/'si' (o parecido).
    Devuelve 'no' o 'si', o None si no hay valor.
    """
    if v is None:
        return None
    s = str(v).strip().lower()
    if s == "":
        return None
    if s in ("0", "false", "no", "n"):
        return "no"
    if s in ("1", "true", "si", "sí", "s", "yes", "y"):
        return "si"
    return None


def norm_iban(v: Any) -> str:
    s = norm_str(v)
    s = s.replace(" ", "").replace("-", "")
    return s


_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{8,30}$")


def looks_like_iban(v: Any) -> bool:
    s = norm_iban(v).upper()
    return bool(_IBAN_RE.match(s))


def read_csv_rows(path: str) -> Iterable[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=",", quotechar='"')
        for row in r:
            yield row


@dataclass
class OdooConn:
    url: str
    db: str
    user: str
    password: str

    def __post_init__(self) -> None:
        common = xmlrpclib.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.user, self.password, {})
        if not uid:
            raise RuntimeError("Odoo authentication failed")
        self.uid = uid
        self.models = xmlrpclib.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def search(self, model: str, domain: List, limit: int = 0) -> List[int]:
        kwargs = {}
        if limit:
            kwargs["limit"] = limit
        return self.models.execute_kw(self.db, self.uid, self.password, model, "search", [domain], kwargs)

    def create(self, model: str, vals: Dict[str, Any]) -> int:
        return self.models.execute_kw(self.db, self.uid, self.password, model, "create", [vals])

    def write(self, model: str, ids: List[int], vals: Dict[str, Any]) -> bool:
        return self.models.execute_kw(self.db, self.uid, self.password, model, "write", [ids, vals])

    def search_read(self, model: str, domain: List, fields: List[str], limit: int = 0) -> List[Dict[str, Any]]:
        kwargs = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        return self.models.execute_kw(self.db, self.uid, self.password, model, "search_read", [domain], kwargs)


class MappingDB:
    def __init__(self, path: str) -> None:
        self.path = path
        self.con = sqlite3.connect(self.path)
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS mapping (
              entity TEXT NOT NULL,
              dynamics_id TEXT NOT NULL,
              odoo_model TEXT NOT NULL,
              odoo_id INTEGER NOT NULL,
              PRIMARY KEY (entity, dynamics_id)
            )
            """
        )
        self.con.commit()

    def get(self, entity: str, dynamics_id: str) -> Optional[int]:
        cur = self.con.execute(
            "SELECT odoo_id FROM mapping WHERE entity=? AND dynamics_id=?",
            (entity, dynamics_id),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None

    def set(self, entity: str, dynamics_id: str, odoo_model: str, odoo_id: int) -> None:
        self.con.execute(
            """
            INSERT INTO mapping(entity, dynamics_id, odoo_model, odoo_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity, dynamics_id) DO UPDATE SET
              odoo_model=excluded.odoo_model,
              odoo_id=excluded.odoo_id
            """,
            (entity, dynamics_id, odoo_model, int(odoo_id)),
        )
        self.con.commit()


def build_payload_comment(row: Dict[str, str]) -> str:
    return "<p>" + json.dumps(row, ensure_ascii=False) + "</p>"


def _country_state_from_row(row: Dict[str, str], conn: OdooConn) -> Tuple[Optional[int], Optional[int]]:
    country_name = norm_str(row.get("address1_country")) or norm_str(row.get("address2_country"))
    country_id: Optional[int] = None
    if country_name:
        found = conn.search("res.country", [("name", "ilike", country_name)], limit=1)
        if found:
            country_id = found[0]

    state_name = norm_str(row.get("address1_stateorprovince")) or norm_str(row.get("address2_stateorprovince"))
    state_id: Optional[int] = None
    if state_name and country_id:
        found = conn.search("res.country.state", [("name", "ilike", state_name), ("country_id", "=", country_id)], limit=1)
        if found:
            state_id = found[0]

    return country_id, state_id


def build_partner_vals_from_account(row: Dict[str, str], conn: OdooConn) -> Dict[str, Any]:
    name = norm_str(row.get("name"))
    vat = norm_str(row.get("new_cif"))
    email = norm_email(row.get("contel_correocontacto") or row.get("emailaddress1"))
    phone = norm_str(row.get("telephone1") or row.get("contel_telefonoempresa"))
    mobile = norm_str(row.get("contel_telefonocontacto") or row.get("telephone2") or row.get("telephone3"))

    street = norm_str(row.get("address1_line1"))
    street2 = norm_str(row.get("address1_line2") or row.get("address1_line3"))
    city = norm_str(row.get("address1_city"))
    zip_code = norm_str(row.get("address1_postalcode"))

    country_id, state_id = _country_state_from_row(row, conn)

    vals: Dict[str, Any] = {
        "name": name or "(sin nombre)",
        "vat": vat or False,
        "is_company": True,
        "company_type": "company",
        "comment": build_payload_comment(row),
    }

    if email:
        vals["email"] = email
    if phone:
        vals["phone"] = phone
    if mobile:
        vals["mobile"] = mobile

    if street:
        vals["street"] = street
    if street2:
        vals["street2"] = street2
    if city:
        vals["city"] = city
    if zip_code:
        vals["zip"] = zip_code
    if country_id:
        vals["country_id"] = country_id
    if state_id:
        vals["state_id"] = state_id

    # ===== Facturación =====
    vals["billing_prepago"] = norm_bool(row.get("contel_clienteprepago"))
    vals["lopd_signed"] = norm_bool(row.get("contel_lopdfirmada"))

    billing_email = norm_email(row.get("contel_emailfacturacion"))
    if billing_email:
        vals["billing_invoice_email"] = billing_email

    inc = norm_selection_yes_no(row.get("contel_incidenciascobro"))
    if inc:
        vals["billing_incidents_cobro"] = inc

    pm_raw = norm_str(row.get("contel_formadepago"))
    pm = pm_raw.lower()
    if pm:
        if pm in ("contado", "cash"):
            vals["billing_payment_method"] = "contado"
        else:
            # No forzamos selections desconocidas: lo guardamos en el custom
            vals["billing_payment_method_custom"] = pm_raw

    # SEPA firmado: tu Odoo exige documento adjunto. Como aquí no importamos documentos,
    # NO marcamos firmado aunque venga True en Dynamics (dejamos warning).
    dyn_sepa_signed = norm_bool(row.get("contel_sepafirmado"))
    dyn_sepa_doc = norm_str(row.get("contel_documentosepa"))
    if dyn_sepa_signed:
        if dyn_sepa_doc:
            # Aún así, no sabemos convertir dyn_sepa_doc a billing_sepa_document_id (Many2one),
            # así que para evitar fallo dejamos False y avisamos.
            print(
                "[WARN] Dynamics indica SEPA firmado con contel_documentosepa no vacío, "
                "pero no se puede adjuntar automáticamente: se deja billing_sepa_signed=False. "
                f"accountid={norm_str(row.get('accountid'))}"
            )
        else:
            print(f"[WARN] SEPA firmado en Dynamics pero sin documento. No se marca en Odoo. accountid={norm_str(row.get('accountid'))}")
        vals["billing_sepa_signed"] = False
    else:
        vals["billing_sepa_signed"] = False

    # ===== Contratos =====
    vals["contract_acronis"] = norm_bool(row.get("contel_acronis"))
    vals["contract_antivirus"] = norm_bool(row.get("contel_antivirus"))
    vals["contract_cloud_centralita"] = norm_bool(row.get("contel_mantenimientocentralitacloud"))
    vals["contract_physical_centralita"] = norm_bool(row.get("contel_mantenimientocentralitafisica"))
    vals["contract_total_it_maintenance"] = norm_bool(row.get("contel_mantenimientototalinformatica"))
    vals["contract_it_bonus"] = norm_bool(row.get("contel_mantenimientoinformatica"))
    vals["contract_vpn"] = norm_bool(row.get("contel_mantenimientovpn"))
    vals["contract_office365"] = norm_bool(row.get("contel_office365"))
    vals["contract_incidents_cobro"] = norm_bool(row.get("contel_incidenciascobro"))

    return vals


def build_partner_vals_from_contact(row: Dict[str, str], conn: OdooConn) -> Dict[str, Any]:
    first = norm_str(row.get("firstname"))
    last = norm_str(row.get("lastname"))
    full = norm_str(row.get("fullname"))
    name = full or " ".join([p for p in [first, last] if p]).strip()

    email = norm_email(row.get("emailaddress1"))
    phone = norm_str(row.get("telephone1"))
    mobile = norm_str(row.get("mobilephone"))

    street = norm_str(row.get("address1_line1"))
    street2 = norm_str(row.get("address1_line2") or row.get("address1_line3"))
    city = norm_str(row.get("address1_city"))
    zip_code = norm_str(row.get("address1_postalcode"))

    country_id, state_id = _country_state_from_row(row, conn)

    vals: Dict[str, Any] = {
        "name": name or "(sin nombre)",
        "is_company": False,
        "company_type": "person",
        "comment": build_payload_comment(row),
    }

    if email:
        vals["email"] = email
    if phone:
        vals["phone"] = phone
    if mobile:
        vals["mobile"] = mobile

    if street:
        vals["street"] = street
    if street2:
        vals["street2"] = street2
    if city:
        vals["city"] = city
    if zip_code:
        vals["zip"] = zip_code
    if country_id:
        vals["country_id"] = country_id
    if state_id:
        vals["state_id"] = state_id

    return vals


def upsert_partner(conn: OdooConn, mapping: MappingDB, entity: str, dynamics_id: str, vals: Dict[str, Any], dry_run: bool) -> int:
    mapped_id = mapping.get(entity, dynamics_id)
    if mapped_id:
        if dry_run:
            print(f"[DRY] UPDATE res.partner id={mapped_id} entity={entity} dynamics_id={dynamics_id}")
            return mapped_id
        conn.write("res.partner", [mapped_id], vals)
        return mapped_id

    # heurística: link por email SOLO para accounts
    email = vals.get("email")
    if entity == "account" and email:
        found = conn.search("res.partner", [("email", "=", email)], limit=1)
        if found:
            pid = found[0]
            if dry_run:
                print(f"[DRY] LINK existing res.partner id={pid} by email={email} entity={entity} dynamics_id={dynamics_id}")
                return pid
            conn.write("res.partner", [pid], vals)
            mapping.set(entity, dynamics_id, "res.partner", pid)
            return pid

    if dry_run:
        print(f"[DRY] CREATE res.partner entity={entity} dynamics_id={dynamics_id} name={vals.get('name')!r}")
        return -1

    pid = conn.create("res.partner", vals)
    mapping.set(entity, dynamics_id, "res.partner", pid)
    return pid


def upsert_partner_bank_account(conn: OdooConn, partner_id: int, iban: str, dry_run: bool) -> None:
    iban_norm = norm_iban(iban).upper()
    if not iban_norm:
        return

    if not looks_like_iban(iban_norm):
        print(f"[WARN] Skip invalid IBAN partner_id={partner_id} iban={iban_norm!r}")
        return

    existing = conn.search("res.partner.bank", [("partner_id", "=", partner_id), ("acc_number", "=", iban_norm)], limit=1)
    if existing:
        return

    vals = {"partner_id": partner_id, "acc_number": iban_norm, "active": True}
    if dry_run:
        print(f"[DRY] CREATE res.partner.bank partner_id={partner_id} acc_number={iban_norm}")
        return

    conn.create("res.partner.bank", vals)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--odoo-url", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)

    ap.add_argument("--accounts", required=True)
    ap.add_argument("--contacts", required=True)

    ap.add_argument("--mapping-db", default="dynamics_odoo_map.sqlite3")
    ap.add_argument("--dry-run", action="store_true")

    ap.add_argument("--skip-bank-accounts", action="store_true", help="No importar cuentas bancarias (evita validación IBAN)")

    args = ap.parse_args()

    conn = OdooConn(args.odoo_url, args.db, args.user, args.password)
    mapping = MappingDB(args.mapping_db)

    pending_main_contact: List[Tuple[str, str]] = []

    print("== Importando ACCOUNTS (empresas) ==")
    for row in read_csv_rows(args.accounts):
        dyn_id = norm_str(row.get("accountid"))
        if not dyn_id:
            continue

        vals = build_partner_vals_from_account(row, conn)
        partner_id = upsert_partner(conn, mapping, "account", dyn_id, vals, args.dry_run)

        if not args.skip_bank_accounts:
            iban = norm_str(row.get("contel_iban") or row.get("new_numerodecuentabancaria"))
            if partner_id and partner_id != -1 and iban:
                upsert_partner_bank_account(conn, partner_id, iban, args.dry_run)

        main_contact_guid = norm_str(row.get("primarycontactid"))
        if main_contact_guid:
            pending_main_contact.append((dyn_id, main_contact_guid))

    print("== Importando CONTACTS (personas) ==")
    for row in read_csv_rows(args.contacts):
        dyn_id = norm_str(row.get("contactid"))
        if not dyn_id:
            continue

        vals = build_partner_vals_from_contact(row, conn)

        parent_guid = norm_str(row.get("contel_cuenta"))
        if parent_guid:
            parent_odoo_id = mapping.get("account", parent_guid)
            if parent_odoo_id and parent_odoo_id != -1:
                vals["parent_id"] = parent_odoo_id

        upsert_partner(conn, mapping, "contact", dyn_id, vals, args.dry_run)

    print("== Resolviendo CONTACTO PRINCIPAL (main_contact_id) ==")
    for account_guid, contact_guid in pending_main_contact:
        account_odoo_id = mapping.get("account", account_guid)
        contact_odoo_id = mapping.get("contact", contact_guid)
        if not account_odoo_id or account_odoo_id == -1:
            continue
        if not contact_odoo_id or contact_odoo_id == -1:
            continue

        if args.dry_run:
            print(f"[DRY] SET main_contact_id account_id={account_odoo_id} -> contact_id={contact_odoo_id}")
            continue

        conn.write("res.partner", [account_odoo_id], {"main_contact_id": contact_odoo_id})

    print("OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())