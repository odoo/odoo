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
    xmlDependencies: ['/web/static/src/legacy/xml/debug.xml'],
    events: {
        "click a[data-action]": "perform_callback",
        "click .profiling": "handle_profiling",
        "change .profiling_param": "handle_profiling",
    },
    init: function () {
        this._super.apply(this, arguments);
        this._events = null;
        var debug = odoo.debug;
        this.debug_mode = debug;
        this.debug_mode_help = debug && debug !== '1' ? ' (' + debug + ')' : '';
        this.profile_session = odoo.session_info && odoo.session_info.profile_session || false;
        this.profile_collectors = odoo.session_info && odoo.session_info.profile_collectors;
        if (! Array.isArray(this.profile_collectors)) {
            this.profile_collectors = ['sql', 'traces_async'];  // use default value when not defined in session.
        }
        this.profile_params = odoo.session_info && odoo.session_info.profile_params || {};
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
    /**
     * Manage profiling actions.
     * open_profiling_button should not prevent dropdown from closing
     * other actions should keep dropdown open and interact with backend to enable or disable profiling features.
     * The main switch, 'enable_profiling' is a special case since it will create or remove a profile session
     */
    handle_profiling: async function (evt) {
        const $target = $(evt.target);
        const target = $target[0];
        if (target.id === 'open_profiling_button') {
            this.do_action('base.action_menu_ir_profile');
            return;
        }
        evt.stopPropagation(); // prevent dropdown from closing
        const kwargs = {
            params: {}
        };
        if (target.nodeName == "LABEL") {
            return
        }
        kwargs.profile = $('#enable_profiling')[0].checked;
        kwargs.collectors = $('input.profile_switch').toArray().filter(i => i.checked).map(i => i.id.replace(/^profile_/, ''));
        $('.profile_param').toArray().forEach(i => kwargs.params[i.id.replace(/^profile_/, '')] = i.value);

        try {
            const resp = await this._rpc({
                model: 'ir.profile',
                method: 'set_profiling',
                kwargs: kwargs,
            });
            this.profile_session = resp.session;
            this.profile_collectors = resp.collectors;
            this.profile_params = resp.params;
        } catch (e) {
            this.profite_session = false;
        }
        this.update_profiling_state();
    },
    /**
     * Update the profiling dropdown menu state after any change to synchronyze server session and client
     * This is mainly usefull to avoid desync in case of multiple tabs
     */
    update_profiling_state: function () {
        const self = this;
        this.$('#enable_profiling')[0].checked = Boolean(this.profile_session);
        this.$('.profile_switch').each(function () {
            this.checked = (self.profile_collectors.indexOf(this.id.replace(/^profile_/, '')) !== -1);
            const params = self.$('.' + this.id);
            params.toggleClass('d-none', !this.checked);
            params.each(function () {
                const params_input = $(this).find('.profile_param')[0];
                params_input.value = self.profile_params[params_input.id.replace(/^profile_/, '')] || '';
            });
        });
        this.$profiling_items.toggleClass('d-none', !this.profile_session);
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
        this.$profiling_items = this.$(".profiling_items");

        this.update_profiling_state();
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
