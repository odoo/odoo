import { Component, onPatched, useProps, signal, t } from "@odoo/owl";

export const ACCORDION = Symbol("Accordion");
export class AccordionItem extends Component {
    static template = "web.AccordionItem";
    static components = {};
    props = useProps({
        slots: t.object({
            default: t.any(),
        }),
        description: t.string(),
        selected: t.boolean().optional(false),
        class: t.string().optional(""),
        onWillToggle: t.function().optional(() => () => {}),
        open: t.boolean().optional(),
    });

    userOpen = signal(null, { type: t.or([t.boolean(), t.literal(null)]) });

    setup() {
        this.parentComponent = this.env[ACCORDION];
        onPatched(() => {
            this.parentComponent?.accordionStateChanged?.();
        });
    }

    get isOpen() {
        return this.userOpen() ?? Boolean(this.props.open);
    }

    async toggle() {
        await this.props.onWillToggle();
        this.userOpen.set(!this.isOpen);
    }
}
