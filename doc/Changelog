4.2.1
	Bugfixes
	Fix context for source_count function
	Create stock move on production for products without BOM lines
	Add IBAN fields in bank view
	Fix uninitialize variable in import data
	Update due date on invoice when payment term change
	Fix store on field function that have type many2one or one2one
	Request summary must be truncate
	Partner event name must be truncate
	Remove parent field on partner contact view
	Fix icon type on journal period
	Remove exception on the size of char field
	Fix reference on move line that comes from invoice (Customer != Supplier)
	Add function search on sheet_id of timesheet_sheet
	Don't return 0 for balance account if there is no fiscal year
	Fix set to draft for expense, now really set to draft
	Add product and partner in the recursive call of tax compute
	Don't compute balance account for inactive account
	Fix bad encoding in log message on report_sxw
	Fix overdue report for refund lines
	Don't start server in non secure mode if secure mode have been set
	Fix default value of move line if move_id is not find
	Fix _product_partner_ref for cannot concatenate 'str' and 'bool' objects
	Add partner_id in the context of SO for browsing the product
	Fix multi-tax code on invoice
	Fix tax definition for Belgium chart
	Remove compute debit/credit on inactive account
	Fix the way the tax are rounded for invoice with tax included prices
	Fix SO to use the right uom and price to create invoice
	Fix on_chnage uos on SO to return the id not the browse record
	Add condition on the button "Sending goods>Packing to be invoiced" to show
		only customer packings
	Fix zero division error when the quantity is zero on an invoice line
	Fix duplicate timesheet line that have been invoiced
	Fix invoice report for bad removeParentNode tag
	Fix priority for product view
	Fix tax line computation when encoding account lines manually
	Fix refund supplier invoice to have the same journal
	New chinese translation
	Pass context to action_done on stock move
	Add product_uom change on sale order line
	Fix demo data for working time UOM
	Fix _sheet function in timesheet_sheet when called with a list of non
		unique id
	Remove commit inside function validate on account move
	Use one function to post account move
	Fix computation of sale/purchase amount in segmentation module
	Use standar uom converion in analytic lines
	Add journal_id in context for account move line search in payment module
	Fix wrong id used by pricelist based on partner form
	Use partner reference from SO/PO for invoice name if there is one
	Make analysis analytic module include child accounts

4.2.0
	Summary:
		Add new view graph
		REPORT_INTRASTAT: new module
		KERNEL: add netrpc (speed improvement)
		REPORT_STOCK: add report on stock by stock location and production lots
		HR_TIMESHEET_INVOICE: add final invoice
		MULTI_COMPANY_ACCOUNT: new module
		ADD modules publication tools
		KERNEL: add timezone
		KERNEL: add concurnecy check
		BASE: allow to specify many view_id in act_window
		BASE: add ir.rules (acces base on record fields)
		KERNEL: add search_count on objects
		KERNEL: add assert tools (unit test)
		KERNEL: improve workflow speed
		KERNEL: move some modules to extra_addons
	Bugfixes:
		Fix pooler for multi-db
		REPORT_ANALYTIC: new reports
		BOARD_ACCOUNT: new dashboard for accountants
		PURCHASE: allow multiple pickings for the same purchase order
		STOCK: When refunding picking: confirm & Assign the newly generated picking
		PRODUCT: add average price
		STOCK: Fix workflow for stock
		TOOLS: Fix export translate for wizard
		KERNEL: add id in import_data
		BASE: add history rate to currency
		ACCOUNT: partner_id is now required for an invoice
		HR_TIMESHEET: add exception if employee haven't product
		I18N: new fr_CH file
		HR_EXPENSE: fix domain
		ACCOUNT: Fix invoice with currency and payment term
		ACCOUNT: Fix currency
		KERNEL: add pidfile
		ACCOUNT,PURCHASE,SALE: use partner lang for description
		Model Acces: Unlink permission (delete) is now available
		KERNEL: Remove set for python2.3
		HR: add id to Attendance menu
		PRODUCT: add dimension to packaging
		ACCOUNT: new cash_discount on payment term
		KERNEL: Add price accuracy
		BASE: Function to remove installed modules
		REPORT_SALE: fix for sale without line
		PURCHASE: remove use of currency
		KERNEL: fix set without values
		PURCHASE: fix domain pricelist
		INVOICE: use date for currency rate
		KERNEL: Fix import many2many by id
		KERNEL: run the cron
		ACCOUNT: bank statment line now have a ref t othe corresponding invoice
		ACCOUNT: Add possibilitty to include tax amount in base amount for the computation of the next taxes
		ACCOUNT: Add product in tax compute python code
		KERNEL: use reportlab 2.0
		BASE: fix import the same lang
		ACCOUNT: fix tax code
		ACCOUNT: define tax account for invoice and refund
		ACCOUNT: add supplier tax to product
		ACCOUNT: don't overwrite tax_code on the creation for account line
		PURCHASE: use partner code for report order
		KERNEL: fix pooler netsvc for multi-db
		TOOLS: add ref to function tag
		PRODUCT: fix digits on volume and weight, add weight_net
		ACCOUNT: split to new module account_cash_discount
		ORM : error message on python constraints are now displayed correctly
		ACCOUNT: add partner to tax compute context
		KERNEL: improve logger
		PROJECT: add check_recursion for project
		HR_TIMESHEET_INVOICE: improve create invoice
		ACCOUNT: add product_id to analytic line create by invoice
		KERNEL: fix the inheritance mechanism
		KERNEL: Fix use always basename for cvs file
		BASE: fix IBAN len to 27
		INVOICE: fix invoice number for analytic
		REPORT: add replace tag for custom header
		ACCOUNT: add ref to analytic line
		BASE: prevent exception in ir_cron
		SALE: fix uos for tax_amount
		MRP: fix dbname in _procure_confirm
		HR_EXPENSE: add domain to analytic_account
		KERNEL: use 0 instead of False for fix on _fnct_read
		SUBSCRIPTION: add required to model
		HR_TIMESHEET: add rounding on report
		SALE: Fix cancel invoice and recreate invoice, now cancel also the order lines
		STOCK-DELIVERY: add wizard invoice_onshipping from delivery to stock
		STOCK: use tax from sale for invoice
		BASE: improve copy of res.partner
		ACCOUNT: pay only invoice if not in state draft
		REPORT: fix rml translation, translate before eval
		PRODUCT_EXTENDED: don't use seller price for bom price
		ACCOUNT_TAX_INCLUDE: fix right amount in account move generate with tax_include
		BASE: improve workflow print
		SALE: fix workflow error when create invoice from wizard
		MRP: Use company currency for Product Cost Structure
		BASE: prevent recursion in company
		KERNEL: Fix deleted property and many2one
		KERNEL: allow directory for import csv
		KERNEL: add store option to fields function
		ACCOUNT: use property_account_tax on on_change_product
		KERNEL: add right-click for translate label
		KERNEL: fix log of backtrace
		KERNEL: fix search on xxx2many
		BASE: use tool to call popen.pipe2
		KERNEL: fix print workflow on win32
		BASE: fix US states
		KERNEL: use python 2.3 format_exception
		ACCOUNT: add multi-company into base accounting
		KERNEL: check return code for exec_pg_command_pipe
		KERNEL: fix search with active args
		KERNEL: improve _sql_contsraints, now insert if doesn't exist
		KERNEL: remove old inheritor and add _constraints and _sql_constraints to the fields inherited
		CRM: bugfix mailgate
		PURCHASE: fix the UOM for purchase line and improve update price unit
		ACCOUNT: new invoice view
		KERNEL,BASE: allow to create zip modules
		BASE: add right-to-left
		KERNEL: copy now ignore technical values ('create_date', 'create_uid', 'write_date' and 'write_uid')
		ACCOUNT_TAX_INCLUDE: Now the module manage correctly the case when the taxes defined on the product differ from the taxes defined on the invoice line
		ALL: fix colspan 3 -> 4
		KERNEL: use context for search
		ACCOUNT: improve speed of analytic account
		ACCOUNT: fix search debit/credit on partner
		ACCOUNT: fix refund invoice if no product_id nor uos_id on lines
		MRP: fix scheduler location of product to produce and method, date of automatic orderpoint
		KERNEL: many2many : fix unlink and link action
		MRP: add default product_uom from context and add link from product to bom
		PROJECT: improve speed for function fields
		ALL: remove bad act_window name
		KERNEL: modification for compatibility with postgres 7.4
		KERNEL: fix size for selection field
		KERNEL: fix compatibility for python2.5
		KERNEL: add new win32 build script
		KERNEL: add test for duplicate report and wizard
		ACCOUNT: force round amount fixed in payment term
		KERNEL: fix print screen
		CRM: Better ergonomy
		SERVER: add sum tag on tree view that display sum of the selected lines
		KERNEL: allow subfield query on one2many
		KERNEL: fix create_date and write_date as there are timestamp now
		SERVER: improve language
		KERNEL: fix search on fields function of type one2many, many2many
		ACCOUNT: fix pay invoice to use period
		ACCOUNT: add check recursion in account.tax.code
		MRP: fix compute cycle for workcenter
		BASE: add constraint uniq module name
		BASE: improve update module list
		ACCOUNT: add round to last payment term
		KERNEL: don't modify the args of the call
		KERNEL: don't use mutable as default value in function defintion
		KERNEL: fix orm for sql query with reserved words

16/03/2007
4.0.3
	Summary:
		Improve the migration scripts
		Some bugfixes
		Print workflow on win32 (with ghostscript)

	Bugfixes:
		BASE: Fix "set default value"
		HR_TIMESHEET_INVOICE: Improve invoice on timesheet
		ACCOUNT: Fix tax amount
		KERNEL: correct the delete for property
		PURCHASE: fix the journal for invoice created by PO
		KERNEL: fix the migration for id removed
		Add id to some menuitem
		BASE: prevent exception in ir_cron when the DB is dropped
		HR: Fix sign-in/sign-out, the user is now allowed to provide a date in
			the future
		SALE: fix uos for the tax amount
		MRP: fix wrong dbname in _procure_confirm
		HR_EXPENSE: add domain to analytic_account
		ACCOUNT: fix debit_get
		SUBSCRIPTION: model is required now
		HR_TIMESHEET: add rounding value to report
		SALE: Fix cancel and recreate invoice, now cancel also the order lines
		STOCK: use the tax define in sale for the invoice
		ACCOUNT: add test to pay only if invoice not in state draft
		KERNEL: root have access to all records
		REPORT: fix rml translation to translate before the eval
		ACCOUNT_TAX_INCLUDE: Use the right amount in account mmove generate
			with tax_include
		BASE: Improve the workflow print
		SALE: Fix workflow error when creating invoice from the wizard
		PRODUCT_EXTENDED: don't use pricelist to compute standard price
		MRP: Use company currency for product cost structure
		KERNEL: fix where clause when deleting false items
		ACCOUNT: product source account depend on the invoice type now
		ACCOUNT: use the property account tax for the on_change_product
		ACCOUNT: use the invoice date for the date of analytic line
		ACCOUNT: Fix the pay invoice when multi-currency
		HR_TIMESHEET_PROJECT: use the right product
		STOCK: Fix to assign picking with product consumable and call the
			workflow
		STOCK: Fix the split lot production
		PURCHASE: fix workflow for purchase with manual invoice to not set
			invoice and paid
		DELIVERY: can use any type of journal for invoice
		KERNEL: fix search on xxx2many
		ACCOUNT: add id to sequence record
		KERNEL: set properly the demo flag for module installed
		KERNEL: Fix print workflow on win32
		LETTER: fix print letter

	Migration:
		Fix migration for postreSQL 7.4
		Fix the default value of demo in module
		Fix migration of account_uos to product_uos

Wed Jan 17 15:06:07 CET 2007
4.0.2
	Summary:
		Improve the migration
		Some bugfixes
		Improve tax

	Bugfixes:
		Fix tax for invoice, refund, etc
		SALE: fix view priority
		PURCHASE: wizard may crash on some data
		BASE: Fix import the same lang
		BASE: start the cron
		PURCHASE: fix domain for pricelist
		KERNEL: fix object set without values
		REPORT_SALE: fix for sale without line
		KERNEL: add pidfile
		BASE: remove 'set' for python2.3 compliant
	Migration:
		Migrate hr_timesheet user_id

Fri Dec 22 12:01:26 CET 2006
4.0.1
	Summary:
		Improve the migration
		Some bugfixes
	
	Bugfixes:
		HR_EXPENSE: Fix domain
		HR_TIMESHEET: Fix employee without product
		TOOLS: Fix export translate
		BASE: fix for concurrency of sequence number
		MRP: fix report
		CRM: fix graph report
		KERNEL: fix instance of osv_pool
		KERNEL: fix setup.py


Mon Dec 4 18:01:55 CET 2006
4.0.0
	Summary:
		Some bugfixes

Tue Nov 28 14:44:20 CET 2006
4.0.0-rc1
	Summary:
		This is a stable version (RC1) with lots of new features. Main
		Improvements were:
			Accounting: more functions, new modules, more stable
			Much more better ergonomy
			Lots of simplification to allows non IT people to use and
				configure Tiny ERP: manage database, step by step configuration
				menu, auto-installers, better help, ...

	New:
		Skill management module
		ACCOUNT:
			New and simpler bank statement form
			New reports:
				on Timesheets (analytic accounting)
				Theorical revenue based on time spent
				Global timesheet report by month
				Chart of accounts
			Different taxes methods supported
				Gross (brut)
				Net
				Fixed amount
		INVOICE:
			invoice on shipping (manufacturing industry)
			invoice on timesheet (services)
		PURCHASE:
			different invoicing control method (on order, on shipping,
			manual)
		Support of prices tax included /excluded in sales orders
		New modules:
			Sale_journal, stock_journal for bigger industries:
				Divide works in different journals
			New invoicing method from partner, to so, to picking
				Daily, Monthly (grouped by partner or not)
			New modules for prices with taxes included / excluded
		New chart of accounts supported:
			l10n_be/                     l10n_chart_be_frnl/
			l10n_chart_id/               l10n_chart_uk/
			l10n_ca-qc/                  l10n_chart_br/
			l10n_chart_it/               l10n_chart_us_general/
			l10n_ch/                     l10n_chart_ca_en/
			l10n_chart_it_cc2424/        l10n_chart_us_manufacturing/
			l10n_ch_pcpbl_association/   l10n_chart_ca_fr/
			l10n_chart_la/               l10n_chart_us_service/
			l10n_ch_pcpbl_independant/   l10n_chart_ch_german/
			l10n_chart_nl/               l10n_chart_us_ucoa/
			l10n_ch_pcpbl_menage/        l10n_chart_cn/
			l10n_chart_nl_standard/      l10n_chart_us_ucoa_ez/
			l10n_ch_pcpbl_plangen/       l10n_chart_cn_traditional/
			l10n_chart_no/               l10n_chart_ve/
			l10n_ch_pcpbl_plangensimpl/  l10n_chart_co/
			l10n_chart_pa/               l10n_fr/
			l10n_ch_vat_brut/            l10n_chart_cz/
			l10n_chart_pl/               l10n_se/
			l10n_ch_vat_forfait/         l10n_chart_da/
			l10n_chart_sp/               l10n_simple/
			l10n_ch_vat_net/             l10n_chart_de_datev_skr03/
			l10n_chart_sw/
			l10n_chart_at/               l10n_chart_de_skr03/
			l10n_chart_sw_church/
			l10n_chart_au/               l10n_chart_hu/
			l10n_chart_sw_food/
		Step by step configuration menu
		Setup wizard on first connection
			Select a company profile, auto-install language, demo data, ...

	Imrovements:
		KERNEL: Demo data improved
			Better import / export system
		KERNEL: Multi-database management system
			Backup, Restore, Create, Drop from the client
		PRODUCT/PRODUCT_EXTD: Eavily change the product form, use the new
			object to compute the pricelist
		REPORTS:
			Better Sale order, purchase order, invocies and customers reports
		ACCOUNT: Support of taxes in accounts
			management of the VAT taxes for most european countries:
				Support of VAT codes in invoices
				Better computation of default values in accounting entries
				Preferences in partners, override products
			Bugfix when closing a fiscal year
			Better ergonomy when writting entries
		New Module Management System:
			Install / Upgrade new modules directly from the client
			Install new languages
		KERNEL:
			Ability to add select=True at the object level for postgresql indexes
			Bugfix in search in some inherited objects
			Added the ability to call methods from a browse object
		KERNEL+BASE: changed the way the migration system works for menuitems:
			now you can change a menuitem defined elsewhere. And this will work
			whether that menuitem has an id or not (it use the name of the
			menuitem to find it)
		KERNEL:
			Installing a module from the client
		Better Windows Auto-Installer
		DELIVERY:
			Delivery and invoicing on picking list
		KERNEL:
			Distinction between active (by default) and installable
		ACCOUNT/PROJECT: Added support for the type of invoicing
		CRM:
			eMAil gateway
			Management of different departments and sections
			Rule system
		About 20 new statistics reporting
		eCommerce interface:
			Better Joomla (virtuemart, OSCommerce) support
			Joomla is now fully functionnal

	Bugfixes:
		ACCOUNT: tree view on reporting analytic account
		KERNEL: Fix the bug that happened when mixing active and child_of
			search
		KERNEL: Check for the existance of active when computing child_of
		PRODUCT: production computation with different UoM

------------------------------------------------------------------------

Fri Oct  6 14:44:05 CEST 2006
Server 3.4.2
    Improvements:
        BASE: changed workflow print system so that it handles inexisting 
              workflows more gracefully (patch from Geoff Gardiner)
        MRP: new view to take into account the orderpoint exceptions
        MRP: made menu title more explicit

    Bugfixes:
        ACCOUNT: fixed typo in invoice + changed sxw file so that it is in 
                 sync with the rml file
        DELIVERY: fixed taxes on delivery line (patch from Brice Vissière)
        PROJECT: skip tasks without user in Gantt charts (it crashed the report)
        PRODUCT: fixed bug when no active pricelist version was found 
        PRODUCT_EXTENDED: correct recursive computation of the price
        SALE: get product price from price list even when quantity is set after
              the product is set
        STOCK: fixed partial picking

    Packaging:
        Changed migration script so that it works on PostgreSQL 7.4

------------------------------------------------------------------------

Tue Sep 12 15:10:31 CEST 2006
Server 3.4.1
    Bugfixes:
        ACCOUNT: fixed a bug which prevented to reconcile posted moves.

------------------------------------------------------------------------

Mon Sep 11 16:12:10 CEST 2006
Server 3.4.0 (changes since 3.3.0)
    New modules:
        ESALE_JOOMLA: integration with Joomla CMS 
        HR_TIMESHEET_ICAL: import iCal to automatically complete timesheet 
            based on outlook meetings
        PARTNER_LDAP: adds partner synchronization with an LDAP server
        SALE_REBATE: adds rebates to sale orders

        4 new modules for reporting using postgresql views:
        REPORT_CRM: reporting on CRM cases: by month, user, ...
        REPORT_PROJECT: reporting on projects: tasks closed by project, user,
                        month, ...
        REPORT_PURCHASE: reporting on purchases
        REPORT_SALE: reporting on sales by periods and by product, category of
                     product, ...

    New features:
        KERNEL: Tiny ERP server and client may now communicate through HTTPS.
                To launch the server with HTTPS, use the -S or --secure option
                Note that if the server runs on HTTPS, the clients MUST connect
                with the "secure" option checked.
        KERNEL: the server can now run as a service on Windows
        Printscreen function (Tree view print)
        KERNEL: added a new --stop-after-init option which stops the server 
                just before it starts listening
        KERNEL: added support for a new forcecreate attribute on XML record 
                fields: it is useful for records are in a data node marked as 
                "noupdate" but the record still needs to be added if it doesn't
                exit yet. The typical use for that is when you add a new record
                to a noupdate file/node.
        KERNEL: manage SQL constraints with human-readable error message on the
                client side, eg: Unique constraints
        KERNEL: added a new system to be able to specify the tooltip for each
                field in the definition of the field (by using the new help="" 
                attribute)
        ACCOUNT: new report: aged trial balance system
        ACCOUNT: added a wizard to pay an invoice from the invoice form
        BASE: print on a module to print the reference guide using introspection
        HR: added report on attendance errors
        PRODUCT: products now support multi-Level variants

    Improvements:
        KERNEL: speed improvement in many parts of the system thanks to some
                optimizations and a new caching system
        KERNEL: New property system which replace the, now deprecated, ir_set 
                system. This leads to better migration of properties, more
                practical use of them (they can be used like normal fields), 
                they can be translated, they are "multi-company aware", and 
                you can specify access rights for them on a per field basis.
        KERNEL: Under windows, the server looks for its configuration file in 
                the "etc" sub directory (relative to the installation path). 
                This was needed so that the server can be run as a windows 
                service (using the SYSTEM profile).
        KERNEL: added ability to import CSV files from the __terp__.py file
        KERNEL: force freeing cursor when closing them, so that they are 
                available again immediately and not when garbage collected.
        KERNEL: automatically drop not null/required constraints from removed
                fields (ie which are in the database but not in the object)
        KERNEL: added a command-line option to specify which smtp server to use
                to send emails.
        KERNEL: made browse_record hashable
        ALL: removed shortcuts for the demo user.
        ACCOUNT: better invoice report
        ACCOUNT: Modifs for account chart, removed old stock_income account type
        ACCOUNT: made the test_paid method on invoices more tolerant to buggy 
                 data (open invoices without move/movelines)
        ACCOUNT: better bank statement reconciliation system
        ACCOUNT: accounting entries encoding improved a lot (using journal)
        ACCOUNT: Adding a date and max Qty field in analytic accounts for 
                 support contract
        ACCOUNT: Adding the View type to analytic account / cost account
        ACCOUNT: changed test_paid so that the workflow works even if there is
                 no move line
        ACCOUNT: Cleanup credit/debit and balance computation methods. Should 
                 be faster too.
        ACCOUNT: use the normal sequence (from the journal) for the name of 
                 moves generated from invoices instead of the longer name.
        ACCOUNT: print Payment delay in invoices
        ACCOUNT: account chart show subtotals
        ACCOUNT: Subtotal in view accounts
        ACCOUNT: Replaced some Typo: moves-> entries, Transaction -> entry
        ACCOUNT: added quantities in analytic accounts view, and modified 
                 cost ledger report for partners/customers
        ACCOUNT: added default value for the currency field in invoices
        ACCOUNT: added the comment/notes field on the invoice report
        BASE: added menuitem (and action) to access partner functions (in the 
              definitions menu)
        BASE: better demo data
        BASE: duplicating a menu item now duplicates its action and submenus
        BASE: Bank Details on Partners
        CRM: View on all actions made on cases (used by our ISO9002 customer 
             to manage corrections to actions)
        CRM: fixed wizard to create a sale order from a case
        CRM: search on non active case, not desactivated by default
        CRM: Case ID in fields with search
        HR_TIMESHEET: new "sign_in, sign_out" using projects. It fills 
                      timesheets and attendance at the same time.
        HR_TIMESHEET: added cost unit to employee demo data
        MRP: improvement in the scheduler
        MRP: purchase order lines' description generated from a procurement
             defaults to the product name instead of procurement name
        MRP: Better traceability
        MRP: Better view for procurement in exception
        MRP: Added production delay in product forms. Use this delay for 
             average production delay for one product
        MRP: dates scheduler, better computation
        MRP: added constraint for non 0 BoM lines
        PRODUCT: Better pricelist system (on template or variant of product)
        PRODUCT_EXTENDED: Compute the price only if there is a supplier
        PROJECT: when a task is closed, use the task's customer to warn the 
                 customer if it is set, otherwise use the project contact.
        PROJECT: better system to automatically send an email to the customer 
                 when a task is closed or reopened.
        PURCHASE: date_planned <= current_time line in red
        PURCHASE: better purchase order report
        PURCHASE: better purchase order duplication: you can now duplicate non 
                  draft purchase orders and the new one will become draft.
        SALE: better sale order report
        SALE: better demo data for sale orders
        SALE: better view for buttons in sale.order
        SALE: select product => description = product name instead of code
        SALE: warehouse field in shop is now required
        SCRUM: lots of improvements for better useability
        STOCK: allows to confirm empty picking lists.
        STOCK: speed up stock computation methods

    Bugfixes:
        KERNEL: fix a huge bug in the search method for objects involving 
                "old-style" inheritance (inherits) which prevented some records
                to be accessible in some cases. Most notable example was some 
                products were not accessible in the sale order lines if you had
                more products in your database than the limit of your search 
                (80 by default).
        KERNEL: fixed bug which caused OO (sxw) reports to behave badly (crash 
                on Windows and not print correctly on Linux) when data 
                contained XML entities (&, <, >)
        KERNEL: reports are now fully concurrency compliant
        KERNEL: fixed bug which caused menuitems without id to cause havoc on 
                update. The menuitems themselves were not created (which is 
                correct) but they created a bad "default" action for all 
                menuitems without action (such as all "menu folders").
        KERNEL: fix a small security issue: we should check the password of the 
                user when a user asks for the result of a report (in addition 
                to the user id and id of that report)
        KERNEL: bugfix in view inheritancy
        KERNEL: fixed duplicating resource with a state field whose selection 
                doesn't contain a 'draft' value (for example project tasks). It
                now uses the default value of the resource for that field.
        KERNEL: fixed updating many2many fields using the (4, id) syntax
        KERNEL: load/save the --logfile option correctly in the config file
        KERNEL: fixed duplicating a resource with many2many fields
        ALL: all properties should be inside a data tag with "noupdate" and
             should have a forcecreate attribute.
        ACCOUNT: fixed rounding bug in tax computation method
        ACCOUNT: bugfix in balance and aged balance reports
        ACCOUNT: fixing precision in function fields methods 
        ACCOUNT: fixed creation of account move lines without using the client 
                 interface
        ACCOUNT: fixed duplicating invoices
        ACCOUNT: fixed opening an invoices whose description contained non 
                 ASCII chars at specific position
        ACCOUNT: small bugfixes in all accounting reports
        ACCOUNT: fixed crash when --without-demo due to missing payment.term
        ACCOUNT: fixed bug in automatic reconciliation
        ACCOUNT: pass the address to the tax computation method so that it is 
                 available in the tax "python applicable code"
        BASE: allows to delete a request which has a history (it now deletes the
              history as well as the request)
        BASE: override copy method for users so that we can duplicate them
        BASE: fixed bug when the user search for a partner by hitting on an 
              empty many2one field (it searched for a partner with ref=='')
        BASE: making ir.sequence call thread-safe.
        CRM: fixed a bug which introduced an invalid case state when closing a
             case (Thanks to Leigh Willard)
        HR: added domain to category tree view so that they are not displayed 
            twice
        HR_TIMESHEET: fixed print graph
        HR_TIMESHEET: fixed printing timesheet report
        HR_TIMESHEET: Remove a timesheet entry removes the analytic line
        MRP: bugfix on "force reservation"
        MRP: fixed bugs in some reports and MRP scheduler when a partner has 
             no address
        MRP: fix Force production button if no product available
        MRP: when computing lots of procurements, the scheduler could raise 
             locking error at the database level. Fixed.
        PRODUCT: added missing context to compute product list price
        PRODUCT: fixed field type of qty_available and virtual_available 
                 (integer->float). This prevented these fields to be displayed
                 in forms.
        PROJECT: fixed the view of unassigned task (form and list) instead of 
                 form only.
        PURCHASE: fixed merging orders that made inventory errors when coming 
                  from a procurement (orderpoint).
        PURCHASE: fix bug which prevented to make a purchase order with 
                  "manual" lines (ie without product)
        PURCHASE: fix wizard to group purchase orders in several ways:
            - only group orders if they are to the same location
            - only group lines if they are the same except for qty and unit
            - fix the workflow redirect method so that procurement are not 
              canceled when we merge orders
        SALE: fixed duplicating a confirmed sale order
        SALE: fixed making sale orders with "manual" lines (without product)
        STOCK: future stock prevision bugfix (for move when date_planned < now)
        STOCK: better view for stock.move
        STOCK: fixed partial pickings (waiting for a production)
        Miscellaneous minor bugfixes

    Packaging:
        Fixed bug in setup.py which didn't copy csv files nor some sub-
            directories
        Added a script to migrate a 3.3.0 server to 3.4.0 (you should read the 
            README file in doc/migrate/3.3.0-3.4.0)
        Removed OsCommerce module

------------------------------------------------------------------------

Fri May 19 10:16:18 CEST 2006
Server 3.3.0
    New features:
        NEW MODULE: hr_timesheet_project
            Automatically maps projects and tasks to analytic account
            So that hours spent closing tasks are automatically encoded
        KERNEL: Added a logfile and a pidfile option (patch from Dan Horak)
        STOCK: Added support for revisions of tracking numbers
        STOCK: Added support for revision of production lots
        STOCK: Added a "splitting and tracking lines" wizard
        PRODUCT_EXTENDED: Added a method to compute the cost of a product
                          automatically from the cost of its parts

    Improvements:
        ALL: Small improvements in wizards (order of buttons)
        PRODUCT: Remove packaging info from supplierinfo
        PROJECT: Better task view (moved unused fields to other tab)
        SALE: Keep formating for sale order lines' notes in the sale order report

    Bugfixes:
        KERNEL: Fixed bug which caused field names with non ascii chars didn't work
                in list mode on Windows
        KERNEL: Fix concurrency issue with UpdatableStr with the use of 
                threading.local
        KERNEL: Removed browse_record __unicode__ method... It made the sale order
                report crash when using product names with non ASCII characters
        KERNEL: Fixed bug which caused the translation export to fail when the server 
                was not launched from the directory its source is.
        BASE: Updating a menuitem now takes care its parent menus
        BASE: Fixed a cursor locking issue with updates
        BASE: Fixed viewing sequence types as a tree/list
        HR: Month field needs to be required in the "hours spent" report
        PURCHASE: fixed group purchase order wizard:
         - if there were orders from several different suppliers, it created a purchase
           order for only the first supplier but canceled other orders, even those which
           weren't merged in the created order (closes bugzilla #236)
         - doesn't trash "manual" lines (ie lines with no product)
         - pay attentions to unit factors when adding several lines together
        MRP: fixed workcenter load report (prints only the selected workcenters) and 
             does't crash if the user didn't select all workcenters
        
    Miscellaneous:
        Removed pydot from required dependencies

------------------------------------------------------------------------

Server 3.3.0-rc1
================

Changelog for Users
-------------------

New module: OS Commerce
    Integration with Tiny ERP and OS Commerce
    Synchronisation 100% automated with eSale;
        Import of categories of products
        Export of products (with photos support)
        Import of Orders (with the eslae module)
        Export of stock level
        Import of OSCommerce Taxes
    Multiple shop allowed with different rules/products
    Simple Installation

New Module: HR_TIMESHEET
    Management by affair, timesheets creates analytic entries in the
    accounting to get costs and revenue of each affairs. Affairs are
    structured in trees.

New Module: Account Follow Up
    Multi-Level and configurable Follows ups for the accounting module

New module; Productivity Analysis of users
    A module to compare productivity of users of Tiny ERP
    Generic module, you can compare everything (sales, products, partners,
    ...)

New Modules for localisations:
    Accounting localisations for be, ca, fr, de, ch, sw
    Fix: corrected encoding (latin1 to utf8) of Swedish account tree XML file

New Module - Sandwich
    Allows employees to order the lunch
    Keeps employees preferences

New Module TOOLS:
    Email automatic importation/integration in the ERP

New Module EDI:
    Import of EDI sale orders
    Export of shippings

Multi-Company:
    Tiny ERP is now fully multi-company !
    New Company and configuration can be made in the client side.

ACCOUNTING:
    Better Entries > Standard Entries (Editable Tree, like in Excel)
        Automatic creation of lines
    Journal centralised or not
        Counterpart of lines in one line or one counterpart per entry
    Analytic accounting recoded from scratch
        5 new reports
        Completly integrated with:
            production,
            hr_timesheet > Management by affairs
            sales & purchases,
            Tasks.
    Added unreconciliation functionnalities
    Added account tree fast rendering
    Better tax computation system supporting worldwide specific countries
    Better subscription system
    Wizard to close a period
    Wizard to clase a fiscal year
    Very powerfull, simple and complete multi-currency system
        in pricelists, sale order, purchases, ...
    Added required fields in currencies (currency code)
    Added decimal support
    Better search on accounts (on code, shortcut or name)
    Added constraint;
        on users
        on group
        on accounts in a journal
    added menuitem for automatic reconciliation; Multi-Levels
    added factor to analytic units
    added form view for budget items dotations
    made number of digits in quantity field of the budget spread wizard coherent with the object field
    fixed journal on purchase invoices/refunds (SugarCRM #6)
    Better bank statement reconciliation
    Fixed some reports

STOCK:
    Better view for location (using localisation of locations; posx, posy, posz)

MARKETING:
    fixed small bug when a partner has no adress
    state field of marketing partner set as readonly
    fixed marketing steps form view
    better history view
    disabled completely send sms wizard
    fixed send email wizard
    good priority -> high priority
    fixed 'call again later' button

NETWORK:
    added tree view for login/password

HR:
    added holiday_status (=type of ...) to expense claim form view

BASE (partner):
    fixed email_send and _email_send methods
    removed partner without addresses from demo data
    Added a date field in the partner form

MRP:
    New report: workcenter futur loads
    Analytic entries when production done.
    SCHEDULER: better error msg in the generated request
    Allows services in BoMs (for eg, subcontracting)

Project/Service Management:
    create orders from tasks; bugfixes
    Completly integrated with the rest of the ERP
        Services can now be MTO/MTS, Buy (subcontracting), produce (task), ...
        Services can be used anywhere (sale.order, bom, ...)
    See this graph;
        http://tiny.be/download/flux/flux_procurement.png
    tasks sorted by ... AND id, so that the order is not random
    within a priority

Automatic translations of all wizards

Scrum Project Management
    Better Ergonomy; click on a sprint to view tasks
    Planned, Effetive hours and progress in backlog, project and sprint
    Better Burndown Chart computation
    Better (simpler) view of tasks

Better demo Data
    In All modules, eth converted to english

PRODUCT:
    computing the weight of the packaging
    Added last order date
    Alternative suppliers (with delay, prefs, ...) for one product

PRICELISTS:
    much more powerfull system
    views simplified
    one pricelist per usage: sale, order, pvc
    price_type on product_view
    Multi-Currency pricelist (EUR pricelist can depend on a $ one)

HR-TIMESHEET: fixed bugs in hours report:
    sum all lines for the same day instead of displaying only the first one
    it now uses the analytic unit factor, so that mixing hours and days has some sense
    close cursor

SALE:
    invoices generated from a sale order are pre-computed (taxes are computed)

    new invoicing functionnality;
        invoice on order quantities or,
        invoice on shipped quantities

    Invoice on a sale.order or a sale.order.line

    added default value for uos_qty in sale order lines (default to 1)


Changelog for Developers
------------------------

New option --debug, that opens a python interpreter when an exception
occurs on the server side.

Better wizard system. Arguements self, cr, uid, context are passed in all
functions of the wizard like normal objects. All wizards converted.

Speed improvements in many views; partners, sale.order, ...
    less requests from client to server when opening a form

Better translation system, wizard terms are exported.

Script to render module dependency graph

KERNEL+ALL: pass context to methods computing a selection.

Modification for actions and view definitions:
    Actions Window:
        New field: view_mode = 'tree,form' or 'form,tree' -> default='form,tree'
        New role of view_type: tree (with shortcuts), form (others with switch button)
    If you need a form that opens in list mode:
        view_mode = 'tree,form' or 'tree'
        view_type = form
    You can define a view in a view (for example sale.order.line in
    sale.order)
        less requests on the client side, no need to define 2 views

Better command-line option message

Fixed bug which prevented to search for names using non ASCII
chars in many2one or many2many fields

Report Engine: bugfix for concurrency

Support of SQL constraints
    Uniq, check, ...
    Good error message in the client side (check an account entry with
    credit and debit >0)

Fixed: when an exception was raised, the cursor wasn't closed and this
could cause a freeze in some cases

Sequence can contains code: %(year)s, ... for prefix, suffix
    EX: ORDER %(year)/0005

Bugfixes for automatic migration system

bugfix on default value with creation of inherits

Improvement in report_sxw; you can redefine preprocess to do some
preprocessing before printing

Barcode support enabled by default

Fixed OpenOffice reports when the server is not launched from the
directory the code reside

Print workflow use a pipe instead of using a temporary file (now workflows
works on Windows Servers)

Inheritancy improved (multiple arguments: replace, inside, after, before)

Lots of small bugfixes

