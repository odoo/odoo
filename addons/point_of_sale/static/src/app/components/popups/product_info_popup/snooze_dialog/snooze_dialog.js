import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SnoozeDialog extends Component {
    static components = { Dialog };
    static props = ["close", "name", "onSave"];
    static template = "point_of_sale.SnoozeDialog";

    setup() {
        this.state = useState({ hours: 1 });
    }
    select(hours) {
        this.state.hours = hours;
    }
    save() {
        this.props.onSave(this.state.hours);
        this.props.close();
    }
    getSnoozeOptions() {
        return [
            { label: _t("1 Hour"), value: 1, id: "1hour" },
            { label: _t("2 Hours"), value: 2, id: "2hour" },
            { label: _t("4 Hours"), value: 4, id: "4hour" },
            { label: _t("Session"), value: 0, id: "session" },
        ];
    }
    get headerTitle() {
        return _t("Make %s unavailable for:", this.props.name);
    }
}
