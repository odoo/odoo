import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";

export class DomainCompanyField extends DomainField {
    getEvaluatedDomain(props = this.props) {
        const domain = super.getEvaluatedDomain(props);
        if (domain.isInvalid) {
            return domain;
        }
        const companyId = props.record.data.company_id?.id;
        if (!companyId) {
            return domain;
        }
        return Domain.and([domain, [["company_id", "=", companyId]]]).toList(this.getContext(props));
    }
}

registry.category("fields").add("domain_company", {
    ...domainField,
    component: DomainCompanyField,
});
