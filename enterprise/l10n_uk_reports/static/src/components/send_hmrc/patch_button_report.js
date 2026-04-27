/** @odoo-module */
import { AccountReportController } from "@account_reports/components/account_report/controller";
import { retrieveHMRCClientInfo } from "../../hmrc_api";

import { patch } from "@web/core/utils/patch";

patch(AccountReportController.prototype, {
    buttonAction(ev, button) {
        if (button.client_tag == 'send_hmrc_button_report') {
            const additionalContext = {client_data: retrieveHMRCClientInfo()}
            this.reportAction(ev, button.action, button.action_param, true, additionalContext);
        }
        else {
            super.buttonAction(ev, button);
        }
    }
})
