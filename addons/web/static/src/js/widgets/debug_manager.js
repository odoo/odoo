odoo.define('web.DebugManager', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.Model');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var utils = require('web.utils');
var ViewManager = require('web.ViewManager');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

if (core.debug) {
    var DebugManager = Widget.extend({
        template: "WebClient.DebugManager",
        events: {
            "click .oe_debug_button": "render_dropdown",
            "click .js_debug_dropdown li": "on_debug_click",
        },
        start: function() {
            this._super();
            this.$dropdown = this.$(".js_debug_dropdown");
        },
        /**
         * Updates its attributes according to the inner_widget of the ActionManager
         */
        _update: function() {
            this.view_manager = odoo.__DEBUG__.services['web.web_client'].action_manager.get_inner_widget();
            if (!this.view_manager instanceof ViewManager) { return; }
            this.dataset = this.view_manager.dataset;
            this.active_view = this.view_manager.active_view;
            if (!this.active_view) { return; }
            this.view = this.active_view.controller;
            return true;
        },
        /**
         * Renders the DebugManager dropdown
         */
        render_dropdown: function() {
            var self = this;

            // Empty the previously rendered dropdown
            this.$dropdown.empty();

            // Attempt to retrieve the inner_widget of the ActionManager
            if (!this._update()) {
                // Disable the button when not available
                console.warn("DebugManager is not available");
                return;
            }

            this.session.user_has_group('base.group_system').then(function(is_admin) {
                // Render the dropdown and append it
                var dropdown_content = QWeb.render('WebClient.DebugDropdown', {
                    widget: self,
                    active_view: self.active_view,
                    view: self.view,
                    action: self.view_manager.action,
                    searchview: self.view_manager.searchview,
                    is_admin: is_admin,
                });
                $(dropdown_content).appendTo(self.$dropdown);
            });
        },
        /**
         * Calls the appropriate callback when clicking on a Debug option
         */
        on_debug_click: function (evt) {
            evt.preventDefault();

            var params = $(evt.target).data();
            var callback = params.action;

            if (callback && this[callback]) {
                // Perform the callback corresponding to the option
                this[callback](params, evt);
            } else {
                console.warn("No debug handler for ", callback);
            }
        },
        get_metadata: function() {
            var ds = this.dataset;
            if (!this.view.get_selected_ids().length) {
                console.warn(_t("No metadata available"));
                return
            }
            ds.call('get_metadata', [this.view.get_selected_ids()]).done(function(result) {
                new Dialog(this, {
                    title: _.str.sprintf(_t("Metadata (%s)"), ds.model),
                    size: 'medium',
                    $content: QWeb.render('WebClient.DebugViewLog', {
                        perm : result[0],
                        format : formats.format_value
                    })
                }).open();
            });
        },
        toggle_layout_outline: function() {
            this.view.rendering_engine.toggle_layout_debugging();
        },
        set_defaults: function() {
            this.view.open_defaults_dialog();
        },
        perform_js_tests: function() {
            this.do_action({
                name: _t("JS Tests"),
                target: 'new',
                type : 'ir.actions.act_url',
                url: '/web/tests?mod=*'
            });
        },
        get_view_fields: function() {
            var self = this;
            self.dataset.call('fields_get', [false, {}]).done(function (fields) {
                var $root = $('<dl>');
                _(fields).each(function (attributes, name) {
                    $root.append($('<dt>').append($('<h4>').text(name)));
                    var $attrs = $('<dl>').appendTo($('<dd>').appendTo($root));
                    _(attributes).each(function (def, name) {
                        if (def instanceof Object) {
                            def = JSON.stringify(def);
                        }
                        $attrs
                            .append($('<dt>').text(name))
                            .append($('<dd style="white-space: pre-wrap;">').text(def));
                    });
                });
                new Dialog(self, {
                    title: _.str.sprintf(_t("Model %s fields"), self.dataset.model),
                    $content: $root
                }).open();
            });
        },
        fvg: function() {
            var dialog = new Dialog(this, { title: _t("Fields View Get") }).open();
            $('<pre>').text(utils.json_node_to_xml(this.view.fields_view.arch, true)).appendTo(dialog.$el);
        },
        manage_filters: function() {
            this.do_action({
                res_model: 'ir.filters',
                name: _t('Manage Filters'),
                views: [[false, 'list'], [false, 'form']],
                type: 'ir.actions.act_window',
                context: {
                    search_default_my_filters: true,
                    search_default_model_id: this.dataset.model
                }
            });
        },
        translate: function() {
            new Model("ir.translation")
                .call('get_technical_translations', [this.dataset.model])
                .then(this.do_action);
        },
        edit: function(params, evt) {
            this.do_action({
                res_model : params.model,
                res_id : params.id,
                name: evt.target.text,
                type : 'ir.actions.act_window',
                view_type : 'form',
                view_mode : 'form',
                views : [[false, 'form']],
                target : 'new',
                flags : {
                    action_buttons : true,
                    headless: true,
                }
            });
        },
        edit_workflow: function() {
            return this.do_action({
                res_model : 'workflow',
                name: _t('Edit Workflow'),
                domain : [['osv', '=', this.dataset.model]],
                views: [[false, 'list'], [false, 'form'], [false, 'diagram']],
                type : 'ir.actions.act_window',
                view_type : 'list',
                view_mode : 'list'
            });
        },
        print_workflow: function() {
            if (this.view.get_selected_ids && this.view.get_selected_ids().length == 1) {
                framework.blockUI();
                var action = {
                    context: { active_ids: this.view.get_selected_ids() },
                    report_name: "workflow.instance.graph",
                    datas: {
                        model: this.dataset.model,
                        id: this.view.get_selected_ids()[0],
                        nested: true,
                    }
                };
                this.session.get_file({
                    url: '/web/report',
                    data: {action: JSON.stringify(action)},
                    complete: framework.unblockUI
                });
            } else {
                this.do_warn("Warning", "No record selected.");
            }
        },
        leave_debug: function() {
            window.location.search="?";
        },
    });

    SystrayMenu.Items.push(DebugManager);
    
    return DebugManager;
}

});
