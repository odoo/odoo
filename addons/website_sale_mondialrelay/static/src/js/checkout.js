import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/checkout";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

const WebsiteSaleCheckout = publicWidget.registry.WebsiteSaleCheckout;

// temporary for OnNoResultReturned bug
import {registry} from "@web/core/registry";
import {ThirdPartyScriptError} from "@web/core/errors/error_service";
const errorHandlerRegistry = registry.category("error_handlers");

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof ThirdPartyScriptError) {
        return true;
    }
}

WebsiteSaleCheckout.include({
    events: Object.assign({
        "click #btn_confirm_relay": "_onClickBtnConfirmRelay",
    }, WebsiteSaleCheckout.prototype.events),

    /**
     * Do not allow use same as delivery if delivery method mondialrelay or mondialrelay address is
     * selected.
     *
     * @override of `website_sale`
     */
    async start() {
        await this._super(...arguments);
        this.$('#use_delivery_as_billing_label')?.tooltip();
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * Loads Mondial Relay modal when method is selected and disable `use_delivery_as_billing` if
     * not available.
     *
     * @override
     */
    async _selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        await this._super(...arguments);
        if (checkedRadio.dataset.isMondialrelay) {
            if (this.use_delivery_as_billing_toggle?.checked) {
                // Uncheck use same as delivery and show the billing address row.
                this.use_delivery_as_billing_toggle.dispatchEvent(new MouseEvent('click'));
            }
            // Fetch delivery method data.
            const result = await this._setDeliveryMethod(checkedRadio.dataset.dmId);
            // Show mondialrelay modal.
            if (!this.modalMondialRelayEl) {
                this._loadMondialRelayModal(result);
            } else {
                this.modalMondialRelayEl
                    .querySelector("#btn_confirm_relay")
                    .classList.toggle("disabled", !result.mondial_relay.current);
                this.modalMondialRelayBS.show();
            }
        }
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * If mondialrelay address is chosen uncheck `use billing as delivery` and show billing address
     * row. Mondialrelay addresses are not allowed to be selected as billing.
     *
     * @override of `website_sale`
     */
    async _changeAddress(ev) {
        const newAddress = ev.currentTarget;
        if (newAddress.dataset.isMondialrelay && this.use_delivery_as_billing_toggle?.checked) {
            // Uncheck use same as delivery and show the billing address row.
            this.use_delivery_as_billing_toggle.dispatchEvent(new MouseEvent('click'));
        }
        await this._super(...arguments);
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * Disable use same as delivery when delivery method mondialrelay or mondialrelay address is
     * selected, otherwise enable it.
     *
     * @private
     * @return {void}
     */
    _adaptUseDeliveryAsBillingToggle() {
        if (this.use_delivery_as_billing_toggle) {
            const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
            const selectedDeliveryAddress = this._getSelectedAddress('delivery');
            const requireSeparateBillingAddress = (
                checkedRadio?.dataset.isMondialrelay
                || selectedDeliveryAddress?.dataset.isMondialrelay
            );
            this.use_delivery_as_billing_toggle.disabled = requireSeparateBillingAddress;
            const tooltip = Tooltip.getOrCreateInstance(document.querySelector("#use_delivery_as_billing_label"));
            if (requireSeparateBillingAddress) {
                tooltip.enable();
            } else {
                tooltip.disable();
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
        this.modalMondialRelayEl = document.querySelector("#modal_mondialrelay");
        this.modalMondialRelayEl
            .querySelector("#btn_confirm_relay")
            .addEventListener("click", this._onClickBtnConfirmRelay.bind(this));

        // load mondial relay script
        const iframeEL = document.createElement("iframe");

        iframeEL.onload = () => {
            const scriptJqueryEl = document.createElement("script");
            scriptJqueryEl.src =
                "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js";
            const divEl = document.createElement("div");
            divEl.setAttribute("id", "o_iframe_zone_widget");
            iframeEL.contentDocument.body.append(divEl);
            iframeEL.contentDocument.head.append(scriptJqueryEl);

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
                    this.modalMondialRelayEl
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

            scriptJqueryEl.onload = () => {
                const scriptMondialRelayEl = document.createElement("script");
                scriptMondialRelayEl.src =
                    "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js";
                iframeEL.contentDocument.head.append(scriptMondialRelayEl);
                scriptMondialRelayEl.onload = () => {
                    const zoneWidgetEl =
                        iframeEL.contentDocument.querySelector("#o_iframe_zone_widget");
                    const $ = iframeEL.contentWindow.$;
                    $(zoneWidgetEl).MR_ParcelShopPicker(params);
                    this.modalMondialRelayBS = new Modal(this.modalMondialRelayEl);
                    this.modalMondialRelayBS.show();
                    $(zoneWidgetEl).trigger("MR_RebindMap");
                };
            };
        };

        this.modalMondialRelayEl.querySelector("#o_zone_widget").append(iframeEL);
    },

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
        }).then(() => {
            location.reload(); // Update the addresses.
        });
    },
});
