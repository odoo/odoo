/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;

export class MediaPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'audioRef', modelName: 'MediaPreview', refName: 'audio' });
        useRefToModel({ fieldName: 'videoRef', modelName: 'MediaPreview', refName: 'video' });
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
