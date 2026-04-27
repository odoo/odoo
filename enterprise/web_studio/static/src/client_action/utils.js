/** @odoo-module */
import { reactive, useComponent, useEnv, useSubEnv } from "@odoo/owl";

export function getFieldsInArch(xmlDoc) {
    const res = [];
    const isInvisible = ["True", "1", "true"];
    xmlDoc.querySelectorAll("field").forEach((el) => {
        if (!el.parentElement.closest("field,groupby")) {
            const invisible = el.getAttribute("invisible") || el.getAttribute("column_invisible");
            const dataUsedBy = el.getAttribute("data-used-by");
            if (dataUsedBy) {
                return;
            }
            if (!invisible || !isInvisible.includes(invisible)) {
                res.push(el.getAttribute("name"));
            }
        }
    });
    return res;
}

export function useDialogConfirmation({ confirm, cancel, before, close }) {
    before = before || (() => {});
    confirm = confirm || (() => {});
    cancel = cancel || (() => {});
    if (!close) {
        const component = useComponent();
        close = () => component.props.close();
    }

    let isProtected = false;
    async function canExecute() {
        if (isProtected) {
            return false;
        }
        isProtected = true;
        await before();
        return true;
    }

    async function execute(cb, ...args) {
        let succeeded = false;
        try {
            succeeded = await cb(...args);
        } catch (e) {
            close();
            throw e;
        }
        if (succeeded === undefined || succeeded) {
            return close();
        }
        isProtected = false;
    }

    async function _confirm(...args) {
        if (!(await canExecute())) {
            return;
        }
        return execute(confirm, ...args);
    }

    async function _cancel(...args) {
        if (!(await canExecute())) {
            return;
        }
        return execute(cancel, ...args);
    }

    const env = useEnv();
    env.dialogData.dismiss = () => _cancel();

    return { confirm: _confirm, cancel: _cancel };
}

export class Reactive {
    constructor() {
        const raw = this;
        // A function not bound to this returning the original not reactive object
        // This is usefull to be able to read stuff without subscribing the caller
        // eg: when reading internals just for checking
        this.raw = () => {
            return raw;
        };
        return reactive(this);
    }
}

// A custom memoize function that doesn't store all results
// First the core/function/memoize tool may yield incorrect result in our case.
// Second, the keys we use usually involve archs themselves that could be heavy in the long run.
export function memoizeOnce(callback) {
    let key, value;
    return function (...args) {
        if (key === args[0]) {
            return value;
        }
        key = args[0];
        value = callback.call(this, ...args);
        return value;
    };
}

export function useSubEnvAndServices(env) {
    const services = env.services;
    const bus = env.bus;
    useSubEnv(env);
    useSubEnv({ services, bus });
}

/**
 * Sorts a list topologically, each element's dependencies should be defined
 * with the getDependencies callback.
 * This is a copy of what is done in python: odoo.tools.misc.py:def topological_sort
 * @params [Array] elems
 * @params [Function] getDependencies
 */
function topologicalSort(elems, getDependencies) {
    const result = [];
    const visited = new Set();
    function visit(n) {
        if (visited.has(n)) {
            return;
        }
        visited.add(n);
        if (!elems.includes(n)) {
            return;
        }
        // first visit all dependencies of n, then append n to result
        for (const dep of getDependencies(n)) {
            visit(dep);
        }
        result.push(n);
    }

    for (const el of elems) {
        visit(el);
    }

    return result;
}

/**
 * Allows to override the services defined in the env with a new instance
 * of each one defined in "overrides".
 * This function assumes all services in overrides start synchronously
 * @params [Object] overrides: new instances of services to create
 *     the key is the service's name, the value is the service definition
 */
export function useServicesOverrides(overrides) {
    let env = useEnv();
    const services = Object.create(env.services);

    useSubEnv({ services });
    env = useEnv();
    const getDependencies = (name) => overrides[name]?.dependencies || [];
    const topoSorted = topologicalSort(Object.keys(overrides), getDependencies);

    for (const servName of topoSorted) {
        services[servName] = overrides[servName].start(env, services);
    }
}
