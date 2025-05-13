import {_t} from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsiteSaleCheckout.include({
    events: Object.assign({}, publicWidget.registry.WebsiteSaleCheckout.prototype.events, {
        'click .js_wsc_delete_product': '_onClickDeleteProduct',
    }),

    async start() {
        await this._super(...arguments);
        this.deliveryAddressTitle = this.el.querySelector('[name="delivery_address_title"]');
        this.deliveryTitle = this.deliveryAddressTitle.textContent;
        this.inStoreTitle = _t('Contact Address');
        this._adaptDeliveryAddressRowTitle();

    },

    // #=== EVENT HANDLERS ===#

    async _selectDeliveryMethod(ev) {
        this._adaptDeliveryAddressRowTitle();
        await this._super(...arguments);
    },

    /**
     * Remove a product from the cart.
     *
     * @private
     * @param {Event} ev
     */
    async _onClickDeleteProduct(ev) {
        await rpc('/shop/cart/update', {
            line_id: parseInt(ev.target.dataset.lineId, 10),
            product_id: parseInt(ev.target.dataset.productId, 10),
            quantity: 0,
        });
        window.location.reload();  // Reload all cart values.
    },

    // #=== DOM MANIPULATION ===#

    _adaptDeliveryAddressRowTitle() {
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        if (checkedRadio.dataset.deliveryType === 'in_store') {
            this.deliveryAddressTitle.textContent = this.inStoreTitle;
        } else {
            this.deliveryAddressTitle.textContent = this.deliveryTitle;
        }
    },

    /**
     * Remove a warning if available pickup location is selected.
     *
     * @override method from `@website_sale/js/checkout`
     */
    _updatePickupLocation(button, location, jsonLocation) {
        this._super.apply(this, arguments);
        const dmContainer = this._getDeliveryMethodContainer(button);
        const radio = dmContainer.querySelector('[name="o_delivery_radio"]');
        if (radio.dataset.deliveryType === 'in_store') {
            dmContainer.querySelector('[name="unavailable_products_warning"]')?.remove();
        }
    },

    /**
     * Return false if there is a warning message, otherwise return the result of the parent method
     * call.
     *
     * @override method from `@website_sale/js/checkout`
     */
    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) {  // If there are no delivery methods.
            return this._super.apply(this, arguments);  // Skip override.
        }
        const checkedRadio = this.el.querySelector('input[name="o_delivery_radio"]:checked');
        let hasWarning = false;
        if (checkedRadio) {
            const deliveryContainer = this._getDeliveryMethodContainer(checkedRadio);
            hasWarning = (
                checkedRadio.dataset.deliveryType === 'in_store'
                && deliveryContainer.querySelector('[name="unavailable_products_warning"]')
            );
        }
        return this._super.apply(this, arguments) && !hasWarning;
    },

    /**
     *  Override to disable the toggle when pick up in store is selected.
     *
     */
    _isUseDeliveryAsBillingDisabled() {
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        return this._super(...arguments) || checkedRadio?.dataset.deliveryType === 'in_store';
    },

    /**
     * Also hide the warning message, if any.
     *
     * @override method from `@website_sale/js/checkout`
     */
    _hidePickupLocation() {
        this._super.apply(this, arguments);
        const warning = this.el.querySelector('[name="unavailable_products_warning"]');
        if (warning) {
            warning.classList.add('d-none');
        }
    },

    // #=== DELIVERY FLOW ===#

    /**
     * Display a warning if any when selecting an in_store delivery method.
     *
     * @override method from `@website_sale/js/checkout`
     */
    async _showPickupLocation(radio) {
        this._super.apply(this, arguments);
        if (radio.dataset.deliveryType === 'in_store') {
            const dmContainer = this._getDeliveryMethodContainer(radio);
            const warning = dmContainer.querySelector('[name="unavailable_products_warning"]');
            if (warning) {
                warning.classList.remove('d-none');
            }
        }
    },

});
