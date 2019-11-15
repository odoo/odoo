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
        'click *[rel="do_action"]': '_onDoAction',
        'click button.js_load_more': '_onLoadMore',
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
        this.$progress = $('');

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /*
     * hide the button to load more statement line
     */
    hideLoadMoreButton: function (show) {
        if (!show) {
            this.$('.js_load_more').show();
        }
        else {
            this.$('.js_load_more').hide();
        }
    },
    showRainbowMan: function (state) {
        if (this.model.display_context !== 'validate') {
            return
        }
        var dt = Date.now()-this.time;
        var $done = $(qweb.render("reconciliation.done", {
            'duration': moment(dt).utc().format(time.getLangTimeFormat()),
            'number': state.valuenow,
            'timePerTransaction': Math.round(dt/1000/state.valuemax),
            'context': state.context,
        }));
        $done.find('*').addClass('o_reward_subcontent');
        $done.find('.button_close_statement').click(this._onCloseBankStatement.bind(this));
        $done.find('.button_back_to_statement').click(this._onGoToBankStatement.bind(this));
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
        this._updateProgressBar(state);

        if (state.valuenow === state.valuemax && !this.$('.done_message').length) {
            this.showRainbowMan(state);
        }

        if (state.notifications) {
            this._renderNotifications(state.notifications);
        }
    },
    _updateProgressBar: function(state) {
        this.$progress.find('.valuenow').text(state.valuenow);
        this.$progress.find('.valuemax').text(state.valuemax);
        this.$progress.find('.progress-bar')
            .attr('aria-valuenow', state.valuenow)
            .attr('aria-valuemax', state.valuemax)
            .css('width', (state.valuenow/state.valuemax*100) + '%');
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
        if (e.currentTarget.dataset.ids) {
            var ids = e.currentTarget.dataset.ids.split(",").map(Number);
            var domain = [['id', 'in', ids]];
        } else {
            var domain = e.currentTarget.dataset.domain;
        }
        var context = e.currentTarget.dataset.context;
        var tag = e.currentTarget.dataset.tag;
        if (tag) {
            this.do_action({
                type: 'ir.actions.client',
                tag: tag,
                context: context,
            })
        } else {
            this.do_action({
                name: name,
                res_model: model,
                domain: domain,
                context: context,
                views: [[false, 'list'], [false, 'form']],
                type: 'ir.actions.act_window',
                view_mode: "list"
            });
        }
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
        $('.o_reward').remove();
        this.do_action({
            name: 'Bank Statements',
            res_model: 'account.bank.statement',
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            context: {search_default_journal_id: journalId, 'journal_type':'bank'},
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
});


/**
 * rendering of the bank statement line, contains line data, proposition and
 * view for 'match' and 'create' mode
 */
var LineRenderer = Widget.extend(FieldManagerMixin, {
    template: "reconciliation.line",
    events: {
        'click .accounting_view caption .o_buttons button': '_onValidate',
        'click .accounting_view tfoot': '_onChangeTab',
        'click': '_onTogglePanel',
        'click .o_field_widget': '_onStopPropagation',
        'keydown .o_input, .edit_amount_input': '_onStopPropagation',
        'click .o_notebook li a': '_onChangeTab',
        'click .cell': '_onEditAmount',
        'change input.filter': '_onFilterChange',
        'click .match .load-more a': '_onLoadMore',
        'click .match .mv_line td': '_onSelectMoveLine',
        'click .accounting_view tbody .mv_line td': '_onSelectProposition',
        'click .o_reconcile_models button': '_onQuickCreateProposition',
        'click .create .add_line': '_onCreateProposition',
        'click .reconcile_model_create': '_onCreateReconcileModel',
        'click .reconcile_model_edit': '_onEditReconcileModel',
        'keyup input': '_onInputKeyup',
        'blur input': '_onInputKeyup',
        'keydown': '_onKeydown',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        'field_changed': '_onFieldChanged',
    }),
    _avoidFieldUpdate: {},
    MV_LINE_DEBOUNCE: 200,

    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ENTER:
                this.trigger_up('navigation_move', {direction: 'validate', handle: this.handle});
                break;
            case $.ui.keyCode.UP:
                ev.stopPropagation();
                ev.preventDefault();
                this.trigger_up('navigation_move', {direction: 'up', handle: this.handle});
                break;
            case $.ui.keyCode.DOWN:
                ev.stopPropagation();
                ev.preventDefault();
                this.trigger_up('navigation_move', {direction: 'down', handle: this.handle});
                break;
        }
    },

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
                            placeholder: self._initialState.st_line.communication_partner_name || _t('Select Partner'),
                        }
                    }
                )
            };
            self.fields.partner_id.insertAfter(self.$('.accounting_view caption .o_buttons'));
        });
        $('<span class="line_info_button fa fa-info-circle"/>')
            .appendTo(this.$('thead .cell_info_popover'))
            .attr("data-content", qweb.render('reconciliation.line.statement_line.details', {'state': this._initialState}));
        this.$el.popover({
            'selector': '.line_info_button',
            'placement': 'left',
            'container': this.$el,
            'html': true,
            // disable bootstrap sanitizer because we use a table that has been
            // rendered using qweb.render so it is safe and also because sanitizer escape table by default.
            'sanitize': false,
            'trigger': 'hover',
            'animation': false,
            'toggle': 'popover'
        });
        var def2 = this._super.apply(this, arguments);
        return Promise.all([def1, def2]);
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
        var to_check_checked = !!(state.to_check);
        this.$('caption .o_buttons button.o_validate').toggleClass('d-none', !!state.balance.type && !to_check_checked);
        this.$('caption .o_buttons button.o_reconcile').toggleClass('d-none', state.balance.type <= 0 || to_check_checked);
        this.$('caption .o_buttons .o_no_valid').toggleClass('d-none', state.balance.type >= 0);
        self.$('caption .o_buttons button.o_validate').toggleClass('text-warning', to_check_checked);

        // partner_id
        this._makePartnerRecord(state.st_line.partner_id, state.st_line.partner_name).then(function (recordID) {
            self.fields.partner_id.reset(self.model.get(recordID));
            self.$el.attr('data-partner', state.st_line.partner_id);
        });

        // mode
        this.$el.data('mode', state.mode).attr('data-mode', state.mode);
        this.$('.o_notebook li a').attr('aria-selected', false);
        this.$('.o_notebook li a').removeClass('active');
        this.$('.o_notebook .tab-content .tab-pane').removeClass('active');
        this.$('.o_notebook li a[href*="notebook_page_' + state.mode + '"]').attr('aria-selected', true);
        this.$('.o_notebook li a[href*="notebook_page_' + state.mode + '"]').addClass('active');
        this.$('.o_notebook .tab-content .tab-pane[id*="notebook_page_' + state.mode + '"]').addClass('active');
        this.$('.create, .match').each(function () {
            $(this).removeAttr('style');
        });

        // reconciliation_proposition
        var $props = this.$('.accounting_view tbody').empty();

        // Search propositions that could be a partial credit/debit.
        var props = [];
        var balance = state.balance.amount_currency;
        _.each(state.reconciliation_proposition, function (prop) {
            if (prop.display) {
                props.push(prop);
            }
        });

        _.each(props, function (line) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state, 'proposition': true}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }
            $props.append($line);
        });

        // mv_lines
        var matching_modes = self.model.modes.filter(x => x.startsWith('match'));
        for (let i = 0; i < matching_modes.length; i++) {
            var stateMvLines = state['mv_lines_'+matching_modes[i]] || [];
            var recs_count = stateMvLines.length > 0 ? stateMvLines[0].recs_count : 0;
            var remaining = state['remaining_' + matching_modes[i]];
            var $mv_lines = this.$('div[id*="notebook_page_' + matching_modes[i] + '"] .match table tbody').empty();
            this.$('.o_notebook li a[href*="notebook_page_' + matching_modes[i] + '"]').parent().toggleClass('d-none', stateMvLines.length === 0 && !state['filter_'+matching_modes[i]]);

            _.each(stateMvLines, function (line) {
                var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
                if (!isNaN(line.id)) {
                    $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
                }
                $mv_lines.append($line);
            });
            this.$('div[id*="notebook_page_' + matching_modes[i] + '"] .match div.load-more').toggle(remaining > 0);
            this.$('div[id*="notebook_page_' + matching_modes[i] + '"] .match div.load-more span').text(remaining);
        }

        // balance
        this.$('.popover').remove();
        this.$('table tfoot').html(qweb.render("reconciliation.line.balance", {'state': state}));

        // create form
        if (state.createForm) {
            var createPromise;
            if (!this.fields.account_id) {
                createPromise = this._renderCreate(state);
            }
            Promise.resolve(createPromise).then(function(){
                var data = self.model.get(self.handleCreateRecord).data;
                return self.model.notifyChanges(self.handleCreateRecord, state.createForm)
                    .then(function () {
                    // FIXME can't it directly written REPLACE_WITH ids=state.createForm.analytic_tag_ids
                        return self.model.notifyChanges(self.handleCreateRecord, {analytic_tag_ids: {operation: 'REPLACE_WITH', ids: []}})
                    })
                    .then(function (){
                        var defs = [];
                        _.each(state.createForm.analytic_tag_ids, function (tag) {
                            defs.push(self.model.notifyChanges(self.handleCreateRecord, {analytic_tag_ids: {operation: 'ADD_M2M', ids: tag}}));
                        });
                        return Promise.all(defs);
                    })
                    .then(function () {
                        return self.model.notifyChanges(self.handleCreateRecord, {tax_ids: {operation: 'REPLACE_WITH', ids: []}})
                    })
                    .then(function (){
                        var defs = [];
                        _.each(state.createForm.tax_ids, function (tag) {
                            defs.push(self.model.notifyChanges(self.handleCreateRecord, {tax_ids: {operation: 'ADD_M2M', ids: tag}}));
                        });
                        return Promise.all(defs);
                    })
                    .then(function () {
                        var record = self.model.get(self.handleCreateRecord);
                        _.each(self.fields, function (field, fieldName) {
                            if (self._avoidFieldUpdate[fieldName]) return;
                            if (fieldName === "partner_id") return;
                            if ((data[fieldName] || state.createForm[fieldName]) && !_.isEqual(state.createForm[fieldName], data[fieldName])) {
                                field.reset(record);
                            }
                            if (fieldName === 'tax_ids') {
                                if (!state.createForm[fieldName].length || state.createForm[fieldName].length > 1) {
                                    $('.create_force_tax_included').addClass('d-none');
                                }
                                else {
                                    $('.create_force_tax_included').removeClass('d-none');
                                    var price_include = state.createForm[fieldName][0].price_include;
                                    var force_tax_included = state.createForm[fieldName][0].force_tax_included;
                                    self.$('.create_force_tax_included input').prop('checked', force_tax_included);
                                    self.$('.create_force_tax_included input').prop('disabled', price_include);
                                }
                            }
                        });
                        if (state.to_check) {
                            // Set the to_check field to true if global to_check is set
                            self.$('.create_to_check input').prop('checked', state.to_check).change();
                        }
                        return true;
                    });
            });
        }
        this.$('.create .add_line').toggle(!!state.balance.amount_currency);
    },

    updatePartialAmount: function(line_id, amount) {
        var $line = this.$('.mv_line[data-line-id='+line_id+']');
        $line.find('.edit_amount').addClass('d-none');
        $line.find('.edit_amount_input').removeClass('d-none');
        $line.find('.edit_amount_input').focus();
        $line.find('.edit_amount_input').val(amount);
        $line.find('.line_amount').addClass('d-none');
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
                domain: ["|", ["is_company", "=", true], ["parent_id", "=", false]],
                options: {
                    no_open: true
                }
            }
        });
    },

    /**
     * create account_id, tax_ids, analytic_account_id, analytic_tag_ids, label and amount fields
     *
     * @private
     * @param {object} state - statement line
     * @returns {Promise}
     */
    _renderCreate: function (state) {
        var self = this;
        return this.model.makeRecord('account.bank.statement.line', [{
            relation: 'account.account',
            type: 'many2one',
            name: 'account_id',
            domain: [['company_id', '=', state.st_line.company_id], ['deprecated', '=', false]],
        }, {
            relation: 'account.journal',
            type: 'many2one',
            name: 'journal_id',
            domain: [['company_id', '=', state.st_line.company_id]],
        }, {
            relation: 'account.tax',
            type: 'many2many',
            name: 'tax_ids',
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
        }, {
            type: 'boolean',
            name: 'to_check',
        }], {
            account_id: {
                string: _t("Account"),
            },
            label: {string: _t("Label")},
            amount: {string: _t("Account")},
        }).then(function (recordID) {
            self.handleCreateRecord = recordID;
            var record = self.model.get(self.handleCreateRecord);

            self.fields.account_id = new relational_fields.FieldMany2One(self,
                'account_id', record, {mode: 'edit', attrs: {can_create:false}});

            self.fields.journal_id = new relational_fields.FieldMany2One(self,
                'journal_id', record, {mode: 'edit'});

            self.fields.tax_ids = new relational_fields.FieldMany2ManyTags(self,
                'tax_ids', record, {mode: 'edit', additionalContext: {append_type_to_tax_name: true}});

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

            self.fields.to_check = new basic_fields.FieldBoolean(self,
                'to_check', record, {mode: 'edit'});

            var $create = $(qweb.render("reconciliation.line.create", {'state': state}));
            self.fields.account_id.appendTo($create.find('.create_account_id .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.account_id));
            self.fields.journal_id.appendTo($create.find('.create_journal_id .o_td_field'));
            self.fields.tax_ids.appendTo($create.find('.create_tax_id .o_td_field'));
            self.fields.analytic_account_id.appendTo($create.find('.create_analytic_account_id .o_td_field'));
            self.fields.analytic_tag_ids.appendTo($create.find('.create_analytic_tag_ids .o_td_field'));
            self.fields.force_tax_included.appendTo($create.find('.create_force_tax_included .o_td_field'));
            self.fields.label.appendTo($create.find('.create_label .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.label));
            self.fields.amount.appendTo($create.find('.create_amount .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.amount));
            self.fields.date.appendTo($create.find('.create_date .o_td_field'));
            self.fields.to_check.appendTo($create.find('.create_to_check .o_td_field'));
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
     * The event on the partner m2o widget was propagated to the bank statement
     * line widget, causing it to expand and the others to collapse. This caused
     * the dropdown to be poorly placed and an unwanted update of this widget.
     *
     * @private
     */
    _onStopPropagation: function(ev) {
        ev.stopPropagation();
    },

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onCreateReconcileModel: function (event) {
        event.preventDefault();
        var self = this;
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.reconcile.model',
            views: [[false, 'form']],
            target: 'current'
        },
        {
            on_reverse_breadcrumb: function() {self.trigger_up('reload');},
        });
    },
    _editAmount: function (event) {
        event.stopPropagation();
        var $line = $(event.target);
        var moveLineId = $line.closest('.mv_line').data('line-id');
        this.trigger_up('partial_reconcile', {'data': {mvLineId: moveLineId, 'amount': $line.val()}});
    },
    _onEditAmount: function (event) {
        event.preventDefault();
        event.stopPropagation();
        // Don't call when clicking inside the input field
        if (! $(event.target).hasClass('edit_amount_input')){
            var $line = $(event.target);
            this.trigger_up('getPartialAmount', {'data': $line.closest('.mv_line').data('line-id')});
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onEditReconcileModel: function (event) {
        event.preventDefault();
        var self = this;
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.reconcile.model',
            views: [[false, 'list'], [false, 'form']],
            view_mode: "list",
            target: 'current'
        },
        {
            on_reverse_breadcrumb: function() {self.trigger_up('reload');},
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
        if (this.$el[0].getAttribute('data-mode') == 'inactive')
            this.trigger_up('change_mode', {'data': 'default'});
    },
    /**
     * @private
     */
    _onChangeTab: function(event) {
        if (event.currentTarget.nodeName === 'TFOOT') {
            this.trigger_up('change_mode', {'data': 'next'});
        } else {
            var modes = this.model.modes;
            var selected_mode = modes.find(function(e) {return event.target.getAttribute('href').includes(e)});
            if (selected_mode) {
                this.trigger_up('change_mode', {'data': selected_mode});
            }
        }
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
            if ($(event.target).hasClass('edit_amount_input')) {
                $(event.target).blur();
                return;
            }
            var created_lines = _.findWhere(this.model.lines, {mode: 'create'});
            if (created_lines && created_lines.balance.amount) {
                this._onCreateProposition();
            }
            return;
        }
        if ($(event.target).hasClass('edit_amount_input')) {
            if (event.type === 'keyup') {
                return;
            }
            else {
                return this._editAmount(event);
            }
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
        this.trigger_up('change_offset');
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onSelectMoveLine: function (event) {
        var $el = $(event.target);
        $el.prop('disabled', true);
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
    }
});


/**
 * rendering of the manual reconciliation action contains progress bar, title
 * and auto reconciliation button
 */
var ManualRenderer = StatementRenderer.extend({
    template: "reconciliation.manual.statement",

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
     * @returns {Promise}
     */
    removeProposition: function (handle, id) {
        if (!id) {
            return Promise.resolve();
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
            return self.model.makeRecord('account.move.line', [{
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
            }).then(function () {
                return self.fields.title_account_id.appendTo(self.$('.accounting_view thead td:eq(0) span:first'));
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
        var self = this;
        var parentPromise = this._super(state).then(function() {
            self.$('.create .create_journal_id').show();
            self.$('.create .create_date').removeClass('d-none');
            self.$('.create .create_journal_id .o_input').addClass('o_required_modifier');
        });
        return parentPromise;
    },

});


return {
    StatementRenderer: StatementRenderer,
    ManualRenderer: ManualRenderer,
    LineRenderer: LineRenderer,
    ManualLineRenderer: ManualLineRenderer,
};
});
