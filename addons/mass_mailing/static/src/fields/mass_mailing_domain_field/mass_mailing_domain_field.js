import { registry } from "@web/core/registry";
import { MassMailingDomainSelector } from "./mass_mailing_domain_selector";
import {
    domainSavableField,
    DomainSavableField,
} from "../domain_savable_field/domain_savable_field";

/**
 * Domain field that toggles `use_exclusion_list` instead of
 * changing the domain to include archived records.
 *
 * Also provides the possibility to save a crafted domain
 * by the user as a dynamic list (`mailing.filter`).
 */
export class MassMailingDomainField extends DomainSavableField {
    static template = "mass_mailing.MassMailingDomainField";
    static components = {
        DomainSelector: MassMailingDomainSelector,
    };

    updateUseExclusionList(value) {
        this.props.record.update({ use_exclusion_list: value });
    }
}

export const massMailingDomainField = {
    ...domainSavableField,
    component: MassMailingDomainField,
};

registry.category("fields").add("mass_mailing_domain", massMailingDomainField);
