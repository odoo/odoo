/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class SendHmrcButton extends Component {

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
                localStorage.setItem('hmrc_gov_client_device_id', this.hmrc_gov_client_device_id);
            }

            const clientInfo = {
                'screen_width': screen.width,
                'screen_height': screen.height,
                'screen_scaling_factor': window.devicePixelRatio,
                'screen_color_depth': screen.colorDepth,
                'window_width': window.outerWidth,
                'window_height': window.outerHeight,
                'hmrc_gov_client_device_id': localStorage.getItem('hmrc_gov_client_device_id'),
            }

            await this.orm.call(
                'l10n_uk.vat.obligation',
                'action_submit_vat_return',
                [this.props.record.data.obligation_id[0], clientInfo]
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

SendHmrcButton.template = "l10n_uk_reports.SendHmrcButton";
registry.category('view_widgets').add('send_hmrc_button', sendHmrcButton);
