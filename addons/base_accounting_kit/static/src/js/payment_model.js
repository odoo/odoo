odoo.define('base_accounting_kit.ReconciliationModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var field_utils = require('web.field_utils');
var utils = require('web.utils');
var session = require('web.session');
//var WarningDialog = require('web.CrashManager').WarningDialog;
var core = require('web.core');
var _t = core._t;


/**
 * Model use to fetch, format and update 'account.reconciliation.widget',
 * datas allowing reconciliation
 *
 * The statement internal structure::
 *
 *  {
 *      valuenow: integer
 *      valuenow: valuemax
 *      [bank_statement_line_id]: {
 *          id: integer
 *          display_name: string
 *      }
 *      reconcileModels: [object]
 *      accounts: {id: code}
 *  }
 *
 * The internal structure of each line is::
 *
 *   {
 *      balance: {
 *          type: number - show/hide action button
 *          amount: number - real amount
 *          amount_str: string - formated amount
 *          account_code: string
 *      },
 *      st_line: {
 *          partner_id: integer
 *          partner_name: string
 *      }
 *      mode: string ('inactive', 'match_rp', 'match_other', 'create')
 *      reconciliation_proposition: {
 *          id: number|string
 *          partial_amount: number
 *          invalid: boolean - through the invalid line (without account, label...)
 *          account_code: string
 *          date: string
 *          date_maturity: string
 *          label: string
 *          amount: number - real amount
 *          amount_str: string - formated amount
 *          [already_paid]: boolean
 *          [partner_id]: integer
 *          [partner_name]: string
 *          [account_code]: string
 *          [journal_id]: {
 *              id: integer
 *              display_name: string
 *          }
 *          [ref]: string
 *          [is_partially_reconciled]: boolean
 *          [to_check]: boolean
 *          [amount_currency_str]: string|false (amount in record currency)
 *      }
 *      mv_lines_match_rp: object - idem than reconciliation_proposition
 *      mv_lines_match_other: object - idem than reconciliation_proposition
 *      limitMoveLines: integer
 *      filter: string
 *      [createForm]: {
 *          account_id: {
 *              id: integer
 *              display_name: string
 *          }
 *          tax_ids: {
 *              id: integer
 *              display_name: string
 *          }
 *          analytic_account_id: {
 *              id: integer
 *              display_name: string
 *          }
 *          analytic_tag_ids: {
 *          }
 *          label: string
 *          amount: number,
 *          [journal_id]: {
 *              id: integer
 *              display_name: string
 *          }
 *      }
 *   }
 */
var StatementModel = BasicModel.extend({
    avoidCreate: false,
    quickCreateFields: ['account_id', 'amount', 'analytic_account_id', 'label', 'tax_ids', 'force_tax_included', 'analytic_tag_ids', 'to_check'],

    // overridden in ManualModel
    modes: ['create', 'match_rp', 'match_other'],

    /**
     * @override
     *
     * @param {Widget} parent
     * @param {object} options
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.reconcileModels = [];
        this.lines = {};
        this.valuenow = 0;
        this.valuemax = 0;
        this.alreadyDisplayed = [];
        this.domain = [];
        this.defaultDisplayQty = options && options.defaultDisplayQty || 10;
        this.limitMoveLines = options && options.limitMoveLines || 15;
        this.display_context = 'init';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * add a reconciliation proposition from the matched lines
     * We also display a warning if the user tries to add 2 line with different
     * account type
     *
     * @param {string} handle
     * @param {number} mv_line_id
     * @returns {Promise}
     */
    addProposition: function (handle, mv_line_id) {
        var self = this;
        var line = this.getLine(handle);
        var prop = _.clone(_.find(line['mv_lines_'+line.mode], {'id': mv_line_id}));
        this._addProposition(line, prop);
        line['mv_lines_'+line.mode] = _.filter(line['mv_lines_'+line.mode], l => l['id'] != mv_line_id);

        // remove all non valid lines
        line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (prop) {return prop && !prop.invalid;});

        // Onchange the partner if not already set on the statement line.
        if(!line.st_line.partner_id && line.reconciliation_proposition
            && line.reconciliation_proposition.length == 1 && prop.partner_id && line.type === undefined){
            return this.changePartner(handle, {'id': prop.partner_id, 'display_name': prop.partner_name}, true);
        }

        return Promise.all([
            this._computeLine(line),
            this._performMoveLine(handle, 'match_rp', line.mode == 'match_rp'? 1 : 0),
            this._performMoveLine(handle, 'match_other', line.mode == 'match_other'? 1 : 0)
        ]);
    },
    /**
     * change the filter for the target line and fetch the new matched lines
     *
     * @param {string} handle
     * @param {string} filter
     * @returns {Promise}
     */
    changeFilter: function (handle, filter) {
        var line = this.getLine(handle);
        line['filter_'+line.mode] = filter;
        line['mv_lines_'+line.mode] = [];
        return this._performMoveLine(handle, line.mode);
    },
    /**
     * change the mode line ('inactive', 'match_rp', 'match_other', 'create'),
     * and fetch the new matched lines or prepare to create a new line
     *
     * ``match_rp``
     *   display the matched lines from receivable/payable accounts, the user
     *   can select the lines to apply there as proposition
     * ``match_other``
     *   display the other matched lines, the user can select the lines to apply
     *   there as proposition
     * ``create``
     *   display fields and quick create button to create a new proposition
     *   for the reconciliation
     *
     * @param {string} handle
     * @param {'inactive' | 'match_rp' | 'create'} mode
     * @returns {Promise}
     */
    changeMode: function (handle, mode) {
        var self = this;
        var line = this.getLine(handle);
        if (mode === 'default') {
            var match_requests = self.modes.filter(x => x.startsWith('match')).map(x => this._performMoveLine(handle, x))
            return Promise.all(match_requests).then(function() {
                return self.changeMode(handle, self._getDefaultMode(handle));
            });
        }
        if (mode === 'next') {
            var available_modes = self._getAvailableModes(handle)
            mode = available_modes[(available_modes.indexOf(line.mode) + 1) % available_modes.length];
        }
        line.mode = mode;
        if (['match_rp', 'match_other'].includes(line.mode)) {
            if (!(line['mv_lines_' + line.mode] && line['mv_lines_' + line.mode].length)) {
                return this._performMoveLine(handle, line.mode);
            } else {
                return this._formatMoveLine(handle, line.mode, []);
            }
        }
        if (line.mode === 'create') {
            return this.createProposition(handle);
        }
        return Promise.resolve();
    },
    /**
     * fetch the more matched lines
     *
     * @param {string} handle
     * @returns {Promise}
     */
    changeOffset: function (handle) {
        var line = this.getLine(handle);
        return this._performMoveLine(handle, line.mode);
    },
    /**
     * change the partner on the line and fetch the new matched lines
     *
     * @param {string} handle
     * @param {bool} preserveMode
     * @param {Object} partner
     * @param {string} partner.display_name
     * @param {number} partner.id
     * @returns {Promise}
     */
    changePartner: function (handle, partner, preserveMode) {
        var self = this;
        var line = this.getLine(handle);
        line.st_line.partner_id = partner && partner.id;
        line.st_line.partner_name = partner && partner.display_name || '';
        line.mv_lines_match_rp = [];
        line.mv_lines_match_other = [];
        return Promise.resolve(partner && this._changePartner(handle, partner.id))
                .then(function() {
                    if(line.st_line.partner_id){
                        _.each(line.reconciliation_proposition, function(prop){
                            if(prop.partner_id != line.st_line.partner_id){
                                line.reconciliation_proposition = [];
                                return false;
                            }
                        });
                    }
                    return self._computeLine(line);
                })
                .then(function () {
                    return self.changeMode(handle, preserveMode ? line.mode : 'default', true);
                })

    },
    /**
     * close the statement
     * @returns {Promise<number>} resolves to the res_id of the closed statements
     */
    closeStatement: function () {
        var self = this;
        return this._rpc({
                model: 'account.bank.statement.line',
                method: 'button_confirm_bank',
                args: [self.bank_statement_line_id.id],
            })
            .then(function () {
                return self.bank_statement_line_id.id;
            });
    },
    /**
     *
     * then open the first available line
     *
     * @param {string} handle
     * @returns {Promise}
     */
    createProposition: function (handle) {
        var line = this.getLine(handle);
        var prop = _.filter(line.reconciliation_proposition, '__focus');
        prop = this._formatQuickCreate(line);
        line.reconciliation_proposition.push(prop);
        line.createForm = _.pick(prop, this.quickCreateFields);
        return this._computeLine(line);
    },
    /**
     * Return context information and journal_id
     * @returns {Object} context
     */
    getContext: function () {
        return this.context;
    },
    /**
     * Return the lines that needs to be displayed by the widget
     *
     * @returns {Object} lines that are loaded and not yet displayed
     */
    getStatementLines: function () {
        var self = this;
        var linesToDisplay = _.pick(this.lines, function(value, key, object) {
            if (value.visible === true && self.alreadyDisplayed.indexOf(key) === -1) {
                self.alreadyDisplayed.push(key);
                return object;
            }
        });
        return linesToDisplay;
    },
    /**
     * Return a boolean telling if load button needs to be displayed or not
     * overridden in ManualModel
     *
     * @returns {boolean} true if load more button needs to be displayed
     */
    hasMoreLines: function () {
        var notDisplayed = _.filter(this.lines, function(line) { return !line.visible; });
        if (notDisplayed.length > 0) {
            return true;
        }
        return false;
    },
    /**
     * get the line data for this handle
     *
     * @param {Object} handle
     * @returns {Object}
     */
    getLine: function (handle) {
        return this.lines[handle];
    },
    /**
     * load data from
     *
     * - 'account.bank.statement' fetch the line id and bank_statement_id info
     * - 'account.reconcile.model'  fetch all reconcile model (for quick add)
     * - 'account.account' fetch all account code
     * - 'account.reconciliation.widget' fetch each line data
     *
     * overridden in ManualModel
     * @param {Object} context
     * @param {number[]} context.statement_line_ids
     * @returns {Promise}
     */
    load: function (context) {
        var self = this;
        this.context = context;
        this.statement_line_ids = context.statement_line_ids;
        if (this.statement_line_ids === undefined) {
            // This could be undefined if the user pressed F5, take everything as fallback instead of rainbowman
            return self._rpc({
                model: 'account.bank.statement.line',
                method: 'search_read',
                fields: ['id'],
                domain: [['journal_id', '=?', context.active_id]],
            }).then(function (result) {
                self.statement_line_ids = result.map(r => r.id);
                return self.reload()
            })
        } else {
            return self.reload();
        }

    },
    /**
     * Load more bank statement line
     *
     * @param {integer} qty quantity to load
     * @returns {Promise}
     */
    loadMore: function(qty) {
        if (qty === undefined) {
            qty = this.defaultDisplayQty;
        }
        var ids = _.pluck(this.lines, 'id');
        ids = ids.splice(this.pagerIndex, qty);
        this.pagerIndex += qty;
        return this.loadData(ids, this._getExcludedIds());
    },
    /**
     * RPC method to load informations on lines
     * overridden in ManualModel
     *
     * @param {Array} ids ids of bank statement line passed to rpc call
     * @param {Array} excluded_ids list of move_line ids that needs to be excluded from search
     * @returns {Promise}
     */
    loadData: function(ids) {
        var self = this;
        var excluded_ids = this._getExcludedIds();
        return self._rpc({
            model: 'account.reconciliation.widget',
            method: 'get_bank_statement_line_data',
            args: [ids, excluded_ids],
            context: self.context,
        })
        .then(function(res){
            return self._formatLine(res['lines']);
        })
    },
    /**
     * Reload all data
     */
    reload: function() {
        var self = this;
        self.alreadyDisplayed = [];
        self.lines = {};
        self.pagerIndex = 0;
        var def_statement = this._rpc({
                model: 'account.reconciliation.widget',
                method: 'get_bank_statement_data',
                kwargs: {"bank_statement_line_ids":self.statement_line_ids, "srch_domain":self.domain},
                context: self.context,
            })
            .then(function (statement) {
                self.statement = statement;
                self.bank_statement_line_id = self.statement_line_ids.length === 1 ? {id: self.statement_line_ids[0], display_name: statement.statement_name} : false;
                self.valuenow = self.valuenow || statement.value_min;
                self.valuemax = self.valuemax || statement.value_max;
                self.context.journal_id = statement.journal_id;
                _.each(statement.lines, function (res) {
                    var handle = _.uniqueId('rline');
                    self.lines[handle] = {
                        id: res.st_line.id,
                        partner_id: res.st_line.partner_id,
                        handle: handle,
                        reconciled: false,
                        mode: 'inactive',
                        mv_lines_match_rp: [],
                        mv_lines_match_other: [],
                        filter_match_rp: "",
                        filter_match_other: "",
                        reconciliation_proposition: [],
                        reconcileModels: [],
                    };
                });
            });
        var domainReconcile = [];
        if (self.context && self.context.company_ids) {
            domainReconcile.push(['company_id', 'in', self.context.company_ids]);
        }
        if (self.context && self.context.active_model === 'account.journal' && self.context.active_ids) {
            domainReconcile.push('|');
            domainReconcile.push(['match_journal_ids', '=', false]);
            domainReconcile.push(['match_journal_ids', 'in', self.context.active_ids]);
        }
        var def_reconcileModel = this._loadReconciliationModel({domainReconcile: domainReconcile});
        var def_account = this._rpc({
                model: 'account.account',
                method: 'search_read',
                fields: ['code'],
            })
            .then(function (accounts) {
                self.accounts = _.object(_.pluck(accounts, 'id'), _.pluck(accounts, 'code'));
            });
        var def_taxes = self._loadTaxes();
        return Promise.all([def_statement, def_reconcileModel, def_account, def_taxes]).then(function () {
            _.each(self.lines, function (line) {
                line.reconcileModels = self.reconcileModels;
            });
            var ids = _.pluck(self.lines, 'id');
            ids = ids.splice(0, self.defaultDisplayQty);
            self.pagerIndex = ids.length;
            return self._formatLine(self.statement.lines);
        });
    },
    _readAnalyticTags: function (params) {
        var self = this;
        this.analyticTags = {};
        if (!params || !params.res_ids || !params.res_ids.length) {
            return $.when();
        }
        var fields = (params && params.fields || []).concat(['id', 'display_name']);
        return this._rpc({
                model: 'account.analytic.tag',
                method: 'read',
                args: [
                    params.res_ids,
                    fields,
                ],
            }).then(function (tags) {
                for (var i=0; i<tags.length; i++) {
                    var tag = tags[i];
                    self.analyticTags[tag.id] = tag;
                }
            });
    },
    _loadReconciliationModel: function (params) {
        var self = this;
        return this._rpc({
                model: 'account.reconcile.model',
                method: 'search_read',
                domain: params.domainReconcile || [],
            })
            .then(function (reconcileModels) {
               var analyticTagIds = [];
                for (var i=0; i<reconcileModels.length; i++) {
                    var modelTags = reconcileModels[i].analytic_tag_ids || [];
                    for (var j=0; j<modelTags.length; j++) {
                        if (analyticTagIds.indexOf(modelTags[j]) === -1) {
                            analyticTagIds.push(modelTags[j]);
                        }
                    }
                }
                return self._readAnalyticTags({res_ids: analyticTagIds}).then(function () {
                    for (var i=0; i<reconcileModels.length; i++) {
                        var recModel = reconcileModels[i];
                        var analyticTagData = [];
                        var modelTags = reconcileModels[i].analytic_tag_ids || [];
                        for (var j=0; j<modelTags.length; j++) {
                            var tagId = modelTags[j];
                            analyticTagData.push([tagId, self.analyticTags[tagId].display_name])
                        }
                        recModel.analytic_tag_ids = analyticTagData;
                    }
                    self.reconcileModels = reconcileModels;
                });
            });
    },
    _loadTaxes: function(){
        var self = this;
        self.taxes = {};
        return this._rpc({
                model: 'account.tax',
                method: 'search_read',
                fields: ['price_include', 'name'],
            }).then(function (taxes) {
                _.each(taxes, function(tax){
                    self.taxes[tax.id] = {
                        price_include: tax.price_include,
                        display_name: tax.name,
                    };
                });
                return taxes;
            });
    },
    /**
     * Add lines into the propositions from the reconcile model
     * Can add 2 lines, and each with its taxes. The second line become editable
     * in the create mode.
     *
     * @see 'updateProposition' method for more informations about the
     * 'amount_type'
     *
     * @param {string} handle
     * @param {integer} reconcileModelId
     * @returns {Promise}
     */
    quickCreateProposition: function (handle, reconcileModelId) {
        var self = this;
        var line = this.getLine(handle);
        var reconcileModel = _.find(this.reconcileModels, function (r) {return r.id === reconcileModelId;});
        var fields = ['account_id', 'amount', 'amount_type', 'analytic_account_id', 'journal_id', 'label', 'force_tax_included', 'tax_ids', 'analytic_tag_ids', 'to_check', 'amount_from_label_regex', 'decimal_separator'];
        this._blurProposition(handle);
        var focus = this._formatQuickCreate(line, _.pick(reconcileModel, fields));
        focus.reconcileModelId = reconcileModelId;
        line.reconciliation_proposition.push(focus);
        var defs = [];
        if (reconcileModel.has_second_line) {
            defs.push(self._computeLine(line).then(function() {
                var second = {};
                _.each(fields, function (key) {
                    second[key] = ("second_"+key) in reconcileModel ? reconcileModel["second_"+key] : reconcileModel[key];
                });
                var second_focus = self._formatQuickCreate(line, second);
                second_focus.reconcileModelId = reconcileModelId;
                line.reconciliation_proposition.push(second_focus);
                self._computeReconcileModels(handle, reconcileModelId);
            }))
        }
        return Promise.all(defs).then(function() {
            line.createForm = _.pick(focus, self.quickCreateFields);
            return self._computeLine(line);
        })
    },
    /**
     * Remove a proposition and switch to an active mode ('create' or 'match_rp' or 'match_other')
     * overridden in ManualModel
     *
     * @param {string} handle
     * @param {number} id (move line id)
     * @returns {Promise}
     */
    removeProposition: function (handle, id) {
        var self = this;
        var line = this.getLine(handle);
        var defs = [];
        var prop = _.find(line.reconciliation_proposition, {'id' : id});
        if (prop) {
            line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (p) {
                return p.id !== prop.id && p.id !== prop.link && p.link !== prop.id && (!p.link || p.link !== prop.link);
            });
            if (prop['reconcileModelId'] === undefined) {
                if (['receivable', 'payable', 'liquidity'].includes(prop.account_type)) {
                    line.mv_lines_match_rp.unshift(prop);
                } else {
                    line.mv_lines_match_other.unshift(prop);
                }
            }

            // No proposition left and then, reset the st_line partner.
            if(line.reconciliation_proposition.length == 0 && line.st_line.has_no_partner)
                defs.push(self.changePartner(line.handle));
        }
        line.mode = (id || line.mode !== "create") && isNaN(id) ? 'create' : 'match_rp';
        defs.push(this._computeLine(line));
        return Promise.all(defs).then(function() {
            return self.changeMode(handle, line.mode, true);
        })
    },
    getPartialReconcileAmount: function(handle, data) {
        var line = this.getLine(handle);
        var formatOptions = {
            currency_id: line.st_line.currency_id,
            noSymbol: true,
        };
        var prop = _.find(line.reconciliation_proposition, {'id': data.data});
        if (prop) {
            var amount = prop.partial_amount || prop.amount;
            // Check if we can get a partial amount that would directly set balance to zero
            var partial = Math.abs(line.balance.amount + amount);
            if (Math.abs(line.balance.amount) >= Math.abs(amount)) {
                amount = Math.abs(amount);
            } else if (partial <= Math.abs(prop.amount) && partial >= 0) {
                amount = partial;
            } else {
                amount = Math.abs(amount);
            }
            return field_utils.format.monetary(amount, {}, formatOptions);
        }
    },
    /**
     * Force the partial reconciliation to display the reconciliate button.
     *
     * @param {string} handle
     * @returns {Promise}
     */
    partialReconcile: function(handle, data) {
        var line = this.getLine(handle);
        var prop = _.find(line.reconciliation_proposition, {'id' : data.mvLineId});
        if (prop) {
            var amount = data.amount;
            try {
                amount = field_utils.parse.float(data.amount);
            }
            catch (err) {
                amount = NaN;
            }
            // Amount can't be greater than line.amount and can not be negative and must be a number
            // the amount we receive will be a string, so take sign of previous line amount in consideration in order to put
            // the amount in the correct left or right column
            if (amount >= Math.abs(prop.amount) || amount <= 0 || isNaN(amount)) {
                delete prop.partial_amount_str;
                delete prop.partial_amount;
                if (isNaN(amount) || amount < 0) {
                    this.do_warn(_.str.sprintf(_t('The amount %s is not a valid partial amount'), data.amount));
                }
                return this._computeLine(line);
            }
            else {
                var format_options = { currency_id: line.st_line.currency_id };
                prop.partial_amount = (prop.amount > 0 ? 1 : -1)*amount;
                prop.partial_amount_str = field_utils.format.monetary(Math.abs(prop.partial_amount), {}, format_options);
            }
        }
        return this._computeLine(line);
    },
    /**
     * Change the value of the editable proposition line or create a new one.
     *
     * If the editable line comes from a reconcile model with 2 lines
     * and their 'amount_type' is "percent"
     * and their total equals 100% (this doesn't take into account the taxes
     * who can be included or not)
     * Then the total is recomputed to have 100%.
     *
     * @param {string} handle
     * @param {*} values
     * @returns {Promise}
     */
    updateProposition: function (handle, values) {
        var self = this;
        var line = this.getLine(handle);
        var prop = _.last(_.filter(line.reconciliation_proposition, '__focus'));
        if ('to_check' in values && values.to_check === false) {
            // check if we have another line with to_check and if yes don't change value of this proposition
            prop.to_check = line.reconciliation_proposition.some(function(rec_prop, index) {
                return rec_prop.id !== prop.id && rec_prop.to_check;
            });
        }
        if (!prop) {
            prop = this._formatQuickCreate(line);
            line.reconciliation_proposition.push(prop);
        }
        _.each(values, function (value, fieldName) {
            if (fieldName === 'analytic_tag_ids') {
                switch (value.operation) {
                    case "ADD_M2M":
                        // handle analytic_tag selection via drop down (single dict) and
                        // full widget (array of dict)
                        var vids = _.isArray(value.ids) ? value.ids : [value.ids];
                        _.each(vids, function (val) {
                            if (!_.findWhere(prop.analytic_tag_ids, {id: val.id})) {
                                prop.analytic_tag_ids.push(val);
                            }
                        });
                        break;
                    case "FORGET":
                        var id = self.localData[value.ids[0]].ref;
                        prop.analytic_tag_ids = _.filter(prop.analytic_tag_ids, function (val) {
                            return val.id !== id;
                        });
                        break;
                }
            }
            else if (fieldName === 'tax_ids') {
                switch(value.operation) {
                    case "ADD_M2M":
                        prop.__tax_to_recompute = true;
                        var vids = _.isArray(value.ids) ? value.ids : [value.ids];
                        _.each(vids, function(val){
                            if (!_.findWhere(prop.tax_ids, {id: val.id})) {
                                value.ids.price_include = self.taxes[val.id] ? self.taxes[val.id].price_include : false;
                                prop.tax_ids.push(val);
                            }
                        });
                        break;
                    case "FORGET":
                        prop.__tax_to_recompute = true;
                        var id = self.localData[value.ids[0]].ref;
                        prop.tax_ids = _.filter(prop.tax_ids, function (val) {
                            return val.id !== id;
                        });
                        break;
                }
            }
            else {
                prop[fieldName] = values[fieldName];
            }
        });
        if ('account_id' in values) {
            prop.account_code = prop.account_id ? this.accounts[prop.account_id.id] : '';
        }
        if ('amount' in values) {
            prop.base_amount = values.amount;
            if (prop.reconcileModelId) {
                this._computeReconcileModels(handle, prop.reconcileModelId);
            }
        }
        if ('force_tax_included' in values || 'amount' in values || 'account_id' in values) {
            prop.__tax_to_recompute = true;
        }
        line.createForm = _.pick(prop, this.quickCreateFields);
        // If you check/uncheck the force_tax_included box, reset the createForm amount.
        if(prop.base_amount)
            line.createForm.amount = prop.base_amount;
        if (prop.tax_ids.length !== 1 ) {
            // When we have 0 or more than 1 taxes, reset the base_amount and force_tax_included, otherwise weird behavior can happen
            prop.amount = prop.base_amount;
            line.createForm.force_tax_included = false;
        }
        return this._computeLine(line);
    },
    /**
     * Format the value and send it to 'account.reconciliation.widget' model
     * Update the number of validated lines
     * overridden in ManualModel
     *
     * @param {(string|string[])} handle
     * @returns {Promise<Object>} resolved with an object who contains
     *   'handles' key
     */
    validate: function (handle) {
        var self = this;
        this.display_context = 'validate';
        var handles = [];
        if (handle) {
            handles = [handle];
        } else {
            _.each(this.lines, function (line, handle) {
                if (!line.reconciled && line.balance && !line.balance.amount && line.reconciliation_proposition.length) {
                    handles.push(handle);
                }
            });
        }
        var ids = [];
        var values = [];
        var handlesPromises = [];
        _.each(handles, function (handle) {
            var line = self.getLine(handle);
            var props = _.filter(line.reconciliation_proposition, function (prop) {return !prop.invalid;});
            var computeLinePromise;
            if (props.length === 0) {
                // Usability: if user has not chosen any lines and click validate, it has the same behavior
                // as creating a write-off of the same amount.
                props.push(self._formatQuickCreate(line, {
                    account_id: [line.st_line.open_balance_account_id, self.accounts[line.st_line.open_balance_account_id]],
                }));
                // update balance of line otherwise it won't be to zero and another line will be added
                line.reconciliation_proposition.push(props[0]);
                computeLinePromise = self._computeLine(line);
            }
            ids.push(line.id);
            handlesPromises.push(Promise.resolve(computeLinePromise).then(function() {
                var values_dict = {
                    "partner_id": line.st_line.partner_id,
                    "counterpart_aml_dicts": _.map(_.filter(props, function (prop) {
                        return !isNaN(prop.id) && !prop.already_paid;
                    }), self._formatToProcessReconciliation.bind(self, line)),
                    "payment_aml_ids": _.pluck(_.filter(props, function (prop) {
                        return !isNaN(prop.id) && prop.already_paid;
                    }), 'id'),
                    "new_aml_dicts": _.map(_.filter(props, function (prop) {
                        return isNaN(prop.id) && prop.display;
                    }), self._formatToProcessReconciliation.bind(self, line)),
                    "to_check": line.to_check,
                };

                // If the lines are not fully balanced, create an unreconciled amount.
                // line.st_line.currency_id is never false here because its equivalent to
                // statement_line.currency_id or statement_line.journal_id.currency_id or statement_line.journal_id.company_id.currency_id (Python-side).
                // see: get_statement_line_for_reconciliation_widget method in account/models/account_bank_statement.py for more details
                var currency = session.get_currency(line.st_line.currency_id);
                var balance = line.balance.amount;
                if (!utils.float_is_zero(balance, currency.digits[1])) {
                    var unreconciled_amount_dict = {
                        'account_id': line.st_line.open_balance_account_id,
                        'credit': balance > 0 ? balance : 0,
                        'debit': balance < 0 ? -balance : 0,
                        'name': line.st_line.name + ' : ' + _t("Open balance"),
                    };
                    values_dict['new_aml_dicts'].push(unreconciled_amount_dict);
                }
                values.push(values_dict);
                line.reconciled = true;
            }));

            _.each(self.lines, function(other_line) {
                if (other_line != line) {
                    var filtered_prop = other_line.reconciliation_proposition.filter(p => !line.reconciliation_proposition.map(l => l.id).includes(p.id));
                    if (filtered_prop.length != other_line.reconciliation_proposition.length) {
                        other_line.need_update = true;
                        other_line.reconciliation_proposition = filtered_prop;
                    }
                    self._computeLine(line);
                }
            })
        });

        return Promise.all(handlesPromises).then(function() {
            return self._rpc({
                    model: 'account.reconciliation.widget',
                    method: 'process_bank_statement_line',
                    args: [ids, values],
                    context: self.context,
                })
                .then(self._validatePostProcess.bind(self))
                .then(function () {
                    self.valuenow += handles.length;
                    return {handles: handles};
                });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * add a line proposition after checking receivable and payable accounts constraint
     *
     * @private
     * @param {Object} line
     * @param {Object} prop
     */
    _addProposition: function (line, prop) {
        line.reconciliation_proposition.push(prop);
    },
    /**
     * stop the editable proposition line and remove it if it's invalid then
     * compute the line
     *
     * See :func:`_computeLine`
     *
     * @private
     * @param {string} handle
     * @returns {Promise}
     */
    _blurProposition: function (handle) {
        var line = this.getLine(handle);
        line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (l) {
            l.__focus = false;
            return !l.invalid;
        });
    },
    /**
     * When changing partner, read property_account_receivable and payable
     * of that partner because the counterpart account might cahnge depending
     * on the partner
     *
     * @private
     * @param {string} handle
     * @param {integer} partner_id
     * @returns {Promise}
     */
    _changePartner: function (handle, partner_id) {
        var self = this;
        return this._rpc({
                model: 'res.partner',
                method: 'read',
                args: [partner_id, ["property_account_receivable_id", "property_account_payable_id"]],
            }).then(function (result) {
                if (result.length > 0) {
                    var line = self.getLine(handle);
                    self.lines[handle].st_line.open_balance_account_id = line.balance.amount < 0 ? result[0]['property_account_payable_id'][0] : result[0]['property_account_receivable_id'][0];
                }
            });
    },
    /**
     * Calculates the balance; format each proposition amount_str and mark as
     * invalid the line with empty account_id, amount or label
     * Check the taxes server side for each updated propositions with tax_ids
     * extended by ManualModel
     *
     * @private
     * @param {Object} line
     * @returns {Promise}
     */
    _computeLine: function (line) {
        //balance_type
        var self = this;

        // compute taxes
        var tax_defs = [];
        var reconciliation_proposition = [];
        var formatOptions = {
            currency_id: line.st_line.currency_id,
        };
        line.to_check = false;
        _.each(line.reconciliation_proposition, function (prop) {
            if (prop.to_check) {
                // If one of the proposition is to_check, set the global to_check flag to true
                line.to_check = true;
            }
            if (prop.tax_repartition_line_id) {
                if (!_.find(line.reconciliation_proposition, {'id': prop.link}).__tax_to_recompute) {
                    reconciliation_proposition.push(prop);
                }
                return;
            }
            if (!prop.already_paid && parseInt(prop.id)) {
                prop.is_move_line = true;
            }
            reconciliation_proposition.push(prop);

            if (prop.tax_ids && prop.tax_ids.length && prop.__tax_to_recompute && prop.base_amount) {
                reconciliation_proposition = _.filter(reconciliation_proposition, function (p) {
                    return !p.tax_repartition_line_id || p.link !== prop.id;
                });
                var args = [prop.tax_ids.map(function(el){return el.id;}), prop.base_amount, formatOptions.currency_id];
                var add_context = {'round': true};
                if(prop.tax_ids.length === 1 && line.createForm && line.createForm.force_tax_included)
                    add_context.force_price_include = true;
                tax_defs.push(self._rpc({
                        model: 'account.tax',
                        method: 'json_friendly_compute_all',
                        args: args,
                        context: $.extend({}, self.context || {}, add_context),
                    })
                    .then(function (result) {
                        _.each(result.taxes, function(tax){
                            var tax_prop = self._formatQuickCreate(line, {
                                'link': prop.id,
                                'tax_ids': tax.tax_ids,
                                'tax_repartition_line_id': tax.tax_repartition_line_id,
                                'tag_ids': tax.tag_ids,
                                'amount': tax.amount,
                                'label': prop.label ? prop.label + " " + tax.name : tax.name,
                                'date': prop.date,
                                'account_id': tax.account_id ? [tax.account_id, null] : prop.account_id,
                                'analytic': tax.analytic,
                                '__focus': false
                            });

                            prop.tax_exigible = tax.tax_exigibility === 'on_payment' ? true : undefined;
                            prop.amount = tax.base;
                            prop.amount_str = field_utils.format.monetary(Math.abs(prop.amount), {}, formatOptions);
                            prop.invalid = !self._isValid(prop);

                            tax_prop.amount_str = field_utils.format.monetary(Math.abs(tax_prop.amount), {}, formatOptions);
                            tax_prop.invalid = prop.invalid;

                            reconciliation_proposition.push(tax_prop);
                        });

                        prop.tag_ids = result.base_tags;
                    }));
            } else {
                prop.amount_str = field_utils.format.monetary(Math.abs(prop.amount), {}, formatOptions);
                prop.display = self._isDisplayedProposition(prop);
                prop.invalid = !self._isValid(prop);
            }
        });

        return Promise.all(tax_defs).then(function () {
            _.each(reconciliation_proposition, function (prop) {
                prop.__tax_to_recompute = false;
            });
            line.reconciliation_proposition = reconciliation_proposition;

            var amount_currency = 0;
            var total = line.st_line.amount || 0;
            var isOtherCurrencyId = _.uniq(_.pluck(_.reject(reconciliation_proposition, 'invalid'), 'currency_id'));
            isOtherCurrencyId = isOtherCurrencyId.length === 1 && !total && isOtherCurrencyId[0] !== formatOptions.currency_id ? isOtherCurrencyId[0] : false;

            _.each(reconciliation_proposition, function (prop) {
                if (!prop.invalid) {
                    total -= prop.partial_amount || prop.amount;
                    if (isOtherCurrencyId) {
                        amount_currency -= (prop.amount < 0 ? -1 : 1) * Math.abs(prop.amount_currency);
                    }
                }
            });
            var company_currency = session.get_currency(line.st_line.currency_id);
            var company_precision = company_currency && company_currency.digits[1] || 2;
            total = utils.round_decimals(total, company_precision) || 0;
            if(isOtherCurrencyId){
                var other_currency = session.get_currency(isOtherCurrencyId);
                var other_precision = other_currency && other_currency.digits[1] || 2;
                amount_currency = utils.round_decimals(amount_currency, other_precision);
            }
            line.balance = {
                amount: total,
                amount_str: field_utils.format.monetary(Math.abs(total), {}, formatOptions),
                currency_id: isOtherCurrencyId,
                amount_currency: isOtherCurrencyId ? amount_currency : total,
                amount_currency_str: isOtherCurrencyId ? field_utils.format.monetary(Math.abs(amount_currency), {}, {
                    currency_id: isOtherCurrencyId
                }) : false,
                account_code: self.accounts[line.st_line.open_balance_account_id],
            };
            line.balance.show_balance = line.balance.amount_currency != 0;
            line.balance.type = line.balance.amount_currency ? (line.st_line.partner_id ? 0 : -1) : 1;
        });
    },
    /**
     *
     *
     * @private
     * @param {string} handle
     * @param {integer} reconcileModelId
     */
    _computeReconcileModels: function (handle, reconcileModelId) {
        var line = this.getLine(handle);
        // if quick create with 2 lines who use 100%, change the both values in same time
        var props = _.filter(line.reconciliation_proposition, {'reconcileModelId': reconcileModelId, '__focus': true});
        if (props.length === 2 && props[0].percent && props[1].percent) {
            if (props[0].percent + props[1].percent === 100) {
                props[0].base_amount = props[0].amount = line.st_line.amount - props[1].base_amount;
                props[0].__tax_to_recompute = true;
            }
        }
    },
    /**
     * format a name_get into an object {id, display_name}, idempotent
     *
     * @private
     * @param {Object|Array} [value] data or name_get
     */
    _formatNameGet: function (value) {
        return value ? (value.id ? value : {'id': value[0], 'display_name': value[1]}) : false;
    },
    _formatMany2ManyTags: function (value) {
        var res = [];
        for (var i=0, len=value.length; i<len; i++) {
            res[i] = {'id': value[i][0], 'display_name': value[i][1]};
        }
        return res;
    },
    _formatMany2ManyTagsTax: function(value) {
        var res = [];
        for (var i=0; i<value.length; i++) {
            res.push({id: value[i], display_name: this.taxes[value[i]] ? this.taxes[value[i]].display_name : ''});
        }
        return res;
    },
    /**
     * Format each propositions (amount, label, account_id)
     * extended in ManualModel
     *
     * @private
     * @param {Object} line
     * @param {Object[]} props
     */
    _formatLineProposition: function (line, props) {
        var self = this;
        if (props.length) {
            _.each(props, function (prop) {
                prop.amount = prop.debit || -prop.credit;
                prop.label = prop.name;
                prop.account_id = self._formatNameGet(prop.account_id || line.account_id);
                prop.is_partially_reconciled = prop.amount_str !== prop.total_amount_str;
                prop.to_check = !!prop.to_check;
            });
        }
    },
    /**
     * Format each server lines and propositions and compute all lines
     * overridden in ManualModel
     *
     * @see '_computeLine'
     *
     * @private
     * @param {Object[]} lines
     * @returns {Promise}
     */
    _formatLine: function (lines) {
        var self = this;
        var defs = [];
        _.each(lines, function (data) {
            var line = _.find(self.lines, function (l) {
                return l.id === data.st_line.id;
            });
            line.visible = true;
            line.limitMoveLines = self.limitMoveLines;
            _.extend(line, data);
            self._formatLineProposition(line, line.reconciliation_proposition);
            if (!line.reconciliation_proposition.length) {
                delete line.reconciliation_proposition;
            }

            // No partner set on st_line and all matching amls have the same one: set it on the st_line.
            defs.push(
                self._computeLine(line)
                .then(function(){
                    if(!line.st_line.partner_id && line.reconciliation_proposition.length > 0){
                        var hasDifferentPartners = function(prop){
                            return !prop.partner_id || prop.partner_id != line.reconciliation_proposition[0].partner_id;
                        };

                        if(!_.any(line.reconciliation_proposition, hasDifferentPartners)){
                            return self.changePartner(line.handle, {
                                'id': line.reconciliation_proposition[0].partner_id,
                                'display_name': line.reconciliation_proposition[0].partner_name,
                            }, true);
                        }
                    }else if(!line.st_line.partner_id && line.partner_id && line.partner_name){
                        return self.changePartner(line.handle, {
                            'id': line.partner_id,
                            'display_name': line.partner_name,
                        }, true);
                    }
                    return true;
                })
                .then(function(){
                    return data.write_off ? self.quickCreateProposition(line.handle, data.model_id) : true;
                })
                .then(function() {
                    // If still no partner set, take the one from context, if it exists
                    if (!line.st_line.partner_id && self.context.partner_id && self.context.partner_name) {
                        return self.changePartner(line.handle, {
                            'id': self.context.partner_id,
                            'display_name': self.context.partner_name,
                        }, true);
                    }
                    return true;
                })
            );
        });
        return Promise.all(defs);
    },
    /**
     * Format the server value then compute the line
     * overridden in ManualModel
     *
     * @see '_computeLine'
     *
     * @private
     * @param {string} handle
     * @param {Object[]} mv_lines
     * @returns {Promise}
     */
    _formatMoveLine: function (handle, mode, mv_lines) {
        var self = this;
        var line = this.getLine(handle);
        line['mv_lines_'+mode] = _.uniq(line['mv_lines_'+mode].concat(mv_lines), l => l.id);
        if (mv_lines[0]){
            line['remaining_'+mode] = mv_lines[0].recs_count - mv_lines.length;
        } else if (line['mv_lines_'+mode].lenght == 0) {
            line['remaining_'+mode] = 0;
        }
        this._formatLineProposition(line, mv_lines);

        if ((line.mode == 'match_other' || line.mode == "match_rp") && !line['mv_lines_'+mode].length && !line['filter_'+mode].length) {
            line.mode = self._getDefaultMode(handle);
            if (line.mode !== 'match_rp' && line.mode !== 'match_other' && line.mode !== 'inactive') {
                return this._computeLine(line).then(function () {
                    return self.createProposition(handle);
                });
            }
        } else {
            return this._computeLine(line);
        }
    },
    /**
     * overridden in ManualModel
     */
    _getDefaultMode: function(handle) {
        var line = this.getLine(handle);
        if (line.balance.amount === 0
            && (!line.st_line.mv_lines_match_rp || line.st_line.mv_lines_match_rp.length === 0)
            && (!line.st_line.mv_lines_match_other || line.st_line.mv_lines_match_other.length === 0)) {
            return 'inactive';
        }
        if (line.mv_lines_match_rp && line.mv_lines_match_rp.length) {
            return 'match_rp';
        }
        if (line.mv_lines_match_other && line.mv_lines_match_other.length) {
            return 'match_other';
        }
        return 'create';
    },
    _getAvailableModes: function(handle) {
        var line = this.getLine(handle);
        var modes = []
        if (line.mv_lines_match_rp && line.mv_lines_match_rp.length) {
            modes.push('match_rp')
        }
        if (line.mv_lines_match_other && line.mv_lines_match_other.length) {
            modes.push('match_other')
        }
        modes.push('create')
        return modes
    },
    /**
     * Apply default values for the proposition, format datas and format the
     * base_amount with the decimal number from the currency
     * extended in ManualModel
     *
     * @private
     * @param {Object} line
     * @param {Object} values
     * @returns {Object}
     */
    _formatQuickCreate: function (line, values) {
        values = values || {};
        var today = new moment().utc().format();
        var account = this._formatNameGet(values.account_id);
        var formatOptions = {
            currency_id: line.st_line.currency_id,
        };
        var amount;
        switch(values.amount_type) {
            case 'percentage':
                amount = line.balance.amount * values.amount / 100;
                break;
            case 'regex':
                var matching = line.st_line.name.match(new RegExp(values.amount_from_label_regex))
                amount = 0;
                if (matching && matching.length == 2) {
                    matching = matching[1].replace(new RegExp('\\D' + values.decimal_separator, 'g'), '');
                    matching = matching.replace(values.decimal_separator, '.');
                    amount = parseFloat(matching) || 0;
                    amount = line.balance.amount > 0 ? amount : -amount;
                }
                break;
            case 'fixed':
                amount = values.amount;
                break;
            default:
                amount = values.amount !== undefined ? values.amount : line.balance.amount;
        }


        var prop = {
            'id': _.uniqueId('createLine'),
            'label': values.label || line.st_line.name,
            'account_id': account,
            'account_code': account ? this.accounts[account.id] : '',
            'analytic_account_id': this._formatNameGet(values.analytic_account_id),
            'analytic_tag_ids': this._formatMany2ManyTags(values.analytic_tag_ids || []),
            'journal_id': this._formatNameGet(values.journal_id),
            'tax_ids': this._formatMany2ManyTagsTax(values.tax_ids || []),
            'tag_ids': values.tag_ids,
            'tax_repartition_line_id': values.tax_repartition_line_id,
            'debit': 0,
            'credit': 0,
            'date': values.date ? values.date : field_utils.parse.date(today, {}, {isUTC: true}),
            'force_tax_included': values.force_tax_included || false,
            'base_amount': amount,
            'percent': values.amount_type === "percentage" ? values.amount : null,
            'link': values.link,
            'display': true,
            'invalid': true,
            'to_check': !!values.to_check,
            '__tax_to_recompute': true,
            '__focus': '__focus' in values ? values.__focus : true,
        };
        if (prop.base_amount) {
            // Call to format and parse needed to round the value to the currency precision
            var sign = prop.base_amount < 0 ? -1 : 1;
            var amount = field_utils.format.monetary(Math.abs(prop.base_amount), {}, formatOptions);
            prop.base_amount = sign * field_utils.parse.monetary(amount, {}, formatOptions);
        }

        prop.amount = prop.base_amount;
        return prop;
    },
    /**
     * Return list of account_move_line that has been selected and needs to be removed
     * from other calls.
     *
     * @private
     * @returns {Array} list of excluded ids
     */
    _getExcludedIds: function () {
        var excludedIds = [];
        _.each(this.lines, function(line) {
            if (line.reconciliation_proposition) {
                _.each(line.reconciliation_proposition, function(prop) {
                    if (parseInt(prop['id'])) {
                        excludedIds.push(prop['id']);
                    }
                });
            }
        });
        return excludedIds;
    },
    /**
     * Defined whether the line is to be displayed or not. Here, we only display
     * the line if it comes from the server or if an account is defined when it
     * is created
     * extended in ManualModel
     *
     * @private
     * @param {object} prop
     * @returns {Boolean}
     */
    _isDisplayedProposition: function (prop) {
        return !isNaN(prop.id) || !!prop.account_id;
    },
    /**
     * extended in ManualModel
     * @private
     * @param {object} prop
     * @returns {Boolean}
     */
    _isValid: function (prop) {
        return !isNaN(prop.id) || prop.account_id && prop.amount && prop.label && !!prop.label.length;
    },
    /**
     * Fetch 'account.reconciliation.widget' propositions.
     * overridden in ManualModel
     *
     * @see '_formatMoveLine'
     *
     * @private
     * @param {string} handle
     * @returns {Promise}
     */
    _performMoveLine: function (handle, mode, limit) {
        limit = limit || this.limitMoveLines;
        var line = this.getLine(handle);
        var excluded_ids = _.map(_.union(line.reconciliation_proposition, line.mv_lines_match_rp, line.mv_lines_match_other), function (prop) {
            return _.isNumber(prop.id) ? prop.id : null;
        }).filter(id => id != null);
        var filter = line['filter_'+mode] || "";
        return this._rpc({
                model: 'account.reconciliation.widget',
                method: 'get_move_lines_for_bank_statement_line',
                args: [line.id, line.st_line.partner_id, excluded_ids, filter, 0, limit, mode === 'match_rp' ? 'rp' : 'other'],
                context: this.context,
            })
            .then(this._formatMoveLine.bind(this, handle, mode));
    },
    /**
     * format the proposition to send information server side
     * extended in ManualModel
     *
     * @private
     * @param {object} line
     * @param {object} prop
     * @returns {object}
     */
    _formatToProcessReconciliation: function (line, prop) {
        var amount = -prop.amount;
        if (prop.partial_amount) {
            amount = -prop.partial_amount;
        }

        var result = {
            name : prop.label,
            debit : amount > 0 ? amount : 0,
            credit : amount < 0 ? -amount : 0,
            tax_exigible: prop.tax_exigible,
            analytic_tag_ids: [[6, null, _.pluck(prop.analytic_tag_ids, 'id')]]
        };
        if (!isNaN(prop.id)) {
            result.counterpart_aml_id = prop.id;
        } else {
            result.account_id = prop.account_id.id;
            if (prop.journal_id) {
                result.journal_id = prop.journal_id.id;
            }
        }
        if (!isNaN(prop.id)) result.counterpart_aml_id = prop.id;
        if (prop.analytic_account_id) result.analytic_account_id = prop.analytic_account_id.id;
        if (prop.tax_ids && prop.tax_ids.length) result.tax_ids = [[6, null, _.pluck(prop.tax_ids, 'id')]];

        if (prop.tag_ids && prop.tag_ids.length) result.tag_ids = [[6, null, prop.tag_ids]];
        if (prop.tax_repartition_line_id) result.tax_repartition_line_id = prop.tax_repartition_line_id;
        if (prop.reconcileModelId) result.reconcile_model_id = prop.reconcileModelId
        return result;
    },
    /**
     * Hook to handle return values of the validate's line process.
     *
     * @private
     * @param {Object} data
     * @param {Object[]} data.moves list of processed account.move
     * @returns {Deferred}
     */
    _validatePostProcess: function (data) {
        var self = this;
        return Promise.resolve();
    },
});


/**
 * Model use to fetch, format and update 'account.move.line' and 'res.partner'
 * datas allowing manual reconciliation
 */
var ManualModel = StatementModel.extend({
    quickCreateFields: ['account_id', 'journal_id', 'amount', 'analytic_account_id', 'label', 'tax_ids', 'force_tax_included', 'analytic_tag_ids', 'date', 'to_check'],

    modes: ['create', 'match'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return a boolean telling if load button needs to be displayed or not
     *
     * @returns {boolean} true if load more button needs to be displayed
     */
    hasMoreLines: function () {
        if (this.manualLines.length > this.pagerIndex) {
            return true;
        }
        return false;
    },
    /**
     * load data from
     * - 'account.reconciliation.widget' fetch the lines to reconciliate
     * - 'account.account' fetch all account code
     *
     * @param {Object} context
     * @param {string} [context.mode] 'customers', 'suppliers' or 'accounts'
     * @param {integer[]} [context.company_ids]
     * @param {integer[]} [context.partner_ids] used for 'customers' and
     *   'suppliers' mode
     * @returns {Promise}
     */
    load: function (context) {
        var self = this;
        this.context = context;

        var domain_account_id = [];
        if (context && context.company_ids) {
            domain_account_id.push(['company_id', 'in', context.company_ids]);
        }

        var def_account = this._rpc({
                model: 'account.account',
                method: 'search_read',
                domain: domain_account_id,
                fields: ['code'],
            })
            .then(function (accounts) {
                self.account_ids = _.pluck(accounts, 'id');
                self.accounts = _.object(self.account_ids, _.pluck(accounts, 'code'));
            });

        var domainReconcile = [];
        var session_allowed_company_ids = session.user_context.allowed_company_ids || []
        var company_ids = context && context.company_ids || session_allowed_company_ids.slice(0, 1);

        if (company_ids) {
            domainReconcile.push(['company_id', 'in', company_ids]);
        }
        var def_reconcileModel = this._loadReconciliationModel({domainReconcile: domainReconcile});
        var def_taxes = this._loadTaxes();

        return Promise.all([def_reconcileModel, def_account, def_taxes]).then(function () {
            switch(context.mode) {
                case 'customers':
                case 'suppliers':
                    var mode = context.mode === 'customers' ? 'receivable' : 'payable';
                    var args = ['partner', context.partner_ids || null, mode];
                    return self._rpc({
                            model: 'account.reconciliation.widget',
                            method: 'get_data_for_manual_reconciliation',
                            args: args,
                            context: context,
                        })
                        .then(function (result) {
                            self.manualLines = result;
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.manualLines).length;
                            var lines = self.manualLines.slice(0, self.defaultDisplayQty);
                            self.pagerIndex = lines.length;
                            return self.loadData(lines);
                        });
                case 'accounts':
                    return self._rpc({
                            model: 'account.reconciliation.widget',
                            method: 'get_data_for_manual_reconciliation',
                            args: ['account', context.account_ids || self.account_ids],
                            context: context,
                        })
                        .then(function (result) {
                            self.manualLines = result;
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.manualLines).length;
                            var lines = self.manualLines.slice(0, self.defaultDisplayQty);
                            self.pagerIndex = lines.length;
                            return self.loadData(lines);
                        });
                default:
                    var partner_ids = context.partner_ids || null;
                    var account_ids = context.account_ids || self.account_ids || null;
                    return self._rpc({
                            model: 'account.reconciliation.widget',
                            method: 'get_all_data_for_manual_reconciliation',
                            args: [partner_ids, account_ids],
                            context: context,
                        })
                        .then(function (result) {
                            // Flatten the result
                            self.manualLines = [].concat(result.accounts, result.customers, result.suppliers);
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.manualLines).length;
                            var lines = self.manualLines.slice(0, self.defaultDisplayQty);
                            self.pagerIndex = lines.length;
                            return self.loadData(lines);
                        });
            }
        });
    },

    /**
     * Reload data by calling load
     * It overrides super.reload() because
     * it is not adapted for this model.
     *
     * Use case: coming back to manual reconcilation
     *           in breadcrumb
     */
    reload: function () {
        this.lines = {};
        return this.load(this.context);
    },

    /**
     * Load more partners/accounts
     * overridden in ManualModel
     *
     * @param {integer} qty quantity to load
     * @returns {Promise}
     */
    loadMore: function(qty) {
        if (qty === undefined) {
            qty = this.defaultDisplayQty;
        }
        var lines = this.manualLines.slice(this.pagerIndex, this.pagerIndex + qty);
        this.pagerIndex += qty;
        return this.loadData(lines);
    },
    /**
     * Method to load informations on lines
     *
     * @param {Array} lines manualLines to load
     * @returns {Promise}
     */
    loadData: function(lines) {
        var self = this;
        var defs = [];
        _.each(lines, function (l) {
            defs.push(self._formatLine(l.mode, l));
        });
        return Promise.all(defs);

    },
    /**
     * Mark the account or the partner as reconciled
     *
     * @param {(string|string[])} handle
     * @returns {Promise<Array>} resolved with the handle array
     */
    validate: function (handle) {
        var self = this;
        var handles = [];
        if (handle) {
            handles = [handle];
        } else {
            _.each(this.lines, function (line, handle) {
                if (!line.reconciled && !line.balance.amount && line.reconciliation_proposition.length) {
                    handles.push(handle);
                }
            });
        }

        var def = Promise.resolve();
        var process_reconciliations = [];
        var reconciled = [];
        _.each(handles, function (handle) {
            var line = self.getLine(handle);
            if(line.reconciled) {
                return;
            }
            var props = line.reconciliation_proposition;
            if (!props.length) {
                self.valuenow++;
                reconciled.push(handle);
                line.reconciled = true;
                process_reconciliations.push({
                    id: line.type === 'accounts' ? line.account_id : line.partner_id,
                    type: line.type,
                    mv_line_ids: [],
                    new_mv_line_dicts: [],
                });
            } else {
                var mv_line_ids = _.pluck(_.filter(props, function (prop) {return !isNaN(prop.id);}), 'id');
                var new_mv_line_dicts = _.map(_.filter(props, function (prop) {return isNaN(prop.id) && prop.display;}), self._formatToProcessReconciliation.bind(self, line));
                process_reconciliations.push({
                    id: null,
                    type: null,
                    mv_line_ids: mv_line_ids,
                    new_mv_line_dicts: new_mv_line_dicts
                });
            }
            line.reconciliation_proposition = [];
        });
        if (process_reconciliations.length) {
            def = self._rpc({
                    model: 'account.reconciliation.widget',
                    method: 'process_move_lines',
                    args: [process_reconciliations],
                });
        }

        return def.then(function() {
            var defs = [];
            var account_ids = [];
            var partner_ids = [];
            _.each(handles, function (handle) {
                var line = self.getLine(handle);
                if (line.reconciled) {
                    return;
                }
                line.filter_match = "";
                defs.push(self._performMoveLine(handle, 'match').then(function () {
                    if(!line.mv_lines_match.length) {
                        self.valuenow++;
                        reconciled.push(handle);
                        line.reconciled = true;
                        if (line.type === 'accounts') {
                            account_ids.push(line.account_id.id);
                        } else {
                            partner_ids.push(line.partner_id);
                        }
                    }
                }));
            });
            return Promise.all(defs).then(function () {
                if (partner_ids.length) {
                    self._rpc({
                            model: 'res.partner',
                            method: 'mark_as_reconciled',
                            args: [partner_ids],
                        });
                }
                return {reconciled: reconciled, updated: _.difference(handles, reconciled)};
            });
        });
    },
    removeProposition: function (handle, id) {
        var self = this;
        var line = this.getLine(handle);
        var defs = [];
        var prop = _.find(line.reconciliation_proposition, {'id' : id});
        if (prop) {
            line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (p) {
                return p.id !== prop.id && p.id !== prop.link && p.link !== prop.id && (!p.link || p.link !== prop.link);
            });
            line.mv_lines_match = line.mv_lines_match || [];
            line.mv_lines_match.unshift(prop);

            // No proposition left and then, reset the st_line partner.
            if(line.reconciliation_proposition.length == 0 && line.st_line.has_no_partner)
                defs.push(self.changePartner(line.handle));
        }
        line.mode = (id || line.mode !== "create") && isNaN(id) ? 'create' : 'match';
        defs.push(this._computeLine(line));
        return Promise.all(defs).then(function() {
            return self.changeMode(handle, line.mode, true);
        })
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * override change the balance type to display or not the reconcile button
     *
     * @override
     * @private
     * @param {Object} line
     * @returns {Promise}
     */
    _computeLine: function (line) {
        return this._super(line).then(function () {
            var props = _.reject(line.reconciliation_proposition, 'invalid');
            _.each(line.reconciliation_proposition, function(p) {
                delete p.is_move_line;
            });
            line.balance.type = -1;
            if (!line.balance.amount_currency && props.length) {
                line.balance.type = 1;
            } else if(_.any(props, function (prop) {return prop.amount > 0;}) &&
                     _.any(props, function (prop) {return prop.amount < 0;})) {
                line.balance.type = 0;
            }
        });
    },
    /**
     * Format each server lines and propositions and compute all lines
     *
     * @see '_computeLine'
     *
     * @private
     * @param {'customers' | 'suppliers' | 'accounts'} type
     * @param {Object} data
     * @returns {Promise}
     */
    _formatLine: function (type, data) {
        var line = this.lines[_.uniqueId('rline')] = _.extend(data, {
            type: type,
            reconciled: false,
            mode: 'inactive',
            limitMoveLines: this.limitMoveLines,
            filter_match: "",
            reconcileModels: this.reconcileModels,
            account_id: this._formatNameGet([data.account_id, data.account_name]),
            st_line: data,
            visible: true
        });
        this._formatLineProposition(line, line.reconciliation_proposition);
        if (!line.reconciliation_proposition.length) {
            delete line.reconciliation_proposition;
        }
        return this._computeLine(line);
    },
    /**
     * override to add journal_id
     *
     * @override
     * @private
     * @param {Object} line
     * @param {Object} props
     */
    _formatLineProposition: function (line, props) {
        var self = this;
        this._super(line, props);
        if (props.length) {
            _.each(props, function (prop) {
                var tmp_value = prop.debit || prop.credit;
                prop.credit = prop.credit !== 0 ? 0 : tmp_value;
                prop.debit = prop.debit !== 0 ? 0 : tmp_value;
                prop.amount = -prop.amount;
                prop.journal_id = self._formatNameGet(prop.journal_id || line.journal_id);
                prop.to_check = !!prop.to_check;
            });
        }
    },
    /**
     * override to add journal_id on tax_created_line
     *
     * @private
     * @param {Object} line
     * @param {Object} values
     * @returns {Object}
     */
    _formatQuickCreate: function (line, values) {
        // Add journal to created line
        if (values && values.journal_id === undefined && line && line.createForm && line.createForm.journal_id) {
            values.journal_id = line.createForm.journal_id;
        }
        return this._super(line, values);
    },
    /**
     * @override
     * @param {object} prop
     * @returns {Boolean}
     */
    _isDisplayedProposition: function (prop) {
        return !!prop.journal_id && this._super(prop);
    },
    /**
     * @override
     * @param {object} prop
     * @returns {Boolean}
     */
    _isValid: function (prop) {
        return prop.journal_id && this._super(prop);
    },
    /**
     * Fetch 'account.move.line' propositions.
     *
     * @see '_formatMoveLine'
     *
     * @override
     * @private
     * @param {string} handle
     * @returns {Promise}
     */
    _performMoveLine: function (handle, mode, limit) {
        limit = limit || this.limitMoveLines;
        var line = this.getLine(handle);
        var excluded_ids = _.map(_.union(line.reconciliation_proposition, line.mv_lines_match), function (prop) {
            return _.isNumber(prop.id) ? prop.id : null;
        }).filter(id => id != null);
        var filter = line.filter_match || "";
        var args = [line.account_id.id, line.partner_id, excluded_ids, filter, 0, limit];
        return this._rpc({
                model: 'account.reconciliation.widget',
                method: 'get_move_lines_for_manual_reconciliation',
                args: args,
                context: this.context,
            })
            .then(this._formatMoveLine.bind(this, handle, ''));
    },

    _formatToProcessReconciliation: function (line, prop) {
        var result = this._super(line, prop);
        result['date'] = prop.date;
        return result;
    },
    _getDefaultMode: function(handle) {
        var line = this.getLine(handle);
        if (line.balance.amount === 0 && (!line.st_line.mv_lines_match || line.st_line.mv_lines_match.length === 0)) {
            return 'inactive';
        }
        return line.mv_lines_match.length > 0 ? 'match' : 'create';
    },
    _formatMoveLine: function (handle, mode, mv_lines) {
        var self = this;
        var line = this.getLine(handle);
        line.mv_lines_match = _.uniq((line.mv_lines_match || []).concat(mv_lines), l => l.id);
        this._formatLineProposition(line, mv_lines);

        if (line.mode !== 'create' && !line.mv_lines_match.length && !line.filter_match.length) {
            line.mode = this.avoidCreate || !line.balance.amount ? 'inactive' : 'create';
            if (line.mode === 'create') {
                return this._computeLine(line).then(function () {
                    return self.createProposition(handle);
                });
            }
        } else {
            return this._computeLine(line);
        }
    },
});

return {
    StatementModel: StatementModel,
    ManualModel: ManualModel,
};
});
