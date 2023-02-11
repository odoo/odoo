odoo.define('stock.stock_report_generic', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var ReportWidget = require('stock.ReportWidget');
var framework = require('web.framework');

var QWeb = core.qweb;

var stock_report_generic = AbstractAction.extend({
    hasControlPanel: true,

    // Stores all the parameters of the action.
    init: function(parent, action) {
        this._super.apply(this, arguments);
        this.actionManager = parent;
        this.given_context = Object.assign({}, session.user_context);
        this.controller_url = action.context.url;
        if (action.context.context) {
            this.given_context = action.context.context;
        }
        this.given_context.active_id = action.context.active_id || action.params.active_id;
        this.given_context.model = action.context.active_model || false;
        this.given_context.ttype = action.context.ttype || false;
        this.given_context.auto_unfold = action.context.auto_unfold || false;
        this.given_context.lot_name = action.context.lot_name || false;
    },
    willStart: function() {
        return Promise.all([this._super.apply(this, arguments), this.get_html()]);
    },
    set_html: function() {
        var self = this;
        var def = Promise.resolve();
        if (!this.report_widget) {
            this.report_widget = new ReportWidget(this, this.given_context);
            def = this.report_widget.appendTo(this.$('.o_content'));
        }
        return def.then(function () {
            self.report_widget.$el.html(self.html);
            self.report_widget.$el.find('.o_report_heading').html('<h1>Traceability Report</h1>');
            if (self.given_context.auto_unfold) {
                _.each(self.$el.find('.fa-caret-right'), function (line) {
                    self.report_widget.autounfold(line, self.given_context.lot_name);
                });
            }
        });
    },
    start: async function() {
        this.controlPanelProps.cp_content = { $buttons: this.$buttons };
        await this._super(...arguments);
        this.set_html();
    },
    // Fetches the html and is previous report.context if any, else create it
    get_html: async function() {
        const { html } = await this._rpc({
            args: [this.given_context],
            method: 'get_html',
            model: 'stock.traceability.report',
        });
        this.html = html;
        this.renderButtons();
    },
    // Updates the control panel and render the elements that have yet to be rendered
    update_cp: function() {
        if (!this.$buttons) {
            this.renderButtons();
        }
        this.controlPanelProps.cp_content = { $buttons: this.$buttons };
        return this.updateControlPanel();
    },
    renderButtons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("stockReports.buttons", {}));
        // pdf output
        this.$buttons.bind('click', function () {
            var $element = $(self.$el[0]).find('.o_stock_reports_table tbody tr');
            var dict = [];

            $element.each(function( index ) {
                var $el = $($element[index]);
                dict.push({
                        'id': $el.data('id'),
                        'model_id': $el.data('model_id'),
                        'model_name': $el.data('model'),
                        'unfoldable': $el.data('unfold'),
                        'level': $el.find('td:first').data('level') || 1
                });
            });
            framework.blockUI();
            var url_data = self.controller_url.replace(':active_id', self.given_context.active_id);
            url_data = url_data.replace(':active_model', self.given_context.model);
            session.get_file({
                url: url_data.replace('output_format', 'pdf'),
                data: {data: JSON.stringify(dict)},
                complete: framework.unblockUI,
                error: (error) => self.call('crash_manager', 'rpc_error', error),
            });
        });
        return this.$buttons;
    },
});

core.action_registry.add("stock_report_generic", stock_report_generic);
return stock_report_generic;
});
