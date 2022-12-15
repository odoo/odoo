/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallParticipantVideo extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallParticipantVideoView}
     */
     get callParticipantVideoView() {
        return this.props.record;
    }

    /**
     * Determine if video should be mirrored for user's own card when video is on
     * @returns {boolean}
     */
     get isVideoMirrored() {
        return this.callParticipantVideoView.callParticipantCardOwner.channelMember.isMemberOfCurrentUser
            && this.callParticipantVideoView.callParticipantCardOwner.rtcSession.isCameraOn;
    }
}

Object.assign(CallParticipantVideo, {
    props: { record: Object },
    template: 'mail.CallParticipantVideo',
});

registerMessagingComponent(CallParticipantVideo);
