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
    if (!component.__owl__.isDestroyed) {
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
