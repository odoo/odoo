import {Component, useProps} from "@odoo/owl";
import {registry} from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AccountBatchSendingSummary extends Component {
    static template = "account.BatchSendingSummary";

    props = useProps(standardFieldProps);

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get data() {
        return this.props.record.data[this.props.name];
    }

    openMove(move, entry) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "account.move",
                views: [[false, "form"]],
            },
            { props: { resId: move.id, resIds: entry.moves.map((m) => m.id) } }
        );
    }
}

export const accountBatchSendingSummary = {
    component: AccountBatchSendingSummary,
}

registry.category("fields").add("account_batch_sending_summary", accountBatchSendingSummary);
