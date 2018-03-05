odoo.define('account.tour_bank_statement_reconciliation', function(require) {
'use strict';

var core = require('web.core');
var rpc = require('web.rpc');
var Tour = require('web_tour.tour');

Tour.register('bank_statement_reconciliation', {
        test: true,
        // Go to the reconciliation page of the statement: "BNK/2014/001"
    }, [
        {
            content: "wait web client",
            extra_trigger: 'body:not(:has(.o_reconciliation))',
            trigger: '.o_web_client',
            run: function () {
                console.log("looking for 'bank_statement_reconciliation' url");
                rpc.query({
                    model: 'account.bank.statement',
                    method: 'search',
                    args: [[['name', '=', 'BNK/2014/001']]], // account in l10n_generic_coa
                }).then(function(ids) {
                    var path  = "/web#statement_ids=" + ids[0] + "&action=bank_statement_reconciliation_view";
                    console.log("'bank_statement_reconciliation' url is: '" + path + "'");
                    window.location.href = path;
                }).fail(function () {
                    throw new Error("'account.bank.statement' named 'BNK/2014/001' not found");
                });
            },
            timeout: 5000
        },
        {
            content: "wait reconciliation page",
            trigger: '.o_reconciliation',
            run: function () {},
        },

        // open a line and reconcile a line proposed by the server

        {
            content: "open the last line in match mode to test the reconcile button",
            extra_trigger: '.o_reconciliation_line:last .o_reconcile:visible',
            trigger: '.o_reconciliation_line:last .accounting_view thead .cell_label:contains("/002")',
        },
        {
            content: "deselect the proposed line",
            extra_trigger: '.o_reconciliation_line:last[data-mode="match"]',
            trigger: '.o_reconciliation_line:last .accounting_view .cell_label:contains("/0002")'
        },
        {
            content: "re-select the line",
            extra_trigger: '.o_reconciliation_line:last .o_no_valid:visible', // the user can't validate the line and display the write-off line
            trigger: '.o_reconciliation_line:last .match .cell_label:contains("INV"):contains("/0002")'
        },
        {
            content: "reconcile the line",
            trigger: '.o_reconciliation_line:last .o_reconcile:visible',
        },

        // Make a partial reconciliation

        {
            content: "open the last line in match mode to test the partial reconciliation",
            extra_trigger: '.o_reconciliation_line:first[data-mode="match"]',
            trigger: '.o_reconciliation_line:last .cell_label:contains("First")'
        },
        {
            content: "select a line with with a higher amount",
            trigger: '.o_reconciliation_line:last .match .cell_right:contains($ 4,610.00)'
        },
        {
            content: "click on partial reconcile",
            trigger: '.o_reconciliation_line:last .accounting_view .do_partial_reconcile_true'
        },
        {
            content: "reconcile the line",
            trigger: '.o_reconciliation_line:last .o_reconcile:visible',
        },

        // Test changing the partner

        {
            content: "change the partner of the second line",
            trigger: '.o_reconciliation_line:nth-child(2) .o_field_many2one input',
            run: 'text Agro'
        },
        {
            content: "select Agrolait",
            extra_trigger: '.ui-autocomplete:visible li:eq(1):contains(Create "Agro")',
            trigger: '.ui-autocomplete:visible li:contains(Agrolait)',
        },
        {
            content: "use filter",
            extra_trigger: '.o_reconciliation_line:nth-child(2) .match:not(:has(tr:eq(2))) tr:eq(1)',
            trigger: '.o_reconciliation_line:nth-child(2) .match .match_controls .filter',
            run: 'text 4610'
        },
        {
            content: "select a line linked to Agrolait",
            extra_trigger: '.o_reconciliation_line:nth-child(2) .match:not(:has(tr:eq(1)))',
            trigger: '.o_reconciliation_line:nth-child(2) .match .line_info_button[data-content*=Agrolait]'
        },
        {
            content: "deselect the line",
            trigger: '.o_reconciliation_line:nth-child(2) .accounting_view tbody .cell_label:first'
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

        // Be done
        {
            content: "check the number off validate lines",
            trigger: '.o_reconciliation .progress-text:contains(3 / 5)'
        },
    ]
);

});
