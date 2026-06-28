import { Component, onPatched, props, proxy, t } from "@odoo/owl";

export const ACCORDION = Symbol("Accordion");
export class AccordionItem extends Component {
    static template = "web.AccordionItem";
    static components = {};
    props = props({
        slots: t.object({
            default: t.any(),
        }),
        description: t.string(),
        selected: t.boolean().optional(false),
        class: t.string().optional(""),
        onWillToggle: t.function().optional(() => () => {}),
    });

    setup() {
        this.state = proxy({
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
