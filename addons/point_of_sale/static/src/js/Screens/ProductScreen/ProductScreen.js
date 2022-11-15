odoo.define('point_of_sale.ProductScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { onChangeOrder, useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { isConnectionError, posbus } = require('point_of_sale.utils');
    const { useState, onMounted } = owl.hooks;
    const { parse } = require('web.field_utils');

    class ProductScreen extends ControlButtonsMixin(PosComponent) {
        constructor() {
            super(...arguments);
            useListener('update-selected-orderline', this._updateSelectedOrderline);
            useListener('new-orderline-selected', this._newOrderlineSelected);
            useListener('set-numpad-mode', this._setNumpadMode);
            useListener('click-product', this._clickProduct);
            useListener('click-customer', this._onClickCustomer);
            useListener('click-pay', this._onClickPay);
            useBarcodeReader({
                product: this._barcodeProductAction,
                weight: this._barcodeProductAction,
                price: this._barcodeProductAction,
                client: this._barcodeClientAction,
                discount: this._barcodeDiscountAction,
                error: this._barcodeErrorAction,
            })
            onChangeOrder(null, (newOrder) => newOrder && this.render());
            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                triggerAtInput: 'update-selected-orderline',
                useWithBarcode: true,
            });
            // Call `reset` when the `onMounted` callback in `NumberBuffer.use` is done.
            // We don't do this in the `mounted` lifecycle method because it is called before
            // the callbacks in `onMounted` hook.
            onMounted(() => NumberBuffer.reset());
            this.state = useState({
                numpadMode: 'quantity',
                mobile_pane: this.props.mobile_pane || 'right',
            });
        }
        mounted() {
            posbus.trigger('start-cash-control');
            this.env.pos.on('change:selectedClient', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:selectedClient', null, this);
        }
        /**
         * To be overridden by modules that checks availability of
         * connected scale.
         * @see _onScaleNotAvailable
         */
        get isScaleAvailable() {
            return true;
        }
        get client() {
            return this.env.pos.get_client();
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        async _getAddProductOptions(product, base_code) {
            let price_extra = 0.0;
            let draftPackLotLines, weight, description, packLotLinesToEdit;

            if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                  .filter((attr) => attr !== undefined);
                let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                    product: product,
                    attributes: attributes,
                });

                if (confirmed) {
                    description = payload.selected_attributes.join(', ');
                    price_extra += payload.price_extra;
                } else {
                    return;
                }
            }

            // Gather lot information if required.
            if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
                const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                if (isAllowOnlyOneLot) {
                    packLotLinesToEdit = [];
                } else {
                    const orderline = this.currentOrder
                        .get_orderlines()
                        .filter(line => !line.get_discount())
                        .find(line => line.product.id === product.id);
                    if (orderline) {
                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                    } else {
                        packLotLinesToEdit = [];
                    }
                }
                const { confirmed, payload } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Lot/Serial Number(s) Required'),
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (confirmed) {
                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = payload.newArray
                        .filter(item => !item.id)
                        .map(item => ({ lot_name: item.text }));

                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
                    // We don't proceed on adding product.
                    return;
                }
            }

            // Take the weight if necessary.
            if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                // Show the ScaleScreen to weigh the product.
                if (this.isScaleAvailable) {
                    const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                        product,
                    });
                    if (confirmed) {
                        weight = payload.weight;
                    } else {
                        // do not add the product;
                        return;
                    }
                } else {
                    await this._onScaleNotAvailable();
                }
            }

            if (base_code && this.env.pos.db.product_packaging_by_barcode[base_code.code]) {
                weight = this.env.pos.db.product_packaging_by_barcode[base_code.code].qty;
            }

            return { draftPackLotLines, quantity: weight, description, price_extra };
        }
        async _clickProduct(event) {
            if (!this.currentOrder) {
                this.env.pos.add_new_order();
            }
            const product = event.detail;
            const options = await this._getAddProductOptions(product);
            // Do not add product if options is undefined.
            if (!options) return;
            // Add the product after having the extra information.
            await this.currentOrder.add_product(product, options);
            NumberBuffer.reset();
        }
        _setNumpadMode(event) {
            const { mode } = event.detail;
            NumberBuffer.capture();
            NumberBuffer.reset();
            this.state.numpadMode = mode;
        }
        async _updateSelectedOrderline(event) {
            if(this.state.numpadMode === 'quantity' && this.env.pos.disallowLineQuantityChange()) {
                let order = this.env.pos.get_order();
                if(!order.orderlines.length)
                    return;
                let selectedLine = order.get_selected_orderline();
                let lastId = order.orderlines.last().cid;
                let currentQuantity = this.env.pos.get_order().get_selected_orderline().get_quantity();

                if(selectedLine.noDecrease) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Invalid action'),
                        body: this.env._t('You are not allowed to change this quantity'),
                    });
                    return;
                }
                const parsedInput = event.detail.buffer && parse.float(event.detail.buffer) || 0;
                if(lastId != selectedLine.cid)
                    await this._showDecreaseQuantityPopup();
                else if(currentQuantity < parsedInput)
                    this._setValue(event.detail.buffer);
                else if(parsedInput < currentQuantity)
                    await this._showDecreaseQuantityPopup();
            } else {
                let { buffer } = event.detail;
                let val = buffer === null ? 'remove' : buffer;
                this._setValue(val);
            }
            if (this.env.pos.config.iface_customer_facing_display) {
                this.env.pos.send_current_order_to_customer_facing_display();
            }
        }
        async _newOrderlineSelected() {
            NumberBuffer.reset();
            this.state.numpadMode = 'quantity';
        }
        _setValue(val) {
            if (this.currentOrder.get_selected_orderline()) {
                if (this.state.numpadMode === 'quantity') {
                    const result = this.currentOrder.get_selected_orderline().set_quantity(val);
                    if (!result) NumberBuffer.reset();
                } else if (this.state.numpadMode === 'discount') {
                    this.currentOrder.get_selected_orderline().set_discount(val);
                } else if (this.state.numpadMode === 'price') {
                    var selected_orderline = this.currentOrder.get_selected_orderline();
                    selected_orderline.price_manually_set = true;
                    selected_orderline.set_unit_price(val);
                }
            }
        }
        async _barcodeProductAction(code) {
            let product = this.env.pos.db.get_product_by_barcode(code.base_code);
            if (!product) {
                // find the barcode in the backend
                let foundProductIds = [];
                try {
                    foundProductIds = await this.rpc({
                        model: 'product.product',
                        method: 'search',
                        args: [[['barcode', '=', code.base_code]]],
                        context: this.env.session.user_context,
                    });
                } catch (error) {
                    if (isConnectionError(error)) {
                        return this.showPopup('OfflineErrorPopup', {
                            title: this.env._t('Network Error'),
                            body: this.env._t("Product is not loaded. Tried loading the product from the server but there is a network error."),
                        });
                    } else {
                        throw error;
                    }
                }
                if (foundProductIds.length) {
                    await this.env.pos._addProducts(foundProductIds);
                    // assume that the result is unique.
                    product = this.env.pos.db.get_product_by_id(foundProductIds[0]);
                } else {
                    return this._barcodeErrorAction(code);
                }
            }
            const options = await this._getAddProductOptions(product, code);
            // Do not proceed on adding the product when no options is returned.
            // This is consistent with _clickProduct.
            if (!options) return;

            // update the options depending on the type of the scanned code
            if (code.type === 'price') {
                Object.assign(options, {
                    price: code.value,
                    extras: {
                        price_manually_set: true,
                    },
                });
            } else if (code.type === 'weight') {
                Object.assign(options, {
                    quantity: code.value,
                    merge: false,
                });
            } else if (code.type === 'discount') {
                Object.assign(options, {
                    discount: code.value,
                    merge: false,
                });
            }
            await this.currentOrder.add_product(product,  options);
        }
        _barcodeClientAction(code) {
            const partner = this.env.pos.db.get_partner_by_barcode(code.code);
            if (partner) {
                if (this.currentOrder.get_client() !== partner) {
                    this.currentOrder.set_client(partner);
                    this.currentOrder.set_pricelist(
                        _.findWhere(this.env.pos.pricelists, {
                            id: partner.property_product_pricelist[0],
                        }) || this.env.pos.default_pricelist
                    );
                }
                return true;
            }
            this._barcodeErrorAction(code);
            return false;
        }
        _barcodeDiscountAction(code) {
            var last_orderline = this.currentOrder.get_last_orderline();
            if (last_orderline) {
                last_orderline.set_discount(code.value);
            }
        }
        // IMPROVEMENT: The following two methods should be in PosScreenComponent?
        // Why? Because once we start declaring barcode actions in different
        // screens, these methods will also be declared over and over.
        _barcodeErrorAction(code) {
            this.showPopup('ErrorBarcodePopup', { code: this._codeRepr(code) });
        }
        _codeRepr(code) {
            if (code.code.length > 32) {
                return code.code.substring(0, 29) + '...';
            } else {
                return code.code;
            }
        }
        async _displayAllControlPopup() {
            await this.showPopup('ControlButtonPopup', {
                controlButtons: this.controlButtons
            });
        }
        /**
         * override this method to perform procedure if the scale is not available.
         * @see isScaleAvailable
         */
        async _onScaleNotAvailable() {}
        async _showDecreaseQuantityPopup() {
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: 0,
                title: this.env._t('Set the new quantity'),
            });
            let newQuantity = inputNumber && inputNumber !== "" ? parse.float(inputNumber) : null;
            if (confirmed && newQuantity !== null) {
                let order = this.env.pos.get_order();
                let selectedLine = this.env.pos.get_order().get_selected_orderline();
                let currentQuantity = selectedLine.get_quantity()
                if(selectedLine.is_last_line() && currentQuantity === 1 && newQuantity < currentQuantity)
                    selectedLine.set_quantity(newQuantity);
                else if(newQuantity >= currentQuantity)
                    selectedLine.set_quantity(newQuantity);
                else {
                    let newLine = selectedLine.clone();
                    let decreasedQuantity = currentQuantity - newQuantity
                    newLine.order = order;

                    newLine.set_quantity( - decreasedQuantity, true);
                    order.add_orderline(newLine);
                }
            }
        }
        async _onClickCustomer() {
            // IMPROVEMENT: This code snippet is very similar to selectClient of PaymentScreen.
            const currentClient = this.currentOrder.get_client();
            if (currentClient && this.currentOrder.getHasRefundLines()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Can't change customer"),
                    body: _.str.sprintf(
                        this.env._t(
                            "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer."
                        ),
                        currentClient.name
                    ),
                });
                return;
            }
            const { confirmed, payload: newClient } = await this.showTempScreen(
                'ClientListScreen',
                { client: currentClient }
            );
            if (confirmed) {
                this.currentOrder.set_client(newClient);
                this.currentOrder.updatePricelist(newClient);
            }
        }
        async _onClickPay() {
            if (this.env.pos.get_order().orderlines.any(line => line.get_product().tracking !== 'none' && !line.has_valid_product_lot() && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots))) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Some Serial/Lot Numbers are missing'),
                    body: this.env._t('You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?'),
                    confirmText: this.env._t('Yes'),
                    cancelText: this.env._t('No')
                });
                if (confirmed) {
                    this.showScreen('PaymentScreen');
                }
            } else {
                this.showScreen('PaymentScreen');
            }
        }
        switchPane() {
            this.state.mobile_pane = this.state.mobile_pane === "left" ? "right" : "left";
        }
    }
    ProductScreen.template = 'ProductScreen';

    Registries.Component.add(ProductScreen);

    return ProductScreen;
});
