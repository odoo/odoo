/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DomainField, domainField } from '@web/views/fields/domain/domain_field';


export class QualityDomainField extends DomainField {}

QualityDomainField.template = 'quality_control_worksheet.QualityDomainField';

export const qualityDomainField = {
    ...domainField,
    component: QualityDomainField,
};

registry.category("fields").add("quality_domain_field", qualityDomainField);
