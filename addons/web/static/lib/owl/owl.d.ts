declare class VToggler {
    key: string;
    child: VNode;
    parentEl?: HTMLElement | undefined;
    constructor(key: string, child: VNode);
    mount(parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement): void;
    moveBeforeVNode(other: VToggler | null, afterNode: Node | null): void;
    patch(other: VToggler, withBeforeRemove: boolean): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node | undefined;
    toString(): string;
}
declare function toggler(key: string, child: VNode): VNode<VToggler>;

type BlockType = (data?: any[], children?: VNode[]) => VNode;
/**
 * Compiling blocks is a multi-step process:
 *
 * 1. build an IntermediateTree from the HTML element. This intermediate tree
 *    is a binary tree structure that encode dynamic info sub nodes, and the
 *    path required to reach them
 * 2. process the tree to build a block context, which is an object that aggregate
 *    all dynamic info in a list, and also, all ref indexes.
 * 3. process the context to build appropriate builder/setter functions
 * 4. make a dynamic block class, which will efficiently collect references and
 *    create/update dynamic locations/children
 *
 * @param str
 * @returns a new block type, that can build concrete blocks
 */
declare function createBlock(str: string): BlockType;

declare class VList {
    children: VNode[];
    anchor: Node | undefined;
    parentEl?: HTMLElement | undefined;
    isOnlyChild?: boolean | undefined;
    constructor(children: VNode[]);
    mount(parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement | undefined): void;
    moveBeforeVNode(other: VList | null, afterNode: Node | null): void;
    patch(other: VList, withBeforeRemove: boolean): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node | undefined;
    toString(): string;
}
declare function list(children: VNode[]): VNode<VList>;

declare class VMulti {
    children: (VNode | undefined)[];
    anchors?: Node[] | undefined;
    parentEl?: HTMLElement | undefined;
    isOnlyChild?: boolean | undefined;
    constructor(children: (VNode | undefined)[]);
    mount(parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement | undefined): void;
    moveBeforeVNode(other: VMulti | null, afterNode: Node | null): void;
    patch(other: VMulti, withBeforeRemove: boolean): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node | undefined;
    toString(): string;
}
declare function multi(children: (VNode | undefined)[]): VNode<VMulti>;

declare abstract class VSimpleNode {
    text: string | String;
    parentEl?: HTMLElement | undefined;
    el?: any;
    constructor(text: string | String);
    mountNode(node: Node, parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement | undefined): void;
    moveBeforeVNode(other: VText | null, afterNode: Node | null): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node;
    toString(): string | String;
}
declare class VText extends VSimpleNode {
    mount(parent: HTMLElement, afterNode: Node | null): void;
    patch(other: VText): void;
}
declare class VComment extends VSimpleNode {
    mount(parent: HTMLElement, afterNode: Node | null): void;
    patch(): void;
}
declare function text(str: string | String): VNode<VText>;
declare function comment(str: string): VNode<VComment>;

declare class VHtml {
    html: string;
    parentEl?: HTMLElement | undefined;
    content: ChildNode[];
    constructor(html: string);
    mount(parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement | undefined): void;
    moveBeforeVNode(other: VHtml | null, afterNode: Node | null): void;
    patch(other: VHtml): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node;
    toString(): string;
}
declare function html(str: string): VNode<VHtml>;

interface VNode<T = any> {
    mount(parent: HTMLElement, afterNode: Node | null): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement): void;
    moveBeforeVNode(other: T | null, afterNode: Node | null): void;
    patch(other: T, withBeforeRemove: boolean): void;
    beforeRemove(): void;
    remove(): void;
    firstNode(): Node | undefined;
    el?: undefined | HTMLElement | Text;
    parentEl?: undefined | HTMLElement;
    isOnlyChild?: boolean | undefined;
    key?: any;
}
type BDom = VNode<any>;
declare function mount$1(vnode: VNode, fixture: HTMLElement, afterNode?: Node | null): void;
declare function patch(vnode1: VNode, vnode2: VNode, withBeforeRemove?: boolean): void;
declare function remove(vnode: VNode, withBeforeRemove?: boolean): void;

interface ResourceOptions<T> {
    name?: string;
    validation?: T;
}
declare class Resource<T> {
    private _items;
    private _name?;
    private _validation?;
    constructor(options?: ResourceOptions<T>);
    items: ReactiveValue<T[], T[]>;
    add(item: T, options?: {
        sequence?: number;
    }): Resource<T>;
    delete(item: T): Resource<T>;
    has(item: T): boolean;
}
declare function useResource<T>(r: Resource<T>, elements: T[]): void;

interface RegistryOptions<T> {
    name?: string;
    validation?: T;
}
declare class Registry<T> {
    private _map;
    private _name;
    private _validation?;
    constructor(options?: RegistryOptions<T>);
    entries: ReactiveValue<[string, T][], [string, T][]>;
    items: ReactiveValue<T[], T[]>;
    addById<U extends {
        id: string;
    } & T>(item: U, options?: {
        sequence?: number;
    }): Registry<T>;
    add(key: string, value: T, options?: {
        sequence?: number;
    }): Registry<T>;
    get(key: string, defaultValue?: T): T;
    delete(key: string): void;
    has(key: string): boolean;
}

interface ReactiveValue<TRead, TWrite = TRead> {
    (): TRead;
    /**
     * Update the value of the reactive with a new value. If the new value is different
     * from the previous values, all computations that depends on this reactive will
     * be invalidated, and effects will rerun.
     */
    set(nextValue: TWrite): void;
}
declare enum ComputationState {
    EXECUTED = 0,
    STALE = 1,
    PENDING = 2
}
interface Atom<T = any> {
    observers: Set<ComputationAtom>;
    value: T;
}
interface ComputationAtom<T = any> extends Atom<T> {
    compute: () => T;
    isDerived: boolean;
    sources: Set<Atom>;
    state: ComputationState;
}
declare function untrack<T>(fn: (...args: any[]) => T): T;

declare const enum STATUS {
    NEW = 0,
    MOUNTED = 1,// is ready, and in DOM. It has a valid el
    CANCELLED = 2,
    DESTROYED = 3
}
type STATUS_DESCR = "new" | "started" | "mounted" | "cancelled" | "destroyed";
declare function status(entity: Component | Plugin): STATUS_DESCR;

interface PluginConstructor {
    new (...args: any[]): Plugin;
    id: string;
}
declare class Plugin {
    private static _shadowId;
    static get id(): string;
    static set id(shadowId: string);
    __owl__: PluginManager;
    constructor(manager: PluginManager);
    setup(): void;
}
interface PluginManagerOptions {
    parent?: PluginManager | null;
    config?: Record<string, any>;
}
declare class PluginManager {
    app: App;
    config: Record<string, any>;
    onDestroyCb: Function[];
    computations: ComputationAtom[];
    plugins: Record<string, Plugin>;
    status: STATUS;
    constructor(app: App, options?: PluginManagerOptions);
    destroy(): void;
    getPluginById<T extends Plugin>(id: string): T | null;
    getPlugin<T extends PluginConstructor>(pluginConstructor: T): InstanceType<T> | null;
    startPlugin<T extends PluginConstructor>(pluginConstructor: T): InstanceType<T> | null;
    startPlugins(pluginConstructors: PluginConstructor[]): void;
}

declare class Fiber {
    node: ComponentNode;
    bdom: BDom | null;
    root: RootFiber | null;
    parent: Fiber | null;
    children: Fiber[];
    appliedToDom: boolean;
    deep: boolean;
    childrenMap: ComponentNode["children"];
    constructor(node: ComponentNode, parent: Fiber | null);
    render(): void;
    _render(): void;
}
declare class RootFiber extends Fiber {
    counter: number;
    willPatch: Fiber[];
    patched: Fiber[];
    mounted: Fiber[];
    locked: boolean;
    complete(): void;
    setCounter(newValue: number): void;
}
type Position = "first-child" | "last-child";
interface MountOptions {
    position?: Position;
}
declare class MountFiber extends RootFiber {
    target: HTMLElement;
    position: Position;
    constructor(node: ComponentNode, target: HTMLElement, options?: MountOptions);
    complete(): void;
}

type LifecycleHook = Function;
declare class ComponentNode implements VNode<ComponentNode> {
    el?: HTMLElement | Text | undefined;
    app: App;
    fiber: Fiber | null;
    component: Component;
    bdom: BDom | null;
    status: STATUS;
    forceNextRender: boolean;
    parentKey: string | null;
    props: Record<string, any>;
    renderFn: Function;
    parent: ComponentNode | null;
    children: {
        [key: string]: ComponentNode;
    };
    willStart: LifecycleHook[];
    willUpdateProps: LifecycleHook[];
    willUnmount: LifecycleHook[];
    mounted: LifecycleHook[];
    willPatch: LifecycleHook[];
    patched: LifecycleHook[];
    willDestroy: LifecycleHook[];
    signalComputation: ComputationAtom;
    computations: ComputationAtom[];
    pluginManager: PluginManager;
    constructor(C: ComponentConstructor, props: Record<string, any>, app: App, parent: ComponentNode | null, parentKey: string | null);
    mountComponent(target: any, options?: MountOptions): void;
    initiateRender(fiber: Fiber | MountFiber): Promise<void>;
    render(deep: boolean): Promise<void>;
    cancel(): void;
    _cancel(): void;
    destroy(): void;
    _destroy(): void;
    updateAndRender(props: Record<string, any>, parentFiber: Fiber): Promise<void>;
    /**
     * Finds a child that has dom that is not yet updated, and update it. This
     * method is meant to be used only in the context of repatching the dom after
     * a mounted hook failed and was handled.
     */
    updateDom(): void;
    firstNode(): Node | undefined;
    mount(parent: HTMLElement, anchor: ChildNode): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement): void;
    moveBeforeVNode(other: ComponentNode | null, afterNode: Node | null): void;
    patch(): void;
    _patch(): void;
    beforeRemove(): void;
    remove(): void;
}

interface StaticComponentProperties {
    template: string;
    components?: {
        [componentName: string]: ComponentConstructor;
    };
}
interface ComponentConstructor extends StaticComponentProperties {
    new (node: ComponentNode): Component;
}
declare class Component {
    static template: string;
    __owl__: ComponentNode;
    constructor(node: ComponentNode);
    setup(): void;
}

type Constructor<T = any> = {
    new (...args: any[]): T;
};
type GetOptionalEntries<T> = {
    [K in keyof T as K extends `${infer P}?` ? P : never]?: T[K];
};
type GetRequiredEntries<T> = {
    [K in keyof T as K extends `${string}?` ? never : K]: T[K];
};
type PrettifyShape<T> = T extends Function ? T : {
    [K in keyof T]: T[K];
};
type ResolveOptionalEntries<T> = PrettifyShape<GetRequiredEntries<T> & GetOptionalEntries<T>>;
type KeyedObject<K extends string[]> = {
    [P in K[number]]: any;
};
type ResolveShapedObject<T extends {}> = PrettifyShape<ResolveOptionalEntries<T>>;
type ResolveObjectType<T extends {}> = ResolveShapedObject<T extends string[] ? KeyedObject<T> : T>;
type UnionToIntersection<U> = (U extends any ? (_: U) => any : never) extends (_: infer I) => void ? I : never;
declare function arrayType(): any[];
declare function arrayType<T>(elementType: T): T[];
declare function constructorType<T extends Constructor>(constructor: T): T;
declare function customValidator<T>(type: T, validator: (value: T) => boolean, errorMessage?: string): T;
declare function functionType(): (...parameters: any[]) => any;
declare function functionType<const P extends any[]>(parameters: P): (...parameters: P) => void;
declare function functionType<const P extends any[], R>(parameters: P, result: R): (...parameters: P) => R;
declare function instanceType<T extends Constructor>(constructor: T): InstanceType<T>;
declare function intersection<T extends any[]>(types: T): UnionToIntersection<T[number]>;
type LiteralTypes = number | string | boolean | null | undefined;
declare function literalType<const T extends LiteralTypes>(literal: T): T;
declare function literalSelection<const T extends LiteralTypes>(literals: T[]): T;
declare function objectType(): Record<string, any>;
declare function objectType<const Keys extends string[]>(keys: Keys): ResolveOptionalEntries<KeyedObject<Keys>>;
declare function objectType<Shape extends {}>(shape: Shape): ResolveOptionalEntries<Shape>;
declare function promiseType(): Promise<void>;
declare function promiseType<T>(type: T): Promise<T>;
declare function recordType(): Record<PropertyKey, any>;
declare function recordType<V>(valueType: V): Record<PropertyKey, V>;
declare function tuple<const T extends any[]>(types: T): T;
declare function union<T extends any[]>(types: T): T[number];
declare function reactiveValueType(): ReactiveValue<any>;
declare function reactiveValueType<T>(type: T): ReactiveValue<T>;
declare function ref(): HTMLElement | null;
declare function ref<T extends Constructor<HTMLElement>>(type: T): InstanceType<T> | null;
declare const types: {
    and: typeof intersection;
    any: any;
    array: typeof arrayType;
    boolean: boolean;
    constructor: typeof constructorType;
    customValidator: typeof customValidator;
    function: typeof functionType;
    instanceOf: typeof instanceType;
    literal: typeof literalType;
    number: number;
    object: typeof objectType;
    or: typeof union;
    promise: typeof promiseType;
    record: typeof recordType;
    ref: typeof ref;
    selection: typeof literalSelection;
    signal: typeof reactiveValueType;
    string: string;
    tuple: typeof tuple;
};

declare const isProps: unique symbol;
type WithDefaults<T, D> = T & Required<D>;
type Props<T extends {}> = T & {
    [isProps]: true;
};
type GetPropsDefaults<T extends object> = PrettifyShape<GetOptionalEntries<T>>;
type GetPropsWithOptionals<T> = T extends Props<infer P> ? (P extends WithDefaults<infer R, any> ? R : P) : never;
type GetProps<T> = {
    [K in keyof T]: T[K] extends {
        [isProps]: true;
    } ? (x: GetPropsWithOptionals<T[K]>) => void : never;
}[keyof T] extends (x: infer I) => void ? {
    [K in keyof I]: I[K];
} : never;
declare function props(): Props<Record<string, any>>;
declare function props<const Keys extends string[]>(keys: Keys): Props<ResolveObjectType<Keys>>;
declare function props<const Keys extends string[], Defaults>(keys: Keys, defaults: Defaults & GetPropsDefaults<KeyedObject<Keys>>): Props<WithDefaults<ResolveObjectType<Keys>, Defaults>>;
declare function props<Shape extends {}>(shape: Shape): Props<ResolveObjectType<Shape>>;
declare function props<Shape extends {}, Defaults>(shape: Shape, defaults: Defaults & GetPropsDefaults<Shape>): Props<WithDefaults<ResolveObjectType<Shape>, Defaults>>;

type Target = object;
type Reactive<T extends Target> = T;
/**
 * Mark an object or array so that it is ignored by the reactivity system
 *
 * @param value the value to mark
 * @returns the object itself
 */
declare function markRaw<T extends Target>(value: T): T;
/**
 * Given a proxy objet, return the raw (non proxy) underlying object
 *
 * @param value a proxy value
 * @returns the underlying value
 */
declare function toRaw<T extends Target, U extends Reactive<T>>(value: U | T): T;
/**
 * Creates a reactive proxy for an object. Reading data on the proxy object
 * subscribes to changes to the data. Writing data on the object will cause the
 * notify callback to be called if there are suscriptions to that data. Nested
 * objects and arrays are automatically made reactive as well.
 *
 * Whenever you are notified of a change, all subscriptions are cleared, and if
 * you would like to be notified of any further changes, you should go read
 * the underlying data again. We assume that if you don't go read it again after
 * being notified, it means that you are no longer interested in that data.
 *
 * Subscriptions:
 * + Reading a property on an object will subscribe you to changes in the value
 *    of that property.
 * + Accessing an object's keys (eg with Object.keys or with `for..in`) will
 *    subscribe you to the creation/deletion of keys. Checking the presence of a
 *    key on the object with 'in' has the same effect.
 * - getOwnPropertyDescriptor does not currently subscribe you to the property.
 *    This is a choice that was made because changing a key's value will trigger
 *    this trap and we do not want to subscribe by writes. This also means that
 *    Object.hasOwnProperty doesn't subscribe as it goes through this trap.
 *
 * @param target the object for which to create a proxy proxy
 * @param callback the function to call when an observed property of the
 *  proxy has changed
 * @returns a proxy that tracks changes to it
 */
declare function proxy<T extends Target>(target: T): T;

type ErrorParams = {
    error: any;
} & ({
    node: ComponentNode;
} | {
    fiber: Fiber;
});
declare function handleError(params: ErrorParams): void;

declare class Scheduler {
    static requestAnimationFrame: ((callback: FrameRequestCallback) => number) & typeof requestAnimationFrame;
    tasks: Set<RootFiber>;
    requestAnimationFrame: Window["requestAnimationFrame"];
    frame: number;
    delayedRenders: Fiber[];
    cancelledNodes: Set<ComponentNode>;
    processing: boolean;
    constructor();
    addFiber(fiber: Fiber): void;
    scheduleDestroy(node: ComponentNode): void;
    /**
     * Process all current tasks. This only applies to the fibers that are ready.
     * Other tasks are left unchanged.
     */
    flush(): void;
    processTasks(): void;
    processFiber(fiber: RootFiber): void;
}

type CustomDirectives = Record<string, (node: Element, value: string, modifier: string[]) => void>;
type Template = (context: any, vnode: any, key?: string) => BDom;
type TemplateFunction = (app: TemplateSet, bdom: any, helpers: any) => Template;

interface TemplateSetConfig {
    dev?: boolean;
    translatableAttributes?: string[];
    translateFn?: (s: string, translationCtx: string) => string;
    templates?: string | Document | Record<string, string>;
    getTemplate?: (s: string) => Element | Function | string | void;
    customDirectives?: CustomDirectives;
    globalValues?: object;
}
declare class TemplateSet {
    static registerTemplate(name: string, fn: TemplateFunction): void;
    dev: boolean;
    rawTemplates: typeof globalTemplates;
    templates: {
        [name: string]: Template;
    };
    getRawTemplate?: (s: string) => Element | Function | string | void;
    translateFn?: (s: string, translationCtx: string) => string;
    translatableAttributes?: string[];
    customDirectives: CustomDirectives;
    runtimeUtils: object;
    hasGlobalValues: boolean;
    constructor(config?: TemplateSetConfig);
    addTemplate(name: string, template: string | Element): void;
    addTemplates(xml: string | Document): void;
    getTemplate(name: string): Template;
    private _compileTemplate;
}
declare const globalTemplates: {
    [key: string]: string | Element | TemplateFunction;
};
declare function xml(...args: Parameters<typeof String.raw>): string;
declare namespace xml {
    var nextId: number;
}

type Callback = (...args: any[]) => void;
/**
 * Creates a batched version of a callback so that all calls to it in the same
 * microtick will only call the original callback once.
 *
 * @param callback the callback to batch
 * @returns a batched version of the original callback
 */
declare function batched(callback: Callback): Callback;
declare function validateTarget(target: HTMLElement | ShadowRoot): void;
declare class EventBus extends EventTarget {
    trigger(name: string, payload?: any): void;
}
declare function whenReady(fn?: any): Promise<void>;
declare class Markup extends String {
}
declare function htmlEscape(str: any): Markup;
declare function markup(strings: TemplateStringsArray, ...placeholders: unknown[]): Markup;
declare function markup(value: string): Markup;

type ComponentInstance<C extends ComponentConstructor> = C extends new (...args: any) => infer T ? T : never;
interface RootConfig<P> {
    props?: P;
}
interface AppConfig extends TemplateSetConfig {
    name?: string;
    plugins?: PluginConstructor[] | Resource<PluginConstructor>;
    config?: Record<string, any>;
    test?: boolean;
}
declare global {
    interface Window {
        __OWL_DEVTOOLS__: {
            apps: Set<App>;
            Fiber: typeof Fiber;
            RootFiber: typeof RootFiber;
            toRaw: typeof toRaw;
            proxy: typeof proxy;
        };
    }
}
type MountTarget = HTMLElement | ShadowRoot;
interface Root<T extends ComponentConstructor> {
    node: ComponentNode;
    promise: Promise<ComponentInstance<T>>;
    mount(target: MountTarget, options?: MountOptions): Promise<ComponentInstance<T>>;
    destroy(): void;
}
declare class App extends TemplateSet {
    static validateTarget: typeof validateTarget;
    static apps: Set<App>;
    static version: string;
    name: string;
    scheduler: Scheduler;
    roots: Set<Root<any>>;
    pluginManager: PluginManager;
    constructor(config?: AppConfig);
    createRoot<T extends ComponentConstructor>(Root: T, config?: RootConfig<GetProps<ComponentInstance<T>>>): Root<T>;
    private mountNode;
    destroy(): void;
    handleError(...args: Parameters<typeof handleError>): void;
}
declare function mount<T extends ComponentConstructor>(C: T, target: MountTarget, config?: AppConfig & RootConfig<GetProps<ComponentInstance<T>>> & MountOptions): Promise<ComponentInstance<T>>;

interface Signal<T> extends ReactiveValue<T> {
    /**
     * Update the value of the signal with a new value. If the new value is different
     * from the previous values, all computations that depends on this signal will
     * be invalidated, and effects will rerun.
     */
    set(nextValue: T): void;
}
interface SignalOptions<T> {
    type?: T;
}
declare function invalidateSignal(signal: Signal<any>): void;
declare function signalArray<T>(initialValue: T[], options?: SignalOptions<T>): Signal<T[]>;
declare function signalObject<T extends Record<PropertyKey, any>>(initialValue: T, options?: SignalOptions<T>): Signal<T>;
interface MapSignalOptions<K, V> {
    name?: string;
    keyType?: K;
    valueType?: V;
}
declare function signalMap<K, V>(initialValue: Map<K, V>, options?: MapSignalOptions<K, V>): Signal<Map<K, V>>;
declare function signalSet<T>(initialValue: Set<T>, options?: SignalOptions<T>): Signal<Set<T>>;
declare function signal<T>(value: T, options?: SignalOptions<T>): Signal<T>;
declare namespace signal {
    var invalidate: typeof invalidateSignal;
    var Array: typeof signalArray;
    var Map: typeof signalMap;
    var Object: typeof signalObject;
    var Set: typeof signalSet;
}

interface ComputedOptions<TWrite> {
    set?(value: TWrite): void;
}
declare function computed<TRead, TWrite = TRead>(getter: () => TRead, options?: ComputedOptions<TWrite>): ReactiveValue<TRead, TWrite>;

declare function effect<T>(fn: () => T): () => void;

/**
 * This hook will run a callback when a component is mounted and patched, and
 * will run a cleanup function before patching and before unmounting the
 * the component.
 *
 * @template T
 * @param {Effect<T>} effect the effect to run on component mount and/or patch
 * @param {()=>[...T]} [computeDependencies=()=>[NaN]] a callback to compute
 *      dependencies that will decide if the effect needs to be cleaned up and
 *      run again. If the dependencies did not change, the effect will not run
 *      again. The default value returns an array containing only NaN because
 *      NaN !== NaN, which will cause the effect to rerun on every patch.
 */
declare function useEffect(fn: Parameters<typeof effect>[0]): void;
/**
 * When a component needs to listen to DOM Events on element(s) that are not
 * part of his hierarchy, we can use the `useListener` hook.
 * It will immediately add the listener, and remove it whenever the plugin or
 * component is destroyed.
 *
 * Example:
 *  a menu needs to listen to the click on window to be closed automatically
 *
 * Usage:
 *  in the constructor of the OWL component that needs to be notified,
 *  `useListener(window, 'click', () => this._doSomething());`
 * */
declare function useListener(target: EventTarget | Signal<EventTarget | null>, eventName: string, handler: EventListener, eventParams?: AddEventListenerOptions): void;
declare function useApp(): App;

declare function onWillStart(fn: () => Promise<void> | void | any): void;
declare function onWillUpdateProps(fn: (nextProps: any) => Promise<void> | void | any): void;
declare function onMounted(fn: () => void | any): void;
declare function onWillPatch(fn: () => any | void): void;
declare function onPatched(fn: () => void | any): void;
declare function onWillUnmount(fn: () => void | any): void;
declare function onWillDestroy(fn: () => void | any): void;
type OnErrorCallback = (error: any) => void | any;
declare function onError(callback: OnErrorCallback): void;

interface ValidationIssue {
    message: string;
    path?: PropertyKey[];
    received?: any;
    [K: string]: any;
}
declare function assertType(value: any, validation: any, errorMessage?: string): void;
declare function validateType(value: any, validation: any): ValidationIssue[];

declare class OwlError extends Error {
    cause?: any;
}

type PluginInstance<T extends PluginConstructor> = Omit<InstanceType<T>, "setup">;
declare function plugin<T extends PluginConstructor>(pluginType: T): PluginInstance<T>;
declare function config<T = any>(name: string, type?: T): T;
declare function providePlugins(pluginConstructors: PluginConstructor[] | Resource<PluginConstructor>, config?: Record<string, any>): void;

interface CapturedContext {
    run<T = void>(callback: () => T): T;
    protectAsync<P extends any[], R>(callback: (...args: P) => Promise<R>): (...args: P) => Promise<R>;
    runWithAsyncProtection<T>(callback: () => Promise<T>): Promise<T>;
}
/**
 * Captures the current context and gives methods to run
 * functions within the captured context.
 */
declare function useContext(): CapturedContext;

declare const blockDom: {
    config: {
        shouldNormalizeDom: boolean;
        mainEventHandler: (data: any, ev: Event, currentTarget?: EventTarget | null) => boolean;
    };
    mount: typeof mount$1;
    patch: typeof patch;
    remove: typeof remove;
    list: typeof list;
    multi: typeof multi;
    text: typeof text;
    toggler: typeof toggler;
    createBlock: typeof createBlock;
    html: typeof html;
    comment: typeof comment;
};

declare const __info__: {
    version: string;
};

export { App, Component, EventBus, OwlError, Plugin, Registry, Resource, __info__, assertType, batched, blockDom, computed, config, effect, htmlEscape, markRaw, markup, mount, onError, onMounted, onPatched, onWillDestroy, onWillPatch, onWillStart, onWillUnmount, onWillUpdateProps, plugin, props, providePlugins, proxy, signal, status, toRaw, types, untrack, useApp, useContext, useEffect, useListener, useResource, validateType, whenReady, xml };
export type { CapturedContext, ComponentConstructor, GetProps, PluginConstructor, PluginInstance, ReactiveValue, Signal };
