import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { _t } from "@web/core/l10n/translation";

export function openCompanyScopedDialog(field) {
    const companyId = field.props.record.data.company_id?.id;
    if (!companyId) {
        return false;
    }
    const domain = Domain.and([
        field.getEvaluatedDomain(),
        [["company_id", "=", companyId]],
    ]).toList(field.getContext());
    field.addDialog(
        SelectCreateDialog,
        {
            title: _t("Selected records"),
            noCreate: true,
            multiSelect: false,
            resModel: field.getResModel(),
            domain,
            context: { ...field.getContext(), allowed_company_ids: [companyId] },
        },
        { onClose: () => field.checkProps() }
    );
    return true;
}

export class DomainCompanyField extends DomainField {
    onButtonClick() {
        if (!openCompanyScopedDialog(this)) {
            super.onButtonClick();
        }
    }
}

registry.category("fields").add("domain_company", {
    ...domainField,
    component: DomainCompanyField,
});
