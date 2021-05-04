/** @odoo-module alias=point_of_sale.ConfirmPopup **/

import Draggable from 'point_of_sale.Draggable';

// formerly ConfirmPopupWidget
class ConfirmPopup extends owl.Component {}
ConfirmPopup.components = { Draggable };
ConfirmPopup.template = 'point_of_sale.ConfirmPopup';
ConfirmPopup.defaultProps = {
    confirmText: 'Ok',
    cancelText: 'Cancel',
    title: 'Confirm ?',
    body: '',
    hideCancel: false,
};

export default ConfirmPopup;
