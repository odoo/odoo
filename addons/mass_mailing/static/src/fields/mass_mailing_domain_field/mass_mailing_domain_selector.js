import { props, t } from "@odoo/owl";
import { DomainSelector, domainSelectorProps } from "@web/core/domain_selector/domain_selector";

export class MassMailingDomainSelector extends DomainSelector {
    static template = "mass_mailing.MassMailingDomainSelector";
    props = props({
        ...domainSelectorProps,
        updateUseExclusionList: t.function(),
        useExclusionList: t.boolean(),
    });
}
