odoo.define('account.ReconciliationRenderer', function (require) {
"use strict";

var Widget = require('web.Widget');
var FieldManagerMixin = require('web.FieldManagerMixin');
var relational_fields = require('web.relational_fields');
var basic_fields = require('web.basic_fields');
var core = require('web.core');
var time = require('web.time');
var session = require('web.session');
var qweb = core.qweb;
var _t = core._t;


/**
 * rendering of the bank statement action contains progress bar, title and
 * auto reconciliation button
 */
var StatementRenderer = Widget.extend(FieldManagerMixin, {
    template: 'reconciliation.statement',
    events: {
        'click div:first h1.statement_name': '_onClickStatementName',
        "click *[rel='do_action']": "_onDoAction",
        'click button.js_load_more': '_onLoadMore',
        'blur .statement_name_edition > input': '_onValidateName',
        'keyup .statement_name_edition > input': '_onKeyupInput'
    },
    /**
     * @override
     */
    init: function (parent, model, state) {
        this._super(parent);
        this.model = model;
        this._initialState = state;
    },
    /**
     * display iniial state and create the name statement field
     *
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        this.time = Date.now();
        this.$progress = this.$('.progress');
        this.clickStatementName = this._initialState.bank_statement_id ? true : false;

        if (this._initialState.bank_statement_id) {
            var def = this.model.makeRecord("account.bank.statement", [{
                type: 'char',
                name: 'name',
                attrs: {string: ""},
                value: this._initialState.bank_statement_id.display_name
            }]).then(function (recordID) {
                self.handleNameRecord = recordID;
                self.name = new basic_fields.FieldChar(self,
                    'name', self.model.get(self.handleNameRecord),
                    {mode: 'edit'});

                self.name.appendTo(self.$('.statement_name_edition')).then(function () {
                    self.name.$el.addClass('o_required_modifier');
                });
                self.$('.statement_name').text(self._initialState.bank_statement_id.display_name);
            });
            defs.push(def);
        }

        this.$('h1.statement_name').text(this._initialState.title || _t('No Title'));

        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super();
        $('body').off('keyup', this.enterHandler);
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /*
     * hide the button to load more statement line
     */
    hideLoadMoreButton: function () {
        this.$('.js_load_more').hide();
    },
    showRainbowMan: function (state) {
        var dt = Date.now()-this.time;
        var $done = $(qweb.render("reconciliation.done", {
            'duration': moment(dt).utc().format(time.getLangTimeFormat()),
            'number': state.valuenow,
            'timePerTransaction': Math.round(dt/1000/state.valuemax),
            'context': state.context,
        }));
        $done.find('.button_close_statement').click(this._onCloseBankStatement.bind(this));
        $done.find('.button_back_to_statement').click(this._onGoToBankStatement.bind(this));
        this.$el.children().hide();
        // display rainbowman after full reconciliation
        if (session.show_effect) {
            this.trigger_up('show_effect', {
                type: 'rainbow_man',
                fadeout: 'no',
                message: $done,
            });
            this.$el.css('min-height', '450px');
        } else {
            $done.appendTo(this.$el);
        }
    },
    /**
     * update the statement rendering
     *
     * @param {object} state - statement data
     * @param {integer} state.valuenow - for the progress bar
     * @param {integer} state.valuemax - for the progress bar
     * @param {string} state.title - for the progress bar
     * @param {[object]} [state.notifications]
     */
    update: function (state) {
        var self = this;
        this.$progress.find('.valuenow').text(state.valuenow);
        this.$progress.find('.valuemax').text(state.valuemax);
        this.$progress.find('.progress-bar')
            .attr('aria-valuenow', state.valuenow)
            .attr('aria-valuemax', state.valuemax)
            .css('width', (state.valuenow/state.valuemax*100) + '%');

        if (state.valuenow === state.valuemax && !this.$('.done_message').length) {
            this.showRainbowMan(state);
        }

        if (state.notifications) {
            this._renderNotifications(state.notifications);
        }

        this.$('.statement_name, .statement_name_edition').toggle();
        this.$('h1.statement_name').text(state.title || _t('No Title'));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * render the notifications
     *
     * @param {[object]} notifications
     */
    _renderNotifications: function(notifications) {
        this.$(".notification_area").empty();
        for (var i=0; i<notifications.length; i++) {
            var $notification = $(qweb.render("reconciliation.notification", notifications[i])).hide();
            $notification.appendTo(this.$(".notification_area")).slideDown(300);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickStatementName: function () {
        if (this._initialState.bank_statement_id) {
            this.$('.statement_name, .statement_name_edition').toggle();
            this.$('.statement_name_edition input').focus();
        }
    },
    /**
     * @private
     * Click on close bank statement button, this will
     * close and then open form view of bank statement
     * @param {MouseEvent} event
     */
    _onCloseBankStatement: function (e) {
        this.trigger_up('close_statement');
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onDoAction: function(e) {
        e.preventDefault();
        var name = e.currentTarget.dataset.action_name;
        var model = e.currentTarget.dataset.model;
        var ids = e.currentTarget.dataset.ids.split(",").map(Number);
        this.do_action({
            name: name,
            res_model: model,
            domain: [['id', 'in', ids]],
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            view_type: "list",
            view_mode: "list"
        });
    },
    /**
     * Open the list view for account.bank.statement model
     * @private
     * @param {MouseEvent} event
     */
    _onGoToBankStatement: function (e) {
        var journalId = $(e.target).attr('data_journal_id');
        if (journalId) {
            journalId = parseInt(journalId);
        }
        this.do_action({
            name: 'Bank Statements',
            res_model: 'account.bank.statement',
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            context: {search_default_journal_id: journalId},
            view_type: 'list',
            view_mode: 'form',
        });
    },
    /**
     * Load more statement lines for reconciliation
     * @private
     * @param {MouseEvent} event
     */
    _onLoadMore: function (e) {
        this.trigger_up('load_more');
    },
    /**
     * @private
     */
    _onValidateName: function () {
        var name = this.$('.statement_name_edition input').val().trim();
        this.trigger_up('change_name', {'data': name});
    },
    /**
     * Save title on enter key pressed
     *
     * @private
     * @param {KeyboardEvent} event
     */
    _onKeyupInput: function (event) {
        if (event.which === $.ui.keyCode.ENTER) {
            this.$('.statement_name_edition input').blur();
        }
    },
});


/**
 * rendering of the bank statement line, contains line data, proposition and
 * view for 'match' and 'create' mode
 */
var LineRenderer = Widget.extend(FieldManagerMixin, {
    template: "reconciliation.line",
    events: {
        'click .accounting_view caption .o_buttons button': '_onValidate',
        'click .accounting_view thead td': '_onTogglePanel',
        'click .accounting_view tfoot td:not(.cell_left,.cell_right)': '_onShowPanel',
        'click tfoot .cell_left, tfoot .cell_right': '_onSearchBalanceAmount',
        'change input.filter': '_onFilterChange',
        'click .match .load-more a': '_onLoadMore',
        'click .match .mv_line td': '_onSelectMoveLine',
        'click .accounting_view tbody .mv_line td': '_onSelectProposition',
        'click .o_reconcile_models button': '_onQuickCreateProposition',
        'click .create .add_line': '_onCreateProposition',
        'click .accounting_view .line_info_button.fa-exclamation-triangle': '_onTogglePartialReconcile',
        'click .reconcile_model_create': '_onCreateReconcileModel',
        'click .reconcile_model_edit': '_onEditReconcileModel',
        'keyup input': '_onInputKeyup',
        'blur input': '_onInputKeyup',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        'field_changed': '_onFieldChanged',
    }),
    _avoidFieldUpdate: {},
    MV_LINE_DEBOUNCE: 200,

    /**
     * create partner_id field in editable mode
     *
     * @override
     */
    init: function (parent, model, state) {
        this._super(parent);
        FieldManagerMixin.init.call(this);

        this.model = model;
        this._initialState = state;
        if (this.MV_LINE_DEBOUNCE) {
            this._onSelectMoveLine = _.debounce(this._onSelectMoveLine, this.MV_LINE_DEBOUNCE, true);
        } else {
            this._onSelectMoveLine = this._onSelectMoveLine;
        }
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        var def1 = this._makePartnerRecord(this._initialState.st_line.partner_id, this._initialState.st_line.partner_name).then(function (recordID) {
            self.fields = {
                partner_id : new relational_fields.FieldMany2One(self,
                    'partner_id',
                    self.model.get(recordID), {
                        mode: 'edit',
                        attrs: {
                            placeholder: self._initialState.st_line.communication_partner_name || '',
                        }
                    }
                )
            };
            self.fields.partner_id.appendTo(self.$('.accounting_view caption'));
        });
        $('<span class="line_info_button fa fa-info-circle"/>')
            .appendTo(this.$('thead .cell_info_popover'))
            .attr("data-content", qweb.render('reconciliation.line.statement_line.details', {'state': this._initialState}));
        this.$el.popover({
            'selector': '.line_info_button',
            'placement': 'left',
            'container': this.$el,
            'html': true,
            'trigger': 'hover',
            'animation': false,
            'toggle': 'popover'
        });
        var def2 = this._super.apply(this, arguments);
        return $.when(def1, def2);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * update the statement line rendering
     *
     * @param {object} state - statement line
     */
    update: function (state) {
        var self = this;
        // isValid
        this.$('caption .o_buttons button.o_validate').toggleClass('d-none', !!state.balance.type);
        this.$('caption .o_buttons button.o_reconcile').toggleClass('d-none', state.balance.type <= 0);
        this.$('caption .o_buttons .o_no_valid').toggleClass('d-none', state.balance.type >= 0);

        // partner_id
        this._makePartnerRecord(state.st_line.partner_id, state.st_line.partner_name).then(function (recordID) {
            self.fields.partner_id.reset(self.model.get(recordID));
            self.$el.attr('data-partner', state.st_line.partner_id);
        });

        // mode
        this.$('.create, .match').each(function () {
            var $panel = $(this);
            $panel.css('-webkit-transition', 'none');
            $panel.css('-moz-transition', 'none');
            $panel.css('-o-transition', 'none');
            $panel.css('transition', 'none');
            $panel.css('max-height', $panel.height());
            $panel.css('-webkit-transition', '');
            $panel.css('-moz-transition', '');
            $panel.css('-o-transition', '');
            $panel.css('transition', '');
        });
        this.$el.data('mode', state.mode).attr('data-mode', state.mode);
        this.$('.create, .match').each(function () {
            $(this).removeAttr('style');
        });

        // reconciliation_proposition
        var $props = this.$('.accounting_view tbody').empty();

        // Search propositions that could be a partial credit/debit.
        var props = [];
        var partialDebitProp;
        var partialCreditProp;
        var balance = state.balance.amount_currency;
        _.each(state.reconciliation_proposition, function (prop) {
            if (prop.display) {
                props.push(prop);

                /*
                Examples:
                statement line      | 100   |       |
                move line 1         |       | 200   | <- can be a partial of 100
                balance: -100

                statement line      | 500   |       |
                move line 1         |       | 300   | <- is not a eligible to be a partial due to the second line.
                move line 2         |       | 300   | <- can be a partial of 200
                balance: -100

                statement line      | 500   |       |
                move line 1         |       | 700   | <- must not be a partial (debit = 800 > 700 = credit).
                move line 2         | 300   |       |
                balance: 100
                */
                if(!prop.display_new && balance < 0 && prop.amount > 0 && balance + prop.amount > 0)
                    partialDebitProp = prop;
                else if(!prop.display_new && balance > 0 && prop.amount < 0 && balance + prop.amount < 0)
                    partialCreditProp = prop;
            }
        });

        _.each(props, function (line) {
            line.display_triangle = (line.already_paid === false &&
                (((state.balance.amount_currency < 0 || line.partial_reconcile) && partialDebitProp && partialDebitProp === line) ||
                ((state.balance.amount_currency > 0 || line.partial_reconcile) && partialCreditProp && partialCreditProp === line)));
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }
            $props.append($line);
        });

        // mv_lines
        var stateMvLines = state.mv_lines || [];
        var recs_count = stateMvLines.length > 0 ? stateMvLines[0].recs_count : 0;
        var remaining = recs_count - stateMvLines.length;
        var $mv_lines = this.$('.match table tbody').empty();

        _.each(stateMvLines, function (line) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }
            $mv_lines.append($line);
        });
        this.$('.match div.load-more').toggle(remaining > 0);
        this.$('.match div.load-more span').text(remaining);
        this.$('.match').css('max-height', !stateMvLines.length && !state.filter.length ? '0px' : '');

        // balance
        this.$('.popover').remove();
        this.$('table tfoot').html(qweb.render("reconciliation.line.balance", {'state': state}));

        // filter
        if (_.str.strip(this.$('input.filter').val()) !== state.filter) {
            this.$('input.filter').val(state.filter);
        }

        // create form
        if (state.createForm) {
            if (!this.fields.account_id) {
                this._renderCreate(state);
            }
            var data = this.model.get(this.handleCreateRecord).data;
            this.model.notifyChanges(this.handleCreateRecord, state.createForm).then(function () {
                // FIXME can't it directly written REPLACE_WITH ids=state.createForm.analytic_tag_ids
                self.model.notifyChanges(self.handleCreateRecord, {analytic_tag_ids: {operation: 'REPLACE_WITH', ids: []}}).then(function (){
                    var defs = [];
                    _.each(state.createForm.analytic_tag_ids, function (tag) {
                        defs.push(self.model.notifyChanges(self.handleCreateRecord, {analytic_tag_ids: {operation: 'ADD_M2M', ids: tag}}));
                    });
                    $.when.apply($, defs).then(function () {
                        var record = self.model.get(self.handleCreateRecord);
                        _.each(self.fields, function (field, fieldName) {
                            if (self._avoidFieldUpdate[fieldName]) return;
                            if (fieldName === "partner_id") return;
                            if ((data[fieldName] || state.createForm[fieldName]) && !_.isEqual(state.createForm[fieldName], data[fieldName])) {
                                field.reset(record);
                            }
                            if (fieldName === 'tax_id') {
                                if (!state.createForm[fieldName] || state.createForm[fieldName].amount_type === "group") {
                                    $('.create_force_tax_included').addClass('d-none');
                                }
                                else {
                                    $('.create_force_tax_included').removeClass('d-none');
                                }
                            } 
                        });
                    });
                });
            });
            if(state.createForm.tax_id){
                // Set the 'Tax Include' field editable or not depending of the 'price_include' value.
                this.$('.create_force_tax_included input').attr('disabled', state.createForm.tax_id.price_include);
            }
        }
        this.$('.create .add_line').toggle(!!state.balance.amount_currency);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQueryElement} $el
     */
    _destroyPopover: function ($el) {
        var popover = $el.data('bs.popover');
        if (popover) {
            popover.dispose();
        }
    },
    /**
     * @private
     * @param {integer} partnerID
     * @param {string} partnerName
     * @returns {string} local id of the dataPoint
     */
    _makePartnerRecord: function (partnerID, partnerName) {
        var field = {
            relation: 'res.partner',
            type: 'many2one',
            name: 'partner_id',
        };
        if (partnerID) {
            field.value = [partnerID, partnerName];
        }
        return this.model.makeRecord('account.bank.statement.line', [field], {
            partner_id: {
                domain: ["|", ["is_company", "=", true], ["parent_id", "=", false], "|", ["customer", "=", true], ["supplier", "=", true]],
                options: {
                    no_open: true
                }
            }
        });
    },

    /**
     * create account_id, tax_id, analytic_account_id, analytic_tag_ids, label and amount fields
     *
     * @private
     * @param {object} state - statement line
     */
    _renderCreate: function (state) {
        var self = this;
        this.model.makeRecord('account.bank.statement.line', [{
            relation: 'account.account',
            type: 'many2one',
            name: 'account_id',
            domain: [['company_id', '=', state.st_line.company_id]],
        }, {
            relation: 'account.journal',
            type: 'many2one',
            name: 'journal_id',
            domain: [['company_id', '=', state.st_line.company_id]],
        }, {
            relation: 'account.tax',
            type: 'many2one',
            name: 'tax_id',
            domain: [['company_id', '=', state.st_line.company_id]],
        }, {
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'analytic_account_id',
        }, {
            relation: 'account.analytic.tag',
            type: 'many2many',
            name: 'analytic_tag_ids',
        }, {
            type: 'boolean',
            name: 'force_tax_included',
        }, {
            type: 'char',
            name: 'label',
        }, {
            type: 'float',
            name: 'amount',
        }, {
            type: 'char', //TODO is it a bug or a feature when type date exists ?
            name: 'date',
        }], {
            account_id: {
                string: _t("Account"),
                domain: [['deprecated', '=', false]],
            },
            label: {string: _t("Label")},
            amount: {string: _t("Account")},
        }).then(function (recordID) {
            self.handleCreateRecord = recordID;
            var record = self.model.get(self.handleCreateRecord);

            self.fields.account_id = new relational_fields.FieldMany2One(self,
                'account_id', record, {mode: 'edit'});

            self.fields.journal_id = new relational_fields.FieldMany2One(self,
                'journal_id', record, {mode: 'edit'});

            self.fields.tax_id = new relational_fields.FieldMany2One(self,
                'tax_id', record, {mode: 'edit', additionalContext: {append_type_to_tax_name: true}});

            self.fields.analytic_account_id = new relational_fields.FieldMany2One(self,
                'analytic_account_id', record, {mode: 'edit'});

            self.fields.analytic_tag_ids = new relational_fields.FieldMany2ManyTags(self,
                'analytic_tag_ids', record, {mode: 'edit'});

            self.fields.force_tax_included = new basic_fields.FieldBoolean(self,
                'force_tax_included', record, {mode: 'edit'});

            self.fields.label = new basic_fields.FieldChar(self,
                'label', record, {mode: 'edit'});

            self.fields.amount = new basic_fields.FieldFloat(self,
                'amount', record, {mode: 'edit'});
            
            self.fields.date = new basic_fields.FieldDate(self,
                'date', record, {mode: 'edit'});

            var $create = $(qweb.render("reconciliation.line.create", {'state': state}));
            self.fields.account_id.appendTo($create.find('.create_account_id .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.account_id));
            self.fields.journal_id.appendTo($create.find('.create_journal_id .o_td_field'));
            self.fields.tax_id.appendTo($create.find('.create_tax_id .o_td_field'));
            self.fields.analytic_account_id.appendTo($create.find('.create_analytic_account_id .o_td_field'));
            self.fields.analytic_tag_ids.appendTo($create.find('.create_analytic_tag_ids .o_td_field'));
            self.fields.force_tax_included.appendTo($create.find('.create_force_tax_included .o_td_field'))
            self.fields.label.appendTo($create.find('.create_label .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.label));
            self.fields.amount.appendTo($create.find('.create_amount .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.amount));
            self.fields.date.appendTo($create.find('.create_date .o_td_field'))
            self.$('.create').append($create);

            function addRequiredStyle(widget) {
                widget.$el.addClass('o_required_modifier');
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onCreateReconcileModel: function (event) {
        event.preventDefault();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.reconcile.model',
            views: [[false, 'form']],
            target: 'current'
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onEditReconcileModel: function (event) {
        event.preventDefault();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.reconcile.model',
            views: [[false, 'list'], [false, 'form']],
            view_type: "list",
            view_mode: "list",
            target: 'current'
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        event.stopPropagation();
        var fieldName = event.target.name;
        if (fieldName === 'partner_id') {
            var partner_id = event.data.changes.partner_id;
            this.trigger_up('change_partner', {'data': partner_id});
        } else {
            if (event.data.changes.amount && isNaN(event.data.changes.amount)) {
                return;
            }
            this.trigger_up('update_proposition', {'data': event.data.changes});
        }
    },
    /**
     * @private
     */
    _onTogglePanel: function () {
        var mode = this.$el.data('mode') === 'inactive' ? 'match' : 'inactive';
        this.trigger_up('change_mode', {'data': mode});
    },
    /**
     * @private
     */
    _onSearchBalanceAmount: function () {
        this.trigger_up('search_balance_amount');
    },
    /**
     * @private
     */
    _onShowPanel: function () {
        var mode = (this.$el.data('mode') === 'inactive' || this.$el.data('mode') === 'match') ? 'create' : 'match';
        this.trigger_up('change_mode', {'data': mode});
    },
    /**
     * @private
     * @param {input event} event
     */
    _onFilterChange: function (event) {
        this.trigger_up('change_filter', {'data': _.str.strip($(event.target).val())});
    },
    /**
     * @private
     * @param {keyup event} event
     */
    _onInputKeyup: function (event) {
        var target_partner_id = $(event.target).parents('[name="partner_id"]');
        if (target_partner_id.length === 1) {
            return;
        }
        if(event.keyCode === 13) {
            var created_lines = _.findWhere(this.model.lines, {mode: 'create'});
            if (created_lines && created_lines.balance.amount) {
                this._onCreateProposition();
            }
            return;
        }

        var self = this;
        for (var fieldName in this.fields) {
            var field = this.fields[fieldName];
            if (!field.$el.is(event.target)) {
                continue;
            }
            this._avoidFieldUpdate[field.name] = event.type !== 'focusout';
            field.value = false;
            field._setValue($(event.target).val()).then(function () {
                self._avoidFieldUpdate[field.name] = false;
            });
            break;
        }
    },
    /**
     * @private
     */
    _onLoadMore: function (ev) {
        ev.preventDefault();
        this.trigger_up('change_offset', {'data': 1});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onSelectMoveLine: function (event) {
        var $el = $(event.target);
        this._destroyPopover($el);
        var moveLineId = $el.closest('.mv_line').data('line-id');
        this.trigger_up('add_proposition', {'data': moveLineId});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onSelectProposition: function (event) {
        var $el = $(event.target);
        this._destroyPopover($el);
        var moveLineId = $el.closest('.mv_line').data('line-id');
        this.trigger_up('remove_proposition', {'data': moveLineId});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onQuickCreateProposition: function (event) {
        document.activeElement && document.activeElement.blur();
        this.trigger_up('quick_create_proposition', {'data': $(event.target).data('reconcile-model-id')});
    },
    /**
     * @private
     */
    _onCreateProposition: function () {
        document.activeElement && document.activeElement.blur();
        var invalid = [];
        _.each(this.fields, function (field) {
            if (!field.isValid()) {
                invalid.push(field.string);
            }
        });
        if (invalid.length) {
            this.do_warn(_t("Some fields are undefined"), invalid.join(', '));
            return;
        }
        this.trigger_up('create_proposition');
    },
    /**
     * @private
     */
    _onValidate: function () {
        this.trigger_up('validate');
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onTogglePartialReconcile: function (e) {
        e.stopPropagation();
        var popover = $(e.target).data('bs.popover');
        popover && popover.dispose();
        this.trigger_up('toggle_partial_reconcile');
    }
});


/**
 * rendering of the manual reconciliation action contains progress bar, title
 * and auto reconciliation button
 */
var ManualRenderer = StatementRenderer.extend({
    template: "reconciliation.manual.statement",

    /**
     * avoid statement name edition
     *
     * @override
     * @private
     */
    _onClickStatementName: function () {}
});


/**
 * rendering of the manual reconciliation, contains line data, proposition and
 * view for 'match' mode
 */
var ManualLineRenderer = LineRenderer.extend({
    template: "reconciliation.manual.line",
     /**
     * @override
     * @param {string} handle
     * @param {number} proposition id (move line id)
     * @returns {Deferred}
     */
    removeProposition: function (handle, id) {
        if (!id) {
            return $.when();
        }
        return this._super(handle, id);
    },
    /**
     * move the partner field
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var defs = [];
            var def;
            if (self._initialState.partner_id) {
                def = self._makePartnerRecord(self._initialState.partner_id, self._initialState.partner_name).then(function (recordID) {
                    self.fields.partner_id = new relational_fields.FieldMany2One(self,
                        'partner_id',
                        self.model.get(recordID),
                        {mode: 'readonly'}
                    );
                });
                defs.push(def);
            } else {
                def = self.model.makeRecord('account.move.line', [{
                    relation: 'account.account',
                    type: 'many2one',
                    name: 'account_id',
                    value: [self._initialState.account_id.id, self._initialState.account_id.display_name],
                }]).then(function (recordID) {
                    self.fields.title_account_id = new relational_fields.FieldMany2One(self,
                        'account_id',
                        self.model.get(recordID),
                        {mode: 'readonly'}
                    );
                });
                defs.push(def);
            }

            return $.when.apply($, defs).then(function () {
                if (!self.fields.title_account_id) {
                    return self.fields.partner_id.prependTo(self.$('.accounting_view thead td:eq(1) span:first'));
                } else {
                    self.fields.partner_id.destroy();
                    return self.fields.title_account_id.appendTo(self.$('.accounting_view thead td:eq(1) span:first'));
                }
            });
        });
    },
    /**
     * @override
     */
    update: function (state) {
        this._super(state);
        var props = _.filter(state.reconciliation_proposition, {'display': true});
        if (!props.length) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': {}, 'state': state}));
            this.$('.accounting_view tbody').append($line);
        }
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * display journal_id field
     *
     * @override
     */
    _renderCreate: function (state) {
        this._super(state);
        this.$('.create .create_journal_id').show();
        this.$('.create .create_date').removeClass('d-none')
        this.$('.create .create_journal_id .o_input').addClass('o_required_modifier');
    },

});


return {
    StatementRenderer: StatementRenderer,
    ManualRenderer: ManualRenderer,
    LineRenderer: LineRenderer,
    ManualLineRenderer: ManualLineRenderer,
};
});
