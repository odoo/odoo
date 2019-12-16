odoo.define('mail.hooks.useRefs', function (require) {
'use strict';

const { Component } = owl;

/**
 * This hook provides support for dynamic-refs.
 *
 * @return {function} returns object whose keys are t-ref values of active refs.
 *   and values are refs.
 */
function useRefs() {
    const component = Component.current;
    return function () {
        return component.__owl__.refs;
    };
}

return useRefs;

});
