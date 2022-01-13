/** @odoo-module **/
'use strict';

const { Component, onPatched } = owl;

/**
 * Shallow compares props `a` and `b`.
 *
 * @param {Object} a
 * @param {Object} b
 * @returns {boolean}
 */
function isEqual(a, b) {
    const keys = Object.keys(a);
    if (Object.keys(b).length !== keys.length) {
        return false;
    }
    for (const key of keys) {
        if (a[key] !== b[key]) {
            return false;
        }
    }
    return true;
}

/**
 * This hook overrides the `shouldUpdate` method to ensure the component is only
 * updated if its props actually changed. This is especially useful to use on
 * components for which an extra render costs proportionally a lot more than
 * comparing props.
 */
export function useShouldUpdateBasedOnProps() {
    const component = Component.current;
    let forceRender = false;
    component.shouldUpdate = nextProps => {
        if (forceRender) {
            return true;
        }
        const allNewProps = Object.assign({}, nextProps);
        const defaultProps = component.constructor.defaultProps;
        for (const key in defaultProps) {
            if (allNewProps[key] === undefined) {
                allNewProps[key] = defaultProps[key];
            }
        }
        forceRender = !isEqual(component.props, allNewProps);
        return forceRender;
    };
    onPatched(() => forceRender = false);
}
