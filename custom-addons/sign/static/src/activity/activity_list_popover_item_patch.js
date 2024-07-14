/** @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";

patch(ActivityListPopoverItem.prototype, {
    get hasMarkDoneButton() {
        return super.hasMarkDoneButton && this.props.activity.activity_category !== "sign_request";
    },

    async onClickRequestSign() {
        await this.env.services["mail.activity"].requestSignature(
            this.props.activity.id,
            this.props.onActivityChanged
        );
    },
});
