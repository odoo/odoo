import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread_model";
/**
 * @typedef {Object} Props
 * @property {import(models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallParticipants extends Component {
    static template = "mail.DiscussSidebarCallParticipants";
    static props = { thread: { type: Thread } };
    static components = {};

    setup() {
        super.setup();
        this.rtc = useState(useService("discuss.rtc"));
    }

    get participants() {
        return this.props.thread.rtcSessions?.sort((s1, s2) => {
            return (
                s1.channelMember?.persona?.nameOrDisplayName?.localeCompare(
                    s2.channelMember?.persona?.nameOrDisplayName
                ) ?? 1
            );
        });
    }
}
