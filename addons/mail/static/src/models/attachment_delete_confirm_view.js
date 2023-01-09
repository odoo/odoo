/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { attr, clear, one, Model } from "@mail/model";
import { sprintf } from "@web/core/utils/strings";

Model({
    name: "AttachmentDeleteConfirmView",
    template: "mail.AttachmentDeleteConfirmView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
    },
    recordMethods: {
        /**
         * Returns whether the given html element is inside this attachment delete confirm view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(
                this.component && this.component.root.el && this.component.root.el.contains(element)
            );
        },
        onClickCancel() {
            this.dialogOwner.delete();
        },
        async onClickOk() {
            const chatter = this.chatter;
            await this.attachment.remove();
            if (chatter && chatter.exists() && chatter.shouldReloadParentFromFileChanged) {
                chatter.reloadParentView();
            }
        },
    },
    fields: {
        attachment: one("Attachment", {
            required: true,
            compute() {
                if (
                    this.dialogOwner &&
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm
                ) {
                    return this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachment;
                }
                if (
                    this.dialogOwner &&
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm
                ) {
                    return this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm
                        .attachment;
                }
                return clear();
            },
        }),
        body: attr({
            compute() {
                return sprintf(
                    this.env._t(`Do you really want to delete "%s"?`),
                    this.attachment.displayName
                );
            },
        }),
        chatter: one("Chatter", {
            compute() {
                if (
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm &&
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList
                        .chatterOwner
                ) {
                    return this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm
                        .attachmentList.chatterOwner;
                }
                if (
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm &&
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList
                        .chatterOwner
                ) {
                    return this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm
                        .attachmentList.chatterOwner;
                }
                return clear();
            },
        }),
        component: attr(),
        dialogOwner: one("Dialog", { identifying: true, inverse: "attachmentDeleteConfirmView" }),
    },
});
