import { attClassObjectToString } from "@mail/utils/common/format";
import { useDialogCloseOnClickAway } from "@mail/utils/common/hooks";
import { TabHeader, TabPanel, Tabs } from "@mail/core/common/tabs";

import { Component, signal, t, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class PollVotesPanel extends Component {
    static components = { Dialog, Tabs, TabHeader, TabPanel };
    static template = "mail.PollVotesPanel";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]).optional(),
            poll: t.instanceOf(this.store["mail.poll"]),
        });
        this.ui = useService("ui");
        this.modalRef = signal.ref();
        useDialogCloseOnClickAway(this.modalRef, () => this.props.close?.());
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
