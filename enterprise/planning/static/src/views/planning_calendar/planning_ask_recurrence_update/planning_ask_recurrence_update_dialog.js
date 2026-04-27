/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class PlanningAskRecurrenceUpdateDialog extends Component {
    static template = "planning.PlanningAskRecurrenceUpdateDialog";
    static components = {
        Dialog,
    };
    static props = {
        confirm: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.possibleValues = {
            this: {
                checked: true,
                label: _t("This shift"),
            },
            subsequent: {
                checked: false,
                label: _t("This and following shifts"),
            },
            all: {
                checked: false,
                label: _t("All shifts"),
            },
        };
    }

    get selected() {
        return Object.entries(this.possibleValues).find(state => state[1].checked)[0];
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
