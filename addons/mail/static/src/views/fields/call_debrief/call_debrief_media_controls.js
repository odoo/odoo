import { Component, props } from "@odoo/owl";
import { formatDuration } from "@mail/views/fields/call_debrief/call_debrief_utils";
import { _t } from "@web/core/l10n/translation";
import { isMobileOS } from "@web/core/browser/feature_detection";

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
        mediaUrl: { type: String, optional: true },
        onTogglePlay: { type: Function },
        onSeek: { type: Function },
        onSetPlaybackRate: { type: Function },
        onSetVolume: { type: Function },
        onToggleMute: { type: Function },
        feedback: { type: Object, optional: true },
        hasVideo: { type: Boolean, optional: true },
        isFullscreen: { type: Boolean, optional: true },
        onToggleFullscreen: { type: Function, optional: true },
    };

    props = props();

    setup() {
        this.isMobileOS = isMobileOS();
    }

    formatDuration(seconds) {
        return formatDuration(seconds, this.props.totalDuration);
    }

    downloadMedia() {
        window.open(this.props.mediaUrl + "?download=1", "_blank");
    }

    get formattedTotalDuration() {
        return this.formatDuration(this.props.totalDuration);
    }

    get volumeIconClass() {
        if (this.props.isMuted || this.props.volume === 0) {
            return "fa-volume-off";
        }
        if (this.props.volume < 0.5) {
            return "fa-volume-down";
        }
        return "fa-volume-up";
    }

    get playPauseTooltip() {
        return !this.isMobileOS ? (this.props.isPlaying ? _t("Pause (K)") : _t("Play (K)")) : '';
    }

    get skipBackwardTooltip() {
        return !this.isMobileOS ? 'Skip backward (J)' : '';
    }

    get skipForwardTooltip() {
        return !this.isMobileOS ? 'Skip forward (L)' : '';
    }

    get muteTooltip() {
        return !this.isMobileOS ? (this.props.isMuted ? _t("Unmute (M)") : _t("Mute (M)")) : '';
    }

    get fullscreenTooltip() {
        return !this.isMobileOS ? (this.props.isFullscreen ? _t("Exit fullscreen (F)") : _t("Fullscreen (F)")) : '';
    }

    get downloadTooltip() {
        return !this.isMobileOS ? _t("Download") : '';
    }
}
