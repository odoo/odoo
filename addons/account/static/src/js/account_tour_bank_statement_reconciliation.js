(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id: 'bank_statement_reconciliation',
        name: _t("Reconcile the demo bank statement"),
        path: '/web',
        mode: 'test',
        // TODO : identify menu by data-menu attr or text node ?
        steps: [
            // Go to the first statement reconciliation
            {
                title:     "go to accounting",
                element:   '.oe_menu_toggler:contains("Accounting"):visible',
            },
            {
                title:     "go to bank statements",
                element:   '.oe_menu_leaf:contains("Bank Statement"):visible',
            },
            {
                title:     "select first bank statement",
                element:   '.oe_list_content tbody tr:contains("BNK/2014/001")',
            },
            {
                title:     "click the reconcile button",
                element:   '.oe_form_container header button:contains("Reconcile")',
            },

            
            // Check mutual exclusion of move lines
            {
                title:      "set second reconciliation in match mode",
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .initial_line'
            },
            {
                title:      "deselect SAJ/2014/002 from second reconciliation",
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line:contains("SAJ/2014/002")'
            },
            {
                title:      "check it appeared in first reconciliation's matches list and select SAJ/2014/002 in second reconciliation",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line:contains("SAJ/2014/002")',
                waitFor:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/002")',
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .mv_line:contains("SAJ/2014/002")'
            },


            // Make a partial reconciliation
            {
                title:      "select SAJ/2014/001",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/001")'
            },
            {
                title:      "click on the partial reconciliation button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/001") .do_partial_reconcile_button'
            },
            {
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
            },


            // Test changing the partner
            {
                title:      "change the partner (1)",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(4)', // wait for the reconciliation to be processed
                element:    '.oe_bank_statement_reconciliation_line:first-child .partner_name'
            },
            {
                title:      "change the partner (2)",
                element:    '.oe_bank_statement_reconciliation_line:first-child .change_partner_container input',
                sampleText: 'Vauxoo',
            },
            {
                title:      "change the partner (3)",
                element:    '.ui-autocomplete .ui-menu-item:contains("Vauxoo")'
            },
            {
                title:      "check the reconciliation is reloaded and has no match",
                element:    '.oe_bank_statement_reconciliation_line:first-child.no_match',
            },
            {
                title:      "change the partner back (1)",
                element:    '.oe_bank_statement_reconciliation_line:first-child .partner_name'
            },
            {
                title:      "change the partner back (2)",
                element:    '.oe_bank_statement_reconciliation_line:first-child .change_partner_container input',
                sampleText: 'Best Designers',
            },
            {
                title:      "change the partner back (3)",
                element:    '.ui-autocomplete .ui-menu-item:contains("Best Designers")'
            },
            {
                title:      "select SAJ/2014/002",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/002")'
            },
            {
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
            },


            // Create a new move line in first reconciliation and validate it
            {
                title:      "check following reconciliation passes in mode create",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(3)', // wait for the reconciliation to be processed
                element:    '.oe_bank_statement_reconciliation_line:first-child[data-mode="create"]'
            },
            {
                title:      "click the Profit/Loss preset",
                element:    '.oe_bank_statement_reconciliation_line:first-child button:contains("Profit / Loss")'
            },
            {
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
            },


            // Leave an open balance
            {
                title:      "select SAJ/2014/003",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(2)', // wait for the reconciliation to be processed
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/003")'
            },
            {
                title:      "click on the Keep Open button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok:not(.oe_highlight)'
            },


            // Be done
            {
                title:      "check 'finish screen' and close the statement",
                waitFor:    '.done_message',
                element:    '.button_close_statement'
            },
            {
                title:      "check the statement is closed",
                element:    '.oe_form_container header .label:contains("Closed")'
            },
        ]
    });

}());
