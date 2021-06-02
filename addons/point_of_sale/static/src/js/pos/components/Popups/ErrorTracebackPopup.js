/** @odoo-module alias=point_of_sale.ErrorTracebackPopup **/

import ErrorPopup from 'point_of_sale.ErrorPopup';
import { _t } from 'web.core';

class ErrorTracebackPopup extends ErrorPopup {
    onExitButtonClick() {
        this.props.respondWith();
        this.env.model.actionHandler({ name: 'actionClosePos' });
    }
    get tracebackUrl() {
        const blob = new Blob([this.props.body]);
        const URL = window.URL || window.webkitURL;
        return URL.createObjectURL(blob);
    }
    get tracebackFilename() {
        return `${this.env._t('error')} ${moment().format('YYYY-MM-DD-HH-mm-ss')}.txt`;
    }
    emailTraceback() {
        const address = this.env.model.company.email;
        const subject = this.env._t('IMPORTANT: Bug Report From Odoo Point Of Sale');
        window.open(
            'mailto:' +
                address +
                '?subject=' +
                (subject ? window.encodeURIComponent(subject) : '') +
                '&body=' +
                (this.props.body ? window.encodeURIComponent(this.props.body) : '')
        );
    }
}
ErrorTracebackPopup.template = 'point_of_sale.ErrorTracebackPopup';
ErrorTracebackPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Error with Traceback'),
    body: '',
    exitButtonIsShown: false,
    exitButtonText: _t('Exit Pos'),
};

export default ErrorTracebackPopup;
