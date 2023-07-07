/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "DeleteMessageConfirmView",
    template: "mail.DeleteMessageConfirmView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
    },
    recordMethods: {
        /**
         * Returns whether the given html element is inside this delete message confirm view.
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
        onClickDelete() {
            this.message.updateContent({
                attachment_ids: [],
                attachment_tokens: [],
                body: "",
            });
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one("Dialog", { identifying: true, inverse: "deleteMessageConfirmView" }),
        message: one("Message", {
            required: true,
            compute() {
                return this.dialogOwner.messageActionViewOwnerAsDeleteConfirm.messageAction
                    .messageActionListOwner.message;
            },
        }),
        /**
         * Determines the message view that this delete message confirm view
         * will use to display this message.
         */
        messageView: one("MessageView", {
            inverse: "deleteMessageConfirmViewOwner",
            required: true,
            compute() {
                return this.message ? { message: this.message } : clear();
            },
        }),
    },
});
