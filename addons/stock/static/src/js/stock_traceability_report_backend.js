odoo.define('stock.stock_report_generic', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var ControlPanelMixin = require('web.ControlPanelMixin');
var session = require('web.session');
var ReportWidget = require('stock.ReportWidget');
var framework = require('web.framework');
var crash_manager = require('web.crash_manager');

var QWeb = core.qweb;

var stock_report_generic = Widget.extend(ControlPanelMixin, {
    // Stores all the parameters of the action.
    init: function(parent, action) {
        this.actionManager = parent;
        this.given_context = {};
        this.controller_url = action.context.url;
        if (action.context.context) {
            this.given_context = action.context.context;
        }
        this.given_context.active_id = action.context.active_id || action.params.active_id;
        this.given_context.model = action.context.active_model || false;
        this.given_context.ttype = action.context.ttype || false;
        return this._super.apply(this, arguments);
    },
    willStart: function() {
        return this.get_html();
    },
    set_html: function() {
        var self = this;
        var def = $.when();
        if (!this.report_widget) {
            this.report_widget = new ReportWidget(this, this.given_context);
            def = this.report_widget.appendTo(this.$el);
        }
        def.then(function () {
            self.report_widget.$el.html(self.html);
            if(self.given_context['ttype'] == 'downstream'){
                self.report_widget.$el.find('.o_report_heading').html('<h1>Downstream Traceability</h1>');
            }
        });
    },
    start: function() {
        this.set_html();
        return this._super();
    },
    // Fetches the html and is previous report.context if any, else create it
    get_html: function() {
        var self = this;
        var defs = [];
        return this._rpc({
                model: 'stock.traceability.report',
                method: 'get_html',
                args: [self.given_context],
            })
            .then(function (result) {
                self.html = result.html;
                self.renderButtons();
                defs.push(self.update_cp());
                return $.when.apply($, defs);
            });
    },
    // Updates the control panel and render the elements that have yet to be rendered
    update_cp: function() {
        if (!this.$buttons) {
            this.renderButtons();
        }
        var status = {
            cp_content: {$buttons: this.$buttons},
        };
        return this.update_control_panel(status);
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
            var url_data = self.controller_url.replace('active_id', self.given_context['active_id']);
            session.get_file({
                url: url_data.replace('output_format', 'pdf'),
                data: {data: JSON.stringify(dict)},
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager),
            });
        });
        return this.$buttons;
    },
    do_show: function() {
        this._super();
        this.update_cp();
    },
});

core.action_registry.add("stock_report_generic", stock_report_generic);
return stock_report_generic;
});
