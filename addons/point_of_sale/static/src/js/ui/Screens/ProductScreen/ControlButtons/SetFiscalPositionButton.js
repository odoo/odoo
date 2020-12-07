/** @odoo-module alias=point_of_sale.SetFiscalPositionButton **/

import PosComponent from 'point_of_sale.PosComponent';

class SetFiscalPositionButton extends PosComponent {
    async onClick() {
        if (!this.props.activeOrder) return;
        const currentFiscalPosition = this.env.model.getRecord(
            'account.fiscal.position',
            this.props.activeOrder.fiscal_position_id
        );
        const fiscalPosList = [
            {
                id: -1,
                label: this.env._t('None'),
                isSelected: !currentFiscalPosition,
            },
        ];
        for (const fiscalPos of this.env.model.getRecords('account.fiscal.position')) {
            fiscalPosList.push({
                id: fiscalPos.id,
                label: fiscalPos.name,
                isSelected: currentFiscalPosition ? fiscalPos.id === currentFiscalPosition.id : false,
            });
        }
        const [confirmed, selectedItem] = await this.env.ui.askUser('SelectionPopup', {
            title: this.env._t('Select Fiscal Position'),
            list: fiscalPosList,
        });
        if (confirmed) {
            const fiscalPositionId = selectedItem.id === -1 ? false : selectedItem.id;
            await this.env.model.actionHandler({
                name: 'actionSetFiscalPosition',
                args: [this.props.activeOrder, fiscalPositionId],
            });
        }
    }
    get currentFiscalPositionName() {
        const defaultName = this.env._t('Tax');
        if (!this.props.activeOrder) return defaultName;
        const fiscalPosition = this.env.model.getRecord(
            'account.fiscal.position',
            this.props.activeOrder.fiscal_position_id
        );
        return fiscalPosition ? fiscalPosition.display_name : defaultName;
    }
}
SetFiscalPositionButton.template = 'point_of_sale.SetFiscalPositionButton';

export default SetFiscalPositionButton;
