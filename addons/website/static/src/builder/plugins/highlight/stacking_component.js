import { xml, Component, reactive, useState, useEffect } from "@odoo/owl";
import { POSITION_BUS } from "@web/core/position/position_hook";

export function useStackingComponentState() {
    const stack = reactive([]);
    let counter = 0;
    const push = (component, props, title, withPrevious) => {
        stack.push({ id: counter++, component, props, title, withPrevious });
    };
    const pop = () => stack.pop();

    return { push, pop, stack };
}

export class StackingComponent extends Component {
    static template = xml`
        <t t-foreach="this.stack" t-as="componentSpec" t-key="componentSpec.id">
            <div t-if="componentSpec_last" t-attf-class="{{this.props.class}} {{componentSpec_last ? '': 'd-none' }}" t-att-style="this.props.style">
                <div t-if="this.stack.length > 1 || componentSpec.title" class="d-flex align-items-center">
                    <button t-if="this.stack.length > 1 and componentSpec.withPrevious" class="fa fa-angle-left btn btn-secondary bg-transparent border-0" t-on-click="this.props.stackState.pop"></button>
                    <span t-out="componentSpec.title" class="lead mb-0"/>
                </div>
                <t t-component="componentSpec.component" t-props="componentSpec.props" />
            </div>
        </t>
    `;
    static props = {
        stackState: { type: Object, required: true },
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        close: { type: Function, optional: true },
    };
    setup() {
        this.stack = useState(this.props.stackState.stack);
        useEffect(
            () => {
                // Recompute the positioning of the popover if any.
                this.env[POSITION_BUS]?.trigger("update");
            },
            () => [this.stack.length]
        );
    }
}
