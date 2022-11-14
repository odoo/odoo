/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { attr, one, Model } from "@mail/model";

Model({
    name: "LinkPreviewDeleteConfirmView",
    template: "mail.LinkPreviewDeleteConfirmView",
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
        onClickOk() {
            this.linkPreview.remove();
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one("Dialog", { identifying: true, inverse: "linkPreviewDeleteConfirmView" }),
        linkPreview: one("LinkPreview", {
            required: true,
            compute() {
                return this.dialogOwner.linkPreviewAsideViewOwnerAsLinkPreviewDeleteConfirm
                    .linkPreview;
            },
        }),
    },
});
