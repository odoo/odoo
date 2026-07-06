// @ts-ignore
const owl = globalThis.owl;

/**
 * @param {any} component
 * @param {boolean} [deep]
 * @deprecated use Owl reactivity {@link https://github.com/odoo/owl/blob/master/doc/v3/owl/reference/reactivity.md}
 */
export function render(component, deep = false) {
    component.__owl__.render(deep);
}

/**
 * Read the element out of a ref, accepting both a legacy `.el` ref (Owl 2 refs,
 * `useRef`, `useChildRef`) and an Owl 3 native signal ref (called to read). The
 * `el` check comes first so ref-like callables (e.g. `useChildRef`) go through
 * the `.el` path and are never called (which would reset their value).
 *
 * @param {{ el: HTMLElement | null } | import("@odoo/owl").Signal<HTMLElement>} [ref]
 * @returns {HTMLElement | null | undefined}
 */
export function getRefEl(ref) {
    return ref && ("el" in ref ? ref.el : ref());
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
