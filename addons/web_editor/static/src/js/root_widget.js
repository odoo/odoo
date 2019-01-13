odoo.define('web_editor.root_widget', function (require) {
'use strict';

var Class = require('web.Class');
var dom = require('web.dom');
var mixins = require('web.mixins');
var session = require('web.session');
var Widget = require('web.Widget');

/**
 * Specialized Widget which automatically instantiates child widgets to attach
 * to internal DOM elements once it is started. The widgets to instantiate are
 * known thanks to a linked registry which contains info about the widget
 * classes and jQuery selectors to use to find the elements to attach them to.
 */
var RootWidget = Widget.extend({
    custom_events: _.extend({}, Widget.prototype.custom_events || {}, {
        registry_update: '_onRegistryUpdate',
        get_session: '_onGetSession',
    }),
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._widgets = [];
        this._listenToUpdates = false;
        this._getRegistry().setParent(this);
    },
    /**
     * @override
     * @see _attachComponents
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        defs.push(this._attachComponents());
        this._listenToUpdates = true;

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates a child widget according to the given registry data.
     *
     * @private
     * @param {Object} childInfo
     * @param {function} childInfo.Widget - the widget class to instantiate
     * @param {string} childInfo.selector
     *        the jQuery selector to use to find the internal DOM element which
     *        needs to be attached to the instantiated widget
     * @param {jQuery} [$from] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.$el.
     * @returns {Deferred}
     */
    _attachComponent: function (childInfo, $from) {
        var self = this;
        var $elements = dom.cssFind($from || this.$el, childInfo.selector);
        var defs = _.map($elements, function (element) {
            var w = new childInfo.Widget(self);
            self._widgets.push(w);
            return w.attachTo(element);
        });
        return $.when.apply($, defs);
    },
    /**
     * Instantiates the child widgets that need to be according to the linked
     * registry.
     *
     * @private
     * @param {jQuery} [$from] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.$el.
     * @returns {Deferred}
     */
    _attachComponents: function ($from) {
        var self = this;
        var childInfos = this._getRegistry().get();
        var defs = _.map(childInfos, function (childInfo) {
            return self._attachComponent(childInfo, $from);
        });
        return $.when.apply($, defs);
    },
    /**
     * Returns the `RootWidgetRegistry` instance that is linked to this
     * `RootWidget` instance.
     *
     * @abstract
     * @private
     * @returns {RootWidgetRegistry}
     */
    _getRegistry: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Get the curuent session module.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onGetSession: function (event) {
        if (event.data.callback) {
            event.data.callback(session);
        }
    },
    /**
     * Called when the linked registry is updated after this `RootWidget`
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onRegistryUpdate: function (ev) {
        ev.stopPropagation();
        if (this._listenToUpdates) {
            this._attachComponent(ev.data);
        }
    },
});

var RootWidgetRegistry = Class.extend(mixins.EventDispatcherMixin, {
    /**
     * @constructor
     */
    init: function () {
        mixins.EventDispatcherMixin.init.call(this);
        this._registry = [];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds an element to the registry (info of what and how to instantiate).
     *
     * @param {function} Widget - the widget class to instantiate
     * @param {string} selector
     *        the jQuery selector to use to find the internal DOM element which
     *        needs to be attached to the instantiated widget
     */
    add: function (Widget, selector) {
        var registryInfo = {
            Widget: Widget,
            selector: selector,
        };
        this._registry.push(registryInfo);
        this.trigger_up('registry_update', registryInfo);
    },
    /**
     * Retrieves all the registry elements.
     */
    get: function () {
        return this._registry;
    },
});

return {
    RootWidget: RootWidget,
    RootWidgetRegistry: RootWidgetRegistry,
};
});
