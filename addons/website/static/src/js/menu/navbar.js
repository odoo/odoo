odoo.define('website.navbar', function (require) {
'use strict';

var rootWidget = require('web_editor.root_widget');
var concurrency = require('web.concurrency');
var Widget = require('web.Widget');
var websiteRootData = require('website.WebsiteRoot');

var websiteNavbarRegistry = new rootWidget.RootWidgetRegistry();

var WebsiteNavbar = rootWidget.RootWidget.extend({
    events: _.extend({}, rootWidget.RootWidget.prototype.events || {}, {
        'click [data-action]': '_onActionMenuClick',
        'mouseover > ul > li.dropdown:not(.show)': '_onMenuHovered',
        'click .o_mobile_menu_toggle': '_onMobileMenuToggleClick',
    }),
    custom_events: _.extend({}, rootWidget.RootWidget.prototype.custom_events || {}, {
        action_demand: '_onActionDemand',
        edit_mode: '_onEditMode',
        ready_to_save: '_onSave',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._widgetDefs = [$.Deferred()];
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._widgetDefs[0].resolve();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _attachComponent: function () {
        var def = this._super.apply(this, arguments);
        this._widgetDefs.push(def);
        return def;
    },
    /**
     * As the WebsiteNavbar instance is designed to be unique, the associated
     * registry has been instantiated outside of the class and is simply
     * returned here.
     *
     * @override
     */
    _getRegistry: function () {
        return websiteNavbarRegistry;
    },
    /**
     * Searches for the automatic widget {@see RootWidget} which can handle that
     * action.
     *
     * @private
     * @param {string} actionName
     * @param {Array} params
     * @returns {Deferred}
     */
    _handleAction: function (actionName, params, _i) {
        var self = this;
        return this._whenReadyForActions().then(function () {
            var defs = [];
            _.each(self._widgets, function (w) {
                if (!w.handleAction) {
                    return;
                }

                var def = w.handleAction(actionName, params);
                if (def !== null) {
                    defs.push(def);
                }
            });
            if (!defs.length) {
                // Handle the case where all action-capable components are not
                // instantiated yet (rare) -> retry some times to eventually abort
                if (_i > 50) {
                    console.warn(_.str.sprintf("Action '%s' was not able to be handled.", actionName));
                    return $.Deferred().reject();
                }
                return concurrency.delay(100).then(function () {
                    return self._handleAction(actionName, params, (_i || 0) + 1);
                });
            }
            return $.when.apply($, defs);
        });
    },
    /**
     * @private
     */
    _whenReadyForActions: function () {
        return $.when.apply($, this._widgetDefs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when an action menu is clicked -> searches for the automatic
     * widget {@see RootWidget} which can handle that action.
     *
     * @private
     * @param {Event} ev
     */
    _onActionMenuClick: function (ev) {
        var $button = $(ev.currentTarget);
        $button.prop('disabled', true);
        this._handleAction($button.data('action')).always(function () {
            $button.prop('disabled', false);
        });
    },
    /**
     * Called when an action is asked to be executed from a child widget ->
     * searches for the automatic widget {@see RootWidget} which can handle
     * that action.
     */
    _onActionDemand: function (ev) {
        var def = this._handleAction(ev.data.actionName, ev.data.params);
        if (ev.data.onSuccess) {
            def.done(ev.data.onSuccess);
        }
        if (ev.data.onFailure) {
            def.fail(ev.data.onFailure);
        }
    },
    /**
     * Called in response to edit mode activation -> hides the navbar.
     *
     * @private
     */
    _onEditMode: function () {
        var self = this;
        this.$el.addClass('editing_mode');
        _.delay(function () {
            self.do_hide();
        }, 800);
    },
    /**
     * Called when a submenu is hovered -> automatically opens it if another
     * menu was already opened.
     *
     * @private
     * @param {Event} ev
     */
    _onMenuHovered: function (ev) {
        var $opened = this.$('> ul > li.dropdown.show');
        if ($opened.length) {
            $opened.find('.dropdown-toggle').dropdown('toggle');
            $(ev.currentTarget).find('.dropdown-toggle').dropdown('toggle');
        }
    },
    /**
     * Called when the mobile menu toggle button is click -> modifies the DOM
     * to open the mobile menu.
     *
     * @private
     */
    _onMobileMenuToggleClick: function () {
        this.$el.parent().toggleClass('o_mobile_menu_opened');
    },
    /**
     * Called in response to edit mode saving -> checks if action-capable
     * children have something to save.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSave: function (ev) {
        ev.data.defs.push(this._handleAction('on_save'));
    },
});

var WebsiteNavbarActionWidget = Widget.extend({
    /**
     * 'Action name' -> 'Handler name' object
     *
     * Any [data-action="x"] element inside the website navbar will
     * automatically trigger an action "x". This action can then be handled by
     * any `WebsiteNavbarActionWidget` instance if the action name "x" is
     * registered in this `actions` object.
     */
    actions: {},

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Checks if the widget can execute an action whose name is given, with the
     * given parameters. If it is the case, execute that action.
     *
     * @param {string} actionName
     * @param {Array} params
     * @returns {Deferred|null} action's deferred or null if no action was found
     */
    handleAction: function (actionName, params) {
        var action = this[this.actions[actionName]];
        if (action) {
            return $.when(action.apply(this, params || []));
        }
        return null;
    },
});

websiteRootData.websiteRootRegistry.add(WebsiteNavbar, '#oe_main_menu_navbar');

return {
    WebsiteNavbar: WebsiteNavbar,
    websiteNavbarRegistry: websiteNavbarRegistry,
    WebsiteNavbarActionWidget: WebsiteNavbarActionWidget,
};
});
