odoo.define('web.custom_hooks', function (require) {
    "use strict";

    const { Component, hooks } = owl;
    const { onMounted, onWillUnmount } = hooks;


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
     * */
    function useExternalListener(target, eventName, handler) {
        const boundHandler = handler.bind(Component.current);

        onMounted(() => target.addEventListener(eventName, boundHandler));
        onWillUnmount(() => target.removeEventListener(eventName, boundHandler));
    }

    return {
        useExternalListener,
    };
});
