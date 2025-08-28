import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { rpc } from '@web/core/network/rpc';
import { Checkout } from '@website_sale/interactions/checkout';

// temporary for OnNoResultReturned bug
import { registry } from '@web/core/registry';
import { ThirdPartyScriptError } from '@web/core/errors/error_service';
const errorHandlerRegistry = registry.category('error_handlers');

function corsIgnoredErrorHandler(env, error) {
    if (error instanceof ThirdPartyScriptError) {
        return true;
    }
}

patch(Checkout.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '#btn_confirm_relay': { 't-on-click': this.onClickBtnConfirmRelay.bind(this) },
        });
        this.mondialRelayModal = undefined;
        this.useDeliveryAsBillingTooltip = undefined;
        const useDeliveryAsBillingLabel = this.el.querySelector('#use_delivery_as_billing_label');
        if (useDeliveryAsBillingLabel) {
            this.useDeliveryAsBillingTooltip = window.Tooltip
                .getOrCreateInstance(useDeliveryAsBillingLabel);
            this.registerCleanup(() => this.useDeliveryAsBillingTooltip.dispose());
        }
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * If the Mondial Relay delivery method is selected, uncheck the "use delivery as billing"
     * toggle and show the Mondial Relay modal.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    async selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        await this.waitFor(super.selectDeliveryMethod(...arguments));
        if (checkedRadio.dataset.isMondialrelay) {
            if (this.useDeliveryAsBillingToggle?.checked) {
                // Uncheck the "use delivery as billing" toggle and show the billing address.
                this.useDeliveryAsBillingToggle.dispatchEvent(new MouseEvent('click'));
            }
            // Fetch delivery method data.
            const result = await this.waitFor(this._setDeliveryMethod(checkedRadio.dataset.dmId));
            // Show the Mondial Relay modal.
            if (!this.mondialRelayModal) {
                this._loadMondialRelayModal(result);
            } else {
                this.mondialRelayModal.querySelector('#btn_confirm_relay').classList.toggle(
                    'disabled', !result.mondial_relay.current
                );
                window.Modal.getOrCreateInstance(this.mondialRelayModal).show();
            }
        }
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * If a Mondial Relay address is selected, uncheck the "use delivery as billing" toggle and show
     * the billing address. Mondial Relay addresses can't be used as billing addresses.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    async changeAddress(ev) {
        const newAddress = ev.currentTarget;
        if (newAddress.dataset.isMondialrelay && this.useDeliveryAsBillingToggle?.checked) {
            // Uncheck the "use delivery as billing" toggle and show the billing address.
            this.useDeliveryAsBillingToggle.dispatchEvent(new MouseEvent('click'));
        }
        await this.waitFor(super.changeAddress(...arguments));
        this._adaptUseDeliveryAsBillingToggle();
    },

    /**
     * Disable the "use delivery as billing" toggle iff the Mondial Relay delivery method is
     * selected, or a Mondial Relay address is selected.
     *
     * @private
     * @return {void}
     */
    _adaptUseDeliveryAsBillingToggle() {
        if (this.useDeliveryAsBillingToggle) {
            const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
            const selectedDeliveryAddress = this._getSelectedAddress('delivery');
            const requireSeparateBillingAddress = (
                checkedRadio?.dataset.isMondialrelay
                || selectedDeliveryAddress?.dataset.isMondialrelay
            );
            this.useDeliveryAsBillingToggle.disabled = requireSeparateBillingAddress;
            requireSeparateBillingAddress
                ? this.useDeliveryAsBillingTooltip?.enable()
                : this.useDeliveryAsBillingTooltip?.disable();
        }
    },

    /**
     * Render the Mondial Relay modal, using the information from `result`, and insert it in the
     * DOM.
     *
     * @private
     * @param {Object} result data about the selected delivery method.
     */
    _loadMondialRelayModal(result) {
        // add modal to body and bind 'save' button
        this.renderAt('website_sale_mondialrelay', {}, document.querySelector('body'));
        this.mondialRelayModal = document.querySelector('#modal_mondialrelay');
        this.mondialRelayModal.querySelector('#btn_confirm_relay').addEventListener(
            'click', this.onClickBtnConfirmRelay.bind(this)
        );

        // load mondial relay script
        const script = document.createElement('script');
        script.src = "https://widget.mondialrelay.com/parcelshop-picker/jquery.plugin.mondialrelay.parcelshoppicker.min.js";
        script.onload = () => {
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
                    this.mondialRelayModal.querySelector('#btn_confirm_relay').classList.remove(
                        'disabled'
                    );
                },
                OnNoResultReturned: () => {
                    // HACK while Mondial Relay fix his bug
                    // disable corsErrorHandler for 10 seconds
                    // If code postal not valid, it will crash with Cors Error:
                    // Cannot read property 'on' of undefined at u.MR_FitBounds
                    const randInt = Math.floor(Math.random() * 100);
                    errorHandlerRegistry.add("corsIgnoredErrorHandler" + randInt, corsIgnoredErrorHandler, {sequence: 10});
                    this.waitForTimeout(
                        () => errorHandlerRegistry.remove("corsIgnoredErrorHandler" + randInt),
                        10000,
                    );
                },
            };
            const zoneWidget = this.mondialRelayModal.querySelector('#o_zone_widget');
            $(zoneWidget).MR_ParcelShopPicker(params);
            window.Modal.getOrCreateInstance(this.mondialRelayModal).show();
            zoneWidget.dispatchEvent(new Event('MR_RebindMap'));
        };
        document.body.appendChild(script);
    },

    /**
     * Update the shipping address on the order and refresh the UI.
     */
    async onClickBtnConfirmRelay() {
        if (!this.lastRelaySelected) return;
        await this.waitFor(rpc('/website_sale_mondialrelay/update_shipping', {
            ...this.lastRelaySelected,
        }));
        location.reload(); // Update the addresses.
    },
});
