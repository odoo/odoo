/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";

import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    async onClickRequestDocument() {
        document.body.click(); // hack to close dropdown
        this.env.services.action.doAction("documents.action_request_form");
    },
});
