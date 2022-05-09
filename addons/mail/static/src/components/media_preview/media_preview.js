/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MediaPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'audioRef', refName: 'audio' });
        useRefToModel({ fieldName: 'videoRef', refName: 'video' });
    }

    /**
     * @returns {MediaPreview}
     */
    get mediaPreview() {
        return this.props.record;
    }
}

Object.assign(MediaPreview, {
    props: { record: Object },
    template: 'mail.MediaPreview',
});

registerMessagingComponent(MediaPreview);
