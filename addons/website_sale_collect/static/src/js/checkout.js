import { rpc } from '@web/core/network/rpc';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsiteSaleCheckout.include({
    events: Object.assign({}, publicWidget.registry.WebsiteSaleCheckout.prototype.events, {
        'click .js_wsc_delete_product': '_onClickDeleteProduct',
        'click [name="edit_pickup_address"]': '_selectPickupLocation',
    }),

    // #=== EVENT HANDLERS ===#

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

    /**
     * Remove a warning if available pickup location is selected.
     *
     * @override method from `@website_sale/js/checkout`
     */
    _updatePickupLocation(button, location, jsonLocation) {
        this._super.apply(this, arguments);
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        if(checkedRadio.dataset.deliveryType == 'in_store'){
            const dmContainer = this._getDeliveryMethodContainer(checkedRadio);
            dmContainer.querySelector('[name="unavailable_products_warning"]')?.remove();
            const pickupLocationContainer = this._getPickupLocationContainer(checkedRadio);
            const pickupLocationButton = pickupLocationContainer.querySelector('span[name="o_pickup_location_selector"]');
            pickupLocationButton.dataset.locationId = location.id;
            pickupLocationButton.dataset.zipCode = location.zip_code;
            pickupLocationButton.dataset.pickupLocationData = jsonLocation;
            pickupLocationButton.classList.remove('border-0');
            pickupLocationButton.classList.add('bg-primary', 'border', 'border-primary', 'js_change_address');
            pickupLocationButton.querySelector('[name="edit_pickup_address"]').classList.remove('d-none');
            pickupLocationContainer.querySelector('a[name="o_pickup_location_selector"]')?.remove();
            pickupLocationContainer.querySelector('span[name="o_pickup_location_selector"]')?.classList.remove('d-none');

        }
    },

    _updatePickupLocationAddress(container, location){
        container.innerHTML = "";
        container.appendChild(document.createTextNode(location.street));
        container.appendChild(document.createElement('br'));
        container.appendChild(document.createTextNode(location.city + ' ' + location.zip_code));
        container.appendChild(document.createElement('br'));
        container.appendChild(document.createTextNode(location.country));
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
        const addressRow = document.querySelector("div[name='address_row']");
        if (radio.dataset.deliveryType === 'in_store') {
            addressRow.classList.add('d-none');
            const dmContainer = this._getDeliveryMethodContainer(radio);
            const warning = dmContainer.querySelector('[name="unavailable_products_warning"]');
            if (warning) {
                warning.classList.remove('d-none');
        }
        }else{
            addressRow.classList.remove('d-none');
        }
        await this._super.apply(this, arguments);
    },

    async _prepareDeliveryMethods() {
        await this._super.apply(this, arguments);
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        if(checkedRadio && checkedRadio.dataset.deliveryType === 'in_store'){
            document.querySelector('div[name="address_row"]').classList.add('d-none');
            this._getPickupLocationContainer(checkedRadio).classList.remove('d-none');
        }
    },

    _getPickupLocationContainer(radio){
        if (radio.dataset.deliveryType === 'in_store'){
            return document.querySelector('#delivery_address_row [name="o_pickup_location"]');
        }else{
            this._super.apply(this, arguments);
        }
    },

});
