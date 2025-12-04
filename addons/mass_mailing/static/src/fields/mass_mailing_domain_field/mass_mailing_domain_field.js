import { registry } from "@web/core/registry";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";
import { MassMailingDomainSelector } from "./mass_mailing_domain_selector";

/**
 * Domain field that toggles `use_exclusion_list` instead of
 * changing the domain to include archived records.
 */
export class MassMailingDomainField extends DomainField {
    static template = "mass_mailing.MassMailingDomainField";
    static props = {
        ...DomainField.props,
    };
    static components = {
        DomainSelector: MassMailingDomainSelector,
    };

    updateUseExclusionList(value) {
        this.props.record.update({ use_exclusion_list: value });
    }
}

export const massMailingDomainField = {
    ...domainField,
    component: MassMailingDomainField,
};

registry.category("fields").add("mass_mailing_domain", massMailingDomainField);
