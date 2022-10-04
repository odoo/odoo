/** @odoo-module */

import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, 'mail', {
    get compileParams() {
        return {
            ...this._super(),
            hasAttachmentViewerInArch: this.props.hasAttachmentViewerInArch,
        };
    },
});

Object.assign(FormRenderer.components, {
    ChatterContainer,
});
