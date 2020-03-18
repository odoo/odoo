odoo.define('report.client_action', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var utils = require('report.utils');

var QWeb = core.qweb;


var AUTHORIZED_MESSAGES = [
    'report:do_action',
];

var ReportAction = AbstractAction.extend({
    hasControlPanel: true,
    contentTemplate: 'report.client_action',

    init: function (parent, action, options) {
        this._super.apply(this, arguments);

        options = options || {};

        this.action_manager = parent;
        this._title = options.display_name || options.name;

        this.report_url = options.report_url;

        // Extra info that will be useful to build a qweb-pdf action.
        this.report_name = options.report_name;
        this.report_file = options.report_file;
        this.data = options.data || {};
        this.context = options.context || {};
    },

    start: function () {
        var self = this;
        this.iframe = this.$('iframe')[0];
        this.$buttons = $(QWeb.render('report.client_action.ControlButtons', {}));
        this.$buttons.on('click', '.o_report_print', this.on_click_print);
        this.controlPanelProps.cp_content = {
            $buttons: this.$buttons,
        };
        return Promise.all([this._super.apply(this, arguments), session.is_bound]).then(async function () {
            var web_base_url = session['web.base.url'];
            var trusted_host = utils.get_host_from_url(web_base_url);
            var trusted_protocol = utils.get_protocol_from_url(web_base_url);
            self.trusted_origin = utils.build_origin(trusted_protocol, trusted_host);

            // Load the report in the iframe. Note that we use a relative URL.
            self.iframe.src = self.report_url;
        });
    },

    do_show: function () {
        this.updateControlPanel({
            cp_content: {
                $buttons: this.$buttons,
            },
        });
        return this._super.apply(this, arguments);
    },

    on_attach_callback: function () {
        // Register now the postMessage event handler. We only want to listen to ~trusted
        // messages and we can only filter them by their origin, so we chose to ignore the
        // messages that do not come from `web.base.url`.
        $(window).on('message', this, this.on_message_received);
        this._super();
    },

    on_detach_callback: function () {
        $(window).off('message', this.on_message_received);
        this._super();
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

    on_click_print: function () {
        var action = {
            'type': 'ir.actions.report',
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
