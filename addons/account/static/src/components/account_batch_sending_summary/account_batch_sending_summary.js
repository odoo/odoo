import { Component, useProps } from "@odoo/owl";
import {registry} from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AccountBatchSendingSummary extends Component {
    static template = "account.BatchSendingSummary";

    props = useProps(standardFieldProps);

    setup() {
        super.setup();
        this.data = this.props.record.data[this.props.name];
    }
}

export const accountBatchSendingSummary = {
    component: AccountBatchSendingSummary,
}

registry.category("fields").add("account_batch_sending_summary", accountBatchSendingSummary);
