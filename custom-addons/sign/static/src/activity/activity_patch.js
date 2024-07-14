/** @odoo-module */

import { Activity } from "@mail/core/web/activity";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    async onClickRequestSign() {
        await this.env.services["mail.activity"].requestSignature(
            this.props.data.id,
            this.props.reloadParentView
        );
    },
});
