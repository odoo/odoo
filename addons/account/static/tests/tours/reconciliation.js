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
            content: "open the 4th line in match_rp mode to test the partial reconciliation",
            extra_trigger: '.o_reconciliation_line:first[data-mode="match_rp"]',
            trigger: '.o_reconciliation_line:nth-child(4) .cell_label:contains("First")'
        },
        {
            content: "select the right line to match",
            trigger: '.o_reconciliation_line:nth-child(4) .o_notebook .cell_label:contains("2019/0001")'
        },
        {
            content: "click on partial reconcile",
            trigger: '.o_reconciliation_line:nth-child(4) .accounting_view .edit_amount',
        },
        {
            content: "Edit amount",
            trigger: '.o_reconciliation_line:nth-child(4) .accounting_view .edit_amount_input:not(.d-none)',
            run: 'text 2000'
        },
        {
            content: "Press enter to validate amount",
            trigger: '.o_reconciliation_line:nth-child(4) .accounting_view .edit_amount_input:not(.d-none)',
            run: 'keydown 13'  // requires focus
        },
        {
            content: "Check that amount has changed",
            trigger: '.o_reconciliation_line:nth-child(4) .accounting_view .line_amount:contains("2,000.00")'
        },
        {
            content: "reconcile the line",
            trigger: '.o_reconciliation_line:nth-child(4) .o_reconcile:visible',
        },

        // Reconciliation of 'Prepayment'
        // Test changing the partner

        {
            content: "change the partner of the second line",
            trigger: '.o_reconciliation_line:nth-child(2) .o_field_many2one[name="partner_id"] input',
            run: 'text Deco'
        },
        {
            content: "select Deco Addict ",
            extra_trigger: '.ui-autocomplete:visible li:eq(1):contains(Create "Deco")',
            trigger: '.ui-autocomplete:visible li:contains(Deco Addict)',
        },
        {
            content: "use filter",
            trigger: '.o_reconciliation_line:nth-child(1) .match .match_controls .filter',
            run: 'text 4610'
        },
        {
            content: "select a line linked to Deco Addict ",
            extra_trigger: ".o_reconciliation_line:nth-child(1) .match .line_info_button:last[data-content*='4,610']",
            trigger: ".o_reconciliation_line:nth-child(1) .match .line_info_button[data-content*='Deco Addict']"
        },
        {
            content: "deselect the line",
            trigger: '.o_reconciliation_line:nth-child(1) .accounting_view tbody .cell_label:first',
            run: function() {
                    $('.o_reconciliation_line:nth-child(1) .accounting_view tbody .cell_label:first').trigger('click');
            }
        },
        {
            content: "create a write-off",
            extra_trigger: '.o_reconciliation_line:nth-child(2) .accounting_view tfoot .cell_left:visible:contains(32.58)',
            trigger: '.o_reconciliation_line:nth-child(2) .o_notebook .nav-link[href*="notebook_page_create"]'
        },
        {
            content: "enter an account",
            trigger: '.o_reconciliation_line:nth-child(2) .o_field_many2one[name="account_id"] input',
            run: 'text 151000'
        },
        {
            content: "select the first account",
            trigger: '.ui-autocomplete:visible li:last:contains(151000)',
        },
        {
            content: "reconcile the line with the write-off",
            trigger: '.o_reconciliation_line:nth-child(2) .o_reconcile:visible',
        },

        // Be done
        {
            content: "check the number off validate lines",
            trigger: '.o_control_panel .progress-reconciliation:contains(3 / 6)'
        },
    ]
);

});
