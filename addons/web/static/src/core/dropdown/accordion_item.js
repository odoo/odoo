import { useState } from "@web/owl2/utils";
import { Component, onPatched } from "@odoo/owl";

export const ACCORDION = Symbol("Accordion");
export class AccordionItem extends Component {
    static template = "web.AccordionItem";
    static components = {};
    static props = {
        slots: {
            type: Object,
            shape: {
                default: {},
            },
        },
        description: String,
        selected: {
            type: Boolean,
            optional: true,
        },
        class: {
            type: String,
            optional: true,
        },
        onWillToggle: {
            type: Function,
            optional: true,
        },
    };
    static defaultProps = {
        class: "",
        selected: false,
        onWillToggle: () => {},
    };

    setup() {
        this.state = useState({
            open: false,
        });
        this.parentComponent = this.env[ACCORDION];
        onPatched(() => {
            this.parentComponent?.accordionStateChanged?.();
        });
    }

    async toggle() {
        await this.props.onWillToggle();
        this.state.open = !this.state.open;
    }
}
