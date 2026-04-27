import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { patch } from "@web/core/utils/patch";

patch(ActivityListPopoverItem.prototype, {
    get hasMarkDoneButton() {
        return super.hasMarkDoneButton && this.props.activity.activity_category !== "sign_request";
    },

    async onClickRequestSign() {
        const { res_model, res_id } = this.props.activity;
        // Skip 'sign.request' model as it's not allowed in the Reference field selection in the backend.
        const documentReference = (res_model && res_model !== 'sign.request') && res_id ? `${res_model},${res_id}` : false;
        await this.props.activity.requestSignature(this.props.onActivityChanged, documentReference);
    },
});
