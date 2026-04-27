/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class SwissdecInteroperabilityClient extends Component {
    static props = {
        ...standardActionServiceProps
    };
    static template = "l10n_ch_hr_payroll_elm_transmission.SwissdecInteroperabilityClient";

    setup() {
        this.orm = useService("orm");
        this.company = useService("company");
        this.state = useState({
            ping_response: false,
            check_interoperability_response: false,
            second_operand: ""
        });
    }

    async PingRequest(){
        this.state.ping_response = await this.orm.call('res.company', 'l10n_ch_hr_payroll_action_ping', [[this.company.currentCompany.id]]);
    }

    async CheckInteroperabilityRequest(ev){
        this.state.check_interoperability_response = await this.orm.call('res.company', 'l10n_ch_hr_payroll_action_check_interoperability', [
            [this.company.currentCompany.id],
            this.state.second_operand
        ]);
    }

    onOperandInput(ev){
        this.state.second_operand = ev.target.value
    }
}

SwissdecInteroperabilityClient.template = "l10n_ch_hr_payroll_elm_transmission.SwissdecInteroperabilityClient";
registry.category("actions").add("swissdec_interoperability_client", SwissdecInteroperabilityClient);
