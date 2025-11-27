import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallPresentationBar extends Component {
    static template = "discuss.CallPresentationBar";
    static props = {};
    static components = { AvatarStack };

    setup() {
        this.rtc = useService("discuss.rtc");
        this.presentationAudio = useState({ enabled: this.rtc.screenAudioTrack?.enabled });
    }

    get presenterPersonas() {
        return this.presenterSessions.map((s) => s.channel_member_id.persona);
    }

    get presenterSessions() {
        const sessions = this.rtc.channel.rtc_session_ids.filter((s) => s.is_screen_sharing_on);
        if (!this.rtc.selfSession.is_screen_sharing_on) {
            return sessions;
        }
        return [this.rtc.selfSession, ...sessions.filter((s) => s.notEq(this.rtc.selfSession))];
    }

    get presenterText() {
        const presenterNames = this.presenterSessions.map((s) => s.channel_member_id.name);
        const presenterCount = presenterNames.length;
        if (this.rtc.selfSession.is_screen_sharing_on) {
            if (presenterCount === 1) {
                return _t("You are presenting");
            }
            if (presenterCount === 2) {
                return _t("You and %(name)s are presenting", { name: presenterNames[1] });
            }
            return _t("You, %(name)s and %(count)s more are presenting", {
                name: presenterNames[1],
                count: presenterCount - 2,
            });
        }
        if (presenterCount === 1) {
            return _t("%(name)s is presenting", { name: presenterNames[0] });
        }
        if (presenterCount === 2) {
            return _t("%(name_1)s and %(name_2)s are presenting", {
                name_1: presenterNames[0],
                name_2: presenterNames[1],
            });
        }
        return _t("%(name_1)s, %(name_2)s and %(count)s more are presenting", {
            name_1: presenterNames[0],
            name_2: presenterNames[1],
            count: presenterCount - 2,
        });
    }

    togglePresentationAudio() {
        this.rtc.screenAudioTrack.enabled = !this.rtc.screenAudioTrack.enabled;
        this.presentationAudio.enabled = this.rtc.screenAudioTrack.enabled;
    }
}
