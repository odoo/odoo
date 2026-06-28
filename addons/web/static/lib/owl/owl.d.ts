export type CustomDirectives = Record<string, (node: Element, value: string, modifier: string[]) => void>;
export type Template = (context: any, vnode: any, key?: string) => any;
export type TemplateFunction = (app: any, bdom: any, helpers: any) => Template;
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
export type BlockType = (data?: any[], children?: VNode[]) => VNode;
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
declare class VText {
	text: string | String;
	parentEl?: HTMLElement | undefined;
	el?: any;
	constructor(text: string | String);
	mount(parent: HTMLElement, afterNode: Node | null): void;
	moveBeforeDOMNode(node: Node | null, parent?: HTMLElement | undefined): void;
	moveBeforeVNode(other: VText | null, afterNode: Node | null): void;
	beforeRemove(): void;
	remove(): void;
	firstNode(): Node;
	patch(other: VText): void;
	toString(): string | String;
}
declare function text(str: string | String): VNode<VText>;
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
export type MountTarget = HTMLElement | ShadowRoot;
export interface VNode<T = any> {
	mount(parent: MountTarget, afterNode: Node | null): void;
	moveBeforeDOMNode(node: Node | null, parent?: MountTarget): void;
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
export type BDom = VNode<any>;
declare function mount(vnode: VNode, fixture: MountTarget, afterNode?: Node | null): void;
declare function patch(vnode1: VNode, vnode2: VNode, withBeforeRemove?: boolean): void;
declare function remove(vnode: VNode, withBeforeRemove?: boolean): void;
export declare class OwlError extends Error {
	cause?: any;
}
declare const STATUS: {
	readonly NEW: 0;
	readonly MOUNTED: 1;
	readonly CANCELLED: 2;
	readonly DESTROYED: 3;
};
export type StatusValue = (typeof STATUS)[keyof typeof STATUS];
export type Callback = (...args: any[]) => void;
/**
 * Creates a batched version of a callback so that all calls to it in the same
 * microtick will only call the original callback once.
 *
 * @param callback the callback to batch
 * @returns a batched version of the original callback
 */
export declare function batched(callback: Callback): Callback;
export interface ReactiveValue<TRead, TWrite = TRead> {
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
export interface Atom<T = any> {
	observers: Set<ComputationAtom>;
	value: T;
}
export interface ComputationAtom<T = any> extends Atom<T> {
	compute: () => T;
	isDerived: boolean;
	sources: Set<Atom>;
	state: ComputationState;
}
export declare function untrack<T>(fn: (...args: any[]) => T): T;
export type Constructor<T = any> = {
	new (...args: any[]): T;
};
export declare const hasDefault: unique symbol;
export type WithDefault<T> = T & {
	[hasDefault]: T;
};
export declare const isOptional: unique symbol;
export type Optional<T> = T & {
	[isOptional]: T;
};
export declare const typeBrand: unique symbol;
export type Type<T> = T & {
	[typeBrand]: T;
	/**
	 * Marks the type as optional: `undefined` passes validation, and an object
	 * key with an optional type may be omitted.
	 */
	optional(): Optional<T>;
	/**
	 * Marks the type as optional, with a default value to fill it: the reader
	 * of the value always gets one (the default replaces an omitted value). The
	 * default can be given as a factory (`() => value`), which is called once
	 * per consumer, so mutable defaults ([], {}) are not shared. A default for
	 * a function type must use the factory form.
	 */
	optional(value: T extends Function ? () => T : T | (() => T)): WithDefault<T>;
	type: T;
};
export type IsAny<T> = 0 extends 1 & T ? true : false;
export type HasDefault<T> = IsAny<T> extends true ? false : T extends {
	[hasDefault]: any;
} ? true : false;
export type IsOptional<T> = IsAny<T> extends true ? false : T extends {
	[isOptional]: any;
} ? true : false;
export type StripDefault<T> = T extends {
	[hasDefault]: infer U;
} ? U : T;
export type StripOptional<T> = T extends {
	[isOptional]: infer U;
} ? U | undefined : T;
export type StripType<T> = T extends {
	[typeBrand]: infer U;
} ? U : T;
export type StripBrands<T> = StripType<StripDefault<StripOptional<T>>>;
export type StripBrandsAll<T extends any[]> = {
	[K in keyof T]: StripBrands<T[K]>;
};
export type GetDefaultedKeys<T> = keyof T extends infer K ? K extends keyof T ? HasDefault<T[K]> extends true ? K : never : never : never;
export type GetOptionalEntries<T> = {
	[K in keyof T as IsOptional<T[K]> extends true ? K : HasDefault<T[K]> extends true ? K : never]?: StripBrands<T[K]>;
};
export type GetRequiredEntries<T> = {
	[K in keyof T as IsOptional<T[K]> extends true ? never : HasDefault<T[K]> extends true ? never : K]: StripBrands<T[K]>;
};
export type PrettifyShape<T> = T extends Function ? T : {
	[K in keyof T]: T[K];
};
export type ResolveOptionalEntries<T> = PrettifyShape<GetRequiredEntries<T> & GetOptionalEntries<T>>;
export type ResolveReaderObjectType<T> = PrettifyShape<{
	[K in keyof T as IsOptional<T[K]> extends true ? never : K]: StripBrands<T[K]>;
} & {
	[K in keyof T as IsOptional<T[K]> extends true ? K : never]?: StripBrands<T[K]>;
}>;
export type KeyedObject<K extends string[]> = {
	[P in K[number]]: any;
};
export type ResolveShapedObject<T extends {}> = PrettifyShape<ResolveOptionalEntries<T>>;
export type ResolveObjectType<T extends {}> = ResolveShapedObject<T extends string[] ? KeyedObject<T> : T>;
export type UnionToIntersection<U> = (U extends any ? (_: U) => any : never) extends (_: infer I) => void ? I : never;
/**
 * Returns the default value factory attached to a type by `.optional(value)`,
 * if any. This is how consumers (props, config, ...) resolve defaults at
 * runtime: validation only runs in dev mode, so defaults are metadata on the
 * schema, not a validation side-effect.
 */
export declare function getDefault(type: any): (() => any) | undefined;
/**
 * Returns `value` with defaults from the schema filled in, at any depth: a
 * default fires when the value at its schema position is `undefined`. The
 * input is never mutated; objects are copied along the changed paths only, so
 * if nothing is filled in, `value` is returned as is.
 *
 * Note that this only recurses through object shapes, tuples and arrays
 * (unions are ambiguous, records have no fixed keys).
 */
export declare function applyDefaults<T>(value: unknown, type: T): StripBrands<T>;
declare function anyType(): Type<any>;
declare function booleanType(): Type<boolean>;
declare function numberType<T extends number = number>(): Type<T>;
declare function stringType<T extends string = string>(): Type<T>;
declare function arrayType(): Type<any[]>;
declare function arrayType<T>(): Type<T[]>;
declare function arrayType<T>(elementType: T): Type<StripBrands<T>[]>;
declare function constructorType<T extends Constructor>(constructor: T): Type<T>;
declare function customValidator<T>(type: T, validator: (value: StripBrands<T>) => boolean, errorMessage?: string): Type<StripBrands<T>>;
declare function functionType(): Type<(...parameters: any[]) => any>;
declare function functionType<const P extends unknown[]>(parameters: P): Type<(...parameters: StripBrandsAll<P>) => void>;
declare function functionType<const P extends unknown[], R>(): Type<(...parameters: P) => R>;
declare function functionType<const P extends unknown[], R>(parameters: P, result: R): Type<(...parameters: StripBrandsAll<P>) => StripBrands<R>>;
declare function instanceType<T extends Constructor>(constructor: T): Type<InstanceType<T>>;
declare function intersection<T extends any[]>(types: T): Type<UnionToIntersection<StripBrands<T[number]>>>;
export type LiteralTypes = number | string | boolean | null | undefined;
declare function literalType<const T extends LiteralTypes>(literal: T): Type<T>;
declare function literalSelection<const T extends LiteralTypes>(literals: T[]): Type<T>;
declare function objectType(): Type<Record<string, any>>;
declare function objectType<const Keys extends string[]>(keys: Keys): Type<ResolveOptionalEntries<KeyedObject<Keys>>>;
declare function objectType<Shape extends {}>(): Type<ResolveOptionalEntries<Shape>>;
declare function objectType<Shape extends {}>(shape: Shape): Type<ResolveOptionalEntries<Shape>>;
declare function strictObjectType<const Keys extends string[]>(keys: Keys): Type<ResolveOptionalEntries<KeyedObject<Keys>>>;
declare function strictObjectType<Shape extends {}>(shape: Shape): Type<ResolveOptionalEntries<Shape>>;
declare function promiseType(): Type<Promise<void>>;
declare function promiseType<T>(type: T): Type<Promise<StripBrands<T>>>;
declare function recordType(): Type<Record<PropertyKey, any>>;
declare function recordType<V>(valueType: V): Type<Record<PropertyKey, StripBrands<V>>>;
declare function tuple<const T extends unknown[]>(types: T): Type<StripBrandsAll<T>>;
declare function union<T extends unknown[]>(types: T): Type<StripBrands<T[number]>>;
declare function reactiveValueType(): Type<ReactiveValue<any>>;
declare function reactiveValueType<T>(): Type<ReactiveValue<T>>;
declare function reactiveValueType<T>(type: T): Type<ReactiveValue<StripBrands<T>>>;
declare function ref(): Type<HTMLElement | null>;
declare function ref<T extends Constructor<HTMLElement>>(type: T): Type<InstanceType<T> | null>;
declare const types: {
	and: typeof intersection;
	any: typeof anyType;
	array: typeof arrayType;
	boolean: typeof booleanType;
	constructor: typeof constructorType;
	customValidator: typeof customValidator;
	function: typeof functionType;
	instanceOf: typeof instanceType;
	literal: typeof literalType;
	number: typeof numberType;
	object: typeof objectType;
	or: typeof union;
	promise: typeof promiseType;
	record: typeof recordType;
	ref: typeof ref;
	selection: typeof literalSelection;
	signal: typeof reactiveValueType;
	strictObject: typeof strictObjectType;
	string: typeof stringType;
	tuple: typeof tuple;
};
export interface ResourceOptions<T> {
	name?: string;
	validation?: T;
}
export interface ResourceAddOptions {
	sequence?: number;
}
export type Item<T> = StripBrands<T>;
export declare class Resource<T> {
	private _items;
	private _name?;
	private _validation?;
	constructor(options?: ResourceOptions<T>);
	items: ReactiveValue<Item<T>[]>;
	add(item: Item<T>, options?: ResourceAddOptions): Resource<T>;
	delete(item: Item<T>): Resource<T>;
	has(item: Item<T>): boolean;
	use(item: Item<T>, options?: ResourceAddOptions): Resource<T>;
}
export interface PluginConstructor {
	new (...args: any[]): Plugin$1;
	id: string;
	sequence: number;
}
declare class Plugin$1 {
	private static _shadowId;
	static get id(): string;
	static set id(shadowId: string);
	static sequence: number;
	__owl__: PluginManager;
	constructor(manager: PluginManager);
	setup(): void;
}
export interface PluginManagerOptions {
	parent?: PluginManager | null;
	config?: Record<string, any>;
}
declare class PluginManager extends Scope {
	config: Record<string, any>;
	plugins: Record<string, Plugin$1>;
	ready: Promise<void>;
	private hasPendingReady;
	constructor(app: any, options?: PluginManagerOptions);
	destroy(): void;
	getPluginById<T extends Plugin$1>(id: string): T | null;
	getPlugin<T extends PluginConstructor>(pluginConstructor: T): InstanceType<T> | null;
	startPlugin<T extends PluginConstructor>(pluginConstructor: T): InstanceType<T> | null;
	startPlugins(pluginConstructors: PluginConstructor[]): void;
}
/**
 * Returns the active scope. Throws if no scope is active — use this inside
 * hooks and setup functions where the caller is expected to be in a scope.
 */
export declare function useScope(): Scope;
export declare abstract class Scope {
	app: any;
	pluginManager: PluginManager;
	status: StatusValue;
	computations: ComputationAtom[];
	willStart: Array<() => any>;
	private _controller;
	private _destroyCbs;
	constructor(app: any);
	/**
	 * Pushes this scope on the stack for the duration of `callback`. Any code
	 * executed inside `callback` can reach this scope via `useScope()`.
	 */
	run<T>(callback: () => T): T;
	/**
	 * An AbortSignal tied to this scope's lifetime. If the scope is already
	 * dead, returns a pre-aborted signal. Lazily allocates an AbortController
	 * on first access.
	 */
	get abortSignal(): AbortSignal;
	/**
	 * Awaits `p`, throwing an AbortError if the scope is dead before or after
	 * the await. Unlike `until(signal, p)`, this does not allocate an
	 * AbortController — status checks are sufficient for guarding between
	 * awaits.
	 */
	until<T>(p: Promise<T>): Promise<T>;
	/**
	 * Registers a callback to run when the scope is destroyed. If the scope is
	 * already destroyed, the callback is invoked immediately.
	 */
	onDestroy(cb: () => void): void;
	/**
	 * Marks the scope as cancelled and aborts its signal. Used when an entity is
	 * abandoned before it reaches the MOUNTED state. Subclasses may override to
	 * extend the behavior (e.g. ComponentNode recurses to children).
	 */
	cancel(): void;
	/**
	 * Aborts the scope's signal, runs all registered onDestroy callbacks in
	 * reverse registration order, disposes any computations attached to this
	 * scope, and transitions status to DESTROYED. Callbacks run *before* the
	 * status transition so they can still observe the pre-destroyed state
	 * (matching the prior onWillDestroy contract). Errors in callbacks are
	 * routed to `reportError`.
	 */
	finalize(reportError: (e: unknown) => void): void;
	/**
	 * Wrapper applied to lifecycle callbacks before they are stored. The base
	 * implementation prepends the scope as the first argument, so every
	 * lifecycle callback receives the scope it was registered in.
	 * ComponentNode overrides to additionally bind `this` to the component and,
	 * in dev mode, to rename the bound function so the hook shows up as
	 * `ComponentName.hookName` in stack traces.
	 */
	decorate(fn: Function, _hookName: string): Function;
}
/**
 * Returns the scope currently active on the stack, or null if none. Prefer
 * `useScope()` in hook-like code that expects to be called inside a scope;
 * reach for `getScope()` only when the absence of a scope is meaningful.
 */
export declare function getScope(): Scope | null;
export type Target = object;
export type Reactive<T extends Target> = T;
/**
 * Mark an object or array so that it is ignored by the reactivity system
 *
 * @param value the value to mark
 * @returns the object itself
 */
export declare function markRaw<T extends Target>(value: T): T;
/**
 * Given a proxy objet, return the raw (non proxy) underlying object
 *
 * @param value a proxy value
 * @returns the underlying value
 */
export declare function toRaw<T extends Target, U extends Reactive<T>>(value: U | T): T;
/**
 * Wraps an object so it behaves like a signal, but with the familiar
 * property-access API: instead of `count()` / `count.set(n)`, you write
 * `state.count` and `state.count = n`. Reading and writing the proxy
 * transparently looks and feels like reading and writing the original object.
 *
 * Reactivity is nested: reading a property that holds another object/array
 * returns a proxy for that value too, recursively. Arrays, Maps, Sets, and
 * WeakMaps are also wrapped, so `state.items.push(x)` or `state.map.set(k, v)`
 * notify subscribers the same way property writes do.
 *
 * Subscriptions are only created when a read happens *while a computation is
 * active* — i.e. inside a component's render, or inside an `effect`,
 * `computed`, or `asyncComputed`. Reading the proxy from a plain function
 * with no surrounding computation just returns the value without subscribing
 * anything.
 *
 * @param target the object to make reactive
 * @returns a proxy that tracks reads/writes against `target`
 */
export declare function proxy<T extends Target>(target: T): T;
export interface Signal<T> extends ReactiveValue<T> {
	/**
	 * Update the value of the signal with a new value. If the new value is different
	 * from the previous values, all computations that depends on this signal will
	 * be invalidated, and effects will rerun.
	 */
	set(nextValue: T): void;
}
export interface SignalOptions<T> {
	type?: T;
}
declare function triggerSignal(signal: Signal<any>): void;
declare function signalRef(): Signal<HTMLElement | null>;
declare function signalRef<T extends Constructor<HTMLElement>>(type: T): Signal<InstanceType<T> | null>;
declare function signalArray<T>(initialValue: T[]): Signal<T[]>;
declare function signalArray<T>(initialValue: NoInfer<T>[], options: SignalOptions<T>): Signal<T[]>;
declare function signalObject<T extends Record<PropertyKey, any>>(initialValue: T): Signal<T>;
declare function signalObject<T extends Record<PropertyKey, any>>(initialValue: NoInfer<T>, options: SignalOptions<T>): Signal<T>;
export interface MapSignalOptions<K, V> {
	name?: string;
	keyType?: K;
	valueType?: V;
}
declare function signalMap<K, V>(initialValue: Map<K, V>): Signal<Map<K, V>>;
declare function signalMap<K, V>(initialValue: NoInfer<Map<K, V>>, options: MapSignalOptions<K, V>): Signal<Map<K, V>>;
declare function signalSet<T>(initialValue: Set<T>): Signal<Set<T>>;
declare function signalSet<T>(initialValue: Set<NoInfer<T>>, options: SignalOptions<T>): Signal<Set<T>>;
export declare function signal<T>(value: T): Signal<T>;
export declare function signal<T>(value: NoInfer<T>, options: SignalOptions<T>): Signal<T>;
export declare namespace signal {
	var trigger: typeof triggerSignal;
	var ref: typeof signalRef;
	var Array: typeof signalArray;
	var Map: typeof signalMap;
	var Object: typeof signalObject;
	var Set: typeof signalSet;
}
export interface ComputedOptions<TWrite> {
	set?(value: TWrite): void;
}
export declare function computed<TRead, TWrite = TRead>(getter: () => TRead, options?: ComputedOptions<TWrite>): ReactiveValue<TRead, TWrite>;
export declare function effect<T>(fn: () => T): () => void;
export interface AsyncComputedContext {
	readonly abortSignal: AbortSignal;
}
export interface AsyncComputedOptions<T> {
	initial?: T;
}
export interface AsyncComputed<T> {
	(): T | undefined;
	loading(): boolean;
	error(): Error | null;
	refresh(): void;
	dispose(): void;
	/**
	 * Returns a promise that resolves as soon as no run is in flight: if a run
	 * is currently running it resolves once that run (or any run that supersedes
	 * it) settles, otherwise it resolves immediately. It never rejects — fetcher
	 * errors are surfaced through `error()`. Handy to await the value in
	 * `onWillStart`: `onWillStart(() => data.currentPromise())`.
	 */
	currentPromise(): Promise<void>;
}
/**
 * @experimental The exact API is subject to change in future versions.
 */
export declare function asyncComputed<T>(fetcher: (ctx: AsyncComputedContext) => Promise<T>, options?: AsyncComputedOptions<T>): AsyncComputed<T>;
export interface ValidationIssue {
	message: string;
	path?: string;
	received?: any;
	[K: string]: any;
}
export declare function assertType(value: any, validation: any, errorMessage?: string): void;
export declare function validateType(value: any, validation: any): ValidationIssue[];
export interface RegistryOptions<T> {
	name?: string;
	validation?: T;
}
export interface RegistryAddOptions extends ResourceAddOptions {
	force?: boolean;
}
type Item$1<T> = StripBrands<T>;
export declare class Registry<T> {
	private _map;
	private _name;
	private _validation?;
	constructor(options?: RegistryOptions<T>);
	entries: ReactiveValue<[
		string,
		Item$1<T>
	][]>;
	items: ReactiveValue<Item$1<T>[]>;
	addById<U extends {
		id: string;
	} & Item$1<T>>(item: U, options?: RegistryAddOptions): Registry<T>;
	add(key: string, value: Item$1<T>, options?: RegistryAddOptions): Registry<T>;
	get(key: string, defaultValue?: Item$1<T>): Item$1<T>;
	delete(key: string): void;
	has(key: string): boolean;
	use(key: string, value: Item$1<T>, options?: RegistryAddOptions): Registry<T>;
	useById<U extends {
		id: string;
	} & Item$1<T>>(item: U, options?: RegistryAddOptions): Registry<T>;
}
/**
 * Creates a reactive effect bound to the surrounding component or plugin.
 * Equivalent to `onWillDestroy(effect(fn))`: the effect runs once immediately,
 * re-runs whenever any reactive value (signal, computed, proxy property) read
 * during its execution changes, and is disposed when the owning scope is
 * destroyed. If the callback returns a function, that function is called as
 * cleanup before each re-run and on disposal.
 */
export declare function useEffect(fn: Parameters<typeof effect>[0]): void;
/**
 * Adds an event listener to a target and automatically removes it when the
 * surrounding component or plugin is destroyed.
 *
 * `target` can be either an `EventTarget` (the listener is attached
 * immediately) or a `Signal<EventTarget | null>` such as a `t-ref` (the
 * listener is attached through a `useEffect` and re-attaches when the signal's
 * value changes; nothing is attached while the signal is null).
 *
 * The handler is not bound: it is passed as-is to `addEventListener`, so inside
 * it `this` is the event target, not the calling component. Wrap a method in an
 * arrow function (or bind it) if it relies on `this`.
 *
 * Example — close a menu when the user clicks anywhere on `window`:
 *   useListener(window, "click", () => this.close());
 */
export declare function useListener(target: EventTarget | Signal<EventTarget | null>, eventName: string, handler: EventListener, eventParams?: AddEventListenerOptions): void;
export declare function onWillStart(fn: (scope: Scope) => Promise<void> | void | any): void;
export declare function onWillDestroy(fn: (scope: Scope) => void | any): void;
export type PluginInstance<T extends PluginConstructor> = Omit<InstanceType<T>, "setup">;
export declare function plugin<T extends PluginConstructor>(pluginType: T): PluginInstance<T>;
export declare function config<T = any>(key: string): T;
export declare function config<T>(key: string, type: WithDefault<T>): T;
export declare function config<T>(key: string, type: Optional<T>): T | undefined;
export declare function config<T>(key: string, type: T): StripBrands<T>;
export declare class EventBus extends EventTarget {
	trigger(name: string, payload?: any): void;
}
declare class Markup extends String {
}
export declare function htmlEscape(str: any): Markup;
export declare function markup(strings: TemplateStringsArray, ...placeholders: unknown[]): Markup;
export declare function markup(value: string): Markup;
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
export type Position = "first-child" | "last-child";
export interface MountOptions {
	position?: Position;
	afterNode?: Node | null;
}
declare class MountFiber extends RootFiber {
	target: MountTarget | null;
	position: Position;
	afterNode: Node | null;
	prepared: boolean;
	onPrepared: (() => void) | null;
	constructor(node: ComponentNode, target: MountTarget | null, options?: MountOptions);
	complete(): void;
	commit(target: MountTarget, options?: MountOptions): void;
	private _mount;
}
export type LifecycleHook = Function;
declare class ComponentNode extends Scope implements VNode<ComponentNode> {
	fiber: Fiber | null;
	component: Component;
	bdom: BDom | null;
	componentName: string;
	forceNextRender: boolean;
	parentKey: string | null;
	props: Record<string, any>;
	defaultProps: Record<string, any> | null;
	renderFn: Function;
	parent: ComponentNode | null;
	children: {
		[key: string]: ComponentNode;
	};
	willUpdateProps: LifecycleHook[];
	propsUpdated: LifecycleHook[];
	willUnmount: LifecycleHook[];
	mounted: LifecycleHook[];
	willPatch: LifecycleHook[];
	patched: LifecycleHook[];
	signalComputation: ComputationAtom;
	trackedRefs: Map<{
		set(v: null): void;
	}, {
		value: HTMLElement | null;
	}> | null;
	constructor(C: ComponentConstructor, props: Record<string, any>, app: App, parent: ComponentNode | null, parentKey: string | null);
	decorate(f: Function, hookName: string): Function;
	initiateRender(fiber: Fiber | MountFiber): Promise<void>;
	render(deep: boolean): Promise<void>;
	cancel(): void;
	_cancel(): void;
	destroy(): void;
	_destroy(): void;
	/**
	 * Unset any tracked t-ref whose element is no longer in the document, and stop
	 * tracking it (createRef re-registers it on the next render if the element
	 * comes back). `isConnected` is the discriminator: a ref the block's own
	 * remove() failed to clear (bulk removal) points at a detached element and is
	 * cleared, while a ref a surviving sibling just took over (t-if/t-else with a
	 * shared signal) points at a still-connected element and is left alone.
	 *
	 * Called after this component's dom settles: at the tail of `_patch` (before
	 * user `onPatched`), so an element removed in place is caught, and — for the
	 * nodes collected during `_destroy` — after a removed subtree is detached.
	 */
	sweepRefs(): void;
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
	/**
	 * Register a t-ref signal bound to an element this component hosts, so its
	 * lifecycle can clear it (see sweepRefs / _destroy). Idempotent — re-tracking
	 * the same signal on each render just refreshes its atom.
	 */
	trackRef(ref: {
		set(v: null): void;
	}, atom: {
		value: HTMLElement | null;
	}): void;
	patch(): void;
	_patch(): void;
	beforeRemove(): void;
	remove(): void;
}
export interface StaticComponentProperties {
	template: string;
	components?: {
		[componentName: string]: ComponentConstructor;
	};
}
export interface ComponentConstructor extends StaticComponentProperties {
	new (node: ComponentNode): Component;
}
export declare class Component {
	static template: string;
	__owl__: ComponentNode;
	constructor(node: ComponentNode);
	setup(): void;
}
declare function staticProp<T = any>(key: string): T;
declare function staticProp<T>(key: string, type: WithDefault<T>): T;
declare function staticProp<T>(key: string, type: Optional<T>): T | undefined;
declare function staticProp<T>(key: string, type: T): StripBrands<T>;
export declare const isProps: unique symbol;
export type Props<T extends {}> = T & {
	[isProps]: never;
};
export type PropsWithDefaults<T extends {}, DK extends PropertyKey> = T & {
	[isProps]: DK;
};
export type GetPropsWithOptionals<T> = T extends {
	[isProps]: infer DK extends PropertyKey;
} ? Omit<T, typeof isProps | (DK & keyof T)> & Partial<Pick<T, DK & keyof T>> : never;
export type GetProps<T> = {
	[K in keyof T]: T[K] extends {
		[isProps]: PropertyKey;
	} ? (x: GetPropsWithOptionals<T[K]>) => void : never;
}[keyof T] extends (x: infer I) => void ? {
	[K in keyof I]: I[K];
} : never;
export type ResolveProps<Shape> = [
	GetDefaultedKeys<Shape>
] extends [
	never
] ? Props<ResolveReaderObjectType<Shape>> : PropsWithDefaults<ResolveReaderObjectType<Shape>, GetDefaultedKeys<Shape> & PropertyKey>;
export interface PropsFunction {
	(): Props<Record<string, any>>;
	<const Keys extends string[]>(keys: Keys): Props<ResolveObjectType<Keys>>;
	<Shape extends {}>(shape: Shape): ResolveProps<Shape>;
	static: typeof staticProp;
}
export declare const props: PropsFunction;
declare class Scheduler {
	static requestAnimationFrame: (callback: FrameRequestCallback) => number;
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
}
export interface TemplateSetConfig {
	dev?: boolean;
	translatableAttributes?: string[];
	translateFn?: (s: string, translationCtx: string) => string;
	templates?: string | Document | Record<string, string | TemplateFunction>;
	getTemplate?: (s: string) => Element | Function | string | void;
	customDirectives?: CustomDirectives;
	globalValues?: object;
}
export declare class TemplateSet {
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
	addTemplate(name: string, template: string | Element | TemplateFunction): void;
	addTemplates(xml: string | Document): void;
	getTemplate(name: string): Template;
	private _compileTemplate;
	private _parseXML;
}
export declare const globalTemplates: {
	[key: string]: string | Element | TemplateFunction;
};
export declare function xml(...args: Parameters<typeof String.raw>): string;
export declare namespace xml {
	var nextId: number;
}
declare function validateTarget(target: HTMLElement | ShadowRoot): void;
export declare function whenReady(fn?: any): Promise<void>;
export type ComponentInstance<C extends ComponentConstructor> = C extends new (...args: any) => infer T ? T : never;
export interface RootConfig<P> {
	props?: P;
}
export interface AppConfig extends TemplateSetConfig {
	name?: string;
	plugins?: PluginConstructor[] | Resource<PluginConstructor>;
	config?: Record<string, any>;
	test?: boolean;
}
export interface Root<T extends ComponentConstructor> {
	node: ComponentNode;
	promise: Promise<ComponentInstance<T>>;
	prepare(): Promise<void>;
	mount(target: MountTarget, options?: MountOptions): Promise<ComponentInstance<T>>;
	destroy(): void;
}
export declare class App extends TemplateSet {
	static validateTarget: typeof validateTarget;
	static apps: Set<App>;
	static version: string;
	name: string;
	scheduler: Scheduler;
	roots: Set<Root<any>>;
	pluginManager: PluginManager;
	destroyed: boolean;
	constructor(config?: AppConfig);
	createRoot<T extends ComponentConstructor>(Root: T, config?: RootConfig<GetProps<ComponentInstance<T>>>): Root<T>;
	destroy(): void;
	_handleError(error: any): void;
}
declare function mount$1<T extends ComponentConstructor>(C: T, target: MountTarget, config?: AppConfig & RootConfig<GetProps<ComponentInstance<T>>> & MountOptions): Promise<ComponentInstance<T>>;
export declare class ErrorBoundary extends Component {
	static template: string;
	props: PropsWithDefaults<{
		error: ReactiveValue<any, any>;
	}, "error">;
	setup(): void;
}
export declare class Portal extends Component {
	static template: string;
	props: Props<{
		slots: {
			default: any;
		};
		target: string | HTMLElement | ReactiveValue<HTMLElement, HTMLElement>;
	}>;
	setup(): void;
}
export declare class Suspense extends Component {
	static template: string;
	props: Props<{
		slots: {
			default: any;
			fallback: any;
		};
	}>;
	private prepared;
	private mounted;
	private subRootMounted;
	setup(): void;
}
export type STATUS_DESCR = "new" | "started" | "mounted" | "cancelled" | "destroyed";
declare function status$1(entity: Component | Plugin$1): STATUS_DESCR;
export declare const useApp: () => App;
export declare function onWillUpdateProps(fn: (nextProps: any, scope: ComponentNode) => Promise<void> | void | any): void;
export declare function onMounted(fn: (scope: ComponentNode) => void | any): void;
export declare function onWillPatch(fn: (scope: ComponentNode) => any | void): void;
export declare function onPatched(fn: (scope: ComponentNode) => void | any): void;
export declare function onWillUnmount(fn: (scope: ComponentNode) => void | any): void;
export type OnErrorCallback = (error: any) => void | any;
export declare function onError(callback: OnErrorCallback): void;
declare const types$1: typeof types & {
	component: () => Type<typeof Component>;
};
export declare function providePlugins(pluginConstructors: PluginConstructor[] | Resource<PluginConstructor>, config?: Record<string, any>): void;
export declare const blockDom: {
	config: {
		shouldNormalizeDom: boolean;
		mainEventHandler: (data: any, ev: Event, currentTarget?: EventTarget | null) => boolean;
	};
	mount: typeof mount;
	patch: typeof patch;
	remove: typeof remove;
	list: typeof list;
	multi: typeof multi;
	text: typeof text;
	toggler: typeof toggler;
	createBlock: typeof createBlock;
	html: typeof html;
};
export declare const __info__: Record<string, string>;

export {
	Plugin$1 as Plugin,
	mount$1 as mount,
	status$1 as status,
	types$1 as t,
	types$1 as types,
};

export {};
