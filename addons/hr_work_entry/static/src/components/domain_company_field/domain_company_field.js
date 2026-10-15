import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";

/**
 * Domain field of the time rules: the employees it lists and counts are also filtered like the rule
 * filters them (see hr.time.rule._get_applicable_employees): on the company of the rule, or else on
 * its country.
 */
export class DomainCompanyField extends DomainField {
    getEvaluatedDomain(props = this.props) {
        const domain = super.getEvaluatedDomain(props);
        if (domain.isInvalid) {
            return domain;
        }
        const { company_id: company, country_id: country } = props.record.data;
        let ruleDomain;
        if (company?.id) {
            ruleDomain = [["company_id", "=", company.id]];
        } else if (country?.id) {
            ruleDomain = [["company_id.country_id", "=", country.id]];
        } else {
            return domain;
        }
        return Domain.and([domain, ruleDomain]).toList(this.getContext(props));
    }
}

registry.category("fields").add("domain_company", {
    ...domainField,
    component: DomainCompanyField,
});
