/** @odoo-module alias=point_of_sale.HeaderButton **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

class HeaderButton extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = useState({ label: this.env._t('Close') });
        this.confirmed = null;
    }
    onClick() {
        if (!this.confirmed) {
            this.state.label = this.env._t('Confirm');
            this.confirmed = setTimeout(() => {
                this.state.label = this.env._t('Close');
                this.confirmed = null;
            }, 2000);
        } else {
            this.env.model.actionHandler({ name: 'actionClosePos' });
        }
    }
}
HeaderButton.template = 'point_of_sale.HeaderButton';

export default HeaderButton;
