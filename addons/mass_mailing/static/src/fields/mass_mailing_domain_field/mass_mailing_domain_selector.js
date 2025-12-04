import { DomainSelector } from "@web/core/domain_selector/domain_selector";

export class MassMailingDomainSelector extends DomainSelector {
    static template = "mass_mailing.MassMailingDomainSelector";
    static props = {
        ...DomainSelector.props,
        updateUseExclusionList: { type: Function },
        useExclusionList: { type: Boolean },
    };
}
