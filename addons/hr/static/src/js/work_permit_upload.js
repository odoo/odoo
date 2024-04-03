/** @odoo-module **/

import basicFields from 'web.basic_fields';
import fieldRegistry from 'web.field_registry';

const WorkPermitUpload = basicFields.FieldBinaryFile.extend({
    template: "hr.WorkPermitUpload",
});

fieldRegistry.add('work_permit_upload', WorkPermitUpload);
