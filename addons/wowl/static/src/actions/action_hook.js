/** @odoo-module **/

import { useBus } from "../core/hooks";
import { getScrollPosition, setScrollPosition } from "../utils/scrolling";

const { useComponent, onMounted, onWillUnmount } = owl.hooks;

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

  function exportState() {
    if (component.props.__exportState__) {
      let state = {};
      state[scrollSymbol] = getScrollPosition(component);
      if (params.export) {
        Object.assign(state, params.export());
      }
      component.props.__exportState__(state);
    }
  }

  onMounted(() => {
    if (component.props.state) {
      setScrollPosition(component, component.props.state[scrollSymbol]);
    }
    if (params.beforeLeave && component.props.__beforeLeave__) {
      component.props.__beforeLeave__(params.beforeLeave);
    }
  });
  onWillUnmount(exportState);

  useBus(component.env.bus, "ACTION_MANAGER:EXPORT_CONTROLLER_STATE", exportState);
}
