odoo.define('website.s_cookiesbar', function (require) {
'use strict';

const {qweb, _t, _lt} = require('web.core');
const config = require('web.config');
const publicWidget = require('web.public.widget');
const utils = require('web.utils');
const Dialog = require('web.Dialog');
const PopupWidget = require('website.s_popup');

const CookieWidget = PopupWidget.extend({
    selector: '.s_cookiesbar',
    xmlDependencies: ['/website/static/src/snippets/s_cookiesbar/000.xml'],

    supportedType: ["required", "preference", "marketing", "statistic"],
    nbDays: 365,

    events: Object.assign({}, PopupWidget.prototype.events, {
        'click .js_cookie_consent_config': '_onConfigConsentClick',
        'click .js_cookie_consent_all': '_onConfigConsentAcceptAllClick',
    }),

    /**
     * @override
     */
    start: function () {
        $("a[href='#cookies-consent']").on('click', () => this._onConfigConsentClick());
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onConfigConsentClick: function () {
        return new Promise(resolve => {
            const dialog = new Dialog(this, {
                size: 'medium',
                title: _t("Cookies Consents"),
                buttons: [
                    {text: _t("Accept All"), classes: 'btn-primary', close: true, click: async (ev) => {
                        const acceptAll = Object.fromEntries(this.supportedType.map((type) => [type, true]));
                        utils.set_cookie('cookies_consent', JSON.stringify(acceptAll), this.nbDays * 24 * 60 * 60, 'required');
                        this._hidePopup();
                    }},{text: _t("Accept chosen"), classes: 'btn-outline-secondary', close: true, click: async (ev) => {
                        const accept = Object.fromEntries(
                            this.supportedType.map((type) => [type, $("#cookie_consent_" + type).is(':checked')])
                        );
                        utils.set_cookie('cookies_consent', JSON.stringify(accept), this.nbDays * 24 * 60 * 60, 'required');
                        this._hidePopup();
                    }},
                    {text: _t("Cancel"), close: true}
                ],
                $content: $(qweb.render('website.cookies_consent_config_modal', {
                    actual_consent: JSON.parse(utils.get_cookie('cookies_consent') || '{}'),
                })),
            });
            dialog.open();
        });
    },
    /**
     * @private
     */
    _onConfigConsentAcceptAllClick: function () {
        const acceptAll = Object.fromEntries(this.supportedType.map((type) => [type, true]))
        utils.set_cookie('cookies_consent', JSON.stringify(acceptAll), this.nbDays * 24 * 60 * 60, 'required');
        this._hidePopup();
    },
});


publicWidget.registry.cookies_bar = CookieWidget;

return CookieWidget;
});
