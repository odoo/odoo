/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { formatDuration } from "./call_debrief_utils";

export class CallDebriefMediaControls extends Component {
    static template = "mail.CallDebriefMediaControls";
    static props = {
        isPlaying: { type: Boolean },
        volume: Number,
        isMuted: Boolean,
        playbackRate: Number,
        playbackRates: Array,
        currentTime: Number,
        totalDuration: Number,
        media: { type: Object, optional: true },
        onTogglePlay: Function,
        onSeek: Function,
        onSetPlaybackRate: Function,
        onSetVolume: Function,
        onToggleMute: Function,
        feedback: { type: Object, optional: true },
    };

    setup() {
        this.state = useState({
            isVolumeSliderVisible: false,
        });
        this.formatDuration = formatDuration;
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
        this.state.isVolumeSliderVisible = true;
    }

    hideVolumeSlider() {
        this.state.isVolumeSliderVisible = false;
    }
}
