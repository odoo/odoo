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

export const onWillRender = owl.onWillRender;
export const onRendered = owl.onRendered;
export const useRef = owl.useRef;
export const useComponent = owl.useComponent;
export const useExternalListener = owl.useExternalListener;
export const useState = owl.useState;
export const reactive = owl.reactive;
export const useLayoutEffect = owl.useLayoutEffect;
export const useEnv = owl.useEnv;
export const useChildEnv = owl.useChildEnv;
delete owl.useChildEnv;
export const provideEnv = owl.provideEnv;
delete owl.provideEnv;
export const useSubEnv = owl.useSubEnv;
export const useChildSubEnv = owl.useChildSubEnv;
export const validate = owl.validate;
