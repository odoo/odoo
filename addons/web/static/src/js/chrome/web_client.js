odoo.define('web.WebClient', function (require) {
"use strict";

var AbstractWebClient = require('web.AbstractWebClient');
var config = require('web.config');
var core = require('web.core');
var data_manager = require('web.data_manager');
var dom = require('web.dom');
var Menu = require('web.Menu');
var session = require('web.session');

return AbstractWebClient.extend({
    custom_events: _.extend({}, AbstractWebClient.prototype.custom_events, {
        app_clicked: 'on_app_clicked',
        menu_clicked: 'on_menu_clicked',
    }),
    start: function () {
        core.bus.on('change_menu_section', this, function (menuID) {
            this.do_push_state(_.extend($.bbq.getState(), {
                menu_id: menuID,
            }));
        });

        return this._super.apply(this, arguments);
    },
    bind_events: function () {
        var self = this;
        this._super.apply(this, arguments);

        /*
            Small patch to allow having a link with a href towards an anchor. Since odoo use hashtag
            to represent the current state of the view, we can't easily distinguish between a link
            towards an anchor and a link towards anoter view/state. If we want to navigate towards an
            anchor, we must not change the hash of the url otherwise we will be redirected to the app
            switcher instead.
            To check if we have an anchor, first check if we have an href attributes starting with #.
            Try to find a element in the DOM using JQuery selector.
            If we have a match, it means that it is probably a link to an anchor, so we jump to that anchor.
        */
        this.$el.on('click', 'a', function (ev) {
            var disable_anchor = ev.target.attributes.disable_anchor;
            if (disable_anchor && disable_anchor.value === "true") {
                return;
            }

            var href = ev.target.attributes.href;
            if (href) {
                if (href.value[0] === '#' && href.value.length > 1) {
                    if (self.$("[id='"+href.value.substr(1)+"']").length) {
                        ev.preventDefault();
                        self.trigger_up('scrollTo', {'selector': href.value});
                    }
                }
            }
        });
    },
    load_menus: function () {
        return this._rpc({
                model: 'ir.ui.menu',
                method: 'load_menus',
                args: [config.debug],
                context: session.user_context,
            })
            .then(function (menuData) {
                // Compute action_id if not defined on a top menu item
                for (var i = 0; i < menuData.children.length; i++) {
                    var child = menuData.children[i];
                    if (child.action === false) {
                        while (child.children && child.children.length) {
                            child = child.children[0];
                            if (child.action) {
                                menuData.children[i].action = child.action;
                                break;
                            }
                        }
                    }
                }
                return menuData;
            });
    },
    show_application: function () {
        var self = this;
        this.set_title();

        return this.instanciate_menu_widgets().then(function () {
            $(window).bind('hashchange', self.on_hashchange);

            // If the url's state is empty, we execute the user's home action if there is one (we
            // show the first app if not)
            if (_.isEmpty($.bbq.getState(true))) {
                return self._rpc({
                        model: 'res.users',
                        method: 'read',
                        args: [session.uid, ["action_id"]],
                    })
                    .then(function (result) {
                        var data = result[0];
                        if (data.action_id) {
                            return self.do_action(data.action_id[0]).then(function () {
                                self.menu.change_menu_section(self.menu.action_id_to_primary_menu_id(data.action_id[0]));
                            });
                        } else {
                            self.menu.openFirstApp();
                        }
                    });
            } else {
                return self.on_hashchange();
            }
        });
    },

    instanciate_menu_widgets: function () {
        var self = this;
        var defs = [];
        return this.load_menus().then(function (menuData) {
            self.menu_data = menuData;

            // Here, we instanciate every menu widgets and we immediately append them into dummy
            // document fragments, so that their `start` method are executed before inserting them
            // into the DOM.
            if (self.menu) {
                self.menu.destroy();
            }
            self.menu = new Menu(self, menuData);
            defs.push(self.menu.prependTo(self.$el));
            return $.when.apply($, defs);
        });
    },

    // --------------------------------------------------------------
    // URL state handling
    // --------------------------------------------------------------
    on_hashchange: function (event) {
        if (this._ignore_hashchange) {
            this._ignore_hashchange = false;
            return $.when();
        }

        var self = this;
        return this.clear_uncommitted_changes().then(function () {
            var stringstate = $.bbq.getState(false);
            if (!_.isEqual(self._current_state, stringstate)) {
                var state = $.bbq.getState(true);
                if (state.action || (state.model && (state.view_type || state.id))) {
                    return self.action_manager.loadState(state, !!self._current_state).then(function () {
                        if (state.menu_id) {
                            if (state.menu_id !== self.menu.current_primary_menu) {
                                core.bus.trigger('change_menu_section', state.menu_id);
                            }
                        } else {
                            var action = self.action_manager.getCurrentAction();
                            if (action) {
                                var menu_id = self.menu.action_id_to_primary_menu_id(action.id);
                                core.bus.trigger('change_menu_section', menu_id);
                            }
                        }
                    });
                } else if (state.menu_id) {
                    var action_id = self.menu.menu_id_to_action_id(state.menu_id);
                    return self.do_action(action_id, {clear_breadcrumbs: true}).then(function () {
                        core.bus.trigger('change_menu_section', state.menu_id);
                    });
                } else {
                    self.menu.openFirstApp();
                }
            }
            self._current_state = stringstate;
        }, function () {
            if (event) {
                self._ignore_hashchange = true;
                window.location = event.originalEvent.oldURL;
            }
        });
    },

    // --------------------------------------------------------------
    // Menu handling
    // --------------------------------------------------------------
    on_app_clicked: function (ev) {
        var self = this;
        return this.menu_dm.add(data_manager.load_action(ev.data.action_id))
            .then(function (result) {
                return self.action_mutex.exec(function () {
                    var completed = $.Deferred();
                    var options = _.extend({}, ev.data.options, {
                        clear_breadcrumbs: true,
                        action_menu_id: ev.data.menu_id,
                    });
                    $.when(self._openMenu(result, options)).fail(function () {
                        completed.resolve();
                    }).done(function () {
                        self._on_app_clicked_done(ev)
                            .then(completed.resolve.bind(completed))
                            .fail(completed.reject.bind(completed));
                    });
                    setTimeout(function () {
                        completed.resolve();
                    }, 2000);
                    return completed;
                });
            });
    },
    _on_app_clicked_done: function (ev) {
        core.bus.trigger('change_menu_section', ev.data.menu_id);
        return $.Deferred().resolve();
    },
    on_menu_clicked: function (ev) {
        var self = this;
        return this.menu_dm.add(data_manager.load_action(ev.data.action_id))
            .then(function (result) {
                return self.action_mutex.exec(function () {
                    var completed = $.Deferred();
                    $.when(self._openMenu(result, {
                        clear_breadcrumbs: true,
                    })).always(function () {
                        completed.resolve();
                    });

                    setTimeout(function () {
                        completed.resolve();
                    }, 2000);

                    return completed;
                });
            }).always(function () {
                self.$el.removeClass('o_mobile_menu_opened');
            });
    },
    /**
     * Open the action linked to a menu.
     * This function is mostly used to allow override in other modules.
     *
     * @private
     * @param {Object} action
     * @param {Object} options
     * @returns {Deferred}
     */
    _openMenu: function (action, options) {
        return this.do_action(action, options);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the left and top scroll positions of the main scrolling area
     * (i.e. the action manager in desktop).
     *
     * @returns {Object} with keys left and top
     */
    getScrollPosition: function () {
        return {
            left: this.action_manager.el.scrollLeft,
            top: this.action_manager.el.scrollTop,
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onGetScrollPosition: function (ev) {
        ev.data.callback(this.getScrollPosition());
    },
    /**
     * @override
     * @private
     */
    _onScrollTo: function (ev) {
        var offset = {top: ev.data.top, left: ev.data.left || 0};
        if (!offset.top) {
            offset = dom.getPosition(document.querySelector(ev.data.selector));
            // Substract the position of the action_manager as it is the scrolling part
            offset.top -= dom.getPosition(this.action_manager.el).top;
        }
        this.action_manager.el.scrollTop = offset.top;
        this.action_manager.el.scrollLeft = offset.left;
    },
});

});
