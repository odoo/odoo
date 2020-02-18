odoo.define('point_of_sale.ProductScreen', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { ProductsWidget } = require('point_of_sale.ProductsWidget');
    const { OrderWidget } = require('point_of_sale.OrderWidget');
    const { NumpadWidget } = require('point_of_sale.NumpadWidget');
    const { ActionpadWidget } = require('point_of_sale.ActionpadWidget');
    const { NumpadState } = require('point_of_sale.models');

    class ProductScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.numpadState = new NumpadState();
        }
        mounted() {
            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    this.render();
                },
                this
            );
            this.env.pos.barcode_reader.set_action_callback({
                product: this._barcodeProductAction.bind(this),
                weight: this._barcodeProductAction.bind(this),
                price: this._barcodeProductAction.bind(this),
                client: this._barcodeClientAction.bind(this),
                discount: this._barcodeDiscountAction.bind(this),
                error: this._barcodeErrorAction.bind(this),
            });
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
            if (this.env.pos.barcode_reader) {
                this.env.pos.barcode_reader.reset_action_callbacks();
            }
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        async clickProduct(event) {
            const product = event.detail;
            let draftPackLotLines, weight, packLotLinesToEdit;

            // Gather lot information if required.
            if (['serial', 'lot'].includes(product.tracking)) {
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
                // Show the ScaleScreen (or ScalePopup) to get the weight.
                // const { confirmed: userAgreed, data } = await this.gui.show_screen('scale', {
                //     product,
                // });
                // if (userAgreed) {
                //     weight = data.weight;
                // }
            }

            // Add the product after having the extra information.
            this.currentOrder.add_product(product, {
                draftPackLotLines,
                quantity: weight,
            });
        }
        _barcodeProductAction(code) {
            // NOTE: scan_product call has side effect in pos if it returned true.
            if (!this.env.pos.scan_product(code)) {
                this._barcodeErrorAction(code);
            }
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
        // TODO jcb: The following two methods should be in PosScreenComponent?
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
    }
    ProductScreen.components = { ProductsWidget, OrderWidget, NumpadWidget, ActionpadWidget };
    // TODO jcb: This is the way to add control buttons above the numpad
    ProductScreen.addControlButton = () => {};

    Chrome.addComponents([ProductScreen]);

    return { ProductScreen };
});
