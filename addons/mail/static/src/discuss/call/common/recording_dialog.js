import { Component, signal, t, useEffect, useProps } from "@odoo/owl";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class RecordingDialog extends Component {
    static template = "discuss.RecordingDialog";
    static components = { CheckBox, Dialog };

    close = useProps.static("close", t.function([]));

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const recordingState = this.store.rtc?.recordingState;
        const isRecording = this.store.rtc?.isRecording();
        this.state = signal.Object({
            transcription: isRecording ? recordingState.transcription : false,
            video: isRecording
                ? recordingState.video
                : Boolean(this.store.rtc?.can_record_audio && this.store.rtc?.can_record_video),
        });
        useEffect(() => {
            if (!this.store.rtc?.isRecording()) {
                return;
            }
            this.state.set({
                transcription: Boolean(this.store.rtc.recordingState.transcription),
                video: Boolean(this.store.rtc.recordingState.video),
            });
        });
    }

    canChangeTranscription() {
        const rtc = this.store.rtc;
        return Boolean(
            rtc?.can_record_transcription &&
                (!rtc?.isRecording() || rtc.recordingState.audio || rtc.recordingState.video)
        );
    }

    isVideoDisabled() {
        return Boolean(
            this.store.rtc?.isRecording() ||
                !this.store.rtc?.can_record_audio ||
                !this.store.rtc?.can_record_video
        );
    }

    isRecordingActionDisabled() {
        return Boolean(
            this.store.rtc?.recordingRequest ||
                (!this.store.rtc?.isRecording() && !this.state().transcription && !this.state().video)
        );
    }

    showUpdateButton() {
        return Boolean(
            this.store.rtc?.isRecording() &&
                this.canChangeTranscription() &&
                this.state().transcription !== this.store.rtc?.recordingState?.transcription
        );
    }

    onChangeTranscription(checked) {
        if (!this.canChangeTranscription()) {
            return;
        }
        this.state().transcription = checked;
    }

    onChangeVideo(checked) {
        if (this.isVideoDisabled()) {
            return;
        }
        this.state().video = checked;
    }

    onClickStartRecording() {
        this.store.rtc.setRecording({
            audio: this.state().video,
            transcription: this.state().transcription,
            video: this.state().video,
        });
        this.close();
    }

    onClickStopRecording() {
        this.store.rtc.stopRecording();
        this.close();
    }

    onClickUpdate() {
        this.store.rtc.setRecording({ transcription: this.state().transcription });
        this.close();
    }
}
