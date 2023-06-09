/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";

import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, "discuss/call/web", {
    onStartMeeting() {
        this.threadActions.actions.find((action) => action.id === "add-users").onSelect();
    },
});
