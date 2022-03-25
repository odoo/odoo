/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Plays the video as some browsers may not support or block autoplay.
     *
     * @private
     * @param {Event} ev
     */
    async _onVideoLoadedMetaData(ev) {
        try {
            await ev.target.play();
        } catch (error) {
            if (typeof error === 'object' && error.name === 'NotAllowedError') {
                // Ignored as some browsers may reject play() calls that do not
                // originate from a user input.
                return;
            }
            throw error;
        }
    }
}

Object.assign(RtcVideo, {
    props: { rtcSessionLocalId: String },
    template: 'mail.RtcVideo',
});

registerMessagingComponent(RtcVideo);
