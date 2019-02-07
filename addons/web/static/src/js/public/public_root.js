odoo.define('web.public.root', function (require) {
'use strict';

var ajax = require('web.ajax');
var ServiceProviderMixin = require('web.ServiceProviderMixin');
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
var PublicRoot = publicWidget.RootWidget.extend(ServiceProviderMixin, {
    events: _.extend({}, publicWidget.RootWidget.prototype.events || {}, {
        'submit .js_website_submit_form': '_onWebsiteFormSubmit',
        'click .js_disable_on_click': '_onDisableOnClick',
    }),
    custom_events: _.extend({}, publicWidget.RootWidget.prototype.custom_events || {}, {
        'animation_start_demand': '_onAnimationStartDemand',
        'animation_stop_demand': '_onAnimationStopDemand',
        'context_get': '_onContextGet',
        'main_object_request': '_onMainObjectRequest',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        ServiceProviderMixin.init.call(this);
        this.animations = [];
    },
    /**
     * @override
     */
    willStart: function () {
        // TODO would be even greater to wait for localeDef only when necessary
        return $.when(
            this._super.apply(this, arguments),
            session.is_bound,
            localeDef
        );
    },
    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        // Animations
        defs.push(this._startAnimations());

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

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Automatically adds the global context to RPCs.
     *
     * @override
     */
    _call_service: function (ev) {
        if (ev.data.service === 'ajax' && ev.data.method === 'rpc') {
            var route = ev.data.args[0];
            if (_.str.startsWith(route, '/web/dataset/call_kw/')) {
                var params = ev.data.args[1];
                var options = ev.data.args[2];
                params.kwargs.context = _.extend({}, this._getContext(), params.kwargs.context || {});
                if (options) {
                    params.kwargs.context = _.omit(params.kwargs.context, options.noContextKeys);
                    ev.data.args[2] = _.omit(options, 'noContextKeys');
                }
                params.kwargs.context = JSON.parse(JSON.stringify(params.kwargs.context));
            }
        }
        return ServiceProviderMixin._call_service.apply(this, arguments);
    },
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
     *        only initialize the animations whose `selector` matches the
     *        element or one of its descendant (default to the wrapwrap element)
     * @param {Object} [options]
     * @returns {Deferred}
     */
    _startAnimations: function ($from, options) {
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

        this._stopAnimations($from);

        var defs = _.map(this._getPublicWidgetsRegistry(options), function (WebsiteWidget) {
            var selector = WebsiteWidget.prototype.selector || '';
            var $target = $from.find(selector).addBack(selector);

            var defs = _.map($target, function (el) {
                var animation = new WebsiteWidget(self, options);
                self.animations.push(animation);
                return animation.attachTo($(el));
            });
            return $.when.apply($, defs);
        });
        return $.when.apply($, defs);
    },
    /**
     * Destroys all registered widget instances. Website would need this before
     * saving while in edition mode for example.
     *
     * @private
     * @param {jQuery} [$from]
     *        only stop the animations linked to the given element(s) or one of
     *        its descendants
     */
    _stopAnimations: function ($from) {
        var removedAnimations = _.map(this.animations, function (animation) {
            if (!$from
                || $from.filter(animation.el).length
                || $from.find(animation.el).length) {
                animation.destroy();
                return animation;
            }
            return null;
        });
        this.animations = _.difference(this.animations, removedAnimations);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the root is notified that the animations have to be
     * (re)started.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAnimationStartDemand: function (ev) {
        this._startAnimations(ev.data.$target, ev.data.options)
            .done(ev.data.onSuccess)
            .fail(ev.data.onFailure);
    },
    /**
     * Called when the root is notified that the animations have to be
     * stopped.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAnimationStopDemand: function (ev) {
        this._stopAnimations(ev.data.$target);
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
     * @todo review
     * @private
     */
    _onWebsiteFormSubmit: function (ev) {
        var $buttons = $(ev.currentTarget).find('button[type="submit"], a.a-submit');
        _.each($buttons, function (btn) {
            var $btn = $(btn);
            $btn.attr('data-loading-text', '<i class="fa fa-spinner fa-spin"></i> ' + $(btn).text());
            $btn.button('loading');
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
});

return {
    PublicRoot: PublicRoot,
    publicRootRegistry: publicRootRegistry,
};
});
