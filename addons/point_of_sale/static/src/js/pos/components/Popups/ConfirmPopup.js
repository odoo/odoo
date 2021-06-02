/** @odoo-module alias=point_of_sale.ConfirmPopup **/

import Draggable from 'point_of_sale.Draggable';
import { _t } from 'web.core';


// formerly ConfirmPopupWidget
class ConfirmPopup extends owl.Component {}
ConfirmPopup.components = { Draggable };
ConfirmPopup.template = 'point_of_sale.ConfirmPopup';
ConfirmPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Confirm ?'),
    body: '',
    hideCancel: false,
};

export default ConfirmPopup;
