/** @odoo-module **/

import { getScrollPosition, setScrollPosition } from "../../core/utils/scrolling";
import { useEffect } from "../../core/effect_hook";

const { useComponent } = owl.hooks;

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
        __exportSearchState__,
        __exportState__,
        __saveParams__,
    } = component.env;

    if (__beforeLeave__ && params.beforeLeave) {
        useCallbackRecorder(__beforeLeave__, params.beforeLeave);
    }
    if (__exportSearchState__ && params.exportSearchState) {
        useCallbackRecorder(__exportSearchState__, params.exportSearchState);
    }
    if (__exportState__) {
        useCallbackRecorder(__exportState__, () => {
            const state = {};
            state[scrollSymbol] = getScrollPosition(component);
            if (params.exportState) {
                Object.assign(state, params.exportState());
            }
            return state;
        });
    }
    if (__saveParams__ && params.saveParams) {
        useCallbackRecorder(__saveParams__, params.saveParams);
    }

    useEffect(
        () => {
            if (component.props.state && component.props.state[scrollSymbol]) {
                setScrollPosition(component, component.props.state[scrollSymbol]);
            }
        },
        () => []
    );
}
