/** @odoo-module alias=point_of_sale.SetPricelistButton **/

import PosComponent from 'point_of_sale.PosComponent';

class SetPricelistButton extends PosComponent {
    async onClick() {
        const selectionList = this.env.model.getRecords('product.pricelist').map((pricelist) => ({
            id: pricelist.id,
            label: pricelist.name,
            isSelected: pricelist.id === this.props.activeOrder.pricelist_id,
        }));

        const [confirmed, selectedItem] = await this.env.ui.askUser('SelectionPopup', {
            title: this.env._t('Select the pricelist'),
            list: selectionList,
        });

        if (confirmed) {
            this.env.model.actionHandler({ name: 'actionSetPricelist', args: [this.props.activeOrder, selectedItem.id] });
        }
    }
    get currentPricelistName() {
        const pricelist = this.env.model.getRecord('product.pricelist', this.props.activeOrder.pricelist_id);
        return this.props.activeOrder && pricelist ? pricelist.display_name : this.env._t('Pricelist');
    }
}
SetPricelistButton.template = 'point_of_sale.SetPricelistButton';

export default SetPricelistButton;
