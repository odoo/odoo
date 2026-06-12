import { TabHeader, TabPanel, Tabs } from "@mail/core/common/tabs";
import { attClassObjectToString } from "@mail/utils/common/format";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";

export class PollVotesPanel extends Component {
    static components = { Dialog, Tabs, TabHeader, TabPanel };
    static template = "mail.PollVotesPanel";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            close: t.function([]).optional(),
            poll: t.instanceOf(this.store["mail.poll"].Class),
        });
        this.ui = useService("ui");
        this.tabsRef = useChildRef();
        onExternalClick(this.tabsRef, (ev) => {
            if (ev.target && !ev.target.closest(".modal-header")) {
                this.props.close?.();
            }
        });
    }

    /** @param {import("models").MailPollOptionModel} option */
    onTabPanelVisible(option) {
        option.fetchPollVotesCached.fetch();
    }

    get contentClass() {
        return attClassObjectToString({
            "h-50 d-flex": true,
            "position-absolute top-100 start-0": this.store.useMobileView,
        });
    }
}
