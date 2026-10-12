import { formatList } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { ListX2ManyField } from "@web/views/fields/x2many/list_x2many_field";

export class One2manyNamesField extends ListX2ManyField {
    get formattedValue() {
        return formatList(
            this.props.record.data[this.props.name].records.map((r) => r.data.display_name)
        );
    }
}

registry.category("fields").add("im_livechat.one2many_names", {
    component: One2manyNamesField,
    relatedFields() {
        return [{ name: "display_name", type: "char" }];
    },
});
