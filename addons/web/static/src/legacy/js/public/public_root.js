odoo.define('web.public.root', function (require) {
'use strict';

var ajax = require('web.ajax');
var dom = require('web.dom');
const env = require('web.public_env');
var session = require('web.session');
var utils = require('web.utils');
var publicWidget = require('web.public.widget');

var publicRootRegistry = new publicWidget.RootWidgetRegistry();

// Load localizations outside the PublicRoot to not wait for DOM ready (but
// wait for them in PublicRoot)
function getLang() {
    var html = document.documentElement;
    return (html.getAttribute('lang') || 'en_US').replace('-', '_');
}
var lang = utils.get_cookie('frontend_lang') || getLang(); // FIXME the cookie value should maybe be in the ctx?
var localeDef = ajax.loadJS('/web/webclient/locale/' + lang.replace('-', '_'));

/**
 * Element which is designed to be unique and that will be the top-most element
 * in the widget hierarchy. So, all other widgets will be indirectly linked to
 * this Class instance. Its main role will be to retrieve RPC demands from its
 * children and handle them.
 */
var PublicRoot = publicWidget.RootWidget.extend({
    events: _.extend({}, publicWidget.RootWidget.prototype.events || {}, {
        'submit .js_website_submit_form': '_onWebsiteFormSubmit',
        'click .js_disable_on_click': '_onDisableOnClick',
    }),
    custom_events: _.extend({}, publicWidget.RootWidget.prototype.custom_events || {}, {
        call_service: '_onCallService',
        context_get: '_onContextGet',
        main_object_request: '_onMainObjectRequest',
        widgets_start_request: '_onWidgetsStartRequest',
        widgets_stop_request: '_onWidgetsStopRequest',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.env = env;
        this.publicWidgets = [];
    },
    /**
     * @override
     */
    willStart: function () {
        // TODO would be even greater to wait for localeDef only when necessary
        return Promise.all([
            this._super.apply(this, arguments),
            session.is_bound,
            localeDef
        ]);
    },
    /**
     * @override
     */
    start: function () {
        var defs = [
            this._super.apply(this, arguments),
            this._startWidgets()
        ];

        // Display image thumbnail
        this.$(".o_image[data-mimetype^='image']").each(function () {
            var $img = $(this);
            if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
                $img.css('background-image', "url('" + $img.data('src') + "')");
            }
        });

        // Auto scroll
        if (window.location.hash.indexOf("scrollTop=") > -1) {
            this.el.scrollTop = +window.location.hash.match(/scrollTop=([0-9]+)/)[1];
        }

        // Fix for IE:
        if ($.fn.placeholder) {
            $('input, textarea').placeholder();
        }

        this.$el.children().on('error.datetimepicker', this._onDateTimePickerError.bind(this));

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Retrieves the global context of the public environment. This is the
     * context which is automatically added to each RPC.
     *
     * @private
     * @param {Object} [context]
     * @returns {Object}
     */
    _getContext: function (context) {
        return _.extend({
            'lang': getLang(),
        }, context || {});
    },
    /**
     * Retrieves the global context of the public environment (as
     * @see _getContext) but with extra informations that would be useless to
     * send with each RPC.
     *
     * @private
     * @param {Object} [context]
     * @returns {Object}
     */
    _getExtraContext: function (context) {
        return this._getContext(context);
    },
    /**
     * @private
     * @param {Object} [options]
     * @returns {Object}
     */
    _getPublicWidgetsRegistry: function (options) {
        return publicWidget.registry;
    },
    /**
     * As the root instance is designed to be unique, the associated
     * registry has been instantiated outside of the class and is simply
     * returned here.
     *
     * @private
     * @override
     */
    _getRegistry: function () {
        return publicRootRegistry;
    },
    /**
     * Creates an PublicWidget instance for each DOM element which matches the
     * `selector` key of one of the registered widgets
     * (@see PublicWidget.selector).
     *
     * @private
     * @param {jQuery} [$from]
     *        only initialize the public widgets whose `selector` matches the
     *        element or one of its descendant (default to the wrapwrap element)
     * @param {Object} [options]
     * @returns {Deferred}
     */
    _startWidgets: function ($from, options) {
        var self = this;

        if ($from === undefined) {
            $from = this.$('#wrapwrap');
            if (!$from.length) {
                // TODO Remove this once all frontend layouts possess a
                // #wrapwrap element (which is necessary for those pages to be
                // adapted correctly if the user installs website).
                $from = this.$el;
            }
        }
        if (options === undefined) {
            options = {};
        }

        this._stopWidgets($from);

        var defs = _.map(this._getPublicWidgetsRegistry(options), function (PublicWidget) {
            var selector = PublicWidget.prototype.selector || '';
            var $target = dom.cssFind($from, selector, true);

            var defs = _.map($target, function (el) {
                var widget = new PublicWidget(self, options);
                self.publicWidgets.push(widget);
                return widget.attachTo($(el));
            });
            return Promise.all(defs);
        });
        return Promise.all(defs);
    },
    /**
     * Destroys all registered widget instances. Website would need this before
     * saving while in edition mode for example.
     *
     * @private
     * @param {jQuery} [$from]
     *        only stop the public widgets linked to the given element(s) or one
     *        of its descendants
     */
    _stopWidgets: function ($from) {
        var removedWidgets = _.map(this.publicWidgets, function (widget) {
            if (!$from
                || $from.filter(widget.el).length
                || $from.find(widget.el).length) {
                widget.destroy();
                return widget;
            }
            return null;
        });
        this.publicWidgets = _.difference(this.publicWidgets, removedWidgets);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Calls the requested service from the env. Automatically adds the global
     * context to RPCs.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onCallService: function (ev) {
        function _computeContext(context, noContextKeys) {
            context = _.extend({}, this._getContext(), context);
            if (noContextKeys) {
                context = _.omit(context, noContextKeys);
            }
            return JSON.parse(JSON.stringify(context));
        }

        const payload = ev.data;
        let args = payload.args || [];
        if (payload.service === 'ajax' && payload.method === 'rpc') {
            // ajax service uses an extra 'target' argument for rpc
            args = args.concat(ev.target);

            var route = args[0];
            if (_.str.startsWith(route, '/web/dataset/call_kw/')) {
                var params = args[1];
                var options = args[2];
                var noContextKeys;
                if (options) {
                    noContextKeys = options.noContextKeys;
                    args[2] = _.omit(options, 'noContextKeys');
                }
                params.kwargs.context = _computeContext.call(this, params.kwargs.context, noContextKeys);
            }
        } else if (payload.service === 'ajax' && payload.method === 'loadLibs') {
            args[1] = _computeContext.call(this, args[1]);
        }

        const service = this.env.services[payload.service];
        const result = service[payload.method].apply(service, args);
        payload.callback(result);
    },
    /**
     * Called when someone asked for the global public context.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContextGet: function (ev) {
        if (ev.data.extra) {
            ev.data.callback(this._getExtraContext(ev.data.context));
        } else {
            ev.data.callback(this._getContext(ev.data.context));
        }
    },
    /**
     * Checks information about the page main object.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onMainObjectRequest: function (ev) {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        ev.data.callback({
            model: m[1],
            id: m[2] | 0,
        });
    },
    /**
     * Called when the root is notified that the public widgets have to be
     * (re)started.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onWidgetsStartRequest: function (ev) {
        this._startWidgets(ev.data.$target, ev.data.options)
            .then(ev.data.onSuccess)
            .guardedCatch(ev.data.onFailure);
    },
    /**
     * Called when the root is notified that the public widgets have to be
     * stopped.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onWidgetsStopRequest: function (ev) {
        this._stopWidgets(ev.data.$target);
    },
    /**
     * @todo review
     * @private
     */
    _onWebsiteFormSubmit: function (ev) {
        var $buttons = $(ev.currentTarget).find('button[type="submit"], a.a-submit');
        _.each($buttons, function (btn) {
            var $btn = $(btn);
            $btn.html('<i class="fa fa-spinner fa-spin"></i> ' + $btn.text());
            $btn.prop('disabled', true);
        });
    },
    /**
     * Called when the root is notified that the button should be
     * disabled after the first click.
     *
     * @private
     * @param {Event} ev
     */
    _onDisableOnClick: function (ev) {
        $(ev.currentTarget).addClass('disabled');
    },
    /**
     * Library clears the wrong date format so just ignore error
     *
     * @private
     * @param {Event} ev
     */
    _onDateTimePickerError: function (ev) {
        return false;
    },
});

return {
    PublicRoot: PublicRoot,
    publicRootRegistry: publicRootRegistry,
};
});
