import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { registry } from "@web/core/registry";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { InRange } from "@web/core/tree_editor/tree_editor_components";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";

class AccrualRuleTreeEditor extends TreeEditor {
    static components = { ...TreeEditor.components, TreeEditor: AccrualRuleTreeEditor };

    getValueEditorInfo(node) {
        const editorInfo = super.getValueEditorInfo(node);
        if (node.operator !== "in range") {
            return editorInfo;
        }
        return {
            ...editorInfo,
            extractProps(params) {
                const props = editorInfo.extractProps(params);
                const valueTypeEditorInfo = props.valueTypeEditorInfo;
                return {
                    ...props,
                    valueTypeEditorInfo: {
                        ...valueTypeEditorInfo,
                        extractProps(valueParams) {
                            return {
                                ...valueTypeEditorInfo.extractProps(valueParams),
                                options: InRange.options,
                            };
                        },
                    },
                };
            },
        };
    }
}

class AccrualRuleDomainSelector extends DomainSelector {
    static components = { ...DomainSelector.components, TreeEditor: AccrualRuleTreeEditor };
}

class AccrualRuleDomainField extends DomainField {
    static components = { ...DomainField.components, DomainSelector: AccrualRuleDomainSelector };
}

registry.category("fields").add("accrual_rule_domain", {
    ...domainField,
    component: AccrualRuleDomainField,
});
