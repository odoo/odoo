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
var crash_manager = require('web.crash_manager');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var Loading = require('web.Loading');
var mixins = require('web.mixins');
var NotificationManager = require('web.notification').NotificationManager;
var RainbowMan = require('web.rainbow_man');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;
var qweb = core.qweb;

var AbstractWebClient = Widget.extend(mixins.ServiceProvider, {
    custom_events: {
        clear_uncommitted_changes: function (e) {
            this.clear_uncommitted_changes().then(e.data.callback);
        },
        toggle_fullscreen: function (event) {
            this.toggle_fullscreen(event.data.fullscreen);
        },
        current_action_updated: function (e) {
            this.current_action_updated(e.data.action);
        },
        // GENERIC SERVICES
        // the next events are dedicated to generic services required by
        // downstream widgets.  Mainly side effects, such as rpcs, notifications
        // or cache.

        // notifications, warnings and effects
        notification: function (e) {
            if(this.notification_manager) {
                this.notification_manager.notify(e.data.title, e.data.message, e.data.sticky);
            }
        },
        warning: '_onDisplayWarning',
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
                .load_filters(event.data.dataset, event.data.action_id)
                .then(event.data.on_success);
        },
        show_effect: '_onShowEffect',
        // session
        get_session: function (event) {
            if (event.data.callback) {
                event.data.callback(session);
            }
        },
        do_action: function (event) {
            this.do_action(event.data.action, event.data.options || {}).then(function (result) {
                if (event.data.on_success) {
                    event.data.on_success(result);
                }
            }).fail(function (result) {
                if (event.data.on_fail) {
                    event.data.on_fail(result);
                }
            });
        },
    },
    init: function (parent) {
        this.client_options = {};
        mixins.ServiceProvider.init.call(this);
        this._super(parent);
        this.origin = undefined;
        this._current_state = null;
        this.menu_dm = new concurrency.DropMisordered();
        this.action_mutex = new concurrency.Mutex();
        this.set('title_part', {"zopenerp": "Odoo"});
    },
    start: function () {
        var self = this;

        // we add the o_touch_device css class to allow CSS to target touch
        // devices.  This is only for styling purpose, if you need javascript
        // specific behaviour for touch device, just use the config object
        // exported by web.config
        this.$el.toggleClass('o_touch_device', config.device.touch);
        this.on("change:title_part", this, this._title_changed);
        this._title_changed();

        return session.is_bound
            .then(function () {
                self.bind_events();
                return $.when(
                    self.set_action_manager(),
                    self.set_notification_manager(),
                    self.set_loading()
                );
            }).then(function () {
                if (session.session_is_valid()) {
                    return self.show_application();
                } else {
                    // database manager needs the webclient to keep going even
                    // though it has no valid session
                    return $.when();
                }
            }).then(function () {
                // Listen to 'scroll' event and propagate it on main bus
                self.action_manager.$el.on('scroll', core.bus.trigger.bind(core.bus, 'scroll'));
                core.bus.trigger('web_client_ready');
            });
    },
    bind_events: function () {
        var self = this;
        $('.oe_systray').show();
        this.$el.on('mouseenter', '.oe_systray > div:not([data-toggle=tooltip])', function () {
            $(this).attr('data-toggle', 'tooltip').tooltip().trigger('mouseenter');
        });
        this.$el.on('click', '.oe_dropdown_toggle', function (ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var doc_width = $(document).width();
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.size() >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
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
                self.$('.oe_dropdown_menu.oe_opened, .oe_dropdown_toggle.oe_opened').removeClass('oe_opened');
            }
        });
        core.bus.on('connection_lost', this, this.on_connection_lost);
        core.bus.on('connection_restored', this, this.on_connection_restored);

        // crash manager integration
        session.on('error', crash_manager, crash_manager.rpc_error);
        window.onerror = function (message, file, line, col, error) {
            // Scripts injected in DOM (eg: google API's js files) won't return a clean error on window.onerror.
            // The browser will just give you a 'Script error.' as message and nothing else for security issue.
            // To enable onerror to work properly with CORS file, you should:
            //   1. add crossorigin="anonymous" to your <script> tag loading the file
            //   2. enabling 'Access-Control-Allow-Origin' on the server serving the file.
            // Since in some case it wont be possible to to this, this handle should have the possibility to be
            // handled by the script manipulating the injected file. For this, you will use window.onOriginError
            // If it is not handled, we should display something clearer than the common crash_manager error dialog
            // since it won't show anything except "Script error."
            // This link will probably explain it better: https://blog.sentry.io/2016/05/17/what-is-script-error.html
            if (message === "Script error." && !file && !line && !col && !error) {
                if (window.onOriginError) {
                    window.onOriginError();
                    delete window.onOriginError;
                } else {
                    crash_manager.show_error({
                        type: _t("Odoo Client Error"),
                        message: _t("Unknown CORS error"),
                        data: {debug: _t("An unknown CORS error occured. The error probably originates from a JavaScript file served from a different origin.")},
                    });
                }
            } else {
                var traceback = error ? error.stack : '';
                crash_manager.show_error({
                    type: _t("Odoo Client Error"),
                    message: message,
                    data: {debug: file + ':' + line + "\n" + _t('Traceback:') + "\n" + traceback},
                });
            }
        };
    },
    set_action_manager: function () {
        this.action_manager = new ActionManager(this, {webclient: this});
        return this.action_manager.appendTo(this.$('.o_main_content'));
    },
    set_notification_manager: function () {
        this.notification_manager = new NotificationManager(this);
        return this.notification_manager.appendTo(this.$el);
    },
    set_loading: function () {
        this.loading = new Loading(this);
        return this.loading.appendTo(this.$el);
    },
    show_application: function () {
    },
    clear_uncommitted_changes: function () {
        var def = $.Deferred().resolve();
        core.bus.trigger('clear_uncommitted_changes', function chain_callbacks(callback) {
            def = def.then(callback);
        });
        return def;
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
        return this.action_manager.do_action.apply(this, arguments);
    },
    do_reload: function () {
        var self = this;
        return session.session_reload().then(function () {
            session.load_modules(true).then(
                self.menu.proxy('do_reload'));
        });
    },
    do_push_state: function (state) {
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
    on_connection_lost: function () {
        this.connection_notification = this.notification_manager.notify(
            _t('Connection lost'),
            _t('Trying to reconnect...'),
            true
        );
    },
    on_connection_restored: function () {
        if (this.connection_notification) {
            this.connection_notification.destroy();
            this.notification_manager.notify(
                _t('Connection restored'),
                _t('You are back online'),
                false
            );
            this.connection_notification = false;
        }
    },
    // Handler to be overwritten
    current_action_updated: function () {
    },
    // --------------------------------------------------------------
    // Scrolltop handling
    // --------------------------------------------------------------
    getScrollTop: function () {
    },
    //--------------------------------------------------------------
    // Misc.
    //--------------------------------------------------------------
    toggle_fullscreen: function (fullscreen) {
        this.$el.toggleClass('o_fullscreen', fullscreen);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Displays a warning in a dialog of with the NotificationManager
     *
     * @private
     * @param {OdooEvent} e
     * @param {string} e.data.message the warning's message
     * @param {string} e.data.title the warning's title
     * @param {string} [e.data.type] 'dialog' to display in a dialog
     * @param {boolean} [e.data.sticky] whether or not the warning should be
     *   sticky (if displayed with the NotificationManager)
     */
    _onDisplayWarning: function (e) {
        var data = e.data;
        if (data.type === 'dialog') {
            new Dialog(this, {
                size: 'medium',
                title: data.title,
                $content: qweb.render("CrashManager.warning", data),
            }).open();
        } else if (this.notification_manager) {
            this.notification_manager.warn(e.data.title, e.data.message, e.data.sticky);
        }
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
            new RainbowMan(data).appendTo(this.$el);
        } else {
            throw new Error('Unknown effect type: ' + type);
        }
    },
});

return AbstractWebClient;

});
