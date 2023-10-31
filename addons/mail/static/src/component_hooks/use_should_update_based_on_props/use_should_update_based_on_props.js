/** @odoo-module **/
'use strict';

const { Component } = owl;
const { onPatched } = owl.hooks;

/**
 * Compares `a` and `b` up to the given `propsCompareDepth`.
 *
 * @param {any} a
 * @param {any} b
 * @param {Object|integer} propsCompareDepth
 * @returns {boolean}
 */
function isEqual(a, b, propsCompareDepth) {
    const keys = Object.keys(a);
    if (Object.keys(b).length !== keys.length) {
        return false;
    }
    for (const key of keys) {
        // the depth can be given either as a number (for all keys) or as
        // an object (for each key)
        let depth;
        if (typeof propsCompareDepth === 'number') {
            depth = propsCompareDepth;
        } else {
            depth = propsCompareDepth[key] || 0;
        }
        if (depth === 0 && a[key] !== b[key]) {
            return false;
        }
        if (depth !== 0) {
            let nextDepth;
            if (typeof depth === 'number') {
                nextDepth = depth - 1;
            } else {
                nextDepth = depth;
            }
            if (!isEqual(a[key], b[key], nextDepth)) {
                return false;
            }
        }
    }
    return true;
}

/**
 * This hook overrides the `shouldUpdate` method to ensure the component is only
 * updated if its props actually changed. This is especially useful to use on
 * components for which an extra render costs proportionally a lot more than
 * comparing props.
 *
 * @param {Object} [param0={}]
 * @param {Object} [param0.propsCompareDepth={}] allows to specify the comparison
 *  depth to use for each prop. Default is shallow compare (depth = 0).
 */
export function useShouldUpdateBasedOnProps({ propsCompareDepth = {} } = {}) {
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
        forceRender = !isEqual(component.props, allNewProps, propsCompareDepth);
        return forceRender;
    };
    onPatched(() => forceRender = false);
}
