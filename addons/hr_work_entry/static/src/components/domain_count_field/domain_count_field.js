import { registry } from "@web/core/registry";
import { DomainField } from "@web/views/fields/domain/domain_field";

export class DomainCountField extends DomainField {
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
