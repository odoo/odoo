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
            parent_id: {string: "Parent", type: 'boolean'},
            is_company: {string: "Is company", type: 'boolean'},
            property_account_receivable_id: {string: 'Account receivable', type: 'many2one', relation: 'account.account'},
            property_account_payable_id: {string: 'Account payable', type: 'many2one', relation: 'account.account'},
        },
        records: [
            {id: 1, display_name: "partner 1", image: 'AAA'},
            {id: 2, display_name: "partner 2", image: 'BBB'},
            {id: 3, display_name: "partner 3", image: 'CCC'},
            {id: 4, display_name: "partner 4", image: 'DDD'},
            {id: 8, display_name: "Agrolait", image: 'EEE'},
            {id: 12, display_name: "Camptocamp", image: 'FFF', property_account_receivable_id: 287, property_account_payable_id: 287},
            // add more to have 'Search More' option
            {id: 98, display_name: "partner 98", image: 'YYY'},
            {id: 99, display_name: "partner 99", image: 'ZZZ'},
        ],
        mark_as_reconciled: function () {
            return Promise.resolve();
        },
    },
    'account.account': {
        fields: {
            id: {string: "ID", type: 'integer'},
            code: {string: "code", type: 'integer'},
            name: {string: "Displayed name", type: 'char'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
            deprecated: {string: "Deprecated", type: 'boolean'},
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
            {id: 499, code: 499001, name: "499001 Suspense Account", company_id: 1},
            {id: 500, code: 500, name: "500 Account", company_id: 1},
            {id: 501, code: 501, name: "501 Account", company_id: 1},
            {id: 502, code: 502, name: "502 Account", company_id: 1},
            {id: 503, code: 503, name: "503 Account", company_id: 1},
            {id: 504, code: 504, name: "504 Account", company_id: 1},
        ],
        mark_as_reconciled: function () {
            return Promise.resolve();
        },
    },
    'account.account.tag':{
        fields: {
            id: {string: "ID", type: 'integer'},
        },
        records: [
            {id: 1},
            {id: 2},
            {id: 3},
            {id: 4},
        ],
    },
    'account.tax.repartition.line': {
        fields: {
            id: {string: "ID", type: 'integer'},
            repartition_type: {string:"Repartition Type", type: 'selection'},
            account_id: {string: "Account", type: 'many2one', relation: 'account.account'},
            factor_percent: {string: "%", type: 'integer'},
            tag_ids: {string:"Tax Grids", type: 'many2many', relation: 'account.account.tag'}
        },
        records: [
            {id: 1, factor_percent: 100, repartition_type: "base", tag_ids: [1]},
            {id: 2, factor_percent: 100, repartition_type: "tax", tag_ids: [2]},
            {id: 3, factor_percent: 100, repartition_type: "base", tag_ids: [3]},
            {id: 4, factor_percent: 100, repartition_type: "tax", tag_ids: [4], account_id: 288},
        ],
    },
    'account.tax': {
        fields: {
            id: {string: "ID", type: 'integer'},
            display_name: {string: "Displayed name", type: 'char'},
            amount: {string: "amout", type: 'float'},
            price_include: {string: "Included in Price", type: 'boolean'},
            company_id: {string: "Company", type: 'many2one', relation: 'res.company'},
            amount_type: {string: "type", type: 'selection'},
            invoice_repartition_line_ids: {string: "Invoice Repartition", type: 'one2many', relation: 'account.tax.repartition.line'},
            //No need for refund repartition lines in our test; they're not used by reconciliation widget anyway
        },
        records: [
            {id: 6, display_name: "Tax 20.00%", amount: 20, amount_type: 'percent', price_include: false, company_id: 1, invoice_repartition_line_ids: [1, 2]},
            {id: 7, display_name: "Tax 10.00% include", amount: 10, amount_type: 'percent', price_include: true, company_id: 1, invoice_repartition_line_ids: [3, 4]},
        ],
        json_friendly_compute_all: function (args) {
            var tax = _.find(db['account.tax'].records, {'id': args[0][0]});
            var amount = args[1];

            var tax_base = null;
            var base_tags = null;
            var taxes = [];

            for (let i = 0 ; i < tax.invoice_repartition_line_ids.length ; i++) {
                var rep_ln = _.find(db['account.tax.repartition.line'].records, {'id': tax.invoice_repartition_line_ids[i]});

                if(rep_ln.repartition_type == 'base') {
                    tax_base = (tax.price_include ? amount*100/(100+tax.amount) : amount) * (rep_ln.factor_percent/100);
                    base_tags = rep_ln.tag_ids;
                }
                else if(rep_ln.repartition_type == 'tax') {
                    /*
                    IMPORTANT :
                    For simplicity of testing, we assume there is ALWAYS a
                    base repartition line before the tax one, so tax_base is non-null
                    */
                    taxes.push({
                        'id': tax.id,
                        'amount': tax_base*tax.amount/100,
                        "base": tax_base,
                        'name': tax.display_name,
                        "analytic": false,
                        'account_id': rep_ln.account_id,
                        'price_include': tax.price_include,
                        'tax_repartition_line_id': rep_ln.id,
                        'tag_ids': rep_ln.tag_ids,
                        'tax_ids': [tax.id],
                    })
                }
            }

            return Promise.resolve({
                "base": amount,
                "taxes": taxes,
                "base_tags": base_tags,
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
        fields: {
            id: {string: 'id', type: 'integer'},
            display_name: {string: 'display_name', type: 'char'},
        },
        records: [
            {id: 1, display_name: 'Come together'},
            {id: 2, display_name: 'Right now'},
        ],
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
            tax_ids: {string: "Tax", type: 'many2many', relation:'account.tax'},
            analytic_account_id: {string: "Analytic Account", type: 'many2one', relation:'account.analytic.account'},
            second_account_id: {string: "Second Account", type: 'many2one', relation:'account.account', domain:[('deprecated', '=', false)]},
            second_journal_id: {string: "Second Journal", type: 'many2one', relation:'account.journal',  help:"This field is ignored in a bank statement reconciliation."},
            second_label: {string: "Second Journal Item Label", type: 'char'},
            second_amount_type: {string: "Second amount_type", type: 'selection', selection: [['fixed', 'Fixed'], ['percentage', 'Percentage of balance']], default:'percentage'},
            second_amount: {string: "Second Amount", type: 'float', digits:0, help:"Fixed amount will count as a debit if it is negative, as a credit if it is positive.", default:100.0},
            second_tax_ids: {string: "Second Tax", type: 'many2many', relation: 'account.tax'},
            second_analytic_account_id: {string: "Second Analytic Account", type: 'many2one', relation:'account.analytic.account'},
            match_journal_ids: {string: "Journal Ids", type: 'many2many', relation: 'account.journal'},
            analytic_tag_ids: {string: 'Analytic tags', type: 'many2many', relation: 'account.analytic.tag'},
        },
        records: [
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 4, 'analytic_account_id': false, 'display_name': "Int\u00e9rrets", 'rule_type': 'writeoff_button', 'second_tax_ids': [], 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 282, 'company_id': [1, "Demo SPRL"], 'tax_ids': [], 'amount_type': "fixed", 'name': "Int\u00e9rrets", 'amount': 0.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 2, 'analytic_account_id': false, 'display_name': "Perte et Profit", 'rule_type': 'writeoff_button', 'second_tax_ids': [], 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 283, 'company_id': [1, "Demo SPRL"], 'tax_ids': [], 'amount_type': "percentage", 'name': "Perte et Profit", 'amount': 100.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 5, 'analytic_account_id': false, 'display_name': "Fs bank", 'rule_type': 'writeoff_button', 'second_tax_ids': [], 'has_second_line': false, 'journal_id': false, 'label': false, 'second_label': false, 'second_account_id': false, 'account_id': 284, 'company_id': [1, "Demo SPRL"], 'tax_ids': [], 'amount_type': "percentage", 'name': "Fs bank", 'amount': 100.0, 'second_amount': 100.0},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 8, 'analytic_account_id': false, 'display_name': "Caisse Sand.", 'rule_type': 'writeoff_button', 'second_tax_ids': [], 'has_second_line': false, 'journal_id': false, 'label': "Caisse Sand.", 'second_label': false, 'second_account_id': false, 'account_id': 308, 'company_id': [1, "Demo SPRL"], 'tax_ids': [], 'amount_type': "percentage", 'name': "Caisse Sand.", 'amount': 100.0, 'second_amount': 100.0, 'match_journal_ids': []},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 3, 'analytic_account_id': false, 'display_name': "ATOS", 'rule_type': 'writeoff_button', 'second_tax_ids': [7], 'has_second_line': true, 'journal_id': false, 'label': "ATOS Banque", 'second_label': "ATOS Frais", 'second_account_id': 286, 'account_id': 285, 'company_id': [1, "Demo SPRL"], 'tax_ids': [6], 'amount_type': "percentage", 'name': "ATOS", 'amount': 97.5, 'second_amount': -14.75},
            {'second_analytic_account_id': false, 'second_amount_type': "percentage", 'second_journal_id': false, 'id': 10, 'analytic_account_id': false, 'display_name': "Double", 'rule_type': 'writeoff_button', 'second_tax_ids': [], 'has_second_line': true, 'journal_id': false, 'label': "Double Banque", 'second_label': "Double Frais", 'second_account_id': 286, 'account_id': 285, 'company_id': [1, "Demo SPRL"], 'tax_ids': [], 'amount_type': "percentage", 'name': "Double", 'amount': 97.5, 'second_amount': 100, 'match_journal_ids': [], 'analytic_tag_ids': [1,2]},
        ]
    },
    'account.reconciliation.widget': {
        fields: {},
        auto_reconcile: function () {
            return Promise.resolve(Datas.used.auto_reconciliation);
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
            return Promise.resolve();
        },
        get_move_lines_for_bank_statement_line: function (args) {
            var partner_id = args.splice(1, 1)[0];
            var excluded_ids = args.splice(1, 1)[0];
            var mode = args.splice(-1, 1) [0]
            if (mode === 'other') return Promise.resolve([])
            args.splice(-1,1); // ignore limit
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
            return Promise.resolve(lines);
        },
        get_bank_statement_line_data: function (args) {
            var ids = args[0];
            var results = {
                value_min: 0,
                value_max: ids.length,
                lines: _.filter(Datas.used.data_widget, function (w) {return _.contains(ids, w.st_line.id);})
            };
            return Promise.resolve(results);
        },
        get_bank_statement_data: function () {
            var results = Datas.used.data_preprocess;
            results.lines = _.filter(Datas.used.data_widget, function (w) {return _.contains(results.st_lines_ids, w.st_line.id);});
            return Promise.resolve(results);
        },
        get_move_lines_for_manual_reconciliation: function (args) {
            var excluded_ids = args.splice(2, 1)[0];
            args.splice(-1,1); // ignore limit
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
            return Promise.resolve(lines);
        },
        get_all_data_for_manual_reconciliation: function (args) {
            var key = JSON.stringify(args);
            if (!Datas.used.data_for_manual_reconciliation_widget[key]) {
                throw new Error("Unknown parameters for get_all_data_for_manual_reconciliation: '"+ key + "'");
            }
            return Promise.resolve(Datas.used.data_for_manual_reconciliation_widget[key]);
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
            return Promise.resolve();
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
    '[5,"",0]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 112, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 134, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_id': [284, "101110 Stock Valuation Account"], 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[5,"b",0]': [
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
    ],
    '[6,"",0]': [
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 376.00", 'partner_id': 7, 'account_name': "Bank", 'name': "BNK1/2017/0002: SUPP.OUT/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 392, 'credit': 376.0, 'journal_id': "Bank", 'amount_str': "$ 376.00", 'debit': 0.0, 'account_code': "101401", 'ref': "BILL/2017/0003", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-22", 'date': "2017-01-23", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-15", 'total_amount_str': "$ 5,749.99", 'partner_id': 7, 'account_name': "Account Payable", 'name': "BILL/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 117, 'credit': 5749.99, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 5,749.99", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[6,"",5]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-15", 'total_amount_str': "$ 5,749.99", 'partner_id': 7, 'account_name': "Account Payable", 'name': "BILL/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 117, 'credit': 5749.99, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 5,749.99", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false}
    ],
    '[7,"",0]': [
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 133, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 4,610.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 106, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 4,610.00", 'debit': 4610.0, 'account_id': [287, "101200 Account Receivable"], 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "payable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-28", 'date': "2017-01-01", 'total_amount_str': "$ 10,000.00", 'partner_id': 12, 'account_name': "Account Payable", 'name': "BILL/2017/0001", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 114, 'credit': 10000.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 10,000.00", 'debit': 0.0, 'account_id': [284, "101110 Stock Valuation Account"], 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 376.00", 'partner_id': 7, 'account_name': "Bank", 'name': "BNK1/2017/0002: SUPP.OUT/2017/0002", 'partner_name': "ASUSTeK", 'total_amount_currency_str': "", 'id': 392, 'credit': 376.0, 'journal_id': "Bank", 'amount_str': "$ 376.00", 'debit': 0.0, 'account_code': "101401", 'ref': "BILL/2017/0003", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 100.00", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0003: CUST.IN/2017/0001", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 394, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101401", 'ref': "", 'already_paid': true},
        {'account_type': "liquidity", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-01-23", 'date': "2017-01-23", 'total_amount_str': "$ 525.50", 'partner_id': 8, 'account_name': "Bank", 'name': "BNK1/2017/0004: CUST.IN/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 396, 'credit': 0.0, 'journal_id': "Bank", 'amount_str': "$ 525.50", 'debit': 525.5, 'account_code': "101401", 'ref': "INV/2017/0003", 'already_paid': true},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-07", 'date': "2017-01-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0002", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 109, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 650.00", 'debit': 650.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-22", 'date': "2017-01-23", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
    ],
    '[8,"",0]': [],
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
    '[null,[282,283,284,285,286,287,288,308,499,500,501,502,503,504]]': {
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
    '[287,8,"",0]': [
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "10,222.00 €", 'currency_id': 1, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [7, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 180.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 21, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 90.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0006: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 23, 'credit': 90.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 90.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-10", 'date': "2017-02-08", 'total_amount_str': "$ 650.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0012", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 6, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1000.00", 'debit': 1000.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-10", 'date': "2017-02-08", 'total_amount_str': "$ 525.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 9, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 525.00", 'debit': 525.0, 'account_code': "101200", 'ref': "", 'already_paid': false}
    ],
    '[7,12,"",0]': [
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [7, "101200 Account Receivable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101200", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 100, 'amount_currency_str': "100.00 €", 'currency_id': 1, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 170.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 21, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 170.00", 'debit': 170.0, 'account_code': "101200", 'ref': "INV fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 100, 'amount_currency_str': "100.00 €", 'currency_id': 1, 'date_maturity': "2017-02-10", 'date': "2017-02-10", 'total_amount_str': "$ 180.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 22, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 170, 'amount_currency_str': "170.00 €", 'currency_id': 1, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 100.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 23, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 100.00", 'debit': 100.0, 'account_code': "101200", 'ref': "INV fddfgfdgfdgsdfg", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [287, "101200 Account Receivable"], 'amount_currency': 180, 'amount_currency_str': "180.00 €", 'currency_id': 1, 'date_maturity': "2017-02-10", 'date': "2017-02-10", 'total_amount_str': "$ 100.00", 'partner_id': 12, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Camptocamp", 'total_amount_currency_str': "", 'id': 24, 'credit': 100.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 100.00", 'debit': 0.0, 'account_code': "101200", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
    ],
    '[284,8,"",0]': [
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-08", 'date': "2017-02-08", 'total_amount_str': "$ 11,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0004: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 17, 'credit': 11000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 11,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "INV/2017/0005: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 19, 'credit': 1000.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "111100", 'ref': "", 'already_paid': false},
        {'account_type': "receivable", 'account_id': [284, "111100 Account Payable"], 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-09", 'date': "2017-02-09", 'total_amount_str': "$ 180.00", 'partner_id': 8, 'account_name': "101200 Account Receivable", 'name': "BILL/2017/0003: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 21, 'credit': 180.0, 'journal_id': [2, "Vendor Bills"], 'amount_str': "$ 180.00", 'debit': 0.0, 'account_code': "111100", 'ref': "fddfgfdgfdgsdfg", 'already_paid': false},
    ],
    '[283,null,"",0]': [
        {'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-02-16", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "BNK1/2017/0006: Customer Payment", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 399, 'credit': 1000.0, 'journal_id': [3, "Bank"], 'amount_str': "$ 1,000.00", 'debit': 0.0, 'account_code': "101000", 'ref': "", 'already_paid': false},
        {'account_type': "other", 'amount_currency_str': "", 'currency_id': false, 'date_maturity': "2017-03-18", 'date': "2017-02-16", 'total_amount_str': "$ 1,000.00", 'partner_id': 8, 'account_name': "101000 Current Assets", 'name': "INV/2017/0006", 'partner_name': "Agrolait", 'total_amount_currency_str': "", 'id': 402, 'credit': 0.0, 'journal_id': [1, "Customer Invoices"], 'amount_str': "$ 1,000.00", 'debit': 1000.0, 'account_code': "101000", 'ref': "", 'already_paid': false}
    ],
    '[284,12,"",0]': [],
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
        statement_line_ids: [4]
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
var ReconciliationRenderer = require('account.ReconciliationRenderer');
var demoData = require('account.reconciliation_tests.data');

var testUtils = require('web.test_utils');
var testUtilsDom = require('web.test_utils_dom');
var testUtilsMock = require('web.test_utils_mock');

QUnit.module('account', {
    beforeEach: function () {
        this.params = demoData.getParams();
        testUtils.patch(ReconciliationRenderer.LineRenderer, {
            MV_LINE_DEBOUNCE: 0,
        });
    },
    afterEach: function () {
        testUtils.unpatch(ReconciliationRenderer.LineRenderer);
    },
}, function () {
    QUnit.module('Reconciliation');

    QUnit.test('Reconciliation basic rendering', async function (assert) {
        assert.expect(10);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        var widget = clientAction.widgets[0];

        assert.hasClass(widget.$el,'o_reconciliation_line', "should instance of widget reconciliation");
        assert.containsOnce(widget, '.accounting_view', "should have one view");
        assert.containsN(widget, '[id*="notebook_page_match"]', 2, "should have 'match_rp' and 'match_other' panel");
        assert.containsOnce(widget, '.create', "should have 'create' panel");

        assert.strictEqual(widget.$('thead').text().replace(/[\n\r\s]+/g, ' '), " 101401 2017-01-01 SAJ/2014/002 and SAJ/2014/003 $ 1,175.00 ", "should display the line information");
        assert.ok(widget.$('caption .o_field_many2one').length, "should display the many2one with to select a partner");

        assert.containsN(clientAction, '[data-mode="inactive"]', 3, "should be as 'inactive' mode by default");
        assert.strictEqual(widget.$el.data('mode'), 'match_rp', "the first one should automatically switch to match_rp mode");

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        assert.strictEqual(widget.$el.data('mode'), 'create', "should switch to 'create' mode");

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_match_rp"]'));
        assert.strictEqual(widget.$el.data('mode'), 'match_rp', "should switch to 'match_rp' mode");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation fields', async function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Agrolait", "the partner many2one should display agrolait");
        assert.strictEqual(clientAction.widgets[2].$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");
        await testUtils.dom.click(widget.$('.accounting_view tfoot td:first'));
        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        assert.containsN(widget, '.create input.o_input', 8,
            "create panel should contain 8 fields (account_id, tax_id, journal_id, analytic_account_id, analytic_tag_ids, label, amount, date)");
        assert.containsN(widget, '.create .create_account_id .o_required_modifier, .create .create_label .o_required_modifier, .create .create_amount .o_required_modifier', 3,
            "account_id, label and amount should be required fields");
        assert.strictEqual(widget.$('.create .create_label input').val(), 'SAJ/2014/002 and SAJ/2014/003',
            "should use the name of the reconciliation line for the default label value");
        assert.strictEqual(widget.$('.create .create_amount input').val(), '1175.00',
            "should have the balance amout as default value for the amout field");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation basic data', async function (assert) {
        assert.expect(17);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        var widget = clientAction.widgets[0];

        assert.containsN(widget, '.match:first .mv_line', 2, "should display 2 account move lines");
        assert.strictEqual(widget.$('.match:first .mv_line').text().replace(/[\n\r\s]+/g, ' ').replace(/[\u200B]/g, ''),
            " 101200 2017-02-07 INV/2017/0002 $ 650.00 101200 2017-02-07 INV/2017/0003 $ 525.00 ",
            "should display 4 account move lines who contains the account_code, due_date, label and the credit");
        assert.strictEqual(widget.$('.match:first .mv_line .cell_right:contains(".")').length, 2, "should display only the credit account move lines (hide the debit)");

        await testUtils.dom.click(clientAction.widgets[1].$('.accounting_view thead td:first'));
        assert.containsN(clientAction.widgets[1], '.mv_line', 5, "should display 5 account move lines");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line .cell_right:contains(".")').length, 3, "should display only the credit account move lines (hide the debit)");
        assert.containsN(clientAction.widgets[1], '.mv_line.already_reconciled', 3, "should display 3 already reconciled account move lines");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line').text().replace(/[\n\r\s]+/g, ' ').replace(/[\u200B]/g, ''),
            " 101401 2017-01-23 ASUSTeK: BNK1/2017/0002: SUPP.OUT/2017/0002 : BILL/2017/0003 $ 376.00 101401 2017-01-23 Agrolait: BNK1/2017/0003: CUST.IN/2017/0001 $ 100.00 111100 2017-02-28 Camptocamp: BILL/2017/0001 $ 10,000.00 101401 2017-01-23 Agrolait: BNK1/2017/0004: CUST.IN/2017/0002 : INV/2017/0003 $ 525.50 101200 2017-02-07 Agrolait: INV/2017/0002 $ 650.00 ",
            "should display 4 account move lines who contains the account_code, due_date, label and the credit");
        assert.strictEqual(clientAction.widgets[1].$('.mv_line .cell_left:contains(".")').length, 2, "should display only 2 debit account move lines");

        // load more
        assert.ok(clientAction.widgets[1].$('.match:first div.load-more a:visible').length, "should display the 'load more' button");
        assert.equal(clientAction.widgets[1].$('.match:first div.load-more span').text(), 3, "should display 3 items remaining");
        await testUtils.dom.click(clientAction.widgets[1].$('.match:first div.load-more a'));
        assert.containsN(clientAction.widgets[1], '.mv_line', 8, "should load 3 more records");
        assert.notOk(clientAction.widgets[1].$('.match:first div.load-more a:visible').length, "should not display the 'load more' button anymore");

        assert.ok(clientAction.widgets[0].$('caption button.btn-secondary:visible').length, "should display the secondary 'Validate' button");
        assert.equal(clientAction.widgets[1].$('caption button:disabled:visible').length, 1,"button should be disabled");
        assert.ok(clientAction.widgets[2].$('caption button.btn-primary:visible').length, "should display the primary 'Validate' button");

        await testUtils.dom.click(clientAction.widgets[3].$('.accounting_view thead td:first'));
        assert.strictEqual(clientAction.widgets[3].$el.data('mode'), 'create', "should switch to 'create' mode instead of 'match_rp' mode when 'match_rp' mode is empty");

        // open the first line
        await testUtils.dom.click(widget.$('.accounting_view thead td:first'));
        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_match_rp"]'));
        // select propositions
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));

        // await testUtils.dom.click(widget.$('caption')); //why is it inactive?

        testUtils.mock.intercept(clientAction, 'call_service', function (event) {
            if (event.data.args[1].method == 'process_bank_statement_line') {
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
                    payment_aml_ids: [], new_aml_dicts: [], to_check: false}]],
                    "Should call process_bank_statement_line with args");
                    var def = testUtils.makeTestPromise();
                    def.abort = function () {};
                    event.data.callback(def);
            }
        });

        // click on reconcile button
        await testUtils.dom.click(widget.$('.o_reconcile:visible'));

        clientAction.destroy();
    });

    QUnit.test('Reconciliation validate without proposition', async function (assert) {
        assert.expect(1);
        // Test added to prevent this issue happening again: https://github.com/odoo/odoo/commit/3549688b21eb65e16b9c3f2b6462eb8d8b52cd47
        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];
        // Ensure that when we validate a line without any selection, it is the same
        // as when we manually create a line with the line.balance and that only one
        // line is send back to server.
        testUtils.mock.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8, to_check: false, counterpart_aml_dicts: [],
                                    payment_aml_ids: [],
                                    to_check: false,
                                    new_aml_dicts: [{
                                        account_id: 287,
                                        credit: 1175,
                                        debit: 0,
                                        name: 'SAJ/2014/002 and SAJ/2014/003',
                                        analytic_tag_ids: [[6, null, []]]
                                    }]}]],
                "Should call process_bank_statement_line with ids");
            var def = testUtils.makeTestPromise();
            def.abort = function () {};
            event.data.callback(def);
        });

        // click on validate button
        await testUtils.dom.click(widget.$('button.o_validate:not(:hidden)'));

        clientAction.destroy();
    });

    QUnit.test('Reconciliation validate with proposition', async function (assert) {
        assert.expect(1);
        // Test added to check this functionality: https://github.com/odoo/odoo/commit/2f3b469dee6f18cbccce1cdf2a81cfe57960c533
        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        var widget = clientAction.widgets[0];
        // Add a line as proposition
        // open the first line
        await testUtils.dom.click(widget.$('.accounting_view thead td:first'),{allowInvisible:true});
        await testUtils.nextTick();
        // select propositions
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'),{allowInvisible:true});
        await testUtils.nextTick();

        // Ensure that when we validate a line with propositions and that there is a remaining balance
        // We also create a line which is the open balance.
        testUtils.mock.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8, to_check: false,
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
            var def = testUtils.makeTestPromise();
            def.abort = function () {};
            event.data.callback(def);
        });

        // click on validate button
        await testUtils.dom.click(widget.$('button.o_validate:not(:hidden)'));
        clientAction.destroy();
    });

    QUnit.test('Reconciliation partial [REQUIRE FOCUS]', async function (assert) {
        assert.expect(8);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                console.log(args.method);
                if (args.method === 'process_bank_statement_line') {
                    var lines = args.args['1'];
                    console.log(args.arsg);
                    assert.deepEqual(args.args, [
                        [6],
                        [{
                            partner_id: lines.length == 1 ? lines[0].partner_id : false,
                            counterpart_aml_dicts:[{
                              "analytic_tag_ids": [[6, null, []]],
                              "counterpart_aml_id": 114,
                              "credit": 0,
                              "debit": 32.58,
                              "name": "BILL/2017/0001"
                            }],
                            payment_aml_ids: [],
                            new_aml_dicts: [],
                            to_check: false,
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        var widget = clientAction.widgets[0];

        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.equal( widget.$('.cell_right .edit_amount').length, 1, "should display the edition pencil");

        widget = clientAction.widgets[1];

        await testUtils.dom.click(widget.$('.accounting_view thead td:first'));
        assert.strictEqual(widget.$('.match:first .mv_line[data-line-id=114] .cell_account_code:first()').length, 1, 'Should have line')
        await testUtils.dom.click(widget.$('.match:first .mv_line[data-line-id=114] .cell_account_code'));

        assert.equal( widget.$('.accounting_view tbody .cell_left .edit_amount').length, 1, "should display the edition pencil");

        // The partner has been set automatically, remove it.
        await testUtils.dom.click(widget.$('.o_input_dropdown input'));
        await testUtils.fields.editAndTrigger(widget.$('.o_input_dropdown input'),'',['keyup','blur']);

        assert.equal(clientAction.widgets[1].$('caption button:disabled:visible').length, 1,"button should be disabled");
        await testUtils.dom.click(widget.$('.accounting_view .cell_left .edit_amount'));
        assert.strictEqual(widget.$('.accounting_view .cell_left .edit_amount_input:not(.d-none)').length, 1, "should display the input field to edit amount");
        // Edit amount
        await testUtils.fields.editAndTrigger(widget.$('.accounting_view .cell_left .edit_amount_input:not(.d-none)'),'32.58',['change','blur']);
        assert.strictEqual(widget.$('.accounting_view .cell_left .line_amount').text().replace(/[\n\r\s]+/g, ' '), " $ 10000.00 $ 32.58 ", "should display previous amount and new amount")

        assert.strictEqual(widget.$('button.btn-primary:visible').length, 1, "should display the reconcile button");
        await testUtils.dom.click(widget.$('button.btn-primary:visible'));

        clientAction.destroy();
    });

    QUnit.test('Reconciliation currencies', async function (assert) {
        assert.expect(2);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
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
            },
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        assert.strictEqual(clientAction.$('.accounting_view tfoot .cell_right, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s]+/g, ' '),
            "$ 1,175.00$ 32.58$ 2,000.00", "should display the different amounts with the currency");
        // await testUtils.dom.click(widget.$('.accounting_view thead .mv_line td:first'));

        assert.strictEqual(clientAction.$('.accounting_view tbody').text().replace(/[\n\r\s]+/g, ' ').replace(/[\u200B]/g, ''),
            " 101200 2017-02-07 INV/2017/0012 $ 650.00 ", "should display the created reconciliation line with the currency");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation change partner', async function (assert) {
        assert.expect(17);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            archs: {
                'res.partner,false,list': '<tree string="Partners"><field name="display_name"/></tree>',
                'res.partner,false,search': '<search string="Partners">' +
                                            '<field name="display_name" string="Name"/>' +
                                        '</search>',
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        var widget = clientAction.widgets[0];
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Agrolait", "the partner many2one should display agrolait");
        assert.containsN(widget, '.match:first table tr', 2, "agrolait should have 2 propositions for reconciliation");

        // Adding the two propositions
        // This is in order to try that after changing partner the propositions are emptied
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.containsN(widget, '.accounting_view tbody tr', 2, "Both proposition should be selected");

        // Similate changing partner to one that does not have propositions to see if create mode is open after
        await testUtils.dom.click(widget.$('.o_input_dropdown input'));
        $('.ui-autocomplete .ui-menu-item a:contains(partner 1)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        clientAction._onAction({target: widget, name: 'change_partner', data: {data: {display_name: 'partner 1', id: 1}}, stopped: false});
        await testUtils.nextTick();
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "partner 1", "the partner many2one should display partner 1");
        assert.containsNone(widget, '.match:first table tr.mv_line', "partner 1 should have 0 propositions for reconciliation");
        assert.strictEqual(widget.$el.data('mode'), 'create', "widget should be in create mode");

        // Simulate changing partner
        await testUtils.dom.clickFirst(widget.$('.o_input_dropdown input'));
        $('.ui-autocomplete .ui-menu-item a:contains(Camptocamp)').trigger('mouseenter').trigger('click');
        clientAction._onAction({target: widget, name: 'change_partner', data: {data: {display_name: 'Camptocamp', id: 12}}, stopped: false});
        await testUtils.nextTick();
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");
        assert.containsN(widget, '.match:first table tr.mv_line', 3, "camptocamp should have 3 propositions for reconciliation");

        // Simulate changing partner with SelectCreateDialog
        widget = clientAction.widgets[1];
        assert.strictEqual($('.modal').length, 0, "shouldn't have any opened modal");
        await testUtils.dom.click(widget.$('.o_input_dropdown input'));
        $('.ui-autocomplete .ui-menu-item a:contains(Search More):eq(1)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        assert.strictEqual($('.modal').length, 1, "should open a SelectCreateDialog");
        await testUtils.dom.click($('.modal table.o_list_table td:contains(Camptocamp)'));
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display Camptocamp");

        widget = clientAction.widgets[2];
        await testUtils.dom.click(widget.$('.accounting_view thead td:first'));
        await testUtils.dom.click(widget.$('.accounting_view .mv_line .cell_label'));
        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "Camptocamp", "the partner many2one should display agrolait");
        assert.containsN(widget, '.match:first table tr', 3, "Camptocamp should have 3 propositions for reconciliation");
        assert.notOk(widget.$('.match:first div.load-more a:visible').length, "should not display the load more button");

        // Simulate remove partner
        await testUtils.dom.click(widget.$('.o_input_dropdown input'));
        await testUtils.fields.editAndTrigger(widget.$('.o_input_dropdown input'),'',['keyup','blur']);

        assert.strictEqual(widget.$('.o_input_dropdown input').val(), "", "the partner many2one should be empty");
        assert.containsN(widget, '.match:first table tr.mv_line', 5, "should have 5 propositions for reconciliation if partner is false");
        assert.ok(widget.$('.match:first div.load-more a:visible').length, "should display the load more button");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line', async function (assert) {
        assert.expect(23);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        assert.strictEqual(clientAction.$('.accounting_view tfoot .cell_right, .accounting_view tfoot .cell_left').text().replace(/[$, ]+/g, ''), " 1175.00 32.58 2000.00", "should display the open balance values");

        var widget = clientAction.widgets[0];

        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), 'Open balance', "should display 'Open Balance' line with the rest to reconcile");

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        await testUtils.dom.click(widget.$('.create .create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(101200 Account Receivable)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();

        assert.notOk(widget.$('.accounting_view tfoot .cell_label').text(), "should not display 'Open Balance' line because the rest to reconcile is null");
        assert.containsOnce(widget, '.accounting_view tbody tr', "should have only the created reconcile line");
        assert.strictEqual(widget.$('.accounting_view tbody tr').text().replace(/[\n\r\s$,]+/g, ' ').replace(/[\u200B]/g, ''), " 101200 New SAJ/2014/002 and SAJ/2014/003 1175.00 ",
            "the new line should have the selected account, name and amout");
        assert.ok(widget.$('caption button.btn-primary:visible').length, "should display the 'Reconcile' button");

        testUtils.mock.intercept(clientAction, 'do_action', function (event) {
            assert.strictEqual(JSON.stringify(event.data.action),
                '{"type":"ir.actions.act_window","res_model":"account.reconcile.model","views":[[false,"form"]],"target":"current"}',
                "should open the reconcile model form view");
        });
        await testUtils.dom.click(widget.$('.create .reconcile_model_create'),{allowInvisible:true});

        testUtils.mock.intercept(clientAction, 'do_action', function (event) {
            assert.strictEqual(JSON.stringify(event.data.action),
                '{"type":"ir.actions.act_window","res_model":"account.reconcile.model","views":[[false,"list"],[false,"form"]],"view_mode":"list","target":"current"}',
                "should open the reconcile model list view");
        });
        await testUtils.dom.click(widget.$('.create .reconcile_model_edit'),{allowInvisible:true});

        await testUtils.fields.editInput(widget.$('.create .create_amount input'), '1100.00');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00", "should display the value 1100.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$ 75.00", "should display 'Open Balance' line because the rest to reconcile is 75.00");
        assert.containsOnce(widget, '.accounting_view tbody tr', "should have ever only the created reconcile line");
        assert.strictEqual(widget.$('.accounting_view tbody tr').text().replace(/[\n\r\s$,]+/g, ' ').replace(/[\u200B]/g, ''), " 101200 New SAJ/2014/002 and SAJ/2014/003 1100.00 ",
            "the new line should be update the amout");
        assert.ok(widget.$('caption button.btn-secondary:visible').length, "should display the 'validate' button");

        await testUtils.dom.click(widget.$('.create .add_line'),{allowInvisible:true});
        await testUtils.fields.editInput(widget.$('.create .create_amount input'), '-100');
        await testUtils.dom.click(widget.$('.create .create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        await testUtils.fields.editInput(widget.$('.create .create_label input'), 'test0');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_left:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 100.00", "should display the value 100.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$ 175.00", "should display 'Open Balance' line because the rest to reconcile is 175.00");
        assert.containsN(widget, '.accounting_view tbody tr', 2, "should have 2 created reconcile lines");
        assert.strictEqual(widget.$('.accounting_view tbody tr:eq(1)').text().replace(/[\n\r\s$,]+/g, ' ').replace(/[\u200B]/g, ''), " 101000 New test0 100.00 ",
            "the new line should have the selected account, name and amout");

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));

        assert.strictEqual(widget.$('.create .create_amount input').val(), "175.00", "should have '175.00' as default amount value");

        await testUtils.fields.editInput(widget.$('.create .create_amount input'), '200');
        widget.$('.create .create_account_id input').trigger('click');
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        await testUtils.fields.editInput(widget.$('.create .create_label input'), 'test1');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 200.00", "should display the value 200.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "$ 25.00", "should display 'Open balance' with 25.00 in left column");
        assert.containsN(widget, '.accounting_view tbody tr', 3, "should have 3 created reconcile lines");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line (many2one test)', async function (assert) {
        assert.expect(5);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        var def = testUtils.makeTestPromise();

        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    return def.then(this._super.bind(this, route, args));
                }
                return this._super(route, args);
            },
        });

        await clientAction.prependTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        // open the first line in write-off mode
        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));

        // select an account with the many2one (drop down)
        await testUtils.dom.click(widget.$('.create .create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(101200)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "101200 Account Receivable", "Display the selected account");
        assert.strictEqual(widget.$('tbody:first .cell_account_code').text().replace(/[\u200B]/g, ''), "101200", "Display the code of the selected account");

        // use the many2one select dialog to change the account
        await testUtils.dom.click(widget.$('.create .create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(Search)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        // select the account who does not appear in the drop drown
        await testUtils.dom.click($('.modal tr.o_data_row:contains(502)'));
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "101200 Account Receivable", "Selected account does not change");
        // wait the name_get to render the changes
        def.resolve();
        await testUtils.nextTick();
        assert.strictEqual(widget.$('.create .create_account_id input').val(), "502 Account", "Display the selected account");
        assert.strictEqual(widget.$('tbody:first .cell_account_code').text().replace(/[\u200B]/g, ''), "502", "Display the code of the selected account");
        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line with taxes', async function (assert) {
        assert.expect(13);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        await testUtils.dom.click(widget.$('.create .create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(101000 Current Assets)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();
        await testUtils.fields.editInput(widget.$('.create .create_label input'), 'test1');
        await testUtils.fields.editInput(widget.$('.create .create_amount input'), '1100');

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right:last').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00", "should display the value 1100.00 in left column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$\u00a075.00", "should display 'Open Balance' with 75.00 in right column");
        assert.containsOnce(widget, '.accounting_view tbody tr', "should have 1 created reconcile lines");

        await testUtils.dom.click(widget.$('.create .create_tax_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(10.00%)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1000.00 $ 100.00", "should have 2 created reconcile lines with right column values");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open Balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_right').text(), "$\u00a075.00", "should display 'Open Balance' with 75.00 in right column");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "", "should display 'Open Balance' without any value in left column");
        assert.containsN(widget, '.accounting_view tbody tr', 2, "should have 2 created reconcile lines");
        await testUtils.dom.click(widget.$('[name="tax_ids"] a.o_delete'));
        widget.$('.create .create_tax_id input').val('').trigger('keyup').trigger('blur');
        await testUtils.dom.click(widget.$('.create .create_tax_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(20.00%)').trigger('mouseenter').trigger('click');
        await testUtils.nextTick();

        assert.strictEqual(widget.$('.accounting_view tbody .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '), "$ 1100.00 $ 220.00", "should have 2 created reconcile lines with right column values");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label').text(), "Open balance", "should display 'Open balance'");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_left').text(), "$\u00a0145.00", "should display 'Open balance' with 145.00 in right column");
        assert.containsN(widget, '.accounting_view tbody tr', 2, "should have 2 created reconcile lines");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation create line from reconciliation model', async function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        await testUtils.dom.click(widget.$('.create .quick_add button:contains(ATOS)'));

        assert.strictEqual(widget.$('.accounting_view tbody .cell_label, .accounting_view tbody .cell_right').text().replace(/[\n\r\s$,]+/g, ' '),
            " ATOS Banque 1145.63 ATOS Banque Tax 20.00% 229.13 ATOS Frais 26.78 ATOS Frais Tax 10.00% include 2.68 ", "should display 4 lines");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s$,]+/g, ''),
            "Openbalance229.22", "should display the 'Open balance' line with value in left column");

        await testUtils.fields.editAndTrigger(widget.$('.create .create_amount input'), '100',['input']);

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' ').replace(/[\u200B]/g, ''),
            " 101120 New ATOS Banque 1145.63 101120 New ATOS Banque Tax 20.00% 229.13 101130 New ATOS Frais 90.91 101300 New ATOS Frais Tax 10.00% include 9.09 ",
            "should update the value of the 2 lines (because the line + its tax must have 100% of the value)");
        assert.strictEqual(widget.$('.accounting_view tfoot .cell_label, .accounting_view tfoot .cell_left').text().replace(/[\n\r\s$,]+/g, ''),
            "Openbalance299.76", "should change the 'Open balance' line because the 20.00% tax is not an include tax");

        await testUtils.dom.click(widget.$('.accounting_view tbody .cell_account_code:first'));
        await testUtils.dom.click(widget.$('.accounting_view tbody .cell_label:first'));

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' '), "", "should removed every line");

        await testUtils.dom.click(widget.$('.create .quick_add button:contains(Double)'));

        assert.strictEqual(widget.$('.accounting_view tbody').text().replace(/[\n\r\s$,]+/g, ' ').replace(/[\u200B]/g, ''),
            " 101120 New Double Banque 1145.63 101130 New Double Frais 29.37 ",
            "should have a sum of reconciliation proposition amounts equal to the line amount");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation fetch correct reconciliation models', async function (assert) {
        assert.expect(1);

        testUtilsMock.patch(this.params.options.context, {
            active_model: 'account.journal', // On account dashboard, click "Reconcile" on a journal
            active_ids: [1,2], // Active journals
            company_ids: [3,4], // Active companies
        });

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: async function (route, args) {
                if (args.model === 'account.reconcile.model' && args.method === 'search_read') {
                    assert.deepEqual(
                        args.kwargs.domain, [
                            ['company_id', 'in', [3,4]],
                            '|',
                            ['match_journal_ids', '=', false],
                            ['match_journal_ids', 'in', [1, 2]],
                        ],
                        'The domain to get reconcile models should contain the right fields and values'
                    );
                }
                return this._super.apply(this, arguments);
            }
        });
        clientAction.appendTo($('#qunit-fixture'));
        testUtilsMock.unpatch(this.params.options.context);

        clientAction.destroy();
    });

    QUnit.test('Reconciliation manual', async function (assert) {
        assert.expect(13);

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: this.params.session,
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        assert.strictEqual(clientAction.$('.accounting_view:first thead').text().replace(/[\n\r\s]+/g, ' '),
            " 101000 Current AssetsLast Reconciliation: 2017-02-16 101000 ",
            "should display the account as title");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:first').data('mode'), "inactive", "should be in 'inactive' mode because no line to displayed and the balance amount is null");
        assert.containsN(clientAction, '.accounting_view:first tbody tr', 2, "should have 2 propositions");
        assert.containsOnce(clientAction, '.accounting_view:first .o_reconcile:visible', "should display the reconcile button");

        await testUtils.dom.click(clientAction.$('.accounting_view:first .o_reconcile:visible'));

        assert.strictEqual(clientAction.$('.accounting_view:first thead').text().replace(/[\n\r\s]+/g, ' '),
            " 101200 Account Receivable 101200 ",
            "should display the account and the account code as title");

        assert.strictEqual(clientAction.$('.o_reconciliation_line:first .match:first tr:first .cell_right').text().trim().replace(/[\n\r\s\u00a0]+/g, ' '),
            "$ 11,000.00", "sould display the line in $");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:first .match:first tr:first .cell_right .o_multi_currency').data('content'),
            "10,222.00 €", "sould display the monetary information in €");

        assert.containsOnce(clientAction, '.accounting_view:first .o_no_valid:visible', "should display the skip button");

        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) .accounting_view'))
        await testUtils.dom.click(clientAction.$('.accounting_view:eq(1) thead td:first'));
        // debugger
        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="21"] .cell_label'));
        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="22"] .cell_label'));

        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) tfoot tr').length, 0, "should not display the 'Write-off' line because the balance is null in Euro");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) .o_reconcile:visible').length, 1, "should display 'Reconcile' button in green");

        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) .o_reconcile:visible'));

        assert.containsOnce(clientAction, '.o_reconciliation_line[data-mode!="inactive"]', "should have only one line open");

        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="23"] .cell_label'));
        await testUtils.dom.click(clientAction.$('.o_reconciliation_line:eq(1) [data-line-id="24"] .cell_label'));

        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) tfoot tr').length, 1, "should display the 'Write-off' line because the balance is not null in Euro");
        assert.strictEqual(clientAction.$('.o_reconciliation_line:eq(1) .o_validate:visible').length, 1, "should display 'Reconcile' button");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation: Payment < inv1 + inv2(partial)', async function (assert) {
        assert.expect(3);

        /*
         * One payment: $1175
         * Two Invoices
         * The first invoice will be fully reconciled $650
         * The second invoice will be partially paid with the rest of the payment $999
         */

        // modify the second line that is already in db to put it at $999
        var indexModif = _.findIndex(this.params.mv_lines['[5,"",0]'], function (line) {return line.id === 112});
        this.params.mv_lines['[5,"",0]'][indexModif] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 999.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0003",
             partner_name: "Agrolait", total_amount_currency_str: "", id: 112, credit: 0.0, journal_id: [1, "Customer Invoices"],
             amount_str: "$ 999.00", debit: 999.0, account_code: "101200", ref: "", already_paid: false};

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                              to_check: false,
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first invoice to reconcile fully
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.ok( widget.$('.cell_right .edit_amount').length,
            "should display the pencil to edit amount");

        // Add second invoice to reconcile partially
        await testUtils.dom.click( widget.$('.match:first .cell_account_code:first'));

        // Edit amount on last invoice
        await testUtils.dom.click(widget.$('.edit_amount:last()'));
        await testUtils.fields.editAndTrigger(widget.$('.edit_amount_input:last()'),'525',['blur']);

        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');

        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        await testUtils.dom.click($buttonReconcile);

        clientAction.destroy();
    });

    QUnit.test('Reconciliation: payment and 2 partials', async function (assert) {
        assert.expect(6);

        /*
         * One payment: $1175
         * Two Invoices as Inv1 = 1200; Inv2 = 1200:
         * Payment < Inv1 AND Payment < Inv2
         * No partial reconcile is possible, as a write-off of 1225 is necessary
         */

        // modify the invoice line to have their amount > payment
        var indexInv1 = _.findIndex(this.params.mv_lines['[5,"",0]'], function (line) {return line.id === 109});
        this.params.mv_lines['[5,"",0]'][indexInv1] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0002", partner_name: "Agrolait",
             total_amount_currency_str: "", id: 109, credit: 0.0, journal_id: [1, "Customer Invoices"], amount_str: "$ 1200.00", debit: 1200.0,
             account_code: "101200", ref: "", already_paid: false};

        var indexInv2 = _.findIndex(this.params.mv_lines['[5,"",0]'], function (line) {return line.id === 112});
        this.params.mv_lines['[5,"",0]'][indexInv2] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0003",
             partner_name: "Agrolait", total_amount_currency_str: "", id: 112, credit: 0.0, journal_id: [1, "Customer Invoices"],
             amount_str: "$ 1200.00", debit: 1200.0, account_code: "101200", ref: "", already_paid: false};

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                              to_check: false,
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first invoice
        // There should be the opportunity to reconcile partially
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.ok(widget.$('.cell_right .edit_amount').length,
            "should display the pencil to edit amount");

        // Add second invoice
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.ok(widget.$('.cell_right .edit_amount').length,
            "should display the pencil to edit amount");

        var writeOffCreate = widget.$('div.create');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        assert.equal(writeOffCreate.find('input[name=amount]').val(), -1225,
            'The right amount should be proposed for the write-off');

        await testUtils.dom.click(writeOffCreate.find('.create_account_id input.ui-autocomplete-input'));
        await testUtils.dom.click($('ul.ui-autocomplete li a:first'));

        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');

        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        await testUtils.dom.click($buttonReconcile);

        clientAction.destroy();
    });

    QUnit.test('Reconciliation: partial payment of 2 invoices with one payment [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        /*
         * One payment: $1175
         * Two Invoices as Inv1 = 1200; Inv2 = 1200:
         * Payment < Inv1 AND Payment < Inv2
         * Assign 500 to inv1 and 675 to inv2
         */

        // modify the invoice line to have their amount > payment
        var indexInv1 = _.findIndex(this.params.mv_lines['[5,"",0]'], function (line) {return line.id === 109});
        this.params.mv_lines['[5,"",0]'][indexInv1] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0002", partner_name: "Agrolait",
             total_amount_currency_str: "", id: 109, credit: 0.0, journal_id: [1, "Customer Invoices"], amount_str: "$ 1200.00", debit: 1200.0,
             account_code: "101200", ref: "", already_paid: false};

        var indexInv2 = _.findIndex(this.params.mv_lines['[5,"",0]'], function (line) {return line.id === 112});
        this.params.mv_lines['[5,"",0]'][indexInv2] =
            {account_type: "receivable", amount_currency_str: "", currency_id: false, date_maturity: "2017-02-07", date: "2017-01-08",
             total_amount_str: "$ 1200.00", partner_id: 8, account_name: "101200 Account Receivable", name: "INV/2017/0003",
             partner_name: "Agrolait", total_amount_currency_str: "", id: 112, credit: 0.0, journal_id: [1, "Customer Invoices"],
             amount_str: "$ 1200.00", debit: 1200.0, account_code: "101200", ref: "", already_paid: false};

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                if (args.method === 'process_bank_statement_line') {
                    assert.deepEqual(args.args,
                        [
                            [5], // Id of the bank statement line

                            [{counterpart_aml_dicts:
                                [{name:"INV/2017/0002",
                                  debit: 0,
                                  credit: 500,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 109},

                                 {name: "INV/2017/0003",
                                  debit: 0,
                                  credit: 675,
                                  analytic_tag_ids: [[6, null, []]],
                                  counterpart_aml_id: 112}],

                              payment_aml_ids: [],
                              partner_id: 8,
                              to_check: false,
                              new_aml_dicts: []
                          }]
                        ], "should call process_bank_statement_line with correct counterpart_aml_dicts");
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first invoice
        // There should be the opportunity to reconcile partially
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.ok(widget.$('.cell_right .edit_amount').length,
            "should display the pencil to edit amount");

        // Add second invoice
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.ok(widget.$('.cell_right .edit_amount').length,
            "should display the pencil to edit amount");

        // Edit invoice first amount
        await testUtils.dom.click(widget.$('.edit_amount:first()'));
        await testUtils.fields.editAndTrigger(widget.$('.edit_amount_input:first()'),'500',['blur']);
        // Edit invoice second amount
        var $buttonReconcile = widget.$('button.o_reconcile:not(hidden)');
        await testUtils.dom.click(widget.$('.edit_amount:last()'));
        await testUtils.fields.editAndTrigger(widget.$('.edit_amount_input:last()'),'675',['blur']);

        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        await testUtils.dom.click($buttonReconcile,{allowInvisible:true});

        clientAction.destroy();
    });

    QUnit.test('Manual Reconciliation: remove a prop to attain balance and reconcile', async function (assert) {
        assert.expect(5);

        // tweak the data to fit our needs
        this.params.data_for_manual_reconciliation_widget['[283, null, "", 0, 6]'] = _.extend({}, this.params.data_for_manual_reconciliation_widget['[null,[282,283,284,285,286,287,288,308,499,500,501,502,503,504]]']);
        this.params.data_for_manual_reconciliation_widget['[283, null, "", 0, 6]'].accounts[0].reconciliation_proposition = [
            {account_id: 283, account_type: "other", amount_currency_str: "", currency_id: false, date_maturity: "2017-03-18", date: "2017-02-16",
             total_amount_str: "$ 500.00", partner_id: 8, account_name: "101000 Current Assets", name: "INV/2017/0987", partner_name: "Agrolait",
             total_amount_currency_str: "", id: 999, credit: 0.0, journal_id: [1, "Customer Invoices"], amount_str: "$ 500.00", debit: 500.0,
             account_code: "101000", ref: "", already_paid: false}
        ];

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        // Add first prop
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        assert.equal( widget.$('.cell_right .edit_amount').length, 0, "should not display the pencil to edit amount");

        // Add second prop
        await testUtils.dom.click(widget.$('.match:first .cell_account_code:first'));
        // Check that a create form is here

        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        var writeOffCreate = widget.$('div.create');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        assert.equal(writeOffCreate.find('input[name=amount]').val(), 500,
            'The right amount should be proposed for the write-off');

        // remove the first line, the other two will balance one another
        await testUtils.dom.click(widget.$('tr[data-line-id="999"] td:first'));

        var $buttonReconcile = widget.$('button.o_reconcile:visible');
        assert.equal($buttonReconcile.length, 1,
            'The reconcile button must be visible');

        await testUtils.dom.click($buttonReconcile);

        clientAction.destroy();
    });

    QUnit.test('Manual Reconciliation: No lines for account', async function (assert) {
        assert.expect(2);

        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The second reconciliation "line" is where it happens
        var widget = clientAction.widgets[1];

        var emptyLine = widget.$('tr.mv_line');

        assert.notOk('data-line-id' in emptyLine.getAttributes(),
            'Empty line should be empty');

        await testUtils.dom.click(emptyLine.find('td:first'));

        // Check that a create form is here
        var writeOffCreate = widget.$('div.create .create_account_id');

        assert.equal(writeOffCreate.length, 1,
            'A write-off creation should be present');

        clientAction.destroy();
    });

    QUnit.test('Tax on account receivable', async function(assert){
        assert.expect(21);

        this.params.data_for_manual_reconciliation_widget['[null,[282,283,284,285,286,287,288,308,499,500,501,502,503,504]]'].accounts = [];
        var clientAction = new ReconciliationClientAction.ManualAction(null, this.params.options);
        testUtils.mock.addMockEnvironment(clientAction, {
            data: this.params.data,
            session: {},
            mockRPC: function(route, args) {
                if (args.method === "name_search") {
                    switch (args.model) {
                        // mock the default mock to do the minimal processing required
                        // to get the available values for the droplists.
                        case 'account.account':
                            assert.step("Account");
                            return Promise.resolve(
                                _.map(this.data[args.model].records, function (record) {
                                    return [record.id, record.name];
                                })
                            );
                        case 'account.tax':
                            assert.step("Tax");
                            return Promise.resolve(
                                _.map(this.data[args.model].records, function (record) {
                                    return [record.id, record.display_name];
                                })
                            );
                        case 'account.journal':
                            assert.step("Journal");
                            return Promise.resolve(
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
                               'account_id', 'name', 'credit', 'debit', 'tax_repartition_line_id'),
                        {account_id: 287, name: "Tax 20.00%", credit: 0, debit: 36, tax_repartition_line_id: 2},
                        "Reconciliation rpc payload, new_mv_line_dicts.tax is correct"
                    );
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        var widget = clientAction.widgets[0];

        // Select invoice of 1k$, payment of 1k$ and payment of 180$
        var $tableToReconcile = widget.$('.match');
        var defs = _.map([6, 19, 21], function(id) {
            return testUtils.dom.click($tableToReconcile.find('tr.mv_line[data-line-id='+id+']:first td:first-child'));
        });
        await Promise.all(defs);
        assert.verifySteps([], "No rpc done");

        // Store the money in excess to the "account receivable" account with 20% taxes
        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));
        var $reconcileForm = widget.$(".create");
        await testUtils.dom.click($reconcileForm.find('.create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(101200 Account Receivable)').trigger('mouseover').trigger('click');
        await testUtils.nextTick();
        assert.verifySteps(["Account"], "Account rpc done");

        await testUtils.dom.click($reconcileForm.find('.create_tax_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(Tax 20.00%)').trigger('mouseover').trigger('click');
        await testUtils.nextTick();
        assert.verifySteps(["Tax"], "Tax rpc done");

        await testUtils.dom.click($reconcileForm.find('.create_journal_id input'),{allowInvisible:true});
        $('.ui-autocomplete .ui-menu-item a:contains(company 1 journal)').trigger('mouseover').trigger('click');
        await testUtils.nextTick();
        await testUtils.fields.editAndTrigger($reconcileForm.find('.create_label input'),'dummy text','input');
        await testUtils.dom.click($reconcileForm.find('.create_label input'));
        assert.verifySteps(["Journal"], "Journal rpc done");

        // Verify the two (gift + tax) lines were added to the list
        var $newLines = widget.$('tr.mv_line[data-line-id^=createLine]');
        var idx = ($($($newLines[0]).find("td")[3]).text().trim() === "dummy text") ? 0 : 1;

        var $newLineGiftTds = $($newLines[1 - idx]).find("td");
        assert.equal($($newLineGiftTds[0]).text().trim().replace(/[\u200B]/g, ''), "101200",
            "Gift line account number is valid");
        assert.equal($($newLineGiftTds[1]).text().trim(), "New",
            "Gift line is flagged as new");
        assert.equal($($newLineGiftTds[2]).text().trim(), "dummy text",
            "Gift line has the correct label");
        assert.equal($($newLineGiftTds[3]).text().trim(), "180.00",
            "Gift line has the correct left amount");
        assert.equal($($newLineGiftTds[4]).text().trim(), "",
            "Gift line has the correct right amount");

        var $newLineTaxeTds = $($newLines[idx]).find("td");
        assert.equal($($newLineTaxeTds[0]).text().trim().replace(/[\u200B]/g, ''), "101200",
            "Tax line account number is valid");
        assert.equal($($newLineTaxeTds[1]).text().trim(), "New",
            "Tax line is flagged as new");
        assert.equal($($newLineTaxeTds[2]).text().trim(), "Tax 20.00%",
            "Tax line has the correct label");
        assert.equal($($newLineTaxeTds[3]).text().trim(), "36.00",
            "Tax line has the correct left amount");
        assert.equal($($newLineTaxeTds[4]).text().trim(), "",
            "Tax line has the correct right amount");

        // Reconcile
        await testUtils.dom.click(widget.$("button.o_reconcile.btn.btn-primary:first"));
        assert.ok(true, "No error in reconciliation");

        clientAction.destroy();
    });

    QUnit.test('Reconcile temporarily and ask to check', async function(assert){
        assert.expect(4);
        this.params.options.context['to_check'] = true;
        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);

        testUtils.mock.addMockEnvironment(clientAction, {
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
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });
        await clientAction.appendTo($('#qunit-fixture'));
        var widget = clientAction.widgets[0];

        // Add a line as proposition
        // open the first line
        await testUtils.nextTick();
        await testUtils.dom.click(widget.$('.accounting_view tfoot td.cell_label'));
        await testUtils.dom.click(widget.$('.o_notebook .nav-link[href*="notebook_page_create"]'));

        var $reconcileForm = widget.$(".create");
        $reconcileForm.find('.create_account_id input').val('499001 Suspense Account').keydown().keyup();
        await testUtils.dom.click($reconcileForm.find('.create_account_id input'));
        $('.ui-autocomplete .ui-menu-item a:contains(499001 Suspense Account)')
            .trigger('mouseover')
            .trigger('click');
        await testUtils.nextTick();

        assert.equal($("button.o_validate.btn.btn-secondary.text-warning:first").length, 0, "should not display reconcile button in orange");
        await testUtils.dom.click($reconcileForm.find('.create_to_check input'));
        assert.equal($("button.o_validate.btn.btn-secondary.text-warning:first").length, 1, "should display reconcile button in orange");

        testUtils.mock.intercept(clientAction, 'call_service', function (event) {
            assert.deepEqual(event.data.args[1].args,
                [[5],[{partner_id: 8,
                        counterpart_aml_dicts: [],
                        payment_aml_ids: [],
                        new_aml_dicts: [{account_id: 499,
                            credit: 1175,
                            debit: 0,
                            analytic_tag_ids: [[6, null, []]],
                            name: 'SAJ/2014/002 and SAJ/2014/003',
                        }],
                        to_check: true,
                }]],
                "Should call process_bank_statement_line with to_check set to true");
            var def = testUtils.makeTestPromise();
            def.abort = function () {};
            event.data.callback(def);
        });

        await testUtils.dom.click(widget.$("button.o_validate.btn.btn-secondary:first"));
        assert.ok(true, "No error in reconciliation");

        clientAction.destroy();
    });

    QUnit.test('Reconciliation Models handle analytic tags', async function (assert) {
        assert.expect(6);

        var clientAction = new ReconciliationClientAction.StatementAction(null, this.params.options);
        testUtils.addMockEnvironment(clientAction, {
            data: this.params.data,
            mockRPC: function (route, args) {
                if (args.method === 'process_bank_statement_line') {
                    var new_aml_dicts = args.args[1][0].new_aml_dicts;
                    assert.strictEqual(new_aml_dicts.length, 2);
                    // I personnally judge the following use case rotten, since
                    // the first and the second line wouldn't have the same tags
                    assert.deepEqual(new_aml_dicts[0].analytic_tag_ids, [[6, null, [1, 2]]]);
                    assert.deepEqual(new_aml_dicts[1].analytic_tag_ids, [[6, null, [2]]]);
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
            archs: {
                'account.bank.statement.line,false,search': '<search string="Statement Line"><field name="display_name"/></search>',
            },
        });

        await clientAction.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();

        // The first reconciliation "line" is where it happens
        var widget = clientAction.widgets[0];

        await testUtilsDom.click(widget.$('.nav-create:visible'));
        await testUtilsDom.click(widget.$('.quick_add button:contains("Double")'));
        assert.containsN(widget, '.create_analytic_tag_ids .o_field_many2manytags .badge', 2,
            'Two tags are loaded');
        assert.containsOnce(widget, '.create_analytic_tag_ids .o_field_many2manytags .badge:contains("Come together")',
            'Tags should have a name');
        assert.containsOnce(widget, '.create_analytic_tag_ids .o_field_many2manytags .badge:contains("Right now")',
            'Tags should have a name');

        await testUtilsDom.click(widget.$('.create_analytic_tag_ids .o_field_many2manytags .badge a.o_delete:first()'));

        await testUtilsDom.click(widget.$('.o_reconcile:visible'));

        clientAction.destroy();
    });
});
});
