odoo.define('web.AbstractWebClient', function (require) {
"use strict";

/**
 * AbstractWebClient
 *
 * This class defines a simple, basic web client.  It is mostly functional.
 * The WebClient is in some way the most important class for the web framework:
 * - this is the class that instantiate everything else,
 * - it is the top of the component tree,
 * - it coordinates many events bubbling up
 */

var ActionManager = require('web.ActionManager');
var concurrency = require('web.concurrency');
var core = require('web.core');
var config = require('web.config');
var WarningDialog = require('web.CrashManager').WarningDialog;
var data_manager = require('web.data_manager');
var dom = require('web.dom');
var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
var Loading = require('web.Loading');
var RainbowMan = require('web.RainbowMan');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

const env = require('web.env');

var _t = core._t;

var AbstractWebClient = Widget.extend(KeyboardNavigationMixin, {
    dependencies: ['notification'],
    events: _.extend({}, KeyboardNavigationMixin.events),
    custom_events: {
        call_service: '_onCallService',
        clear_uncommitted_changes: function (e) {
            this.clear_uncommitted_changes().then(e.data.callback);
        },
        toggle_fullscreen: function (event) {
            this.toggle_fullscreen(event.data.fullscreen);
        },
        current_action_updated: function (ev) {
            this.current_action_updated(ev.data.action, ev.data.controller);
        },
        // GENERIC SERVICES
        // the next events are dedicated to generic services required by
        // downstream widgets.  Mainly side effects, such as rpcs, notifications
        // or cache.
        warning: '_onDisplayWarning',
        load_action: '_onLoadAction',
        load_views: function (event) {
            var params = {
                model: event.data.modelName,
                context: event.data.context,
                views_descr: event.data.views,
            };
            return data_manager
                .load_views(params, event.data.options || {})
                .then(event.data.on_success);
        },
        load_filters: function (event) {
            return data_manager
                .load_filters(event.data)
                .then(event.data.on_success);
        },
        create_filter: '_onCreateFilter',
        delete_filter: '_onDeleteFilter',
        push_state: '_onPushState',
        show_effect: '_onShowEffect',
        // session
        get_session: function (event) {
            if (event.data.callback) {
                event.data.callback(session);
            }
        },
        do_action: function (event) {
            const actionProm = this.do_action(event.data.action, event.data.options || {});
            this.menu_dp.add(actionProm).then(function (result) {
                if (event.data.on_success) {
                    event.data.on_success(result);
                }
            }).guardedCatch(function (result) {
                if (event.data.on_fail) {
                    event.data.on_fail(result);
                }
            });
        },
        getScrollPosition: '_onGetScrollPosition',
        scrollTo: '_onScrollTo',
        set_title_part: '_onSetTitlePart',
        webclient_started: '_onWebClientStarted',
    },
    init: function (parent) {
        // a flag to determine that odoo is fully loaded
        odoo.isReady = false;
        this.client_options = {};
        this._super(parent);
        KeyboardNavigationMixin.init.call(this);
        this.origin = undefined;
        this._current_state = null;
        this.menu_dp = new concurrency.DropPrevious();
        this.action_mutex = new concurrency.Mutex();
        this.set('title_part', {"zopenerp": "Odoo"});
        this.env = env;
        this.env.bus.on('set_title_part', this, this._onSetTitlePart);
    },
    /**
     * @override
     */
    start: function () {
        KeyboardNavigationMixin.start.call(this);
        var self = this;

        // we add the o_touch_device css class to allow CSS to target touch
        // devices.  This is only for styling purpose, if you need javascript
        // specific behaviour for touch device, just use the config object
        // exported by web.config
        this.$el.toggleClass('o_touch_device', config.device.touch);
        this.on("change:title_part", this, this._title_changed);
        this._title_changed();

        var state = $.bbq.getState();
        // If not set on the url, retrieve cids from the local storage
        // of from the default company on the user
        var current_company_id = session.user_companies.current_company[0]
        if (!state.cids) {
            state.cids = utils.get_cookie('cids') !== null ? utils.get_cookie('cids') : String(current_company_id);
        }
        // If a key appears several times in the hash, it is available in the
        // bbq state as an array containing all occurrences of that key
        const cids = Array.isArray(state.cids) ? state.cids[0] : state.cids;
        let stateCompanyIDS = cids.split(',').map(cid => parseInt(cid, 10));
        var userCompanyIDS = _.map(session.user_companies.allowed_companies, function(company) {return company[0]});
        // Check that the user has access to all the companies
        if (!_.isEmpty(_.difference(stateCompanyIDS, userCompanyIDS))) {
            state.cids = String(current_company_id);
            stateCompanyIDS = [current_company_id]
        }
        // Update the user context with this configuration
        session.user_context.allowed_company_ids = stateCompanyIDS;
        $.bbq.pushState(state);
        // Update favicon
        $("link[type='image/x-icon']").attr('href', '/web/image/res.company/' + String(stateCompanyIDS[0]) + '/favicon/')

        return session.is_bound
            .then(function () {
                self.$el.toggleClass('o_rtl', _t.database.parameters.direction === "rtl");
                self.bind_events();
                return Promise.all([
                    self.set_action_manager(),
                    self.set_loading()
                ]);
            }).then(function () {
                if (session.session_is_valid()) {
                    return self.show_application();
                } else {
                    // database manager needs the webclient to keep going even
                    // though it has no valid session
                    return Promise.resolve();
                }
            });
    },
    /**
     * @override
     */
    destroy: function () {
        KeyboardNavigationMixin.destroy.call(this);
        return this._super(...arguments);
    },
    bind_events: function () {
        var self = this;
        $('.oe_systray').show();
        this.$el.on('mouseenter', '.oe_systray > div:not([data-toggle=tooltip])', function () {
            $(this).attr('data-toggle', 'tooltip').tooltip().trigger('mouseenter');
        });
        // TODO: this handler seems useless since 11.0, should be removed
        this.$el.on('click', '.oe_dropdown_toggle', function (ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var doc_width = $(document).width();
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.length >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
            var state = $menu.is('.oe_opened');
            setTimeout(function () {
                // Do not alter propagation
                $toggle.add($menu).toggleClass('oe_opened', !state);
                if (!state) {
                    // Move $menu if outside window's edge
                    var offset = $menu.offset();
                    var menu_width = $menu.width();
                    var x = doc_width - offset.left - menu_width - 2;
                    if (x < 0) {
                        $menu.offset({ left: offset.left + x }).width(menu_width);
                    }
                }
            }, 0);
        });
        core.bus.on('click', this, function (ev) {
            $('.tooltip').remove();
            if (!$(ev.target).is('input[type=file]')) {
                $(this.el.getElementsByClassName('oe_dropdown_menu oe_opened')).removeClass('oe_opened');
                $(this.el.getElementsByClassName('oe_dropdown_toggle oe_opened')).removeClass('oe_opened');
            }
        });
        core.bus.on('connection_lost', this, this._onConnectionLost);
        core.bus.on('connection_restored', this, this._onConnectionRestored);
    },
    set_action_manager: function () {
        var self = this;
        this.action_manager = new ActionManager(this, session.user_context);
        this.env.bus.on('do-action', this, payload => {
            this.do_action(payload.action, payload.options || {})
                .then(payload.on_success || (() => {}))
                .guardedCatch(payload.on_fail || (() => {}));
        });
        var fragment = document.createDocumentFragment();
        return this.action_manager.appendTo(fragment).then(function () {
            dom.append(self.$el, fragment, {
                in_DOM: true,
                callbacks: [{widget: self.action_manager}],
            });
        });
    },
    set_loading: function () {
        this.loading = new Loading(this);
        return this.loading.appendTo(this.$el);
    },
    show_application: function () {
    },
    clear_uncommitted_changes: function () {
        return this.action_manager.clearUncommittedChanges();
    },
    destroy_content: function () {
        _.each(_.clone(this.getChildren()), function (el) {
            el.destroy();
        });
        this.$el.children().remove();
    },
    // --------------------------------------------------------------
    // Window title handling
    // --------------------------------------------------------------
    /**
     * Sets the first part of the title of the window, dedicated to the current action.
    */
    set_title: function (title) {
        this.set_title_part("action", title);
    },
    /**
     * Sets an arbitrary part of the title of the window. Title parts are
     * identified by strings. Each time a title part is changed, all parts
     * are gathered, ordered by alphabetical order and displayed in the title
     * of the window separated by ``-``.
     *
     * @private
     * @param {string} part
     * @param {string} title
     */
    set_title_part: function (part, title) {
        var tmp = _.clone(this.get("title_part"));
        tmp[part] = title;
        this.set("title_part", tmp);
    },
    _title_changed: function () {
        var parts = _.sortBy(_.keys(this.get("title_part")), function (x) { return x; });
        var tmp = "";
        _.each(parts, function (part) {
            var str = this.get("title_part")[part];
            if (str) {
                tmp = tmp ? tmp + " - " + str : str;
            }
        }, this);
        document.title = tmp;
    },
    // --------------------------------------------------------------
    // do_*
    // --------------------------------------------------------------
    /**
     * When do_action is performed on the WebClient, forward it to the main ActionManager
     * This allows to widgets that are not inside the ActionManager to perform do_action
     */
    do_action: function () {
        return this.action_manager.doAction.apply(this.action_manager, arguments);
    },
    do_reload: function () {
        var self = this;
        return session.session_reload().then(function () {
            session.load_modules(true).then(
                self.menu.proxy('do_reload'));
        });
    },
    do_push_state: function (state) {
        if (!state.menu_id && this.menu) { // this.menu doesn't exist in the POS
            state.menu_id = this.menu.getCurrentPrimaryMenu();
        }
        if ('title' in state) {
            this.set_title(state.title);
            delete state.title;
        }
        var url = '#' + $.param(state);
        this._current_state = $.deparam($.param(state), false); // stringify all values
        $.bbq.pushState(url);
        this.trigger('state_pushed', state);
    },
    // --------------------------------------------------------------
    // Connection notifications
    // --------------------------------------------------------------
    /**
     * Handler to be overridden, called each time the UI is updated by the
     * ActionManager.
     *
     * @param {Object} action the action of the currently displayed controller
     * @param {Object} controller the currently displayed controller
     */
    current_action_updated: function (action, controller) {
    },
    //--------------------------------------------------------------
    // Misc.
    //--------------------------------------------------------------
    toggle_fullscreen: function (fullscreen) {
        this.$el.toggleClass('o_fullscreen', fullscreen);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the left and top scroll positions of the main scrolling area
     * (i.e. the '.o_content' div in desktop).
     *
     * @returns {Object} with keys left and top
     */
    getScrollPosition: function () {
        var scrollingEl = this.action_manager.el.getElementsByClassName('o_content')[0];
        return {
            left: scrollingEl ? scrollingEl.scrollLeft : 0,
            top: scrollingEl ? scrollingEl.scrollTop : 0,
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Calls the requested service from the env.
     *
     * For the ajax service, the arguments are extended with the target so that
     * it can call back the caller.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onCallService: function (ev) {
        const payload = ev.data;
        let args = payload.args || [];
        if (payload.service === 'ajax' && payload.method === 'rpc') {
            // ajax service uses an extra 'target' argument for rpc
            args = args.concat(ev.target);
        }
        const service = this.env.services[payload.service];
        const result = service[payload.method].apply(service, args);
        payload.callback(result);
    },
    /**
     * Whenever the connection is lost, we need to notify the user.
     *
     * @private
     */
    _onConnectionLost: function () {
        this.connectionNotificationID = this.displayNotification({
            message: _t('Connection lost. Trying to reconnect...'),
            sticky: true
        });
    },
    /**
     * Whenever the connection is restored, we need to notify the user.
     *
     * @private
     */
    _onConnectionRestored: function () {
        if (this.connectionNotificationID) {
            this.call('notification', 'close', this.connectionNotificationID);
            this.displayNotification({
                type: 'info',
                message: _t('Connection restored. You are back online.'),
                sticky: false
            });
            this.connectionNotificationID = false;
        }
    },
    /**
     * @private
     * @param {OdooEvent} e
     * @param {Object} e.data.filter the filter description
     * @param {function} e.data.on_success called when the RPC succeeds with its
     *   returned value as argument
     */
    _onCreateFilter: function (e) {
        data_manager
            .create_filter(e.data.filter)
            .then(e.data.on_success);
    },
    /**
     * @private
     * @param {OdooEvent} e
     * @param {Object} e.data.filter the filter description
     * @param {function} e.data.on_success called when the RPC succeeds with its
     *   returned value as argument
     */
    _onDeleteFilter: function (e) {
        data_manager
            .delete_filter(e.data.filterId)
            .then(e.data.on_success);
    },
    /**
     * Displays a warning in a dialog or with the notification service
     *
     * @private
     * @param {OdooEvent} e
     * @param {string} e.data.message the warning's message
     * @param {string} e.data.title the warning's title
     * @param {string} [e.data.type] 'dialog' to display in a dialog
     * @param {boolean} [e.data.sticky] whether or not the warning should be
     *   sticky (if displayed with the Notification)
     */
    _onDisplayWarning: function (e) {
        var data = e.data;
        if (data.type === 'dialog') {
            new WarningDialog(this, {
                title: data.title,
            }, data).open();
        } else {
            data.type = 'warning';
            this.call('notification', 'notify', data);
        }
    },
    /**
     * Provides to the caller the current scroll position (left and top) of the
     * main scrolling area of the webclient.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} ev.data.callback
     */
    _onGetScrollPosition: function (ev) {
        ev.data.callback(this.getScrollPosition());
    },
    /**
     * Loads an action from the database given its ID.
     *
     * @private
     * @param {OdooEvent} event
     * @param {integer} event.data.actionID
     * @param {Object} event.data.context
     * @param {function} event.data.on_success
     */
    _onLoadAction: function (event) {
        data_manager
            .load_action(event.data.actionID, event.data.context)
            .then(event.data.on_success);
    },
    /**
     * @private
     * @param {OdooEvent} e
     */
    _onPushState: function (e) {
        this.do_push_state(_.extend(e.data.state, {'cids': $.bbq.getState().cids}));
    },
    /**
     * Scrolls either to a given offset or to a target element (given a selector).
     * It must be called with: trigger_up('scrollTo', options).
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer} [ev.data.top] the number of pixels to scroll from top
     * @param {integer} [ev.data.left] the number of pixels to scroll from left
     * @param {string} [ev.data.selector] the selector of the target element to
     *   scroll to
     */
    _onScrollTo: function (ev) {
        var scrollingEl = this.action_manager.el.getElementsByClassName('o_content')[0];
        if (!scrollingEl) {
            return;
        }
        var offset = {top: ev.data.top, left: ev.data.left || 0};
        if (ev.data.selector) {
            offset = dom.getPosition(document.querySelector(ev.data.selector));
            // Substract the position of the scrolling element
            offset.top -= dom.getPosition(scrollingEl).top;
        }

        scrollingEl.scrollTop = offset.top;
        scrollingEl.scrollLeft = offset.left;
    },
    /**
     * @private
     * @param {Object} payload
     * @param {string} payload.part
     * @param {string} [payload.title]
     */
    _onSetTitlePart: function (payload) {
        var part = payload.part;
        var title = payload.title;
        this.set_title_part(part, title);
    },
    /**
     * Displays a visual effect (for example, a rainbowman0
     *
     * @private
     * @param {OdooEvent} e
     * @param {Object} [e.data] - key-value options to decide rainbowman
     *   behavior / appearance
     */
    _onShowEffect: function (e) {
        var data = e.data || {};
        var type = data.type || 'rainbow_man';
        if (type === 'rainbow_man') {
            if (session.show_effect) {
                new RainbowMan(data).appendTo(this.$el);
            } else {
                // For instance keep title blank, as we don't have title in data
                this.call('notification', 'notify', {
                    title: "",
                    message: data.message,
                    sticky: false
                });
            }
        } else {
            throw new Error('Unknown effect type: ' + type);
        }
    },
    /**
     * Reacts to the end of the loading of the WebClient as a whole
     * It allows for signalling to the rest of the ecosystem that the interface is usable
     *
     * @private
     */
    _onWebClientStarted: function() {
        if (!this.isStarted) {
            // Listen to 'scroll' event and propagate it on main bus
            this.action_manager.$el.on('scroll', core.bus.trigger.bind(core.bus, 'scroll'));
            odoo.isReady = true;
            core.bus.trigger('web_client_ready');
            if (session.uid === 1) {
                this.$el.addClass('o_is_superuser');
            }
            this.isStarted = true;
        }
    }
});

return AbstractWebClient;

});
