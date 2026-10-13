import { Tab, Tabs } from "@mail/core/common/tabs";
import { attClassObjectToString } from "@mail/utils/common/format";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component, signal, t, usePlugin, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useService } from "@web/core/utils/hooks";

export class PollVotesPanel extends Component {
    static components = { Dialog, Tabs, Tab };
    static template = "mail.PollVotesPanel";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]).optional(),
            poll: t.instanceOf(this.store["mail.poll"]),
        });
        this.ui = usePlugin(UIPlugin);
        this.tabsRef = signal.ref();
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
