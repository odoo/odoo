import { Component, useComponent, useState, useSubEnv, xml } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export function useDomState(getState) {
    const state = useState(getState());
    const component = useComponent();
    useBus(component.env.editorBus, "STEP_ADDED", () => {
        Object.assign(state, getState());
    });
    return state;
}

export class WithSubEnv extends Component {
    static template = xml`<t t-slot="default" />`;
    static props = {
        env: Object,
        slots: Object,
    };

    setup() {
        useSubEnv(this.props.env);
    }
}

export function useWeComponent() {
    const comp = useComponent();
    if (comp.props.applyTo) {
        // todo: react to the change of applyTo
        // todo: make sure that the code that read env.editingElement properly react to the change if editingElement changes
        // todo: make sure that if there is an action that changes the structure of the dom, the applyTo is re-calculed.
        useSubEnv({
            editingElement: comp.env.editingElement.querySelector(comp.props.applyTo),
        });
    }
}

export const basicContainerWeWidgetProps = {
    applyTo: { type: String, optional: true },
    // preview: { type: Boolean, optional: true },
    // reloadPage: { type: Boolean, optional: true },

    action: { type: String, optional: true },
    actionParam: { validate: () => true, optional: true },

    // Shorthand actions.
    classAction: { type: String, optional: true },
    attributeAction: { type: String, optional: true },
    dataAttributeAction: { type: String, optional: true },
    styleAction: { type: String, optional: true },
};
