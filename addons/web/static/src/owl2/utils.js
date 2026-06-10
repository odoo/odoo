// @ts-ignore
const owl = globalThis.owl;

/**
 * Normalise any ref to the `{ el }` form expected by OWL 2 APIs.
 *
 * - OWL 3 signal ref (callable, no `.el`): wrapped so reading `.el` calls the
 *   signal via `untrack`, preventing the component from subscribing to the
 *   signal and receiving spurious re-renders on initial mount.
 * - Legacy ref (object with `.el`) or ref-like callable with `.el` (e.g.
 *   `useChildRef`): returned as-is — calling a ref-like callable would corrupt
 *   its internal state.
 */
export function normalizeRef(ref) {
    if (typeof ref === "function" && !("el" in ref)) {
        return { get el() { return owl.untrack(ref); } };
    }
    return ref;
}

/**
 * @param {any} component
 * @param {boolean} [deep]
 * @deprecated use Owl reactivity {@link https://github.com/odoo/owl/blob/master/doc/v3/owl/reference/reactivity.md}
 */
export function render(component, deep = false) {
    component.__owl__.render(deep);
}

export const onWillRender = owl.onWillRender;
export const onRendered = owl.onRendered;
export const useRef = owl.useRef;
export const useComponent = owl.useComponent;
export const useExternalListener = owl.useExternalListener;
export const useLayoutEffect = owl.useLayoutEffect;
export const useEnv = owl.useEnv;
export const useChildEnv = owl.useChildEnv;
delete owl.useChildEnv;
export const provideEnv = owl.provideEnv;
delete owl.provideEnv;
export const useSubEnv = owl.useSubEnv;
export const useChildSubEnv = owl.useChildSubEnv;
