/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { DocumentsInspector } from "@documents/views/inspector/documents_inspector";
import { patch } from '@web/core/utils/patch';
import { useService } from "@web/core/utils/hooks";

patch(DocumentsInspector.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.user = useService("user");
        onWillStart(async () => {
            this.purchaseGroup = await this.user.hasGroup('account.group_purchase_receipts');
        });
    },

    /**
     * @override
     * Override to allow the creation of vendor receipt when the group is enabled.
     */
    getCommonRules() {
        let commonRules = super.getCommonRules();
        if (!this.purchaseGroup) {
            commonRules = commonRules.filter((rec) => rec._values.create_model !== 'account.move.in_receipt');
        }
        return commonRules;
    }
});
