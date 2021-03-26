/** @odoo-module **/
'use strict';

const { Component } = owl;

/**
 * Compares `a` and `b` up to the given `compareDepth`.
 *
 * @param {any} a
 * @param {any} b
 * @param {Object|integer} compareDepth
 * @returns {boolean}
 */
function isEqual(a, b, compareDepth) {
    const keys = Object.keys(a);
    if (Object.keys(b).length !== keys.length) {
        return false;
    }
    for (const key of keys) {
        // the depth can be given either as a number (for all keys) or as
        // an object (for each key)
        let depth;
        if (typeof compareDepth === 'number') {
            depth = compareDepth;
        } else {
            depth = compareDepth[key] || 0;
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
 * @param {Object} [param0.compareDepth={}] allows to specify the comparison
 *  depth to use for each prop. Default is shallow compare (depth = 0).
 */
function useShouldUpdateBasedOnProps({ compareDepth = {} } = {}) {
    const component = Component.current;
    component.shouldUpdate = nextProps => {
        const allNewProps = Object.assign({}, nextProps);
        const defaultProps = component.constructor.defaultProps;
        for (const key in defaultProps) {
            if (allNewProps[key] === undefined) {
                allNewProps[key] = defaultProps[key];
            }
        }
        return !isEqual(component.props, allNewProps, compareDepth);
    };
}

export default useShouldUpdateBasedOnProps;
