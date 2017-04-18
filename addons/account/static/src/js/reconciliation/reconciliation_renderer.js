odoo.define('account.ReconciliationRenderer', function (require) {
"use strict";

var Widget = require('web.Widget');
var FieldManagerMixin = require('web.FieldManagerMixin');
var relational_fields = require('web.relational_fields');
var basic_fields = require('web.basic_fields');
var core = require('web.core');
var time = require('web.time');
var qweb = core.qweb;
var _t = core._t;


/**
 * rendering of the bank statement action contains progress bar, title and
 * auto reconciliation button
 */
var StatementRenderer = Widget.extend(FieldManagerMixin, {
    template: 'reconciliation.statement',
    events: {
        'click div:first button.o_automatic_reconciliation': '_onAutoReconciliation',
        'click div:first h1.statement_name': '_onClickStatementName',
        'click div:first h1.statement_name_edition button': '_onValidateName',
        "click *[rel='do_action']": "_onDoAction",
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
                    self.name.$el.addClass('o_form_required');
                });
                self.$('.statement_name').text(self._initialState.bank_statement_id.display_name);
            });
            defs.push(def);
        }

        this.$('h1.statement_name').text(this._initialState.title);

        delete this._initialState;

        this.enterHandler = function (e) {
            if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey)) {
                this.trigger_up('validate_all_balanced');
            }
        }.bind(this);
        $('body').on('keyup', this.enterHandler);

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
        this.$progress.find('.valuenow').text(state.valuenow);
        this.$progress.find('.valuemax').text(state.valuemax);
        this.$progress.find('.progress-bar')
            .attr('aria-valuenow', state.valuenow)
            .attr('aria-valuemax', state.valuemax)
            .css('width', (state.valuenow/state.valuemax*100) + '%');

        if (state.valuenow === state.valuemax) {
            var dt = Date.now()-this.time;
            var $done = $(qweb.render("reconciliation.done", {
                'duration': moment(dt).utc().format(time.strftime_to_moment_format(_t.database.parameters.time_format)),
                'number': state.valuenow,
                'timePerTransaction': Math.round(dt/1000/state.valuemax)
            }));
            $done.appendTo(this.$el.first());
            this.$('.o_automatic_reconciliation').hide();
        }

        if (state.notifications) {
            this._renderNotifications(state.notifications);
        }

        this.$('h1.statement_name').text(state.title);
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
        for (var i=0; i<notifications.length; i++) {
            var $notification = $(qweb.render("reconciliation.notification", {
                type: notifications[i].type,
                message: notifications[i].message,
                details: notifications[i].details,
            })).hide();
            $notification.appendTo(this.$(".notification_area")).slideDown(300);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAutoReconciliation: function () {
        this.trigger_up('auto_reconciliation');
    },
    /**
     * @private
     */
    _onClickStatementName: function () {
        this.$('.statement_name, .statement_name_edition').toggle();
    },
    /**
     * @private
     */
    _onValidateName: function () {
        var name = this.model.get(this.handleNameRecord).data.name;
        this.trigger_up('change_name', {'data': name});
        this.$('.statement_name, .statement_name_edition').toggle();
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
        'click .accounting_view tfoot td': '_onShowPanel',
        'input input.filter': '_onFilterChange',
        'click .match_controls .fa-chevron-left:not(.disabled)': '_onPrevious',
        'click .match_controls .fa-chevron-right:not(.disabled)': '_onNext',
        'click .match .mv_line td': '_onSelectMoveLine',
        'click .accounting_view tbody .mv_line td': '_onSelectProposition',
        'click .o_reconcile_models button': '_onQuickCreateProposition',
        'click .create .add_line': '_onCreateProposition',
        'click .accounting_view .line_info_button.fa-exclamation-triangle': '_onTogglePartialReconcile',
        'click .reconcile_model_create': '_onCreateReconcileModel',
        'click .reconcile_model_edit': '_onEditReconcileModel',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        'field_changed': '_onFieldChanged',
    }),

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
                    self.model.get(recordID),
                    {mode: 'edit'}
                )
            };
            self.fields.partner_id.appendTo(self.$('.accounting_view caption'));
        });
        this.$('thead .line_info_button').attr("data-content", qweb.render('reconciliation.line.statement_line.details', {'state': this._initialState}));
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
        this.$('caption .o_buttons button.o_validate').toggleClass('hidden', !!state.balance.type);
        this.$('caption .o_buttons button.o_reconcile').toggleClass('hidden', state.balance.type <= 0);
        this.$('caption .o_buttons .o_no_valid').toggleClass('hidden', state.balance.type >= 0);

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
        var props = _.filter(state.reconciliation_proposition, {'display': true});
        _.each(props, function (line) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }

            if ((state.balance.amount !== 0 || line.partial_reconcile) && props.length === 1) {
                var $cell = $line.find(line.amount > 0 ? '.cell_right' : '.cell_left');
                var text;
                if (line.partial_reconcile) {
                    text = _t("Undo the partial reconciliation.");
                    $cell.text(state.st_line.amount_str);
                } else {
                    text = _t("This move's amount is higher than the transaction's amount. Click to register a partial payment and keep the payment balance open.");
                }

                $('<span class="do_partial_reconcile_'+(!line.partial_reconcile)+' line_info_button fa fa-exclamation-triangle"/>')
                    .prependTo($cell)
                    .attr("data-content", text);
            }
            $props.append($line);
        });

        // mv_lines
        var $mv_lines = this.$('.match table tbody').empty();
        _.each(state.mv_lines.slice(0,5), function (line) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }
            $mv_lines.append($line);
        });
        this.$('.match .fa-chevron-right').toggleClass('disabled', state.mv_lines.length <= 5);
        this.$('.match .fa-chevron-left').toggleClass('disabled', !state.offset);
        this.$('.match').css('max-height', !state.mv_lines.length && !state.filter.length ? '0px' : '');

        // balance
        this.$('table tfoot').html(qweb.render("reconciliation.line.balance", {'state': state}));

        // create form
        if (state.createForm) {
            if (!this.fields.account_id) {
                this._renderCreate(state);
            }
            var data = this.model.get(this.handleCreateRecord).data;
            this.model.notifyChanges(this.handleCreateRecord, state.createForm);
            var record = this.model.get(this.handleCreateRecord);
            _.each(this.fields, function (field, fieldName) {
                if (fieldName === "partner_id") return;
                if ((data[fieldName] || state.createForm[fieldName]) && !_.isEqual(state.createForm[fieldName], data[fieldName])) {
                    field.reset(record);
                }
            });
        }
        this.$('.create .add_line').toggle(!!state.balance.amount);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
                domain: [["parent_id", "=", false], "|", ["customer", "=", true], ["supplier", "=", true]],
                options: {
                    no_open: true
                }
            }
        });
    },

    /**
     * create account_id, tax_id, analytic_account_id, label and amount field
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
        }, {
            relation: 'account.journal',
            type: 'many2one',
            name: 'journal_id',
        }, {
            relation: 'account.tax',
            type: 'many2one',
            name: 'tax_id',
        }, {
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'analytic_account_id',
        }, {
            type: 'char',
            name: 'label',
        }, {
            type: 'float',
            name: 'amount',
        }], {
            account_id: {string: _t("Account")},
            label: {string: _t("Label")},
            amount: {string: _t("Account")}
        }).then(function (recordID) {
            self.handleCreateRecord = recordID;
            var record = self.model.get(self.handleCreateRecord);

            self.fields.account_id = new relational_fields.FieldMany2One(self,
                'account_id', record, {mode: 'edit'});

            self.fields.journal_id = new relational_fields.FieldMany2One(self,
                'journal_id', record, {mode: 'edit'});

            self.fields.tax_id = new relational_fields.FieldMany2One(self,
                'tax_id', record, {mode: 'edit'});

            self.fields.analytic_account_id = new relational_fields.FieldMany2One(self,
                'analytic_account_id', record, {mode: 'edit'});

            self.fields.label = new basic_fields.FieldChar(self,
                'label', record, {mode: 'edit'});

            self.fields.amount = new basic_fields.FieldFloat(self,
                'amount', record, {mode: 'edit'});

            var $create = $(qweb.render("reconciliation.line.create", {'state': state}));
            self.fields.account_id.appendTo($create.find('.create_account_id .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.account_id));
            self.fields.journal_id.appendTo($create.find('.create_journal_id .o_td_field'));
            self.fields.tax_id.appendTo($create.find('.create_tax_id .o_td_field'));
            self.fields.analytic_account_id.appendTo($create.find('.create_analytic_account_id .o_td_field'));
            self.fields.label.appendTo($create.find('.create_label .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.label));
            self.fields.amount.appendTo($create.find('.create_amount .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.amount));
            self.$('.create').append($create);

            function addRequiredStyle(widget) {
                widget.$el.addClass('o_form_required');
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
    _onShowPanel: function () {
        var mode = (this.$el.data('mode') === 'inactive' || this.$el.data('mode') === 'match') ? 'create' : 'match';
        this.trigger_up('change_mode', {'data': mode});
    },
    /**
     * @private
     */
    _onFilterChange: function () {
        this.trigger_up('change_filter', {'data': _.str.strip($(event.target).val())});
    },
    /**
     * @private
     */
    _onPrevious: function () {
        this.trigger_up('change_offset', {'data': -5});
    },
    /**
     * @private
     */
    _onNext: function () {
        this.trigger_up('change_offset', {'data': 5});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onSelectMoveLine: function (event) {
        var mv_line_id = $(event.target).closest('.mv_line').data('line-id');
        this.trigger_up('add_proposition', {'data': mv_line_id});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onSelectProposition: function (event) {
        var mv_line_id = $(event.target).closest('.mv_line').data('line-id');
        this.trigger_up('remove_proposition', {'data': mv_line_id});
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
            this.do_warn(_("Some fields are undefined"), invalid.join(', '));
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
        popover && popover.destroy();
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
                    self.fields.partner_id.$el.prependTo(self.$('.accounting_view thead td:eq(1) span:first'));
                } else {
                    self.fields.partner_id.destroy();
                    self.fields.title_account_id.appendTo(self.$('.accounting_view thead td:eq(1) span:first'));
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
    },

});


return {
    StatementRenderer: StatementRenderer,
    ManualRenderer: ManualRenderer,
    LineRenderer: LineRenderer,
    ManualLineRenderer: ManualLineRenderer,
};
});
