/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { retrieveHMRCClientInfo } from "../../hmrc_api";

function isValidUuid(str) {
    return /^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i.test(str);
}

export class SendHmrcButton extends Component {
    static template = "l10n_uk_reports.SendHmrcButton";
    static props = {...standardWidgetProps};


    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.title = _t('Send Data to the HMRC Service');
        this.hmrcGovClientDeviceIdentifier = this.props.record.data.hmrc_gov_client_device_id;
    }

    async retrieveClientInfo() {
        this.env.services.ui.block();
        try {
            if (!localStorage.getItem('hmrc_gov_client_device_id')) {
                localStorage.setItem('hmrc_gov_client_device_id', this.hmrcGovClientDeviceIdentifier);
            }
            if (!isValidUuid(localStorage.getItem('hmrc_gov_client_device_id'))) {
                localStorage.removeItem('hmrc_gov_client_device_id');
            }
            let clientData = retrieveHMRCClientInfo();
            clientData.hmrc_gov_client_device_id = localStorage.getItem('hmrc_gov_client_device_id');
            await this.orm.call(
                'l10n_uk.vat.obligation',
                'action_submit_vat_return',
                [this.props.record.data.obligation_id[0], clientData]
            );
            this.actionService.doAction({'type': 'ir.actions.act_window_close'})
        } finally {
            this.env.services.ui.unblock();
        }
    }
}

export const sendHmrcButton = {
    component: SendHmrcButton,
}

registry.category('view_widgets').add('send_hmrc_button', sendHmrcButton);
