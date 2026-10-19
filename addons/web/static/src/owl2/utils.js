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
 * @param {any} component
 * @returns {"new" | "mounted" | "destroyed"}
 * @deprecated read the status of the component scope instead: `useScope().status`
 *  (to compare with `STATUS` from "@odoo/owl")
 */
export function status(component) {
    switch (component.__owl__.status) {
        case owl.STATUS.NEW:
            return "new";
        case owl.STATUS.MOUNTED:
            return "mounted";
        case owl.STATUS.DESTROYED:
            return "destroyed";
    }
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
