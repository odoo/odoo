/** @odoo-module */

import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import publicRootData from '@web/legacy/js/public/public_root';
import "@website/libs/zoomodoo/zoomodoo";
import { pick } from "@web/core/utils/objects";

import { markup } from "@odoo/owl";

export const WebsiteRoot = publicRootData.PublicRoot.extend({
    events: Object.assign({}, publicRootData.PublicRoot.prototype.events || {}, {
        'click .js_change_lang': '_onLangChangeClick',
        'click .js_publish_management .js_publish_btn': '_onPublishBtnClick',
        'shown.bs.modal': '_onModalShown',
    }),
    custom_events: Object.assign({}, publicRootData.PublicRoot.prototype.custom_events || {}, {
        'gmap_api_request': '_onGMapAPIRequest',
        'gmap_api_key_request': '_onGMapAPIKeyRequest',
        'ready_to_clean_for_save': '_onWidgetsStopRequest',
        'seo_object_request': '_onSeoObjectRequest',
        'will_remove_snippet': '_onWidgetsStopRequest',
    }),

    /**
     * @override
     */
    init() {
        this.isFullscreen = false;
        this.rpc = this.bindService("rpc");
        this.notification = this.bindService("notification");
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start: function () {
        // Enable magnify on zommable img
        this.$('.zoomable img[data-zoom]').zoomOdoo();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getContext: function (context) {
        var html = document.documentElement;
        return Object.assign({
            'website_id': html.getAttribute('data-website-id') | 0,
        }, this._super.apply(this, arguments));
    },
    /**
     * @override
     */
    _getExtraContext: function (context) {
        var html = document.documentElement;
        return Object.assign({
            'editable': !!(html.dataset.editable || $('[data-oe-model]').length), // temporary hack, this should be done in python
            'translatable': !!html.dataset.translatable,
            'edit_translations': !!html.dataset.edit_translations,
        }, this._super.apply(this, arguments));
    },
    /**
     * @private
     * @param {boolean} [refetch=false]
     */
    async _getGMapAPIKey(refetch) {
        if (refetch || !this._gmapAPIKeyProm) {
            this._gmapAPIKeyProm = new Promise(async resolve => {
                const data = await this.rpc('/website/google_maps_api_key');
                resolve(JSON.parse(data).google_maps_api_key || '');
            });
        }
        return this._gmapAPIKeyProm;
    },
    /**
     * @override
     */
    _getPublicWidgetsRegistry: function (options) {
        var registry = this._super.apply(this, arguments);
        if (options.editableMode) {
            const toPick = Object.keys(registry).filter((key) => {
                const PublicWidget = registry[key];
                return !PublicWidget.prototype.disabledInEditableMode;
            });
            return pick(registry, ...toPick);
        }
        return registry;
    },
    /**
     * @private
     * @param {boolean} [editableMode=false]
     * @param {boolean} [refetch=false]
     */
    async _loadGMapAPI(editableMode, refetch) {
        // Note: only need refetch to reload a configured key and load the
        // library. If the library was loaded with a correct key and that the
        // key changes meanwhile... it will not work but we can agree the user
        // can bother to reload the page at that moment.
        if (refetch || !this._gmapAPILoading) {
            this._gmapAPILoading = new Promise(async resolve => {
                const key = await this._getGMapAPIKey(refetch);

                window.odoo_gmap_api_post_load = (async function odoo_gmap_api_post_load() {
                    await this._startWidgets($("section.s_google_map"), {editableMode: editableMode});
                    resolve(key);
                }).bind(this);

                if (!key) {
                    if (!editableMode && session.is_admin) {
                        const message = _t("Cannot load google map.");
                        const urlTitle = _t("Check your configuration.");
                        this.notification.add(
                            markup(`<div>
                                <span>${message}</span><br/>
                                <a href="/web#action=website.action_website_configuration">${urlTitle}</a>
                            </div>`),
                            { type: 'warning', sticky: true }
                        );
                    }
                    resolve(false);
                    this._gmapAPILoading = false;
                    return;
                }
                await loadJS(`https://maps.googleapis.com/maps/api/js?v=3.exp&libraries=places&callback=odoo_gmap_api_post_load&key=${encodeURIComponent(key)}`);
            });
        }
        return this._gmapAPILoading;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onWidgetsStartRequest: function (ev) {
        ev.data.options = Object.assign({}, ev.data.options || {});
        ev.data.options.editableMode = ev.data.editableMode;
        this._super.apply(this, arguments);
    },
    /**
     * @todo review
     * @private
     */
    _onLangChangeClick: function (ev) {
        ev.preventDefault();
        // In edit mode, the client action redirects the iframe to the correct
        // location with the chosen language.
        if (document.body.classList.contains('editor_enable')) {
            return;
        }
        var $target = $(ev.currentTarget);
        // retrieve the hash before the redirect
        var redirect = {
            lang: encodeURIComponent($target.data('url_code')),
            url: encodeURIComponent($target.attr('href').replace(/[&?]edit_translations[^&?]+/, '')),
            hash: encodeURIComponent(window.location.hash)
        };
        window.location.href = `/website/lang/${redirect.lang}?r=${redirect.url}${redirect.hash}`;
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    async _onGMapAPIRequest(ev) {
        ev.stopPropagation();
        const apiKey = await this._loadGMapAPI(ev.data.editableMode, ev.data.refetch);
        ev.data.onSuccess(apiKey);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    async _onGMapAPIKeyRequest(ev) {
        ev.stopPropagation();
        const apiKey = await this._getGMapAPIKey(ev.data.refetch);
        ev.data.onSuccess(apiKey);
    },
    /**
    /**
     * Checks information about the page SEO object.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSeoObjectRequest: function (ev) {
        var res = this._unslugHtmlDataObject('seo-object');
        ev.data.callback(res);
    },
    /**
     * Returns a model/id object constructed from html data attribute.
     *
     * @private
     * @param {string} dataAttr
     * @returns {Object} an object with 2 keys: model and id, or null
     * if not found
     */
    _unslugHtmlDataObject: function (dataAttr) {
        var repr = $('html').data(dataAttr);
        var match = repr && repr.match(/(.+)\((\d+),(.*)\)/);
        if (!match) {
            return null;
        }
        return {
            model: match[1],
            id: match[2] | 0,
        };
    },
    /**
     * @todo review
     * @private
     */
    _onPublishBtnClick: function (ev) {
        ev.preventDefault();
        if (document.body.classList.contains('editor_enable')) {
            return;
        }

        var $data = $(ev.currentTarget).parents(".js_publish_management:first");
        this.rpc($data.data('controller') || '/website/publish', {
            id: +$data.data('id'),
            object: $data.data('object'),
        })
        .then(function (result) {
            $data.toggleClass("css_published", result).toggleClass("css_unpublished", !result);
            $data.find('input').prop("checked", result);
            $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onModalShown: function (ev) {
        $(ev.target).addClass('modal_shown');
    },
});

export default {
    WebsiteRoot: WebsiteRoot,
};
