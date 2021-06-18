odoo.define('web.public.widget', function (require) {
'use strict';

/**
 * Provides a way to start JS code for public contents.
 */

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
 *
 * @todo Merge with 'PublicWidget' ?
 */
var RootWidget = Widget.extend({
    custom_events: _.extend({}, Widget.prototype.custom_events || {}, {
        'registry_update': '_onRegistryUpdate',
        'get_session': '_onGetSession',
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

        return Promise.all(defs);
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
        return Promise.all(defs);
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
        return Promise.all(defs);
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

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * Provides a way for executing code once a website DOM element is loaded in the
 * dom.
 */
var PublicWidget = Widget.extend({
    /**
     * The selector attribute, if defined, allows to automatically create an
     * instance of this widget on page load for each DOM element which
     * matches this selector. The `PublicWidget.$target` element will then be
     * that particular DOM element. This should be the main way of instantiating
     * `PublicWidget` elements.
     *
     * @todo do not make this part of the Widget but rather an info to give when
     * registering the widget.
     */
    selector: false,
    /**
     * Extension of @see Widget.events
     *
     * A description of the event handlers to bind/delegate once the widget
     * has been rendered::
     *
     *   'click .hello .world': 'async _onHelloWorldClick',
     *     _^_      _^_           _^_        _^_
     *      |        |             |          |
     *      |  (Optional) jQuery   |  Handler method name
     *      |  delegate selector   |
     *      |                      |_ (Optional) space separated options
     *      |                          * async: use the automatic system
     *      |_ Event name with           making handlers promise-ready (see
     *         potential jQuery          makeButtonHandler, makeAsyncHandler)
     *         namespaces
     *
     * Note: the values may be replaced by a function declaration. This is
     * however a deprecated behavior.
     *
     * @type {Object}
     */
    events: {},

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} [options]
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options || {};
    },
    /**
     * Destroys the widget and basically restores the target to the state it
     * was before the start method was called (unlike standard widget, the
     * associated $el DOM is not removed, if this was instantiated thanks to the
     * selector property).
     */
    destroy: function () {
        if (this.selector) {
            var $oldel = this.$el;
            // The difference with the default behavior is that we unset the
            // associated element first so that:
            // 1) its events are unbinded
            // 2) it is not removed from the DOM
            this.setElement(null);
        }

        this._super.apply(this, arguments);

        if (this.selector) {
            // Reassign the variables afterwards to allow extensions to use them
            // after calling the _super method
            this.$el = $oldel;
            this.el = $oldel[0];
            this.$target = this.$el;
            this.target = this.el;
        }
    },
    /**
     * @override
     */
    setElement: function () {
        this._super.apply(this, arguments);
        if (this.selector) {
            this.$target = this.$el;
            this.target = this.el;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @see this.events
     * @override
     */
    _delegateEvents: function () {
        var self = this;
        var originalEvents = this.events;

        var events = {};
        _.each(this.events, function (method, event) {
            // If the method is a function, use the default Widget system
            if (typeof method !== 'string') {
                events[event] = method;
                return;
            }
            // If the method is only a function name without options, use the
            // default Widget system
            var methodOptions = method.split(' ');
            if (methodOptions.length <= 1) {
                events[event] = method;
                return;
            }
            // If the method has no meaningful options, use the default Widget
            // system
            var isAsync = _.contains(methodOptions, 'async');
            if (!isAsync) {
                events[event] = method;
                return;
            }

            method = self.proxy(methodOptions[methodOptions.length - 1]);
            if (_.str.startsWith(event, 'click')) {
                // Protect click handler to be called multiple times by
                // mistake by the user and add a visual disabling effect
                // for buttons.
                method = dom.makeButtonHandler(method);
            } else {
                // Protect all handlers to be recalled while the previous
                // async handler call is not finished.
                method = dom.makeAsyncHandler(method);
            }
            events[event] = method;
        });

        this.events = events;
        this._super.apply(this, arguments);
        this.events = originalEvents;
    },
    /**
     * @private
     * @param {boolean} [extra=false]
     * @param {Object} [extraContext]
     * @returns {Object}
     */
    _getContext: function (extra, extraContext) {
        var context;
        this.trigger_up('context_get', {
            extra: extra || false,
            context: extraContext,
            callback: function (ctx) {
                context = ctx;
            },
        });
        return context;
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of widgets that should be instantiated
 * thanks to their selector property if any.
 */
var registry = {};

/**
 * This is a fix for apple device (<= IPhone 4, IPad 2)
 * Standard bootstrap requires data-toggle='collapse' element to be <a/> tags.
 * Unfortunatly some layouts use a <div/> tag instead. The fix forces an empty
 * click handler on these div, which allows standard bootstrap to work.
 */
registry._fixAppleCollapse = PublicWidget.extend({
    selector: 'div[data-toggle="collapse"]',
    events: {
        'click': function () {},
    },
});

return {
    RootWidget: RootWidget,
    RootWidgetRegistry: RootWidgetRegistry,
    Widget: PublicWidget,
    registry: registry,
};
});
