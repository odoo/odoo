import { Component, onPatched, useState } from "@odoo/owl";

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
    };
    static defaultProps = {
        class: "",
        selected: false,
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
}
