odoo.define('point_of_sale.ErrorTracebackPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ErrorTracebackPopupWidget
    class ErrorTracebackPopup extends AbstractAwaitablePopup {
        static template = 'ErrorTracebackPopup';
        get tracebackUrl() {
            const blob = new Blob([this.props.body]);
            const URL = window.URL || window.webkitURL;
            return URL.createObjectURL(blob);
        }
        get tracebackFilename() {
            return `${this.env._t('error')} ${moment().format('YYYY-MM-DD-HH-mm-ss')}.txt`;
        }
        emailTraceback() {
            const address = this.env.pos.company.email;
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
    ErrorTracebackPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error with Traceback',
        body: '',
        exitButtonIsShown: false,
        exitButtonText: 'Exit Pos',
        exitButtonTrigger: 'close-pos'
    };

    addComponents(Chrome, [ErrorTracebackPopup]);

    return { ErrorTracebackPopup };
});
