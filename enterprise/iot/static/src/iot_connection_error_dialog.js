/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class IoTConnectionErrorDialog extends Component {
    static template = "iot.IoTConnectionErrorDialog";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        href: { type: String },
        close: { type: Function }, // always provided by the dialog service
    };
    static defaultProps = {
        title: _t("Connection to IoT Box failed"),
    };
}
