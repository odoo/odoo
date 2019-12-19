odoo.define('web.custom_hooks', function (require) {
    "use strict";

    const { Component, hooks } = owl;
    const { onMounted, onPatched, onWillUnmount } = hooks;

    /**
     * Returns a function which purpose is to focus the given selector on the next
     * repaint (mount or patch). Its default selector is the first element having
     * an `autofocus' attribute. Text selection will be set at the end of the value
     * if the target is a text element. The action is lost if no element was found.
     *
     * @returns {Function}
     */
    function useFocusOnUpdate() {
        const component = Component.current;
        component.__willFocus = null;

        function _focusSelector() {
            if (component.__willFocus) {
                const target = component.el.querySelector(component.__willFocus);
                if (target) {
                    target.focus();
                    if (['INPUT', 'TEXTAREA'].includes(target.tagName)) {
                        target.selectionStart = target.selectionEnd = target.value.length;
                    }
                }
                component.__willFocus = null;
            }
        }

        onMounted(_focusSelector);
        onPatched(_focusSelector);

        return function focusOnUpdate(selector = '[autofocus]') {
            component.__willFocus = selector;
        };
    }

    /**
     * When component needs to listen to DOM Events on element(s) that is not part of his hierarchy, we can use
     * `useExternalListener` hook.
     * It will correctly add and remove the event listener.
     *
     * Example:
     *  a menu needs to listen to the click on window to be closed automatically
     *
     * Usage:
     *  in the constructor of the OWL component that needs to be notified,
     *  `useExternalListener(window, 'click', this._doSomething);` listen to the click event on window and call
     *  `this._doSomething` function of the component when the click happened
     *
     * @param {EventTarget} target
     * @param {string} eventName
     * @param {Function} handler
     * @param {(Object|boolean)} [eventParams]
     */
    function useExternalListener(target, eventName, handler, eventParams) {
        const boundHandler = handler.bind(Component.current);

        onMounted(() => target.addEventListener(eventName, boundHandler, eventParams));
        onWillUnmount(() => target.removeEventListener(eventName, boundHandler, eventParams));
    }

    return {
        useFocusOnUpdate,
        useExternalListener,
    };
});
