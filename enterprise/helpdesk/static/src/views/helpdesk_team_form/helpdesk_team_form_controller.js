/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { onMounted, onWillStart, onPatched } from "@odoo/owl";

export class HelpdeskTeamController extends FormController {
    setup() {
        super.setup();
        this.reloadInstall = false;
        this.fieldsToObserve = {};
        this.featuresToObserve = {};
        this.featuresToCheck = [];
        this.helpdeskResId = this.props.resId;
        onWillStart(this.onWillStart);
        onMounted(() => {
            this.updateFieldsToObserve();
        });
        onPatched(this.onPatched);
    }

    async onWillStart() {
        this.featuresToObserve = await this.orm.call(
            this.modelParams.config.resModel,
            "check_features_enabled",
            []
        );
    }

    onPatched() {
        if (this.helpdeskResId !== this.model.root.resId) {
            this.helpdeskResId = this.model.root.resId;
            this.fieldsToObserve = {};
            this.updateFieldsToObserve();
        }
    }

    updateFieldsToObserve() {
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
    async onWillSaveRecord(record, changes) {
        const res = await super.onWillSaveRecord(...arguments);
        const fields = [];
        for (const [fName, value] of Object.entries(changes)) {
            if (value && fName in this.fieldsToObserve && this.fieldsToObserve[fName] !== value) {
                fields.push(fName);
            }
            if (fName in this.featuresToObserve && value !== this.featuresToObserve[fName]) {
                this.featuresToCheck.push(fName);
            }
        }
        if (Object.keys(fields).length) {
            this.reloadInstall = await record.model.orm.call(
                record.resModel,
                "check_modules_to_install",
                [fields]
            );
        }
        return res;
    }

    /**
     * @override
     */
    async onRecordSaved(record) {
        await super.onRecordSaved(...arguments);
        let updatedEnabledFeatures = {};
        if (!this.reloadInstall && this.featuresToCheck.length) {
            updatedEnabledFeatures = await record.model.orm.call(
                record.resModel,
                "check_features_enabled",
                [this.featuresToCheck]
            );
        }
        if (
            this.reloadInstall ||
            Object.entries(updatedEnabledFeatures).some(
                ([fName, value]) => value !== this.featuresToObserve[fName]
            )
        ) {
            this.reloadInstall = false;
            this.model.action.doAction("reload_context");
        }
        this.updateFieldsToObserve();
        this.featuresToCheck = [];
    }
}
