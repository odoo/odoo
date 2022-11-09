/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField } from "@web/views/fields/binary/binary_field";

export class WorkPermitUploadField extends BinaryField {}
WorkPermitUploadField.template = "hr.WorkPermitUploadField";

registry.category("fields").add("work_permit_upload", WorkPermitUploadField);
