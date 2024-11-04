import { useComponent, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export function useDomState(getState) {
    const state = useState(getState());
    const component = useComponent();
    useBus(component.env.editorBus, "STEP_ADDED", () => {
        Object.assign(state, getState());
    });
    return state;
}
