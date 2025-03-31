import { AttachmentView } from "@mail/core/common/attachment_view";
import { Chatter } from "@mail/chatter/web_portal/chatter";

import { onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { SIZES } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this.mailComponents = {
            AttachmentView,
            Chatter,
        };
        this.highlightMessageId = router.current.highlight_message_id;
        this.messagingState = useState({
            /** @type {import("models").Thread} */
            thread: undefined,
        });
        if (this.env.services["mail.store"]) {
            this.mailStore = useService("mail.store");
        }
        this.uiService = useService("ui");
        this.mailPopoutService = useService("mail.popout");

        this.onResize = useDebounced(this.render, 200);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));
    },
    /**
     * @returns {boolean}
     */
    hasFile() {
        if (!this.mailStore || !this.props.record.resId) {
            return false;
        }
        this.messagingState.thread = this.mailStore.Thread.insert({
            id: this.props.record.resId,
            model: this.props.record.resModel,
        });
        return this.messagingState.thread.attachmentsInWebClientView.length > 0;
    },
    mailLayout(hasAttachmentContainer) {
        const xxl = this.uiService.size >= SIZES.XXL;
        const hasFile = this.hasFile();
        const hasChatter = !!this.mailStore;
        const hasExternalWindow = !!this.mailPopoutService.externalWindow;
        if (hasExternalWindow && hasFile && hasAttachmentContainer) {
            if (xxl) {
                return "EXTERNAL_COMBO_XXL"; // chatter on the side, attachment in separate tab
            }
            return "EXTERNAL_COMBO"; // chatter on the bottom, attachment in separate tab
        }
        if (hasChatter) {
            if (xxl) {
                if (hasAttachmentContainer && hasFile) {
                    return "COMBO"; // chatter on the bottom, attachment on the side
                }
                return "SIDE_CHATTER"; // chatter on the side, no attachment
            }
            return "BOTTOM_CHATTER"; // chatter on the bottom, no attachment
        }
        return "NONE";
    },
});
