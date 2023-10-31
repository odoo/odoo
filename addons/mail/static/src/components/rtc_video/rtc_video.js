/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component } = owl;
const { useRef } = owl.hooks;

export class RtcVideo extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        this._videoRef = useRef("video");
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get rtcSession() {
        return this.messaging.models["mail.rtc_session"].get(
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
        if (!this._videoRef) {
            return;
        }
        if (!this.rtcSession || !this.rtcSession.videoStream) {
            this._videoRef.el.srcObject = undefined;
        } else {
            this._videoRef.el.srcObject = this.rtcSession.videoStream;
        }
        this._videoRef.el.load();
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
    props: {
        rtcSessionLocalId: {
            type: String,
        },
    },
    template: 'mail.RtcVideo',
});

registerMessagingComponent(RtcVideo);
