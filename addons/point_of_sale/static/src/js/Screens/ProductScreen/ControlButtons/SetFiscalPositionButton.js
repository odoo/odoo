odoo.define('point_of_sale.SetFiscalPositionButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

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
            const currentFiscalPosition = this.currentOrder.fiscal_position;
            const fiscalPosList = [
                {
                    id: -1,
                    label: this.env._t('None'),
                    isSelected: !currentFiscalPosition,
                },
            ];
            for (let fiscalPos of this.env.pos.fiscal_positions) {
                fiscalPosList.push({
                    id: fiscalPos.id,
                    label: fiscalPos.name,
                    isSelected: currentFiscalPosition
                        ? fiscalPos.id === currentFiscalPosition.id
                        : false,
                    item: fiscalPos,
                });
            }
            const { confirmed, payload: selectedFiscalPosition } = await this.showPopup(
                'SelectionPopup',
                {
                    title: this.env._t('Select Fiscal Position'),
                    list: fiscalPosList,
                }
            );
            if (confirmed) {
                this.currentOrder.fiscal_position = selectedFiscalPosition;
                // IMPROVEMENT: The following is the old implementation and I believe
                // there could be a better way of doing it.
                for (let line of this.currentOrder.orderlines.models) {
                    line.set_quantity(line.quantity);
                }
                this.currentOrder.trigger('change');
            }
        }
    }
    SetFiscalPositionButton.template = 'SetFiscalPositionButton';

    ProductScreen.addControlButton({
        component: SetFiscalPositionButton,
        condition: function() {
            return this.env.pos.fiscal_positions.length > 0;
        },
        position: ['before', 'SetPricelistButton'],
    });

    Registries.Component.add(SetFiscalPositionButton);

    return SetFiscalPositionButton;
});
