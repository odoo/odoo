import { AccountLabelTextField } from "@account/components/account_label_text/account_label_text";
import {
    ListSaleOrderLineText,
    listSaleOrderLineText,
    saleOrderLineText,
} from "./sale_order_line_field";
import { registry } from "@web/core/registry";

export class SaleLabelTextField extends AccountLabelTextField {
    get productDomain() {
        return [["sale_ok", "=", true]];
    }
}

export class ListSaleLabelSectionAndNoteText extends ListSaleOrderLineText {
    get componentToUse() {
        const record = this.props.record;
        if (!record.data.display_type && "product_id" in record.activeFields) {
            return SaleLabelTextField;
        }
        return super.componentToUse;
    }
}

registry.category("fields").add("sol_label_text", saleOrderLineText);
registry.category("fields").add("list.sol_label_text", {
    ...listSaleOrderLineText,
    component: ListSaleLabelSectionAndNoteText,
});
