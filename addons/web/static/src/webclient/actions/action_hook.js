/** @odoo-module **/

import { getScrollPosition, setScrollPosition } from "./scrolling";

const { useComponent, useEffect, useExternalListener } = owl;

// -----------------------------------------------------------------------------
// Action hook
// -----------------------------------------------------------------------------
const scrollSymbol = Symbol("scroll");

export class CallbackRecorder {
    constructor() {
        this.setup();
    }
    setup() {
        this._callbacks = [];
    }
    /**
     * @returns {Function[]}
     */
    get callbacks() {
        return this._callbacks.map(({ callback }) => callback);
    }
    /**
     * @param {any} owner
     * @param {Function} callback
     */
    add(owner, callback) {
        if (!callback) {
            throw new Error("Missing callback");
        }
        this._callbacks.push({ owner, callback });
    }
    /**
     * @param {any} owner
     */
    remove(owner) {
        this._callbacks = this._callbacks.filter((s) => s.owner !== owner);
    }
}

/**
 * @param {CallbackRecorder} callbackRecorder
 * @param {Function} callback
 */
export function useCallbackRecorder(callbackRecorder, callback) {
    const component = useComponent();
    useEffect(
        () => {
            callbackRecorder.add(component, callback);
            return () => callbackRecorder.remove(component);
        },
        () => []
    );
}

/**
 */
export function useSetupAction(params = {}) {
    const component = useComponent();
    const {
        __beforeLeave__,
        __getGlobalState__,
        __getLocalState__,
        __getContext__,
    } = component.env;

    if (params.beforeUnload) {
        useExternalListener(window, "beforeunload", params.beforeUnload);
    }
    if (__beforeLeave__ && params.beforeLeave) {
        useCallbackRecorder(__beforeLeave__, params.beforeLeave);
    }
    if (__getGlobalState__ && params.getGlobalState) {
        useCallbackRecorder(__getGlobalState__, params.getGlobalState);
    }
    if (__getLocalState__) {
        useCallbackRecorder(__getLocalState__, () => {
            const state = {};
            state[scrollSymbol] = getScrollPosition(component.env);
            if (params.getLocalState) {
                Object.assign(state, params.getLocalState());
            }
            return state;
        });
    }
    if (__getContext__ && params.getContext) {
        useCallbackRecorder(__getContext__, params.getContext);
    }

    useEffect(
        () => {
            if (component.props.state && component.props.state[scrollSymbol]) {
                setScrollPosition(component.env, component.props.state[scrollSymbol]);
            }
        },
        () => []
    );
}
