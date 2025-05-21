import { patch } from "@web/core/utils/patch";
import { PortalComposer } from "@portal/interactions/portal_composer";

patch(PortalComposer.prototype, {
    /**
     * For slide channel message update, ensure the body isn't empty so the message shows as deleted instead of hidden.
     * Exception: If you haven't left a rating yet, you can do so without a message (body empty).
     * @override
     */
    prepareMessageData() {
        const needOverride =
            this.options.force_submit_url === "/mail/message/update_content" &&
            this.options.res_model === "slide.channel" &&
            this.options.default_message_id;
        const res = super.prepareMessageData(...arguments);
        if (needOverride) {
            res.body = res.body || " ";
        }
        return res;
    },
});
