/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

export class MediaPreview extends owl.Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'audioRef', modelName: 'MediaPreview', propNameAsRecordLocalId: 'localId', refName: 'audio' });
        useRefToModel({ fieldName: 'videoRef', modelName: 'MediaPreview', propNameAsRecordLocalId: 'localId', refName: 'video' });
    }

    /**
     * @returns {MediaPreview}
     */
    get mediaPreview() {
        return this.messaging && this.messaging.models['MediaPreview'].get(this.props.localId);
    }
}

Object.assign(MediaPreview, {
    props: { localId: String },
    template: 'mail.MediaPreview',
});

registerMessagingComponent(MediaPreview);
