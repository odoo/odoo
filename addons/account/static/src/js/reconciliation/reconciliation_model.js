odoo.define('account.ReconciliationModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var field_utils = require('web.field_utils');
var CrashManager = require('web.CrashManager');
var core = require('web.core');
var _t = core._t;


/**
 * Model use to fetch, format and update 'account.bank.statement' and
 * 'account.bank.statement.line' datas allowing reconciliation
 *
 * The statement internal structure:
 *
 *  {
 *      valuenow: integer
 *      valuenow: valuemax
 *      [bank_statement_id]: {
 *          id: integer
 *          display_name: string
 *      }
 *      reconcileModels: [object]
 *      accounts: {id: code}
 *  }
 *
 * The internal structure of each line is:
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
 *      mode: string ('inactive', 'match', 'create')
 *      reconciliation_proposition: {
 *          id: number|string
 *          partial_reconcile: boolean
 *          invalid: boolean - through the invalid line (without account, label...)
 *          is_tax: boolean
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
 *          [amount_currency_str]: string|false (amount in record currency)
 *      }
 *      mv_lines: object - idem than reconciliation_proposition
 *      offset: integer
 *      filter: string
 *      [createForm]: {
 *          account_id: {
 *              id: integer
 *              display_name: string
 *          }
 *          tax_id: {
 *              id: integer
 *              display_name: string
 *          }
 *          analytic_account_id: {
 *              id: integer
 *              display_name: string
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
    quickCreateFields: ['account_id', 'amount', 'analytic_account_id', 'label', 'tax_id'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.reconcileModels = [];
        this.lines = {};
        this.valuenow = 0;
        this.valuemax = 0;
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
     * @param {number} mv_lines id
     * @returns {Deferred}
     */
    addProposition: function (handle, mv_line_id) {
        var line = this.getLine(handle);
        var prop = _.clone(_.find(line.mv_lines, {'id': mv_line_id}));

        function checkAccountType (r) {
            return !isNaN(r.id) && r.account_type !== prop.account_type;
        }
        if (_.any(line.reconciliation_proposition, checkAccountType)) {
            new CrashManager().show_warning({data: {
                exception_type: _t("Incorrect Operation"),
                message: _t("You cannot mix items from receivable and payable accounts.")
            }});
            return $.when();
        }

        line.reconciliation_proposition.push(prop);
        _.each(line.reconciliation_proposition, function (line) {
            line.partial_reconcile = false;
        });
        return $.when(this._computeLine(line), this._performMoveLine(handle));
    },
    /**
     * send information 'account.bank.statement.line' model to reconciliate
     * lines, call rpc to 'reconciliation_widget_auto_reconcile'
     * Update the number of validated line
     *
     * @returns {Deferred<Object>} resolved with an object who contains
     *   'handles' key and 'notifications'
     */
    autoReconciliation: function () {
        var self = this;
        var ids = _.pluck(_.filter(_.values(this.lines), {'reconciled': false}), 'id');
        return this._rpc({
                model: 'account.bank.statement.line',
                method: 'reconciliation_widget_auto_reconcile',
                args: [ids, self.valuenow],
            })
            .then(function (result) {
                var reconciled_ids = _.difference(ids, result.st_lines_ids);
                self.valuenow += reconciled_ids.length;
                result.handles = [];
                _.each(self.lines, function (line, handle) {
                    if (reconciled_ids.indexOf(line.id) !== -1) {
                        line.reconciled = true;
                        result.handles.push(handle);
                    }
                });
                return result;
            });
    },
    /**
     * change the filter for the target line and fetch the new matched lines
     *
     * @param {string} handle
     * @param {string} filter
     * @returns {Deferred}
     */
    changeFilter: function (handle, filter) {
        this.getLine(handle).filter = filter;
        return this._performMoveLine(handle);
    },
    /**
     * change the mode line ('inactive', 'match', 'create'), and fetch the new
     * matched lines or prepare to create a new line
     *
     * 'match': display the matched lines, the user can select the lines to
     *   apply there as proposition
     * 'create': display fields and quick create button to create a new
     *   proposition for the reconciliation
     *
     * @param {string} handle
     * @param {string} mode
     * @returns {Deferred}
     */
    changeMode: function (handle, mode) {
        var line = this.getLine(handle);
        if (line.mode  === 'create') {
            this._blurProposition(handle);
            line.createForm = null;
        }
        if (mode  === 'create' && this.avoidCreate) {
            mode = 'match';
        }
        line.mode = mode;
        if (mode === 'match') {
            return this._performMoveLine(handle);
        }
        if (line.mode === 'create') {
            return this.createProposition(handle);
        }
        return $.when();
    },
    /**
     * call 'write' method on the 'account.bank.statement'
     *
     * @param {string} name
     * @returns {Deferred}
     */
    changeName: function (name) {
        return this._rpc({
                model: 'account.bank.statement',
                method: 'write',
                args: [this.bank_statement_id.id, {name: name}],
            });
    },
    /**
     * change the offset for the matched lines, and fetch the new matched lines
     *
     * @param {string} handle
     * @param {number} offset
     * @returns {Deferred}
     */
    changeOffset: function (handle, offset) {
        this.getLine(handle).offset += offset;
        return this._performMoveLine(handle);
    },
    /**
     * change the partner on the line and fetch the new matched lines
     *
     * @param {string} handle
     * @param {Object} partner
     * @param {string} partner.display_name
     * @param {number} partner.id
     * @returns {Deferred}
     */
    changePartner: function (handle, partner) {
        var self = this;
        var line = this.getLine(handle);
        line.st_line.partner_id = partner && partner.id;
        line.st_line.partner_name = partner && partner.display_name || '';
        return this._performMoveLine(handle).then(function () {
            if (line.mode === 'create') {
                return self.createProposition(handle);
            }
        });
    },
    /**
     *
     * then open the first available line
     *
     * @param {string} handle
     * @returns {Deferred}
     */
    createProposition: function (handle) {
        var line = this.getLine(handle);
        var prop = _.filter(line.reconciliation_proposition, '__focus');
        var last = prop[prop.length-1];
        if (last && (!last.account_id || !last.label.length || !last.amount)) {
            return $.Deferred().reject();
        }

        prop = this._formatQuickCreate(line);
        line.reconciliation_proposition.push(prop);
        line.createForm = _.pick(prop, this.quickCreateFields);
        return this._computeLine(line);
    },
    /**
     * get the line data for this handle
     *
     * @param {OdooEvent} event
     * @returns {Object}
     */
    getLine: function (handle) {
        return this.lines[handle];
    },
    /**
     * load data from
     * - 'account.bank.statement' fetch the line id and bank_statement_id info
     * - 'account.reconcile.model'  fetch all reconcile model (for quick add)
     * - 'account.account' fetch all account code
     * - 'account.bank.statement.line' fetch each line data
     *
     * @param {Object} context
     * @param {number[]} context.statement_ids
     * @returns {Deferred}
     */
    load: function (context) {
        var self = this;
        var statement_ids = context.statement_ids;
        if (!statement_ids) {
            return $.when();
        }
        var def_statement = this._rpc({
                model: 'account.bank.statement',
                method: 'reconciliation_widget_preprocess',
                args: [statement_ids],
            })
            .then(function (statement) {
                self.bank_statement_id = statement_ids.length === 1 ? {id: statement_ids[0], display_name: statement.statement_name} : false;
                self.valuenow = 0;
                self.valuemax = statement.st_lines_ids.length;
                _.each(statement.st_lines_ids, function (id) {
                    self.lines[_.uniqueId('rline')] = {
                        'id': id,
                        'reconciled': false,
                        'mode': 'inactive',
                        'mv_lines': [],
                        'offset': 0,
                        'filter': "",
                        'reconciliation_proposition': [],
                        'reconcileModels': []
                    };
                });
            });
        var def_reconcileModel = this._rpc({
                model: 'account.reconcile.model',
                method: 'search_read',
            })
            .then(function (reconcileModels) {
                self.reconcileModels = reconcileModels;
            });
        var def_account = this._rpc({
                model: 'account.account',
                method: 'search_read',
                fields: ['code'],
            })
            .then(function (accounts) {
                self.accounts = _.object(_.pluck(accounts, 'id'), _.pluck(accounts, 'code'));
            });
        return $.when(def_statement, def_reconcileModel, def_account).then(function () {
            _.each(self.lines, function (line) {
                line.reconcileModels = self.reconcileModels;
            });
            var ids = _.pluck(self.lines, 'id');
            return self._rpc({
                    model: 'account.bank.statement.line',
                    method: 'get_data_for_reconciliation_widget',
                    args: [ids],
                })
                .then(self._formatLine.bind(self));
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
     * @param {integer} reconcile model id
     * @returns {Deferred}
     */
    quickCreateProposition: function (handle, reconcileModelId) {
        var line = this.getLine(handle);
        var reconcileModel = _.find(this.reconcileModels, function (r) {return r.id === reconcileModelId;});
        var fields = ['account_id', 'amount', 'amount_type', 'analytic_account_id', 'journal_id', 'label', 'tax_id'];
        this._blurProposition(handle);

        var focus = this._formatQuickCreate(line, _.pick(reconcileModel, fields));
        focus.reconcileModelId = reconcileModelId;
        line.reconciliation_proposition.push(focus);

        if (reconcileModel.has_second_line) {
            var second = {};
            _.each(fields, function (key) {
                second[key] = ("second_"+key) in reconcileModel ? reconcileModel["second_"+key] : reconcileModel[key];
            });
            focus = this._formatQuickCreate(line, second);
            focus.reconcileModelId = reconcileModelId;
            line.reconciliation_proposition.push(focus);
            this._computeReconcileModels(handle, reconcileModelId);
        }
        line.createForm = _.pick(focus, this.quickCreateFields);
        return this._computeLine(line);
    },
    /**
     * Remove a proposition and switch to an active mode ('create' or 'match')
     *
     * @param {string} handle
     * @param {number} proposition id (move line id)
     * @returns {Deferred}
     */
    removeProposition: function (handle, id) {
        var self = this;
        var line = this.getLine(handle);
        var prop = _.find(line.reconciliation_proposition, {'id' : id});
        line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (p) {
            return p.id !== prop.id && p.id !== prop.link && p.link !== prop.id && (!p.link || p.link !== prop.link);
        });
        line.mode = isNaN(id) && !this.avoidCreate ? 'create' : 'match';
        var def = this._computeLine(line);
        if (line.mode === 'create') {
            return def.then(function () {
                return self.createProposition(handle);
            });
        } else if (line.mode === 'match') {
            return $.when(def, self._performMoveLine(handle));
        }
        return def;
    },
    /**
     * Force the partial reconciliation to display the reconciliate button.
     * This method should only  be called when there is onely one proposition.
     *
     * @param {string} handle
     * @returns {Deferred}
     */
    togglePartialReconcile: function (handle) {
        var line = this.getLine(handle);
        var prop = _.find(line.reconciliation_proposition, {'invalid': false});
        prop.partial_reconcile = !prop.partial_reconcile;
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
     * @param {number[]} context.statement_ids
     * @returns {Deferred}
     */
    updateProposition: function (handle, values) {
        var line = this.getLine(handle);
        var prop = _.last(_.filter(line.reconciliation_proposition, '__focus'));
        if (!prop) {
            prop = this._formatQuickCreate(line);
            line.reconciliation_proposition.push(prop);
        }
        _.each(values, function (value, fieldName) {
            prop[fieldName] = values[fieldName];
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
        if ('account_id' in values || 'amount' in values || 'tax_id' in values) {
            prop.__tax_to_recompute = true;
        }
        line.createForm = _.pick(prop, this.quickCreateFields);
        return this._computeLine(line);
    },
    /**
     * Format the value and send it to 'account.bank.statement.line' model
     * Update the number of validated lines
     *
     * @param {(string|string[])} handle
     * @returns {Deferred<Object>} resolved with an object who contains
     *   'handles' key
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
        var ids = [];
        var values = [];
        _.each(handles, function (handle) {
            var line = self.getLine(handle);
            var props = _.filter(line.reconciliation_proposition, function (prop) {return !prop.is_tax && !prop.invalid;});
            ids.push(line.id);
            values.push({
                "partner_id": line.st_line.partner_id,
                "counterpart_aml_dicts": _.map(_.filter(props, function (prop) {return !isNaN(prop.id) && !prop.already_paid;}), self._formatToProcessReconciliation),
                "payment_aml_ids": _.map(_.filter(props, function (prop) {return !isNaN(prop.id) && prop.already_paid;}), self._formatToProcessReconciliation),
                "new_aml_dicts": _.map(_.filter(props, function (prop) {return isNaN(prop.id);}), self._formatToProcessReconciliation),
            });
            line.reconciled = true;
            self.valuenow++;
        });

        return this._rpc({
                model: 'account.bank.statement.line',
                method: 'process_reconciliations',
                args: [ids, values],
            })
            .then(function () {
                return {handles: handles};
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * stop the editable proposition line and remove it if it's invalid then
     * compute the line
     *
     * @see '_computeLine'
     *
     * @private
     * @param {string} handle
     * @returns {Deferred}
     */
    _blurProposition: function (handle) {
        var line = this.getLine(handle);
        line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (l) {
            l.__focus = false;
            return !l.invalid;
        });
        return this._computeLine(line);
    },
    /**
     * Calculates the balance; format each proposition amount_str and mark as
     * invalid the line with empty account_id, amount or label
     * Check the taxes server side for each updated propositions with tax_id
     *
     * @private
     * @param {Object}
     * @returns {Deferred}
     */
    _computeLine: function (line) {
        //balance_type
        var self = this;

        // compute taxes
        var tax_defs = [];
        var reconciliation_proposition = [];
        var format_options = {
            currency_id: line.st_line.currency_id,
        };
        _.each(line.reconciliation_proposition, function (prop) {
            if (prop.is_tax) {
                if (!_.find(line.reconciliation_proposition, {'id': prop.link}).__tax_to_recompute) {
                    reconciliation_proposition.push(prop);
                }
                return;
            }
            reconciliation_proposition.push(prop);

            if (prop.tax_id && prop.__tax_to_recompute && prop.base_amount) {
                line.reconciliation_proposition = _.filter(line.reconciliation_proposition, function (p) {
                    return !p.is_tax || p.link !== prop.id;
                });

                var args = [[prop.tax_id.id], prop.base_amount, line.st_line.currency_id];
                tax_defs.push(self._rpc({
                        model: 'account.tax',
                        method: 'json_friendly_compute_all',
                        args: args,
                    })
                    .then(function (result) {
                        var tax = result.taxes[0];
                        var tax_prop = self._formatQuickCreate(line, {
                            'link': prop.id,
                            'tax_id': tax.id,
                            'amount': tax.amount,
                            'label': tax.name,
                            'account_id': tax.account_id ? [tax.account_id, null] : prop.account_id,
                            'analytic': tax.analytic,
                            'is_tax': true,
                            '__focus': false
                        });

                        prop.amount = tax.base;
                        prop.amount_str = field_utils.format.monetary(Math.abs(prop.amount), {}, format_options);
                        prop.invalid = !self._isValid(prop);

                        tax_prop.amount_str = field_utils.format.monetary(Math.abs(tax_prop.amount), {}, format_options);
                        tax_prop.invalid = prop.invalid;

                        reconciliation_proposition.push(tax_prop);
                    }));
            } else {
                var currencyData = {
                    currency_id: line.st_line.currency_id
                };

                prop.amount_str = field_utils.format.monetary(Math.abs(prop.amount), {}, currencyData);
                prop.display = self._isDisplay(prop);
                prop.invalid = !self._isValid(prop);
            }
        });

        return $.when.apply($, tax_defs).then(function () {
            _.each(reconciliation_proposition, function (prop) {
                prop.__tax_to_recompute = false;
            });
            line.reconciliation_proposition = reconciliation_proposition;

            var total = line.st_line.amount || 0;
            _.each(line.reconciliation_proposition, function (prop) {
                if (!prop.invalid) {
                    total -= prop.amount;
                }
            });
            total = Math.round(total*1000)/1000 || 0;
            line.balance = {
                'amount': total,
                'amount_str': field_utils.format.monetary(Math.abs(total), {}, format_options),
                'account_code': self.accounts[line.st_line.open_balance_account_id],
            };
            line.balance.type = line.balance.amount ? (line.balance.amount > 0 && line.st_line.partner_id ? 0 : -1) : 1;

            if (line.balance.type === -1) {
                var props = _.filter(line.reconciliation_proposition, {'invalid': false});
                if (props.length === 1 && props[0].partial_reconcile) {
                    line.balance.type = 0;
                }
            }
        });
    },
    /**
     * 
     *
     * @private
     * @param {string} handle
     * @param {integer} reconcile model id
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
     * @param {Object|Array} data or name_get
     * @param {Object|false} {id, display_name}
     */
    _formatNameGet: function (value) {
        return value ? (value.id ? value : {'id': value[0], 'display_name': value[1]}) : false;
    },
    /**
     * Format each propositions (amount, label, account_id)
     *
     * @private
     * @param {Object}
     */
    _formatLineProposition: function (line, props) {
        var self = this;
        if (props.length) {
            _.each(props, function (prop) {
                prop.amount = prop.debit || -prop.credit;
                prop.label = prop.name;
                prop.account_id = self._formatNameGet(prop.account_id || line.account_id);
            });
        }
    },
    /**
     * Format each server lines and propositions and compute all lines
     *
     * @see '_computeLine'
     *
     * @private
     * @param {Object[]}
     * @returns {Deferred}
     */
    _formatLine: function (lines) {
        var self = this;
        var defs = [];
        _.each(lines, function (data) {
            var line = _.find(self.lines, function (l) {
                return l.id === data.st_line.id;
            });
            _.extend(line, data);
            self._formatLineProposition(line, line.reconciliation_proposition);
            if (!line.reconciliation_proposition.length) {
                delete line.reconciliation_proposition;
            }
            defs.push(self._computeLine(line));
        });
        return $.when.apply($, defs);
    },
    /**
     * Format the server value then compute the line
     *
     * @see '_computeLine'
     *
     * @private
     * @param {string} handle
     * @param {Object[]}
     * @returns {Deferred}
     */
    _formatMoveLine: function (handle, mv_lines) {
        var self = this;
        var line = this.getLine(handle);
        _.extend(line, {'mv_lines': mv_lines});
        this._formatLineProposition(line, mv_lines);
        if (line.mode !== 'create' && !mv_lines.length && !line.filter.length) {
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
    /**
     * Apply default values for the proposition, format datas and format the
     * base_amount with the decimal number from the currency
     *
     * @private
     * @param {Object}
     * @param {Object}
     * @returns {Object}
     */
    _formatQuickCreate: function (line, values) {
        values = values || {};
        var account = this._formatNameGet(values.account_id);
        var prop = {
            'id': _.uniqueId('createLine'),
            'label': values.label || line.st_line.name,
            'account_id': account,
            'account_code': account ? this.accounts[account.id] : '',
            'analytic_account_id': this._formatNameGet(values.analytic_account_id),
            'journal_id': this._formatNameGet(values.journal_id),
            'tax_id': this._formatNameGet(values.tax_id),
            'debit': 0,
            'credit': 0,
            'base_amount': values.amount_type !== "percentage" ?
                (values.amount || line.balance.amount) :
                line.st_line.amount * values.amount / 100,
            'percent': values.amount_type === "percentage" ? values.amount : null,
            'link': values.link,
            'display': true,
            'invalid': true,
            '__tax_to_recompute': true,
            'is_tax': values.is_tax,
            '__focus': '__focus' in values ? values.__focus : true,
        };
        if (prop.base_amount) {
            var sign = prop.base_amount < 0 ? -1 : 1;
            var amount = field_utils.format.monetary(Math.abs(prop.base_amount), {}, line);
            prop.base_amount = sign * field_utils.parse.monetary(amount);
        }
        prop.amount = prop.base_amount;
        return prop;
    },
    /**
     * @private
     * @param {object} prop
     * @returns {Boolean}
     */
    _isDisplay: function (prop) {
        return !!prop.account_id;
    },
    /**
     * @private
     * @param {object} prop
     * @returns {Boolean}
     */
    _isValid: function (prop) {
        return prop.account_id && prop.amount && prop.label && !!prop.label.length;
    },
    /**
     * Fetch 'account.bank.statement.line' propositions.
     *
     * @see '_formatMoveLine'
     *
     * @private
     * @param {string} handle
     * @returns {Deferred}
     */
    _performMoveLine: function (handle) {
        var line = this.getLine(handle);
        var excluded_ids = _.flatten(_.map(this.lines, function (line) {
            return _.filter(_.pluck(line.reconciliation_proposition, 'id'), _.isNumber);
        }));
        var filter = line.filter || "";
        var offset = line.offset;
        var limit = 6;
        return this._rpc({
                model: 'account.bank.statement.line',
                method: 'get_move_lines_for_reconciliation_widget',
                args: [line.id, line.st_line.partner_id, excluded_ids, filter, offset, limit],
            })
            .then(this._formatMoveLine.bind(this, handle));
    },
    /**
     * format the proposition to send information server side
     *
     * @private
     * @param {object} proposition
     * @returns {object}
     */
    _formatToProcessReconciliation: function (prop) {
        var result = {
            'name' : prop.label,
            'debit' : prop.amount > 0 ? prop.amount : 0,
            'credit' : prop.amount < 0 ? -prop.amount : 0,
            'account_id' : prop.account_id.id,
            'journal_id' : prop.journal_id && prop.journal_id.id,
        };
        if (!isNaN(prop.id)) result.counterpart_aml_id = prop.id;
        if (prop.analytic_account_id) result.analytic_account_id = prop.analytic_account_id.id;
        if (prop.tax_id) result.tax_ids = [[4, prop.tax_id.id, null]];
        return result;
    },
});


/**
 * Model use to fetch, format and update 'account.move.line' and 'res.partner'
 * datas allowing manual reconciliation
 */
var ManualModel = StatementModel.extend({
    quickCreateFields: ['account_id', 'journal_id', 'amount', 'analytic_account_id', 'label', 'tax_id'],

    /**
     * load data from
     * - 'account.move.line' fetch the lines to reconciliate
     * - 'account.account' fetch all account code
     *
     * @param {Object} context
     * @param {string} [context.mode] 'customers', 'suppliers' or 'accounts'
     * @param {integer[]} [context.company_ids]
     * @param {integer[]} [context.partner_ids] used for 'customers' and
     *   'suppliers' mode
     * @returns {Deferred}
     */
    load: function (context) {
        var self = this;

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

        return def_account.then(function () {
            switch(context.mode) {
                case 'customers':
                case 'suppliers':
                    var mode = context.mode === 'customers' ? 'receivable' : 'payable';
                    var args = ['partner', context.partner_ids || null, mode];
                    return self._rpc({
                            model: 'account.move.line',
                            method: 'get_data_for_manual_reconciliation',
                            args: args,
                        })
                        .then(function (result) {
                            var defs = _.map(result, self._formatLine.bind(self, context.mode));
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.lines).length;
                            return $.when.apply($, defs);
                        });
                case 'accounts':
                    return self._rpc({
                            model: 'account.move.line',
                            method: 'get_data_for_manual_reconciliation',
                            args: ['account', self.account_ids],
                        })
                        .then(function (result) {
                            var defs = _.map(result, self._formatLine.bind(self, 'accounts'));
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.lines).length;
                            return $.when.apply($, defs);
                        });
                default:
                    var partner_ids = context.partner_ids;
                    var account_ids = self.account_ids;
                    if (partner_ids && !account_ids) account_ids = [];
                    if (!partner_ids && account_ids) partner_ids = [];
                    account_ids = null; // TOFIX: REMOVE ME
                    partner_ids = null; // TOFIX: REMOVE ME
                    return self._rpc({
                            model: 'account.move.line',
                            method: 'get_data_for_manual_reconciliation_widget',
                            args: [partner_ids, account_ids],
                        })
                        .then(function (result) {
                            var defs = _.map(result.accounts, self._formatLine.bind(self, 'accounts'));
                            defs = defs.concat(_.map(result.customers, self._formatLine.bind(self, 'customers')));
                            defs = defs.concat(_.map(result.suppliers, self._formatLine.bind(self, 'suppliers')));
                            self.valuenow = 0;
                            self.valuemax = Object.keys(self.lines).length;
                            return $.when.apply($, defs);
                        });
            }
        });
    },
    /**
     * Mark the account or the partner as reconciled
     *
     * @param {(string|string[])} handle
     * @returns {Deferred<Array>} resolved with the handle array
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

        var def = $.when();
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
                var new_mv_line_dicts = _.map(_.filter(props, function (prop) {return isNaN(prop.id);}), self._formatToProcessReconciliation);
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
                    model: 'account.move.line',
                    method: 'process_reconciliations',
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
                defs.push(self._performMoveLine(handle).then(function () {
                    if(!line.mv_lines.length) {
                        self.valuenow++;
                        reconciled.push(handle);
                        line.reconciled = true;
                        if (line.type === 'accounts') {
                            account_ids.push(line.account_id.id);
                        } else {
                            partner_ids.push(line.partner_id.id);
                        }
                    }
                }));
            });
            return $.when(defs).then(function() {
                if (account_ids.length) {
                    self._rpc({
                            model: 'account.account',
                            method: 'mark_as_reconciled',
                            args: [account_ids],
                        });
                }
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * override change the balance type to display or not the reconcile button
     * 
     * @override
     * @private
     * @param {Object}
     * @returns {Deferred}
     */
    _computeLine: function (line) {
        return this._super(line).then(function () {
            var props = line.reconciliation_proposition;
            line.balance.type = -1;
            if (!line.balance.amount && props.length) {
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
     * @param {string} 'customers', 'suppliers' or 'accounts'
     * @param {Object}
     * @returns {Deferred}
     */
    _formatLine: function (type, data) {
        var line = this.lines[_.uniqueId('rline')] = _.extend(data, {
            'type': type,
            'reconciled': false,
            'mode': 'inactive',
            'offset': 0,
            'filter': "",
            'reconcileModels': [],
            'account_id': this._formatNameGet([data.account_id, data.account_name]),
            'st_line': data
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
     * @param {Object}
     * @param {Object}
     */
    _formatLineProposition: function (line, props) {
        var self = this;
        this._super(line, props);
        if (props.length) {
            _.each(props, function (prop) {
                prop.journal_id = self._formatNameGet(prop.journal_id || line.journal_id);
            });
        }
    },
    /**
     * @override
     * @param {object} prop
     * @returns {Boolean}
     */
    _isDisplay: function (prop) {
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
     * @returns {Deferred}
     */
    _performMoveLine: function (handle) {
        var line = this.getLine(handle);
        var excluded_ids = _.flatten(_.map(this.lines, function (line) {
            return _.filter(_.pluck(line.reconciliation_proposition, 'id'), _.isNumber);
        }));
        var filter = line.filter || "";
        var offset = line.offset;
        var limit = 6;
        var args = [line.account_id.id, line.partner_id, excluded_ids, filter, offset, limit];
        return this._rpc({
                model: 'account.move.line',
                method: 'get_move_lines_for_manual_reconciliation',
                args: args,
            })
            .then(this._formatMoveLine.bind(this, handle));
    },
});

return {
    StatementModel: StatementModel,
    ManualModel: ManualModel,
};
});