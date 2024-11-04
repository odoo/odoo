import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class AskRecurrenceUpdatePolicyDialog extends Component {
    static template = "calendar.AskRecurrenceUpdatePolicyDialog";
    static components = {
        Dialog,
    };
    static props = {
        confirm: Function,
        close: Function,
    };

    setup() {
        this.possibleValues = {
            self_only: {
                checked: true,
                label: _t("This event"),
            },
            future_events: {
                checked: false,
                label: _t("This and following events"),
            },
            all_events: {
                checked: false,
                label: _t("All events"),
            },
        };
    }

    get selected() {
        return Object.entries(this.possibleValues).find((state) => state[1].checked)[0];
    }

    set selected(val) {
        this.possibleValues[this.selected].checked = false;
        this.possibleValues[val].checked = true;
    }

    confirm() {
        this.props.confirm(this.selected);
        this.props.close();
    }
}
