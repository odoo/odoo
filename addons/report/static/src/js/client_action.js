odoo.define('report.client_action', function (require) {
'use strict';

var core = require('web.core');
var ControlPanelMixin = require('web.ControlPanelMixin');
var session = require('web.session');
var Widget = require('web.Widget');
var utils = require('report.utils');

var QWeb = core.qweb;


var AUTHORIZED_MESSAGES = [
    'report.editor:save_ok',
    'report.editor:discard_ok',
    'report:do_action',
];

var ReportAction = Widget.extend(ControlPanelMixin, {

    template: 'report.client_action',

    init: function (parent, action, options) {
        this._super.apply(this, arguments);

        options = options || {};

        this.action_manager = parent;
        this.title = options.display_name || options.name;

        this.edit_mode_available = false;
        this.in_edit_mode = false;
        this.report_url = options.report_url;

        // Extra info that will be useful to build a qweb-pdf action.
        this.report_name = options.report_name;
        this.report_file = options.report_file;
        this.data = options.data || {};
        this.context = options.context || {};
    },

    start: function () {
        var self = this;
        this.set('title', this.title);
        this.iframe = this.$('iframe')[0];
        return $.when(this._super.apply(this, arguments), session.is_bound).then(function () {
            var web_base_url = session['web.base.url'];
            var trusted_host = utils.get_host_from_url(web_base_url);
            var trusted_protocol = utils.get_protocol_from_url(web_base_url);
            self.trusted_origin = utils.build_origin(trusted_protocol, trusted_host);

            self.$buttons = $(QWeb.render('report.client_action.ControlButtons', {}));
            self.$buttons.on('click', '.o_report_edit', self.on_click_edit);
            self.$buttons.on('click', '.o_report_print', self.on_click_print);
            self.$buttons.on('click', '.o_report_save', self.on_click_save);
            self.$buttons.on('click', '.o_report_discard', self.on_click_discard);

            self._update_control_panel();

            // Load the report in the iframe. Note that we use a relative URL.
            self.iframe.src = self.report_url;

            // Once the iframe is loaded, check if we can edit the report.
            self.iframe.onload = function () {
                self._on_iframe_loaded();
            };
        });
    },

    do_show: function () {
        this._update_control_panel();
        return this._super.apply(this, arguments);
    },

    on_attach_callback: function () {
        // Register now the postMessage event handler. We only want to listen to ~trusted
        // messages and we can only filter them by their origin, so we chose to ignore the
        // messages that do not come from `web.base.url`.
        $(window).on('message', this, this.on_message_received);
    },

    on_detach_callback: function () {
        $(window).off('message', this.on_message_received);
    },

    _on_iframe_loaded: function () {
        var editable = $(this.iframe).contents().find('html').data('editable');
        if (editable === 1) {
            this.edit_mode_available = true;
            this._update_control_panel();
        }
    },

    _update_control_panel: function () {
        this.update_control_panel({
            breadcrumbs: this.action_manager.get_breadcrumbs(),
            cp_content: {
                $buttons: this.$buttons,
            },
        });
        this._update_control_panel_buttons();
    },

    /**
     * Helper allowing to toggle groups of buttons in the control panel
     * according to the `this.in_edit_mode` flag.
     */
    _update_control_panel_buttons: function () {
        this.$buttons.filter('div.o_report_edit_mode').toggle(this.in_edit_mode);
        this.$buttons.filter('div.o_report_no_edit_mode').toggle(! this.in_edit_mode);
        this.$buttons.filter('div.o_edit_mode_available').toggle(core.debug && this.edit_mode_available && ! this.in_edit_mode);
    },

    /**
     * Event handler of the message post. We only handle them if they're from
     * `web.base.url` host and protocol and if they're part of `AUTHORIZED_MESSAGES`.
     */
    on_message_received: function (ev) {
        // Check the origin of the received message.
        var message_origin = utils.build_origin(ev.originalEvent.source.location.protocol, ev.originalEvent.source.location.host);
        if (message_origin === this.trusted_origin) {

            // Check the syntax of the received message.
            var message = ev.originalEvent.data;
            if (_.isObject(message)) {
                message = message.message;
            }
            if (! _.isString(message) || (_.isString(message) && ! _.contains(AUTHORIZED_MESSAGES, message))) {
                return;
            }

            switch(message) {
                case 'report.editor:save_ok':
                    // Reload the iframe in order to disable the editor.
                    this.iframe.src = this.report_url;
                    this.in_edit_mode = false;
                    this._update_control_panel_buttons();
                    break;
                case 'report.editor:discard_ok':
                    // Reload the iframe in order to disable the editor.
                    this.iframe.src = this.report_url;
                    this.in_edit_mode = false;
                    this._update_control_panel_buttons();
                    break;
                case 'report:do_action':
                    return this.do_action(ev.originalEvent.data.action);
                default:
            }
        }
    },

    /**
     * Helper allowing to send a message to the `this.el` iframe's window and
     * seting the `targetOrigin` as `this.trusted_origin` (which is the 
     * `web.base.url` ir.config_parameter key) - in other word, only when using
     * this method we only send the message to a trusted domain.
     */
    _post_message: function (message) {
        this.iframe.contentWindow.postMessage(message, this.trusted_origin);
    },

    on_click_edit: function () {
        // We reload the iframe with a special query string to enable the editor.
        if (this.report_url.indexOf('?') === -1) {
            this.iframe.src = this.report_url + '?enable_editor=1';
        } else {
            this.iframe.src = this.report_url + '&enable_editor=1';
        }
        this.in_edit_mode = true;
        this._update_control_panel_buttons();
    },

    on_click_discard: function () {
        this._post_message('report.editor:ask_discard');
    },

    on_click_save: function () {
        this._post_message('report.editor:ask_save');
    },

    on_click_print: function () {
        var action = {
            'type': 'ir.actions.report.xml',
            'report_type': 'qweb-pdf',
            'report_name': this.report_name,
            'report_file': this.report_file,
            'data': this.data,
            'context': this.context,
            'display_name': this.title,
        };
        return this.do_action(action);
    },

});

core.action_registry.add('report.client_action', ReportAction);

return ReportAction;

});
