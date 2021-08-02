/** @odoo-module **/

import { getScrollPosition, setScrollPosition } from "@web/core/utils/scrolling";
import { useEffect } from "@web/core/utils/hooks";

const { useComponent } = owl.hooks;

// -----------------------------------------------------------------------------
// Action hook
// -----------------------------------------------------------------------------
const scrollSymbol = Symbol("scroll");

/**
 * This hooks should be used by Action Components (client actions or views). It
 * allows to implement the 'export' feature which aims at restoring the state
 * of the Component when we come back to it (e.g. using the breadcrumbs).
 */
export function useSetupAction(params) {
    const component = useComponent();

    useEffect(
        () => {
            if (component.props.registerCallback) {
                if (params.beforeLeave) {
                    component.props.registerCallback("beforeLeave", params.beforeLeave);
                }
                component.props.registerCallback("export", () => {
                    const state = {};
                    state[scrollSymbol] = getScrollPosition(component);
                    if (params.export) {
                        Object.assign(state, params.export());
                    }
                    return state;
                });
            }
            if (component.props.state) {
                setScrollPosition(component, component.props.state[scrollSymbol]);
            }
        },
        () => []
    );
}
