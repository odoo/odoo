/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class IoTConnectionErrorDialog extends Component {}
IoTConnectionErrorDialog.template = 'iot.IoTConnectionErrorDialog';
IoTConnectionErrorDialog.components = { Dialog };
IoTConnectionErrorDialog.props = {
    title: { type: String, optional: true },
    href: { type: String },
    close: { type: Function }, // always provided by the dialog service
};
IoTConnectionErrorDialog.defaultProps = {
    title: _t('Connection to IoT Box failed'),
};
