/** @odoo-module */

import { Chatter } from "@mail/new/web/chatter";
import { AttachmentView } from "@mail/new/attachments/attachment_view";

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, "mail", {
    get compileParams() {
        return {
            ...this._super(),
            hasAttachmentViewerInArch: this.props.hasAttachmentViewerInArch,
        };
    },
});

patch(FormRenderer.props, "mail", {
    hasAttachmentViewerInArch: { type: Boolean, optional: true },
    // Template props : added by the FormCompiler
    hasAttachmentViewer: { type: Boolean, optional: true },
});

Object.assign(FormRenderer.components, {
    AttachmentView,
    Chatter,
});
