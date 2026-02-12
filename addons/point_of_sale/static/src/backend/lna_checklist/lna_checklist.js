/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class LnaChecklistWidget extends Component {
    static template = "point_of_sale.PosConfigLnaChecklist";

    setup() {
        this.storage_key = "pos_lna_checklist";
        this.originalSave = this.props.record.save.bind(this.props.record);
        this.state = useState({ checks: {} });

        onWillStart(() => {
            try {
                this.state.checks = JSON.parse(localStorage.getItem(this.storage_key) || "{}");
            } catch {
                this.state.checks = {};
            }
        });

        onMounted(() => {
            this.props.record.save = async (...args) => {
                localStorage.setItem(this.storage_key, JSON.stringify(this.state.checks));

                return this.originalSave(...args);
            };
        });

        onWillUnmount(() => {
            this.props.record.save = this.originalSave;
        });
    }

    toggle(ev) {
        this.state.checks[ev.currentTarget.id] = ev.currentTarget.checked;
    }

    checked(key) {
        return this.state.checks[key];
    }
}

registry.category("view_widgets").add("lna_checklist", {
    component: LnaChecklistWidget,
});
