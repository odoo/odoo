import { TabHeader, TabPanel, Tabs } from "@mail/core/common/tabs";
import { attClassObjectToString } from "@mail/utils/common/format";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").MailPollModel} poll
 * @extends {Component<Props, Env>}
 */
export class PollVotesPanel extends Component {
    static template = "mail.PollVotesPanel";
    static props = ["poll", "close?"];
    static components = { Dialog, Tabs, TabHeader, TabPanel };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.tabsRef = useChildRef();
        onExternalClick(this.tabsRef, (ev) => {
            if (ev.target && !ev.target.closest(".modal-header")) {
                this.props.close?.();
            }
        });
        onWillStart(() => {
            this.props.poll.fetchPollOptionsCached();
        });
        onWillUpdateProps((next) => {
            if (next.poll?.notEq(this.props.poll)) {
                next.poll.fetchPollOptionsCached();
            }
        });
    }

    /** @param {import("models").MailPollOptionModel} option */
    onTabPanelVisible(option) {
        option.fetchPollVotesCached();
    }

    get contentClass() {
        return attClassObjectToString({
            "h-50 d-flex": true,
            "position-absolute top-100 start-0": this.store.useMobileView,
        });
    }
}
