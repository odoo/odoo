import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { rpc } from '@web/core/network/rpc';
import { Checkout } from '@website_sale/interactions/checkout';

patch(Checkout.prototype, {
     setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '.js_wsc_update_product_qty': { 't-on-click': this.onClickUpdateProductQty.bind(this) },
        });
    },

    /**
     * Remove a product from the cart or update its quantity to match the available quantity.
     *
     * @param {Event} ev
     */
    async onClickUpdateProductQty(ev) {
        await this.waitFor(rpc('/shop/cart/update', {
            line_id: parseInt(ev.currentTarget.dataset.lineId, 10),
            product_id: parseInt(ev.currentTarget.dataset.productId, 10),
            quantity: parseInt(ev.currentTarget.dataset.availableQty || 0, 10),
        }));
        window.location.reload(); // Reload all cart values.
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Add country selector specific data to location selector.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _prepareLocationDialogData(dataset) {
        const {
            countryCode,
            deliveryMethodId,
            deliveryMethodType,
        } = dataset;
        const superDialogData = super._prepareLocationDialogData(dataset);
        if (deliveryMethodType === 'in_store') {
            return {
                ...superDialogData,
                countryCode: countryCode,
                deliveryMethodId: parseInt(deliveryMethodId),
                deliveryMethodType: deliveryMethodType,
            };
        }
        return superDialogData;

    },

    /**
     * Reload the page after setting the pickup location if the delivery method is in_store to
     * update the warning message.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _updatePickupLocation(button, locationData, jsonLocation) {
        super._updatePickupLocation(...arguments);
        const dmContainer = this._getDeliveryMethodContainer(button);
        const radio = dmContainer.querySelector('[name="o_delivery_radio"]');
        if (radio.dataset.deliveryType === 'in_store') {
            location.reload();
        }
    },

    /**
     * Return false if there is a warning message, otherwise return the result of the parent method
     * call.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) { // If there are no delivery methods.
            return super._isDeliveryMethodReady(...arguments); // Skip override.
        }
        const checkedRadio = this._getSelectedDeliveryRadio();
        let hasWarning = false;
        if (checkedRadio) {
            const deliveryContainer = this._getDeliveryMethodContainer(checkedRadio);
            hasWarning = (
                checkedRadio.dataset.deliveryType === 'in_store'
                && deliveryContainer.querySelector('[name="unavailable_products_warning"]')
            );
        }
        return super._isDeliveryMethodReady(...arguments) && !hasWarning;
    },

    /**
     * Also hide the warning message, if any.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    _hidePickupLocation() {
        super._hidePickupLocation(...arguments);
        const warning = this.el.querySelector('[name="unavailable_products_warning"]');
        if (warning) {
            warning.classList.add('d-none');
        }
    },

    // #=== DELIVERY FLOW ===#

    /**
     * Display a warning if any when selecting an in_store delivery method.
     *
     * @override method from `@website_sale/interactions/checkout`
     */
    async _showPickupLocation(radio) {
        super._showPickupLocation(...arguments);
        if (radio.dataset.deliveryType === 'in_store') {
            const dmContainer = this._getDeliveryMethodContainer(radio);
            const warning = dmContainer.querySelector('[name="unavailable_products_warning"]');
            if (warning) {
                warning.classList.remove('d-none');
            }
        }
    },
});
