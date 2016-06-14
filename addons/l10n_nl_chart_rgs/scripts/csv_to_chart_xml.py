# -*- coding: utf-8 -*-
"""Convert Reference Chart of Account (RGS) to xml format."""
# © 2016 Therp BV (http://therp.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import csv

HEADER = """\
<?xml version="1.0" encoding="utf-8"?>
<openerp>
    <data noupdate="1">
"""

FOOTER = """    </data>
</openerp>"""

ROOT_RECORD = """\
    <record id="rgs_root" model="account.account.template">
        <field name="name">NEDERLANDS REFERENTIE GROOTBOEKSCHEMA</field>
        <field name="code">0</field>
        <field name="type">view</field>
        <field name="user_type" ref="account.data_account_type_view"/>
    </record>
"""

RECORD = """\
    <record id="%(xml_id)s" model="account.account.template">
        <field name="name">%(name)s</field>
        <field name="code">%(code)s</field>
        <field name="type">%(type)s</field>
        <field name="user_type" ref="%(user_type)s"/>
        <field name="parent_id" ref="%(parent_id)s"/>
        <field name="reconcile" eval="%(reconcile)s"/>
    </record>
"""


def get_type(row):
    """Determine type for row.

    Type can be:
    - view (is a parent for other accounts)
    - receivable
    - payable
    - liquidity
    - other (not any of the above)
    """
    account_type = 'view'
    row_type = row[0][0]  # first letter of first column - B or W
    row_subtype = row[0][0:4]  # first four letters
    row_subsubtype = row[0][0:7]  # first seven letters
    level = int(row[4].strip())
    if ((row_type == 'B' and level == 5) or
        # TODO: Some subtypes have both level 4 and 5:
            (row_subtype == 'BLas' and level == 4) or  # Financial lease
            (row_subtype == 'BLim' and level == 4) or  # Liquidity
            (row_subtype == 'BVor' and level == 4) or  # Receivable
            (row_subtype == 'BVrd' and level == 4) or  # Stock ('voorraad')
            (row_subtype == 'BSch' and level == 4) or  # Debt
            (row_type == 'W' and level == 4)):
        if row_subtype == 'BLim':
            account_type = 'liquidity'
        elif row_subsubtype == 'BVorDeb' and level == 4:
            account_type = 'receivable'  # 'vorderingen'
        elif row_subsubtype == 'BSchCre' and level == 4:
            account_type = 'payable'  # 'schulden'
        else:
            account_type = 'other'
    return account_type


def get_user_type(row, account_type):
    """Link record to account_account_type."""
    xml_id = 'data_account_type_view'
    row_type = row[0][0]  # first letter of first column - B or W
    row_subtype = row[0][0:4]  # first four letters
    debit_credit = row[3]
    # Handle income and expense accounts:
    if row_type == 'W':
        if debit_credit == 'C' and account_type == 'other':
            xml_id = 'data_account_type_income'
        elif debit_credit == 'C' and account_type == 'view':
            xml_id = 'account_type_income_view1'
        elif  account_type == 'other':  # must be debit_credit 'D'
            xml_id = 'data_account_type_expense'
        else:  # must be account_type 'view'
            xml_id = 'account_type_expense_view1'
    else:  # must be row_type 'B'
        asset_subtypes = [
            'BIva',  # IMMATERIËLE VASTE ACTIVA
            'BMva',  # MATERIËLE VASTE ACTIVA
            'BFva',  # FINANCIËLE VASTE ACTIVA
            'BVrd',  # VOORRADEN
            'BPrj',  # PROJECTEN
        ]
        equity_subtypes = [
            'BEff',  # EFFECTEN
            'BEiv',  # EIGEN VERMOGEN
        ]
        liability_subtypes = [
            'BVrz',  # VOORZIENINGEN
            'BLas',  # LANGLOPENDE SCHULDEN
            'BSch',  # KORTLOPENDE SCHULDEN
        ]
        if 'Btw' in row[0]:
            xml_id = 'conf_account_type_tax'
        elif account_type == 'payable':
            xml_id = 'data_account_type_payable'
        elif account_type == 'receivable':
            xml_id = 'data_account_type_receivable'
        elif row_subtype in asset_subtypes and account_type == 'other':
            xml_id = 'data_account_type_asset'
        elif row_subtype in asset_subtypes and account_type == 'view':
            xml_id = 'account_type_asset_view1'
        elif row_subtype in equity_subtypes:
            xml_id = 'conf_account_type_equity'
        elif row_subtype in liability_subtypes and account_type == 'other':
            xml_id = 'data_account_type_liability'
        elif row_subtype in liability_subtypes and account_type == 'view':
            xml_id = 'account_type_liability_view1'
        elif row_subtype == 'BLim':  # liquidity
            if account_type == 'other':
                xml_id = 'data_account_type_view'
            elif 'Kas' in row[0]:
                xml_id = 'data_account_type_cash'
            else:
                xml_id = 'data_account_type_bank'
        else:
            xml_id = 'data_account_type_view'
    return "account.%s" % xml_id


def get_reconcile(account_type):
    """Wether account should be reconciled."""
    if account_type in ['payable', 'receivable']:
        return 'True'
    return 'False'


def get_parent_id(row):
    """Determine parent xml_id for row."""
    reference_code = row[0]
    if len(reference_code) < 4:
        return 'rgs_root'
    return reference_code[0:(len(reference_code) - 3)].lower()


def get_code(row):
    """Get code for row."""
    return row[1] or row[0]


def get_description(row):
    """Get description for row."""
    if row[2]:
        description = row[2].replace('<', '&lt;').replace('>', '&gt;')
    else:
        description = row[0]
    return description


print HEADER
print ROOT_RECORD
with open('rgs2dot0.csv', 'rb') as csvfile:
    skip = 1
    counter = 0
    for row in csv.reader(csvfile, delimiter=";", quotechar='"'):
        counter += 1
        if counter <= skip:
            continue
        account_type = get_type(row)  # selection
        user_type = get_user_type(row, account_type)  # link to account_account_type
        print RECORD % {
            'xml_id': row[0].lower(),
            'code': get_code(row),
            'name': get_description(row),
            'type': account_type,
            'user_type': user_type,
            'parent_id': get_parent_id(row),
            'reconcile': get_reconcile(account_type)
        }
print FOOTER
