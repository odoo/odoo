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

var core = require('web.core');
var framework = require('web.framework');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;

var Loading = Widget.extend({
    template: "Loading",

    init: function(parent) {
        this._super(parent);
        this.count = 0;
        this.blocked_ui = false;
        session.on("request", this, this.request_call);
        session.on("response", this, this.response_call);
        session.on("response_failed", this, this.response_call);
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
        var self = this;
        if (!this.count && increment === 1) {
            // Block UI after 3s
            this.long_running_timer = setTimeout(function () {
                self.blocked_ui = true;
                framework.blockUI();
            }, 3000);
        }

        this.count += increment;
        if (this.count > 0) {
            if (session.debug) {
                this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
            } else {
                this.$el.text(_t("Loading"));
            }
            this.$el.show();
            this.getParent().$el.addClass('oe_wait');
        } else {
            this.count = 0;
            clearTimeout(this.long_running_timer);
            // Don't unblock if blocked by somebody else
            if (self.blocked_ui) {
                this.blocked_ui = false;
                framework.unblockUI();
            }
            this.$el.fadeOut();
            this.getParent().$el.removeClass('oe_wait');
        }
    }
});

return Loading;
});

