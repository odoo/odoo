Minimal set of accounts to start to work in Perú.
=================================================

The usage of this CoA must refer to the official documentation on MEF.

https://www.mef.gob.pe/contenidos/conta_publ/documentac/VERSION_MODIFICADA_PCG_EMPRESARIAL.pdf
https://www.mef.gob.pe/contenidos/conta_publ/documentac/PCGE_2019.pdf

All the legal references can be found here.

http://www.sunat.gob.pe/legislacion/general/index.html

Considerations.
===============

Chart of account:
-----------------

The tree of the CoA is done using account groups, the most common accounts 
are available within their group, if you want to create a new account use 
the groups as reference. 

Taxes:
------

'IGV': {'name': 'VAT', 'code': 'S'},
'IVAP': {'name': 'VAT', 'code': ''},
'ISC': {'name': 'EXC', 'code': 'S'},
'ICBPER': {'name': 'OTH', 'code': ''},
'EXP': {'name': 'FRE', 'code': 'G'},
'GRA': {'name': 'FRE', 'code': 'Z'},
'EXO': {'name': 'VAT', 'code': 'E'},
'INA': {'name': 'FRE', 'code': 'O'},
'OTHERS': {'name': 'OTH', 'code': 'S'},

We added on this module the 3 concepts in taxes (necessary for the EDI
signature)

EDI Peruvian Code: used to select the type of tax from the SUNAT
EDI UNECE code: used to select the type of tax based on the United Nations
Economic Commission
EDI Affect. Reason: type of affectation to the IGV based on the Catalog 07

Products:
---------

Code for products to be used in the EDI are availables here, in order to decide
which tax use due to which code following this reference and python code:

https://docs.google.com/spreadsheets/d/1f1fxV8uGhA-Qz9-R1L1-dJirZ8xi3Wfg/edit#gid=662652969

**Nota:**
---------

**RELACIÓN ENTRE EL PCGE Y LA LEGISLACIÓN TRIBUTARIA:**

Este PCGE ha sido preparado como una herramienta de carácter contable, para acumular información que
requiere ser expuesta en el cuerpo de los estados financieros o en las notas a dichos estados. Esa acumulación se
efectúa en los libros o registros contables, cuya denominación y naturaleza depende de las actividades que se
efectúen, y que permiten acciones de verificación, control y seguimiento. Las NIIF completas y la NIIF PYMES no
contienen prescripciones sobre teneduría de libros, y consecuentemente, sobre los libros y otros registros
de naturaleza contable. Por otro lado, si bien es cierto la contabilidad es también un insumo, dentro de otros, para
labores de cumplimiento tributario, este PCGE no ha sido elaborado para satisfacer prescripciones tributarias ni su
verificación. No obstante ello, donde no hubo oposición entre la contabilidad financiera prescrita por las NIIF y
la legislación tributaria, este PCGE ha incluido subcuentas, divisionarias y sub divisionarias, para
distinguir componentes con validez tributaria, dentro del conjunto de componentes que corresponden a una
perspectiva contable íntegramente. Por lo tanto, este PCGE no debe ser considerado en ningún aspecto
como una guía con propósitos distintos del contable.
