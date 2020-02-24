odoo.define('point_of_sale.SetFiscalPositionButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');

    class SetFiscalPositionButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        mounted() {
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
        }
        willUnmount() {
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get currentFiscalPositionName() {
            return this.currentOrder && this.currentOrder.fiscal_position
                ? this.currentOrder.fiscal_position.display_name
                : this.env._t('Tax');
        }
        async onClick() {
            const selectionList = this.env.pos.fiscal_positions.map(fiscalPosition => {
                return {
                    id: fiscalPosition.id,
                    label: fiscalPosition.name,
                    isSelected: fiscalPosition.id === this.currentOrder.fiscal_position.id,
                    item: fiscalPosition,
                };
            });
            const { confirmed, payload: selectedFiscalPosition } = await this.showPopup(
                'SelectionPopup',
                {
                    title: this.env._t('Select Fiscal Position'),
                    list: selectionList,
                }
            );
            if (confirmed) {
                this.currentOrder.fiscal_position = selectedFiscalPosition;
                // TODO jcb: The following is the old implementation and I believe
                // there could be a better way of doing it.
                for (let line of this.currentOrder.orderlines.models) {
                    line.set_quantity(line.quantity);
                }
                this.currentOrder.trigger('change');
            }
        }
    }

    ProductScreen.addControlButton({
        component: SetFiscalPositionButton,
        condition: function() {
            return this.env.pos.fiscal_positions.length > 0;
        },
        position: ['before', 'SetPricelistButton'],
    });

    return { SetFiscalPositionButton };
});
