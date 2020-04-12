odoo.define('web.DebugManager', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;

/**
 * DebugManager base + general features (applicable to any context)
 */
var DebugManager = Widget.extend({
    template: "WebClient.DebugManager",
    xmlDependencies: ['/web/static/src/xml/debug.xml'],
    events: {
        "click a[data-action]": "perform_callback",
    },
    init: function () {
        this._super.apply(this, arguments);
        this._events = null;
        var debug = odoo.debug;
        this.debug_mode = debug;
        this.debug_mode_help = debug && debug !== '1' ? ' (' + debug + ')' : '';
    },
    start: function () {
        core.bus.on('rpc:result', this, function (req, resp) {
            this._debug_events(resp.debug);
        });

        this.$dropdown = this.$(".o_debug_dropdown");
        // whether the current user is an administrator
        this._is_admin = session.is_system;
        return Promise.resolve(
            this._super()
        ).then(function () {
            return this.update();
        }.bind(this));
    },
    /**
     * Calls the appropriate callback when clicking on a Debug option
     */
    perform_callback: function (evt) {
        evt.preventDefault();
        var params = $(evt.target).data();
        var callback = params.action;

        if (callback && this[callback]) {
            // Perform the callback corresponding to the option
            this[callback](params, evt);
        } else {
            console.warn("No handler for ", callback);
        }
    },

    _debug_events: function (events) {
        if (!this._events) {
            return;
        }
        if (events && events.length) {
            this._events.push(events);
        }
        this.trigger('update-stats', this._events);
    },

    /**
     * Update the debug manager: reinserts all "universal" controls
     */
    update: function () {
        this.$dropdown
            .empty()
            .append(QWeb.render('WebClient.DebugManager.Global', {
                manager: this,
            }));
        return Promise.resolve();
    },
    split_assets: function () {
        window.location = $.param.querystring(window.location.href, 'debug=assets');
    },
    tests_assets: function () {
        // Enable also 'assets' to see non minimized assets
        window.location = $.param.querystring(window.location.href, 'debug=assets,tests');
    },
    /**
     * Delete assets bundles to force their regeneration
     *
     * @returns {void}
     */
    regenerateAssets: function () {
        var self = this;
        var domain = utils.assetsDomain();
        this._rpc({
            model: 'ir.attachment',
            method: 'search',
            args: [domain],
        }).then(function (ids) {
            self._rpc({
                model: 'ir.attachment',
                method: 'unlink',
                args: [ids],
            }).then(window.location.reload());
        });
    },
    leave_debug_mode: function () {
        var qs = $.deparam.querystring();
        qs.debug = '';
        window.location.search = '?' + $.param(qs);
    },
    /**
     * @private
     * @param {string} model
     * @param {string} operation
     * @returns {Promise<boolean>}
     */
    _checkAccessRight(model, operation) {
        return this._rpc({
            model: model,
            method: 'check_access_rights',
            kwargs: {operation, raise_exception: false},
        })
    },
});

return DebugManager;

});
