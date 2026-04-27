/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";

import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    /**
     * @override
     * This is necessary because the generic action loads a standard Action View,
     * whereas the specific action defines the 'js_class' required to initialize
     * the custom Documents view controller.
     */
    async executeActivityAction(group, domain, views, context) {
        if (group.model === "documents.document") {
            const action = await this.env.services.action.loadAction("documents.document_action");

            action.domain = domain;

            return this.action.doAction(action, {
                clearBreadcrumbs: true,
                viewType: group.view_type,
                additionalContext: context,
            });
        }

        return super.executeActivityAction(...arguments);
    },

    async onClickRequestDocument() {
        this.dropdown.close();
        this.env.services.action.doAction("documents.action_request_form");
    },
});
