import {
    onMounted,
    onRendered,
    onPatched,
    onWillDestroy,
    reactive,
    toRaw,
    useComponent,
    useRef,
    useState,
} from "@odoo/owl";

/**
 * @typedef {HTMLElement} HostElement host element for an embedded component
 * @typedef {Object} State state obtained from `useState` usage
 * @typedef {Record<string, HTMLElement>} EditableDescendants
 * @typedef {(state, previous, next) => void} PropertyUpdate function applying
 *          a state change which can be computed from `previous` and `next`
 *          to `state`.
 * @typedef {Record<string, PropertyUpdate>} PropertyUpdater
 *
 * @typedef {Object} StateChangeManagerConfig
 * @property {PropertyUpdater} [propertyUpdater] object mapping a key of the
 *        state to a function which will compute how values from a stateChange
 *        are applied to the current state. Defined in the embedding definition
 *        of a component.
 * @property {function(HostElement):State} [getEmbeddedState]
 *        custom function to get the first embedded state (the one used during
 *        setup), in case not all embedded props should be part of the state, or
 *        if more properties should be added to it.
 * @property {function(HostElement, State):Object} [stateToEmbeddedProps]
 *        custom function to compute the props, i.e. in case the entire state
 *        should not be converted to props.
 *
 * @typedef {Object} Embedding object provided to the instance which mounts
 *          Embedded components (EmbeddedComponentPlugin, HtmlViewer, ...)
 * @property {String} name
 * @property {Component} Component
 * @property {function(HostElement):Object} getProps props for the given
 *           Component class instance.
 * @property {function(HostElement):EditableDescendants} [getEditableDescendants]
 *           @see useEditableDescendants
 * @property {function(StateChangeManagerConfig):StateChangeManager} [getStateChangeManager]
 *           @see useEmbeddedState
 */

/**
 * Get all element children with `data-embedded-editable` attribute which are
 * descendants of the host's own embedded component and not part of another
 * embedded component descendant (an embedded component can contain others).
 * If multiple elements have the same `data-embedded-editable`, only the last
 * one is considered.
 * @param {HostElement} host
 * @returns {EditableDescendants} editableDescendants
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
 * Handle the rendering of editableDescendants:
 * It is a node owned by the editor, which will be inserted under a ref of
 * the same name as the attribute `data-embedded-editable` of that node, in the
 * component's template. This allows to use editor features inside an embedded
 * component. EditableDescendants are shared in collaboration and are saved
 * between edition sessions.
 *
 * Warning: there must be a ref in the template for every editableDescendants,
 * available at all times no matter the component state to guarantee that the
 * editor can save their values at any given time, synchronously.
 *
 * @param {HostElement} host
 * @returns {EditableDescendants} (HTMLElement) by the value of their
 *          `data-embedded-editable` attribute.
 */
export function useEditableDescendants(host) {
    const component = useComponent();
    if (!component.env.getEditableDescendants) {
        throw new Error(
            "Missing `getEditableDescendants` function in the `embedding` provided to the `EmbeddedComponentPlugin`."
        );
    }
    const editableDescendants = Object.freeze(component.env.getEditableDescendants(host));
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
    if (component.env.editorShared?.preserveSelection) {
        onRendered(() => {
            _restoreSelection = component.env.editorShared.preserveSelection().restore;
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
            // Handle partial patch
            if (!host.contains(editableDescendants[name])) {
                render();
            }
        }
        restoreSelection();
    });
    return editableDescendants;
}

/**
 * Create a ProxyHandler to manage a serializable "buffer" (Proxy target) for
 * changes. The buffer must be a @see reactive which should update state
 * with its callback (commit).
 * @see useEmbeddedState
 * The Proxy target and state must be serializable through JSON.stringify.
 *
 * @param {Object} state
 * @param {Object} stateChangeManager
 * @param {Object} stateChangeManager.previousEmbeddedState null, or a deep copy
 *        of the target used as a reference point for comparison
 *        (before <-> after) so that multiple synchronous changes can be handled
 *        at once.
 * @returns {ProxyHandler}
 */
function embeddedStateProxyHandler(state, stateChangeManager) {
    return {
        // Write operations are always done on the target ("buffer").
        // During the first write operation before a commit, keep a deep copy of
        // the target through serialization, which will be used as a reference
        // point for a comparison (before <-> after).
        set(target, key, value, receiver) {
            if (
                value !== Reflect.get(target, key, receiver) &&
                !stateChangeManager.previousEmbeddedState
            ) {
                stateChangeManager.previousEmbeddedState = JSON.parse(
                    JSON.stringify(stateChangeManager.embeddedState)
                );
            }
            return Reflect.set(target, key, value, receiver);
        },
        deleteProperty(target, key) {
            if (Reflect.has(target, key) && !stateChangeManager.previousEmbeddedState) {
                stateChangeManager.previousEmbeddedState = JSON.parse(
                    JSON.stringify(stateChangeManager.embeddedState)
                );
            }
            return Reflect.deleteProperty(target, key);
        },
        // Read operations should also be done on state to register the
        // rendering callback.
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
 * Extract props serialized in `data-embedded-props` attribute.
 *
 * @param {HostElement} host
 * @returns {Object} props
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
 * Compute the difference between next and previous, and apply that difference
 * to container[key]. Comparison is done through JSON.stringify, so all values
 * must be serializable.
 *
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
 * Overwrite container[key] with value.
 *
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
     * @param {Function} config.dispatch plugin dispatch to send editor commands
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
        // Used in case `data-embedded-state` is removed (i.e. when reverting
        // the first mutation setting that attribute)
        this.defaultStateChange = defaultStateChange;
        // Used to keep track of the last applied stateChange, to avoid
        // applying it multiple times (i.e. revertMutations + stageRecords
        // during undo)
        this.previousStateChange = defaultStateChange;
        // Used to discard batch changes when a component is destroyed,
        // pending state changes should not be applied
        this.batchId = 0;
        this.setupUnmounted();
    }

    /**
     * Called at setup and when an embedded component is destroyed. This resets
     * state values related to the mounted component. State changes will be
     * handled differently when unmounted.
     */
    setupUnmounted() {
        this.previousEmbeddedState = null;
        this.state = null;
        this.embeddedState = null;
        this.embeddedStateProxy = null;
        this.isLiveComponent = false;
        this.batchId += 1;
    }

    /**
     * Construct the proxy object to use inside an embedded component. It can
     * be read on to register for rendering updates in the component template,
     * and written on to trigger a re-rendering, sharing changes in
     * collaboration and registering them for the history.
     * @param {Object} state
     * @returns {Proxy} embeddedStateProxy
     */
    constructEmbeddedState(state) {
        this.state = state;
        this.embeddedState = reactive(
            this.assignDeepProxyCopy({}, state),
            this.batchedChangeState()
        );
        this.embeddedStateProxy = new Proxy(
            this.embeddedState,
            embeddedStateProxyHandler(state, this)
        );
        // First subscription to changes.
        observeAllKeys(this.embeddedStateProxy);
        this.isLiveComponent = true;
        return this.embeddedStateProxy;
    }

    /**
     * Depending on whether the component is destroyed or started mounting,
     * return its effective state.
     * @returns {Object} state
     */
    getState() {
        let state = this.state;
        if (!this.isLiveComponent) {
            state = this.getEmbeddedState();
        }
        return state;
    }

    /**
     * Called when `data-embedded-state` attribute is being changed. This
     * will update the state, the embedded state, the embedded props and
     * recompute a new expression when necessary.
     * @param {string} attrState JSON representation of a stateChange
     * @param { Object } options
     * @param {boolean} options.reverse whether to read the stateChange from
     *        next to previous
     * @param {boolean} options.forNewStep whether the attribute change is being
     *        used to create a new step.
     * @returns {string} new JSON representation of a stateChange, in case
     *          it needs to be represented under another form to be shared
     *          in collaboration (a local peer doing revertMutations implies
     *          that collaborators will do applyMutations, so the stateChange
     *          must be expressed with another form for them).
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
                this.stateToEmbeddedProps(this.config.host, sortedState)
            );
            if (this.isLiveComponent && !this.previousEmbeddedState) {
                // Update the embeddedState only if there is no pending change.
                // If there is a pending change, it will be updated when the
                // pending change is applied in `changeState`.
                this.assignDeepProxyCopy(toRaw(this.embeddedState), sortedState);
            }
            if (!forNewStep) {
                this.previousStateChange = stateChange;
            } else {
                // If mutations are being applied to create a new step, the
                // state change must be expressed under another form for
                // collaborators, since the collaborator will always
                // "applyMutations" and never "revertMutations" when receiving
                // external steps.
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
     * Allow to write on the embeddedState multiple times synchronously
     * and batch all changes at once afterwards. A batch is discarded as soon
     * as the component is destroyed.
     * @returns {Function} batched changeState
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

    /**
     * Apply a stateChange that was done on the embeddedState to the state,
     * to trigger a re-rendering, and write the stateChange in
     * `data-embedded-state` for the history and collaboration. Also
     * recompute `data-embedded-props` for the next mounting operation.
     */
    changeState() {
        const previousEmbeddedState = this.previousEmbeddedState;
        this.previousEmbeddedState = null;
        const previous = JSON.stringify(sortedCopy(this.state));
        this.commitStateChange(
            this.state,
            previousEmbeddedState,
            JSON.parse(JSON.stringify(this.embeddedState))
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
            this.config.host.dataset.embeddedState = JSON.stringify(this.previousStateChange);
            this.config.host.dataset.embeddedProps = JSON.stringify(
                this.stateToEmbeddedProps(this.config.host, sortedState)
            );
            this.config.dispatch("ADD_STEP");
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
     * Replace every key of target with deep proxy copies of source.
     * This will make it so that any change at any level will pass by the
     * embeddedStateProxyHandler traps.
     * @param {Object} target
     * @param {Object} source
     * @returns {Object} copy with proxies as keys
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
     * Create a deep proxy copy of value ensuring that any change at any level
     * will pass by the embeddedStateProxyHandler traps.
     * @param {Object} value
     * @returns {Proxy} deep proxy copy of value
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
     * Apply a transaction to the active state. `previous` is the state
     * before the transaction, and `next` is the state after the
     * transaction was done. Keep in mind that the current state may have
     * been changed after the transaction was done, but before it was
     * applied. By default, will always accept nextState as
     * the final state. `propertyUpdater` should be provided in the config
     * to handle some keys differently, i.e. object composition.
     * @see applyObjectPropertyDifference
     * @param {Object} state current state
     * @param {Object} previous state before the transaction
     * @param {Object} next state after the transaction
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
     * Extract values to be used as the first embedded state (used for setup)
     * from the host.
     * Extract all values from `data-embedded-props` by default.
     * @returns {Object} state
     */
    getEmbeddedState() {
        const host = this.config.host;
        return this.config.getEmbeddedState?.(host) || getEmbeddedProps(host);
    }

    /**
     * Convert a state to an object containing the props to be
     * saved in `data-embedded-props`, which will be used for the next mount
     * operation, and saved in the database. The returned object should be
     * serializable using JSON.
     * Return the entire state by default.
     * @param {HostElement} host
     * @param {Object} state
     * @returns {Object} props
     */
    stateToEmbeddedProps(host, state) {
        const props = this.config.stateToEmbeddedProps?.(host, state) || state;
        // Clean undefined values to save space
        for (const key of Object.keys(props)) {
            if (props[key] === undefined) {
                delete props[key];
            }
        }
        return props;
    }
}

/**
 * Manage updates to `data-embedded-props` (To change props given to an
 * embedded component when it will be mounted in the future), through history
 * and collaborative operations.
 * This is done through a special `embeddedState` which can be used externally
 * as a normal state.
 * That state can be modified through 2 channels:
 * - By the component itself, as with any normal state.
 * - By the embedded_component_plugin, during history or collaborative
 *   operations (undo/redo/resetStepsUntil/addExternalStep). The attribute
 *   `data-embedded-state` will be used to contain a serialized representation
 *   of a state change.
 *
 * While the embedded state evolves, the `data-embedded-props` attribute is
 * always maintained to its relative value.
 *
 * `data-embedded-state` and `data-embedded-props` attributes are maintained
 * even if the related component is in a destroyed state, in order to prepare
 * the next mount operation if the host is re-inserted in the DOM through an
 * history operation.
 * If the component is currently mounted/being mounted, state changes are
 * applied to the attribute and the embeddedState object.
 *
 * By default, a property change in the state is handled by replacing the
 * previous value with the new one (overwrite). To change this behavior,
 * provide a config extension in `getStateChangeManager` in the embedding
 * definition, with a @see propertyUpdater mapping each state key to a change
 * handler function.
 *
 * @param {HostElement} host
 * @returns {Proxy} embeddedState state which can be used for rendering, and
 *                  which is tied to the saved embedded props. Can only contain
 *                  JSON serializable values.
 */
export function useEmbeddedState(host) {
    const component = useComponent();
    if (!component.env.getStateChangeManager) {
        throw new Error(
            "Missing `getStateChangeManager` function in the `embedding` provided to the `EmbeddedComponentPlugin`."
        );
    }
    const stateChangeManager = component.env.getStateChangeManager(host);
    onWillDestroy(() => stateChangeManager.setupUnmounted());
    const state = useState(stateChangeManager.getEmbeddedState());
    return stateChangeManager.constructEmbeddedState(state);
}
