/** @odoo-module */

import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
import { WebClientViewAttachmentViewContainer } from "@mail/components/web_client_view_attachment_view_container/web_client_view_attachment_view_container";

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
    chatter: { type: Object, optional: true },
});

Object.assign(FormRenderer.components, {
    ChatterContainer,
    WebClientViewAttachmentViewContainer,
});
