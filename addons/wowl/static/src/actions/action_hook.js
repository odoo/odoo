/** @odoo-module **/

const { useComponent, onMounted, onWillUnmount } = owl.hooks;

// -----------------------------------------------------------------------------
// Action hook
// -----------------------------------------------------------------------------
const scrollSymbol = Symbol("scroll");

/**
 * Retrieve the current top and left scroll position. By default, the scrolling
 * area is the '.o_content' main div. In mobile, it is the body.
 */
function getScrollPosition(component) {
  let scrollingEl;
  if (component.env.isSmall) {
    scrollingEl = document.body;
  } else {
    scrollingEl = component.el.querySelector(".o_action_manager .o_content");
  }
  return {
    left: scrollingEl ? scrollingEl.scrollLeft : 0,
    top: scrollingEl ? scrollingEl.scrollTop : 0,
  };
}

/**
 * Set top and left scroll positions to the given values. By default, the
 * scrolling area is the '.o_content' main div. In mobile, it is the body.
 */
function setScrollPosition(component, offset) {
  let scrollingEl;
  if (component.env.isSmall) {
    scrollingEl = document.body;
  } else {
    scrollingEl = component.el.querySelector(".o_action_manager .o_content");
  }
  if (scrollingEl) {
    scrollingEl.scrollLeft = offset.left || 0;
    scrollingEl.scrollTop = offset.top || 0;
  }
}

/**
 * This hooks should be used by Action Components (client actions or views). It
 * allows to implement the 'export' feature which aims at restoring the state
 * of the Component when we come back to it (e.g. using the breadcrumbs).
 */
export function useSetupAction(params) {
  const component = useComponent();
  onMounted(() => {
    if (component.props.state) {
      setScrollPosition(component, component.props.state[scrollSymbol]);
    }
    if (params.beforeLeave && component.props.__beforeLeave__) {
      component.props.__beforeLeave__(params.beforeLeave);
    }
  });
  onWillUnmount(() => {
    if (component.props.__exportState__) {
      let state = {};
      state[scrollSymbol] = getScrollPosition(component);
      if (params.export) {
        Object.assign(state, params.export());
      }
      component.props.__exportState__(state);
    }
  });
  return {
    scrollTo(offset) {
      setScrollPosition(component, offset);
    },
  };
}
