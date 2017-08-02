odoo.define('sale.reconciliation_tests.data', function (require) {
"use strict";

var demoData = require('account.reconciliation_tests.data');


demoData.params.data['ir.model.data'] = {
    fields: {},
    xmlid_to_res_id: function () {
        return $.when(1);
    }
};
demoData.params.data['sale.order'] = {
    fields: {
        id: {string: "ID", type: 'integer'},
        name: {string: "Name", type: 'char'},
        partner_id: {string: 'Partner', type: 'many2one', relation: 'res.partner'},
        client_order_ref: {string: "Ref", type: 'char'},
        amount_total: {string: "Total", type: 'float'},
        currency_id: {string: "Currency", type: 'integer'},
        state: {string: "State", type: "selection", selection: [
                ['draft', 'Quotation'],
                ['sent', 'Quotation Sent'],
                ['sale', 'Sales Order'],
                ['done', 'Locked'],
                ['cancel', 'Cancelled'],
            ]},
        invoice_ids: {string: 'Partner', type: 'one2many', relation: 'account.invoice'},
        invoice_status: {string: "Invoice Status", type: "selection", selection: [
                ['upselling', 'Upselling Opportunity'],
                ['invoiced', 'Fully Invoiced'],
                ['to invoice', 'To Invoice'],
                ['no', 'Nothing to Invoice'],
            ]},
    },
    records: [
        {id: 1, name: 'name_1', partner_id: 8, client_order_ref: 'ref_1', amount_total: 100, state: 'sent', invoice_status: 'no', currency_id: 3},
        {id: 2, name: 'name_2', partner_id: 12, client_order_ref: 'ref_2', amount_total: 1175, state: 'sent', invoice_status: 'no', currency_id: 3},
        {id: 3, name: 'name_3', partner_id: 1, client_order_ref: 'ref_3', amount_total: 200, state: 'sent', invoice_status: 'no', currency_id: 3},
        {id: 4, name: 'name_4', partner_id: 8, client_order_ref: 'ref_4', amount_total: 300, state: 'draft', invoice_status: 'no', currency_id: 3},
        {id: 5, name: 'name_5', partner_id: 8, client_order_ref: 'ref_5', amount_total: 400, state: 'sale', invoice_status: 'no', currency_id: 3},
        {id: 6, name: 'name_6', partner_id: 8, client_order_ref: 'ref_6', amount_total: 500, state: 'cancel', invoice_status: 'no', currency_id: 3},
    ],
    action_confirm: function () {
        demoData.current.data['sale.order'].records[1].state = 'sale';
    },
};

demoData.params.data['sale.advance.payment.inv'] = {
    fields: {
        id: {string: "ID", type: 'integer'},
        count: {string: "count", type: 'integer', default: 1},
        advance_payment_method: {string: "payment method", type: 'selection', selection: [
            ['delivered', 'Invoiceable lines'],
            ['all', 'Invoiceable lines (deduct down payments)'],
            ['percentage', 'Down payment (percentage)'],
            ['fixed', 'Down payment (fixed amount)']
        ], default: 'all'},
        product_id: {string: 'product_id', type: 'many2one', relation: 'product.product'},
        amount: {string: "amount", type: 'float'},
        deposit_account_id: {string: "deposit_account_id", type: 'many2one', relation: 'account.account'},
        deposit_taxes_id: {string: "deposit_taxes_id", type: 'many2one', relation: 'account.tax'},
    },
    records: [
    ],
    create_invoices: function () {
        demoData.current.data['sale.order'].records[1].invoice_status = 'invoiced';
        return $.Deferred().resolve({'type': 'ir.actions.act_window_close'});
    },
};

demoData.params.data['account.reconciliation'].reconciliation_create_move_lines_propositions = function () {
    return $.Deferred().resolve([
        {
            'account_type': "receivable",
            'amount_currency_str': "",
            'currency_id': false,
            'date_maturity': "2017-02-07",
            'date': "2017-01-08",
            'total_amount_str': "$ 1175.00",
            'partner_id': 12,
            'account_name': "Account Receivable",
            'name': "INV for SO 2",
            'partner_name': "Camptocamp",
            'total_amount_currency_str': "",
            'id': 133,
            'credit': 0.0,
            'journal_id': [1, "Customer Invoices"],
            'amount_str': "$ 1175.00",
            'debit': 1175,
            'account_id': [287, "101200 Account Receivable"],
            'account_code': "101200",
            'ref': "",
            'already_paid': false
        },
    ]);
};

demoData.params.data_widget[0].order_ids = [1,5];
demoData.params.data_widget[1].order_ids = [1,2,5];
demoData.params.data_widget[2].order_ids = [2];
demoData.params.data_widget[3].order_ids = [2];

});


odoo.define('sale.reconciliation_tests', function (require) {
"use strict";

var ReconciliationClientAction = require('account.ReconciliationClientAction');
var demoData = require('account.reconciliation_tests.data');
var testUtils = require('web.test_utils');

QUnit.module('sale', {
    beforeEach: function () {
        this.params = demoData.getParams();
    }
}, function () {
    QUnit.module('Reconciliation');

    QUnit.test('Reconciliation change partner', function (assert) {
        assert.expect(21);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            archs: {
                'sale.order,1,list':
                    '<tree string="Sales Orders">'+
                        '<field name="name" string="Order Number"/>'+
                        '<field name="client_order_ref" string="Reference"/>'+
                        '<field name="partner_id"/>'+
                        '<field name="amount_total" sum="Total Tax Included" widget="monetary"/>'+
                        '<field name="currency_id" invisible="1"/>'+
                        '<field name="state"/>'+
                    '</tree>',
                'sale.order,1,search':
                    '<search string="Search Sales Order">'+
                        '<field name="name" string="Sales Order" filter_domain="[\'|\',(\'name\',\'ilike\',self),(\'client_order_ref\',\'ilike\',self)]"/>'+
                        '<field name="partner_id" operator="child_of"/>'+
                        '<field name="amount_total" filter_domain="[\'|\',(\'amount_total\',\'ilike\',self),(\'amount_untaxed\',\'ilike\',self)]"/>'+
                        '<group expand="0" string="Group By">'+
                            '<filter name="groupby_partner_id" context="{\'group_by\' : \'partner_id\'}" string="Customer"/>'+
                        '</group>'+
                   '</search>',
                'sale.advance.payment.inv,false,form':
                    '<form string="Invoice Sales Order">'+
                        '<p class="oe_grey">'+
                            'Invoices will be created in draft so that you can review '+
                            'them before validation.'+
                        '</p>'+
                        '<group>'+
                            '<field name="count" invisible="[(\'count\',\'=\',1)]" readonly="True"/>'+
                            '<field name="advance_payment_method" class="oe_inline" widget="radio" attrs="{\'invisible\': [(\'count\',\'&gt;\',1)]}"/>'+
                            '<field name="product_id"'+
                                ' context="{\'search_default_services\': 1, \'default_type\': \'service\', \'default_invoice_policy\': \'order\'}" class="oe_inline"'+
                                ' invisible="1"/>'+
                            '<label for="amount" attrs="{\'invisible\': [(\'advance_payment_method\', \'not in\', (\'fixed\',\'percentage\'))]}"/>'+
                            '<div attrs="{\'invisible\': [(\'advance_payment_method\', \'not in\', (\'fixed\',\'percentage\'))]}">'+
                                '<field name="amount"'+
                                    ' attrs="{\'required\': [(\'advance_payment_method\', \'in\', (\'fixed\',\'percentage\'))]}" class="oe_inline" widget="monetary"/>'+
                                '<label string="%"'+
                                    ' attrs="{\'invisible\': [(\'advance_payment_method\', \'!=\', \'percentage\')]}" class="oe_inline"/>'+
                            '</div>'+
                            '<field name="deposit_account_id" class="oe_inline"'+
                                ' attrs="{\'invisible\': [\'|\', (\'advance_payment_method\', \'not in\', (\'fixed\', \'percentage\')), (\'product_id\', \'!=\', False)]}" groups="account.group_account_manager"/>'+
                            '<field name="deposit_taxes_id" class="oe_inline" widget="many2many_tags"'+
                                ' domain="[(\'type_tax_use\',\'=\',\'sale\')]"'+
                                ' attrs="{\'invisible\': [\'|\', (\'advance_payment_method\', \'not in\', (\'fixed\', \'percentage\')), (\'product_id\', \'!=\', False)]}"/>'+
                        '</group>'+
                        '<footer>'+
                            '<button name="create_invoices" string="Create and View Invoices" type="object"'+
                                ' context="{\'open_invoices\': True}" class="btn-primary"/>'+
                            '<button name="create_invoices" string="Create Invoices" type="object"'+
                                ' class="btn-primary"/>'+
                            '<button string="Cancel" class="btn-default" special="cancel"/>'+
                        '</footer>'+
                    '</form>',
            },
        });

        clientAction.appendTo($('#qunit-fixture'));
        var widget = clientAction.widgets[0];
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Agrolait", "the partner many2one should display agrolait");
        assert.strictEqual(widget.$('.match table tr').length, 2, "agrolait should have 2 propositions for reconciliation");

        assert.strictEqual(widget.$('.o_reconcile_so:not(:hidden)').length, 1, "agrolait should have the 'Reconcile with sales order(s)' button");

        // Simulate changing partner
        widget.$('.o_input_dropdown input').trigger('focus').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(Camptocamp)').trigger('mouseenter').trigger('click');
        widget.$('.o_input_dropdown input').trigger('blur');
        clientAction._onAction({target: widget, name: 'change_partner', data: {data: {display_name: 'Camptocamp', id: 12}}, stopped: false});
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");
        assert.strictEqual(widget.$('.match table tr').length, 3, "camptocamp should have 3 propositions for reconciliation");

        assert.strictEqual(widget.$('.o_reconcile_so:not(:hidden)').length, 1, "Camptocamp should have the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[1].$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[2].$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[3].$('.o_reconcile_so:not(:hidden)').length, 1, "Should have the 'Reconcile with sales order(s)' button");

        // open the modal to reconcile with sale order
        widget.$('.o_reconcile_so').trigger('click');
        assert.strictEqual($('.modal td.o_list_record_selector').length, 0, "Camptocamp should not have any order line with the current filter");
        $('.modal .o_facet_remove').trigger('click');
        assert.strictEqual($('.modal td.o_list_record_selector').length, 1, "Camptocamp should have one order line with the current filter");

        // select a sale order
        $('.modal td.o_list_record_selector input').trigger('click');
        $('.modal .o_select_button').trigger('click');
        assert.strictEqual(widget.$('.o_reconciliation_blockui:not(.hidden)').length, 1, "Should display the line block ui");

        // cancel
        $('.modal:has(button:contains(Create)) .o_form_button_cancel').trigger('click');
        assert.strictEqual(widget.$('.o_reconciliation_blockui:not(.hidden)').length, 0, "Should hide the line block ui");
        assert.strictEqual(widget.$('.o_reconcile_so:not(:hidden)').length, 1, "Camptocamp should always have the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[1].$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[2].$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the 'Reconcile with sales order(s)' button");
        assert.strictEqual(clientAction.widgets[3].$('.o_reconcile_so:not(:hidden)').length, 1, "Should always have the 'Reconcile with sales order(s)' button");
        
        // open the modal to reconcile with sale order
        widget.$('.o_reconcile_so').trigger('click');
        $('.modal .o_facet_remove').trigger('click');
        $('.modal td.o_list_record_selector input').trigger('click');
        $('.modal .o_select_button').trigger('click');
        $('.modal .btn-primary').trigger('click');
        assert.strictEqual(widget.$('.accounting_view .mv_line').length, 1, "Should display the new proposition");
        assert.strictEqual(widget.$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the reconcile button");
        assert.strictEqual(widget.$('.o_reconcile:not(:hidden)').length, 1, "Should display the 'Reconcile' button");
        assert.strictEqual(clientAction.widgets[3].$('.o_reconcile_so:not(:hidden)').length, 0, "Should hide the 'Reconcile with sales order(s)' button");

        clientAction.destroy();
    });
});

});
