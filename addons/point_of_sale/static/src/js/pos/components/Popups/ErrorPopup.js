/** @odoo-module alias=point_of_sale.ErrorPopup **/

import Draggable from 'point_of_sale.Draggable';
import { _t } from 'web.core';

class ErrorPopup extends owl.Component {
    mounted() {
        this.env.ui.playSound('error');
    }
}
ErrorPopup.components = { Draggable };
ErrorPopup.template = 'point_of_sale.ErrorPopup';
ErrorPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Error'),
    body: '',
};

export default ErrorPopup;
