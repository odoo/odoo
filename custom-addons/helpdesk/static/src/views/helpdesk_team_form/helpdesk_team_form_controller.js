/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { onMounted } from "@odoo/owl";

export class HelpdeskTeamController extends FormController {
    setup() {
        super.setup();
        this.mustReload = false;
        this.fieldsToObserve = {};
        onMounted(this.onMounted);
    }

    onMounted() {
        for (const [fieldName, value] of Object.entries(this.model.root.data)) {
            if (fieldName.startsWith("use_")) {
                this.fieldsToObserve[fieldName] = value;
            }
        }
    }

    /**
     *
     * @override
     */
    async onWillSaveRecord(record) {
        const fields = [];
        for (const [fName, value] of Object.entries(record.data)) {
            if (fName in this.fieldsToObserve && value && this.fieldsToObserve[fName] !== value) {
                fields.push(fName);
            }
        }
        if (fields.length) {
            this.mustReload = await record.model.orm.call(
                record.resModel,
                "check_modules_to_install",
                [fields]
            );
        }
    }

    /**
     * @override
     */
    onRecordSaved(record) {
        if (this.mustReload) {
            this.mustReload = false;
            this.model.action.doAction("reload_context");
        }
    }
}
