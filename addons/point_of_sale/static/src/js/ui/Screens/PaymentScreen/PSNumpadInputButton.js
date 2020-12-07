/** @odoo-module alias=point_of_sale.PSNumpadInputButton **/

import PosComponent from 'point_of_sale.PosComponent';

class PSNumpadInputButton extends PosComponent {
    get _class() {
        return this.props.changeClassTo || 'input-button number-char';
    }
}
PSNumpadInputButton.template = 'point_of_sale.PSNumpadInputButton';

export default PSNumpadInputButton;
