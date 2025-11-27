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

declare type BlockType = (data?: any[], children?: VNode[]) => VNode;
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
declare type BDom = VNode<any>;
declare function mount$1(vnode: VNode, fixture: HTMLElement, afterNode?: Node | null): void;
declare function patch(vnode1: VNode, vnode2: VNode, withBeforeRemove?: boolean): void;
declare function remove(vnode: VNode, withBeforeRemove?: boolean): void;

declare type BaseType = {
    new (...args: any[]): any;
} | true | "*";
interface TypeInfo {
    type?: TypeDescription;
    optional?: boolean;
    validate?: Function;
    shape?: Schema;
    element?: TypeDescription;
    values?: TypeDescription;
}
declare type ValueType = {
    value: any;
};
declare type TypeDescription = BaseType | TypeInfo | ValueType | TypeDescription[];
declare type SimplifiedSchema = string[];
declare type NormalizedSchema = {
    [key: string]: TypeDescription;
};
declare type Schema = SimplifiedSchema | NormalizedSchema;
/**
 * Main validate function
 */
declare function validate(obj: {
    [key: string]: any;
}, spec: Schema): void;
declare function validateType(key: string, value: any, descr: TypeDescription): string | null;

declare type Fn<T> = () => T;
declare class Registry<T> {
    _map: {
        [key: string]: [number, T];
    };
    _name: string;
    _type?: TypeDescription;
    items: Fn<T[]>;
    entries: Fn<[string, T][]>;
    constructor(name?: string, type?: TypeDescription);
    set(key: string, value: T, sequence?: number): void;
    get(key: string, defaultValue?: T): T;
}

declare type customDirectives = Record<string, (node: Element, value: string, modifier: string[]) => void>;
declare enum ComputationState {
    EXECUTED = 0,
    STALE = 1,
    PENDING = 2
}
declare type Computation<T = any> = {
    compute?: () => T;
    state: ComputationState;
    sources: Set<Atom | Derived<any, any>>;
    isEager?: boolean;
    isDerived?: boolean;
    value: T;
    childrenEffect?: Computation[];
} & Opts;
declare type Opts = {
    name?: string;
};
declare type Atom<T = any> = {
    value: T;
    observers: Set<Computation>;
} & Opts;
interface Derived<Prev, Next = Prev> extends Atom<Next>, Computation<Next> {
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
declare type Position = "first-child" | "last-child";
interface MountOptions {
    position?: Position;
}
declare class MountFiber extends RootFiber {
    target: HTMLElement;
    position: Position;
    constructor(node: ComponentNode, target: HTMLElement, options?: MountOptions);
    complete(): void;
}

interface PluginCtor {
    new (deps: any): Plugin<any>;
    id: string;
    dependencies: string[];
}
interface PluginMetaData {
    isDestroyed: boolean;
}
declare class Plugin<Deps = {
    [name: string]: Plugin;
}> {
    static id: string;
    static dependencies: string[];
    readonly plugins: Deps;
    static resources: {};
    resources: {
        [name: string]: any;
    };
    __meta__: PluginMetaData;
    setup(): void;
    destroy(): void;
    get isDestroyed(): boolean;
}
declare class PluginManager {
    _parent: PluginManager | null;
    _children: PluginManager[];
    plugins: {
        [id: string]: Plugin;
    };
    resources: {
        [id: string]: any;
    };
    constructor(parent: PluginManager | null, Plugins: PluginCtor[] | (() => PluginCtor[]));
    destroy(): void;
    getPlugin(name: string): Plugin | null;
    getResource(name: string): any[];
}
declare function usePlugins(Plugins: PluginCtor[]): void;

declare const enum STATUS {
    NEW = 0,
    MOUNTED = 1,
    CANCELLED = 2,
    DESTROYED = 3
}
declare type STATUS_DESCR = "new" | "mounted" | "cancelled" | "destroyed";
declare function status(component: Component): STATUS_DESCR;

declare function useComponent(): Component;
/**
 * Creates a reactive object that will be observed by the current component.
 * Reading data from the returned object (eg during rendering) will cause the
 * component to subscribe to that data and be rerendered when it changes.
 *
 * @param state the state to observe
 * @returns a reactive object that will cause the component to re-render on
 *  relevant changes
 * @see reactive
 */
declare function useState<T extends object>(state: T): T;
declare type LifecycleHook = Function;
declare class ComponentNode<P extends Props = any, Plugins = any, E = any> implements VNode<ComponentNode<P, E>> {
    el?: HTMLElement | Text | undefined;
    app: App;
    fiber: Fiber | null;
    component: Component<P, Plugins, E>;
    bdom: BDom | null;
    status: STATUS;
    forceNextRender: boolean;
    parentKey: string | null;
    props: P;
    nextProps: P | null;
    renderFn: Function;
    parent: ComponentNode | null;
    childEnv: Env;
    children: {
        [key: string]: ComponentNode;
    };
    refs: any;
    willStart: LifecycleHook[];
    willUpdateProps: LifecycleHook[];
    willUnmount: LifecycleHook[];
    mounted: LifecycleHook[];
    willPatch: LifecycleHook[];
    patched: LifecycleHook[];
    willDestroy: LifecycleHook[];
    signalComputation: Computation;
    pluginManager: PluginManager;
    constructor(C: ComponentConstructor<P, Plugins, E>, props: P, app: App, parent: ComponentNode | null, parentKey: string | null);
    mountComponent(target: any, options?: MountOptions): void;
    initiateRender(fiber: Fiber | MountFiber): Promise<void>;
    render(deep: boolean): Promise<void>;
    cancel(): void;
    _cancel(): void;
    destroy(): void;
    _destroy(): void;
    updateAndRender(props: P, parentFiber: Fiber): Promise<void>;
    /**
     * Finds a child that has dom that is not yet updated, and update it. This
     * method is meant to be used only in the context of repatching the dom after
     * a mounted hook failed and was handled.
     */
    updateDom(): void;
    /**
     * Sets a ref to a given HTMLElement.
     *
     * @param name the name of the ref to set
     * @param el the HTMLElement to set the ref to. The ref is not set if the el
     *  is null, but useRef will not return elements that are not in the DOM
     */
    setRef(name: string, el: HTMLElement | null): void;
    firstNode(): Node | undefined;
    mount(parent: HTMLElement, anchor: ChildNode): void;
    moveBeforeDOMNode(node: Node | null, parent?: HTMLElement): void;
    moveBeforeVNode(other: ComponentNode<P, E> | null, afterNode: Node | null): void;
    patch(): void;
    _patch(): void;
    beforeRemove(): void;
    remove(): void;
    get name(): string;
}

declare type Props = {
    [key: string]: any;
};
interface StaticComponentProperties {
    template: string;
    defaultProps?: any;
    props?: Schema;
    components?: {
        [componentName: string]: ComponentConstructor;
    };
}
declare type ComponentConstructor<P extends Props = any, Plugins = any, E = any> = (new (props: P, env: E, plugins: Plugins, node: ComponentNode) => Component<P, Plugins, E>) & StaticComponentProperties;
declare class Component<Props = any, Plugins = PluginManager["plugins"], Env = any> {
    static template: string;
    static props?: Schema;
    static defaultProps?: any;
    props: Props;
    env: Env;
    plugins: Plugins;
    __owl__: ComponentNode;
    constructor(props: Props, env: Env, plugins: Plugins, node: ComponentNode);
    setup(): void;
    render(deep?: boolean): void;
}

declare type ErrorParams = {
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

interface Config {
    translateFn?: (s: string, translationCtx: string) => string;
    translatableAttributes?: string[];
    dev?: boolean;
}

declare type Template = (context: any, vnode: any, key?: string) => BDom;
declare type TemplateFunction = (app: TemplateSet, bdom: any, helpers: any) => Template;
interface CompileOptions extends Config {
    name?: string;
    customDirectives?: customDirectives;
    hasGlobalValues: boolean;
}
declare function compile(template: string | Element, options?: CompileOptions): TemplateFunction;

declare class Portal extends Component {
    static template: string;
    static props: {
        readonly target: {
            readonly type: StringConstructor;
        };
        readonly slots: true;
    };
    setup(): void;
}

interface TemplateSetConfig {
    dev?: boolean;
    translatableAttributes?: string[];
    translateFn?: (s: string, translationCtx: string) => string;
    templates?: string | Document | Record<string, string>;
    getTemplate?: (s: string) => Element | Function | string | void;
    customDirectives?: customDirectives;
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
    Portal: typeof Portal;
    customDirectives: customDirectives;
    runtimeUtils: object;
    hasGlobalValues: boolean;
    constructor(config?: TemplateSetConfig);
    addTemplate(name: string, template: string | Element): void;
    addTemplates(xml: string | Document): void;
    getTemplate(name: string): Template;
    _compileTemplate(name: string, template: string | Element): ReturnType<typeof compile>;
    callTemplate(owner: any, subTemplate: string, ctx: any, parent: any, key: any): any;
}
declare const globalTemplates: {
    [key: string]: string | Element | TemplateFunction;
};
declare function xml(...args: Parameters<typeof String.raw>): string;
declare namespace xml {
    var nextId: number;
}

declare type Callback = () => void;
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
declare function loadFile(url: string): Promise<string>;
declare class Markup extends String {
}
declare function htmlEscape(str: any): Markup;
declare function markup(strings: TemplateStringsArray, ...placeholders: unknown[]): Markup;
declare function markup(value: string): Markup;

declare type Target = object;
declare type Reactive<T extends Target> = T;
/**
 * Mark an object or array so that it is ignored by the reactivity system
 *
 * @param value the value to mark
 * @returns the object itself
 */
declare function markRaw<T extends Target>(value: T): T;
/**
 * Given a reactive objet, return the raw (non reactive) underlying object
 *
 * @param value a reactive value
 * @returns the underlying value
 */
declare function toRaw<T extends Target, U extends Reactive<T>>(value: U | T): T;
/**
 * Creates a reactive proxy for an object. Reading data on the reactive object
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
 * @param target the object for which to create a reactive proxy
 * @param callback the function to call when an observed property of the
 *  reactive has changed
 * @returns a proxy that tracks changes to it
 */
declare function reactive<T extends Target>(target: T): T;

interface Env {
    [key: string]: any;
}
interface RootConfig<P, E> {
    props?: P;
    env?: E;
    Plugins?: PluginCtor[];
}
interface AppConfig<P, E> extends TemplateSetConfig, RootConfig<P, E> {
    name?: string;
    test?: boolean;
    warnIfNoStaticProps?: boolean;
}
declare global {
    interface Window {
        __OWL_DEVTOOLS__: {
            apps: Set<App>;
            Fiber: typeof Fiber;
            RootFiber: typeof RootFiber;
            toRaw: typeof toRaw;
            reactive: typeof reactive;
        };
    }
}
interface Root<P extends Props, E> {
    node: ComponentNode<P, E>;
    mount(target: HTMLElement | ShadowRoot, options?: MountOptions): Promise<Component<P, E>>;
    destroy(): void;
}
declare class App<T extends abstract new (...args: any) => any = any, Plugins = any, P extends object = any, E = any> extends TemplateSet {
    static validateTarget: typeof validateTarget;
    static apps: Set<App<any, any, any, any>>;
    static version: string;
    name: string;
    Root: ComponentConstructor<P, Plugins, E>;
    props: P;
    env: E;
    scheduler: Scheduler;
    subRoots: Set<ComponentNode>;
    root: ComponentNode<P, E> | null;
    warnIfNoStaticProps: boolean;
    pluginManager: PluginManager;
    constructor(Root: ComponentConstructor<P, Plugins, E>, config?: AppConfig<P, E>);
    mount(target: HTMLElement | ShadowRoot, options?: MountOptions): Promise<Component<P, E> & InstanceType<T>>;
    createRoot<Props extends object, Plugins = any, SubEnv = any>(Root: ComponentConstructor<Props, Plugins, E>, config?: RootConfig<Props, SubEnv>): Root<Props, SubEnv>;
    makeNode(Component: ComponentConstructor, props: any): ComponentNode;
    mountNode(node: ComponentNode, target: HTMLElement | ShadowRoot, options?: MountOptions): any;
    destroy(): void;
    createComponent<P extends Props>(name: string | null, isStatic: boolean, hasSlotsProp: boolean, hasDynamicPropList: boolean, propList: string[]): (props: P, key: string, ctx: ComponentNode, parent: any, C: any) => any;
    handleError(...args: Parameters<typeof handleError>): void;
}
declare function mount<T extends abstract new (...args: any) => any = any, Plugins = any, P extends object = any, E = any>(C: T & ComponentConstructor<P, Plugins, E>, target: HTMLElement, config?: AppConfig<P, E> & MountOptions): Promise<Component<P, Plugins, E> & InstanceType<T>>;

declare function signal<T>(value: T, opts?: Opts): {
    readonly get: () => T;
    readonly set: (newValue: T | ((prevValue: T) => T)) => void;
};
declare function effect<T>(fn: () => T, opts?: Opts): () => void;
declare function derived<T>(fn: () => T, opts?: Opts): () => T;
declare function withoutReactivity<T extends (...args: any[]) => any>(fn: T): ReturnType<T>;

/**
 * The purpose of this hook is to allow components to get a reference to a sub
 * html node or component.
 */
declare function useRef<T extends HTMLElement = HTMLElement>(name: string): {
    el: T | null;
};
/**
 * This hook is useful as a building block for some customized hooks, that may
 * need a reference to the env of the component calling them.
 */
declare function useEnv<E extends Env>(): E;
/**
 * This hook is a simple way to let components use a sub environment.  Note that
 * like for all hooks, it is important that this is only called in the
 * constructor method.
 */
declare function useSubEnv(envExtension: Env): void;
declare function useChildSubEnv(envExtension: Env): void;
declare type EffectDeps<T extends unknown[]> = T | (T extends [...infer H, never] ? EffectDeps<H> : never);
/**
 * @template T
 * @param {...T} dependencies the dependencies computed by computeDependencies
 * @returns {void|(()=>void)} a cleanup function that reverses the side
 *      effects of the effect callback.
 */
declare type Effect<T extends unknown[]> = (...dependencies: EffectDeps<T>) => void | (() => void);
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
declare function useEffect<T extends unknown[]>(effect: Effect<T>, computeDependencies?: () => [...T]): void;
/**
 * When a component needs to listen to DOM Events on element(s) that are not
 * part of his hierarchy, we can use the `useExternalListener` hook.
 * It will correctly add and remove the event listener, whenever the
 * component is mounted and unmounted.
 *
 * Example:
 *  a menu needs to listen to the click on window to be closed automatically
 *
 * Usage:
 *  in the constructor of the OWL component that needs to be notified,
 *  `useExternalListener(window, 'click', this._doSomething);`
 * */
declare function useExternalListener(target: EventTarget, eventName: string, handler: EventListener, eventParams?: AddEventListenerOptions): void;

declare function onWillStart(fn: () => Promise<void> | void | any): void;
declare function onWillUpdateProps(fn: (nextProps: any) => Promise<void> | void | any): void;
declare function onMounted(fn: () => void | any): void;
declare function onWillPatch(fn: () => any | void): void;
declare function onPatched(fn: () => void | any): void;
declare function onWillUnmount(fn: () => void | any): void;
declare function onWillDestroy(fn: () => void | any): void;
declare function onWillRender(fn: () => void | any): void;
declare function onRendered(fn: () => void | any): void;
declare type OnErrorCallback = (error: any) => void | any;
declare function onError(callback: OnErrorCallback): void;

declare class OwlError extends Error {
    cause?: any;
}

declare const blockDom: {
    config: {
        shouldNormalizeDom: boolean;
        mainEventHandler: (data: any, ev: Event, currentTarget?: EventTarget | null | undefined) => boolean;
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

export { App, Component, ComponentConstructor, EventBus, OwlError, Plugin, PluginManager, Registry, __info__, batched, blockDom, derived, effect, htmlEscape, loadFile, markRaw, markup, mount, onError, onMounted, onPatched, onRendered, onWillDestroy, onWillPatch, onWillRender, onWillStart, onWillUnmount, onWillUpdateProps, reactive, signal, status, toRaw, useChildSubEnv, useComponent, useEffect, useEnv, useExternalListener, usePlugins, useRef, useState, useSubEnv, validate, validateType, whenReady, withoutReactivity, xml };
