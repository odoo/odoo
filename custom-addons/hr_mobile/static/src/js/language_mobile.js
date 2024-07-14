/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { updateAccountOnMobileDevice } from "@web_mobile/js/core/mixins";
import { EmployeeProfileController } from "@hr/views/profile_form_view";

patch(EmployeeProfileController.prototype, {
    async onRecordSaved(record) {
        await updateAccountOnMobileDevice();
        return await super.onRecordSaved(...arguments);
    },
});
