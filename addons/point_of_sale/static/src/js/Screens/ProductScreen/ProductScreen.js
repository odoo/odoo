odoo.define('point_of_sale.ProductScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { isConnectionError } = require('point_of_sale.utils');
    const { parse } = require('web.field_utils');
    const { _lt } = require('@web/core/l10n/translation');

    const { onMounted, useState } = owl;

    class ProductScreen extends ControlButtonsMixin(PosComponent) {
        setup() {
            super.setup();
            useListener('update-selected-orderline', (...args) => {
                if (!this.env.pos.tempScreenIsShown) this._updateSelectedOrderline(...args);
            });
            useListener('select-line', this._selectLine);
            useListener('set-numpad-mode', this._setNumpadMode);
            useListener('click-product', this._clickProduct);
            useListener('click-partner', this.onClickPartner);
            useListener('click-pay', this._onClickPay);
            useBarcodeReader({
                product: this._barcodeProductAction,
                quantity: this._barcodeProductAction,
                weight: this._barcodeProductAction,
                price: this._barcodeProductAction,
                client: this._barcodePartnerAction,
                discount: this._barcodeDiscountAction,
                error: this._barcodeErrorAction,
                gs1: this._barcodeGS1Action,
            });
            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                triggerAtInput: 'update-selected-orderline',
                useWithBarcode: true,
            });
            onMounted(this.onMounted);
            // Call `reset` when the `onMounted` callback in `NumberBuffer.use` is done.
            // We don't do this in the `mounted` lifecycle method because it is called before
            // the callbacks in `onMounted` hook.
            onMounted(() => NumberBuffer.reset());
            this.state = useState({
                mobile_pane: this.props.mobile_pane || 'right',
            });
        }
        onMounted() {
            this.env.posbus.trigger('start-cash-control');
        }
        /**
         * To be overridden by modules that checks availability of
         * connected scale.
         * @see _onScaleNotAvailable
         */
        get isScaleAvailable() {
            return true;
        }
        get partner() {
            return this.currentOrder ? this.currentOrder.get_partner() : null;
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        async _getAddProductOptions(product, code) {
            let price_extra = 0.0;
            let draftPackLotLines, weight, description, packLotLinesToEdit;

            if (_.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let { confirmed, payload } = await this._openProductConfiguratorPopup(product);
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
                // if the lot information exists in the barcode, we don't need to ask it from the user.
                if (code && code.type === 'lot') {
                    // consider the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        packLotLinesToEdit.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = [
                        { lot_name: code.code },
                    ];
                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
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

            if (code && this.env.pos.db.product_packaging_by_barcode[code.code]) {
                weight = this.env.pos.db.product_packaging_by_barcode[code.code].qty;
            }

            return { draftPackLotLines, quantity: weight, description, price_extra };
        }
        async _openProductConfiguratorPopup(product) {
            let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                  .filter((attr) => attr !== undefined);

            // avoid opening the popup when each attribute has only one available option.
            if (_.some(attributes, (attribute) => attribute.values.length > 1 || _.some(attribute.values, (value) => value.is_custom))) {
                return await this.showPopup('ProductConfiguratorPopup', {
                    product: product,
                    attributes: attributes,
                });
            };

            let selected_attributes = [];
            let price_extra = 0.0;

            attributes.forEach((attribute) => {
                selected_attributes.push(attribute.values[0].name);
                price_extra += attribute.values[0].price_extra;
            });

            return {
                confirmed: true,
                payload: {
                    selected_attributes,
                    price_extra,
                }
            };
        }
        async _addProduct(product, options) {
            this.currentOrder.add_product(product, options);
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
            await this._addProduct(product, options);
            NumberBuffer.reset();
        }
        _setNumpadMode(event) {
            const { mode } = event.detail;
            NumberBuffer.capture();
            NumberBuffer.reset();
            this.env.pos.numpadMode = mode;
        }
        _selectLine() {
            NumberBuffer.reset();
        }
        async _updateSelectedOrderline(event) {
            const order = this.env.pos.get_order();
            const selectedLine = order.get_selected_orderline();
            // This validation must not be affected by `disallowLineQuantityChange`
            if (selectedLine && selectedLine.isTipLine() && this.env.pos.numpadMode !== "price") {
                /**
                 * You can actually type numbers from your keyboard, while a popup is shown, causing
                 * the number buffer storage to be filled up with the data typed. So we force the
                 * clean-up of that buffer whenever we detect this illegal action.
                 */
                NumberBuffer.reset();
                if (event.detail.key === "Backspace") {
                    this._setValue("remove");
                } else {
                    this.showPopup("ErrorPopup", {
                        title: this.env._t("Cannot modify a tip"),
                        body: this.env._t("Customer tips, cannot be modified directly"),
                    });
                }
            } else if (this.env.pos.numpadMode === 'quantity' && this.env.pos.disallowLineQuantityChange()) {
                if(!order.orderlines.length)
                    return;
                let orderlines = order.orderlines;
                let lastId = orderlines.length !== 0 && orderlines.at(orderlines.length - 1).cid;
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
                    this._showDecreaseQuantityPopup();
                else if(currentQuantity < parsedInput)
                    this._setValue(event.detail.buffer);
                else if(parsedInput < currentQuantity)
                    this._showDecreaseQuantityPopup();
            } else {
                let { buffer } = event.detail;
                let val = buffer === null ? 'remove' : buffer;
                this._setValue(val);
                if (val == 'remove') {
                    NumberBuffer.reset();
                    this.env.pos.numpadMode = 'quantity';
                }
            }
        }
        _setValue(val) {
            if (this.currentOrder.get_selected_orderline()) {
                if (this.env.pos.numpadMode === 'quantity') {
                    const result = this.currentOrder.get_selected_orderline().set_quantity(val);
                    if (!result) NumberBuffer.reset();
                } else if (this.env.pos.numpadMode === 'discount') {
                    this.currentOrder.get_selected_orderline().set_discount(val);
                } else if (this.env.pos.numpadMode === 'price') {
                    var selected_orderline = this.currentOrder.get_selected_orderline();
                    selected_orderline.price_manually_set = true;
                    selected_orderline.set_unit_price(val);
                }
            }
        }
        async _getProductByBarcode(code) {
            let product = this.env.pos.db.get_product_by_barcode(code.base_code);
            if (!product) {
                // find the barcode in the backend
                let foundProductIds = [];
                const foundPackagings = [];
                try {
                    const { product_id = [], packaging = [] } = await this.rpc({
                        model: 'pos.session',
                        method: 'find_product_by_barcode',
                        args: [odoo.pos_session_id, code.base_code],
                        context: this.env.session.user_context,
                    });
                    foundProductIds.push(...product_id);
                    foundPackagings.push(...packaging);
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
                    await this.env.pos._addProducts(foundProductIds, false);
                    if (foundPackagings.length) {
                        this.env.pos.db.add_packagings(foundPackagings);
                    }
                    // assume that the result is unique.
                    product = this.env.pos.db.get_product_by_id(foundProductIds[0]);
                } else {
                    return this._barcodeErrorAction(code);
                }
            }
            return product
        }
        async _barcodeProductAction(code) {
            const product = await this._getProductByBarcode(code);
            if (!product) {
                return;
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
            } else if (code.type === 'weight' || code.type === 'quantity') {
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
            this.currentOrder.add_product(product,  options);
            NumberBuffer.reset();
        }
        _barcodePartnerAction(code) {
            const partner = this.env.pos.db.get_partner_by_barcode(code.code);
            if (partner) {
                if (this.currentOrder.get_partner() !== partner) {
                    this.currentOrder.set_partner(partner);
                    this.currentOrder.updatePricelist(partner);
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
        async _parseElementsFromGS1(parsed_results) {
            const productBarcode = parsed_results.find(element => element.type === 'product');
            const lotBarcode = parsed_results.find(element => element.type === 'lot');
            const product = await this._getProductByBarcode(productBarcode);
            return { product, lotBarcode, customProductOptions: {} }
        }
        /**
         * Add a product to the current order using the product identifier and lot number from parsed results.
         * This function retrieves the product identifier and lot number from the `parsed_results` parameter.
         * It then uses these values to retrieve the product and add it to the current order.
         */
        async _barcodeGS1Action(parsed_results) {
            const { product, lotBarcode, customProductOptions } = await this._parseElementsFromGS1(parsed_results)
            if (!product) {
                return;
            }
            const options = await this._getAddProductOptions(product, lotBarcode);
            await this.currentOrder.add_product(product, { ...options, ...customProductOptions });
            NumberBuffer.reset();
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
                return true;
            }
            return false;
        }
        async onClickPartner() {
            // IMPROVEMENT: This code snippet is very similar to selectPartner of PaymentScreen.
            const currentPartner = this.currentOrder.get_partner();
            if (currentPartner && this.currentOrder.getHasRefundLines()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Can't change customer"),
                    body: _.str.sprintf(
                        this.env._t(
                            "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer."
                        ),
                        currentPartner.name
                    ),
                });
                return;
            }
            const { confirmed, payload: newPartner } = await this.showTempScreen(
                'PartnerListScreen',
                { partner: currentPartner }
            );
            if (confirmed) {
                this.currentOrder.set_partner(newPartner);
                this.currentOrder.updatePricelist(newPartner);
            }
        }
        async _onClickPay() {
            if (this.env.pos.get_order().orderlines.some(line => line.get_product().tracking !== 'none' && !line.has_valid_product_lot()) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
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
    ProductScreen.numpadActionName = _lt('Payment');

    Registries.Component.add(ProductScreen);

    return ProductScreen;
});
