/** @odoo-module native */
import {
    onMounted,
    onPatched,
    onRendered,
    onWillDestroy,
    reactive,
    toRaw,
    useEnv,
    useRef,
    useState,
} from "@odoo/owl";

/**
 * @typedef {HTMLElement} HostElement
 * @typedef {Object} State
 * @typedef {Record<string, HTMLElement>} EditableDescendants
 * @typedef {(state, previous, next) => void} PropertyUpdate
 * @typedef {Record<string, PropertyUpdate>} PropertyUpdater
 * @typedef {Object} StateChangeManagerConfig
 * @property {PropertyUpdater} [propertyUpdater]
 * @property {function(HostElement):State} [getEmbeddedState]
 * @property {function(HostElement, State):Object} [stateToEmbeddedProps]
 * @typedef {Object} Embedding
 * @property {String} name
 * @property {Component} Component
 * @property {function(HostElement):Object} getProps
 * @property {function(HostElement):EditableDescendants} [getEditableDescendants]
 * @property {function(StateChangeManagerConfig):StateChangeManager} [getStateChangeManager]
 */

/**
 * @param {HostElement} host
 * @returns {EditableDescendants}
 */
export function getEditableDescendants(host) {
    const editableDescendants = {};
    for (const candidate of host.querySelectorAll("[data-embedded-editable]")) {
        if (candidate.closest("[data-embedded]") === host) {
            editableDescendants[candidate.dataset.embeddedEditable] = candidate;
        }
    }
    return editableDescendants;
}

/**
 * @param {HostElement} host
 * @returns {EditableDescendants}
 */
export function useEditableDescendants(host) {
    const env = useEnv();
    if (!env.getEditableDescendants) {
        throw new Error(
            "Missing `getEditableDescendants` function in the `embedding` provided to the `EmbeddedComponentPlugin`.",
        );
    }
    const editableDescendants = Object.freeze(env.getEditableDescendants(host));
    const refs = {};
    const renders = {};
    for (const name of Object.keys(editableDescendants)) {
        refs[name] = useRef(name);
        renders[name] = () => refs[name].el.replaceChildren(editableDescendants[name]);
    }
    let _restoreSelection;
    const restoreSelection = () => {
        if (_restoreSelection) {
            _restoreSelection();
            _restoreSelection = undefined;
        }
    };
    if (env.editorShared?.selection) {
        onRendered(() => {
            _restoreSelection = env.editorShared.selection.preserveSelection().restore;
        });
    }
    onMounted(() => {
        for (const render of Object.values(renders)) {
            render();
        }
        restoreSelection();
    });
    onPatched(() => {
        for (const [name, render] of Object.entries(renders)) {
            if (!host.contains(editableDescendants[name])) {
                render();
            }
        }
        restoreSelection();
    });
    return editableDescendants;
}

/**
 * @param {Object} state
 * @param {Object} stateChangeManager
 * @param {Object} stateChangeManager.previousEmbeddedState
 * @returns {ProxyHandler}
 */
function embeddedStateProxyHandler(state, stateChangeManager) {
    return {
        set(target, key, value, receiver) {
            if (
                value !== Reflect.get(target, key, receiver) &&
                !stateChangeManager.previousEmbeddedState
            ) {
                stateChangeManager.previousEmbeddedState = JSON.parse(
                    JSON.stringify(stateChangeManager.embeddedState),
                );
            }
            return Reflect.set(target, key, value, receiver);
        },
        deleteProperty(target, key) {
            if (Reflect.has(target, key) && !stateChangeManager.previousEmbeddedState) {
                stateChangeManager.previousEmbeddedState = JSON.parse(
                    JSON.stringify(stateChangeManager.embeddedState),
                );
            }
            return Reflect.deleteProperty(target, key);
        },
        get(target, key, receiver) {
            Reflect.get(state, key, state);
            return Reflect.get(target, key, receiver);
        },
        ownKeys(target) {
            Reflect.ownKeys(state);
            return Reflect.ownKeys(target);
        },
        has(target, key) {
            Reflect.has(state, key);
            return Reflect.has(target, key);
        },
    };
}

function observeAllKeys(reactive) {
    for (const key in reactive) {
        const prop = reactive[key];
        if (prop instanceof Object) {
            observeAllKeys(prop);
        }
    }
}

/**
 * @param {HostElement} host
 * @returns {Object}
 */
export function getEmbeddedProps(host) {
    return host.dataset.embeddedProps ? JSON.parse(host.dataset.embeddedProps) : {};
}

function sortedCopy(obj) {
    const result = {};
    const propNames = Object.keys(obj).sort();
    for (const propName of propNames) {
        result[propName] = obj[propName];
    }
    return result;
}

/**
 * @param {Object} container
 * @param {string} key
 * @param {Object} previous
 * @param {Object} next
 */
export function applyObjectPropertyDifference(container, key, previous, next) {
    if (!container[key]) {
        container[key] = {};
    }
    const obj1 = { ...(previous || {}) };
    const obj2 = { ...(next || {}) };
    const dest = container[key];
    for (const key in obj2) {
        if (JSON.stringify(obj1[key]) !== JSON.stringify(obj2[key])) {
            dest[key] = obj2[key];
        }
        delete obj1[key];
    }
    for (const key in obj1) {
        delete dest[key];
    }
    if (!Object.keys(dest).length && !next) {
        delete container[key];
    }
}

/**
 * @param {Object} container
 * @param {string} key
 * @param {Object} value
 */
export function replaceProperty(container, key, value) {
    if (value === undefined) {
        delete container[key];
    } else {
        container[key] = value;
    }
}

export class StateChangeManager {
    /**
     * @param {StateChangeManagerConfig} config
     * @param {HostElement} config.host
     * @param {Function} config.commitStateChanges
     */
    constructor(config) {
        this.config = config;
    }
    setup() {
        const defaultState = sortedCopy(this.getEmbeddedState());
        const defaultStateChange = {
            stateChangeId: null,
            previous: defaultState,
            next: defaultState,
        };
        this.defaultStateChange = defaultStateChange;
        this.previousStateChange = defaultStateChange;
        this.batchId = 0;
        this.setupUnmounted();
    }

    setupUnmounted() {
        this.previousEmbeddedState = null;
        this.state = null;
        this.embeddedState = null;
        this.embeddedStateProxy = null;
        this.isLiveComponent = false;
        this.batchId += 1;
    }

    /**
     * @param {Object} state
     * @returns {Proxy}
     */
    constructEmbeddedState(state) {
        this.state = state;
        this.embeddedState = reactive(
            this.assignDeepProxyCopy({}, state),
            this.batchedChangeState(),
        );
        this.embeddedStateProxy = new Proxy(
            this.embeddedState,
            embeddedStateProxyHandler(state, this),
        );
        observeAllKeys(this.embeddedStateProxy);
        this.isLiveComponent = true;
        return this.embeddedStateProxy;
    }

    /**
     * @returns {Object}
     */
    getState() {
        let state = this.state;
        if (!this.isLiveComponent) {
            state = this.getEmbeddedState();
        }
        return state;
    }

    /**
     * @param {string} attrState
     * @param { Object } options
     * @param {boolean} options.reverse
     * @param {boolean} options.forNewStep
     * @returns {string}
     */
    onStateChanged(attrState, { reverse = false, forNewStep = false } = {}) {
        const stateChange = attrState ? JSON.parse(attrState) : this.defaultStateChange;
        const state = this.getState();
        if (reverse) {
            this.reverseStateChange(stateChange);
        }
        if (!this.areStateChangesEqual(this.previousStateChange, stateChange)) {
            const previous = JSON.stringify(sortedCopy(state));
            this.commitStateChange(state, stateChange.previous, stateChange.next);
            const sortedState = sortedCopy(state);
            this.config.host.dataset.embeddedProps = JSON.stringify(
                this.stateToEmbeddedProps(this.config.host, sortedState),
            );
            if (this.isLiveComponent && !this.previousEmbeddedState) {
                this.assignDeepProxyCopy(toRaw(this.embeddedState), sortedState);
            }
            if (!forNewStep) {
                this.previousStateChange = stateChange;
            } else {
                const next = JSON.stringify(sortedState);
                if (previous !== next) {
                    this.previousStateChange = {
                        stateChangeId: this.generateId(),
                        previous: JSON.parse(previous),
                        next: JSON.parse(next),
                    };
                    return JSON.stringify(this.previousStateChange);
                }
            }
        }
    }

    /**
     * @returns {Function}
     */
    batchedChangeState() {
        let scheduled = false;
        const batchId = this.batchId;
        return async () => {
            if (this.isLiveComponent && !scheduled) {
                scheduled = true;
                await Promise.resolve();
                scheduled = false;
                if (batchId === this.batchId) {
                    this.changeState();
                }
            }
        };
    }

    changeState() {
        if (!this.previousEmbeddedState) {
            return;
        }
        const previousEmbeddedState = this.previousEmbeddedState;
        this.previousEmbeddedState = null;
        const previous = JSON.stringify(sortedCopy(this.state));
        this.commitStateChange(
            this.state,
            previousEmbeddedState,
            JSON.parse(JSON.stringify(this.embeddedState)),
        );
        const sortedState = sortedCopy(this.state);
        const next = JSON.stringify(sortedState);
        this.assignDeepProxyCopy(toRaw(this.embeddedState), sortedState);
        if (previous !== next) {
            this.previousStateChange = {
                stateChangeId: this.generateId(),
                previous: JSON.parse(previous),
                next: JSON.parse(next),
            };
            this.config.host.dataset.embeddedState = JSON.stringify(
                this.previousStateChange,
            );
            this.config.host.dataset.embeddedProps = JSON.stringify(
                this.stateToEmbeddedProps(this.config.host, sortedState),
            );
            this.config.commitStateChanges();
        }
        observeAllKeys(this.embeddedStateProxy);
    }

    areStateChangesEqual(sc1, sc2) {
        return (
            sc1.stateChangeId === sc2.stateChangeId &&
            JSON.stringify(sc1.previous) === JSON.stringify(sc2.previous) &&
            JSON.stringify(sc1.next) === JSON.stringify(sc2.next)
        );
    }

    reverseStateChange(stateChange) {
        const previous = stateChange.previous;
        stateChange.previous = stateChange.next;
        stateChange.next = previous;
    }

    /**
     * @param {Object} target
     * @param {Object} source
     * @returns {Object}
     */
    assignDeepProxyCopy(target, source) {
        for (const key of Object.keys(target)) {
            delete target[key];
        }
        for (const key of Object.keys(source)) {
            target[key] = this.deepProxyCopy(source[key]);
        }
        return target;
    }

    /**
     * @param {Object} value
     * @returns {Proxy}
     */
    deepProxyCopy(value) {
        if (value instanceof Object) {
            const copy = value instanceof Array ? [] : {};
            for (const prop in value) {
                copy[prop] = this.deepProxyCopy(value[prop]);
            }
            return new Proxy(copy, embeddedStateProxyHandler(value, this));
        }
        return value;
    }

    generateId() {
        return Math.floor(Math.random() * Math.pow(2, 52));
    }

    /**
     * @param {Object} state
     * @param {Object} previous
     * @param {Object} next
     */
    commitStateChange(state, previous, next) {
        const currentKeys = new Set([
            ...Object.keys(state),
            ...Object.keys(previous),
            ...Object.keys(next),
        ]);
        for (const key of currentKeys) {
            if (key in (this.config.propertyUpdater || {})) {
                this.config.propertyUpdater[key](state, previous, next);
            } else if (JSON.stringify(previous[key]) !== JSON.stringify(next[key])) {
                replaceProperty(state, key, next[key]);
            }
        }
    }

    /**
     * @returns {Object}
     */
    getEmbeddedState() {
        const host = this.config.host;
        return this.config.getEmbeddedState?.(host) || getEmbeddedProps(host);
    }

    /**
     * @param {HostElement} host
     * @param {Object} state
     * @returns {Object}
     */
    stateToEmbeddedProps(host, state) {
        const props = this.config.stateToEmbeddedProps?.(host, state) || state;
        for (const key of Object.keys(props)) {
            if (props[key] === undefined) {
                delete props[key];
            }
        }
        return props;
    }
}

/**
 * @param {HostElement} host
 * @returns {Proxy}
 */
export function useEmbeddedState(host) {
    const env = useEnv();
    if (!env.getStateChangeManager) {
        throw new Error(
            "Missing `getStateChangeManager` function in the `embedding` provided to the `EmbeddedComponentPlugin`.",
        );
    }
    const stateChangeManager = env.getStateChangeManager(host);
    onWillDestroy(() => stateChangeManager.setupUnmounted());
    const state = useState(stateChangeManager.getEmbeddedState());
    return stateChangeManager.constructEmbeddedState(state);
}
