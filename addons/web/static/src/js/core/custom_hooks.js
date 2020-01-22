odoo.define('web.custom_hooks', function () {
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

    return {
        useFocusOnUpdate,
    };
});
