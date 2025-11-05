import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

export class RecordingDialog extends Component {
    static template = "discuss.RecordingDialog";
    static props = [ "close" ];
    static components = { Dialog };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const recordingState = this.store.rtc?.recordingState;
        this.state = useState({
            audio: recordingState?.recording ? recordingState.audio : true,
            video: recordingState?.recording ? recordingState.video : false,
            transcription: recordingState?.recording ? recordingState.transcription : false,
        });
    }

    get isRecording() {
        return this.store.rtc?.recordingState?.recording;
    }

    get canChangeTranscription() {
        // Can only change transcription if audio is enabled (either currently recording with audio, or selected)
        if (this.isRecording) {
            return this.store.rtc?.recordingState?.audio;
        }
        return this.state.audio;
    }

    get recordingButtonText() {
        if (this.isRecording) {
            return "Stop recording";
        }
        return "Start recording";
    }

    get updateButtonText() {
        return "Update";
    }

    get showUpdateButton() {
        // Show update button when recording and transcription state differs from current
        // Can only update if audio is true (transcription requires audio)
        if (!this.isRecording) {
            return false;
        }
        if (!this.store.rtc?.recordingState?.audio) {
            return false;
        }
        return this.state.transcription !== this.store.rtc?.recordingState?.transcription;
    }

    onClickRecording() {
        if (this.isRecording) {
            this.store.rtc.stopRecordingDebounce();
        } else {
            this.store.rtc.startRecordingDebounce({
                audio: this.state.audio,
                transcription: this.state.transcription,
                video: this.state.video
            });
        }
        this.props.close();
    }

    onClickUpdate() {
        // Update transcription while recording (audio must be true for this to work)
        this.store.rtc.startRecordingDebounce({
            audio: this.store.rtc.recordingState.audio,
            transcription: this.state.transcription,
            video: this.store.rtc.recordingState.video
        });
        this.props.close();
    }
}
