/** @odoo-module */

import { Chatter } from "@mail/web/chatter";
import { AttachmentView } from "@mail/attachments/attachment_view";

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, "mail", {
    setup() {
        this._super();
        this.mailComponents = { AttachmentView, Chatter };
    },
    get compileParams() {
        return {
            ...this._super(),
            hasAttachmentViewerInArch: this.props.hasAttachmentViewerInArch,
            saveButtonClicked: this.props.saveButtonClicked,
        };
    },
});

patch(FormRenderer.props, "mail", {
    hasAttachmentViewerInArch: { type: Boolean, optional: true },
    // Template props : added by the FormCompiler
    hasAttachmentViewer: { type: Boolean, optional: true },
    chatter: { type: Object, optional: true },
    saveButtonClicked: { type: Function, optional: true },
});
