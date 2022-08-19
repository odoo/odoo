odoo.define('point_of_sale.Orderline', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    class Orderline extends PosComponent {
        setup() {
            super.setup();
            useListener('click-product-info', this.onClickProductInfo);
            useListener('click-customer-note', this.onClickCustomerNote);
        }
        selectLine() {
            this.trigger('select-line', { orderline: this.props.line });
        }
        lotIconClicked() {
            this.trigger('edit-pack-lot-lines', { orderline: this.props.line });
        }
        get addedClasses() {
            return {
                selected: this.props.line.selected,
            };
        }
        get customerNote() {
            return this.props.line.get_customer_note();
        }
        onClickProductInfo() {
            const orderline = this.env.pos.get_order().get_selected_orderline();
            if (orderline) {
                const product = orderline.get_product();
                const quantity = orderline.get_quantity();
                this.showPopup('ProductInfoPopup', { product, quantity });
            }
        }
        async onClickCustomerNote() {
            const selectedOrderline = this.env.pos.get_order().get_selected_orderline();
            if (!selectedOrderline) return;

            const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
                startingValue: selectedOrderline.get_customer_note(),
                title: this.env._t('Add Customer Note'),
            });

            if (confirmed) {
                selectedOrderline.set_customer_note(inputNote);
            }
        }
    }
    Orderline.template = 'Orderline';

    Registries.Component.add(Orderline);

    return Orderline;
});
