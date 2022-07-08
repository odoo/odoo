/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { LegacyComponent } from '@web/legacy/legacy_component';

export class WebClientViewAttachmentView extends LegacyComponent {
    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'iframeViewerPdfRef', refName: 'iframeViewerPdf' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
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
    template: 'mail.WebClientViewAttachmentView',
});

registerMessagingComponent(WebClientViewAttachmentView);
