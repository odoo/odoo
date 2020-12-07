/** @odoo-module alias=point_of_sale.EditListInput **/

import PosComponent from 'point_of_sale.PosComponent';

class EditListInput extends PosComponent {
    onKeyup(event) {
        if (event.key === 'Enter' && event.target.value.trim() !== '') {
            this.trigger('create-new-item');
        }
    }
}
EditListInput.template = 'point_of_sale.EditListInput';

export default EditListInput;
