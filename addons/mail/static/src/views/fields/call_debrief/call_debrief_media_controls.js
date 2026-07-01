import { Component, props, t } from "@odoo/owl";
import { formatDuration } from "@mail/views/fields/call_debrief/call_debrief_utils";
import { _t } from "@web/core/l10n/translation";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class CallDebriefMediaControls extends Component {
    static template = "mail.CallDebriefMediaControls";
    setup() {
        super.setup();
        this.props = props({
            isPlaying: t.boolean(),
            volume: t.number(),
            isMuted: t.boolean(),
            playbackRate: t.number(),
            playbackRates: t.array(),
            currentTime: t.number(),
            totalDuration: t.number(),
            mediaUrl: t.string().optional(),
            onTogglePlay: t.function(),
            onSeek: t.function(),
            onSetPlaybackRate: t.function(),
            onSetVolume: t.function(),
            onToggleMute: t.function(),
            feedback: t.object().optional(),
            hasVideo: t.boolean().optional(),
            isFullscreen: t.boolean().optional(),
            onToggleFullscreen: t.function().optional(),
        });
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
        return !this.isMobileOS ? (this.props.isPlaying ? _t("Pause (K)") : _t("Play (K)")) : "";
    }

    get skipBackwardTooltip() {
        return !this.isMobileOS ? "Skip backward (J)" : "";
    }

    get skipForwardTooltip() {
        return !this.isMobileOS ? "Skip forward (L)" : "";
    }

    get muteTooltip() {
        return !this.isMobileOS ? (this.props.isMuted ? _t("Unmute (M)") : _t("Mute (M)")) : "";
    }

    get fullscreenTooltip() {
        return !this.isMobileOS
            ? this.props.isFullscreen
                ? _t("Exit fullscreen (F)")
                : _t("Fullscreen (F)")
            : "";
    }

    get downloadTooltip() {
        return !this.isMobileOS ? _t("Download") : "";
    }
}
