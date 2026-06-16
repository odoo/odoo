import { Component, onPatched, onWillUpdateProps, props, proxy, t } from "@odoo/owl";

export const ACCORDION = Symbol("Accordion");
export class AccordionItem extends Component {
    static template = "web.AccordionItem";
    static components = {};
    props = props({
        slots: t.object({
            default: t.any(),
        }),
        description: t.string().optional,
        selected: t.boolean().optional(false),
        class: t.string().optional(""),
        onWillToggle: t.function().optional(() => () => {}),
        open: t.boolean().optional()
    });

    setup() {
        this.state = proxy({
            open: this.props.open,
        });
        this.parentComponent = this.env[ACCORDION];
        onPatched(() => {
            this.parentComponent?.accordionStateChanged?.();
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.open && !this.state.open) {
                this.state.open = true;
            }
        });
    }

    async toggle() {
        await this.props.onWillToggle();
        this.state.open = !this.state.open;
    }
}
