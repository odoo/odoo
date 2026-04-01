import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Typing } from "@mail/discuss/typing/common/typing";

import { Component, useState, useSubEnv } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useChildRef, useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} [thread]
 * @extends {Component<Props, Env>}
 */
export class MeetingChat extends Component {
    static template = "mail.MeetingChat";
    static components = {
        ActionPanel,
        Composer,
        Thread,
        Typing,
    };
    static props = ["thread?"];

    setup() {
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        this.state = useState({ jumpPresent: 0 });
        this.panelContentRef = useChildRef();
        this.isMobileOS = isMobileOS();
        useSubEnv({ inMeetingChat: true });
    }

    get thread() {
        return this.store.rtc.channel;
    }
}
