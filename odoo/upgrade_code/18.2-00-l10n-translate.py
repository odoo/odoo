from __future__ import annotations

import csv
import difflib
import glob
import re
import typing
from collections import defaultdict
from io import StringIO

from lxml.builder import E
import lxml.etree as etree
import polib

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


MODELS = {
    'account.account.tag': ['name'],
    'account.cash.rounding': ['name'],
    'account.disallowed.expenses.category': ['name'],
    'account.incoterms': ['name'],
    'account.journal': ['name'],
    'account.payment.method': ['name'],
    'account.report': ['name'],
    'account.report.column': ['name'],
    'account.report.line': ['name'],
    'account.tax.group': ['name'],
    'account.tax.report': ['name'],
    'hr.contract.salary.benefit': ['name', 'description', 'fold_label'],
    'hr.contract.salary.benefit.value': ['name'],
    'hr.contract.salary.personal.info': ['name', 'helper', 'value', 'placeholder'],
    'hr.leave.type': ['name'],
    'hr.payroll.dashboard.warning': ['name'],
    'hr.payroll.structure': ['payslip_name'],
    'hr.salary.rule': ['name'],
    'hr.salary.rule.category': ['name'],
    'hr.work.entry.type': ['name'],
    'l10n_br.operation.type': ['name'],
    'l10n_eg_edi.activity.type': ['name'],
    'l10n_eg_edi.uom.code': ['name'],
    'l10n_es_edi_facturae.ac_role_type': ['name'],
    'l10n_it.document.type': ['name'],
    'l10n_latam.document.type': ['name'],
    'l10n_latam.identification.type': ['name'],
    'l10n_mx_edi.res.locality': ['name'],
    'l10n_pe.res.city.district': ['name'],
    'l10n_ro_saft.account.asset.category': ['description'],
    'l10n_ro_saft.tax.type': ['description'],
    'product.template': ['name'],
    'res.city': ['name'],
    'res.country.state': ['name'],
    'res.currency': ['l10n_cl_short_name', 'l10n_cl_currency_code'],
    'res.partner.category': ['name'],
    'res.partner.title': ['name', 'shortcut'],
}

def parse_xmlid(xmlid: str, default_module: str) -> tuple[str, str]:
    split_id = xmlid.split('.', maxsplit=1)
    if len(split_id) == 1:
        return default_module, split_id[0]
    return split_id[0], split_id[1]

def upgrade(file_manager: FileManager):
    translation_files = [
        f for f in file_manager
        if f.path.suffix in ('.po', '.pot')
        and f.path.parts[-3].startswith('l10n_')
        and f.path.parts[-2] == 'i18n'
    ]
    nb_translation_files = len(translation_files)
    data_files = [
        f for f in file_manager
        if f.path.suffix in ('.xml', '.csv')
        and f.path.parts[-3].startswith('l10n_')
        and f.path.parts[-2] == 'data'
    ]
    nb_data_files = len(data_files)

    translations = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # {module: {model: {xmlid: {lang: msgstr}}}}
    for i, file in enumerate(translation_files):
        file_manager.print_progress(i, nb_translation_files + nb_data_files, file.path)
        module_name = file.path.parts[-3]
        lang = file.path.stem
        pofile = polib.pofile(str(file.path))
        original_pofile = polib.pofile(str(file.path))
        for entry in pofile:
            if file.path.suffix == '.po':
                for occurence in entry.occurrences:
                    if occurence[0].startswith('model:'):
                        xmlid = occurence[0].split(':')[2]
                        model = occurence[0].split(':')[1].split(',')[0]
                        translations[module_name][model][xmlid][lang] = entry.msgstr
            entry.occurrences = [
                occurence
                for occurence in entry.occurrences
                if not any(
                    occurence[0].startswith(f'model:{model}')
                    for model in MODELS
                )
            ]
            if not entry.occurrences:
                entry.obsolete = True

        for entry in pofile.obsolete_entries():
            pofile.remove(entry)
        if pofile != original_pofile:
            file.content = str(pofile)

    for i, file in enumerate(data_files):
        file_manager.print_progress(nb_translation_files + i, nb_translation_files + nb_data_files, file.path)
        module_name = file.path.parts[-3]
        if file.path.suffix == '.xml':
            tree = etree.parse(str(file.path))
            for record_node in tree.xpath(f"""//record[{' or '.join(f"@model='{m}'" for m in MODELS)}]"""):
                model = record_node.attrib['model']
                xmlid = '.'.join(parse_xmlid(record_node.attrib['id'], module_name))
                for fname in MODELS[model]:
                    base_node = record_node.find(f"field[@name='{fname}']")
                    if base_node is not None:
                        name_tail = base_node.tail
                        base_node.tail = None
                        for lang, translated in translations[module_name][model][xmlid].items():
                            if translated:
                                translated_node = E('field', translated, **{fname: f'{fname}@{lang}'})
                                translated_node.tail = name_tail
                                base_node.addnext(translated_node)
                        base_node.tail = name_tail

            file.content = ''.join(
                diff[2:]
                for diff in difflib.ndiff(
                    file.content.splitlines(keepends=True),
                    etree.tostring(tree, encoding="utf-8").decode().splitlines(keepends=True),
                )
                # avoid any diff generated by lxml and only keep diff for the lines added
                if diff.startswith((' ', '-'))
                or re.match(r"""\+\s*<field name="\w+@""", diff)
            )
        elif file.path.suffix == '.csv':
            model = file.path.stem
            csv_file = csv.DictReader(file.content.splitlines())
            csv_data = list(csv_file)
            first_row = csv_data[0]
            fnames = model in MODELS and sorted(set(first_row.keys()) & set(MODELS[model]))
            if fnames:
                langs = sorted({
                    lang
                    for fname in fnames
                    for lang, val in translations[module_name][model][first_row[fname]].items()
                    if val
                })
                if langs:
                    buffer = StringIO()
                    writer = csv.DictWriter(
                        buffer,
                        fieldnames=csv_file.fieldnames + [
                            f'{fname}@{lang}'
                            for lang in langs
                            for fname in fnames
                        ],
                        delimiter=',',
                        quotechar='"',
                        quoting=csv.QUOTE_ALL
                    )
                    writer.writeheader()
                    for row in csv_data:
                        xmlid = '.'.join(parse_xmlid(row['id'], module_name))
                        for lang in langs:
                            for fname in fnames:
                                row[f'{fname}@{lang}'] = translations[module_name][model][xmlid].get(lang, "")
                        writer.writerow(row)
                    file.content = buffer.getvalue()
