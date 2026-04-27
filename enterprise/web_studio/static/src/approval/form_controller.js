import { useSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this._shouldUseSubEnv()) {
            const { relatedModels } = this.props;
            const hasApprovalRules = {};
            for (const model in relatedModels || {}) {
                hasApprovalRules[model] = relatedModels[model].has_approval_rules || false;
            }
            useSubEnv({ hasApprovalRules });
        }
    },
    _shouldUseSubEnv() {
        return true;
    },
});
