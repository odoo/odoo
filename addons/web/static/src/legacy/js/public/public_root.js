import { cookie } from "@web/core/browser/cookie";
import publicWidget from '@web/legacy/js/public/public_widget';

import lazyloader from "@web/legacy/js/public/lazyloader";

import { makeEnv, startServices } from "@web/env";
import { getTemplate } from '@web/core/templates';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { browser } from '@web/core/browser/browser';
import { _t } from "@web/core/l10n/translation";
import { jsToPyLocale, pyToJsLocale } from "@web/core/l10n/utils";
import { App, Component, whenReady } from "@odoo/owl";
import { RPCError } from '@web/core/network/rpc';
import { patch } from "@web/core/utils/patch";

const { Settings } = luxon;

// Load localizations outside the PublicRoot to not wait for DOM ready (but
// wait for them in PublicRoot)
function getLang() {
    var html = document.documentElement;
    return jsToPyLocale(html.getAttribute('lang')) || 'en_US';
}
const lang = cookie.get('frontend_lang') || getLang(); // FIXME the cookie value should maybe be in the ctx?


/**
 * Element which is designed to be unique and that will be the top-most element
 * in the widget hierarchy. So, all other widgets will be indirectly linked to
 * this Class instance. Its main role will be to retrieve RPC demands from its
 * children and handle them.
 */
export const PublicRoot = publicWidget.Widget.extend({
    events: {
        'submit .js_website_submit_form': '_onWebsiteFormSubmit',
        'click .js_disable_on_click': '_onDisableOnClick',
    },
    custom_events: {
        call_service: '_onCallService',
        context_get: '_onContextGet',
        main_object_request: '_onMainObjectRequest',
        widgets_start_request: '_onWidgetsStartRequest',
        widgets_stop_request: '_onWidgetsStopRequest',
    },

    /**
     * @constructor
     */
    init: function (_, env) {
        this._super.apply(this, arguments);
        this.env = env;
        this.publicWidgets = [];
        // Patch interaction_service so that it also starts and stops public
        // widgets.
        const interactionsService = this.env.services["public.interactions"];
        const publicRoot = this;
        if (interactionsService) {
            patch(interactionsService.constructor.prototype, {
                startInteractions(el) {
                    super.startInteractions(el);
                    if (!publicRoot.startFromEventHandler) {
                        // this.editMode is assigned by website_edit_service
                        publicRoot._startWidgets($(el || this.el), { fromInteractionPatch: true, editableMode: this.editMode })
                    }
                },
                stopInteractions(el) {
                    super.stopInteractions(el);
                    // Call to interactions is only from the event handler.
                    if (!publicRoot.stopFromEventHandler) {
                        publicRoot._stopWidgets($(el || this.el));
                    }
                },
            });
        }
    },
    /**
     * @override
     */
    start: function () {
        var defs = [
            this._super.apply(this, arguments),
            this._startWidgets(undefined, { starting: true })
        ];

        // Display image thumbnail
        this.$(".o_image[data-mimetype^='image']").each(function () {
            var $img = $(this);
            if (/gif|jpe|jpg|png|webp/.test($img.data('mimetype')) && $img.data('src')) {
                $img.css('background-image', "url('" + $img.data('src') + "')");
            }
        });

        // Auto scroll
        if (window.location.hash.indexOf("scrollTop=") > -1) {
            this.el.scrollTop = +window.location.hash.match(/scrollTop=([0-9]+)/)[1];
        }

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
     * Restarts interactions from the specified targetEl, or from #wrapwrap.
     *
     * @private
     * @param {HTMLElement} targetEl
     * @param {Object} [options]
     */
    _restartInteractions(targetEl, options) {
        const publicInteractions = this.bindService("public.interactions");
        publicInteractions.stopInteractions(targetEl);
        publicInteractions.startInteractions(targetEl);
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
        if (!options?.starting && !options?.fromInteractionPatch) {
            if ($from) {
                for (const fromEl of $from) {
                    this._restartInteractions(fromEl, options);
                }
            } else {
                this._restartInteractions(undefined, options);
            }
        }

        var defs = Object.values(this._getPublicWidgetsRegistry(options)).map((PublicWidget) => {
            const selector = PublicWidget.prototype.selector;
            if (!selector) {
                return;
            }
            const selectorHas = PublicWidget.prototype.selectorHas;
            const selectorFunc = typeof selector === 'function'
                ? selector
                : fromEl => {
                    const els = [...fromEl.querySelectorAll(selector)];
                    if (fromEl.matches(selector)) {
                        els.push(fromEl);
                    }
                    return els;
                };

            let targetEls = [];
            for (const fromEl of $from) {
                targetEls.push(...selectorFunc(fromEl));
            }
            if (selectorHas) {
                targetEls = targetEls.filter(el => !!el.querySelector(selectorHas));
            }

            const proms = targetEls.map(el => {
                var widget = new PublicWidget(self, options);
                self.publicWidgets.push(widget);
                return widget.attachTo(el);
            });
            return Promise.all(proms);
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
        var removedWidgets = this.publicWidgets.map((widget) => {
            if (!$from
                || $from.filter(widget.el).length
                || $from.find(widget.el).length) {
                widget.destroy();
                return widget;
            }
            return null;
        });
        this.publicWidgets = this.publicWidgets.filter((x) => removedWidgets.indexOf(x) < 0);
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
        const payload = ev.data;
        const service = this.env.services[payload.service];
        const result = service[payload.method].apply(service, payload.args || []);
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
    async _onWidgetsStartRequest(ev) {
        this.startFromEventHandler = true;
        try {
            await this._startWidgets(ev.data.$target, ev.data.options);
            ev.data.onSuccess?.();
        } catch (e) {
            ev.data.onFailure?.(e);
            if (!(e instanceof RPCError)) {
                throw e;
            }
        } finally {
            this.stopFromEventHandler = true;
        }
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
        // also stops interactions
        const targetEl = ev.data.$target ? ev.data.$target[0] : undefined;
        const publicInteractions = this.bindService("public.interactions");
        this.stopFromEventHandler = true;
        try {
            publicInteractions.stopInteractions(targetEl);
        } finally {
            this.stopFromEventHandler = false;
        }
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
 * This widget is important, because the tour manager needs a root widget in
 * order to work. The root widget must be a service provider with the ajax
 * service, so that the tour manager can let the server know when tours have
 * been consumed.
 */
export async function createPublicRoot(RootWidget) {
    await lazyloader.allScriptsLoaded;
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    Component.env = env;
    await env.services.public_component.mountComponents();
    const publicRoot = new RootWidget(null, env);
    const app = new App(MainComponentsContainer, {
        getTemplate,
        env,
        dev: env.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    const locale = pyToJsLocale(lang) || browser.navigator.language;
    Settings.defaultLocale = locale;
    const [root] = await Promise.all([
        app.mount(document.body),
        publicRoot.attachTo(document.body),
    ]);
    odoo.__WOWL_DEBUG__ = { root };
    return publicRoot;
}

export default { PublicRoot, createPublicRoot };
