/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "CallParticipantVideoView",
    template: "mail.CallParticipantVideoView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        useUpdateToModel({ methodName: "onComponentUpdate" });
    },
    recordMethods: {
        /**
         * Since it is not possible to directly put a mediaStreamObject as the src
         * or src-object of the template, the video src is manually inserted into
         * the DOM.
         */
        onComponentUpdate() {
            if (!this.component.root.el) {
                return;
            }
            if (!this.rtcSession || !this.rtcSession.videoStream) {
                this.component.root.el.srcObject = undefined;
            } else {
                this.component.root.el.srcObject = this.rtcSession.videoStream;
            }
            this.component.root.el.load();
        },
        /**
         * Plays the video as some browsers may not support or block autoplay.
         *
         * @param {Event} ev
         */
        async onVideoLoadedMetaData(ev) {
            try {
                await ev.target.play();
            } catch (error) {
                if (typeof error === "object" && error.name === "NotAllowedError") {
                    // Ignored as some browsers may reject play() calls that do not
                    // originate from a user input.
                    return;
                }
                throw error;
            }
        },
    },
    fields: {
        callParticipantCardOwner: one("CallParticipantCard", {
            identifying: true,
            inverse: "callParticipantVideoView",
        }),
        component: attr(),
        rtcSession: one("RtcSession", {
            compute() {
                if (this.callParticipantCardOwner.rtcSession) {
                    return this.callParticipantCardOwner.rtcSession;
                }
                return clear();
            },
        }),
    },
});
