/** @odoo-module alias=point_of_sale.ErrorPopup **/

import Draggable from 'point_of_sale.Draggable';

class ErrorPopup extends owl.Component {
    mounted() {
        this.env.ui.playSound('error');
    }
}
ErrorPopup.components = { Draggable };
ErrorPopup.template = 'point_of_sale.ErrorPopup';
ErrorPopup.defaultProps = {
    confirmText: 'Ok',
    cancelText: 'Cancel',
    title: 'Error',
    body: '',
};

export default ErrorPopup;
