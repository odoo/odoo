/* @odoo-module */

import { AttachmentView } from "@mail/new/attachments/attachment_view";
import { onMounted, onWillUnmount, useChildSubEnv, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { evaluateExpr } from "@web/core/py_js/py";
import { SIZES } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Chatter } from "./chatter";

FormController.components.Chatter = Chatter;
FormController.components.AttachmentView = AttachmentView;
FormRenderer.components.Chatter = Chatter;

function getOptions(xml) {
    return evaluateExpr((xml && xml.getAttribute("options")) || "{}");
}

patch(FormController.prototype, "mail/new", {
    setup() {
        this.messagingState = useState({
            /** @type {import("@mail/new/core/thread_model").Thread} */
            thread: undefined,
        });
        if (this.env.services["mail.thread"]) {
            this.threadService = useService("mail.thread");
        }

        this.onResize = useDebounced(this.render, 200);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));

        let hasAttachmentAndSheet = false;
        let hasActivities = false;
        let hasFollowers = false;
        let hasMessageList = false;
        let hasParentReloadOnAttachmentsChanged = false;
        let hasParentReloadOnFollowersUpdate = false;
        let hasParentReloadOnMessagePosted = false;
        let isAttachmentBoxVisibleInitially = false;
        const archXml = this.props.archInfo.xmlDoc;
        // check for attachment preview feature
        this.hasAttachment = false;
        const xmlAttachment = archXml.querySelector("div.o_attachment_preview");
        if (xmlAttachment) {
            this.hasAttachment = true;
        }

        // transform arch to add chatter feature
        const xmlChatter = archXml.querySelector("div.oe_chatter");
        this.hasChatter = Boolean(xmlChatter);
        if (this.hasChatter) {
            const xmlActivity = xmlChatter.querySelector("field[name='activity_ids']");
            const xmlFollowers = xmlChatter.querySelector("field[name='message_follower_ids']");
            const xmlMessageIds = xmlChatter.querySelector("field[name='message_ids']");
            hasActivities = Boolean(xmlActivity);
            hasFollowers = Boolean(xmlFollowers);
            hasMessageList = Boolean(xmlMessageIds);

            const messageOptions = getOptions(xmlMessageIds);
            const messageFollowerOptions = getOptions(xmlFollowers);
            isAttachmentBoxVisibleInitially = Boolean(
                messageOptions.open_attachments || messageFollowerOptions.open_attachments
            );
            hasParentReloadOnAttachmentsChanged = messageOptions.post_refresh === "always";
            hasParentReloadOnMessagePosted = Boolean(messageOptions.post_refresh);
            hasParentReloadOnFollowersUpdate = messageFollowerOptions.post_refresh;

            const doc = archXml.ownerDocument;
            const rootT = doc.createElement("div");
            rootT.setAttribute("chatter", "");
            rootT.setAttribute("class", "o_FormRenderer_chatterContainer");
            rootT.setAttribute("t-if", "__comp__.env.hasChatter()");
            const chatterTag = doc.createElement("Chatter");
            chatterTag.setAttribute(
                "t-props",
                "__comp__.env.getChatterProps(__comp__.props.record)"
            );
            rootT.appendChild(chatterTag);
            xmlChatter.replaceWith(rootT);
            if (this.hasAttachment) {
                const formSheetBgXml = archXml.querySelector("sheet");
                if (formSheetBgXml) {
                    hasAttachmentAndSheet = true;
                    const sheetChatter = rootT.cloneNode(true);
                    sheetChatter.setAttribute(
                        "class",
                        "o_FormRenderer_chatterContainer o-isInFormSheetBg"
                    );
                    sheetChatter.setAttribute("t-if", "__comp__.env.hasSheetChatter()");
                    formSheetBgXml.appendChild(sheetChatter);
                }
            }
        }
        useChildSubEnv({
            hasChatter: () =>
                !hasAttachmentAndSheet && (!this.hasSideChatter() || this.hasAttachmentViewer()),
            hasSheetChatter: () =>
                hasAttachmentAndSheet && (!this.hasSideChatter() || this.hasAttachmentViewer()),
            getChatterProps: this.getChatterProps.bind(this),
        });

        this._super();
        this.chatterBaseProps = {
            hasActivities,
            hasFollowers,
            hasMessageList,
            isAttachmentBoxVisibleInitially,
            hasParentReloadOnAttachmentsChanged,
            hasParentReloadOnFollowersUpdate,
            hasParentReloadOnMessagePosted,
            saveRecord: this.saveButtonClicked.bind(this),
        };
    },

    getChatterProps(record) {
        return {
            ...this.chatterBaseProps,
            threadId: record.resId,
            threadModel: record.resModel,
            displayName: record.data.display_name,
            webRecord: record,
        };
    },

    hasSideChatter() {
        return this.hasChatter && this.ui.size >= SIZES.XXL;
    },

    hasAttachmentViewer() {
        if (
            !this.threadService ||
            this.ui.size < SIZES.XXL ||
            !this.hasAttachment ||
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

    _isAttachmentBoxOpenedInitially(xmlDocChatter) {
        const messageField = xmlDocChatter.querySelector("field[name='message_ids']");
        const messageFollowerField = xmlDocChatter.querySelector(
            "field[name='message_follower_ids']"
        );
        const messageOptions = evaluateExpr(
            (messageField && messageField.getAttribute("options")) || "{}"
        );
        const messageFollowerOptions = evaluateExpr(
            (messageFollowerField && messageFollowerField.getAttribute("options")) || "{}"
        );
        return Boolean(
            messageOptions["open_attachments"] || messageFollowerOptions["open_attachments"]
        );
    },
});

patch(FormCompiler.prototype, "mail/new", {
    compileGenericNode(el, params) {
        if (el.hasAttribute("chatter")) {
            return el;
        }
        return this._super(el, params);
    },
    validateNode(node) {
        if (!node.hasAttribute("chatter")) {
            return this._super(node);
        }
    },
});
