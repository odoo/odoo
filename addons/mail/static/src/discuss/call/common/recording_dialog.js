import { Component, proxy } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

export class RecordingDialog extends Component {
    static template = "discuss.RecordingDialog";
    static props = ["close"];
    static components = { Dialog };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const recordingState = this.store.rtc?.recordingState;
        this.state = proxy({
            audio: recordingState?.recording ? recordingState.audio : true,
            video: recordingState?.recording ? recordingState.video : false,
            transcription: recordingState?.recording ? recordingState.transcription : false,
        });
    }

    get isRecording() {
        return this.store.rtc?.recordingState?.recording;
    }

    get canChangeTranscription() {
        if (this.isRecording) {
            return this.store.rtc?.recordingState?.audio;
        }
        return this.state.audio;
    }

    get showUpdateButton() {
        if (!this.isRecording) {
            return false;
        }
        if (!this.store.rtc?.recordingState?.audio) {
            return false;
        }
        if (!this.store.rtc.canTranscribe) {
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
                video: this.state.video,
            });
        }
        this.props.close();
    }

    onClickUpdate() {
        this.store.rtc.startRecordingDebounce({ transcription: this.state.transcription });
        this.props.close();
    }
}
