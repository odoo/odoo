/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { localization } from "@web/core/l10n/localization";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class FollowupTrustPopOver extends Component {
    static template = "account_followup.FollowupTrustPopOver";
    static props = {
        record: Object,
        widget: Object,
        close: { optional: true, type: Function },
    };
}

class FollowupTrustWidget extends Component {
    static template = "account_followup.FollowupTrustWidget";
    static props = {...standardFieldProps};
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

registry.category("fields").add("followup_trust_widget", {
    component: FollowupTrustWidget,
});
