odoo.define('account.reconciliation_tests.data', function () {
"use strict";

/*
 * Debug tip:
 * To be able to "see" the test in the browser:
 *       var $body = $('body');
 *       $body.addClass('debug');
 *       clientAction.appendTo($body);
 */

var Datas = {};

var db = {
    'res.company': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
        },
        records: [
            {id: 1, display_name: "company 1"},
        ],
    },
    'res.partner': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
            image: {string: "image", type: 'integer'},
            customer: {string: "customer", type: 'boolean'},
            supplier: {string: "supplier", type: 'boolean'},
            parent_id: {string: "Parent", type: 'boolean'},
            property_account_receivable_id: {string: 'Account receivable', type: 'many2one', relation: 'account.account'},
            property_account_payable_id: {string: 'Account payable', type: 'many2one', relation: 'account.account'},
        },
        records: [
            {id: 1, display_name: "partner 1", image: 'AAA', customer: true},
            {id: 2, display_name: "partner 2", image: 'BBB', customer: true},
            {id: 3, display_name: "partner 3", image: 'CCC', customer: true},
            {id: 4, display_name: "partner 4", image: 'DDD', customer: true},
            {id: 8, display_name: "Agrolait", image: 'EEE', customer: true},
            {id: 12, display_name: "Camptocamp", image: 'FFF', supplier: true, property_account_receivable_id: 287, property_account_payable_id: 287},
            // add more to have 'Search More' option
            {id: 98, display_name: "partner 98", image: 'YYY', customer: true},
            {id: 99, display_name: "partner 99", image: 'ZZZ', customer: true},
        ],
        mark_as_reconciled: function () {
            return $.when();
        },
    },
    'account.account': {
        fields: {
            id: {string: "ID", type: 'integer'},
            code: {string: "code", type: 'integer'},
            name: {string: "Displayed name", type: 'char'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
        },
        records: [
            {id: 282, code: 100000, name: "100000 Fixed Asset Account", company_id: 1},
            {id: 283, code: 101000, name: "101000 Current Assets", company_id: 1},
            {id: 284, code: 101110, name: "101110 Stock Valuation Account", company_id: 1},
            {id: 285, code: 101120, name: "101120 Stock Interim Account (Received)", company_id: 1},
            {id: 286, code: 101130, name: "101130 Stock Interim Account (Delivered)", company_id: 1},
            {id: 287, code: 101200, name: "101200 Account Receivable", company_id: 1},
            {id: 288, code: 101300, name: "101300 Tax Paid", company_id: 1},
            {id: 308, code: 101401, name: "101401 Bank", company_id: 1},
            {id: 500, code: 500, name: "500 Account", company_id: 1},
            {id: 501, code: 501, name: "501 Account", company_id: 1},
            {id: 502, code: 502, name: "502 Account", company_id: 1},
            {id: 503, code: 503, name: "503 Account", company_id: 1},
            {id: 504, code: 504, name: "504 Account", company_id: 1},
        ],
        mark_as_reconciled: function () {
            return $.when();
        },
    },
    'account.tax': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
            amount: {string: "amout", type: 'float'},
            price_include: {string: "Included in Price", type: 'boolean'},
            account_id: {string: "partner", type: 'many2one', relation: 'account.account'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
            amount_type: {string: "type", type: 'selection'}
        },
        records: [
            {id: 6, display_name: "Tax 20.00%", amount: 20, amount_type: 'percent', price_include: false, company_id: 1},
            {id: 7, display_name: "Tax 10.00% include", amount: 10, amount_type: 'percent', price_include: true, account_id: 288, company_id: 1},
        ],
        json_friendly_compute_all: function (args) {
            var tax = _.find(db['account.tax'].records, {'id': args[0][0]});
            var amount = args[1];
            var tax_base = tax.price_include ? amount*100/(100+tax.amount) : amount;
            return $.when({
                "base": amount,
                "taxes": [{
                    'id': tax.id,
                    'amount': tax_base*tax.amount/100,
                    "base": tax_base,
                    'name': tax.display_name,
                    "analytic": false,
                    "refund_account_id": false,
                    'account_id': tax.account_id
                }],
                "total_excluded": amount/100*(100-tax.amount),
                "total_included": amount,
            });
        },
    },
    'account.journal': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
        },
        records: [
            {id: 8, display_name: "company 1 journal", company_id: 1}
        ]
    },
    'account.analytic.account': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
        },
        records: [
            {id: 16, display_name: "Administrative"},
            {id: 7, display_name: "Agrolait - Agrolait"},
            {id: 8, display_name: "Asustek - ASUSTeK"},
            {id: 15, display_name: "Camp to Camp - Camptocamp"},
            {id: 6, display_name: "CampToCamp - Camptocamp"},
            {id: 17, display_name: "Commercial & Marketing"},
            {id: 23, display_name: "Data Import/Export Plugin - Delta PC"},
            {id: 9, display_name: "Delta PC - Delta PC"},
        ]
    },
    'account.analytic.tag': {
        fields: {},
        records: []
    },
    'account.bank.statement': {
        fields: {},
    },
    'account.bank.statement.line': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
            partner_id: {string: "partner", type: 'many2one', relation: 'res.partner'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
        },
        records: [
            {id: 5, display_name: "SAJ/2014/002 and SAJ/2014/003", company_id: 1},
            {id: 6, display_name: "Bank fees", company_id: 1},
            {id: 7, display_name: "Prepayment", company_id: 1},
            {id: 8, display_name: "First 2000 \u20ac of SAJ/2014/001", company_id: 1},
        ],
    },
    'account.move.line': {
        fields: {},
    },
    'account.reconcile.model': {
        fields: {
            id: {string: "ID", type: 'integer'},
            name: {string: "Button Label", type: 'char'},
            rule_type: {string: "Type", type: 'selection', selection: [['writeoff_button', 'Create a Button'], ['writeoff_suggestion', 'Write off Suggestion'], ['invoice_matching', 'Invoice matching']], default:'writeoff_button'},
            has_second_line: {string: "Add a second line", type: 'boolean'},
            account_id: {string: "Account", type: 'many2one', relation:'account.account'},
            journal_id: {string: "Journal", type: 'many2one', relation:'account.journal'},
            label: {string: "Journal Item Label", type: 'char'},
            amount_type: {string: 'amount_type', type: 'selection', selection: [['fixed', 'Fixed'], ['percentage', 'Percentage of balance']], default:'percentage'},
            amount: {string: "Amount", type: 'float', digits:0, help:"Fixed amount will count as a debit if it is negative, as a credit if it is positive.", default:100.0},
            tax_id: {string: "Tax", type: 'many2one', relation:'account.tax', domain:[('type_tax_use', '=', 'purchase')]},
            analytic_account_id: {string: "Analytic Account", type: 'many2one', relation:'account.analytic.account'},
            second_account_id: {string: "Second Account", type: 'many2one', relation:'account.account', domain:[('deprecated', '=', false)]},
            second_journal_id: {string: "Second Journal", type: 'many2one', relation:'account.journal',  help:"This field is ignored in a bank statement reconciliation."},
            second_label: {string: "Second Journal Item Label", type: 'char'},
            second_amount_type: {string: "Second amount_type", type: 'selection', selection: [['fixed', 'Fixed'], ['percentage', 'Percentage of balance']], default:'percentage'},
            second_amount: {string: "Second Amount", type: 'float', digits:0, help:"Fixed amount will count as a debit if it is negative, as a credit if it is positive.", default:100.0},
            second_tax_id: {string: "Second Tax", type: 'many2one', relation:'account.tax', domain:[('type_tax_use', '=', 'purchase')]},
            second_analytic_account_id: {string: "Second Analytic Account", type: 'many2one', relation:'account.analytic.account'},
            match_journal_ids: {string: "Journal Ids", type: 'many2many', relation: 'account.journal'}
        },
        records: [
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 4, 'analytic_account_id': false, 'display_name': "Int\u00e9rrets", 'rule_type': 'writeoff_button', 'second_tax_id': false, 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 282, 'company_id': [1, "Demo SPRL"], 'tax_id': false, 'amount_type': "fixed", 'name': "Int\u00e9rrets", 'amount': 0.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 2, 'analytic_account_id': false, 'display_name': "Perte et Profit", 'rule_type': 'writeoff_button', 'second_tax_id': false, 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 283, 'company_id': [1, "Demo SPRL"], 'tax_id': false, 'amount_type': "percentage", 'name': "Perte et Profit", 'amount': 100.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 5, 'analytic_account_id': false, 'display_name': "Fs bank", 'rule_type': 'writeoff_button', 'second_tax_id': false, 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 284, 'company_id': [1, "Demo SPRL"], 'tax_id': false, 'amount_type': "percentage", 'name': "Fs bank", 'amount': 100.0, 'second_amount': 100.0},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 8, 'analytic_account_id': false, 'display_name': "Caisse Sand.", 'rule_type': 'writeoff_button', 'second_tax_id': false, 'has_second_line': false, 'journal_id': false, 'label': "Caisse Sand.", 'second_label': false, 'second_account_id': false, 'account_id': 308, 'company_id': [1, "Demo SPRL"], 'tax_id': false, 'amount_type': "percentage", 'name': "Caisse Sand.", 'amount': 100.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 3, 'analytic_account_id': false, 'display_name': "ATOS", 'rule_type': 'writeoff_button', 'second_tax_id': 7, 'has_second_line': true, 'journal_id': false, 'label': "ATOS Banque", 'second_label': "ATOS Frais", 'second_account_id': 286, 'account_id': 285, 'company_id': [1, "Demo SPRL"], 'tax_id': 6, 'amount_type': "percentage", 'name': "ATOS", 'amount': 97.5, 'second_amount': 2.5},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 10, 'analytic_account_id': false, 'display_name': "Double", 'rule_type': 'writeoff_button', 'second_tax_id': false, 'has_second_line': true, 'journal_id': false, 'label': "Double Banque", 'second_label': "Double Frais", 'second_account_id': 286, 'account_id': 285, 'company_id': [1, "Demo SPRL"], 'tax_id': false, 'amount_type': "percentage", 'name': "Double", 'amount': 97.5, 'second_amount': 2.5, 'match_journal_ids': []},
        ]
    },
    'account.reconciliation.widget': {
        fields: {},
        auto_reconcile: function () {
            return $.when(Datas.used.auto_reconciliation);
        },
        process_bank_statement_line: function (args) {
            var datas = args[1];
            var ids = _.flatten(_.pluck(_.pluck(datas, 'counterpart_aml_dicts'), 'counterpart_aml_id'));
            ids = ids.concat(_.flatten(_.pluck(datas, 'payment_aml_ids')));
            ids = _.compact(ids);

            for (var key in Datas.used.move_lines_for_manual_reconciliation) {
                Datas.used.move_lines_for_manual_reconciliation[key] = _.filter(Datas.used.move_lines_for_manual_reconciliation[key], function (mv_line) {
                    return ids.indexOf(mv_line.id) === -1;
                });
            }
            return $.when();
        },
        get_move_lines_for_bank_statement_line: function (args) {
            var partner_id = args.splice(1, 1)[0];
            var excluded_ids = args.splice(1, 1)[0];
            var key = JSON.stringify(args);
            if (!Datas.used.mv_lines[key]) {
                throw new Error("Unknown parameters for get_move_lines_for_bank_statement_line: '"+ key + "'");
            }
            var lines = Datas.used.mv_lines[key]
                .filter(function (line) {
                    return excluded_ids.indexOf(line.id) === -1 && (!partner_id || partner_id === line.partner_id);
                })
                .map(function (line, i, src) {
                    line.recs_count = src.length;
                    return line;
                })
                .slice(0, options.params.limitMoveLines);
            return $.when(lines);
        },
        get_bank_statement_line_data: function (args) {
            var ids = args[0];
            var results = {
                value_min: 0,
                value_max: ids.length,
                lines: _.filter(Datas.used.data_widget, function (w) {return _.contains(ids, w.st_line.id);})
            };
            return $.when(results);
        },
        get_bank_statement_data: function () {
            var results = Datas.used.data_preprocess;
            results.lines = _.filter(Datas.used.data_widget, function (w) {return _.contains(results.st_lines_ids, w.st_line.id);});
            return $.when(results);
        },
        get_move_lines_for_manual_reconciliation: function (args) {
            var excluded_ids = args.splice(2, 1)[0];
            var key = JSON.stringify(args);
            if (!Datas.used.move_lines_for_manual_reconciliation[key]) {
                throw new Error("Unknown parameters for get_move_lines_for_manual_reconciliation: '"+ key + "'");
            }
            var lines = Datas.used.move_lines_for_manual_reconciliation[key]
                .filter(function (line) {
                    return excluded_ids.indexOf(line.id) === -1;
                })
                .map(function (line, i, src) {
                    line.recs_count = src.length;
                    return line;
                })
                .slice(0, options.params.limitMoveLines);
            return $.when(lines);
        },
        get_all_data_for_manual_reconciliation: function (args) {
            var key = JSON.stringify(args);
            if (!Datas.used.data_for_manual_reconciliation_widget[key]) {
                throw new Error("Unknown parameters for get_all_data_for_manual_reconciliation: '"+ key + "'");
            }
            return $.when(Datas.used.data_for_manual_reconciliation_widget[key]);
        },
        process_move_lines: function (args) {
            var datas = args[0];
            for (var i in datas) {
                var data = datas[i];
                for (var key in Datas.used.move_lines_for_manual_reconciliation) {
                    Datas.used.move_lines_for_manual_reconciliation[key] = _.filter(Datas.used.move_lines_for_manual_reconciliation[key], function (mv_line) {
                        return data.mv_line_ids.indexOf(mv_line.id) === -1;
                    });
                }
            }
            return $.when();
        },
    }
};

var data_preprocess = {
    value_min: 0,
    value_max: 4,
    notifications: [],
    num_already_reconciled_lines: 0,
    st_lines_ids: [5, 6, 7, 8],
    statement_name: 'BNK/2014/001',
};

var data_widget = [
    {
        'st_line': {
            'currency_id': 3,
            'communication_partner_name': false,
            'open_balance_account_id': 287,
            'name': "SAJ/2014/002 and SAJ/2014/003",
            'partner_name': "Agrolait",
            'partner_id': 8,
            'has_no_partner': false,
            'journal_id': 84,
            'account_name': "Bank",
            'note': "",
            'amount': 1175.0,
            'amount_str': "$ 1,175.00",
            'amount_currency_str': "",
            'date': "2017-01-01",
            'account_code': "101401",
            'ref': "",
            'id': 5,
            'statement_id': 2,
            'company_id': 1,
        },
        'reconciliation_proposition': []
    },
    {
        'st_line': {
            'currency_id': 3,
            'communication_partner_name': false,
            'name': "Bank fees",
            'partner_name': false,
            'partner_id': false,
            'has_no_partner': true,
            'journal_id': 84,
            'account_name': "Bank",
            'note': "",
            'amount': -32.58,
            'amount_str': "$ 32.58",
            'amount_currency_str': "",
            'date': "2017-01-01",
            'account_code': "101401",
            'ref': "",
            'id': 6,
            'statement_id': 2,
            'company_id': 1,
        },
        'reconciliation_proposition': []
    },
    {
        'st_line': {
            'currency_id': 3,
            'communication_partner_name': false,
            'open_balance_account_id': 287,
            'name': "Prepayment",
            'partner_name': "Camptocamp",
            'partner_id': 12,
            'has_no_partner': false,
            'journal_id': 84,
            'account_name': "Bank",
            'note': "",
            'amount': 650.0,
            'amount_str': "$ 650.00",
            'amount_currency_str': "",
            'date': "2017-01-01",
            'account_code': "101401",
            'ref': "",
            'id': 7,
            'statement_id': 2,
            'company_id': 1,
        },
        'reconciliation_proposition': [
            {
                'account_type': "receivable",
                'amount_currency_str': "",
                'currency_id': false,
                'date_maturity': "2017-02-07",
                'date': "2017-01-08",
                'total_amount_str': "$ 650.00",
                'partner_id': 12,
                'account_name': "101200 Account Receivable",
                'name': "INV/2017/0012",
                'partner_name': "Camptocamp",
                'total_amount_currency_str': "",
                'id': 133,
                'credit': 0.0,
                'journal_id': [1, "Customer Invoices"],
                'amount_str': "$ 650.00",
                'debit': 650.0,
                'account_id': [287, "101200 Account Receivable"],
                'account_code': "101200",
                'ref': "",
                'already_paid': false
            },
        ]
    },
    {
        'st_line': {
            'currency_id': 3,
            'communication_partner_name': false,
            'open_balance_account_id': 285,
            'name': "First 2000 \u20ac of SAJ/2014/001",
            'partner_name': "Camptocamp",
            'partner_id': 12,
            'has_no_partner': false,
            'journal_id': 84,
            'account_name': "Bank",
            'note': "",
            'amount': 2000.0,
            'amount_str': "$ 2,000.00",
            'amount_currency_str': "",
            'date': "2017-01-01",
            'account_code': "101401",
            'ref': "",
            'id': 8,
            'statement_id': 2,
            'company_id': 1,
        },
        'reconciliation_proposition': []
    },
];

var mv_lines = {
    '[]': [],
    '[5,"",0,5]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 112, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 134, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_id': [284, "101110 Stock Valuation Account"], 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[5,"b",0,5]': [
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
    ],
    '[6,"",0,5]': [
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 376.00", 'partner_id': 7, 'account_name': "Bank", 'name': "BNK1/2017/0002: SUPP.OUT/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 392, 'credit': 376.0, 'journal_id': "Bank", 'amount_str': "$ 376.00", 'debit': 0.0, 'account_code': "101401", 'ref': "BILL/2017/0003", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-22", 'date': "2017-01-23", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
                {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-15", 'total_amount_str': "$ 5,749.99", 'partner_id': 7, 'account_name': "Account Payable", 'name': "BILL/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 117, 'credit': 5749.99, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 5,749.99", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[6,"",5,5]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-15", 'total_amount_str': "$ 5,749.99", 'partner_id': 7, 'account_name': "Account Payable", 'name': "BILL/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 117, 'credit': 5749.99, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 5,749.99", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[7,"",0,5]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 133, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_id': [284, "101110 Stock Valuation Account"], 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 376.00", 'partner_id': 7, 'account_name': "Bank", 'name': "BNK1/2017/0002: SUPP.OUT/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 392, 'credit': 376.0, 'journal_id': "Bank", 'amount_str': "$ 376.00", 'debit': 0.0, 'account_code': "101401", 'ref': "BILL/2017/0003", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-22", 'date': "2017-01-23", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
    ],
    '[7,"",0,6]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 133, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_id': [284, "101110 Stock Valuation Account"], 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 376.00", 'partner_id': 7, 'account_name': "Bank", 'name': "BNK1/2017/0002: SUPP.OUT/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 392, 'credit': 376.0, 'journal_id': "Bank", 'amount_str': "$ 376.00", 'debit': 0.0, 'account_code': "101401", 'ref': "BILL/2017/0003", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-22", 'date': "2017-01-23", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
    ],
    '[8,"",0,5]': [],
};

var auto_reconciliation = {
    'num_already_reconciled_lines': 1,
    'notifications': [{
        'message': "1 transaction was automatically reconciled.",
        'type': "info",
        'details': {
            'model': "account.move",
            'name': "Automatically reconciled items",
            'ids': [143]
        }
    }],
    'st_lines_ids': [5, 6, 8],
    'statement_name': false
};

var data_for_manual_reconciliation_widget = {
    '[null,null]': {
        'customers': [
            {'account_id': 287, 'partner_name': "Agrolait", 'reconciliation_proposition': [], 'currency_id': 3, 'max_date': "2017-02-14 12:30:31", 'last_time_entries_checked': null, 'account_code': "101200", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'mode': "customers"},
            {'account_id': 7, 'partner_name': "Camptocamp", 'reconciliation_proposition': [], 'currency_id': 3, 'max_date': "2017-02-13 14:24:55", 'last_time_entries_checked': null, 'account_code': "101200", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'mode': "customers"}
        ],
        'accounts': [
            {
                'account_id': 283, 'account_name': "101000 Current Assets", 'currency_id': 3, 'max_date': "2017-02-16 14:32:04", 'last_time_entries_checked': "2017-02-16", 'account_code': "101000", 'mode': "accounts",
                'reconciliation_proposition': [
                    {'account_id': 283, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-16", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "BNK1/2017/0006: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 1000.0, 'journal_id': [3, "Bank"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101000", 'ref': "", 'already_paid': false},
                    {'account_id': 283, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-18", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "INV/2017/0006", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 402, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 1000.0, 'account_code': "101000", 'ref': "", 'already_paid': false}
                ]
            }
        ],
        'suppliers': [
            {
                'account_id': 284, 'partner_name': "Agrolait",
                'reconciliation_proposition': [
                    {'account_id': 284, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-16", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "BNK1/999: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 999, 'credit': 1000.0, 'journal_id': [3, "Bank"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
                    {'account_id': 284, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-18", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "INV/998", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 998, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 1000.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
                ],
                'currency_id': 3, 'max_date': "2017-02-14 12:36:05", 'last_time_entries_checked': null, 'account_code': "111100", 'partner_id': 8, 'account_name': "Account Payable", 'mode': "suppliers"
            }, {
                'account_id': 284, 'partner_name': "Camptocamp",
                'reconciliation_proposition': [
                    {'account_id': 284, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-16", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 12, 'account_name': "101000 Current Assets", 'name': "BNK1/1999: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 1999, 'credit': 1000.0, 'journal_id': [3, "Bank"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
                    {'account_id': 284, 'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-18", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 12, 'account_name': "101000 Current Assets", 'name': "INV/1998", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 1998, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 1000.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
                ],
                'currency_id': 3, 'max_date': "2017-02-14 12:36:05", 'last_time_entries_checked': null, 'account_code': "111100", 'partner_id': 12, 'account_name': "Account Payable", 'mode': "suppliers"
            }
        ]
    },
    '["partner",null,"receivable"]': [
        {'account_id': 287, 'partner_name': "Agrolait", 'reconciliation_proposition': [], 'currency_id': 3, 'max_date': "2017-02-14 12:30:31", 'last_time_entries_checked': null, 'account_code': "101200", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'mode': "customers"},
        {'account_id': 287, 'partner_name': "Camptocamp", 'reconciliation_proposition': [], 'currency_id': 3, 'max_date': "2017-02-13 14:24:55", 'last_time_entries_checked': null, 'account_code': "101200", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'mode': "customers"}
    ]
};

var move_lines_for_manual_reconciliation = {
    '[287,8,"",0,5]': [
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "10,222.00 €", 'currency_id': 1, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [7, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 180.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 21, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 90.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0006: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 23, 'credit': 90.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 90.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-10", 'date': "2017-02-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 6, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1000.00", 'debit': 1000.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-10", 'date': "2017-02-08", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 9, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false}
    ],
    '[7,12,"",0,5]': [
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [7, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 100, 'amount_currency_str': "100.00 €", 'currency_id': 1, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 170.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 21, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 170.00", 'debit': 170.0, 'account_code': "101200", 'ref': "INV fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 100, 'amount_currency_str': "100.00 €", 'currency_id': 1, 'date_maturity': "2017-02-10", 'date': "2017-02-10", 'total_amount_str': "$ 180.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 22, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 170, 'amount_currency_str': "170.00 €", 'currency_id': 1, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 100.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 23, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101200", 'ref': "INV fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 180, 'amount_currency_str': "180.00 €", 'currency_id': 1, 'date_maturity': "2017-02-10", 'date': "2017-02-10", 'total_amount_str': "$ 100.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 24, 'credit': 100.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 100.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
    ],
    '[284,8,"",0,6]': [
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 180.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 21, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "111100", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
    ],
    '[283,null,"",0,5]': [
        {'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-16", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "BNK1/2017/0006: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 1000.0, 'journal_id': [3, "Bank"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101000", 'ref': "", 'already_paid': false},
        {'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-18", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "INV/2017/0006", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 402, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 1000.0, 'account_code': "101000", 'ref': "", 'already_paid': false}
    ],
    '[284,12,"",0,6]': [],
};

var session = {
    currencies: {
        3: {
            digits: [69, 2],
            position: "before",
            symbol: "$"
        }
    }
};

var options = {
    context: {
        statement_ids: [4]
    },
    params: {
        limitMoveLines: 5,
    },
};

Datas.params = {
    data: db,
    data_preprocess: data_preprocess,
    data_widget: data_widget,
    mv_lines: mv_lines,
    auto_reconciliation: auto_reconciliation,
    data_for_manual_reconciliation_widget: data_for_manual_reconciliation_widget,
    move_lines_for_manual_reconciliation: move_lines_for_manual_reconciliation,
    session: session,
    options: options,
};
    // this is the main function for this module. Its job is to export (and clone) all data for a test.
Datas.getParams = function () {
    return (this.used = $.extend(true, {}, this.params));
};
return Datas;
});

odoo.define('account.reconciliation_tests', function (require) {
"use strict";

var ReconciliationClientAction = require('account.ReconciliationClientAction');
var demoData = require('account.reconciliation_tests.data');

var testUtils = require('web.test_utils');

QUnit.module('account', {
    beforeEach: function () {
        this.params = demoData.getParams();
    }
}, function () {
    QUnit.module('Reconciliation');

    QUnit.test('Reconciliation basic rendering', function (assert) {
        assert.expect(11);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            'data': this.params.data,
        });
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        assert.ok(widget.$el.hasClass('o_reconciliation_line'), "should instance of widget reconciliation");
        assert.strictEqual(widget.$('.accounting_view').length, 1, "should have one view");
        assert.strictEqual(widget.$('.match').length, 1, "should have 'match' panel");
        assert.strictEqual(widget.$('.create').length, 1, "should have 'create' panel");

        assert.strictEqual(widget.$('thead').text().replace(/[\n\r\s]+/g, ' '), " 101401 2017-01-01 SAJ/2014/002 and SAJ/2014/003 $ 1,175.00 ", "should display the line information");
        assert.ok(widget.$('caption .o_field_many2one').length, "should display the many2one with to select a partner");

        assert.strictEqual(clientAction.$('[data-mode="inactive"]').length, 3, "should be as 'inactive' mode by default");
        assert.strictEqual(widget.$el.data('mode'), 'match', "the first one should automatically switch to match mode");

        widget.$('.accounting_view thead td:first').trigger('click');
        assert.strictEqual(widget.$el.data('mode'), 'inactive', "should switch to 'inactive' mode");

        widget.$('.accounting_view tfoot td:first').trigger('click');
        assert.strictEqual(widget.$el.data('mode'), 'create', "should switch to 'create' mode");
        widget.$('.accounting_view tfoot td:first').trigger('click');
        assert.strictEqual(widget.$el.data('mode'), 'match', "should switch to 'match' mode");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation fields', function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Agrolait", "the partner many2one should display agrolait");
        assert.strictEqual(clientAction.widgets[2].$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");
        widget.$('.accounting_view tfoot td:first').trigger('click');
        assert.strictEqual(widget.$('.create input.o_input').length, 7,
            "create panel should contain 7 fields (account_id, tax_id, journal_id, analytic_account_id, analytic_tag_ids, label, amount)");
        assert.strictEqual(widget.$('.create .create_account_id .o_required_modifier, .create .create_label .o_required_modifier, .create .create_amount .o_required_modifier').length, 3,
            "account_id, label and amount should be required fields");
        assert.strictEqual(widget.$('.create .create_label input').val(), 'SAJ/2014/002 and SAJ/2014/003',
            "should use the name of the reconciliation line for the default label value");
        assert.strictEqual(widget.$('.create .create_amount input').val(), '1175.00',
            "should have the balance amout as default value for the amout field");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation basic data', function (assert) {
        assert.expect(16);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));
        var widget = clientAction.widgets[0];

        assert.strictEqual(widget.$('.mv_line').length, 2, "should display 2 account move lines");
        assert.strictEqual(widget.$('.mv_line').text().replace(/[\n\r\s]+/g, ' '),
            " 101200 2017-02-07 INV/2017/0002 $ 650.00 101200 2017-02-07 INV/2017/0003 $ 525.00 ",
            "should display 4 account move lines who contains the account_code, due_date, label and the credit");
        assert.strictEqual(widget.$('.mv_line .cell_right:contains(".")').length, 2, "should display only the credit account move lines (hide the debit)");

        clientAction.widgets[1].$('.accounting_view thead td:first').trigger('click');
        assert.strictEqual(clientAction.widgets[1].$('.mv_line').length, 5, "should display 5 account move lines");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line .cell_right:contains(".")').length, 3, "should display only the credit account move lines (hide the debit)");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line.already_reconciled').length, 3, "should display 3 already reconciled account move lines");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line').text().replace(/[\n\r\s]+/g, ' '),
            " 101401 2017-01-23 ASUSTeK: BNK1/2017/0002: SUPP.OUT/2017/0002 : BILL/2017/0003 $ 376.00 101401 2017-01-23 Agrolait: BNK1/2017/0003: CUST.IN/2017/0001 $ 100.00 111100 2017-02-28 Camptocamp: BILL/2017/0001 $ 10,000.00 101401 2017-01-23 Agrolait: BNK1/2017/0004: CUST.IN/2017/0002 : INV/2017/0003 $ 525.50 101200 2017-02-07 Agrolait: INV/2017/0002 $ 650.00 ",
            "should display 4 account move lines who contains the account_code, due_date, label and the credit");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line .cell_left:contains(".")').length, 2, "should display only 2 debit account move lines");

        // load more
        assert.ok(clientAction.widgets[1].$('.match div.load-more a:visible').length, "should display the 'load more' button");
        assert.equal(clientAction.widgets[1].$('.match div.load-more span').text(), 4, "should display 4 items remaining");
        clientAction.widgets[1].$('.match div.load-more a').trigger('click');
        assert.strictEqual(clientAction.widgets[1].$('.mv_line').length, 8, "should load 3 more records"),
        // assert.notOk(clientAction.widgets[1].$('.match div.load-more a:visible').length, "should not display the 'load more' button anymore");

        assert.ok(clientAction.widgets[0].$('caption button.btn-secondary:visible').length, "should display the 'validate' button");
        assert.ok(clientAction.widgets[1].$('caption .text-danger:visible').length, "should display the 'Select a partner or choose a counterpart' message");
        assert.ok(clientAction.widgets[2].$('caption button.btn-primary:visible').length, "should display the 'Reconcile' button");

        clientAction.widgets[3].$('.accounting_view thead td:first').trigger('click');
        assert.strictEqual(clientAction.widgets[3].$el.data('mode'), 'create', "should switch to 'create' mode instead 'match' mode when 'match' mode is empty");

        // open the first line
        widget.$('.accounting_view thead td:first').trigger('click');
        // select propositions
        widget.$('.match .cell_account_code:first').trigger('click');
        widget.$('.match .cell_account_code:first').trigger('click');

        testUtils.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8, counterpart_aml_dicts: [{
                                                                  "counterpart_aml_id": 109,
                                                                  "credit": 650,
                                                                  "debit": 0,
                                                                  "name": "INV/2017/0002",
                                                                  "analytic_tag_ids": [[6, null, []]]
                                                                },
                                                                {
                                                                  "counterpart_aml_id": 112,
                                                                  "credit": 525,
                                                                  "debit": 0,
                                                                  "name": "INV/2017/0003",
                                                                  "analytic_tag_ids": [[6, null, []]]
                                                                }],
                                    payment_aml_ids: [], new_aml_dicts: []}]],
                "Should call process_bank_statement_line with ids");
            var def = $.Deferred();
            def.abort = function () {};
            event.data.callback(def);
        });

        // click on reconcile button
        widget.$('button.o_reconcile:not(:hidden)').trigger('click');

        clientAction.destroy();
    });

    QUnit.test('Reconciliation validate without proposition', function (assert) {
        assert.expect(1);
        // Test added to prevent this issue happening again: https://github.com/odoo/odoo/commit/3549688b21eb65e16b9c3f2b6462eb8d8b52cd47
        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];
        // Ensure that when we validate a line without any selection, it is the same
        // as when we manually create a line with the line.balance and that only one
        // line is send back to server.
        testUtils.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8, counterpart_aml_dicts: [],
                                    payment_aml_ids: [], new_aml_dicts: [{
                                        account_id: 287,
                                        credit: 1175,
                                        debit: 0,
                                        name: 'SAJ/2014/002 and SAJ/2014/003',
                                        analytic_tag_ids: [[6, null, []]]
                                    }]}]],
                "Should call process_bank_statement_line with ids");
            var def = $.Deferred();
            def.abort = function () {};
            event.data.callback(def);
        });

        // click on validate button
        widget.$('button.o_validate:not(:hidden)').trigger('click');
        clientAction.destroy();
    });

    QUnit.test('Reconciliation validate with proposition', function (assert) {
        assert.expect(1);
        // Test added to check this functionality: https://github.com/odoo/odoo/commit/2f3b469dee6f18cbccce1cdf2a81cfe57960c533
        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];
        // Add a line as proposition
        // open the first line
        widget.$('.accounting_view thead td:first').trigger('click');
        // select propositions
        widget.$('.match .cell_account_code:first').trigger('click');

        // Ensure that when we validate a line with propositions and that there is a remaining balance
        // We also create a line which is the open balance.
        testUtils.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8,
                                    counterpart_aml_dicts: [{
                                        counterpart_aml_id: 109,
                                        credit: 650,
                                        debit: 0,
                                        name: 'INV/2017/0002',
                                        analytic_tag_ids: [[6, null, []]]
                                    }],
                                    payment_aml_ids: [],
                                    new_aml_dicts: [{
                                        account_id: 287,
                                        credit: 525,
                                        debit: 0,
                                        name: 'SAJ/2014/002 and SAJ/2014/003 : Open balance'
                                    }]}]],
                "Should call process_bank_statement_line with ids");
            var def = $.Deferred();
            def.abort = function () {};
            event.data.callback(def);
        });

        // click on validate button
        widget.$('button.o_validate:not(:hidden)').trigger('click');
        clientAction.destroy();
    });

    QUnit.test('Reconciliation partial', function (assert) {
        assert.expect(10);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                console.log(args.method);
                if (args.method === 'process_bank_statement_line') {
                    var lines = args.args['1'];
                    assert.deepEqual(args.args, [
                        [6],
                        [{
                            partner_id: lines.length == 1 ? lines[0].partner_id : false,
                            counterpart_aml_dicts:[{
                              "analytic_tag_ids": [[6, null, []]],
                              "counterpart_aml_id": 114,
                              "credit": 0,
                              "debit": 32.57999999999993,
                              "name": "BILL/2017/0001"
                            }],
                            payment_aml_ids: [],
                            new_aml_dicts: [],
                        }]
                    ], "should call process_bank_statement_line with partial reconcile values");
                }
                return this._super(route, args);
            },
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        widget.$('.match .cell_account_code:first').trigger('click');
        assert.notOk( widget.$('.cell_right .line_info_button').length, "should not display the partial reconciliation alert");

        widget = clientAction.widgets[1];

        assert.notOk( widget.$('.cell_left .line_info_button').length, "should not display the partial reconciliation alert");
        widget.$('.accounting_view thead td:first').trigger('click');
        widget.$('.match .mv_line[data-line-id=114] .cell_account_code').trigger('click');
        assert.equal( widget.$('.accounting_view tbody .cell_left .line_info_button').length, 1, "should display the partial reconciliation alert");

        // The partner has been set automatically, remove it.
        widget.$('.o_input_dropdown input').trigger('click');
        widget.$('.o_input_dropdown input').val('').trigger('keyup').trigger('blur');

        assert.strictEqual(widget.$('button.btn-primary:visible').length, 0, "should display the reconcile model buttons");
        assert.strictEqual(widget.$('.text-danger:visible').length, 1, "should display counterpart alert");
        widget.$('.accounting_view .cell_left .line_info_button').trigger('click');
        assert.strictEqual(widget.$('.accounting_view .cell_left .line_info_button').length, 1, "should display a partial reconciliation alert");
        assert.notOk(widget.$('.accounting_view .cell_left .line_info_button').hasClass('do_partial_reconcile_true'), "should display the partial reconciliation information");
        assert.strictEqual(widget.$('button.btn-primary:visible').length, 1, "should display the reconcile button");
        assert.strictEqual( widget.$el.data('mode'), "inactive", "should be inactive mode");
        widget.$('button.btn-primary:visible').trigger('click');

        clientAction.destroy();
    });

    QUnit.test('Reconciliation title', function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            'data': this.params.data,
        });

        clientAction.appendTo($('#qunit-fixture'));

        assert.strictEqual(clientAction.$('h1.statement_name:visible').text(), "BNK/2014/001", "Should display the statement name");
        clientAction.$('h1.statement_name').trigger('click');
        assert.strictEqual(clientAction.$('h1.statement_name:visible').length, 0, "Should hide the statement name title to edit the content");
        assert.strictEqual(clientAction.$('h1.statement_name_edition:visible').length, 1, "Should show the edition field of statement name");
        clientAction.$('h1.statement_name_edition input').val('BNK/2014/001-BB').trigger('input').blur();
        assert.strictEqual(clientAction.$('h1.statement_name_edition:visible').length, 0, "Should hide the edition field of statement name");
        assert.strictEqual(clientAction.$('h1.statement_name:visible').length, 1, "Should show the statement name");
        assert.strictEqual(clientAction.$('h1.statement_name:visible').text(), "BNK/2014/001-BB", "Should update the statement name");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation currencies', function (assert) {
        assert.expect(2);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            'data': this.params.data,
            session: this.params.session,
            translateParameters: {
                date_format: "%m/%d/%Y",
                direction:"ltr",
                name:"English",
                thousands_sep: ",",
                time_format: "%H:%M:%S",
                decimal_point: ".",
                id:1,
                grouping: [3,0],
            }
        });
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        assert.strictEqual(clientAction.$('.accounting_view tfoot .cell_right, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s]+/g, ' '),
            "$ 1,175.00$ 32.58$ 2,000.00", "should display the different amounts with the currency");
        widget.$('.accounting_view thead .mv_line td:first').trigger('click');

        assert.strictEqual(clientAction.$('.accounting_view tbody').text().replace(/[\n\r\s]+/g, ' '),
            " 101200 2017-02-07 INV/2017/0012 $ 650.00 ", "should display the created reconciliation line with the currency");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation change partner', function (assert) {
        assert.expect(17);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            archs: {
                'res.partner,false,list': '<tree string="Partners"><field name="display_name"/></tree>',
                'res.partner,false,search': '<search string="Partners">' +
                                            '<field name="display_name" string="Name"/>' +
                                        '</search>',
            },
        });

        clientAction.appendTo($('#qunit-fixture'));
        var widget = clientAction.widgets[0];
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Agrolait", "the partner many2one should display agrolait");
        assert.strictEqual(widget.$('.match table tr').length, 2, "agrolait should have 2 propositions for reconciliation");

        // Adding the two propositions
        // This is in order to try that after changing partner the propositions are emptied
        widget.$('.match .cell_account_code:first').trigger('click');
        widget.$('.match .cell_account_code:first').trigger('click');
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 2, "Both proposition should be selected");

        // Similate changing partner to one that does not have propositions to see if create mode is open after
        widget.$('.o_input_dropdown input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(partner 1)').trigger('mouseenter').trigger('click');
        clientAction._onAction({target: widget, name: 'change_partner', data: {data: {display_name: 'partner 1', id: 1}}, stopped: false});
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "partner 1", "the partner many2one should display partner 1");
        assert.strictEqual(widget.$('.match table tr.mv_line').length, 0, "partner 1 should have 0 propositions for reconciliation");
        assert.strictEqual(widget.$el.data('mode'), 'create', "widget should be in create mode");

        // Simulate changing partner
        widget.$('.o_input_dropdown input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(Camptocamp)').trigger('mouseenter').trigger('click');
        clientAction._onAction({target: widget, name: 'change_partner', data: {data: {display_name: 'Camptocamp', id: 12}}, stopped: false});
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");
        assert.strictEqual(widget.$('.match table tr.mv_line').length, 3, "camptocamp should have 3 propositions for reconciliation");

        // Simulate changing partner with SelectCreateDialog
        widget = clientAction.widgets[1];
        assert.strictEqual($('.modal').length, 0, "shouldn't have any opened modal");
        widget.$('.o_input_dropdown input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(Search More):eq(1)').trigger('mouseenter').trigger('click');
        assert.strictEqual($('.modal').length, 1, "should open a SelectCreateDialog");
        $('.modal table.o_list_view td:contains(Camptocamp)').click();
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");

        widget = clientAction.widgets[2];
        widget.$('.accounting_view thead td:first').trigger('click');
        widget.$('.accounting_view .mv_line .cell_label').trigger('click');
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display agrolait");
        assert.strictEqual(widget.$('.match table tr').length, 3, "Camptocamp should have 3 propositions for reconciliation");
        assert.notOk(widget.$('.match div.load-more a:visible').length, "should not display the load more button");

        // Simulate remove partner
        widget.$('.o_input_dropdown input').trigger('click');
        widget.$('.o_input_dropdown input').val('').trigger('keyup').trigger('blur');
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "", "the partner many2one should be empty");
        assert.strictEqual(widget.$('.match table tr.mv_line').length, 5, "should have 5 propositions for reconciliation if partner is false");
        assert.ok(widget.$('.match div.load-more a:visible').length, "should display the load more button");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line', function (assert) {
        assert.expect(23);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });
        clientAction.appendTo($('#qunit-fixture'));

        assert.strictEqual(clientAction.$('.accounting_view tfoot .cell_right, .accounting_view tfoot .cell_left').text().replace(/[$, ]+/g, ''), " 1175.00 32.58 2000.00", "should display the open balance values");

        var widget = clientAction.widgets[0];

        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), 'Open balance', "should display 'Open Balance' line with the rest to reconcile");

        widget.$('.accounting_view tfoot td:first').trigger('click');
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101200 Account Receivable)').trigger('mouseenter').trigger('click');

        assert.notOk(widget.$('.accounting_view tfoot .cell_label').text(), "should not display 'Open Balance' line because the rest to reconcile is null");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 1, "should have only the created reconcile line");
        assert.strictEqual(widget.$('.accounting_view tbody tr').text().replace(/[\n\r\s$,]+/g, ' '), " 101200 New SAJ/2014/002 and SAJ/2014/003 1175.00 ",
            "the new line should have the selected account, name and amout");
        assert.ok(widget.$('caption button.btn-primary:visible').length, "should display the 'Reconcile' button");

        testUtils.intercept(clientAction, 'do_action', function (event) {
            assert.strictEqual(JSON.stringify(event.data.action),
                '{"type":"ir.actions.act_window","res_model":"account.reconcile.model","views":[[false,"form"]],"target":"current"}',
                "should open the reconcile model form view");
        });
        widget.$('.create .reconcile_model_create').trigger('click');

        testUtils.intercept(clientAction, 'do_action', function (event) {
            assert.strictEqual(JSON.stringify(event.data.action),
                '{"type":"ir.actions.act_window","res_model":"account.reconcile.model","views":[[false,"list"],[false,"form"]],"view_type":"list","view_mode":"list","target":"current"}',
                "should open the reconcile model list view");
        });
        widget.$('.create .reconcile_model_edit').trigger('click');

        widget.$('.create .create_amount input').val('1100.00').trigger('input');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00", "should display the value 1100.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$ 75.00", "should display 'Open Balance' line because the rest to reconcile is 75.00");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 1, "should have ever only the created reconcile line");
        assert.strictEqual(widget.$('.accounting_view tbody tr').text().replace(/[\n\r\s$,]+/g, ' '), " 101200 New SAJ/2014/002 and SAJ/2014/003 1100.00 ",
            "the new line should be update the amout");
        assert.ok(widget.$('caption button.btn-secondary:visible').length, "should display the 'validate' button");

        widget.$('.create .add_line').trigger('click').trigger('click');
        widget.$('.create .create_amount input').val('-100').trigger('input');
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        widget.$('.create .create_label input').val('test0').trigger('input');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_left:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 100.00", "should display the value 100.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$ 175.00", "should display 'Open Balance' line because the rest to reconcile is 175.00");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 2, "should have 2 created reconcile lines");
        assert.strictEqual(widget.$('.accounting_view tbody tr:eq(1)').text().replace(/[\n\r\s$,]+/g, ' '), " 101000 New test0 100.00 ",
            "the new line should have the selected account, name and amout");

        widget.$('.accounting_view tfoot td:first').trigger('click');
        widget.$('.accounting_view tfoot td:first').trigger('click');

        assert.strictEqual(widget.$('.create .create_amount input').val(), "175.00", "should have '175.00' as default amount value");

        widget.$('.create .create_amount input').val('200').trigger('input');
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        widget.$('.create .create_label input').val('test1').trigger('input');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 200.00", "should display the value 200.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "$ 25.00", "should display 'Open balance' with 25.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 3, "should have 3 created reconcile lines");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line (many2one test)', function (assert) {
        assert.expect(5);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        var def = $.Deferred();

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
            archs: {
                "account.account,false,list": '<tree string="Account"><field name="code"/><field name="name"/></tree>',
                "account.account,false,search": '<search string="Account"><field name="code"/></search>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    return def.then(this._super.bind(this, route, args));
                }
                return this._super(route, args);
            },
        });

        clientAction.prependTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        // open the first line in write-off mode
        widget.$('.accounting_view tfoot td:first').trigger('click');

        // select an account with the many2one (drop down)
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101200)').trigger('mouseenter').trigger('click');
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "101200 Account Receivable", "Display the selected account");
        assert.strictEqual(widget.$('tbody:first .cell_account_code').text(), "101200", "Display the code of the selected account");

        // use the many2one select dialog to change the account
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(Search)').trigger('mouseenter').trigger('click');
        // select the account who does not appear in the drop drown
        $('.modal tr.o_data_row:contains(502)').click();
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "101200 Account Receivable", "Selected account does not change");
        // wait the name_get to render the changes
        def.resolve();
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "502 Account", "Display the selected account");
        assert.strictEqual(widget.$('tbody:first .cell_account_code').text(), "502", "Display the code of the selected account");
        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line with taxes', function (assert) {
        assert.expect(13);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        widget.$('.accounting_view tfoot td:first').trigger('click');
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        widget.$('.create .create_label input').val('test1').trigger('input');
        widget.$('.create .create_amount input').val('1100').trigger('input');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00", "should display the value 1100.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$\u00a075.00", "should display 'Open Balance' with 75.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 1, "should have 1 created reconcile lines");

        widget.$('.create .create_tax_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(10.00%)').trigger('mouseenter').trigger('click');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1000.00 $ 100.00", "should have 2 created reconcile lines with right column values");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$\u00a075.00", "should display 'Open Balance' with 75.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "", "should display 'Open Balance' without any value in left column");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 2, "should have 2 created reconcile lines");

        widget.$('.create .create_tax_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(20.00%)').trigger('mouseenter').trigger('click');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00 $ 220.00", "should have 2 created reconcile lines with right column values");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "$\u00a0145.00", "should display 'Open balance' with 145.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tbody tr').length, 2, "should have 2 created reconcile lines");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line from reconciliation model', function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
        });
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        widget.$('.accounting_view tfoot td:first').trigger('click');
        widget.$('.create .quick_add button:contains(ATOS)').trigger('click');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_label, .accounting_view tbody .cell_right').text().replace(/[\n\r\s$,]+/g, ' '),
            " ATOS Banque 1145.62 Tax 20.00% 229.12 ATOS Frais 26.71 Tax 10.00% include 2.67 ", "should display 4 lines");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s$,]+/g, ' '),
            "Open balance229.12", "should display the 'Open balance' line with value in left column");

        widget.$('.create .create_amount input').val('100').trigger('input');

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' '),
            " 101120 New ATOS Banque 1075.00 101120 New Tax 20.00% 215.00 101130 New ATOS Frais 90.91 101300 New Tax 10.00% include 9.09 ",
            "should update the value of the 4 lines (because the line must have 100% of the value)");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s$,]+/g, ' '),
            "Open balance215.00", "should change the 'Open balance' line because the 20.00% tax is not an include tax");

        widget.$('.accounting_view tbody .cell_account_code:first').trigger('click');
        widget.$('.accounting_view tbody .cell_label:first').trigger('click');

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' '), "", "should removed every line");

        widget.$('.create .quick_add button:contains(Double)').trigger('click');

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' '),
            " 101120 New Double Banque 1145.62 101130 New Double Frais 29.38 ",
            "should have a sum of reconciliation proposition amounts equal to the line amount");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation manual', function (assert) {
        assert.expect(13);

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: this.params.session,
        });
        clientAction.appendTo($('#qunit-fixture'));

        assert.strictEqual(clientAction.$('.accounting_view:first thead').text().replace(/[\n\r\s]+/g, ' '),
            " 101000 Current AssetsLast Reconciliation: 2017-02-16 101000 ",
            "should display the account as title");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:first').data('mode'), "inactive", "should be in 'inactive' mode because no line to displayed and the balance amount is null");
        assert.strictEqual(clientAction.$('.accounting_view:first tbody tr').length, 2, "should have 2 propositions");
        assert.strictEqual(clientAction.$('.accounting_view:first .o_reconcile:visible').length, 1, "should display the reconcile button");

        clientAction.$('.accounting_view:first .o_reconcile:visible').trigger('click');

        assert.strictEqual(clientAction.$('.accounting_view:first thead').text().replace(/[\n\r\s]+/g, ' '),
            " Agrolait 101200 ",
            "should display the partner and the account code as title");

        assert.strictEqual(clientAction.$('.o_reconciliation_line:first .match tr:first .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '),
            "$ 11,000.00", "sould display the line in $");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:first .match tr:first .cell_right .o_multi_currency').data('content'),
            "10,222.00 €", "sould display the monetary information in €");

        assert.strictEqual(clientAction.$('.accounting_view:first .o_no_valid:visible').length, 1, "should display the skip button");

        clientAction.$('.accounting_view:eq(1) thead td:first').trigger('click');
        clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="21"] .cell_label').trigger('click');
        clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="22"] .cell_label').trigger('click');

        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) tfoot tr').length, 0, "should not display the 'Write-off' line because the balance is null in Euro");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) .o_reconcile:visible').length, 1, "should display 'Reconcile' button in green");

        clientAction.$('.o_reconciliation_line:eq(1) .o_reconcile:visible').trigger('click');

        assert.strictEqual(clientAction.$('.o_reconciliation_line[data-mode!="inactive"]').length, 1, "should have only one line open");

        clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="23"] .cell_label').trigger('click');
        clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="24"] .cell_label').trigger('click');

        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) tfoot tr').length, 1, "should display the 'Write-off' line because the balance is not null in Euro");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) .o_validate:visible').length, 1, "should display 'Reconcile' button");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation: Payment < inv1 + inv2(partial)', function (assert) {
        assert.expect(4);

        /*
         * One payment: $1175
         * Two Invoices
         * The first invoice will be fully reconciled $650
         * The second invoice will be partially paid with the rest of the payment $999
         */

        // modify the second line that is already in db to put it at $999
        var indexModif = _.findIndex(this.params.mv_lines['[5,"",0,5]'], function (line) {return line.id === 112});
        this.params.mv_lines['[5,"",0,5]'][indexModif] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 999.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0003",
             partner_name: "Agrolait", total_amount_currency_str: "", id: 112, credit: 0.0, journal_id: [1, "Customer Invoices"],
             amount_str: "$ 999.00", debit: 999.0, account_code: "101200", ref: "", already_paid: false};

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                if (args.method === 'process_bank_statement_line') {
                    assert.deepEqual(args.args,
                        [
                            [5], // Id of the bank statement line

                            [{counterpart_aml_dicts:
                                [{name:"INV/2017/0002",
                                  debit: 0,
                                  credit: 650,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 109},

                                 {name: "INV/2017/0003",
                                  debit: 0,
                                  credit: 525,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 112}],

                              payment_aml_ids: [],
                              partner_id: 8,
                              new_aml_dicts: []}]
                        ], "should call process_bank_statement_line with partial reconcile values");
                }
                return this._super(route, args);
            },
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });
        clientAction.appendTo($('#qunit-fixture'));

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first invoice to reconcile fully
        widget.$('.match .cell_account_code:first').trigger('click');
        assert.notOk( widget.$('.cell_right .line_info_button').length,
            "should not display the partial reconciliation alert");

        // Add second invoice to reconcile partially
        widget.$('.match .cell_account_code:first').trigger('click');
        var $reconciliationAlert = widget.$('.cell_right .line_info_button');

        assert.ok($reconciliationAlert.length,
            "should display the partial reconciliation alert");

        $reconciliationAlert.click();

        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');

        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        $buttonReconcile.click();

        clientAction.destroy();
    });

    QUnit.test('Reconciliation: payment and 2 partials', function (assert) {
        assert.expect(6);

        /*
         * One payment: $1175
         * Two Invoices as Inv1 = 1200; Inv2 = 1200:
         * Payment < Inv1 AND Payment < Inv2
         * No partial reconcile is possible, as a write-off of 1225 is necessary
         */

        // modify the invoice line to have their amount > payment
        var indexInv1 = _.findIndex(this.params.mv_lines['[5,"",0,5]'], function (line) {return line.id === 109});
        this.params.mv_lines['[5,"",0,5]'][indexInv1] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0002", partner_name: "Agrolait",
             total_amount_currency_str: "", id: 109, credit: 0.0, journal_id: [1, "Customer Invoices"], amount_str: "$ 1200.00", debit: 1200.0,
             account_code: "101200", ref: "", already_paid: false};

        var indexInv2 = _.findIndex(this.params.mv_lines['[5,"",0,5]'], function (line) {return line.id === 112});
        this.params.mv_lines['[5,"",0,5]'][indexInv2] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0003",
             partner_name: "Agrolait", total_amount_currency_str: "", id: 112, credit: 0.0, journal_id: [1, "Customer Invoices"],
             amount_str: "$ 1200.00", debit: 1200.0, account_code: "101200", ref: "", already_paid: false};

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                if (args.method === 'process_bank_statement_line') {
                    assert.deepEqual(args.args,
                        [
                            [5], // Id of the bank statement line

                            [{counterpart_aml_dicts:
                                [{name:"INV/2017/0002",
                                  debit: 0,
                                  credit: 1200,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 109},

                                 {name: "INV/2017/0003",
                                  debit: 0,
                                  credit: 1200,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 112}],

                              payment_aml_ids: [],
                              partner_id: 8,
                              new_aml_dicts: [
                                {account_id: 282,
                                 credit: 0,
                                 debit: 1225,
                                 analytic_tag_ids: [[6, null, []]],
                                 name: 'SAJ/2014/002 and SAJ/2014/003',
                                }
                              ]}]
                        ], "should call process_bank_statement_line with new aml dict reconcile values");
                }
                return this._super(route, args);
            },
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });
        clientAction.appendTo($('#qunit-fixture'));

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first invoice
        // There should be the opportunity to reconcile partially
        widget.$('.match .cell_account_code:first').trigger('click');
        assert.ok(widget.$('.cell_right .line_info_button').length,
            "should display the partial reconciliation alert");

        // Add second invoice
        widget.$('.match .cell_account_code:first').trigger('click');
        assert.notOk(widget.$('.cell_right .line_info_button').length,
            "should not display the partial reconciliation alert");

        var writeOffCreate = widget.$('div.create');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        assert.equal(writeOffCreate.find('input[name=amount]').val(), -1225,
            'The right amount should be proposed for the write-off');

        writeOffCreate.find('.create_account_id input.ui-autocomplete-input').click();
        $('ul.ui-autocomplete li a:first').click(); // select first account to do the write off in

        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');

        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        $buttonReconcile.click();

        clientAction.destroy();
    });

    QUnit.test('Manual Reconciliation: remove a prop to attain balance and reconcile', function (assert) {
        assert.expect(5);

        // tweak the data to fit our needs
        this.params.data_for_manual_reconciliation_widget['[283, null, "", 0, 6]'] = _.extend({}, this.params.data_for_manual_reconciliation_widget['[null,null]']);
        this.params.data_for_manual_reconciliation_widget['[283, null, "", 0, 6]'].accounts[0].reconciliation_proposition = [
            {account_id: 283, account_type: "other", amount_currency_str: "", currency_id: false, date_maturity: "2017-03-18", date: "2017-02-16",
             total_amount_str: "$ 500.00", partner_id: 8, account_name: "101000 Current Assets", name: "INV/2017/0987", partner_name: "Agrolait",
             total_amount_currency_str: "", id: 999, credit: 0.0, journal_id: [1, "Customer Invoices"], amount_str: "$ 500.00", debit: 500.0,
             account_code: "101000", ref: "", already_paid: false}
        ];

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                if (args.method === 'process_move_lines') {
                    assert.deepEqual(args.args,
                        [
                            [{id: null, type: null,
                              mv_line_ids: [399, 402],
                              new_mv_line_dicts: []}
                            ]
                        ], "should call process_move_lines without the new mv line dict");
                }

                return this._super(route, args);
            },
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first prop
        widget.$('.match .cell_account_code:first').trigger('click');
        assert.equal( widget.$('.cell_right .line_info_button').length, 1, "should display the partial reconciliation alert");

        // Add second prop
        widget.$('.match .cell_account_code:first').trigger('click');

        // Check that a create form is here
        var writeOffCreate = widget.$('div.create');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        assert.equal(writeOffCreate.find('input[name=amount]').val(), 500,
            'The right amount should be proposed for the write-off');

        // remove the first line, the other two will balance one another
        widget.$('tr[data-line-id="999"] td:first').click()

        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');
        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        $buttonReconcile.click();

        clientAction.destroy();
    });

    QUnit.test('Manual Reconciliation: No lines for account', function (assert) {
        assert.expect(2);

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {
                currencies: {
                    3: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$"
                    }
                }
            },
        });

        clientAction.appendTo($('#qunit-fixture'));

        // The second reconciliation "line" is where it happens
        var widget = clientAction.widgets[1];

        var emptyLine = widget.$('tr.mv_line');

        assert.notOk('data-line-id' in emptyLine.getAttributes(),
            'Empty line should be empty');

        emptyLine.find('td:first').click();

        // Check that a create form is here
        var writeOffCreate = widget.$('div.create .create_account_id');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        clientAction.destroy();
    });

    QUnit.test('Tax on account receivable', function(assert){
        assert.expect(21);

        this.params.data_for_manual_reconciliation_widget['[null,null]'].accounts = [];
        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {},
            mockRPC: function(route, args) {
                if (args.method === "name_search") {
                    switch (args.model) {
                        // mock the default mock to do the minimal processing required
                        // to get the available values for the droplists.
                        case 'account.account':
                            assert.step("Account");
                            return $.when(
                                _.map(this.data[args.model].records, function (record) {
                                    return [record.id, record.name];
                                })
                            );
                        case 'account.tax':
                            assert.step("Tax");
                            return $.when(
                                _.map(this.data[args.model].records, function (record) {
                                    return [record.id, record.display_name];
                                })
                            );
                        case 'account.journal':
                            assert.step("Journal");
                            return $.when(
                                _.map(this.data[args.model].records, function (record) {
                                    return [record.id, record.display_name];
                                })
                            );
                    }
                }
                if (args.method === 'process_move_lines') {
                    var mv_line_ids = args.args[0][0].mv_line_ids.slice(0);
                    mv_line_ids.sort(function(a, b) {return a - b});
                    assert.deepEqual(mv_line_ids, [6, 19, 21],
                        "Reconciliation rpc payload, mv_line_ids are correct");

                    // Index aiming at the correct object in the list
                    var idx = _.has(args.args[0][0].new_mv_line_dicts[0], 'journal_id') ? 0 : 1;
                    assert.deepEqual(
                        _.pick(args.args[0][0].new_mv_line_dicts[idx],
                               'account_id', 'name', 'credit', 'debit', 'journal_id'),
                        {account_id: 287, name: "dummy text", credit: 0, debit: 180, journal_id: 8},
                        "Reconciliation rpc payload, new_mv_line_dicts.gift is correct"
                    );
                    assert.deepEqual(
                        _.pick(args.args[0][0].new_mv_line_dicts[1 - idx],
                               'account_id', 'name', 'credit', 'debit', 'tax_line_id'),
                        {account_id: 287, name: "Tax 20.00%", credit: 0, debit: 36, tax_line_id: 6},
                        "Reconciliation rpc payload, new_mv_line_dicts.tax is correct"
                    );
                }
                return this._super.apply(this, arguments);
            }
        });
        
        clientAction.appendTo($('#qunit-fixture'));

        var widget = clientAction.widgets[0];

        // Select invoice of 1k$, payment of 1k$ and payment of 180$
        var $tableToReconcile = widget.$('.match');
        _.each([6, 19, 21], function(id) {
            $tableToReconcile.find('tr.mv_line[data-line-id='+id+']:first td:first-child').click();
        });
        
        assert.verifySteps([], "No rpc done");

        // Store the money in excess to the "account receivable" account with 20% taxes
        widget.$("table tfoot tr td:first").click();
        var $reconcileForm = widget.$(".create");
        $reconcileForm.find('.create_account_id input').click();
        $('.ui-autocomplete .ui-menu-item a:contains(101200 Account Receivable)')
            .trigger('mouseover')
            .trigger('click');
        assert.verifySteps(["Account"], "Account rpc done");

        $reconcileForm.find('.create_tax_id input').click();
        $('.ui-autocomplete .ui-menu-item a:contains(Tax 20.00%)')
            .trigger('mouseover')
            .trigger('click');
        assert.verifySteps(["Account", "Tax"], "Tax rpc done");

        $reconcileForm.find('.create_journal_id input').click();
        $('.ui-autocomplete .ui-menu-item a:contains(company 1 journal)')
            .trigger('mouseover')
            .trigger('click');
        $reconcileForm.find('.create_label input').val('dummy text').trigger('input');
        assert.verifySteps(["Account", "Tax", "Journal"], "Journal rpc done");

        // Verify the two (gift + tax) lines were added to the list
        var $newLines = widget.$('tr.mv_line[data-line-id^=createLine]');
        var idx = ($($($newLines[0]).find("td")[3]).text().trim() === "dummy text") ? 0 : 1;

        var $newLineGiftTds = $($newLines[idx]).find("td");
        assert.equal($($newLineGiftTds[1]).text().trim(), "101200",
            "Gift line account number is valid");
        assert.equal($($newLineGiftTds[2]).text().trim(), "New",
            "Gift line is flagged as new");
        assert.equal($($newLineGiftTds[3]).text().trim(), "dummy text",
            "Gift line has the correct label");
        assert.equal($($newLineGiftTds[4]).text().trim(), "180.00",
            "Gift line has the correct left amount");
        assert.equal($($newLineGiftTds[5]).text().trim(), "",
            "Gift line has the correct right amount");

        var $newLineTaxeTds = $($newLines[1 - idx]).find("td");
        assert.equal($($newLineTaxeTds[1]).text().trim(), "101200",
            "Tax line account number is valid");
        assert.equal($($newLineTaxeTds[2]).text().trim(), "New",
            "Tax line is flagged as new");
        assert.equal($($newLineTaxeTds[3]).text().trim(), "Tax 20.00%",
            "Tax line has the correct label");
        assert.equal($($newLineTaxeTds[4]).text().trim(), "36.00",
            "Tax line has the correct left amount");
        assert.equal($($newLineTaxeTds[5]).text().trim(), "",
            "Tax line has the correct right amount");

        // Reconcile
        widget.$("button.o_reconcile.btn.btn-primary:first").click();
        assert.ok(true, "No error in reconciliation");

        clientAction.destroy();
    });
});
});
