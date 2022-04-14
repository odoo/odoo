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
     * @returns {RtcSession|undefined}
     */
    get rtcSession() {
        return this.messaging.models['RtcSession'].get(
            this.props.rtcSessionLocalId
        );
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
        if (!this.rtcSession || !this.rtcSession.videoStream) {
            this.root.el.srcObject = undefined;
        } else {
            this.root.el.srcObject = this.rtcSession.videoStream;
        }
        this.root.el.load();
    }

}

Object.assign(RtcVideo, {
    props: { rtcSessionLocalId: String },
    template: 'mail.RtcVideo',
});

registerMessagingComponent(RtcVideo);
