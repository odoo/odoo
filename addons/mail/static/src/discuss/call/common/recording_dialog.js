import { Component, proxy, t, useEffect, useProps } from "@odoo/owl";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class RecordingDialog extends Component {
    static template = "discuss.RecordingDialog";
    static components = { CheckBox, Dialog };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const recordingState = this.store.rtc?.recordingState;
        this.state = proxy({
            transcription: recordingState?.recording ? recordingState.transcription : false,
            video: recordingState?.recording
                ? recordingState.video
                : Boolean(this.store.rtc?.canRecordAudio && this.store.rtc?.canRecordVideo),
        });
        this.props = useProps({ close: t.function([]) });
        useEffect(() => {
            if (!this.isRecording) {
                return;
            }
            this.state.transcription = Boolean(this.store.rtc.recordingState.transcription);
            this.state.video = Boolean(this.store.rtc.recordingState.video);
        });
    }

    get isRecording() {
        return this.store.rtc?.recordingState?.recording;
    }

    get canChangeTranscription() {
        return Boolean(this.store.rtc?.canRecordTranscription);
    }

    get isVideoDisabled() {
        return Boolean(
            this.isRecording || !this.store.rtc?.canRecordAudio || !this.store.rtc?.canRecordVideo
        );
    }

    get isRecordingActionDisabled() {
        return Boolean(
            this.store.rtc?.recordingRequest ||
                (!this.isRecording && !this.state.transcription && !this.state.video)
        );
    }

    get showUpdateButton() {
        return Boolean(
            this.isRecording &&
                this.canChangeTranscription &&
                this.state.transcription !== this.store.rtc?.recordingState?.transcription
        );
    }

    onChangeTranscription(checked) {
        if (!this.canChangeTranscription) {
            return;
        }
        this.state.transcription = checked;
    }

    onChangeVideo(checked) {
        if (this.isVideoDisabled) {
            return;
        }
        this.state.video = checked;
    }

    onClickRecording() {
        if (this.isRecording) {
            this.store.rtc.stopRecordingDebounce();
        } else {
            this.store.rtc.startRecordingDebounce({
                audio: this.state.video,
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
