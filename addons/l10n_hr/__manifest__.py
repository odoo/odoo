# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Goran Kliska
# mail:   goran.kliska(AT)slobodni-programi.hr
# Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
# Copyright (c) 2022 - Daj Mi 5, Zagreb
# Contributions:
#           Tomislav Bošnjaković, Storm Computers d.o.o. :
#              - account types
#           port to odoo 16 and new tax schema - Davor Bojkić
{
    "name": "Croatia - Accounting (RRIF 2021)",
    "description": """
Croatian localisation.
======================

Author: 
  - Goran Kliska, Exocdica d.o.o - original module for v6.1  
    (cla/ex : Decodio-applications d.o.o., ex Slobodni programi d.o.o.)
  - Davor Bojkić, Daj mi 5 - port to odoo 16, update tax schema to 2022
  - Alberto Poljak, e-Sustavi d.o.o - update port for Odoo 16
    

Description
-----------
 
- Chart of Accounts (RRIF ver.2021)
    - source: https://www.rrif.hr/dok/preuzimanje/RRIF-RP2021.PDF
    - 4 dev : https://www.rrif.hr/dok/preuzimanje/RRIF-RP2021.7z
    - Kontni plan prema RRIF-u, dorađen u smislu kraćenja naziva i dodavanja analitika
    - Analitičke grupe konta (1-4 znamenaka) dodane (account.group.template) 
- Stavke poreznog izvještaja prema PDV obrascu
    - source: https://www.porezna-uprava.hr/HR_obrasci/Documents/POREZ%20NA%20DODANU%20VRIJEDNOST/PDV.pdf
    - Potencijalno moguće dodati : PDV-S i ZP... 

Porezi prema pozicijama PDV obrasca:

- PDV-I - neoporezivi ili 0%
    - 0% Tuzemni PPO
    - 0% ISP.U DR.DRŽ.ČLANICAMA
    - 0% DOBRA EU
    - 0% USLUGE EU
    - 0% BEZ SJEDIŠTA
    - 0% SAST/POST EU
    - 0% PRIJEVOZNA SREDSTVA EU
    - 0% TUZEMNE ISP.
    - 0% IZVOZNE ISP.
    - 0% OSTALA OSLOBOĐENJA
- PDV-II - oporezive transakcije - Isporuke
    - 25% PDV na Dobra
    - 25% PDV na Usluge
    - 25% PDV na Predujam 
    - 13% PDV Dobra
    - 13% PDV Usluge
    - 13% PDV na Predujam
    - 5% PDV na Dobra
    - 5% PDV na Predujam
- PDV-III - obračunati pretporez - Nabava
    - PPDV 25% na Dobra
    - PPDV 25% Usluge
    - PPDV 25% na Predujam
    - PPDV 13% na Dobra
    - PPDV 13% Usluge
    - PPDV 13% na Predujam  
    - PPDV 5% na Dobra 
    - PPDV 5% na Predujam
- PDV III-II - reverse charge - Nabava   
    - Prijenos PO 25%       ( PPO PP 25% - PPO PDV 25% )
    - EU 5% DOBRA           ( EU PP 5% na dobra - EU PDV 5% na Dobra )
    - EU 13% DOBRA          ( EU PP 13% na dobra - EU PDV 13% na Dobra )
    - EU 25% DOBRA          ( EU PP 25% na Dobra - EU PDV 25% na Dobra )
    - EU 25% USLUGE         ( EU PP 25% na Usluge - EU PDV 25% na Usluge )
    - Bez sjedišta 25%  ( Bez sjedišta PP 25% - Bez sjedišta PDV 25% )(13%,5%)
    - UVOZ 25%          ( Uvoz PP 25% - Uvoz PDV 25% ) (13%,5%)
  
- Grupa država: EU - Croatia     
- Osnovne fiskalne pozicije
    - R1 partneri
    - EU Partneri
    - INO partneri
    - AVANS
    - Prijenos PO
    - Bez sjedista
 

""",
    "version": "16.0",
    "author": "OpenERP Croatian Community, DAJ MI 5",
    'category': 'Accounting/Localizations/Account Charts',

    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_hr_chart_data.xml',
        #'data/account.account.template.csv',
        'data/2021/account.account.template.csv',
        'data/2021/account.group.template.csv',  # Account groups full structure for analytic
        'data/account_chart_tag_data.xml',
        'data/account.tax.group.csv',
        #'data/account_tax_report_data.xml',
        'data/2021/account_tax_report_data.xml',
        #'data/account_tax_template_data.xml',
        'data/2021/account_tax_template_data.xml',
        #'data/account_tax_fiscal_position_data.xml',
        'data/2021/res_country_group.xml',
        'data/2021/account_tax_fiscal_position_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
