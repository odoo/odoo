// @ts-ignore
const owl = globalThis.owl;

/**
 * @template T
 * @param {T} target
 * @param {keyof T} name
 * @param {typeof owl.signal} [signalFn]
 * @deprecated use {@link owl.signal} instead
 */
export function makeReactive(target, name, signalFn = owl.signal) {
    const _signal = signalFn(target[name]);
    Object.defineProperty(target, name, {
        get: _signal,
        set: _signal.set,
    });
}

/**
 * @param {any} component
 * @param {boolean} [deep]
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
