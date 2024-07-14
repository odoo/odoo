/** @odoo-module */

import { formatDate, deserializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

import { useState, Component } from "@odoo/owl";

export class StudioApprovalInfos extends Component {
    setup() {
        this.user = useService("user");
        const approval = this.props.approval;
        this.approval = approval;
        this.state = useState(approval.state);
    }

    formatDate(val, format) {
        return formatDate(deserializeDate(val), { format });
    }

    getEntry(ruleId) {
        return this.state.entries.find((e) => e.rule_id[0] === ruleId);
    }

    setApproval(ruleId, approved) {
        return this.approval.setApproval(ruleId, approved);
    }

    cancelApproval(ruleId) {
        return this.approval.cancelApproval(ruleId);
    }
}
StudioApprovalInfos.template = "StudioApprovalInfos";
StudioApprovalInfos.components = { Dialog };
