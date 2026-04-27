/** @odoo-module */

import { formatDate, deserializeDate } from "@web/core/l10n/dates";
import { Dialog } from "@web/core/dialog/dialog";
import { user } from "@web/core/user";

import { useState, Component, onWillRender } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { groupBy, sortBy } from "@web/core/utils/arrays";

export class StudioApprovalInfos extends Component {
    static template = "StudioApprovalInfos";
    static components = { Dialog };
    static props = {
        isPopover: Boolean,
        approval: Object,
        close: { type: Function, optional: true },
    };

    setup() {
        this.user = user;
        const approval = this.props.approval;
        this.approval = approval;
        this.state = useState(approval.state);
        this.actionService = useService("action");
        onWillRender(() => {
            this.ruleIdToEntry = Object.fromEntries(
                this.state.entries.map((e) => [e.rule_id[0], e])
            );

            let ruleGrouped = groupBy(
                Object.values(this.props.approval.rules),
                "notification_order"
            );
            ruleGrouped = sortBy(
                Object.entries(ruleGrouped),
                ([key, group]) => parseInt(key),
                "desc"
            );

            let canRevoke = false;
            for (const group of ruleGrouped) {
                const localCanRevoke = canRevoke;
                group[1].forEach((r) => {
                    r._canRevoke = localCanRevoke;
                    canRevoke = canRevoke || r.can_validate;
                });
            }
        });
    }

    formatDate(val, format) {
        return formatDate(deserializeDate(val), { format });
    }

    getEntry(ruleId) {
        return this.ruleIdToEntry[ruleId];
    }

    setApproval(ruleId, approved) {
        return this.approval.setApproval(ruleId, approved);
    }

    canRevokeEntry(ruleId) {
        const rule = this.props.approval.rules[ruleId];
        const entry = this.getEntry(ruleId);
        return entry.user_id[0] === this.user.userId || rule._canRevoke;
    }

    cancelApproval(ruleId) {
        return this.approval.cancelApproval(ruleId);
    }

    openKanbanApprovalRules() {
        const { resModel, method, action } = this.approval;
        return this.actionService.doActionButton({
            type: "object",
            name: "open_kanban_rules",
            resModel: "studio.approval.rule",
            resIds: [],
            args: JSON.stringify([resModel, method, action]),
        });
    }
}
