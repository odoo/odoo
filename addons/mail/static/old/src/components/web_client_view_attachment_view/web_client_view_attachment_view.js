/** @odoo-module **/

import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { registerMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from "@odoo/owl";

export class WebClientViewAttachmentView extends Component {
    /**
     * @override
     */
    setup() {
        useRefToModel({ fieldName: "iframeViewerPdfRef", refName: "iframeViewerPdf" });
        useUpdateToModel({ methodName: "onComponentUpdate" });
    }
    /**
     * @returns {WebClientViewAttachmentView}
     */
    get webClientViewAttachmentView() {
        return this.props.record;
    }
}

Object.assign(WebClientViewAttachmentView, {
    props: { record: Object },
    template: "mail.WebClientViewAttachmentView",
});

registerMessagingComponent(WebClientViewAttachmentView);
