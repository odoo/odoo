/* @odoo-module */

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useMessaging } from "../core/messaging_hook";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { CallMain } from "@mail/new/rtc/call_main";
import { CallParticipantCard } from "@mail/new/rtc/call_participant_card";
import { _t } from "@web/core/l10n/translation";

export class Call extends Component {
    static components = { CallMain, CallParticipantCard };
    static props = ["thread", "compact?"];
    static template = "mail.call";

    setup() {
        this.messaging = useMessaging();
        this.notification = useService("notification");
        this.rtc = useRtc();
        this.state = useState({
            isFullscreen: false,
            sidebar: false,
        });
        this.onFullScreenChange = this.onFullScreenChange.bind(this);
        onMounted(() => {
            browser.addEventListener("fullscreenchange", this.onFullScreenChange);
        });
        onWillUnmount(() => {
            browser.removeEventListener("fullscreenchange", this.onFullScreenChange);
        });
    }

    get minimized() {
        if (this.state.isFullscreen || this.props.compact || this.props.thread.activeRtcSession) {
            return false;
        }
        if (this.rtc.state.channel !== this.props.thread || this.props.thread.videoCount === 0) {
            return true;
        }
        return false;
    }

    async enterFullScreen() {
        const el = document.body;
        try {
            if (el.requestFullscreen) {
                await el.requestFullscreen();
            } else if (el.mozRequestFullScreen) {
                await el.mozRequestFullScreen();
            } else if (el.webkitRequestFullscreen) {
                await el.webkitRequestFullscreen();
            }
            this.state.isFullscreen = true;
        } catch {
            this.state.isFullscreen = false;
            this.notification.add(_t("The Fullscreen mode was denied by the browser"), {
                type: "warning",
            });
        }
    }

    async exitFullScreen() {
        const fullscreenElement = document.webkitFullscreenElement || document.fullscreenElement;
        if (fullscreenElement) {
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            } else if (document.mozCancelFullScreen) {
                await document.mozCancelFullScreen();
            } else if (document.webkitCancelFullScreen) {
                await document.webkitCancelFullScreen();
            }
        }
        this.state.isFullscreen = false;
    }

    /**
     * @private
     */
    onFullScreenChange() {
        this.state.isFullscreen = Boolean(
            document.webkitFullscreenElement || document.fullscreenElement
        );
    }

    get visibleSessions() {
        // TODO filter them based on settings "video only" when settings is done
        /* skip session if
            settings.showOnlyVideo &&
            thread.videoCount > 0 &&
            !channelMember.isStreaming (should be = rtcSession.videoStream)
        */
        return [...Object.values(this.props.thread.rtcSessions)];
    }
}
