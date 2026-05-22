import { DocumentState } from "@account/components/document_state/document_state_field";
import { registry } from "@web/core/registry";
import { selectionField } from "@web/views/fields/selection/selection_field";

export class NilveraSendStatus extends DocumentState {
    get nilveraSendStatus() {
        return this.props.record.data.l10n_tr_nilvera_send_status;
    }

    get message() {
        if (this.nilveraSendStatus !== "error") {
            return "";
        }
        const value = this.props.record.data.l10n_tr_nilvera_customer_status;
        if (!value) {
            return "";
        }
        const field = this.props.record.fields.l10n_tr_nilvera_customer_status;
        const entry = field?.selection?.find(([v]) => v === value);
        return entry ? entry[1] : value;
    }
}

registry.category("fields").add("l10n_tr_nilvera_send_status", {
    ...selectionField,
    component: NilveraSendStatus,
});
