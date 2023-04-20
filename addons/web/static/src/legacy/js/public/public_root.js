/** @odoo-module alias=web.public.root */

import dom from 'web.dom';
import legacyEnv from 'web.public_env';
import session from 'web.session';
import {getCookie} from 'web.utils.cookies';
import publicWidget from 'web.public.widget';
import { registry } from '@web/core/registry';

import AbstractService from "web.AbstractService";
import lazyloader from "web.public.lazyloader";

import {
    makeLegacyNotificationService,
    makeLegacySessionService,
    makeLegacyDialogMappingService,
    mapLegacyEnvToWowlEnv,
    makeLegacyRainbowManService,
} from "../../utils";
import { standaloneAdapter } from "web.OwlCompatibility";

import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, loadJS, templates } from '@web/core/assets';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { browser } from '@web/core/browser/browser';
import { jsonrpc } from '@web/core/network/rpc_service';
import { _t } from "@web/core/l10n/translation";


const serviceRegistry = registry.category("services");
import { Component, App, whenReady } from "@odoo/owl";

// Load localizations outside the PublicRoot to not wait for DOM ready (but
// wait for them in PublicRoot)
function getLang() {
    var html = document.documentElement;
    return (html.getAttribute('lang') || 'en_US').replace('-', '_');
}
const lang = getCookie('frontend_lang') || getLang(); // FIXME the cookie value should maybe be in the ctx?
// momentjs don't have config for en_US, so avoid useless RPC
var localeDef = lang !== 'en_US' ? loadJS('/web/webclient/locale/' + lang.replace('-', '_')) : Promise.resolve();


/**
 * Element which is designed to be unique and that will be the top-most element
 * in the widget hierarchy. So, all other widgets will be indirectly linked to
 * this Class instance. Its main role will be to retrieve RPC demands from its
 * children and handle them.
 */
export const PublicRoot = publicWidget.RootWidget.extend({
    events: Object.assign({}, publicWidget.RootWidget.prototype.events || {}, {
        'submit .js_website_submit_form': '_onWebsiteFormSubmit',
        'click .js_disable_on_click': '_onDisableOnClick',
    }),
    custom_events: Object.assign({}, publicWidget.RootWidget.prototype.custom_events || {}, {
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
        this.env = legacyEnv;
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
        return Object.assign({
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
        return registry.category("public_root_widgets");
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
        options = Object.assign({}, options, {
            wysiwyg: $('#wrapwrap').data('wysiwyg'),
        });

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
            context = Object.assign({}, this._getContext(), context);
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
            if (String(route).startsWith("/web/dataset/call_kw/")) {
                var params = args[1];
                var options = args[2];
                var noContextKeys;
                if (options) {
                    noContextKeys = options.noContextKeys;
                    args[2] = _.omit(options, 'noContextKeys');
                }
                params.kwargs.context = _computeContext.call(this, params.kwargs.context, noContextKeys);
            }
        } else {
            return;
        }

        const service = this.env.services[payload.service];
        const result = service[payload.method].apply(service, args);
        payload.callback(result);
        ev.stopPropagation();
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
        var $buttons = $(ev.currentTarget).find('button[type="submit"], a.a-submit').toArray();
        $buttons.forEach((btn) => {
            var $btn = $(btn);
            $btn.prepend('<i class="fa fa-circle-o-notch fa-spin"></i> ');
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

/**
 * Configure Owl with the public env
 */
owl.Component.env = legacyEnv;

/**
 * This widget is important, because the tour manager needs a root widget in
 * order to work. The root widget must be a service provider with the ajax
 * service, so that the tour manager can let the server know when tours have
 * been consumed.
 */
export async function createPublicRoot(RootWidget) {
    await lazyloader.allScriptsLoaded;
    AbstractService.prototype.deployServices(legacyEnv);
    // add a bunch of mapping services that will redirect service calls from the legacy env
    // to the wowl env
    serviceRegistry.add("legacy_session", makeLegacySessionService(legacyEnv, session));
    serviceRegistry.add("legacy_notification", makeLegacyNotificationService(legacyEnv));
    serviceRegistry.add("legacy_dialog_mapping", makeLegacyDialogMappingService(legacyEnv));
    serviceRegistry.add("legacy_rainbowman_service", makeLegacyRainbowManService(legacyEnv));
    const wowlToLegacyServiceMappers = registry.category('wowlToLegacyServiceMappers').getEntries();
    for (const [legacyServiceName, wowlToLegacyServiceMapper] of wowlToLegacyServiceMappers) {
        serviceRegistry.add(legacyServiceName, wowlToLegacyServiceMapper(legacyEnv));
    }
    await Promise.all([whenReady(), session.is_bound]);

    // Patch browser.fetch and the rpc service to use the correct base url when
    // embeded in an external page
    const baseUrl = session.prefix;
    const { fetch } = browser;
    browser.fetch = function(url, ...args) {
        if (!url.match(/^(?:https?:)?\/\//)) {
            url = baseUrl + url;
        }
        return fetch(url, ...args);
    }
    serviceRegistry.add("rpc", {
        async: true,
        start(env) {
            let rpcId = 0;
            return function rpc(route, params = {}, settings) {
                if (!route.match(/^(?:https?:)?\/\//)) {
                    route = baseUrl + route;
                }
                return jsonrpc(env, rpcId++, route, params, settings);
            };
        },
    }, { force: true });

    const wowlEnv = makeEnv();

    await startServices(wowlEnv);
    mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv);
    // The root widget's parent is a standalone adapter so that it has _trigger_up
    const publicRoot = new RootWidget(standaloneAdapter({ Component }));
    const app = new App(MainComponentsContainer, {
        templates,
        env: wowlEnv,
        dev: wowlEnv.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    setLoadXmlDefaultApp(app);
    await Promise.all([
        app.mount(document.body),
        publicRoot.attachTo(document.body),
    ]);
    return publicRoot;
}

export default { PublicRoot, createPublicRoot };
