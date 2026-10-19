const _owl = window.owl;

/**
 * This function fills a missing 't.map()' in Owl exported type validators.
 *
 * @param {any} keyType
 * @param {any} valueType
 */
function t_map(keyType, valueType) {
    return t.customValidator(t.instanceOf(Map), function validateMap(mapValue) {
        const issues = [];
        for (const [key, value] of mapValue) {
            issues.push(..._owl.validateType(key, keyType), ..._owl.validateType(value, valueType));
        }
        return issues;
    });
}

/**
 * This function fills a missing 't.set()' in Owl exported type validators.
 *
 * @param {any} valueType
 */
function t_set(valueType) {
    return t.customValidator(t.instanceOf(Set), function validateSet(setValue) {
        const issues = [];
        for (const value of setValue) {
            issues.push(..._owl.validateType(value, valueType));
        }
        return issues;
    });
}

/**
 * When running its own tests, signals are modified to run in "strict" mode: this
 * effectively enforces that:
 * - all signals must have a type;
 * - the type of all signals must be validated; on initalization and on each mutation.
 *
 * This validation is only performed for Hoot's own tests as this is costly, and
 * as it only serves to validate the framework; not the tests themselves.
 *
 * @template {(...args: any[]) => any} T
 * @param {T} signalFn
 * @param {(...args: Parameters<T>) => boolean} [makeTypeValidator]
 * @param {boolean} [discardValue]
 * @returns {T}
 */
function makeStrictSignal(signalFn, makeTypeValidator, discardValue) {
    /** @type {T} */
    function strictSignal(value, options) {
        const typeValidator = makeTypeValidator?.(value, options) || options?.type;
        if (!typeValidator) {
            throw new Error(`In Hoot strict mode, all signals require a type.`);
        }

        if (discardValue) {
            // for 'signal.ref()', default value needs to be null
            value = null;
        }

        // Initial assertion
        _owl.assertType(value, typeValidator, `Invalid signal type:`);

        const actualSignal = signalFn(value, options);
        const typedSignal = computed(actualSignal, {
            set(value) {
                // Assertion on set
                _owl.assertType(value, typeValidator, `Invalid signal type:`);
                actualSignal.set(value);
            },
        });

        return typedSignal;
    }

    return strictSignal;
}

const strictSignal = makeStrictSignal(_owl.signal);
strictSignal.ref = makeStrictSignal(_owl.signal.ref, (value) => t.ref(value), true);
strictSignal.Array = makeStrictSignal(_owl.signal.Array, (_value, { type }) => t.array(type));
strictSignal.Map = makeStrictSignal(_owl.signal.Map, (_value, { keyType, valueType }) =>
    t_map(keyType, valueType)
);
strictSignal.Object = makeStrictSignal(_owl.signal.Object, (_value, { type }) => t.object(type));
strictSignal.Set = makeStrictSignal(_owl.signal.Set, (_value, { type }) => t_set(type));

export const __info__ = _owl.__info__;
export const App = _owl.App;
export const applyDefaults = _owl.applyDefaults;
export const assertType = _owl.assertType;
export const asyncComputed = _owl.asyncComputed;
export const batched = _owl.batched;
export const blockDom = _owl.blockDom;
export const Component = _owl.Component;
export const computed = _owl.computed;
export const effect = _owl.effect;
export const ErrorBoundary = _owl.ErrorBoundary;
export const EventBus = _owl.EventBus;
export const getDefault = _owl.getDefault;
export const getScope = _owl.getScope;
export const globalTemplates = _owl.globalTemplates;
export const htmlEscape = _owl.htmlEscape;
export const immediateEffect = _owl.immediateEffect;
export const markRaw = _owl.markRaw;
export const markup = _owl.markup;
export const mount = _owl.mount;
export const onError = _owl.onError;
export const onMounted = _owl.onMounted;
export const onPatched = _owl.onPatched;
export const onWillDestroy = _owl.onWillDestroy;
export const onWillPatch = _owl.onWillPatch;
export const onWillStart = _owl.onWillStart;
export const onWillUnmount = _owl.onWillUnmount;
export const onWillUpdateProps = _owl.onWillUpdateProps;
export const OwlError = _owl.OwlError;
export const Plugin = _owl.Plugin;
export const Portal = _owl.Portal;
export const providePlugins = _owl.providePlugins;
export const proxy = _owl.proxy;
export const Registry = _owl.Registry;
export const Resource = _owl.Resource;
export const Scope = _owl.Scope;
export const shallowEqual = _owl.shallowEqual;
export const signal = strictSignal;
export const status = _owl.status;
export const Suspense = _owl.Suspense;
export const t = _owl.t;
export const TemplateSet = _owl.TemplateSet;
export const toRaw = _owl.toRaw;
export const types = _owl.types;
export const untrack = _owl.untrack;
export const useApp = _owl.useApp;
export const useConfig = _owl.useConfig;
export const useEffect = _owl.useEffect;
export const useListener = _owl.useListener;
export const usePlugin = _owl.usePlugin;
export const useProps = _owl.useProps;
export const useScope = _owl.useScope;
export const validateType = _owl.validateType;
export const whenReady = _owl.whenReady;
export const xml = _owl.xml;
