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
                element:   '.oe_menu_toggler[data-menu="134"]',
            },
            {
                title:     "go to bank statements",
                element:   '.oe_menu_leaf[data-menu="176"]',
            },
            {
                title:     "select first bank statement",
                element:   '.oe_list_content tbody tr:first-child',
            },
            {
                title:     "click the reconcile button",
                element:   '.oe_form_container header button:contains("Reconcile")',
            },


            // Make a partial reconciliation
            {
                title:      "deselect SAJ/2014/005",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line[data-lineid="15"]'
            },
            {
                title:      "select SAJ/2014/001",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line[data-lineid="3"]'
            },
            {
                title:      "click on the partial reconciliation button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line[data-lineid="3"] .do_partial_reconcile_button'
            },
            {
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
            },


            // Test changing the partner
            {
                title:      "change the partner (1)",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(4)', // wait for the first reconciliation to be processed
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
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
            },


            {
                title:      "check following reconciliation passes in mode match",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(3)', // wait for the first reconciliation to be processed
                element:    '.oe_bank_statement_reconciliation_line:first-child[data-mode="match"]'
            },


            // Check mutual exclusion of move lines
            {
                title:      "deselect SAJ/2014/003 from second reconciliation",
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line[data-lineid="9"]'
            },
            {
                title:      "check it appeared in first reconciliation's matches list and select SAJ/2014/003 in second reconciliation",
                waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line[data-lineid="9"]',
                waitFor:    '.oe_bank_statement_reconciliation_line:first-child .match .mv_line[data-lineid="9"]',
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .match .mv_line[data-lineid="9"]'
            },
            {
                title:      "check SAJ/2014/003 disappeared in first reconciliation, second is in mode no-match and validate it",
                waitNot:    '.oe_bank_statement_reconciliation_line:first-child .mv_line[data-lineid="9"]',
                waitFor:    '.oe_bank_statement_reconciliation_line:nth-child(2).no_match',
                element:    '.oe_bank_statement_reconciliation_line:nth-child(2) .button_ok.oe_highlight'
            },


            // Create a new move line in first reconciliation and validate it
            {
                title:      "set first reconciliation in create mode",
                element:    '.oe_bank_statement_reconciliation_line:first-child .line_open_balance'
            },
            {
                title:      "click the Profit/Loss preset",
                element:    '.oe_bank_statement_reconciliation_line:first-child button:contains("Profit / Loss")'
            },
            {
                title:      "click on the OK button",
                element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
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
