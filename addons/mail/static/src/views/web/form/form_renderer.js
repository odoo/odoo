/* @odoo-module */

import { AttachmentView } from "@mail/core/common/attachment_view";
import { insertThread } from "@mail/core/common/thread_service";
import { Chatter } from "@mail/core/web/chatter";

import { onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { SIZES } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, "mail/views/web", {
    setup() {
        this._super();
        this.mailComponents = {
            AttachmentView,
            Chatter,
        };
        this.messagingState = useState({
            /** @type {import("@mail/core/common/thread_model").Thread} */
            thread: undefined,
        });
        this.uiService = useService("ui");

        this.onResize = useDebounced(this.render, 200);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));
    },
    /**
     * @returns {boolean}
     */
    hasFileViewer() {
        if (this.uiService.size < SIZES.XXL || !this.props.record.resId) {
            return false;
        }
        this.messagingState.thread = insertThread({
            id: this.props.record.resId,
            model: this.props.record.resModel,
            type: "chatter",
        });
        return this.messagingState.thread.attachmentsInWebClientView.length > 0;
    },
});

patch(FormRenderer.props, "mail/views/web", {
    // Template props : added by the FormCompiler
    saveButtonClicked: { type: Function, optional: true },
});
