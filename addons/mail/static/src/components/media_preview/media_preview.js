/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useHtmlRefToModel } from '@mail/component_hooks/use_html_ref_to_model/use_html_ref_to_model';

export class MediaPreview extends owl.Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useHtmlRefToModel({ fieldName: 'audioRef', modelName: 'mail.media_preview', propNameAsRecordLocalId: 'localId', refName: 'audio' });
        useHtmlRefToModel({ fieldName: 'videoRef', modelName: 'mail.media_preview', propNameAsRecordLocalId: 'localId', refName: 'video' });
    }

    /**
     * @returns {mail.media_preview}
     */
    get mediaPreview() {
        return this.messaging && this.messaging.models['mail.media_preview'].get(this.props.localId);
    }
}

Object.assign(MediaPreview, {
    props: { localId: String },
    template: 'mail.MediaPreview',
});

registerMessagingComponent(MediaPreview);
