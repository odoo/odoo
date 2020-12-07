/** @odoo-module alias=point_of_sale.ErrorBarcodePopup **/

import ErrorPopup from 'point_of_sale.ErrorPopup';

class ErrorBarcodePopup extends ErrorPopup {
    get errorMessage() {
        if (!this.props.message) {
            return this.env._t(
                'The Point of Sale could not find any product, client, employee or action associated with the scanned barcode.'
            );
        } else {
            return this.props.message;
        }
    }
}
ErrorBarcodePopup.template = 'point_of_sale.ErrorBarcodePopup';
ErrorBarcodePopup.defaultProps = {
    confirmText: 'Ok',
};

export default ErrorBarcodePopup;
