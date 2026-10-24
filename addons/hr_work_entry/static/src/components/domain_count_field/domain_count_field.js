import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { DomainCompanyField } from "@hr_work_entry/components/domain_company_field/domain_company_field";

patch(ListRenderer.prototype, {
    getCellTitle(column, record) {
        if (column.widget === "domain_count") {
            return undefined;
        }
        return super.getCellTitle(column, record);
    },
});

export class DomainCountField extends DomainCompanyField {
    static template = "hr_work_entry.DomainCountField";
}

registry.category("fields").add("domain_count", {
    component: DomainCountField,
    supportedTypes: ["char", "text"],
    isEmpty: () => false,
    extractProps({ options }, dynamicInfo) {
        return {
            resModel: options.model,
            context: dynamicInfo.context,
        };
    },
});
