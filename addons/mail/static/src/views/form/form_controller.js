/** @odoo-module */

import { AttachmentView } from "@mail/new/attachments/attachment_view";
import { Chatter } from "@mail/new/web/chatter";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";
import { FormController } from "@web/views/form/form_controller";
import { useViewCompiler } from "@web/views/view_compiler";
import { evalDomain } from "@web/views/utils";

import { MailFormCompiler } from "./form_compiler";

import { onMounted, onWillUnmount, useState } from "@odoo/owl";

patch(FormController.prototype, "mail", {
    setup() {
        this._super();
        this.messagingState = useState({
            /** @type {import("@mail/new/core/thread_model").Thread} */
            thread: undefined,
        });
        if (this.env.services["mail.thread"]) {
            this.threadService = useService("mail.thread");
        }
        this.uiService = useService("ui");
        this.hasAttachmentViewerInArch = false;

        const { archInfo } = this.props;

        const template = createElement("t");
        const xmlDocAttachmentPreview = archInfo.xmlDoc.querySelector("div.o_attachment_preview");
        if (xmlDocAttachmentPreview && xmlDocAttachmentPreview.parentNode.nodeName === "form") {
            // TODO hasAttachmentViewer should also depend on the groups= and/or invisible modifier on o_attachment_preview (see invoice form)
            template.appendChild(xmlDocAttachmentPreview);
            this.hasAttachmentViewerInArch = true;
            archInfo.arch = archInfo.xmlDoc.outerHTML;
        }

        const xmlDocChatter = archInfo.xmlDoc.querySelector("div.oe_chatter");
        if (xmlDocChatter && xmlDocChatter.parentNode.nodeName === "form") {
            template.appendChild(xmlDocChatter.cloneNode(true));
        }

        const mailTemplates = useViewCompiler(MailFormCompiler, archInfo.arch, { Mail: template }, {});
        this.mailTemplate = mailTemplates.Mail;

        this.onResize = useDebounced(this.render, 200);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));
    },
    /**
     * @returns {boolean}
     */
    hasAttachmentViewer() {
        if (
            !this.threadService ||
            this.uiService.size < SIZES.XXL ||
            !this.hasAttachmentViewerInArch ||
            !this.model.root.resId
        ) {
            return false;
        }
        this.messagingState.thread = this.threadService.insert({
            id: this.model.root.resId,
            model: this.model.root.resModel,
            type: "chatter",
        });
        return this.messagingState.thread.attachmentsInWebClientView.length > 0;
    },
    evalDomainFromRecord(record, expr) {
        return evalDomain(expr, record.evalContext);
    },
});

Object.assign(FormController.components, {
    AttachmentView,
    Chatter,
});
