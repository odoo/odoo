/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'LinkPreviewDeleteConfirmView',
    recordMethods: {
        /**
         * Returns whether the given html element is inside this attachment delete confirm view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onClickCancel() {
            this.dialogOwner.delete();
        },
        onClickOk() {
            this.linkPreview.remove();
        },
        /**
         * @private
         * @returns {LinkPreview}
         */
        _computeLinkPreview() {
            return this.dialogOwner.linkPreviewAsideViewOwnerAsLinkPreviewDeleteConfirm.linkPreview;
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'linkPreviewDeleteConfirmView',
        }),
        linkPreview: one('LinkPreview', {
            compute: '_computeLinkPreview',
            required: true,
        }),
    },
});
