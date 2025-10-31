import { Component, props, signal } from "@odoo/owl";

export class CallDebriefMediaControls extends Component {
    static template = "mail.CallDebriefMediaControls";
    static props = {
        isPlaying: { type: Boolean },
        volume: { type: Number },
        isMuted: { type: Boolean },
        playbackRate: { type: Number },
        playbackRates: { type: Array },
        currentTime: { type: Number },
        totalDuration: { type: Number },
        media: { type: Object, optional: true },
        onTogglePlay: { type: Function },
        onSeek: { type: Function },
        onSetPlaybackRate: { type: Function },
        onSetVolume: { type: Function },
        onToggleMute: { type: Function },
        feedback: { type: Object, optional: true },
    };

    props = props();

    setup() {
        this.isVolumeSliderVisible = signal(false);
    }

    get volumeIconClass() {
        if (this.props.isMuted || this.props.volume === 0) {
            return "fa fa-volume-off";
        }
        if (this.props.volume < 0.5) {
            return "fa fa-volume-down";
        }
        return "fa fa-volume-up";
    }

    showVolumeSlider() {
        this.isVolumeSliderVisible.set(true);
    }

    hideVolumeSlider() {
        this.isVolumeSliderVisible.set(false);
    }
}
