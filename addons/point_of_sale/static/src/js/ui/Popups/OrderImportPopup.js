/** @odoo-module alias=point_of_sale.OrderImportPopup **/

import Draggable from 'point_of_sale.Draggable';

class OrderImportPopup extends owl.Component {
    get unpaidSkipped() {
        return (this.props.report.unpaid_skipped_existing || 0) + (this.props.report.unpaid_skipped_session || 0);
    }
}
OrderImportPopup.components = { Draggable };
OrderImportPopup.template = 'point_of_sale.OrderImportPopup';
OrderImportPopup.defaultProps = {
    confirmText: 'Ok',
    cancelText: 'Cancel',
    body: '',
};

export default OrderImportPopup;
