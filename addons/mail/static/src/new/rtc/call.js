/* @odoo-module */

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useMessaging, useStore } from "../core/messaging_hook";
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
        this.userSettings = useState(useService("mail.user_settings"));
        this.rtc = useRtc();
        this.store = useStore();
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

    get visibleCards() {
        const cards = [];
        const filterVideos = this.userSettings.showOnlyVideo && this.props.thread.videoCount > 0;
        for (const session of Object.values(this.props.thread.rtcSessions)) {
            if (!filterVideos || session.videoStream) {
                cards.push({
                    key: "session_" + session.id,
                    session,
                });
            }
        }
        if (!filterVideos) {
            for (const memberId of this.props.thread.invitedMemberIds) {
                cards.push({
                    key: "member_" + memberId,
                    member: this.store.channelMembers[memberId],
                });
            }
        }
        return cards;
    }
}
