/** @odoo-module **/
const { Component, hooks } = owl;

// -----------------------------------------------------------------------------
// Hook function
// -----------------------------------------------------------------------------

/**
 * Import a service into a component
 *
 * @param {string} serviceName
 * @returns {any}
 */
export function useService(serviceName) {
  const component = Component.current;
  const env = component.env;
  const service = env.services[serviceName];
  if (!service) {
    throw new Error(`Service ${serviceName} is not available`);
  }
  return typeof service === "function" ? service.bind(component) : service;
}

/**
 * Ensures a bus event listener is attached and cleared the proper way.
 *
 * @param {EventBus} bus
 * @param {string} eventName
 * @param {Callback} callback
 */
export function useBus(bus, eventName, callback) {
  const component = Component.current;
  hooks.onMounted(() => bus.on(eventName, component, callback));
  hooks.onWillUnmount(() => bus.off(eventName, component));
}

/**
 * Focus a given selector as soon as it appears in the DOM and if it was not
 * displayed before. If the selected target is an input|textarea, set the selection
 * at the end.
 *
 * @param {Object} [params]
 * @param {string} [params.selector='autofocus'] default: select the first element
 *                 with an `autofocus` attribute.
 * @returns {Function} function that forces the focus on the next update if visible.
 */
export function useAutofocus(params = {}) {
  const comp = Component.current;
  // Prevent autofocus in mobile
  // FIXME: device not yet available in the env
  // if (comp.env.device.isMobile) {
  //     return () => {};
  // }
  const selector = params.selector || "[autofocus]";
  let target = null;
  function autofocus() {
    const prevTarget = target;
    target = comp.el.querySelector(selector);
    if (target && target !== prevTarget) {
      target.focus();
      if (["INPUT", "TEXTAREA"].includes(target.tagName)) {
        const inputEl = target;
        inputEl.selectionStart = inputEl.selectionEnd = inputEl.value.length;
      }
    }
  }
  hooks.onMounted(autofocus);
  hooks.onPatched(autofocus);
  return function focusOnUpdate() {
    target = null;
  };
}
