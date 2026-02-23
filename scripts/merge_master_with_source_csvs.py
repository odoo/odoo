#!/usr/bin/env python3
import csv
import argparse
from pathlib import Path

csv.field_size_limit(1024 * 1024 * 200)


def norm(value: str) -> str:
    return (value or "").strip().casefold()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_master(master_path: Path):
    _, rows = read_csv(master_path)

    by_display = {}
    by_id = {}
    by_xml = {}

    for row in rows:
        if row.get("row_type") != "MAIN_RECORD":
            continue
        display = row.get("display_name", "")
        odoo_id = row.get("id", "")
        xml_id = row.get("xml_id", "")

        key = norm(display)
        if key and key not in by_display:
            by_display[key] = {
                "id": odoo_id,
                "xml_id": xml_id,
                "display_name": display,
            }

        if odoo_id and odoo_id not in by_id:
            by_id[odoo_id] = {
                "id": odoo_id,
                "xml_id": xml_id,
                "display_name": display,
            }

        if xml_id and xml_id not in by_xml:
            by_xml[xml_id] = {
                "id": odoo_id,
                "xml_id": xml_id,
                "display_name": display,
            }

    rel_by_field_display = {}
    for row in rows:
        if row.get("row_type") != "RELATION_VALUE":
            continue
        field = (row.get("field") or "").strip()
        display = (row.get("display_name") or "").strip()
        xml_id = (row.get("xml_id") or "").strip()
        if not field or not display or not xml_id:
            continue
        field_map = rel_by_field_display.setdefault(field, {})
        key = norm(display)
        if key and key not in field_map:
            field_map[key] = xml_id

    return by_display, by_id, by_xml, rel_by_field_display


def ext_account_id(account_guid: str) -> str:
    account_guid = (account_guid or "").strip()
    return f"legacy.account_{account_guid}" if account_guid else ""


def ext_contact_id(contact_guid: str) -> str:
    contact_guid = (contact_guid or "").strip()
    return f"legacy.contact_{contact_guid}" if contact_guid else ""


def pick_partner_ref(match: dict, fallback_external: str) -> str:
    if not match:
        return fallback_external
    xml_id = (match.get("xml_id") or "").strip()
    if not xml_id:
        return fallback_external
    if xml_id.startswith("__import__") or ".dyn_" in xml_id:
        return fallback_external
    return xml_id


def pick_rel_xml(rel_map: dict, value: str, default: str = "") -> str:
    key = norm(value)
    if not key:
        return default
    return rel_map.get(key, default)


def build_accounts(accounts_rows, contacts_by_guid, master_by_display, accounts_by_guid):
    out = []
    for row in accounts_rows:
        row = dict(row)

        account_guid = (row.get("accountid") or "").strip()
        parent_guid = (row.get("parentaccountid") or "").strip()
        primary_contact_guid = (row.get("primarycontactid") or "").strip()
        name = (row.get("name") or "").strip()

        own_match = master_by_display.get(norm(name))

        parent_row = accounts_by_guid.get(parent_guid)
        parent_name = (parent_row or {}).get("name", "")
        parent_match = master_by_display.get(norm(parent_name)) if parent_name else None

        primary_contact = contacts_by_guid.get(primary_contact_guid)
        primary_contact_name = (primary_contact or {}).get("fullname", "")
        primary_contact_match = master_by_display.get(norm(primary_contact_name)) if primary_contact_name else None

        row["odoo_match_id"] = (own_match or {}).get("id", "")
        row["odoo_match_xml_id"] = (own_match or {}).get("xml_id", "")
        row["odoo_match_display_name"] = (own_match or {}).get("display_name", "")

        row["parentaccountid_odoo_id"] = (parent_match or {}).get("id", "")
        row["parentaccountid_odoo_xml_id"] = (parent_match or {}).get("xml_id", "")
        row["primarycontactid_odoo_id"] = (primary_contact_match or {}).get("id", "")
        row["primarycontactid_odoo_xml_id"] = (primary_contact_match or {}).get("xml_id", "")

        row["import_id"] = ext_account_id(account_guid)
        row["import_name"] = name
        row["import_vat"] = (row.get("new_cif") or "").strip()
        row["import_email"] = (row.get("emailaddress1") or "").strip()
        row["import_phone"] = (row.get("telephone1") or "").strip()
        row["import_mobile"] = (row.get("telephone2") or "").strip()
        row["import_street"] = (row.get("address1_line1") or "").strip()
        row["import_city"] = (row.get("address1_city") or "").strip()
        row["import_zip"] = (row.get("address1_postalcode") or "").strip()
        row["import_state_name"] = (row.get("address1_stateorprovince") or "").strip()
        row["import_country_name"] = (row.get("address1_country") or "").strip()

        parent_fallback = ext_account_id(parent_guid)
        row["import_parent_id/id"] = pick_partner_ref(parent_match, parent_fallback)

        primary_fallback = ext_contact_id(primary_contact_guid)
        row["import_contact_id/id"] = pick_partner_ref(primary_contact_match, primary_fallback)

        out.append(row)

    return out


def build_contacts(contacts_rows, accounts_by_guid, contacts_by_guid, master_by_display):
    out = []
    for row in contacts_rows:
        row = dict(row)

        contact_guid = (row.get("contactid") or "").strip()
        account_guid = (row.get("contel_cuenta") or "").strip()
        parent_contact_guid = (row.get("parent_contactid") or "").strip()

        fullname = (row.get("fullname") or "").strip()
        own_match = master_by_display.get(norm(fullname))

        account_row = accounts_by_guid.get(account_guid)
        account_name = (account_row or {}).get("name", "")
        account_match = master_by_display.get(norm(account_name)) if account_name else None

        parent_contact_row = contacts_by_guid.get(parent_contact_guid)
        parent_contact_name = (parent_contact_row or {}).get("fullname", "")
        parent_contact_match = master_by_display.get(norm(parent_contact_name)) if parent_contact_name else None

        row["odoo_match_id"] = (own_match or {}).get("id", "")
        row["odoo_match_xml_id"] = (own_match or {}).get("xml_id", "")
        row["odoo_match_display_name"] = (own_match or {}).get("display_name", "")

        row["contel_cuenta_odoo_id"] = (account_match or {}).get("id", "")
        row["contel_cuenta_odoo_xml_id"] = (account_match or {}).get("xml_id", "")

        row["parent_contactid_odoo_id"] = (parent_contact_match or {}).get("id", "")
        row["parent_contactid_odoo_xml_id"] = (parent_contact_match or {}).get("xml_id", "")

        row["import_id"] = ext_contact_id(contact_guid)
        row["import_name"] = fullname or (row.get("firstname") or "").strip()
        row["import_firstname"] = (row.get("firstname") or "").strip()
        row["import_lastname"] = (row.get("lastname") or "").strip()
        row["import_email"] = (row.get("emailaddress1") or "").strip()
        row["import_phone"] = (row.get("telephone1") or "").strip()
        row["import_mobile"] = (row.get("mobilephone") or "").strip()
        row["import_street"] = (row.get("address1_line1") or "").strip()
        row["import_city"] = (row.get("address1_city") or "").strip()
        row["import_zip"] = (row.get("address1_postalcode") or "").strip()
        row["import_state_name"] = (row.get("address1_stateorprovince") or "").strip()
        row["import_country_name"] = (row.get("address1_country") or "").strip()
        row["import_function"] = (row.get("jobtitle") or "").strip()

        account_fallback = ext_account_id(account_guid)
        row["import_parent_id/id"] = pick_partner_ref(account_match, account_fallback)

        parent_contact_fallback = ext_contact_id(parent_contact_guid)
        row["import_parent_contact_id/id"] = pick_partner_ref(parent_contact_match, parent_contact_fallback)

        out.append(row)

    return out


def main():
    parser = argparse.ArgumentParser(description="Fusiona master de Odoo con CSV de cuentas/contactos para preparar importación.")
    parser.add_argument("--master", required=True, help="CSV master (res_partner_import_master_map.csv)")
    parser.add_argument("--accounts", required=True, help="CSV de cuentas origen")
    parser.add_argument("--contacts", required=True, help="CSV de contactos origen")
    parser.add_argument("--outdir", required=True, help="Directorio de salida")
    args = parser.parse_args()

    master_path = Path(args.master)
    accounts_path = Path(args.accounts)
    contacts_path = Path(args.contacts)
    outdir = Path(args.outdir)

    if not master_path.exists():
        raise FileNotFoundError(f"No existe master: {master_path}")
    if not accounts_path.exists():
        raise FileNotFoundError(f"No existe accounts: {accounts_path}")
    if not contacts_path.exists():
        raise FileNotFoundError(f"No existe contacts: {contacts_path}")

    master_by_display, _, _, rel_by_field_display = load_master(master_path)

    accounts_fields, accounts_rows = read_csv(accounts_path)
    contacts_fields, contacts_rows = read_csv(contacts_path)

    accounts_by_guid = { (r.get("accountid") or "").strip(): r for r in accounts_rows if (r.get("accountid") or "").strip() }
    contacts_by_guid = { (r.get("contactid") or "").strip(): r for r in contacts_rows if (r.get("contactid") or "").strip() }

    merged_accounts = build_accounts(accounts_rows, contacts_by_guid, master_by_display, accounts_by_guid)
    merged_contacts = build_contacts(contacts_rows, accounts_by_guid, contacts_by_guid, master_by_display)

    accounts_extra = [
        "odoo_match_id", "odoo_match_xml_id", "odoo_match_display_name",
        "parentaccountid_odoo_id", "parentaccountid_odoo_xml_id",
        "primarycontactid_odoo_id", "primarycontactid_odoo_xml_id",
        "import_id", "import_name", "import_vat", "import_email", "import_phone", "import_mobile",
        "import_street", "import_city", "import_zip", "import_state_name", "import_country_name",
        "import_parent_id/id", "import_contact_id/id",
    ]

    contacts_extra = [
        "odoo_match_id", "odoo_match_xml_id", "odoo_match_display_name",
        "contel_cuenta_odoo_id", "contel_cuenta_odoo_xml_id",
        "parent_contactid_odoo_id", "parent_contactid_odoo_xml_id",
        "import_id", "import_name", "import_firstname", "import_lastname", "import_email",
        "import_phone", "import_mobile", "import_street", "import_city", "import_zip",
        "import_state_name", "import_country_name", "import_function",
        "import_parent_id/id", "import_parent_contact_id/id",
    ]

    out_accounts = outdir / "accounts_merged_for_import.csv"
    out_contacts = outdir / "contacts_merged_for_import.csv"
    out_accounts_auto = outdir / "accounts_odoo_auto_import.csv"
    out_accounts_detect = outdir / "accounts_odoo_detect_ok.csv"
    out_contacts_auto = outdir / "contacts_odoo_auto_import.csv"
    out_contacts_detect = outdir / "contacts_odoo_detect_ok.csv"
    out_accounts_final = outdir / "accounts_odoo_final.csv"
    out_contacts_final = outdir / "contacts_odoo_final.csv"

    write_csv(out_accounts, list(accounts_fields) + accounts_extra, merged_accounts)
    write_csv(out_contacts, list(contacts_fields) + contacts_extra, merged_contacts)

    country_map = rel_by_field_display.get("country_id", {})
    state_map = rel_by_field_display.get("state_id", {})

    accounts_auto_rows = []
    for row in merged_accounts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        accounts_auto_rows.append({
            "id": row.get("import_id", ""),
            "name": row.get("import_name", ""),
            "is_company": "True",
            "company_type": "company",
            "type": "contact",
            "vat": row.get("import_vat", ""),
            "email": row.get("import_email", ""),
            "phone": row.get("import_phone", ""),
            "mobile": row.get("import_mobile", ""),
            "street": row.get("import_street", ""),
            "city": row.get("import_city", ""),
            "zip": row.get("import_zip", ""),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id/id": row.get("import_parent_id/id", ""),
            "comment": row.get("description", ""),
        })

    contacts_auto_rows = []
    for row in merged_contacts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        parent_partner = row.get("import_parent_id/id", "") or row.get("import_parent_contact_id/id", "")
        firstname = (row.get("import_firstname") or "").strip()
        lastname = (row.get("import_lastname") or "").strip()
        computed_name = row.get("import_name", "") or " ".join(v for v in [firstname, lastname] if v).strip()

        contacts_auto_rows.append({
            "id": row.get("import_id", ""),
            "name": computed_name,
            "is_company": "False",
            "company_type": "person",
            "type": "contact",
            "email": row.get("import_email", ""),
            "phone": row.get("import_phone", ""),
            "mobile": row.get("import_mobile", ""),
            "street": row.get("import_street", ""),
            "city": row.get("import_city", ""),
            "zip": row.get("import_zip", ""),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id/id": parent_partner,
            "function": row.get("import_function", ""),
        })

    accounts_detect_rows = []
    for row in merged_accounts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        parent_guid = (row.get("parentaccountid") or "").strip()
        parent_name = ""
        if parent_guid:
            parent_name = (accounts_by_guid.get(parent_guid, {}) or {}).get("name", "")

        phone_work = (row.get("telephone1") or "").strip() or (row.get("address1_telephone1") or "").strip()
        mobile = (row.get("telephone2") or "").strip() or (row.get("address1_telephone2") or "").strip()

        accounts_detect_rows.append({
            "name": (row.get("name") or "").strip(),
            "is_company": "True",
            "company_type": "company",
            "type": "contact",
            "vat": (row.get("new_cif") or "").strip(),
            "email": (row.get("emailaddress1") or "").strip(),
            "phone": phone_work,
            "mobile": mobile,
            "website": (row.get("websiteurl") or "").strip(),
            "street": (row.get("address1_line1") or "").strip(),
            "city": (row.get("address1_city") or "").strip(),
            "zip": (row.get("address1_postalcode") or "").strip(),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id": parent_name,
            "comment": (row.get("description") or "").strip(),
        })

    contacts_detect_rows = []
    for row in merged_contacts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        phone_work = (row.get("telephone1") or "").strip() or (row.get("business2") or "").strip()
        mobile = (row.get("mobilephone") or "").strip() or (row.get("telephone2") or "").strip()
        parent_name = (row.get("company") or "").strip()
        if not parent_name:
            parent_name = (row.get("parent_id") or "").strip()

        computed_name = (row.get("import_name") or "").strip()
        if not computed_name:
            computed_name = (row.get("fullname") or "").strip()
        if not computed_name:
            first = (row.get("firstname") or "").strip()
            last = (row.get("lastname") or "").strip()
            computed_name = " ".join([v for v in [first, last] if v]).strip()
        if not computed_name:
            computed_name = (row.get("emailaddress1") or "").strip()

        contacts_detect_rows.append({
            "name": computed_name,
            "is_company": "False",
            "company_type": "person",
            "type": "contact",
            "email": (row.get("emailaddress1") or "").strip(),
            "phone": phone_work,
            "mobile": mobile,
            "function": (row.get("jobtitle") or "").strip(),
            "street": (row.get("address1_line1") or "").strip(),
            "city": (row.get("address1_city") or "").strip(),
            "zip": (row.get("address1_postalcode") or "").strip(),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id": parent_name,
            "company_name": parent_name,
        })

    write_csv(
        out_accounts_auto,
        [
            "id", "name", "is_company", "company_type", "type", "vat", "email", "phone", "mobile",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id/id", "comment",
        ],
        accounts_auto_rows,
    )
    write_csv(
        out_accounts_detect,
        [
            "name", "is_company", "company_type", "type", "vat", "email", "phone", "mobile", "website",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id", "comment",
        ],
        accounts_detect_rows,
    )
    write_csv(
        out_contacts_auto,
        [
            "id", "name", "is_company", "company_type", "type", "email", "phone", "mobile",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id/id", "function",
        ],
        contacts_auto_rows,
    )

    write_csv(
        out_contacts_detect,
        [
            "name", "is_company", "company_type", "type", "email", "phone", "mobile", "function",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id", "company_name",
        ],
        contacts_detect_rows,
    )

    accounts_final_rows = []
    for row in merged_accounts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        parent_guid = (row.get("parentaccountid") or "").strip()
        parent_id = ext_account_id(parent_guid)

        phone_work = (row.get("telephone1") or "").strip() or (row.get("address1_telephone1") or "").strip()
        mobile = (row.get("telephone2") or "").strip() or (row.get("address1_telephone2") or "").strip()

        accounts_final_rows.append({
            "id": ext_account_id((row.get("accountid") or "").strip()),
            "name": (row.get("name") or "").strip(),
            "is_company": "True",
            "company_type": "company",
            "type": "contact",
            "vat": (row.get("new_cif") or "").strip(),
            "email": (row.get("emailaddress1") or "").strip(),
            "phone": phone_work,
            "mobile": mobile,
            "website": (row.get("websiteurl") or "").strip(),
            "street": (row.get("address1_line1") or "").strip(),
            "city": (row.get("address1_city") or "").strip(),
            "zip": (row.get("address1_postalcode") or "").strip(),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id/id": parent_id,
            "comment": (row.get("description") or "").strip(),
        })

    account_id_by_norm_name = {}
    account_name_by_id = {}
    for row in accounts_final_rows:
        acc_id = (row.get("id") or "").strip()
        acc_name = (row.get("name") or "").strip()
        if acc_id:
            account_name_by_id[acc_id] = acc_name
        key = norm(acc_name)
        if key and acc_id and key not in account_id_by_norm_name:
            account_id_by_norm_name[key] = acc_id
    available_account_ids = set(account_name_by_id.keys())

    contacts_final_rows = []
    for row in merged_contacts:
        country_name = (row.get("import_country_name") or "").strip()
        state_name = (row.get("import_state_name") or "").strip()
        country_xml = pick_rel_xml(country_map, country_name, "base.es" if norm(country_name) in {"españa", "espana", "spain"} else "")
        state_xml = pick_rel_xml(state_map, state_name, "")

        cid = (row.get("contactid") or "").strip()
        account_guid = (row.get("contel_cuenta") or "").strip()
        parent_account_id = ext_account_id(account_guid)

        company_raw = (row.get("company") or "").strip() or (row.get("adx_organizationname") or "").strip()
        if parent_account_id and parent_account_id not in available_account_ids:
            parent_account_id = ""
        if not parent_account_id and company_raw:
            parent_account_id = account_id_by_norm_name.get(norm(company_raw), "")

        first = (row.get("firstname") or "").strip()
        last = (row.get("lastname") or "").strip()
        computed_name = (row.get("fullname") or "").strip() or (row.get("name") or "").strip()
        if not computed_name:
            computed_name = " ".join(v for v in [first, last] if v).strip()
        if not computed_name:
            computed_name = (row.get("emailaddress1") or "").strip()
        phone_work = (row.get("telephone1") or "").strip() or (row.get("business2") or "").strip()
        mobile = (row.get("mobilephone") or "").strip() or (row.get("telephone2") or "").strip()

        company_name = account_name_by_id.get(parent_account_id, "") if parent_account_id else company_raw

        contacts_final_rows.append({
            "id": ext_contact_id(cid),
            "name": computed_name,
            "firstname": first,
            "lastname": last,
            "is_company": "False",
            "company_type": "person",
            "type": "contact",
            "email": (row.get("emailaddress1") or "").strip(),
            "phone": phone_work,
            "mobile": mobile,
            "function": (row.get("jobtitle") or "").strip(),
            "street": (row.get("address1_line1") or "").strip(),
            "city": (row.get("address1_city") or "").strip(),
            "zip": (row.get("address1_postalcode") or "").strip(),
            "state_id/id": state_xml,
            "country_id/id": country_xml,
            "parent_id/id": parent_account_id,
            "company_name": company_name,
        })

    write_csv(
        out_accounts_final,
        [
            "id", "name", "is_company", "company_type", "type", "vat", "email", "phone", "mobile", "website",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id/id", "comment",
        ],
        accounts_final_rows,
    )

    write_csv(
        out_contacts_final,
        [
            "id", "name", "firstname", "lastname", "is_company", "company_type", "type", "email", "phone", "mobile", "function",
            "street", "city", "zip", "state_id/id", "country_id/id", "parent_id/id", "company_name",
        ],
        contacts_final_rows,
    )

    print(f"OK: {out_accounts}")
    print(f"OK: {out_contacts}")
    print(f"OK: {out_accounts_auto}")
    print(f"OK: {out_accounts_detect}")
    print(f"OK: {out_contacts_auto}")
    print(f"OK: {out_contacts_detect}")
    print(f"OK: {out_accounts_final}")
    print(f"OK: {out_contacts_final}")


if __name__ == "__main__":
    main()
