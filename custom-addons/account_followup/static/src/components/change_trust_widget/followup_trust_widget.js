/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { localization } from "@web/core/l10n/localization";
import { Component } from "@odoo/owl";

class FollowupTrustPopOver extends Component {}
FollowupTrustPopOver.template = "account_followup.FollowupTrustPopOver";

class FollowupTrustWidget extends Component {
    setup() {
        super.setup();
        const position = localization.direction === "rtl" ? "bottom" : "right";
        this.popover = usePopover(FollowupTrustPopOver, { position });
    }

    displayTrust() {
        var selections = this.props.record.fields.trust.selection;
        var trust = this.props.record.data[this.props.name];
        for (var i=0; i < selections.length; i++) {
            if (selections[i][0] == trust) {
                return selections[i][1];
            }
        }
    }

    onTrustClick(ev) {
        this.popover.open(ev.currentTarget, {
            record: this.props.record,
            widget: this,
        });
    }

    async setTrust(trust) {
        this.props.record.update({ [this.props.name]: trust });
        this.popover.close();
    }
}

FollowupTrustWidget.template = "account_followup.FollowupTrustWidget";
registry.category("fields").add("followup_trust_widget", {
    component: FollowupTrustWidget,
});
