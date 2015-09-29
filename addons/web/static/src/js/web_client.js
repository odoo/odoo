odoo.define('web.WebClient', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var framework = require('web.framework');
var Loading = require('web.Loading');
var Menu = require('web.Menu');
var Model = require('web.DataModel');
var NotificationManager = require('web.notification').NotificationManager;
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var UserMenu = require('web.UserMenu');
var utils = require('web.utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var WebClient = Widget.extend({
    events: {
        'click .oe_logo_edit_admin': 'logo_edit',
        'click .oe_logo img': 'on_logo_click',
    },
    custom_events: {
        'notification': function (e) {
            if(this.notification_manager) {
                this.notification_manager.notify(e.data.title, e.data.message, e.data.sticky);
            }
        },
        'warning': function (e) {
            if(this.notification_manager) {
                this.notification_manager.warn(e.data.title, e.data.message, e.data.sticky);
            }
        },
    },

    init: function(parent, client_options) {
        this.client_options = {};
        this._super(parent);
        this.origin = undefined;
        if (client_options) {
            _.extend(this.client_options, client_options);
        }
        this._current_state = null;
        this.menu_dm = new utils.DropMisordered();
        this.action_mutex = new utils.Mutex();
        this.set('title_part', {"zopenerp": "Odoo"});
    },
    start: function() {
        var self = this;
        this.on("change:title_part", this, this._title_changed);
        this._title_changed();

        core.bus.on('web_client_toggle_bars', this, function () {
            this.toggle_bars.apply(this, arguments);
        });

        document.body.classList.add('o_web_client');
        return session.session_bind(this.origin).then(function() {
            self.bind_events();
            return self.show_common();
        }).then(function() {
            if (session.session_is_valid()) {
                self.show_application();
            }
            if (self.client_options.action) {
                self.action_manager.do_action(self.client_options.action);
                delete(self.client_options.action);
            }
            core.bus.trigger('web_client_ready');
        });
    },
    bind_events: function() {
        var self = this;
        $('.oe_systray').show();
        this.$el.on('mouseenter', '.oe_systray > div:not([data-toggle=tooltip])', function() {
            $(this).attr('data-toggle', 'tooltip').tooltip().trigger('mouseenter');
        });
        this.$el.on('click', '.oe_dropdown_toggle', function(ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var doc_width = $(document).width();
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.size() >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
            var state = $menu.is('.oe_opened');
            setTimeout(function() {
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
        core.bus.on('click', this, function(ev) {
            $('.tooltip').remove();
            if (!$(ev.target).is('input[type=file]')) {
                self.$el.find('.oe_dropdown_menu.oe_opened, .oe_dropdown_toggle.oe_opened').removeClass('oe_opened');
            }
        });
        core.bus.on('set_full_screen', this, function (full_screen) {
            this.set_content_full_screen(full_screen);
        });
    },
    on_logo_click: function(ev) {
        ev.preventDefault();
        return this.clear_uncommitted_changes().then(function() {
            framework.redirect("/web" + (core.debug ? "?debug" : ""));
        });
    },
    show_common: function() {
        var self = this;
        session.on('error', crash_manager, crash_manager.rpc_error);
        self.notification_manager = new NotificationManager(this);
        self.notification_manager.appendTo(self.$('.openerp'));
        self.loading = new Loading(self);
        self.loading.appendTo(self.$('.openerp_webclient_container'));
        self.action_manager = new ActionManager(self);
        self.action_manager.replace(self.$('.oe_application'));

        window.onerror = function (message, file, line, col, error) {
            var traceback = error ? error.stack : '';
            crash_manager.show_error({
                type: _t("Client Error"),
                message: message,
                data: {debug: file + ':' + line + "\n" + _t('Traceback:') + "\n" + traceback}
            });
        };

    },
    toggle_bars: function(value) {
        this.$('tr:has(td.navbar),.oe_leftbar').toggle(value);
    },
    clear_uncommitted_changes: function() {
        var def = $.Deferred().resolve();
        core.bus.trigger('clear_uncommitted_changes', function chain_callbacks(callback) {
            def = def.then(callback);
        });
        return def;
    },
    /**
        Sets the first part of the title of the window, dedicated to the current action.
    */
    set_title: function(title) {
        this.set_title_part("action", title);
    },
    /**
        Sets an arbitrary part of the title of the window. Title parts are identified by strings. Each time
        a title part is changed, all parts are gathered, ordered by alphabetical order and displayed in the
        title of the window separated by '-'.
    */
    set_title_part: function(part, title) {
        var tmp = _.clone(this.get("title_part"));
        tmp[part] = title;
        this.set("title_part", tmp);
    },
    _title_changed: function() {
        var parts = _.sortBy(_.keys(this.get("title_part")), function(x) { return x; });
        var tmp = "";
        _.each(parts, function(part) {
            var str = this.get("title_part")[part];
            if (str) {
                tmp = tmp ? tmp + " - " + str : str;
            }
        }, this);
        document.title = tmp;
    },
    show_application: function() {
        var self = this;
        self.toggle_bars(true);

        self.update_logo();

        // Menu is rendered server-side thus we don't want the widget to create any dom
        self.menu = new Menu(self);
        self.menu.setElement(this.$el.parents().find('.oe_application_menu_placeholder'));
        self.menu.on('menu_click', this, this.on_menu_action);

        // Create the user menu (rendered client-side)
        self.user_menu = new UserMenu(self);
        var user_menu_loaded = self.user_menu.appendTo(this.$el.parents().find('.oe_user_menu_placeholder'));
        self.user_menu.on('user_logout', self, self.on_logout);
        self.user_menu.do_update();

        // Create the systray menu (rendered server-side)
        self.systray_menu = new SystrayMenu(self);
        self.systray_menu.setElement(this.$el.parents().find('.oe_systray'));
        var systray_menu_loaded = self.systray_menu.start();

        // Start the menu once both systray and user menus are rendered
        // to prevent overflows while loading
        $.when(systray_menu_loaded, user_menu_loaded).done(function() {
            self.menu.start();
        });

        self.bind_hashchange();
        self.set_title();
        if (self.client_options.action_post_login) {
            self.action_manager.do_action(self.client_options.action_post_login);
            delete(self.client_options.action_post_login);
        }
    },
    update_logo: function() {
        var company = session.company_id;
        var img = session.url('/web/binary/company_logo' + '?db=' + session.db + (company ? '&company=' + company : ''));
        this.$('.oe_logo img').attr('src', '').attr('src', img);
        this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', session.uid === 1);
    },
    logo_edit: function(ev) {
        var self = this;
        ev.preventDefault();
        self.alive(new Model("res.users").get_func("read")(session.uid, ["company_id"])).then(function(res) {
            self.rpc("/web/action/load", { action_id: "base.action_res_company_form" }).done(function(result) {
                result.res_id = res.company_id[0];
                result.target = "new";
                result.views = [[false, 'form']];
                result.flags = {
                    action_buttons: true,
                    headless: true,
                };
                self.action_manager.do_action(result);
                var form = self.action_manager.dialog_widget.views.form.controller;
                form.on("on_button_cancel", self.action_manager, self.action_manager.dialog_stop);
                form.on('record_saved', self, function() {
                    self.action_manager.dialog_stop();
                    self.update_logo();
                });
            });
        });
        return false;
    },
    /**
     * When do_action is performed on the WebClient, forward it to the main ActionManager
     * This allows to widgets that are not inside the ActionManager to perform do_action
     */
    do_action: function() {
        return this.action_manager.do_action.apply(this, arguments);
    },
    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$el.children().remove();
    },
    do_reload: function() {
        var self = this;
        return this.session.session_reload().then(function () {
            session.load_modules(true).then(
                self.menu.proxy('do_reload')); });
    },
    on_logout: function() {
        var self = this;
        this.clear_uncommitted_changes().then(function() {
            self.action_manager.do_action('logout');
        });
    },
    bind_hashchange: function() {
        var self = this;
        $(window).bind('hashchange', this.on_hashchange);

        var state = $.bbq.getState(true);
        if (_.isEmpty(state) || state.action == "login") {
            self.menu.is_bound.done(function() {
                new Model("res.users").call("read", [session.uid, ["action_id"]]).done(function(data) {
                    if(data.action_id) {
                        self.action_manager.do_action(data.action_id[0]);
                        self.menu.open_action(data.action_id[0]);
                    } else {
                        var first_menu_id = self.menu.$el.find("a:first").data("menu");
                        if(first_menu_id) {
                            self.menu.menu_click(first_menu_id);
                        }                    }
                });
            });
        } else {
            $(window).trigger('hashchange');
        }
    },
    on_hashchange: function(event) {
        var self = this;
        var stringstate = event.getState(false);
        if (!_.isEqual(this._current_state, stringstate)) {
            var state = event.getState(true);
            if(!state.action && state.menu_id) {
                self.menu.is_bound.done(function() {
                    self.menu.menu_click(state.menu_id);
                });
            } else {
                state._push_me = false;  // no need to push state back...
                this.action_manager.do_load_state(state, !!this._current_state);
            }
        }
        this._current_state = stringstate;
    },
    do_push_state: function(state) {
        this.set_title(state.title);
        delete state.title;
        var url = '#' + $.param(state);
        this._current_state = $.deparam($.param(state), false);     // stringify all values
        $.bbq.pushState(url);
        this.trigger('state_pushed', state);
    },
    on_menu_action: function(options) {
        var self = this;
        return this.menu_dm.add(this.rpc("/web/action/load", { action_id: options.action_id }))
            .then(function (result) {
                return self.action_mutex.exec(function() {
                    if (options.needaction) {
                        result.context = new data.CompoundContext(result.context, {
                            search_default_message_needaction: true,
                            search_disable_custom_filters: true,
                        });
                    }
                    var completed = $.Deferred();
                    $.when(self.action_manager.do_action(result, {
                        clear_breadcrumbs: true,
                        action_menu_id: self.menu.current_menu,
                    })).fail(function() {
                        self.menu.open_menu(options.previous_menu_id);
                    }).always(function() {
                        completed.resolve();
                    });
                    setTimeout(function() {
                        completed.resolve();
                    }, 2000);
                    // We block the menu when clicking on an element until the action has correctly finished
                    // loading. If something crash, there is a 2 seconds timeout before it's unblocked.
                    return completed;
                });
            });
    },
    set_content_full_screen: function(fullscreen) {
        $(document.body).css('overflow-y', fullscreen ? 'hidden' : 'scroll');
        this.$('.oe_webclient').toggleClass(
            'oe_content_full_screen', fullscreen);
    },
});

return WebClient;

});
