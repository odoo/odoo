import { onMounted, onWillUnmount, untrack, useListener, useProps, useScope } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "../owl2/utils";

export const scrollSymbol = Symbol("scroll");

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
    const scope = useScope();
    onMounted(() => callbackRecorder.add(scope, callback));
    onWillUnmount(() => callbackRecorder.remove(scope));
}

/**
 */
export function useSetupAction(params = {}) {
    const env = useEnv();
    const props = useProps();
    const ui = useService("ui");
    const {
        __beforeLeave__,
        __getGlobalState__,
        __getUrlState__,
        __getLocalState__,
        __getContext__,
        __getOrderBy__,
    } = env;

    const {
        beforeVisibilityChange,
        beforeUnload,
        beforeLeave,
        getGlobalState,
        getUrlState,
        getLocalState,
        rootRef,
    } = params;

    if (beforeVisibilityChange) {
        useListener(document, "visibilitychange", beforeVisibilityChange);
    }

    if (beforeUnload) {
        useListener(window, "beforeunload", beforeUnload);
    }
    if (__beforeLeave__ && beforeLeave) {
        useCallbackRecorder(__beforeLeave__, beforeLeave);
    }
    if (__getGlobalState__ && getGlobalState) {
        useCallbackRecorder(__getGlobalState__, () => Object.assign({}, getGlobalState()));
    }
    if (__getUrlState__ && getUrlState) {
        useCallbackRecorder(__getUrlState__, () => Object.assign({}, getUrlState()));
    }

    const getRootEl = () => untrack(rootRef);

    function setScrollFromState() {
        const { state } = props;
        const scrolling = state && state[scrollSymbol];
        if (scrolling) {
            const rootEl = getRootEl();
            if (!rootEl) {
                return;
            }
            if (ui.isSmall) {
                rootEl.scrollTop = (scrolling.root && scrolling.root.top) || 0;
                rootEl.scrollLeft = (scrolling.root && scrolling.root.left) || 0;
            } else if (scrolling.content) {
                const contentEl =
                    rootEl.querySelector(".o_component_with_search_panel > .o_renderer") ||
                    rootEl.querySelector(".o_content");
                if (contentEl) {
                    contentEl.scrollTop = scrolling.content.top || 0;
                    contentEl.scrollLeft = scrolling.content.left || 0;
                }
            }
        }
    }
    if (__getLocalState__ && (getLocalState || rootRef)) {
        useCallbackRecorder(__getLocalState__, () => {
            const state = {};
            if (getLocalState) {
                Object.assign(state, getLocalState());
            }
            if (rootRef) {
                const rootEl = getRootEl();
                if (!rootEl) {
                    return state;
                }
                if (ui.isSmall) {
                    state[scrollSymbol] = {
                        root: { left: rootEl.scrollLeft, top: rootEl.scrollTop },
                    };
                } else {
                    const contentEl =
                        rootEl.querySelector(".o_component_with_search_panel > .o_renderer") ||
                        rootEl.querySelector(".o_content");
                    if (contentEl) {
                        state[scrollSymbol] = {
                            content: { left: contentEl.scrollLeft, top: contentEl.scrollTop },
                        };
                    }
                }
            }
            return state;
        });

        if (rootRef) {
            onMounted(() => setScrollFromState());
        }
    }
    if (__getContext__ && params.getContext) {
        useCallbackRecorder(__getContext__, params.getContext);
    }
    if (__getOrderBy__ && params.getOrderBy) {
        useCallbackRecorder(__getOrderBy__, params.getOrderBy);
    }

    return {
        setScrollFromState,
    };
}
