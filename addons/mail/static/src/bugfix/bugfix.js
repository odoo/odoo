/**
 * This file allows introducing new JS modules without contaminating other files.
 * This is useful when bug fixing requires adding such JS modules in stable
 * versions of Odoo. Any module that is defined in this file should be isolated
 * in its own file in master.
 */
odoo.define('mail/static/src/bugfix/bugfix.js', function (require) {
'use strict';

});

// Should be moved to its own file in master.
odoo.define('mail/static/src/component_hooks/use_rendered_values/use_rendered_values.js', function (require) {
'use strict';

const { Component } = owl;
const { onMounted, onPatched } = owl.hooks;

/**
 * This hooks provides support for accessing the values returned by the given
 * selector at the time of the last render. The values will be updated after
 * every mount/patch.
 *
 * @param {function} selector function that will be executed at the time of the
 *  render and of which the result will be stored for future reference.
 * @returns {function} function to call to retrieve the last rendered values.
 */
function useRenderedValues(selector) {
    const component = Component.current;
    let renderedValues;
    let patchedValues;

    const __render = component.__render.bind(component);
    component.__render = function () {
        renderedValues = selector();
        return __render(...arguments);
    };
    onMounted(onUpdate);
    onPatched(onUpdate);
    function onUpdate() {
        patchedValues = renderedValues;
    }
    return () => patchedValues;
}

return useRenderedValues;

});

// Should be moved to its own file in master.
odoo.define('mail/static/src/component_hooks/use_update/use_update.js', function (require) {
'use strict';

const { Component } = owl;
const { onMounted, onPatched } = owl.hooks;

const executionQueue = [];

function executeNextInQueue() {
    if (executionQueue.length === 0) {
        return;
    }
    const { component, func } = executionQueue.shift();
    if (component.__owl__.status !== 5 /* DESTROYED */) {
        func();
    }
    executeNextInQueue();
}

/**
 * @param {Object} param0
 * @param {Component} param0.component
 * @param {function} param0.func
 * @param {integer} param0.priority
 */
async function addFunctionToQueue({ component, func, priority }) {
    const index = executionQueue.findIndex(item => item.priority > priority);
    const item = { component, func, priority };
    if (index === -1) {
        executionQueue.push(item);
    } else {
        executionQueue.splice(index, 0, item);
    }
    // Timeout to allow all components to register their function before
    // executing any of them, to respect all priorities.
    await new Promise(resolve => setTimeout(resolve));
    executeNextInQueue();
}

/**
 * This hook provides support for executing code after update (render or patch).
 *
 * @param {Object} param0
 * @param {function} param0.func the function to execute after the update.
 * @param {integer} [param0.priority] determines the execution order of the function
 *  among the update function of other components. Lower priority is executed
 *  first. If no priority is given, the function is executed immediately.
 *  This param is deprecated because desynchronized update is causing issue if
 *  there is a new render planned in the meantime (models data become obsolete
 *  in the update method).
 */
function useUpdate({ func, priority }) {
    const component = Component.current;
    onMounted(onUpdate);
    onPatched(onUpdate);
    function onUpdate() {
        if (priority === undefined) {
            func();
            return;
        }
        addFunctionToQueue({ component, func, priority });
    }
}

return useUpdate;

});

// Should be moved to its own file in master.
odoo.define('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js', function (require) {
'use strict';

const { Component } = owl;
const { onPatched } = owl.hooks;

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
        forceRender = !isEqual(component.props, allNewProps, compareDepth);
        return forceRender;
    };
    onPatched(() => forceRender = false);
}

return useShouldUpdateBasedOnProps;

});
