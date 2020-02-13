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
            this.gui = this.props.gui;
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
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
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
                    const orderline = this.env.pos
                        .get_order()
                        .get_orderlines()
                        .filter(line => !line.get_discount())
                        .find(line => line.product.id === product.id);
                    if (orderline) {
                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                    } else {
                        packLotLinesToEdit = [];
                    }
                }
                const { agreed: isUserAgreed, data } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Lot/Serial Number(s) Required'),
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (isUserAgreed) {
                    // Remove items with empty text.
                    const newArray = data.array.filter(item => item.text.trim() !== '');

                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        newArray.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = newArray
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
                // const { agreed: userAgreed, data } = await this.gui.show_screen('scale', {
                //     product,
                // });
                // if (userAgreed) {
                //     weight = data.weight;
                // }
            }

            // Add the product after having the extra information.
            this.env.pos.get_order().add_product(product, {
                draftPackLotLines,
                quantity: weight,
            });
        }
    }
    ProductScreen.components = { ProductsWidget, OrderWidget, NumpadWidget, ActionpadWidget };
    // TODO jcb: This is the way to add control buttons above the numpad
    ProductScreen.addControlButton = () => {};

    Chrome.addComponents([ProductScreen]);

    return { ProductScreen };
});
