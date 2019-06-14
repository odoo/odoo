odoo.define('web.Loading', function (require) {
"use strict";

/**
 * Loading Indicator
 *
 * When the user performs an action, it is good to give him some feedback that
 * something is currently happening.  The purpose of the Loading Indicator is to
 * display a small rectangle on the bottom right of the screen with just the
 * text 'Loading' and the number of currently running rpcs.
 *
 * After a delay of 3s, if a rpc is still not completed, we also block the UI.
 */

var config = require('web.config');
var core = require('web.core');
var framework = require('web.framework');
var Widget = require('web.Widget');

var _t = core._t;

var Loading = Widget.extend({
    template: "Loading",
    custom_events: {
        "loading.inform": "_onInform",
        "loading.blocked": "_onBlocked",
        "loading.finished": "_onUnblocked",
    },
    _wait_ms: 3000,

    init: function(parent) {
        this._super(parent);
        this.count = 0;
        this.blocked_ui = false;
    },
    start: function() {
        core.bus.on('rpc_request', this, this.request_call);
        core.bus.on("rpc_response", this, this.response_call);
        core.bus.on("rpc_response_failed", this, this.response_call);
    },
    destroy: function() {
        this.on_rpc_event(-this.count);
        this._super();
    },
    request_call: function() {
        this.on_rpc_event(1);
    },
    response_call: function() {
        this.on_rpc_event(-1);
    },
    on_rpc_event : function(increment) {
        if (!this.count && increment === 1) {
            // Block UI after 3s
            this.long_running_timer = setTimeout(
                () => this.trigger_up("loading.blocked"),
                this.waitTimeout(),
            );
        }

        this.count += increment;
        if (this.count > 0) {
            this.trigger_up("loading.inform");
            if (config.isDebug()) {
                this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
            } else {
                this.$el.text(_t("Loading"));
            }
            this.$el.show();
            this.getParent().$el.addClass('oe_wait');
        } else {
            this.count = 0;
            clearTimeout(this.long_running_timer);
            this.trigger_up("loading.finished");
        }
    },

    /**
     * Milliseconds to wait for blocking the UI
     *
     * @returns {Number}
     */
    waitTimeout: function () {
        return this._wait_ms;
    },

    _onInform: function () {
        if (session.debug) {
            this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
        } else {
            this.$el.text(_t("Loading"));
        }
        this.$el.show();
        this.getParent().$el.addClass('oe_wait');
    },

    _onBlocked: function () {
        this.blocked_ui = true;
        framework.blockUI();
    },

    _onUnblocked: function () {
        // Don't unblock if blocked by somebody else
        if (this.blocked_ui) {
            this.blocked_ui = false;
            framework.unblockUI();
        }
        this.$el.fadeOut();
        this.getParent().$el.removeClass('oe_wait');
    },
});

return Loading;
});

