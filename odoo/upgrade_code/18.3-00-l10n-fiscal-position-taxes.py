import csv
import logging
# import typing

from io import StringIO
from collections import defaultdict

# if typing.TYPE_CHECKING:
#     from odoo.cli.upgrade_code import FileManager

# def upgrade(file_manager: FileManager):
def upgrade(file_manager):
    log = logging.getLogger(__name__)

    SRC_FIELD = 'tax_ids/tax_src_id'
    DEST_FIELD = 'tax_ids/tax_dest_id'
    fiscal_position_data_files = [
        file for file in file_manager
        if file.path.suffix in ('.csv')
        and 'account.fiscal.position' in file.path.name
    ]
    nb_fiscal_position_files = len(fiscal_position_data_files)

    tax_data_files = [
        file for file in file_manager
        if file.path.suffix in ('.csv')
        and 'account.tax-' in file.path.name
    ]
    nb_tax_files = len(tax_data_files)

    tax_positions = defaultdict(lambda: defaultdict(lambda: defaultdict(fp=None, replaces=[])))  # {module_name: { tax_x: {fp: "fiscal_position_1,fiscal_position_2", replaces: [tax1]}}
    for i, file in enumerate(fiscal_position_data_files, start=1):
        file_manager.print_progress(i, nb_fiscal_position_files, file.path)

        module_name = file.path.parts[-4]
        csv_file = csv.DictReader(file.content.splitlines())
        csv_data = list(csv_file)
        first_row = csv_data[0]
        field_names = first_row.keys()
        if SRC_FIELD not in field_names or DEST_FIELD not in field_names:
            continue

        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                f
                for f in csv_file.fieldnames
                if f not in (SRC_FIELD, DEST_FIELD)
            ],
            delimiter=',',
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator='\n',
        )
        writer.writeheader()

        domestic_fp_id = f'{module_name}_domestic_fiscal_position'
        domestic_fp_name = f'{module_name[5:7].upper()} Domestic'
        fiscal_position = ''
        for row_nb, row in enumerate(csv_data, start=1):
            fiscal_position = row['id'] or fiscal_position
            src_tax = row.pop(SRC_FIELD)
            dest_tax = row.pop(DEST_FIELD)
            if row_nb == 1:
                # copy the first fiscal position to create a generic domestic fiscal position
                # REMOVE THE CREATION OF DOMESTIC FISCAL POSITIONS - leave tax blank instead?
                writer.writerow({
                    **row,
                    'id': domestic_fp_id,
                    'name': domestic_fp_name,
                })
            if src_tax and dest_tax:
                existing_fp = tax_positions[module_name][dest_tax]['fp']
                if existing_fp and fiscal_position not in existing_fp:
                    log.warning("In module: %s, Tax: %s will be assigned to multiple Fiscal Positions: %s. A corresponding tax might be missing for %s", module_name, dest_tax, f"{existing_fp},{fiscal_position}", existing_fp)
                tax_positions[module_name][src_tax]['fp'] = domestic_fp_id
                tax_positions[module_name][dest_tax]['fp'] = f"{existing_fp},{fiscal_position}" if existing_fp and fiscal_position not in existing_fp else fiscal_position
                tax_positions[module_name][dest_tax]['replaces'].append(src_tax)
                if row['id']:
                    writer.writerow(row)
            else:
                writer.writerow(row)

        file.content = buffer.getvalue()

    for i, file in enumerate(tax_data_files, start=1):
        file_manager.print_progress(i, nb_tax_files, file.path)

        module_name = file.path.parts[-4]
        csv_file = csv.DictReader(file.content.splitlines())
        csv_data = list(csv_file)

        is_primary_tax = 'name' in csv_file.fieldnames
        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=csv_file.fieldnames + (['fiscal_position_ids', 'alternative_tax_ids'] if is_primary_tax else []),
            delimiter=',',
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator='\n',
        )
        writer.writeheader()
        for tax_row in csv_data:
            tax_id = tax_row['id']
            if tax_id and is_primary_tax:
                tax_info = tax_positions[module_name][tax_id] if tax_id else {}
                writer.writerow({
                    **tax_row,
                    'fiscal_position_ids': tax_info.get('fp'),
                    'alternative_tax_ids': ','.join(tax_info.get('replaces', [])),
                })
            else:
                writer.writerow(tax_row)
        file.content = buffer.getvalue()
