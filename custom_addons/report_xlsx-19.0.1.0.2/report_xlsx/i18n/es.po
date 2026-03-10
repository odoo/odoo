# Translation of Odoo Server.
# This file contains the translation of the following modules:
# * report_xlsx
#
# Translators:
# Pedro M. Baeza <pedro.baeza@gmail.com>, 2016
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 10.0\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2016-11-01 20:11+0000\n"
"PO-Revision-Date: 2023-09-02 20:42+0000\n"
"Last-Translator: Ivorra78 <informatica@totmaterial.es>\n"
"Language-Team: Spanish (https://www.transifex.com/oca/teams/23907/es/)\n"
"Language: es\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: \n"
"Plural-Forms: nplurals=2; plural=n != 1;\n"
"X-Generator: Weblate 4.17\n"

#. module: report_xlsx
#: model:ir.model,name:report_xlsx.model_report_report_xlsx_abstract
msgid "Abstract XLSX Report"
msgstr "Informe XLSX en abstracto"

#. module: report_xlsx
#: model:ir.model,name:report_xlsx.model_report_report_xlsx_partner_xlsx
msgid "Partner XLSX Report"
msgstr "Informe empresa XLSX"

#. module: report_xlsx
#: model:ir.actions.report,name:report_xlsx.partner_xlsx
msgid "Print to XLSX"
msgstr "Imprimir en XLSX"

#. module: report_xlsx
#: model:ir.model,name:report_xlsx.model_ir_actions_report
msgid "Report Action"
msgstr "Informar Acción"

#. module: report_xlsx
#: model:ir.model.fields,field_description:report_xlsx.field_ir_actions_report__report_type
msgid "Report Type"
msgstr "Tipo informe"

#. module: report_xlsx
#: model:ir.model.fields,help:report_xlsx.field_ir_actions_report__report_type
msgid ""
"The type of the report that will be rendered, each one having its own "
"rendering method. HTML means the report will be opened directly in your "
"browser PDF means the report will be rendered using Wkhtmltopdf and "
"downloaded by the user."
msgstr ""
"El tipo de informe que se representará, cada uno con su propio método de "
"representación. HTML significa que el informe se abrirá directamente en el "
"PDF de su navegador significa que el informe se representará usando "
"Wkhtmltopdf y el usuario lo descargará."

#. module: report_xlsx
#: model:ir.model.fields.selection,name:report_xlsx.selection__ir_actions_report__report_type__xlsx
msgid "XLSX"
msgstr "XLSX"

#, python-format
#~ msgid "%s model was not found"
#~ msgstr "%s modelo no fue encontrado"

#, python-format
#~ msgid ""
#~ "A popup window with your report was blocked. You may need to change your "
#~ "browser settings to allow popup windows for this page."
#~ msgstr ""
#~ "Una ventana emergente con su informe fue bloqueada. Puede que necesite "
#~ "cambiar las preferencias de su navegador para que permita ventanas "
#~ "emergentes en esta página."

#~ msgid "Display Name"
#~ msgstr "Nombre mostrado"

#~ msgid "ID"
#~ msgstr "ID"

#~ msgid "Last Modified on"
#~ msgstr "Última modificación el"

#, python-format
#~ msgid "Warning"
#~ msgstr "Aviso"

#, fuzzy
#~ msgid "ir.actions.report"
#~ msgstr "ir.actions.report.xml"
