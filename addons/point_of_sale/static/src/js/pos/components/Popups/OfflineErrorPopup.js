/** @odoo-module alias=point_of_sale.OfflineErrorPopup **/

import ErrorPopup from 'point_of_sale.ErrorPopup';
import { _t } from 'web.core';

/**
 * This is a special kind of error popup as it introduces
 * an option to not show it again.
 */
class OfflineErrorPopup extends ErrorPopup {
    dontShowAgain() {
        this.env.model.data.uiState.showOfflineError = false;
        this.props.respondWith();
    }
}
OfflineErrorPopup.template = 'point_of_sale.OfflineErrorPopup';
OfflineErrorPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Offline Error'),
    body: _t('Either the server is inaccessible or browser is not connected online.'),
};

export default OfflineErrorPopup;
