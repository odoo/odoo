odoo.define('account.tour_bank_statement_reconciliation', function(require) {
'use strict';

var core = require('web.core');
var rpc = require('web.rpc');
var Tour = require('web_tour.tour');

Tour.register('bank_statement_reconciliation', {
        test: true,
        // Go to the reconciliation page of the statement: "BNK/2014/001"
    }, [
        // Reconciliation of 'INV/2018/0002'
        // Click on reconcile (matching done automatically by the reconciliation rule).

        {
            content: "reconcile the line",
            trigger: '.o_reconciliation_line:nth-child(1) .o_reconcile:visible',
        },

        // Reconciliation of 'First 2000 $ of INV/2018/0001'
        // Make a partial reconciliation

        {
            content: "open the last line in match mode to test the partial reconciliation",
            extra_trigger: '.o_reconciliation_line:first[data-mode="match"]',
            trigger: '.o_reconciliation_line .cell_label:contains("First 2000 $ of"):contains("/0001"):last'
        },
        {
            content: "click on partial reconcile",
            trigger: '.o_reconciliation_line:contains("First 2000 $ of"):contains("/0001"):last .accounting_view .do_partial_reconcile_true'
        },
        {
            content: "reconcile the line",
            trigger: '.o_reconciliation_line:contains("First 2000 $ of"):contains("/0001"):last .o_reconcile:visible',
        },

        // Reconciliation of 'Prepayment'
        // Test changing the partner

        {
            content: "change the partner of the second line",
            trigger: '.o_reconciliation_line:nth-child(2) .o_field_many2one input',
            run: 'text Deco'
        },
        {
            content: "select Deco Addict ",
            extra_trigger: '.ui-autocomplete:visible li:eq(1):contains(Create "Deco")',
            trigger: '.ui-autocomplete:visible li:contains(Deco Addict)',
        },
        {
            content: "use filter",
            trigger: '.o_reconciliation_line:nth-child(2) .match .match_controls .filter',
            run: 'text 4610'
        },
        {
            content: "select a line linked to Deco Addict ",
            trigger: ".o_reconciliation_line:nth-child(2) .match .line_info_button[data-content*='Deco Addict']"
        },
        {
            content: "deselect the line",
            trigger: '.o_reconciliation_line:nth-child(2) .accounting_view tbody .cell_label:first',
            run: function() {
                    $('.o_reconciliation_line:nth-child(2) .accounting_view tbody .cell_label:first').trigger('click');
            }
        },
        {
            content: "create a write-off",
            extra_trigger: '.o_reconciliation_line:nth-child(2) .accounting_view tbody:not(:has(.cell_label))',
            trigger: '.o_reconciliation_line:nth-child(2) .accounting_view tfoot .cell_label'
        },
        {
            content: "enter an account",
            trigger: '.o_reconciliation_line:nth-child(2) .o_field_many2one[name="account_id"] input',
            run: 'text 100000'
        },
        {
            content: "select the first account",
            extra_trigger: '.ui-autocomplete:visible li:eq(1):contains(Create "100000")',
            trigger: '.ui-autocomplete:visible li:contains(100000)',
        },
        {
            content: "reconcile the line with the write-off",
            trigger: '.o_reconciliation_line:nth-child(2) .o_reconcile:visible',
        },
    ]
);

});
