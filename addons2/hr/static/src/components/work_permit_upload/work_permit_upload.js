/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class WorkPermitUploadField extends BinaryField {}
WorkPermitUploadField.template = "hr.WorkPermitUploadField";

export const workPermitUploadField = {
    ...binaryField,
    component: WorkPermitUploadField,
};

registry.category("fields").add("work_permit_upload", workPermitUploadField);
