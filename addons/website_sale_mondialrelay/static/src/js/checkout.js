/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/checkout";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

const websiteSaleCheckoutWidget = publicWidget.registry.websiteSaleCheckout;

// temporary for OnNoResultReturned bug
import {registry} from "@web/core/registry";
import {ThirdPartyScriptError} from "@web/core/errors/error_service";
const errorHandlerRegistry = registry.category("error_handlers");

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof ThirdPartyScriptError) {
        return true;
    }
}

websiteSaleCheckoutWidget.include({
    events: Object.assign({
        "click #btn_confirm_relay": "_onClickBtnConfirmRelay",
    }, websiteSaleCheckoutWidget.prototype.events),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Loads Mondial Relay the first time, else show it.
     *
     * @override
     */
    _updateAmountBadge(radio, result) {
        this._super(...arguments);
        if (result.mondial_relay) {
            if (!document.querySelector("#modal_mondialrelay")) {
                this._loadMondialRelayModal(result);
            } else {
                this.modal_mondialrelay
                    .querySelector("#btn_confirm_relay")
                    .classList.toggle("disabled", !result.mondial_relay.current);
                new Modal(this.modal_mondialrelay).show();
            }
        }
    },
    /**
     * This method render the modal, and inject it in dom with the Modial Relay Widgets script.
     * Once script loaded, it initialize the widget pre-configured with the information of result
     *
     * @private
     *
     * @param {Object} result: dict returned by call of _order_summary_values (python)
     */
    _loadMondialRelayModal: function (result) {
        // add modal to body and bind 'save' button
        document.body.append(renderToElement("website_sale_mondialrelay", {}));
        this.modal_mondialrelay = document.querySelector("#modal_mondialrelay");
        this.modal_mondialrelay
            .querySelector("#btn_confirm_relay")
            ?.addEventListener("click", this._onClickBtnConfirmRelay.bind(this));

        // load mondial relay script
        const iframeEL = document.createElement("iframe");
        iframeEL.src = "/website_sale_mondialrelay/get_mondialrelay";
        iframeEL.style.width = "100%";
        iframeEL.style.height = "950px";
        iframeEL.scrolling = "no";
        this.modal_mondialrelay.querySelector("#o_zone_widget").append(iframeEL);
        
        iframeEL.onload = () => {
            const iframeEl = document.querySelector("iframe");
            const script = document.createElement("script");
            script.src = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js";
            iframeEl.contentWindow.document.head.append(script);

            // instanciate MondialRelay widget
            const params = {
                Target: "", // required but handled by OnParcelShopSelected
                Brand: result.mondial_relay.brand,
                ColLivMod: result.mondial_relay.col_liv_mod,
                AllowedCountries: result.mondial_relay.allowed_countries,
                Country: result.mondial_relay.partner_country_code,
                PostCode: result.mondial_relay.partner_zip,
                Responsive: true,
                ShowResultsOnMap: true,
                AutoSelect: result.mondial_relay.current,
                OnParcelShopSelected: (RelaySelected) => {
                    this.lastRelaySelected = RelaySelected;
                    this.modal_mondialrelay
                        .querySelector("#btn_confirm_relay")
                        .classList.remove("disabled");
                },
                OnNoResultReturned: () => {
                    // HACK while Mondial Relay fix his bug
                    // disable corsErrorHandler for 10 seconds
                    // If code postal not valid, it will crash with Cors Error:
                    // Cannot read property 'on' of undefined at u.MR_FitBounds
                    const randInt = Math.floor(Math.random() * 100);
                    errorHandlerRegistry.add("corsIgnoredErrorHandler" + randInt, corsIgnoredErrorHandler, {sequence: 10});
                    setTimeout(function () {
                        errorHandlerRegistry.remove("corsIgnoredErrorHandler" + randInt);
                    }, 10000);
                },
            };
            script.onload = () =>  {
                const zoneWidgetEl = iframeEl.contentWindow.document.querySelector("#o_iframe_zone_widget");
                const $ = iframeEl.contentWindow.$;
                $(zoneWidgetEl).MR_ParcelShopPicker(params);
                new Modal(this.modal_mondialrelay).show();
                $(zoneWidgetEl).trigger("MR_RebindMap");
            }
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------


    /**
     * Update the shipping address on the order and refresh the UI.
     *
     * @private
     *
     */
    _onClickBtnConfirmRelay: function () {
        if (!this.lastRelaySelected) {
            return;
        }
        rpc('/website_sale_mondialrelay/update_shipping', {
            ...this.lastRelaySelected,
        }).then((o) => {
            if (document.querySelector('#address_on_payment')) {
                document.querySelector('#address_on_payment').innerHTML = o.address;
            }
            Modal.getOrCreateInstance(this.modal_mondialrelay).hide();
        });
    },
});
