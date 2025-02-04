import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

export class CreateLeadPanel extends Component {
    static template = "mail.CreateLeadPanel";
    static components = { ActionPanel };
    static props = ["thread", "close?"];

    setup() {
        super.setup();
        this.state = useState({
            leadTitle: "",
        });
        this.store = useService("mail.store");
        this.inputRef = useRef("inputRef");
        onMounted(() => {
            if (this.store.self.type === "partner" && this.props.thread) {
                this.inputRef.el.focus();
            }
        });
    }

    get title() {
        return _t("Create lead");
    }

    async createLead() {
        await this.props.thread.executeCommand(
            commandRegistry.get("lead", false),
            "/lead " + this.state.leadTitle
        );
        this.props.close();
    }
}
