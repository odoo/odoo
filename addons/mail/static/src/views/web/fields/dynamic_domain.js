import { domainField } from "@web/views/fields/domain/domain_field";
import { registry } from "@web/core/registry";

registry.category("fields").add("dynamic_domain", {
    ...domainField,
    extractProps({ options }, dynamicInfo) {
        const context = dynamicInfo.context || {};
        return {
            editInDialog: options.in_dialog || context.default_dynamic_domain_in_dialog,
            isFoldable: options.foldable || context.default_dynamic_domain_foldable,
            allowExpressions:
                options.allow_expressions || context.default_dynamic_domain_allow_expressions,
            resModel: options.model || context.default_dynamic_domain_model,
            countLimit: options.count_limit || context.default_dynamic_domain_count_limit,
            context: dynamicInfo.context,
        };
    },
});
