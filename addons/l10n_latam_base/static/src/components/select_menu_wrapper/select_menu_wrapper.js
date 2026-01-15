import { Component, useState } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useBus } from "@web/core/utils/hooks";

export class SelectMenuWrapper extends Component {
    static template = "l10n_latam_base.SelectMenuWrapper";
    static components = { SelectMenu };
    static props = {
        el: { optional: true, type: Object },
    };

    setup() {
        this.state = useState({
            choices: [],
            value: this.props.el.value,
        });
        this.state.choices = [...this.props.el.querySelectorAll("option")].filter((x) => x.value);
        this.props.el.classList.add("d-none");
        useBus(this.props.el, "select", (ev) => this.onSelect(ev.detail.value));
    }

    onSelect(value) {
        this.state.value = value;
        this.props.el.value = value;
        // Manually trigger the change event
        const event = new Event("change", { bubbles: true });
        this.props.el.dispatchEvent(event);
    }
}
