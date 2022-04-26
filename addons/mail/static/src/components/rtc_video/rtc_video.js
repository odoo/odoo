/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcVideo extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {RtcVideoView}
     */
     get rtcVideoView() {
        return this.messaging && this.messaging.models['RtcVideoView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _update() {
        this._loadVideo();
    }

    /**
     * Since it is not possible to directly put a mediaStreamObject as the src
     * or src-object of the template, the video src is manually inserted into
     * the DOM.
     *
     */
    _loadVideo() {
        if (!this.root.el) {
            return;
        }
        if (!this.rtcVideoView) {
            return;
        }
        if (!this.rtcVideoView.rtcSession || !this.rtcVideoView.rtcSession.videoStream) {
            this.root.el.srcObject = undefined;
        } else {
            this.root.el.srcObject = this.rtcVideoView.rtcSession.videoStream;
        }
        this.root.el.load();
    }

}

Object.assign(RtcVideo, {
    props: { localId: String },
    template: 'mail.RtcVideo',
});

registerMessagingComponent(RtcVideo);
