"use strict";
var owl = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // src/index.ts
  var index_exports = {};
  __export(index_exports, {
    App: () => App,
    Component: () => Component,
    ErrorBoundary: () => ErrorBoundary,
    EventBus: () => EventBus,
    OwlError: () => OwlError,
    Plugin: () => Plugin,
    Portal: () => Portal,
    Registry: () => Registry,
    Resource: () => Resource,
    Scope: () => Scope,
    Suspense: () => Suspense,
    TemplateSet: () => TemplateSet,
    __info__: () => __info__,
    assertType: () => assertType,
    asyncComputed: () => asyncComputed,
    batched: () => batched,
    blockDom: () => blockDom,
    computed: () => computed,
    config: () => config2,
    effect: () => effect,
    getScope: () => getScope,
    globalTemplates: () => globalTemplates,
    htmlEscape: () => htmlEscape,
    immediateEffect: () => immediateEffect,
    markRaw: () => markRaw,
    markup: () => markup,
    mount: () => mount2,
    onError: () => onError,
    onMounted: () => onMounted,
    onPatched: () => onPatched,
    onWillDestroy: () => onWillDestroy,
    onWillPatch: () => onWillPatch,
    onWillStart: () => onWillStart,
    onWillUnmount: () => onWillUnmount,
    onWillUpdateProps: () => onWillUpdateProps,
    plugin: () => plugin,
    prop: () => prop,
    props: () => props,
    providePlugins: () => providePlugins,
    proxy: () => proxy,
    signal: () => signal,
    status: () => status,
    toRaw: () => toRaw,
    types: () => types2,
    untrack: () => untrack,
    useApp: () => useApp,
    useEffect: () => useEffect,
    useListener: () => useListener,
    useScope: () => useScope,
    validateType: () => validateType,
    whenReady: () => whenReady,
    xml: () => xml
  });

  // ../owl-core/dist/owl-core.es.js
  var OwlError = class extends Error {
    cause;
  };
  var STATUS = {
    NEW: 0,
    MOUNTED: 1,
    // is ready, and in DOM. It has a valid el
    // component has been created, but has been replaced by a newer component before being mounted
    // it is cancelled until the next animation frame where it will be destroyed
    CANCELLED: 2,
    DESTROYED: 3
  };
  function batched(callback) {
    let scheduled = false;
    return function batchedCall(...args) {
      if (!scheduled) {
        scheduled = true;
        Promise.resolve().then(() => {
          scheduled = false;
          callback(...args);
        });
      }
    };
  }
  var ComputationState = /* @__PURE__ */ ((ComputationState2) => {
    ComputationState2[ComputationState2["EXECUTED"] = 0] = "EXECUTED";
    ComputationState2[ComputationState2["STALE"] = 1] = "STALE";
    ComputationState2[ComputationState2["PENDING"] = 2] = "PENDING";
    return ComputationState2;
  })(ComputationState || {});
  var atomSymbol = /* @__PURE__ */ Symbol("Atom");
  var observers = [];
  var immediateObservers = [];
  var currentComputation;
  function createComputation(compute, isDerived, state = 1, immediate = false) {
    return {
      state,
      value: void 0,
      compute,
      sources: /* @__PURE__ */ new Set(),
      observers: /* @__PURE__ */ new Set(),
      isDerived,
      immediate
    };
  }
  function onReadAtom(atom) {
    if (!currentComputation) {
      return;
    }
    currentComputation.sources.add(atom);
    atom.observers.add(currentComputation);
  }
  function onWriteAtom(atom) {
    for (const ctx of atom.observers) {
      if (ctx.state === 0) {
        if (ctx.isDerived) {
          markDownstream(ctx);
        } else if (ctx.immediate) {
          immediateObservers.push(ctx);
        } else {
          observers.push(ctx);
        }
      }
      ctx.state = 1;
    }
    if (immediateObservers.length) {
      const toRun = immediateObservers;
      immediateObservers = [];
      for (const ctx of toRun) {
        updateComputation(ctx);
      }
    }
    batchProcessEffects();
  }
  var batchProcessEffects = batched(processEffects);
  function processEffects() {
    const pending = observers;
    observers = [];
    for (let i = 0; i < pending.length; i++) {
      updateComputation(pending[i]);
    }
  }
  function getCurrentComputation() {
    return currentComputation;
  }
  function setComputation(computation) {
    currentComputation = computation;
  }
  function updateComputation(computation) {
    const state = computation.state;
    if (state === 0) {
      return;
    }
    if (state === 2) {
      for (const source of computation.sources) {
        if (!("compute" in source)) {
          continue;
        }
        updateComputation(source);
        if (computation.state === 1) {
          break;
        }
      }
      if (computation.state !== 1) {
        computation.state = 0;
        return;
      }
    }
    removeSources(computation);
    const previousComputation = currentComputation;
    currentComputation = computation;
    try {
      computation.value = computation.compute();
      computation.state = 0;
    } finally {
      currentComputation = previousComputation;
    }
  }
  function removeSources(computation) {
    const sources = computation.sources;
    for (const source of sources) {
      const observers2 = source.observers;
      observers2.delete(computation);
    }
    sources.clear();
  }
  function disposeComputation(computation) {
    for (const source of computation.sources) {
      source.observers.delete(computation);
      if ("compute" in source && source.isDerived && source.observers.size === 0) {
        disposeComputation(source);
      }
    }
    computation.sources.clear();
    computation.state = 1;
  }
  function markDownstream(computation) {
    const stack = [computation];
    let current;
    while (current = stack.pop()) {
      for (const observer of current.observers) {
        if (observer.state) {
          continue;
        }
        observer.state = 2;
        if (observer.isDerived) {
          stack.push(observer);
        } else {
          observers.push(observer);
        }
      }
    }
  }
  function untrack(fn) {
    const previousComputation = currentComputation;
    currentComputation = void 0;
    let result;
    try {
      result = fn();
    } finally {
      currentComputation = previousComputation;
    }
    return result;
  }
  var scopeStack = [];
  function useScope() {
    const scope = getScope();
    if (!scope) {
      throw new OwlError("No active scope");
    }
    return scope;
  }
  var Scope = class {
    app;
    status = STATUS.NEW;
    computations = [];
    willStart = [];
    _controller = null;
    _destroyCbs = null;
    constructor(app) {
      this.app = app;
    }
    /**
     * Pushes this scope on the stack for the duration of `callback`. Any code
     * executed inside `callback` can reach this scope via `useScope()`.
     */
    run(callback) {
      scopeStack.push(this);
      try {
        return callback();
      } finally {
        scopeStack.pop();
      }
    }
    /**
     * An AbortSignal tied to this scope's lifetime. If the scope is already
     * dead, returns a pre-aborted signal. Lazily allocates an AbortController
     * on first access.
     */
    get abortSignal() {
      if (this.status > STATUS.MOUNTED) {
        if (!this._controller) {
          this._controller = new AbortController();
          this._controller.abort();
        }
        return this._controller.signal;
      }
      return (this._controller ??= new AbortController()).signal;
    }
    /**
     * Awaits `p`, throwing an AbortError if the scope is dead before or after
     * the await. Unlike `until(signal, p)`, this does not allocate an
     * AbortController — status checks are sufficient for guarding between
     * awaits.
     */
    async until(p) {
      if (this.status > STATUS.MOUNTED) {
        throw makeAbortError();
      }
      const result = await p;
      if (this.status > STATUS.MOUNTED) {
        throw makeAbortError();
      }
      return result;
    }
    /**
     * Registers a callback to run when the scope is destroyed. If the scope is
     * already destroyed, the callback is invoked immediately.
     */
    onDestroy(cb) {
      if (this.status >= STATUS.DESTROYED) {
        cb();
        return;
      }
      (this._destroyCbs ??= []).push(cb);
    }
    /**
     * Marks the scope as cancelled and aborts its signal. Used when an entity is
     * abandoned before it reaches the MOUNTED state. Subclasses may override to
     * extend the behavior (e.g. ComponentNode recurses to children).
     */
    cancel() {
      if (this.status > STATUS.MOUNTED) {
        return;
      }
      this.status = STATUS.CANCELLED;
      this._controller?.abort();
    }
    /**
     * Aborts the scope's signal, runs all registered onDestroy callbacks in
     * reverse registration order, disposes any computations attached to this
     * scope, and transitions status to DESTROYED. Callbacks run *before* the
     * status transition so they can still observe the pre-destroyed state
     * (matching the prior onWillDestroy contract). Errors in callbacks are
     * routed to `reportError`.
     */
    finalize(reportError) {
      if (this.status >= STATUS.DESTROYED) {
        return;
      }
      if (this._controller && !this._controller.signal.aborted) {
        this._controller.abort();
      }
      const cbs = this._destroyCbs;
      if (cbs) {
        this._destroyCbs = null;
        for (let i = cbs.length - 1; i >= 0; i--) {
          try {
            cbs[i]();
          } catch (e) {
            reportError(e);
          }
        }
      }
      for (const computation of this.computations) {
        disposeComputation(computation);
      }
      this.status = STATUS.DESTROYED;
    }
    /**
     * Wrapper applied to lifecycle callbacks before they are stored. The base
     * implementation prepends the scope as the first argument, so every
     * lifecycle callback receives the scope it was registered in.
     * ComponentNode overrides to additionally bind `this` to the component and,
     * in dev mode, to rename the bound function so the hook shows up as
     * `ComponentName.hookName` in stack traces.
     */
    decorate(fn, _hookName) {
      return fn.bind(void 0, this);
    }
  };
  function getScope() {
    const len = scopeStack.length;
    return len ? scopeStack[len - 1] : null;
  }
  function isAbortError(e) {
    return typeof e === "object" && e !== null && e.name === "AbortError";
  }
  function makeAbortError() {
    const err = new Error("The operation was aborted");
    err.name = "AbortError";
    return err;
  }
  var KEYCHANGES = /* @__PURE__ */ Symbol("Key changes");
  var objectToString = Object.prototype.toString;
  var objectHasOwnProperty = Object.prototype.hasOwnProperty;
  function canBeMadeReactive(value) {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const raw = toRaw(value);
    if (Array.isArray(raw) || raw instanceof Set || raw instanceof Map || raw instanceof WeakMap) {
      return true;
    }
    return objectToString.call(raw) === "[object Object]";
  }
  function possiblyReactive(val, atom) {
    return !atom && canBeMadeReactive(val) ? proxy(val) : val;
  }
  var skipped = /* @__PURE__ */ new WeakSet();
  function markRaw(value) {
    skipped.add(value);
    return value;
  }
  function toRaw(value) {
    return targets.has(value) ? targets.get(value) : value;
  }
  var targetToKeysToAtomItem = /* @__PURE__ */ new WeakMap();
  function getTargetKeyAtom(target, key) {
    let keyToAtomItem = targetToKeysToAtomItem.get(target);
    if (!keyToAtomItem) {
      keyToAtomItem = /* @__PURE__ */ new Map();
      targetToKeysToAtomItem.set(target, keyToAtomItem);
    }
    let atom = keyToAtomItem.get(key);
    if (!atom) {
      atom = {
        value: void 0,
        observers: /* @__PURE__ */ new Set()
      };
      keyToAtomItem.set(key, atom);
    }
    return atom;
  }
  function onReadTargetKey(target, key, atom) {
    onReadAtom(atom ?? getTargetKeyAtom(target, key));
  }
  function onWriteTargetKey(target, key, atom) {
    if (!atom) {
      const keyToAtomItem = targetToKeysToAtomItem.get(target);
      if (!keyToAtomItem) {
        return;
      }
      if (!keyToAtomItem.has(key)) {
        return;
      }
      atom = keyToAtomItem.get(key);
    }
    onWriteAtom(atom);
  }
  var targets = /* @__PURE__ */ new WeakMap();
  var proxyCache = /* @__PURE__ */ new WeakMap();
  function proxifyTarget(target, atom) {
    if (!canBeMadeReactive(target)) {
      throw new OwlError(`Cannot make the given value reactive`);
    }
    if (skipped.has(target)) {
      return target;
    }
    if (targets.has(target)) {
      return target;
    }
    const reactive = proxyCache.get(target);
    if (reactive) {
      return reactive;
    }
    let handler;
    if (target instanceof Map) {
      handler = collectionsProxyHandler(target, "Map", atom);
    } else if (target instanceof Set) {
      handler = collectionsProxyHandler(target, "Set", atom);
    } else if (target instanceof WeakMap) {
      handler = collectionsProxyHandler(target, "WeakMap", atom);
    } else {
      handler = basicProxyHandler(atom);
    }
    const proxy2 = new Proxy(target, handler);
    proxyCache.set(target, proxy2);
    targets.set(proxy2, target);
    return proxy2;
  }
  function proxy(target) {
    return proxifyTarget(target, null);
  }
  function basicProxyHandler(atom) {
    return {
      get(target, key, receiver) {
        onReadTargetKey(target, key, atom);
        const value = Reflect.get(target, key, receiver);
        if (atom || typeof value !== "object" || value === null) {
          return value;
        }
        if (!canBeMadeReactive(value)) {
          return value;
        }
        const desc = Object.getOwnPropertyDescriptor(target, key);
        if (desc && !desc.writable && !desc.configurable) {
          return value;
        }
        return proxifyTarget(value, null);
      },
      set(target, key, value, receiver) {
        const hadKey = objectHasOwnProperty.call(target, key);
        const originalValue = Reflect.get(target, key, receiver);
        const ret = Reflect.set(target, key, toRaw(value), receiver);
        if (!hadKey && objectHasOwnProperty.call(target, key)) {
          onWriteTargetKey(target, KEYCHANGES, atom);
        }
        if (originalValue !== Reflect.get(target, key, receiver) || key === "length" && Array.isArray(target)) {
          onWriteTargetKey(target, key, atom);
        }
        return ret;
      },
      deleteProperty(target, key) {
        const ret = Reflect.deleteProperty(target, key);
        onWriteTargetKey(target, KEYCHANGES, atom);
        onWriteTargetKey(target, key, atom);
        return ret;
      },
      ownKeys(target) {
        onReadTargetKey(target, KEYCHANGES, atom);
        return Reflect.ownKeys(target);
      },
      has(target, key) {
        onReadTargetKey(target, KEYCHANGES, atom);
        return Reflect.has(target, key);
      }
    };
  }
  function makeKeyObserver(methodName, target, atom) {
    return (key) => {
      key = toRaw(key);
      onReadTargetKey(target, key, atom);
      return possiblyReactive(target[methodName](key), atom);
    };
  }
  function makeIteratorObserver(methodName, target, atom) {
    return function* () {
      onReadTargetKey(target, KEYCHANGES, atom);
      const keys = target.keys();
      for (const item of target[methodName]()) {
        const key = keys.next().value;
        onReadTargetKey(target, key, atom);
        yield possiblyReactive(item, atom);
      }
    };
  }
  function makeForEachObserver(target, atom) {
    return function forEach(forEachCb, thisArg) {
      onReadTargetKey(target, KEYCHANGES, atom);
      target.forEach(function(val, key, targetObj) {
        onReadTargetKey(target, key, atom);
        forEachCb.call(
          thisArg,
          possiblyReactive(val, atom),
          possiblyReactive(key, atom),
          possiblyReactive(targetObj, atom)
        );
      }, thisArg);
    };
  }
  function delegateAndNotify(setterName, getterName, target, atom) {
    return (key, value) => {
      key = toRaw(key);
      const hadKey = target.has(key);
      const originalValue = target[getterName](key);
      const ret = target[setterName](key, value);
      const hasKey = target.has(key);
      if (hadKey !== hasKey) {
        onWriteTargetKey(target, KEYCHANGES, atom);
      }
      if (originalValue !== target[getterName](key)) {
        onWriteTargetKey(target, key, atom);
      }
      return ret;
    };
  }
  function makeClearNotifier(target, atom) {
    return () => {
      const allKeys = [...target.keys()];
      target.clear();
      onWriteTargetKey(target, KEYCHANGES, atom);
      for (const key of allKeys) {
        onWriteTargetKey(target, key, atom);
      }
    };
  }
  var rawTypeToFuncHandlers = {
    Set: (target, atom) => ({
      has: makeKeyObserver("has", target, atom),
      add: delegateAndNotify("add", "has", target, atom),
      delete: delegateAndNotify("delete", "has", target, atom),
      keys: makeIteratorObserver("keys", target, atom),
      values: makeIteratorObserver("values", target, atom),
      entries: makeIteratorObserver("entries", target, atom),
      [Symbol.iterator]: makeIteratorObserver(Symbol.iterator, target, atom),
      forEach: makeForEachObserver(target, atom),
      clear: makeClearNotifier(target, atom),
      get size() {
        onReadTargetKey(target, KEYCHANGES, atom);
        return target.size;
      }
    }),
    Map: (target, atom) => ({
      has: makeKeyObserver("has", target, atom),
      get: makeKeyObserver("get", target, atom),
      set: delegateAndNotify("set", "get", target, atom),
      delete: delegateAndNotify("delete", "has", target, atom),
      keys: makeIteratorObserver("keys", target, atom),
      values: makeIteratorObserver("values", target, atom),
      entries: makeIteratorObserver("entries", target, atom),
      [Symbol.iterator]: makeIteratorObserver(Symbol.iterator, target, atom),
      forEach: makeForEachObserver(target, atom),
      clear: makeClearNotifier(target, atom),
      get size() {
        onReadTargetKey(target, KEYCHANGES, atom);
        return target.size;
      }
    }),
    WeakMap: (target, atom) => ({
      has: makeKeyObserver("has", target, atom),
      get: makeKeyObserver("get", target, atom),
      set: delegateAndNotify("set", "get", target, atom),
      delete: delegateAndNotify("delete", "has", target, atom)
    })
  };
  function collectionsProxyHandler(target, targetRawType, atom) {
    const specialHandlers = rawTypeToFuncHandlers[targetRawType](target, atom);
    return Object.assign(basicProxyHandler(atom), {
      // FIXME: probably broken when part of prototype chain since we ignore the receiver
      get(target2, key) {
        if (objectHasOwnProperty.call(specialHandlers, key)) {
          return specialHandlers[key];
        }
        onReadTargetKey(target2, key, atom);
        return possiblyReactive(target2[key], atom);
      }
    });
  }
  function buildSignal(value, set) {
    const atom = {
      type: "signal",
      value,
      observers: /* @__PURE__ */ new Set()
    };
    let readValue = set(atom);
    const readSignal = () => {
      onReadAtom(atom);
      return readValue;
    };
    readSignal[atomSymbol] = atom;
    readSignal.set = function writeSignal(newValue) {
      if (Object.is(atom.value, newValue)) {
        return;
      }
      atom.value = newValue;
      readValue = set(atom);
      onWriteAtom(atom);
    };
    return readSignal;
  }
  function triggerSignal(signal2) {
    if (typeof signal2 !== "function" || signal2[atomSymbol]?.type !== "signal") {
      throw new OwlError(`Value is not a signal (${signal2})`);
    }
    onWriteAtom(signal2[atomSymbol]);
  }
  function signalArray(initialValue) {
    return buildSignal(initialValue, (atom) => proxifyTarget(atom.value, atom));
  }
  function signalObject(initialValue) {
    return buildSignal(initialValue, (atom) => proxifyTarget(atom.value, atom));
  }
  function signalMap(initialValue) {
    return buildSignal(initialValue, (atom) => proxifyTarget(atom.value, atom));
  }
  function signalSet(initialValue) {
    return buildSignal(initialValue, (atom) => proxifyTarget(atom.value, atom));
  }
  function signal(value) {
    return buildSignal(value, (atom) => atom.value);
  }
  signal.trigger = triggerSignal;
  signal.Array = signalArray;
  signal.Map = signalMap;
  signal.Object = signalObject;
  signal.Set = signalSet;
  function readonlySetter() {
    throw new OwlError(
      "Cannot write to a read-only computed value. Pass a `set` option to make it writable."
    );
  }
  function computed(getter, options = {}) {
    const computation = createComputation(() => {
      const newValue = getter();
      if (!Object.is(computation.value, newValue)) {
        onWriteAtom(computation);
      }
      return newValue;
    }, true);
    function readComputed() {
      if (computation.state !== 0) {
        updateComputation(computation);
      }
      onReadAtom(computation);
      return computation.value;
    }
    readComputed[atomSymbol] = computation;
    readComputed.set = options.set ?? readonlySetter;
    getScope()?.computations.push(computation);
    return readComputed;
  }
  function effect(fn) {
    const computation = createComputation(() => {
      setComputation(void 0);
      unsubscribeEffect(computation);
      setComputation(computation);
      return fn();
    }, false);
    getCurrentComputation()?.observers.add(computation);
    updateComputation(computation);
    return function cleanupEffect2() {
      const previousComputation = getCurrentComputation();
      setComputation(void 0);
      unsubscribeEffect(computation);
      setComputation(previousComputation);
    };
  }
  function immediateEffect(fn) {
    const computation = createComputation(
      () => {
        setComputation(void 0);
        unsubscribeEffect(computation);
        setComputation(computation);
        return fn();
      },
      false,
      1,
      true
    );
    getCurrentComputation()?.observers.add(computation);
    updateComputation(computation);
    return function cleanupImmediateEffect() {
      const previousComputation = getCurrentComputation();
      setComputation(void 0);
      unsubscribeEffect(computation);
      setComputation(previousComputation);
    };
  }
  function unsubscribeEffect(effect2) {
    removeSources(effect2);
    cleanupEffect(effect2);
    for (const childEffect of effect2.observers) {
      childEffect.state = 0;
      removeSources(childEffect);
      unsubscribeEffect(childEffect);
    }
    effect2.observers.clear();
  }
  function cleanupEffect(effect2) {
    const cleanupFn = effect2.value;
    if (cleanupFn && typeof cleanupFn === "function") {
      cleanupFn();
      effect2.value = void 0;
    }
  }
  function asyncComputed(fetcher, options = {}) {
    const value = signal(options.initial);
    const loading = signal(false);
    const error = signal(null);
    const refreshTick = signal(0);
    const scope = getScope();
    let runId = 0;
    let runController = null;
    const stopEffect = effect(() => {
      refreshTick();
      const myRunId = ++runId;
      if (runController) {
        runController.abort();
      }
      const controller = new AbortController();
      runController = controller;
      const abortSignals = [controller.signal];
      if (scope?.abortSignal) {
        abortSignals.push(scope.abortSignal);
      }
      loading.set(true);
      error.set(null);
      let promise;
      try {
        promise = fetcher({ abortSignal: AbortSignal.any(abortSignals) });
      } catch (e) {
        if (myRunId !== runId) return;
        if (isAbortError(e)) {
          loading.set(false);
          return;
        }
        error.set(e);
        loading.set(false);
        return;
      }
      promise.then(
        (result) => {
          if (myRunId !== runId) return;
          value.set(result);
          loading.set(false);
        },
        (e) => {
          if (myRunId !== runId) return;
          if (isAbortError(e)) {
            loading.set(false);
            return;
          }
          error.set(e);
          loading.set(false);
        }
      );
    });
    function dispose() {
      stopEffect();
      runController?.abort();
      runController = null;
    }
    scope?.onDestroy(dispose);
    const read = (() => value());
    read.loading = () => loading();
    read.error = () => error();
    read.refresh = () => refreshTick.set(refreshTick() + 1);
    read.dispose = dispose;
    return read;
  }
  function assertType(value, validation, errorMessage = "Value does not match the type") {
    const issues = validateType(value, validation);
    if (issues.length) {
      const issueStrings = JSON.stringify(
        issues,
        (key, value2) => {
          if (typeof value2 === "function") {
            return value2.name;
          }
          return value2;
        },
        2
      );
      throw new OwlError(`${errorMessage}
${issueStrings}`);
    }
  }
  function createContext(issues, value, path, parent) {
    return {
      issueDepth: 0,
      path,
      value,
      get isValid() {
        return !issues.length;
      },
      addIssue(issue) {
        issues.push({
          received: this.value,
          path: this.path,
          ...issue
        });
      },
      mergeIssues(newIssues) {
        issues.push(...newIssues);
      },
      validate(type) {
        type(this);
        if (!this.isValid && parent) {
          parent.issueDepth = this.issueDepth + 1;
        }
      },
      withIssues(issues2) {
        return createContext(issues2, this.value, this.path, this);
      },
      withKey(key) {
        return createContext(issues, this.value[key], this.path.concat(key), this);
      }
    };
  }
  function validateType(value, validation) {
    const issues = [];
    validation(createContext(issues, value, []));
    return issues;
  }
  function anyType() {
    return function validateAny() {
    };
  }
  function booleanType() {
    return function validateBoolean(context) {
      if (typeof context.value !== "boolean") {
        context.addIssue({ message: "value is not a boolean" });
      }
    };
  }
  function numberType() {
    return function validateNumber(context) {
      if (typeof context.value !== "number") {
        context.addIssue({ message: "value is not a number" });
      }
    };
  }
  function stringType() {
    return function validateString(context) {
      if (typeof context.value !== "string" && !(context.value instanceof String)) {
        context.addIssue({ message: "value is not a string" });
      }
    };
  }
  function arrayType(elementType) {
    return function validateArray(context) {
      if (!Array.isArray(context.value)) {
        context.addIssue({ message: "value is not an array" });
        return;
      }
      if (!elementType) {
        return;
      }
      for (let index = 0; index < context.value.length; index++) {
        context.withKey(index).validate(elementType);
      }
    };
  }
  function constructorType(constructor) {
    return function validateConstructor(context) {
      if (!(typeof context.value === "function") || !(context.value === constructor || context.value.prototype instanceof constructor)) {
        context.addIssue({ message: `value is not '${constructor.name}' or an extension` });
      }
    };
  }
  function customValidator(type, validator, errorMessage = "value does not match custom validation") {
    return function validateCustom(context) {
      context.validate(type);
      if (!context.isValid) {
        return;
      }
      if (!validator(context.value)) {
        context.addIssue({ message: errorMessage });
      }
    };
  }
  function functionType(parameters = [], result = void 0) {
    return function validateFunction(context) {
      if (typeof context.value !== "function") {
        context.addIssue({ message: "value is not a function" });
      }
    };
  }
  function instanceType(constructor) {
    return function validateInstanceType(context) {
      if (!(context.value instanceof constructor)) {
        context.addIssue({ message: `value is not an instance of '${constructor.name}'` });
      }
    };
  }
  function intersection(types22) {
    return function validateIntersection(context) {
      for (const type of types22) {
        context.validate(type);
      }
    };
  }
  function literalType(literal) {
    return function validateLiteral(context) {
      if (context.value !== literal) {
        context.addIssue({
          message: `value is not equal to ${typeof literal === "string" ? `'${literal}'` : literal}`
        });
      }
    };
  }
  function literalSelection(literals) {
    return union(literals.map(literalType));
  }
  function validateObject(context, schema, isStrict) {
    if (typeof context.value !== "object" || Array.isArray(context.value) || context.value === null) {
      context.addIssue({ message: "value is not an object" });
      return;
    }
    if (!schema) {
      return;
    }
    const isShape = !Array.isArray(schema);
    let shape = schema;
    if (Array.isArray(schema)) {
      shape = {};
      for (const key of schema) {
        shape[key] = null;
      }
    }
    const missingKeys = [];
    for (const key in shape) {
      const property = key.endsWith("?") ? key.slice(0, -1) : key;
      if (context.value[property] === void 0) {
        if (!key.endsWith("?")) {
          missingKeys.push(property);
        }
        continue;
      }
      if (isShape) {
        context.withKey(property).validate(shape[key]);
      }
    }
    if (missingKeys.length) {
      context.addIssue({
        message: "object value has missing keys",
        missingKeys
      });
    }
    if (isStrict) {
      const unknownKeys = [];
      for (const key in context.value) {
        if (!(key in shape) && !(`${key}?` in shape)) {
          unknownKeys.push(key);
        }
      }
      if (unknownKeys.length) {
        context.addIssue({
          message: "object value has unknown keys",
          unknownKeys
        });
      }
    }
  }
  function objectType(schema = {}) {
    return function validateLooseObject(context) {
      validateObject(context, schema, false);
    };
  }
  function strictObjectType(schema) {
    return function validateStrictObject(context) {
      validateObject(context, schema, true);
    };
  }
  function promiseType(type) {
    return function validatePromise(context) {
      if (!(context.value instanceof Promise)) {
        context.addIssue({ message: "value is not a promise" });
      }
    };
  }
  function recordType(valueType) {
    return function validateRecord(context) {
      if (typeof context.value !== "object" || Array.isArray(context.value) || context.value === null) {
        context.addIssue({ message: "value is not an object" });
        return;
      }
      if (!valueType) {
        return;
      }
      for (const key in context.value) {
        context.withKey(key).validate(valueType);
      }
    };
  }
  function tuple(types22) {
    return function validateTuple(context) {
      if (!Array.isArray(context.value)) {
        context.addIssue({ message: "value is not an array" });
        return;
      }
      if (context.value.length !== types22.length) {
        context.addIssue({ message: "tuple value does not have the correct length" });
        return;
      }
      for (let index = 0; index < types22.length; index++) {
        context.withKey(index).validate(types22[index]);
      }
    };
  }
  function union(types22) {
    return function validateUnion(context) {
      let firstIssueIndex = 0;
      const subIssues = [];
      for (const type of types22) {
        const subContext = context.withIssues(subIssues);
        subContext.validate(type);
        if (subIssues.length === firstIssueIndex || subContext.issueDepth > 0) {
          context.mergeIssues(subIssues.slice(firstIssueIndex));
          return;
        }
        firstIssueIndex = subIssues.length;
      }
      context.addIssue({
        message: "value does not match union type",
        subIssues
      });
    };
  }
  function reactiveValueType(type) {
    return function validateReactiveValue(context) {
      if (typeof context.value !== "function" || !context.value[atomSymbol]) {
        context.addIssue({ message: "value is not a reactive value" });
      }
    };
  }
  function ref(type) {
    return union([literalType(null), instanceType(type)]);
  }
  var types = {
    and: intersection,
    any: anyType,
    array: arrayType,
    boolean: booleanType,
    constructor: constructorType,
    customValidator,
    function: functionType,
    instanceOf: instanceType,
    literal: literalType,
    number: numberType,
    object: objectType,
    or: union,
    promise: promiseType,
    record: recordType,
    ref,
    selection: literalSelection,
    signal: reactiveValueType,
    strictObject: strictObjectType,
    string: stringType,
    tuple
  };
  var Registry = class {
    _map = signal.Object(/* @__PURE__ */ Object.create(null));
    _name;
    _validation;
    constructor(options = {}) {
      this._name = options.name || "registry";
      this._validation = options.validation;
    }
    entries = computed(() => {
      const entries = Object.entries(this._map()).sort((el1, el2) => el1[1][0] - el2[1][0]).map(([str, elem]) => [str, elem[1]]);
      return entries;
    });
    items = computed(() => this.entries().map((e) => e[1]));
    addById(item, options = {}) {
      if (!item.id) {
        throw new OwlError(`Item should have an id key (registry '${this._name}')`);
      }
      return this.add(item.id, item, options);
    }
    add(key, value, options = {}) {
      if (!options.force && key in this._map()) {
        throw new OwlError(
          `Key "${key}" is already registered (registry '${this._name}'). Use { force: true } to overwrite.`
        );
      }
      if (this._validation) {
        const info = this._name ? ` (registry '${this._name}', key: '${key}')` : ` (key: '${key}')`;
        assertType(value, this._validation, `Registry entry does not match the type${info}`);
      }
      this._map()[key] = [options.sequence ?? 50, value];
      return this;
    }
    get(key, defaultValue) {
      const hasKey = key in this._map();
      if (!hasKey && arguments.length < 2) {
        throw new OwlError(`Cannot find key "${key}" (registry '${this._name}')`);
      }
      return hasKey ? this._map()[key][1] : defaultValue;
    }
    delete(key) {
      delete this._map()[key];
    }
    has(key) {
      return key in this._map();
    }
    use(key, value, options = {}) {
      const scope = useScope();
      this.add(key, value, options);
      scope.onDestroy(() => {
        if (this._map()[key]?.[1] === value) {
          this.delete(key);
        }
      });
      return this;
    }
    useById(item, options = {}) {
      if (!item.id) {
        throw new OwlError(`Item should have an id key (registry '${this._name}')`);
      }
      return this.use(item.id, item, options);
    }
  };
  var Resource = class {
    _items = signal.Array([]);
    _name;
    _validation;
    constructor(options = {}) {
      this._name = options.name;
      this._validation = options.validation;
    }
    items = computed(() => {
      return this._items().sort((el1, el2) => el1[0] - el2[0]).map((elem) => elem[1]);
    });
    add(item, options = {}) {
      if (this._validation) {
        const info = this._name ? ` (resource '${this._name}')` : "";
        assertType(item, this._validation, `Resource item does not match the type${info}`);
      }
      this._items().push([options.sequence ?? 50, item]);
      return this;
    }
    delete(item) {
      const items = this._items().filter(([seq, val]) => val !== item);
      this._items.set(items);
      return this;
    }
    has(item) {
      return this._items().some(([s, value]) => value === item);
    }
    use(item, options = {}) {
      const scope = useScope();
      this.add(item, options);
      scope.onDestroy(() => this.delete(item));
      return this;
    }
  };
  var Plugin = class {
    static _shadowId;
    static get id() {
      return this._shadowId ?? this.name;
    }
    static set id(shadowId) {
      this._shadowId = shadowId;
    }
    __owl__;
    constructor(manager) {
      this.__owl__ = manager;
    }
    setup() {
    }
  };
  var PluginManager = class extends Scope {
    config;
    plugins;
    // Resolves once all pending plugin willStart callbacks have settled. The
    // scope transitions to MOUNTED as the last step of this chain. Consumers
    // (App.mount, providePlugins) await this before treating the manager as
    // ready. `willStart` itself is inherited from Scope.
    ready = Promise.resolve();
    constructor(app, options = {}) {
      super(app);
      this.config = options.config ?? {};
      if (options.parent) {
        const parent = options.parent;
        parent.onDestroy(() => this.destroy());
        this.plugins = Object.create(parent.plugins);
      } else {
        this.plugins = {};
      }
    }
    destroy() {
      this.finalize((e) => console.error(e));
    }
    getPluginById(id) {
      return this.plugins[id] || null;
    }
    getPlugin(pluginConstructor) {
      return this.getPluginById(pluginConstructor.id);
    }
    startPlugin(pluginConstructor) {
      if (!pluginConstructor.id) {
        throw new OwlError(`Plugin "${pluginConstructor.name}" has no id`);
      }
      if (this.plugins.hasOwnProperty(pluginConstructor.id)) {
        const existingPluginType = this.getPluginById(pluginConstructor.id).constructor;
        if (existingPluginType !== pluginConstructor) {
          throw new OwlError(
            `Trying to start a plugin with the same id as an other plugin (id: '${pluginConstructor.id}', existing plugin: '${existingPluginType.name}', starting plugin: '${pluginConstructor.name}')`
          );
        }
        return null;
      }
      const plugin2 = new pluginConstructor(this);
      this.plugins[pluginConstructor.id] = plugin2;
      plugin2.setup();
      return plugin2;
    }
    startPlugins(pluginConstructors) {
      scopeStack.push(this);
      try {
        for (const pluginConstructor of pluginConstructors) {
          this.startPlugin(pluginConstructor);
        }
      } finally {
        scopeStack.pop();
      }
      const pending = this.willStart.splice(0);
      if (pending.length) {
        this.ready = Promise.all(pending.map((fn) => fn())).then(() => {
          if (this.status < STATUS.MOUNTED) {
            this.status = STATUS.MOUNTED;
          }
        });
      } else if (this.status < STATUS.MOUNTED) {
        this.status = STATUS.MOUNTED;
      }
    }
  };
  function startPlugins(manager, plugins) {
    if (Array.isArray(plugins)) {
      manager.startPlugins(plugins);
    } else {
      manager.onDestroy(
        effect(() => {
          const pluginItems = plugins.items();
          untrack(() => manager.startPlugins(pluginItems));
        })
      );
    }
  }

  // ../owl-runtime/dist/owl-runtime.es.js
  var version = "3.0.0-alpha.31";
  var fibersInError = /* @__PURE__ */ new WeakMap();
  var nodeErrorHandlers = /* @__PURE__ */ new WeakMap();
  function invokeErrorHandlers(node, error, finalize, markFibers) {
    while (node) {
      if (markFibers && node.fiber) {
        fibersInError.set(node.fiber, error);
      }
      const handlers = nodeErrorHandlers.get(node);
      if (handlers) {
        for (let i = handlers.length - 1; i >= 0; i--) {
          try {
            handlers[i](error, finalize);
            return { handled: true, error };
          } catch (e) {
            error = e;
          }
        }
      }
      node = node.parent;
    }
    return { handled: false, error };
  }
  function forwardErrorToParent(boundary) {
    return (error, finalize) => {
      if (boundary.app.destroyed) {
        throw error;
      }
      const { handled } = invokeErrorHandlers(boundary, error, finalize, false);
      if (!handled) {
        boundary.app._handleError(finalize());
      }
    };
  }
  function handleError(params) {
    let { error } = params;
    let node = "node" in params ? params.node : params.fiber.node;
    const fiber = "fiber" in params ? params.fiber : node.fiber;
    const app = node.app;
    if (app.destroyed) {
      throw error;
    }
    if (fiber) {
      let current = fiber;
      do {
        current.node.fiber = current;
        fibersInError.set(current, error);
        current = current.parent;
      } while (current);
      fibersInError.set(fiber.root, error);
    }
    const finalize = () => {
      try {
        app.destroy();
      } catch (e) {
      }
      return error;
    };
    const result = invokeErrorHandlers(node, error, finalize, true);
    if (!result.handled) {
      error = result.error;
      app._handleError(finalize());
    }
  }
  function filterOutModifiersFromData(dataList) {
    dataList = dataList.slice();
    const modifiers = [];
    let elm;
    while ((elm = dataList[0]) && typeof elm === "string") {
      modifiers.push(dataList.shift());
    }
    return { modifiers, data: dataList };
  }
  var config = {
    // whether or not blockdom should normalize DOM whenever a block is created.
    // Normalizing dom mean removing empty text nodes (or containing only spaces)
    shouldNormalizeDom: true,
    // this is the main event handler. Every event handler registered with blockdom
    // will go through this function, giving it the data registered in the block
    // and the event
    mainEventHandler: (data, ev, currentTarget) => {
      if (typeof data === "function") {
        data(ev);
      } else if (Array.isArray(data)) {
        data = filterOutModifiersFromData(data).data;
        data[0](data[1], ev);
      }
      return false;
    }
  };
  var txt = document.createTextNode("");
  var VToggler = class {
    key;
    child;
    parentEl;
    constructor(key, child) {
      this.key = key;
      this.child = child;
    }
    mount(parent, afterNode) {
      this.parentEl = parent;
      this.child.mount(parent, afterNode);
    }
    moveBeforeDOMNode(node, parent) {
      this.child.moveBeforeDOMNode(node, parent);
    }
    moveBeforeVNode(other, afterNode) {
      this.moveBeforeDOMNode(other && other.firstNode() || afterNode);
    }
    patch(other, withBeforeRemove) {
      if (this === other) {
        return;
      }
      let child1 = this.child;
      let child2 = other.child;
      if (this.key === other.key) {
        child1.patch(child2, withBeforeRemove);
      } else {
        const firstNode = child1.firstNode();
        firstNode.parentElement.insertBefore(txt, firstNode);
        if (withBeforeRemove) {
          child1.beforeRemove();
        }
        child1.remove();
        child2.mount(this.parentEl, txt);
        this.child = child2;
        this.key = other.key;
      }
    }
    beforeRemove() {
      this.child.beforeRemove();
    }
    remove() {
      this.child.remove();
    }
    firstNode() {
      return this.child.firstNode();
    }
    toString() {
      return this.child.toString();
    }
  };
  function toggler(key, child) {
    return new VToggler(key, child);
  }
  var elemSetAttribute;
  var removeAttribute;
  var tokenListAdd;
  var tokenListRemove;
  if (typeof Element !== "undefined") {
    ({ setAttribute: elemSetAttribute, removeAttribute } = Element.prototype);
    const tokenList = DOMTokenList.prototype;
    tokenListAdd = tokenList.add;
    tokenListRemove = tokenList.remove;
  }
  var isArray = Array.isArray;
  var { split, trim } = String.prototype;
  var wordRegexp = /\s+/;
  function setAttribute(key, value) {
    switch (value) {
      case false:
      case null:
      case void 0:
        removeAttribute.call(this, key);
        break;
      case true:
        elemSetAttribute.call(this, key, "");
        break;
      default:
        elemSetAttribute.call(this, key, value);
    }
  }
  function createAttrUpdater(attr) {
    return function(value) {
      setAttribute.call(this, attr, value);
    };
  }
  function attrsSetter(attrs) {
    if (isArray(attrs)) {
      if (attrs[0] === "class") {
        setClass.call(this, attrs[1]);
      } else if (attrs[0] === "style") {
        setStyle.call(this, attrs[1]);
      } else {
        setAttribute.call(this, attrs[0], attrs[1]);
      }
    } else {
      for (let k in attrs) {
        if (k === "class") {
          setClass.call(this, attrs[k]);
        } else if (k === "style") {
          setStyle.call(this, attrs[k]);
        } else {
          setAttribute.call(this, k, attrs[k]);
        }
      }
    }
  }
  function attrsUpdater(attrs, oldAttrs) {
    if (isArray(attrs)) {
      const name = attrs[0];
      const val = attrs[1];
      if (name === oldAttrs[0]) {
        if (val === oldAttrs[1]) {
          return;
        }
        if (name === "class") {
          updateClass.call(this, val, oldAttrs[1]);
        } else if (name === "style") {
          updateStyle.call(this, val, oldAttrs[1]);
        } else {
          setAttribute.call(this, name, val);
        }
      } else {
        removeAttribute.call(this, oldAttrs[0]);
        setAttribute.call(this, name, val);
      }
    } else {
      for (let k in oldAttrs) {
        if (!(k in attrs)) {
          if (k === "class") {
            updateClass.call(this, "", oldAttrs[k]);
          } else if (k === "style") {
            updateStyle.call(this, "", oldAttrs[k]);
          } else {
            removeAttribute.call(this, k);
          }
        }
      }
      for (let k in attrs) {
        const val = attrs[k];
        if (val !== oldAttrs[k]) {
          if (k === "class") {
            updateClass.call(this, val, oldAttrs[k]);
          } else if (k === "style") {
            updateStyle.call(this, val, oldAttrs[k]);
          } else {
            setAttribute.call(this, k, val);
          }
        }
      }
    }
  }
  function toClassObj(expr) {
    const result = {};
    switch (typeof expr) {
      case "string":
        const str = trim.call(expr);
        if (!str) {
          return {};
        }
        let words = split.call(str, wordRegexp);
        for (let i = 0, l = words.length; i < l; i++) {
          result[words[i]] = true;
        }
        return result;
      case "object":
        for (let key in expr) {
          const value = expr[key];
          if (value) {
            key = trim.call(key);
            if (!key) {
              continue;
            }
            const words2 = split.call(key, wordRegexp);
            for (let word of words2) {
              result[word] = value;
            }
          }
        }
        return result;
      case "undefined":
        return {};
      case "number":
        return { [expr]: true };
      default:
        return { [expr]: true };
    }
  }
  var CSS_PROP_CACHE = {};
  function toKebabCase(prop2) {
    if (prop2 in CSS_PROP_CACHE) {
      return CSS_PROP_CACHE[prop2];
    }
    const result = prop2.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
    CSS_PROP_CACHE[prop2] = result;
    return result;
  }
  var IMPORTANT_RE = /\s*!\s*important\s*$/i;
  function setStyleProp(style, prop2, value) {
    if (IMPORTANT_RE.test(value)) {
      style.setProperty(prop2, value.replace(IMPORTANT_RE, ""), "important");
    } else {
      style.setProperty(prop2, value);
    }
  }
  function toStyleObj(expr) {
    const result = {};
    switch (typeof expr) {
      case "string": {
        const str = expr;
        const len = str.length;
        let i = 0;
        while (i < len) {
          const start = i;
          let depth = 0;
          let quote = 0;
          while (i < len) {
            const c = str.charCodeAt(i);
            if (quote) {
              if (c === 92) {
                i += 2;
                continue;
              }
              if (c === quote) {
                quote = 0;
              }
            } else if (c === 34 || c === 39) {
              quote = c;
            } else if (c === 40) {
              depth++;
            } else if (c === 41) {
              if (depth > 0) depth--;
            } else if (c === 59 && depth === 0) {
              break;
            }
            i++;
          }
          const part = trim.call(str.slice(start, i));
          i++;
          if (!part) {
            continue;
          }
          const colonIdx = part.indexOf(":");
          if (colonIdx === -1) {
            continue;
          }
          const prop2 = trim.call(part.slice(0, colonIdx));
          const value = trim.call(part.slice(colonIdx + 1));
          if (prop2 && value && value !== "undefined") {
            result[prop2] = value;
          }
        }
        return result;
      }
      case "object":
        for (let prop2 in expr) {
          const value = expr[prop2];
          if (value || value === 0) {
            result[toKebabCase(prop2)] = String(value);
          }
        }
        return result;
      default:
        return {};
    }
  }
  function setClass(val) {
    val = val === "" ? {} : toClassObj(val);
    for (let k in val) {
      tokenListAdd.call(this.classList, k);
    }
  }
  function updateClass(val, oldVal) {
    oldVal = oldVal === "" ? {} : toClassObj(oldVal);
    val = val === "" ? {} : toClassObj(val);
    for (let k in oldVal) {
      if (!(k in val)) {
        tokenListRemove.call(this.classList, k);
      }
    }
    for (let k in val) {
      if (val[k] !== oldVal[k]) {
        tokenListAdd.call(this.classList, k);
      }
    }
  }
  function setStyle(val) {
    val = val === "" ? {} : toStyleObj(val);
    const style = this.style;
    for (let prop2 in val) {
      setStyleProp(style, prop2, val[prop2]);
    }
  }
  function updateStyle(val, oldVal) {
    oldVal = oldVal === "" ? {} : toStyleObj(oldVal);
    val = val === "" ? {} : toStyleObj(val);
    const style = this.style;
    for (let prop2 in oldVal) {
      if (!(prop2 in val)) {
        style.removeProperty(prop2);
      }
    }
    for (let prop2 in val) {
      if (val[prop2] !== oldVal[prop2]) {
        setStyleProp(style, prop2, val[prop2]);
      }
    }
    if (!style.cssText) {
      removeAttribute.call(this, "style");
    }
  }
  function inOwnerDocument(el) {
    if (!el) {
      return false;
    }
    if (el.ownerDocument.contains(el)) {
      return true;
    }
    const rootNode = el.getRootNode();
    return rootNode instanceof ShadowRoot && el.ownerDocument.contains(rootNode.host);
  }
  function isAttachedToDocument(element, documentElement) {
    let current = element;
    const shadowRoot = documentElement.defaultView.ShadowRoot;
    while (current) {
      if (current === documentElement) {
        return true;
      }
      if (current.parentNode) {
        current = current.parentNode;
      } else if (current instanceof shadowRoot && current.host) {
        current = current.host;
      } else {
        return false;
      }
    }
    return false;
  }
  function validateTarget(target) {
    const document2 = target && target.ownerDocument;
    if (document2) {
      if (!document2.defaultView) {
        throw new OwlError(
          "Cannot mount a component: the target document is not attached to a window (defaultView is missing)"
        );
      }
      const HTMLElement2 = document2.defaultView.HTMLElement;
      if (target instanceof HTMLElement2 || target instanceof ShadowRoot) {
        if (!isAttachedToDocument(target, document2)) {
          throw new OwlError("Cannot mount a component on a detached dom node");
        }
        return;
      }
    }
    throw new OwlError("Cannot mount component: the target is not a valid DOM element");
  }
  var EventBus = class extends EventTarget {
    trigger(name, payload) {
      this.dispatchEvent(new CustomEvent(name, { detail: payload }));
    }
  };
  function whenReady(fn) {
    return new Promise(function(resolve) {
      if (document.readyState !== "loading") {
        resolve(true);
      } else {
        document.addEventListener("DOMContentLoaded", resolve, false);
      }
    }).then(fn || function() {
    });
  }
  var Markup = class extends String {
  };
  function htmlEscape(str) {
    if (str instanceof Markup) {
      return str;
    }
    if (str === void 0) {
      return markup("");
    }
    if (typeof str === "number") {
      return markup(String(str));
    }
    [
      ["&", "&amp;"],
      ["<", "&lt;"],
      [">", "&gt;"],
      ["'", "&#x27;"],
      ['"', "&quot;"],
      ["`", "&#x60;"]
    ].forEach((pairs) => {
      str = String(str).replace(new RegExp(pairs[0], "g"), pairs[1]);
    });
    return markup(str);
  }
  function markup(valueOrStrings, ...placeholders) {
    if (!Array.isArray(valueOrStrings)) {
      return new Markup(valueOrStrings);
    }
    const strings = valueOrStrings;
    let acc = "";
    let i = 0;
    for (; i < placeholders.length; ++i) {
      acc += strings[i] + htmlEscape(placeholders[i]);
    }
    acc += strings[i];
    return new Markup(acc);
  }
  function createEventHandler(rawEvent) {
    const eventName = rawEvent.split(".")[0];
    const capture = rawEvent.includes(".capture");
    const passive = rawEvent.includes(".passive");
    if (rawEvent.includes(".synthetic")) {
      return createSyntheticHandler(eventName, capture, passive);
    } else {
      return createElementHandler(eventName, capture, passive);
    }
  }
  var nextNativeEventId = 1;
  function createElementHandler(evName, capture = false, passive = false) {
    let eventKey = `__event__${evName}_${nextNativeEventId++}`;
    if (capture) {
      eventKey = `${eventKey}_capture`;
    }
    function listener(ev) {
      const currentTarget = ev.currentTarget;
      if (!currentTarget || !inOwnerDocument(currentTarget)) return;
      const data = currentTarget[eventKey];
      if (!data) return;
      config.mainEventHandler(data, ev, currentTarget);
    }
    const options = { capture, passive };
    function setup(data) {
      this[eventKey] = data;
      this.addEventListener(evName, listener, options);
    }
    function remove2() {
      delete this[eventKey];
      this.removeEventListener(evName, listener, options);
    }
    function update(data) {
      this[eventKey] = data;
    }
    return { setup, update, remove: remove2 };
  }
  var nextSyntheticEventId = 1;
  function createSyntheticHandler(evName, capture = false, passive = false) {
    let eventKey = `__event__synthetic_${evName}`;
    if (capture) {
      eventKey = `${eventKey}_capture`;
    }
    setupSyntheticEvent(evName, eventKey, capture, passive);
    const currentId = nextSyntheticEventId++;
    function setup(data) {
      const _data = this[eventKey] || {};
      _data[currentId] = data;
      this[eventKey] = _data;
    }
    function remove2() {
      delete this[eventKey];
    }
    return { setup, update: setup, remove: remove2 };
  }
  function nativeToSyntheticEvent(eventKey, event) {
    let dom = event.target;
    while (dom !== null) {
      const _data = dom[eventKey];
      if (_data) {
        for (const data of Object.values(_data)) {
          const stopped = config.mainEventHandler(data, event, dom);
          if (stopped) return;
        }
      }
      dom = dom.parentNode;
    }
  }
  var CONFIGURED_SYNTHETIC_EVENTS = {};
  function setupSyntheticEvent(evName, eventKey, capture = false, passive = false) {
    if (CONFIGURED_SYNTHETIC_EVENTS[eventKey]) {
      return;
    }
    document.addEventListener(evName, (event) => nativeToSyntheticEvent(eventKey, event), {
      capture,
      passive
    });
    CONFIGURED_SYNTHETIC_EVENTS[eventKey] = true;
  }
  var getDescriptor = (o, p) => Object.getOwnPropertyDescriptor(o, p);
  var nodeInsertBefore;
  var nodeSetTextContent;
  var nodeRemoveChild;
  if (typeof Node !== "undefined") {
    const nodeProto2 = Node.prototype;
    nodeInsertBefore = nodeProto2.insertBefore;
    nodeSetTextContent = getDescriptor(nodeProto2, "textContent").set;
    nodeRemoveChild = nodeProto2.removeChild;
  }
  var VMulti = class {
    children;
    anchors;
    parentEl;
    isOnlyChild;
    constructor(children) {
      this.children = children;
    }
    mount(parent, afterNode) {
      const children = this.children;
      const l = children.length;
      const anchors = new Array(l);
      for (let i = 0; i < l; i++) {
        let child = children[i];
        if (child) {
          child.mount(parent, afterNode);
        } else {
          const childAnchor = document.createTextNode("");
          anchors[i] = childAnchor;
          nodeInsertBefore.call(parent, childAnchor, afterNode);
        }
      }
      this.anchors = anchors;
      this.parentEl = parent;
    }
    moveBeforeDOMNode(node, parent = this.parentEl) {
      this.parentEl = parent;
      const children = this.children;
      const anchors = this.anchors;
      for (let i = 0, l = children.length; i < l; i++) {
        let child = children[i];
        if (child) {
          child.moveBeforeDOMNode(node, parent);
        } else {
          const anchor = anchors[i];
          nodeInsertBefore.call(parent, anchor, node);
        }
      }
    }
    moveBeforeVNode(other, afterNode) {
      if (other) {
        const next = other.children[0];
        afterNode = (next ? next.firstNode() : other.anchors[0]) || null;
      }
      const children = this.children;
      const parent = this.parentEl;
      const anchors = this.anchors;
      for (let i = 0, l = children.length; i < l; i++) {
        let child = children[i];
        if (child) {
          child.moveBeforeVNode(null, afterNode);
        } else {
          const anchor = anchors[i];
          nodeInsertBefore.call(parent, anchor, afterNode);
        }
      }
    }
    patch(other, withBeforeRemove) {
      if (this === other) {
        return;
      }
      const children1 = this.children;
      const children2 = other.children;
      const anchors = this.anchors;
      const parentEl = this.parentEl;
      for (let i = 0, l = children1.length; i < l; i++) {
        const vn1 = children1[i];
        const vn2 = children2[i];
        if (vn1) {
          if (vn2) {
            vn1.patch(vn2, withBeforeRemove);
          } else {
            const afterNode = vn1.firstNode();
            const anchor = document.createTextNode("");
            anchors[i] = anchor;
            nodeInsertBefore.call(parentEl, anchor, afterNode);
            if (withBeforeRemove) {
              vn1.beforeRemove();
            }
            vn1.remove();
            children1[i] = void 0;
          }
        } else if (vn2) {
          children1[i] = vn2;
          const anchor = anchors[i];
          vn2.mount(parentEl, anchor);
          nodeRemoveChild.call(parentEl, anchor);
        }
      }
    }
    beforeRemove() {
      const children = this.children;
      for (let i = 0, l = children.length; i < l; i++) {
        const child = children[i];
        if (child) {
          child.beforeRemove();
        }
      }
    }
    remove() {
      const parentEl = this.parentEl;
      if (this.isOnlyChild) {
        nodeSetTextContent.call(parentEl, "");
      } else {
        const children = this.children;
        const anchors = this.anchors;
        for (let i = 0, l = children.length; i < l; i++) {
          const child = children[i];
          if (child) {
            child.remove();
          } else {
            nodeRemoveChild.call(parentEl, anchors[i]);
          }
        }
      }
    }
    firstNode() {
      const child = this.children[0];
      return child ? child.firstNode() : this.anchors[0];
    }
    toString() {
      return this.children.map((c) => c ? c.toString() : "").join("");
    }
  };
  function multi(children) {
    return new VMulti(children);
  }
  var getDescriptor2 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
  var nodeInsertBefore2;
  var characterDataSetData;
  var nodeRemoveChild2;
  if (typeof Node !== "undefined") {
    const nodeProto2 = Node.prototype;
    nodeInsertBefore2 = nodeProto2.insertBefore;
    nodeRemoveChild2 = nodeProto2.removeChild;
    characterDataSetData = getDescriptor2(CharacterData.prototype, "data").set;
  }
  var VText = class {
    text;
    parentEl;
    el;
    constructor(text2) {
      this.text = text2;
    }
    mount(parent, afterNode) {
      this.parentEl = parent;
      const node = document.createTextNode(toText(this.text));
      nodeInsertBefore2.call(parent, node, afterNode);
      this.el = node;
    }
    moveBeforeDOMNode(node, parent = this.parentEl) {
      this.parentEl = parent;
      nodeInsertBefore2.call(parent, this.el, node);
    }
    moveBeforeVNode(other, afterNode) {
      nodeInsertBefore2.call(this.parentEl, this.el, other ? other.el : afterNode);
    }
    beforeRemove() {
    }
    remove() {
      nodeRemoveChild2.call(this.parentEl, this.el);
    }
    firstNode() {
      return this.el;
    }
    patch(other) {
      const text2 = other.text;
      if (this.text !== text2) {
        characterDataSetData.call(this.el, toText(text2));
        this.text = text2;
      }
    }
    toString() {
      return this.text;
    }
  };
  function text(str) {
    return new VText(str);
  }
  function toText(value) {
    switch (typeof value) {
      case "string":
        return value;
      case "number":
        return String(value);
      case "boolean":
        return value ? "true" : "false";
      default:
        return value || "";
    }
  }
  var getDescriptor3 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
  var nodeProto;
  var elementProto;
  var characterDataSetData2;
  var nodeGetFirstChild;
  var nodeGetNextSibling;
  if (typeof Node !== "undefined") {
    nodeProto = Node.prototype;
    elementProto = Element.prototype;
    characterDataSetData2 = getDescriptor3(CharacterData.prototype, "data").set;
    nodeGetFirstChild = getDescriptor3(nodeProto, "firstChild").get;
    nodeGetNextSibling = getDescriptor3(nodeProto, "nextSibling").get;
  }
  var NO_OP = () => {
  };
  function makePropSetter(name) {
    return function setProp(value) {
      this[name] = value === 0 ? 0 : value ? value.valueOf() : "";
    };
  }
  var cache = {};
  function createBlock(str) {
    if (str in cache) {
      return cache[str];
    }
    const doc = new DOMParser().parseFromString(`<t>${str}</t>`, "text/xml");
    const node = doc.firstChild.firstChild;
    if (config.shouldNormalizeDom) {
      normalizeNode(node);
    }
    const tree = buildTree(node);
    const context = buildContext(tree);
    const template = tree.el;
    const Block = buildBlock(template, context);
    cache[str] = Block;
    return Block;
  }
  function normalizeNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (!/\S/.test(node.textContent)) {
        node.remove();
        return;
      }
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
      if (node.tagName === "pre") {
        return;
      }
    }
    for (let i = node.childNodes.length - 1; i >= 0; --i) {
      normalizeNode(node.childNodes.item(i));
    }
  }
  function buildTree(node, parent = null, domParentTree = null) {
    switch (node.nodeType) {
      case Node.ELEMENT_NODE: {
        let currentNS = domParentTree && domParentTree.currentNS;
        const tagName = node.tagName;
        let el = void 0;
        const info = [];
        if (tagName.startsWith("block-text-")) {
          const index = parseInt(tagName.slice(11), 10);
          info.push({ type: "text", idx: index });
          el = document.createTextNode("");
        }
        if (tagName.startsWith("block-child-")) {
          if (!domParentTree.isRef) {
            addRef(domParentTree);
          }
          const index = parseInt(tagName.slice(12), 10);
          info.push({ type: "child", idx: index });
          el = document.createTextNode("");
        }
        currentNS ||= node.namespaceURI;
        if (!el) {
          el = currentNS ? document.createElementNS(currentNS, tagName) : document.createElement(tagName);
        }
        if (el instanceof Element) {
          if (!domParentTree) {
            const fragment = document.createElement("template").content;
            fragment.appendChild(el);
          }
          const attrs = node.attributes;
          for (let i = 0; i < attrs.length; i++) {
            const attrName = attrs[i].name;
            const attrValue = attrs[i].value;
            if (attrName.startsWith("block-handler-")) {
              const idx = parseInt(attrName.slice(14), 10);
              info.push({
                type: "handler",
                idx,
                event: attrValue
              });
            } else if (attrName.startsWith("block-attribute-")) {
              const idx = parseInt(attrName.slice(16), 10);
              info.push({
                type: "attribute",
                idx,
                name: attrValue,
                tag: tagName
              });
            } else if (attrName.startsWith("block-property-")) {
              const idx = parseInt(attrName.slice(15), 10);
              info.push({
                type: "property",
                idx,
                name: attrValue,
                tag: tagName
              });
            } else if (attrName === "block-attributes") {
              info.push({
                type: "attributes",
                idx: parseInt(attrValue, 10)
              });
            } else if (attrName === "block-ref") {
              info.push({
                type: "ref",
                idx: parseInt(attrValue, 10)
              });
            } else {
              el.setAttribute(attrs[i].name, attrValue);
            }
          }
        }
        const tree = {
          parent,
          firstChild: null,
          nextSibling: null,
          el,
          info,
          refN: 0,
          currentNS
        };
        if (node.firstChild) {
          const childNode = node.childNodes[0];
          if (node.childNodes.length === 1 && childNode.nodeType === Node.ELEMENT_NODE && childNode.tagName.startsWith("block-child-")) {
            const tagName2 = childNode.tagName;
            const index = parseInt(tagName2.slice(12), 10);
            info.push({ idx: index, type: "child", isOnlyChild: true });
          } else {
            tree.firstChild = buildTree(node.firstChild, tree, tree);
            el.appendChild(tree.firstChild.el);
            let curNode = node.firstChild;
            let curTree = tree.firstChild;
            while (curNode = curNode.nextSibling) {
              curTree.nextSibling = buildTree(curNode, curTree, tree);
              el.appendChild(curTree.nextSibling.el);
              curTree = curTree.nextSibling;
            }
          }
        }
        if (tree.info.length) {
          addRef(tree);
        }
        return tree;
      }
      case Node.TEXT_NODE: {
        return {
          parent,
          firstChild: null,
          nextSibling: null,
          el: document.createTextNode(node.textContent),
          info: [],
          refN: 0,
          currentNS: null
        };
      }
    }
    throw new OwlError("boom");
  }
  function addRef(tree) {
    tree.isRef = true;
    do {
      tree.refN++;
    } while (tree = tree.parent);
  }
  function parentTree(tree) {
    let parent = tree.parent;
    while (parent && parent.nextSibling === tree) {
      tree = parent;
      parent = parent.parent;
    }
    return parent;
  }
  function buildContext(tree, ctx, fromIdx) {
    if (!ctx) {
      const children = new Array(tree.info.filter((v) => v.type === "child").length);
      ctx = { collectors: [], locations: [], children, cbRefs: [], refN: tree.refN };
      fromIdx = 0;
    }
    if (tree.refN) {
      const initialIdx = fromIdx;
      const isRef = tree.isRef;
      const firstChild = tree.firstChild ? tree.firstChild.refN : 0;
      const nextSibling = tree.nextSibling ? tree.nextSibling.refN : 0;
      if (isRef) {
        for (let info of tree.info) {
          info.refIdx = initialIdx;
        }
        tree.refIdx = initialIdx;
        updateCtx(ctx, tree);
        fromIdx++;
      }
      if (nextSibling) {
        const idx = fromIdx + firstChild;
        ctx.collectors.push({ idx, prevIdx: initialIdx, getVal: nodeGetNextSibling });
        buildContext(tree.nextSibling, ctx, idx);
      }
      if (firstChild) {
        ctx.collectors.push({ idx: fromIdx, prevIdx: initialIdx, getVal: nodeGetFirstChild });
        buildContext(tree.firstChild, ctx, fromIdx);
      }
    }
    return ctx;
  }
  function updateCtx(ctx, tree) {
    for (let info of tree.info) {
      switch (info.type) {
        case "text":
          ctx.locations.push({
            idx: info.idx,
            refIdx: info.refIdx,
            setData: setText,
            updateData: setText
          });
          break;
        case "child":
          if (info.isOnlyChild) {
            ctx.children[info.idx] = {
              parentRefIdx: info.refIdx,
              isOnlyChild: true
            };
          } else {
            ctx.children[info.idx] = {
              parentRefIdx: parentTree(tree).refIdx,
              afterRefIdx: info.refIdx
            };
          }
          break;
        case "property": {
          const refIdx = info.refIdx;
          const setProp = makePropSetter(info.name);
          ctx.locations.push({
            idx: info.idx,
            refIdx,
            setData: setProp,
            updateData: setProp
          });
          break;
        }
        case "attribute": {
          const refIdx = info.refIdx;
          let updater;
          let setter;
          if (info.name === "class") {
            setter = setClass;
            updater = updateClass;
          } else if (info.name === "style") {
            setter = setStyle;
            updater = updateStyle;
          } else {
            setter = createAttrUpdater(info.name);
            updater = setter;
          }
          ctx.locations.push({
            idx: info.idx,
            refIdx,
            setData: setter,
            updateData: updater
          });
          break;
        }
        case "attributes":
          ctx.locations.push({
            idx: info.idx,
            refIdx: info.refIdx,
            setData: attrsSetter,
            updateData: attrsUpdater
          });
          break;
        case "handler": {
          const { setup, update } = createEventHandler(info.event);
          ctx.locations.push({
            idx: info.idx,
            refIdx: info.refIdx,
            setData: setup,
            updateData: update
          });
          break;
        }
        case "ref": {
          ctx.locations.push({
            idx: info.idx,
            refIdx: info.refIdx,
            setData: NO_OP,
            updateData: NO_OP
          });
          ctx.cbRefs.push(info.idx);
          break;
        }
      }
    }
  }
  function buildBlock(template, ctx) {
    let B = createBlockClass(template, ctx);
    if (ctx.children.length) {
      B = class extends B {
        children;
        constructor(data, children) {
          super(data);
          this.children = children;
        }
      };
      B.prototype.beforeRemove = VMulti.prototype.beforeRemove;
      return (data, children = []) => new B(data, children);
    }
    return (data) => new B(data);
  }
  function createBlockClass(template, ctx) {
    const { refN, collectors, children, locations, cbRefs } = ctx;
    locations.sort((a, b) => a.idx - b.idx);
    const locN = locations.length;
    const childN = children.length;
    const isDynamic = refN > 0;
    const locRefIdxs = locations.map((l) => l.refIdx);
    const locSetters = locations.map((l) => l.setData);
    const locUpdaters = locations.map((l) => l.updateData);
    const GETTERS = [nodeGetNextSibling, nodeGetFirstChild];
    const colN = collectors.length;
    const colPacked = collectors.map(
      (c) => c.idx & 32767 | (c.prevIdx & 32767) << 15 | (c.getVal === nodeGetFirstChild ? 1 : 0) << 30
    );
    const childInfos = children.map(
      (c) => c.parentRefIdx & 32767 | (c.isOnlyChild ? 1 : 0) << 15 | ((c.afterRefIdx ?? 0) & 32767) << 16
    );
    const nodeCloneNode = nodeProto.cloneNode;
    const nodeInsertBefore5 = nodeProto.insertBefore;
    const elementRemove = elementProto.remove;
    class Block {
      el;
      parentEl;
      data;
      children;
      refs;
      constructor(data) {
        this.data = data;
      }
      beforeRemove() {
      }
      remove() {
        elementRemove.call(this.el);
      }
      firstNode() {
        return this.el;
      }
      moveBeforeDOMNode(node, parent = this.parentEl) {
        this.parentEl = parent;
        nodeInsertBefore5.call(parent, this.el, node);
      }
      moveBeforeVNode(other, afterNode) {
        nodeInsertBefore5.call(this.parentEl, this.el, other ? other.el : afterNode);
      }
      toString() {
        const div = document.createElement("div");
        this.mount(div, null);
        return div.innerHTML;
      }
      mount(parent, afterNode) {
        const el = nodeCloneNode.call(template, true);
        nodeInsertBefore5.call(parent, el, afterNode);
        this.el = el;
        this.parentEl = parent;
      }
      patch(other, withBeforeRemove) {
      }
    }
    if (isDynamic) {
      Block.prototype.mount = function mount3(parent, afterNode) {
        const el = nodeCloneNode.call(template, true);
        const refs = new Array(refN);
        this.refs = refs;
        refs[0] = el;
        for (let i = 0; i < colN; i++) {
          const packed = colPacked[i];
          refs[packed & 32767] = GETTERS[packed >> 30 & 1].call(refs[packed >> 15 & 32767]);
        }
        if (locN) {
          const data = this.data;
          for (let i = 0; i < locN; i++) {
            locSetters[i].call(refs[locRefIdxs[i]], data[i]);
          }
        }
        if (childN) {
          const children2 = this.children;
          for (let i = 0; i < childN; i++) {
            const child = children2[i];
            if (child) {
              const info = childInfos[i];
              const afterRefIdx = info >> 16 & 32767;
              const afterNode2 = afterRefIdx ? refs[afterRefIdx] : null;
              child.isOnlyChild = !!(info & 1 << 15);
              child.mount(refs[info & 32767], afterNode2);
            }
          }
        }
        nodeInsertBefore5.call(parent, el, afterNode);
        this.el = el;
        this.parentEl = parent;
        if (cbRefs.length) {
          const data = this.data;
          const refs2 = this.refs;
          for (let cbRef of cbRefs) {
            const fn = data[cbRef];
            fn(refs2[locRefIdxs[cbRef]], null);
          }
        }
      };
      Block.prototype.patch = function patch2(other, withBeforeRemove) {
        if (this === other) {
          return;
        }
        const refs = this.refs;
        if (locN) {
          const data1 = this.data;
          const data2 = other.data;
          for (let i = 0; i < locN; i++) {
            const val1 = data1[i];
            const val2 = data2[i];
            if (val1 !== val2) {
              locUpdaters[i].call(refs[locRefIdxs[i]], val2, val1);
            }
          }
          this.data = data2;
        }
        if (childN) {
          let children1 = this.children;
          const children2 = other.children;
          for (let i = 0; i < childN; i++) {
            const child1 = children1[i];
            const child2 = children2[i];
            if (child1) {
              if (child2) {
                child1.patch(child2, withBeforeRemove);
              } else {
                if (withBeforeRemove) {
                  child1.beforeRemove();
                }
                child1.remove();
                children1[i] = void 0;
              }
            } else if (child2) {
              const info = childInfos[i];
              const afterRefIdx = info >> 16 & 32767;
              const afterNode = afterRefIdx ? refs[afterRefIdx] : null;
              child2.mount(refs[info & 32767], afterNode);
              children1[i] = child2;
            }
          }
        }
      };
      Block.prototype.remove = function remove2() {
        if (cbRefs.length) {
          const data = this.data;
          const refs = this.refs;
          for (let cbRef of cbRefs) {
            const fn = data[cbRef];
            fn(null, refs[locRefIdxs[cbRef]]);
          }
        }
        elementRemove.call(this.el);
      };
    }
    return Block;
  }
  function setText(value) {
    characterDataSetData2.call(this, toText(value));
  }
  var getDescriptor4 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
  var nodeInsertBefore3;
  var nodeAppendChild;
  var nodeRemoveChild3;
  var nodeSetTextContent2;
  if (typeof Node !== "undefined") {
    const nodeProto2 = Node.prototype;
    nodeInsertBefore3 = nodeProto2.insertBefore;
    nodeAppendChild = nodeProto2.appendChild;
    nodeRemoveChild3 = nodeProto2.removeChild;
    nodeSetTextContent2 = getDescriptor4(nodeProto2, "textContent").set;
  }
  var VList = class {
    children;
    anchor;
    parentEl;
    isOnlyChild;
    constructor(children) {
      this.children = children;
    }
    mount(parent, afterNode) {
      const children = this.children;
      const _anchor = document.createTextNode("");
      this.anchor = _anchor;
      nodeInsertBefore3.call(parent, _anchor, afterNode);
      const l = children.length;
      if (l) {
        const mount3 = children[0].mount;
        for (let i = 0; i < l; i++) {
          mount3.call(children[i], parent, _anchor);
        }
      }
      this.parentEl = parent;
    }
    moveBeforeDOMNode(node, parent = this.parentEl) {
      this.parentEl = parent;
      const children = this.children;
      for (let i = 0, l = children.length; i < l; i++) {
        children[i].moveBeforeDOMNode(node, parent);
      }
      parent.insertBefore(this.anchor, node);
    }
    moveBeforeVNode(other, afterNode) {
      if (other) {
        const next = other.children[0];
        afterNode = (next ? next.firstNode() : other.anchor) || null;
      }
      const children = this.children;
      for (let i = 0, l = children.length; i < l; i++) {
        children[i].moveBeforeVNode(null, afterNode);
      }
      this.parentEl.insertBefore(this.anchor, afterNode);
    }
    patch(other, withBeforeRemove) {
      if (this === other) {
        return;
      }
      const ch1 = this.children;
      const ch2 = other.children;
      if (ch2.length === 0 && ch1.length === 0) {
        return;
      }
      this.children = ch2;
      const proto = ch2[0] || ch1[0];
      const {
        mount: cMount,
        patch: cPatch,
        remove: cRemove,
        beforeRemove,
        moveBeforeVNode: cMoveBefore,
        firstNode: cFirstNode
      } = proto;
      const _anchor = this.anchor;
      const isOnlyChild = this.isOnlyChild;
      const parent = this.parentEl;
      if (ch2.length === 0 && isOnlyChild) {
        if (withBeforeRemove) {
          for (let i = 0, l = ch1.length; i < l; i++) {
            beforeRemove.call(ch1[i]);
          }
        }
        nodeSetTextContent2.call(parent, "");
        nodeAppendChild.call(parent, _anchor);
        return;
      }
      let startIdx1 = 0;
      let startIdx2 = 0;
      let startVn1 = ch1[0];
      let startVn2 = ch2[0];
      let endIdx1 = ch1.length - 1;
      let endIdx2 = ch2.length - 1;
      let endVn1 = ch1[endIdx1];
      let endVn2 = ch2[endIdx2];
      let mapping = void 0;
      while (startIdx1 <= endIdx1 && startIdx2 <= endIdx2) {
        if (startVn1 === null) {
          startVn1 = ch1[++startIdx1];
          continue;
        }
        if (endVn1 === null) {
          endVn1 = ch1[--endIdx1];
          continue;
        }
        let startKey1 = startVn1.key;
        let startKey2 = startVn2.key;
        if (startKey1 === startKey2) {
          cPatch.call(startVn1, startVn2, withBeforeRemove);
          ch2[startIdx2] = startVn1;
          startVn1 = ch1[++startIdx1];
          startVn2 = ch2[++startIdx2];
          continue;
        }
        let endKey1 = endVn1.key;
        let endKey2 = endVn2.key;
        if (endKey1 === endKey2) {
          cPatch.call(endVn1, endVn2, withBeforeRemove);
          ch2[endIdx2] = endVn1;
          endVn1 = ch1[--endIdx1];
          endVn2 = ch2[--endIdx2];
          continue;
        }
        if (startKey1 === endKey2) {
          cPatch.call(startVn1, endVn2, withBeforeRemove);
          ch2[endIdx2] = startVn1;
          const nextChild = ch2[endIdx2 + 1];
          cMoveBefore.call(startVn1, nextChild, _anchor);
          startVn1 = ch1[++startIdx1];
          endVn2 = ch2[--endIdx2];
          continue;
        }
        if (endKey1 === startKey2) {
          cPatch.call(endVn1, startVn2, withBeforeRemove);
          ch2[startIdx2] = endVn1;
          const nextChild = ch1[startIdx1];
          cMoveBefore.call(endVn1, nextChild, _anchor);
          endVn1 = ch1[--endIdx1];
          startVn2 = ch2[++startIdx2];
          continue;
        }
        mapping = mapping || createMapping(ch1, startIdx1, endIdx1);
        let idxInOld = mapping[startKey2];
        if (idxInOld === void 0) {
          cMount.call(startVn2, parent, cFirstNode.call(startVn1) || null);
        } else {
          const elmToMove = ch1[idxInOld];
          cMoveBefore.call(elmToMove, startVn1, null);
          cPatch.call(elmToMove, startVn2, withBeforeRemove);
          ch2[startIdx2] = elmToMove;
          ch1[idxInOld] = null;
        }
        startVn2 = ch2[++startIdx2];
      }
      if (startIdx1 <= endIdx1 || startIdx2 <= endIdx2) {
        if (startIdx1 > endIdx1) {
          const nextChild = ch2[endIdx2 + 1];
          const anchor = nextChild ? cFirstNode.call(nextChild) || null : _anchor;
          for (let i = startIdx2; i <= endIdx2; i++) {
            cMount.call(ch2[i], parent, anchor);
          }
        } else {
          for (let i = startIdx1; i <= endIdx1; i++) {
            let ch = ch1[i];
            if (ch) {
              if (withBeforeRemove) {
                beforeRemove.call(ch);
              }
              cRemove.call(ch);
            }
          }
        }
      }
    }
    beforeRemove() {
      const children = this.children;
      const l = children.length;
      if (l) {
        const beforeRemove = children[0].beforeRemove;
        for (let i = 0; i < l; i++) {
          beforeRemove.call(children[i]);
        }
      }
    }
    remove() {
      const { parentEl, anchor } = this;
      if (this.isOnlyChild) {
        nodeSetTextContent2.call(parentEl, "");
      } else {
        const children = this.children;
        const l = children.length;
        if (l) {
          const remove2 = children[0].remove;
          for (let i = 0; i < l; i++) {
            remove2.call(children[i]);
          }
        }
        nodeRemoveChild3.call(parentEl, anchor);
      }
    }
    firstNode() {
      const child = this.children[0];
      return child ? child.firstNode() : void 0;
    }
    toString() {
      return this.children.map((c) => c.toString()).join("");
    }
  };
  function list(children) {
    return new VList(children);
  }
  function createMapping(ch1, startIdx1, endIdx2) {
    let mapping = {};
    for (let i = startIdx1; i <= endIdx2; i++) {
      mapping[ch1[i].key] = i;
    }
    return mapping;
  }
  var nodeInsertBefore4;
  var nodeRemoveChild4;
  if (typeof Node !== "undefined") {
    const nodeProto2 = Node.prototype;
    nodeInsertBefore4 = nodeProto2.insertBefore;
    nodeRemoveChild4 = nodeProto2.removeChild;
  }
  var VHtml = class {
    html;
    parentEl;
    content = [];
    constructor(html2) {
      this.html = html2;
    }
    mount(parent, afterNode) {
      this.parentEl = parent;
      const template = document.createElement("template");
      template.innerHTML = this.html;
      this.content = [...template.content.childNodes];
      for (let elem of this.content) {
        nodeInsertBefore4.call(parent, elem, afterNode);
      }
      if (!this.content.length) {
        const textNode = document.createTextNode("");
        this.content.push(textNode);
        nodeInsertBefore4.call(parent, textNode, afterNode);
      }
    }
    moveBeforeDOMNode(node, parent = this.parentEl) {
      this.parentEl = parent;
      for (let elem of this.content) {
        nodeInsertBefore4.call(parent, elem, node);
      }
    }
    moveBeforeVNode(other, afterNode) {
      const target = other ? other.content[0] : afterNode;
      this.moveBeforeDOMNode(target);
    }
    patch(other) {
      if (this === other) {
        return;
      }
      const html2 = other.html;
      if (this.html !== html2) {
        const parent = this.parentEl;
        const afterNode = this.content[0];
        const template = document.createElement("template");
        template.innerHTML = html2;
        const content = [...template.content.childNodes];
        for (let elem of content) {
          nodeInsertBefore4.call(parent, elem, afterNode);
        }
        if (!content.length) {
          const textNode = document.createTextNode("");
          content.push(textNode);
          nodeInsertBefore4.call(parent, textNode, afterNode);
        }
        this.remove();
        this.content = content;
        this.html = other.html;
      }
    }
    beforeRemove() {
    }
    remove() {
      const parent = this.parentEl;
      for (let elem of this.content) {
        nodeRemoveChild4.call(parent, elem);
      }
    }
    firstNode() {
      return this.content[0];
    }
    toString() {
      return this.html;
    }
  };
  function html(str) {
    return new VHtml(str);
  }
  function createCatcher(eventsSpec) {
    const n = Object.keys(eventsSpec).length;
    class VCatcher {
      child;
      handlerData;
      handlerFns = [];
      parentEl;
      afterNode = null;
      constructor(child, handlers) {
        this.child = child;
        this.handlerData = handlers;
      }
      mount(parent, afterNode) {
        this.parentEl = parent;
        this.child.mount(parent, afterNode);
        this.afterNode = document.createTextNode("");
        parent.insertBefore(this.afterNode, afterNode);
        this.wrapHandlerData();
        for (let name in eventsSpec) {
          const index = eventsSpec[name];
          const handler = createEventHandler(name);
          this.handlerFns[index] = handler;
          handler.setup.call(parent, this.handlerData[index]);
        }
      }
      wrapHandlerData() {
        for (let i = 0; i < n; i++) {
          let handler = this.handlerData[i];
          let idx = handler.length - 2;
          let origFn = handler[idx];
          const self = this;
          handler[idx] = function(ctx, ev) {
            const target = ev.target;
            let currentNode = self.child.firstNode();
            const afterNode = self.afterNode;
            while (currentNode && currentNode !== afterNode) {
              if (currentNode.contains(target)) {
                return origFn(ctx, ev);
              }
              currentNode = currentNode.nextSibling;
            }
          };
        }
      }
      moveBeforeDOMNode(node, parent = this.parentEl) {
        this.parentEl = parent;
        this.child.moveBeforeDOMNode(node, parent);
        parent.insertBefore(this.afterNode, node);
      }
      moveBeforeVNode(other, afterNode) {
        if (other) {
          afterNode = other.firstNode() || afterNode;
        }
        this.child.moveBeforeVNode(other ? other.child : null, afterNode);
        this.parentEl.insertBefore(this.afterNode, afterNode);
      }
      patch(other, withBeforeRemove) {
        if (this === other) {
          return;
        }
        this.handlerData = other.handlerData;
        this.wrapHandlerData();
        for (let i = 0; i < n; i++) {
          this.handlerFns[i].update.call(this.parentEl, this.handlerData[i]);
        }
        this.child.patch(other.child, withBeforeRemove);
      }
      beforeRemove() {
        this.child.beforeRemove();
      }
      remove() {
        for (let i = 0; i < n; i++) {
          this.handlerFns[i].remove.call(this.parentEl);
        }
        this.child.remove();
        this.afterNode.remove();
      }
      firstNode() {
        return this.child.firstNode();
      }
      toString() {
        return this.child.toString();
      }
    }
    return function(child, handlers) {
      return new VCatcher(child, handlers);
    };
  }
  function mount(vnode, fixture, afterNode = null) {
    vnode.mount(fixture, afterNode);
  }
  function patch(vnode1, vnode2, withBeforeRemove = false) {
    vnode1.patch(vnode2, withBeforeRemove);
  }
  function remove(vnode, withBeforeRemove = false) {
    if (withBeforeRemove) {
      vnode.beforeRemove();
    }
    vnode.remove();
  }
  function status(entity) {
    switch (entity.__owl__.status) {
      case STATUS.NEW:
        return "new";
      case STATUS.CANCELLED:
        return "cancelled";
      case STATUS.MOUNTED:
        return entity instanceof Plugin ? "started" : "mounted";
      case STATUS.DESTROYED:
        return "destroyed";
    }
  }
  function makeChildFiber(node, parent) {
    let current = node.fiber;
    if (current) {
      cancelFibers(current.children);
      current.root = null;
    }
    return new Fiber(node, parent);
  }
  function makeRootFiber(node) {
    let current = node.fiber;
    if (current) {
      let root = current.root;
      root.locked = true;
      root.setCounter(root.counter + 1 - cancelFibers(current.children));
      root.locked = false;
      current.children = [];
      current.childrenMap = {};
      current.bdom = null;
      if (fibersInError.has(current)) {
        fibersInError.delete(current);
        fibersInError.delete(root);
        current.appliedToDom = false;
        if (current instanceof RootFiber) {
          current.mounted = current instanceof MountFiber ? [current] : [];
        }
      }
      return current;
    }
    const fiber = new RootFiber(node, null);
    if (node.willPatch.length) {
      fiber.willPatch.push(fiber);
    }
    if (node.patched.length) {
      fiber.patched.push(fiber);
    }
    return fiber;
  }
  function throwOnRender() {
    throw new OwlError("Attempted to render cancelled fiber");
  }
  function cancelFibers(fibers) {
    let result = 0;
    for (let fiber of fibers) {
      let node = fiber.node;
      fiber.render = throwOnRender;
      if (node.status === STATUS.NEW) {
        node.cancel();
      }
      node.fiber = null;
      if (fiber.bdom) {
        node.forceNextRender = true;
      } else {
        result++;
        if (node.bdom) {
          node.forceNextRender = true;
        }
      }
      result += cancelFibers(fiber.children);
    }
    return result;
  }
  var Fiber = class {
    node;
    bdom = null;
    root;
    // A Fiber that has been replaced by another has no root
    parent;
    children = [];
    appliedToDom = false;
    deep = false;
    childrenMap = {};
    constructor(node, parent) {
      this.node = node;
      this.parent = parent;
      if (parent) {
        this.deep = parent.deep;
        const root = parent.root;
        root.setCounter(root.counter + 1);
        this.root = root;
        parent.children.push(this);
      } else {
        this.root = this;
      }
    }
    render() {
      const scheduler = this.root.node.app.scheduler;
      if (scheduler.tasks.size > 1) {
        let prev = this.root.node;
        let current = prev.parent;
        while (current) {
          if (current.fiber) {
            let root2 = current.fiber.root;
            if (root2.counter === 0 && prev.parentKey in current.fiber.childrenMap) {
              current = root2.node;
            } else {
              scheduler.delayedRenders.push(this);
              return;
            }
          }
          prev = current;
          current = current.parent;
        }
      }
      const node = this.node;
      const root = this.root;
      if (root) {
        const c = getCurrentComputation();
        removeSources(node.signalComputation);
        setComputation(node.signalComputation);
        node.signalComputation.state = ComputationState.EXECUTED;
        try {
          this.bdom = true;
          this.bdom = node.renderFn();
        } catch (e) {
          handleError({ node, error: e });
        } finally {
          setComputation(c);
        }
        const newCounter = root.counter - 1;
        root.counter = newCounter;
        if (newCounter === 0) {
          scheduler.flush();
        }
      }
    }
  };
  var RootFiber = class extends Fiber {
    counter = 1;
    // only add stuff in this if they have registered some hooks
    willPatch = [];
    patched = [];
    mounted = [];
    // A fiber is typically locked when it is completing and the patch has not, or is being applied.
    // i.e.: render triggered in onWillUnmount or in willPatch will be delayed
    locked = false;
    complete() {
      const node = this.node;
      this.locked = true;
      let current = void 0;
      let mountedFibers = this.mounted;
      try {
        for (current of this.willPatch) {
          let node2 = current.node;
          if (node2.fiber === current) {
            const component = node2.component;
            for (let cb of node2.willPatch) {
              cb.call(component);
            }
          }
        }
        current = void 0;
        node._patch();
        this.locked = false;
        while (current = mountedFibers.pop()) {
          current = current;
          if (current.appliedToDom) {
            for (let cb of current.node.mounted) {
              cb();
            }
          }
        }
        let patchedFibers = this.patched;
        while (current = patchedFibers.pop()) {
          current = current;
          if (current.appliedToDom) {
            for (let cb of current.node.patched) {
              cb();
            }
          }
        }
      } catch (e) {
        for (let fiber of mountedFibers) {
          fiber.node.willUnmount = [];
        }
        this.locked = false;
        handleError({ fiber: current || this, error: e });
      }
    }
    setCounter(newValue) {
      this.counter = newValue;
      if (newValue === 0) {
        this.node.app.scheduler.flush();
      }
    }
  };
  var MountFiber = class extends RootFiber {
    target;
    position;
    afterNode = null;
    // true once the render phase finishes (counter reaches 0). If target is
    // set at that point, we mount immediately; otherwise we signal readiness
    // via onPrepared and wait for commit() to supply a target.
    prepared = false;
    onPrepared = null;
    constructor(node, target, options = {}) {
      super(node, null);
      this.target = target;
      this.position = options.position || "last-child";
      this.afterNode = options.afterNode ?? null;
    }
    complete() {
      this.prepared = true;
      if (this.target) {
        this._mount();
      } else {
        this.appliedToDom = true;
        this.onPrepared?.();
      }
    }
    commit(target, options = {}) {
      this.target = target;
      this.position = options.position || "last-child";
      this.afterNode = options.afterNode ?? null;
      if (this.prepared) {
        this._mount();
      }
    }
    _mount() {
      let current = this;
      try {
        const node = this.node;
        node.children = this.childrenMap;
        node.app.constructor.validateTarget(this.target);
        if (node.bdom) {
          node.updateDom();
        } else {
          node.bdom = this.bdom;
          if (this.afterNode) {
            mount(node.bdom, this.target, this.afterNode);
          } else if (this.position === "last-child" || this.target.childNodes.length === 0) {
            mount(node.bdom, this.target);
          } else {
            const firstChild = this.target.childNodes[0];
            mount(node.bdom, this.target, firstChild);
          }
        }
        node.fiber = null;
        node.status = STATUS.MOUNTED;
        this.appliedToDom = true;
        let mountedFibers = this.mounted;
        while (current = mountedFibers.pop()) {
          if (current.appliedToDom) {
            for (let cb of current.node.mounted) {
              cb();
            }
          }
        }
      } catch (e) {
        handleError({ fiber: current, error: e });
      }
    }
  };
  var ComponentNode = class extends Scope {
    fiber = null;
    component;
    bdom = null;
    componentName;
    forceNextRender = false;
    parentKey;
    props;
    defaultProps = null;
    renderFn;
    parent;
    children = /* @__PURE__ */ Object.create(null);
    willUpdateProps = [];
    willUnmount = [];
    mounted = [];
    willPatch = [];
    patched = [];
    signalComputation;
    pluginManager;
    constructor(C, props2, app, parent, parentKey) {
      super(app);
      this.parent = parent;
      this.parentKey = parentKey;
      this.pluginManager = parent ? parent.pluginManager : app.pluginManager;
      this.componentName = C.name;
      this.signalComputation = createComputation(
        () => this.render(false),
        false,
        ComputationState.EXECUTED
      );
      this.props = props2;
      const previousComputation = getCurrentComputation();
      setComputation(void 0);
      scopeStack.push(this);
      try {
        this.component = new C(this);
        const ctx = { this: this.component, __owl__: this };
        this.renderFn = app.getTemplate(C.template).bind(this.component, ctx, this);
        this.component.setup();
      } finally {
        scopeStack.pop();
        setComputation(previousComputation);
      }
    }
    decorate(f, hookName) {
      const component = this.component;
      const scope = this;
      if (this.app.dev) {
        const name = `${this.componentName}.${hookName}`;
        const wrapper = {
          [name](...args) {
            return f.call(component, scope, ...args);
          }
        };
        return wrapper[name];
      }
      return f.bind(component, scope);
    }
    async initiateRender(fiber) {
      this.fiber = fiber;
      if (this.mounted.length) {
        fiber.root.mounted.push(fiber);
      }
      const component = this.component;
      let prev = getCurrentComputation();
      setComputation(void 0);
      try {
        let promises = this.willStart.map((f) => f.call(component));
        setComputation(prev);
        await Promise.all(promises);
      } catch (e) {
        if (isAbortError(e) && this.status > STATUS.MOUNTED) {
          return;
        }
        handleError({ node: this, error: e });
        return;
      }
      if (this.status === STATUS.NEW && this.fiber === fiber) {
        fiber.render();
      }
    }
    async render(deep) {
      if (this.status >= STATUS.CANCELLED) {
        return;
      }
      let current = this.fiber;
      if (current && (current.root.locked || current.bdom === true)) {
        await Promise.resolve();
        current = this.fiber;
      }
      if (current) {
        if (!current.bdom && !fibersInError.has(current)) {
          if (deep) {
            current.deep = deep;
          }
          return;
        }
        deep = deep || current.deep;
      } else if (!this.bdom) {
        return;
      }
      const fiber = makeRootFiber(this);
      fiber.deep = deep;
      this.fiber = fiber;
      this.app.scheduler.addFiber(fiber);
      await Promise.resolve();
      if (this.status >= STATUS.CANCELLED) {
        return;
      }
      if (this.fiber === fiber && (current || !fiber.parent)) {
        fiber.render();
      }
    }
    cancel() {
      this._cancel();
      delete this.parent.children[this.parentKey];
      this.app.scheduler.scheduleDestroy(this);
    }
    _cancel() {
      super.cancel();
      const children = this.children;
      for (let childKey in children) {
        children[childKey]._cancel();
      }
    }
    destroy() {
      let shouldRemove = this.status === STATUS.MOUNTED;
      this._destroy();
      if (shouldRemove) {
        this.bdom.remove();
      }
    }
    _destroy() {
      const component = this.component;
      if (this.status === STATUS.MOUNTED) {
        for (let cb of this.willUnmount) {
          cb.call(component);
        }
      }
      for (let childKey in this.children) {
        this.children[childKey]._destroy();
      }
      this.finalize((e) => handleError({ error: e, node: this }));
      disposeComputation(this.signalComputation);
    }
    /**
     * Finds a child that has dom that is not yet updated, and update it. This
     * method is meant to be used only in the context of repatching the dom after
     * a mounted hook failed and was handled.
     */
    updateDom() {
      if (!this.fiber) {
        return;
      }
      if (this.bdom === this.fiber.bdom) {
        for (let k in this.children) {
          const child = this.children[k];
          child.updateDom();
        }
      } else {
        this.bdom.patch(this.fiber.bdom, false);
        this.fiber.appliedToDom = true;
        this.fiber = null;
      }
    }
    // ---------------------------------------------------------------------------
    // Block DOM methods
    // ---------------------------------------------------------------------------
    firstNode() {
      const bdom2 = this.bdom;
      return bdom2 ? bdom2.firstNode() : void 0;
    }
    mount(parent, anchor) {
      const bdom2 = this.fiber.bdom;
      this.bdom = bdom2;
      bdom2.mount(parent, anchor);
      this.status = STATUS.MOUNTED;
      this.fiber.appliedToDom = true;
      this.children = this.fiber.childrenMap;
      this.fiber = null;
    }
    moveBeforeDOMNode(node, parent) {
      this.bdom.moveBeforeDOMNode(node, parent);
    }
    moveBeforeVNode(other, afterNode) {
      this.bdom.moveBeforeVNode(other ? other.bdom : null, afterNode);
    }
    patch() {
      if (this.fiber && this.fiber.parent) {
        this._patch();
      }
    }
    _patch() {
      let hasChildren = false;
      for (let _k in this.children) {
        hasChildren = true;
        break;
      }
      const fiber = this.fiber;
      this.children = fiber.childrenMap;
      this.bdom.patch(fiber.bdom, hasChildren);
      fiber.appliedToDom = true;
      this.fiber = null;
    }
    beforeRemove() {
      this._destroy();
    }
    remove() {
      this.bdom.remove();
    }
  };
  function getComponentScope() {
    const scope = useScope();
    if (!(scope instanceof ComponentNode)) {
      throw new OwlError("Expected to be in a component scope");
    }
    return scope;
  }
  var requestAnimationFrame;
  if (typeof window !== "undefined") {
    requestAnimationFrame = window.requestAnimationFrame.bind(window);
  }
  var Scheduler = class _Scheduler {
    // capture the value of requestAnimationFrame as soon as possible, to avoid
    // interactions with other code, such as test frameworks that override them
    static requestAnimationFrame = requestAnimationFrame;
    tasks = /* @__PURE__ */ new Set();
    requestAnimationFrame;
    frame = 0;
    delayedRenders = [];
    cancelledNodes = /* @__PURE__ */ new Set();
    processing = false;
    constructor() {
      this.requestAnimationFrame = _Scheduler.requestAnimationFrame;
    }
    addFiber(fiber) {
      this.tasks.add(fiber.root);
    }
    scheduleDestroy(node) {
      this.cancelledNodes.add(node);
      if (this.frame === 0) {
        this.frame = this.requestAnimationFrame(() => this.processTasks());
      }
    }
    /**
     * Process all current tasks. This only applies to the fibers that are ready.
     * Other tasks are left unchanged.
     */
    flush() {
      if (this.delayedRenders.length) {
        let renders = this.delayedRenders;
        this.delayedRenders = [];
        for (let f of renders) {
          if (f.root && f.node.status !== STATUS.DESTROYED && f.node.fiber === f) {
            f.render();
          }
        }
      }
      if (this.frame === 0) {
        this.frame = this.requestAnimationFrame(() => this.processTasks());
      }
    }
    processTasks() {
      if (this.processing) {
        return;
      }
      this.processing = true;
      this.frame = 0;
      for (let node of this.cancelledNodes) {
        node._destroy();
      }
      this.cancelledNodes.clear();
      for (let fiber of this.tasks) {
        if (fiber.root !== fiber) {
          this.tasks.delete(fiber);
          continue;
        }
        const hasError = fibersInError.has(fiber);
        if (hasError && fiber.counter !== 0) {
          this.tasks.delete(fiber);
          continue;
        }
        if (fiber.node.status === STATUS.DESTROYED) {
          this.tasks.delete(fiber);
          continue;
        }
        if (fiber.counter === 0) {
          if (!hasError) {
            fiber.complete();
          }
          if (fiber.appliedToDom) {
            this.tasks.delete(fiber);
          }
        }
      }
      for (let task of this.tasks) {
        if (task.node.status === STATUS.DESTROYED) {
          this.tasks.delete(task);
        }
      }
      this.processing = false;
    }
  };
  var Component = class {
    static template = "";
    __owl__;
    constructor(node) {
      this.__owl__ = node;
    }
    setup() {
    }
  };
  var ObjectCreate = Object.create;
  function withDefault(value, defaultValue) {
    return value === void 0 || value === null || value === false ? defaultValue : value;
  }
  function callSlot(ctx, parent, key, name, dynamic, extra, defaultContent) {
    key = key + "__slot_" + name;
    const slots = ctx.__owl__.props.slots || {};
    const { __render, __ctx, __scope } = slots[name] || {};
    const slotScope = ObjectCreate(__ctx || {});
    if (__scope) {
      slotScope[__scope] = extra;
    }
    const slotBDom = __render ? __render(slotScope, parent, key) : null;
    if (defaultContent) {
      let child1 = void 0;
      let child2 = void 0;
      if (slotBDom) {
        child1 = dynamic ? toggler(name, slotBDom) : slotBDom;
      } else {
        child2 = defaultContent(ctx, parent, key);
      }
      return multi([child1, child2]);
    }
    return slotBDom || text("");
  }
  function withKey(elem, k) {
    elem.key = k;
    return elem;
  }
  function prepareList(collection) {
    let keys;
    let values;
    if (Array.isArray(collection)) {
      keys = collection;
      values = collection;
    } else if (collection instanceof Map) {
      keys = [...collection.keys()];
      values = [...collection.values()];
    } else if (Symbol.iterator in Object(collection)) {
      keys = [...collection];
      values = keys;
    } else if (collection && typeof collection === "object") {
      values = Object.values(collection);
      keys = Object.keys(collection);
    } else {
      throw new OwlError(`Invalid loop expression: "${collection}" is not iterable`);
    }
    const n = values.length;
    return [keys, values, n, new Array(n)];
  }
  function toNumber(val) {
    const n = parseFloat(val);
    return isNaN(n) ? val : n;
  }
  function shallowEqual(l1, l2) {
    for (let i = 0, l = l1.length; i < l; i++) {
      if (l1[i] !== l2[i]) {
        return false;
      }
    }
    return true;
  }
  var LazyValue = class {
    fn;
    ctx;
    component;
    node;
    key;
    constructor(fn, ctx, component, node, key) {
      this.fn = fn;
      this.ctx = ctx;
      this.component = component;
      this.node = node;
      this.key = key;
    }
    evaluate() {
      return this.fn.call(this.component, this.ctx, this.node, this.key);
    }
    toString() {
      return this.evaluate().toString();
    }
  };
  function safeOutput(value, defaultValue) {
    if (value === void 0 || value === null) {
      return defaultValue ? toggler("default", defaultValue) : toggler("undefined", text(""));
    }
    let safeKey;
    let block;
    if (value instanceof Markup) {
      safeKey = `string_safe`;
      block = html(value);
    } else if (value instanceof LazyValue) {
      safeKey = `lazy_value`;
      block = value.evaluate();
    } else {
      safeKey = "string_unsafe";
      block = text(value);
    }
    return toggler(safeKey, block);
  }
  function createRef(ref2) {
    if (!ref2) {
      throw new OwlError(`Ref is undefined or null`);
    }
    let add;
    let remove2;
    if (ref2.add && ref2.delete) {
      add = ref2.add.bind(ref2);
      remove2 = ref2.delete.bind(ref2);
    } else if (ref2.set) {
      add = ref2.set.bind(ref2);
      const atom = ref2[atomSymbol];
      remove2 = atom ? (prevEl) => {
        if (atom.value === prevEl) ref2.set(null);
      } : () => ref2.set(null);
    } else {
      throw new OwlError(
        `Ref should implement either a 'set' function or 'add' and 'delete' functions`
      );
    }
    return (el, previousEl) => {
      if (previousEl) {
        remove2(previousEl);
      }
      if (el) {
        add(el);
      }
    };
  }
  function callHandler(fn, ctx, ev) {
    if (typeof fn !== "function") {
      throw new OwlError(
        `Invalid handler expression: the \`t-on\` expression should evaluate to a function, but got '${typeof fn}'. Did you mean to use an arrow function? (e.g. \`t-on-click="() => expr"\`)`
      );
    }
    fn.call(ctx["this"], ev);
  }
  var signalCaches = /* @__PURE__ */ new WeakMap();
  function toSignal(node, cacheKey, value) {
    let cache22 = signalCaches.get(node);
    if (!cache22) {
      cache22 = /* @__PURE__ */ new Map();
      signalCaches.set(node, cache22);
    }
    const existing = cache22.get(cacheKey);
    if (existing) {
      existing.set(value);
      return existing.readonly;
    }
    const s = signal(value);
    s.readonly = computed(s);
    cache22.set(cacheKey, s);
    return s.readonly;
  }
  function modelExpr(value) {
    if (typeof value !== "function" || typeof value.set !== "function") {
      throw new OwlError(
        `Invalid t-model expression: expression should evaluate to a function with a 'set' method defined on it`
      );
    }
    return value;
  }
  function createComponent(app, name, isStatic, hasSlotsProp, hasDynamicPropList, propList) {
    const isDynamic = !isStatic;
    let arePropsDifferent;
    const hasNoProp = propList.length === 0;
    if (hasSlotsProp) {
      arePropsDifferent = (_1, _2) => true;
    } else if (hasDynamicPropList) {
      arePropsDifferent = function(props1, props2) {
        for (let k in props1) {
          if (props1[k] !== props2[k]) {
            return true;
          }
        }
        return Object.keys(props1).length !== Object.keys(props2).length;
      };
    } else if (hasNoProp) {
      arePropsDifferent = (_1, _2) => false;
    } else {
      arePropsDifferent = function(props1, props2) {
        for (let p of propList) {
          if (props1[p] !== props2[p]) {
            return true;
          }
        }
        return false;
      };
    }
    const initiateRender = ComponentNode.prototype.initiateRender;
    return (props2, key, ctx, parent, C) => {
      let children = ctx.children;
      let node = children[key];
      if (isDynamic && node && node.component.constructor !== C) {
        node = void 0;
      }
      const parentFiber = ctx.fiber;
      if (node) {
        if (arePropsDifferent(node.props, props2) || parentFiber.deep || node.forceNextRender) {
          node.forceNextRender = false;
          const hooks = node.willUpdateProps;
          const fiber = makeChildFiber(node, parentFiber);
          node.fiber = fiber;
          const parentRoot = parentFiber.root;
          if (node.willPatch.length) parentRoot.willPatch.push(fiber);
          if (node.patched.length) parentRoot.patched.push(fiber);
          let promises;
          if (hooks.length) {
            let nextProps = props2;
            const defaultProps = node.defaultProps;
            if (defaultProps) {
              nextProps = Object.assign({}, props2);
              for (const k in defaultProps) {
                if (nextProps[k] === void 0) {
                  nextProps[k] = defaultProps[k];
                }
              }
            }
            const component = node.component;
            const prev = getCurrentComputation();
            setComputation(void 0);
            for (const f of hooks) {
              const r = f.call(component, nextProps);
              if (r && typeof r.then === "function") {
                (promises ||= []).push(r);
              }
            }
            setComputation(prev);
          }
          if (promises) {
            const p = promises.length === 1 ? promises[0] : Promise.all(promises);
            p.then(
              () => {
                if (fiber !== node.fiber) return;
                node.props = props2;
                fiber.render();
              },
              (error) => {
                handleError({ node, error });
              }
            );
          } else {
            node.props = props2;
            fiber.render();
          }
        }
      } else {
        if (isStatic) {
          const components = parent.constructor.components;
          if (!components) {
            throw new OwlError(
              `Cannot find the definition of component "${name}", missing static components key in parent`
            );
          }
          C = components[name];
          if (!C) {
            throw new OwlError(`Cannot find the definition of component "${name}"`);
          } else if (!(C.prototype instanceof Component)) {
            throw new OwlError(
              `"${name}" is not a Component. It must inherit from the Component class`
            );
          }
        }
        node = new ComponentNode(C, props2, app, ctx, key);
        children[key] = node;
        const fiber = new Fiber(node, parentFiber);
        if (node.willStart.length) {
          initiateRender.call(node, fiber);
        } else {
          node.fiber = fiber;
          if (node.mounted.length) {
            fiber.root.mounted.push(fiber);
          }
          fiber.render();
        }
      }
      parentFiber.childrenMap[key] = node;
      return node;
    };
  }
  function callTemplate(subTemplate, owner, app, ctx, parent, key) {
    const template = app.getTemplate(subTemplate);
    return toggler(subTemplate, template.call(owner, ctx, parent, key + subTemplate));
  }
  var helpers = {
    withDefault,
    zero: /* @__PURE__ */ Symbol("zero"),
    callSlot,
    withKey,
    prepareList,
    shallowEqual,
    toNumber,
    LazyValue,
    safeOutput,
    createCatcher,
    markRaw,
    OwlError,
    createRef,
    modelExpr,
    createComponent,
    callTemplate,
    callHandler,
    toSignal
  };
  var bdom = { text, createBlock, list, multi, html, toggler };
  var TemplateSet = class {
    static registerTemplate(name, fn) {
      globalTemplates[name] = fn;
    }
    dev;
    rawTemplates = Object.create(globalTemplates);
    templates = {};
    getRawTemplate;
    translateFn;
    translatableAttributes;
    customDirectives;
    runtimeUtils;
    hasGlobalValues;
    constructor(config3 = {}) {
      this.dev = config3.dev || false;
      this.translateFn = config3.translateFn;
      this.translatableAttributes = config3.translatableAttributes;
      if (config3.templates) {
        if (config3.templates instanceof Document || typeof config3.templates === "string") {
          this.addTemplates(config3.templates);
        } else {
          for (const name in config3.templates) {
            this.addTemplate(name, config3.templates[name]);
          }
        }
      }
      this.getRawTemplate = config3.getTemplate;
      this.customDirectives = config3.customDirectives || {};
      this.runtimeUtils = { ...helpers, __globals__: config3.globalValues || {} };
      this.hasGlobalValues = Boolean(config3.globalValues && Object.keys(config3.globalValues).length);
    }
    addTemplate(name, template) {
      if (name in this.rawTemplates) {
        if (!this.dev) {
          return;
        }
        const rawTemplate = this.rawTemplates[name];
        if (areTemplatesEqual(rawTemplate, template)) {
          return;
        }
        throw new OwlError(`Template ${name} already defined with different content`);
      }
      this.rawTemplates[name] = template;
    }
    addTemplates(xml2) {
      if (!xml2) {
        return;
      }
      xml2 = xml2 instanceof Document ? xml2 : this._parseXML(xml2);
      for (const template of xml2.querySelectorAll("[t-name]")) {
        const name = template.getAttribute("t-name");
        this.addTemplate(name, template);
      }
    }
    getTemplate(name) {
      const cacheKey = name;
      if (!(cacheKey in this.templates)) {
        const rawTemplate = this.getRawTemplate?.(name) || this.rawTemplates[name];
        if (rawTemplate === void 0) {
          let extraInfo = "";
          const scope = getScope();
          if (scope instanceof ComponentNode) {
            extraInfo = ` (for component "${scope.componentName}")`;
          }
          throw new OwlError(`Missing template: "${name}"${extraInfo}`);
        }
        const isFn = typeof rawTemplate === "function" && !(rawTemplate instanceof Element);
        const templateFn = isFn ? rawTemplate : this._compileTemplate(name, rawTemplate);
        const templates = this.templates;
        this.templates[cacheKey] = function(context, parent) {
          return templates[cacheKey].call(this, context, parent);
        };
        const template = templateFn(this, bdom, this.runtimeUtils);
        this.templates[cacheKey] = template;
      }
      return this.templates[cacheKey];
    }
    _compileTemplate(name, template) {
      throw new OwlError(`Unable to compile a template. Please use owl full build instead`);
    }
    _parseXML(xml2) {
      throw new OwlError(
        `Unable to parse XML templates. Please use owl full build instead, or pass a Document instance.`
      );
    }
  };
  var globalTemplates = {};
  function xml(...args) {
    const name = `__template__${xml.nextId++}`;
    const value = String.raw(...args);
    globalTemplates[name] = value;
    return name;
  }
  xml.nextId = 1;
  function areTemplatesEqual(t1, t2) {
    if (t1 === t2) {
      return true;
    }
    if (typeof t1 === "function" !== (typeof t2 === "function")) {
      return false;
    }
    const s1 = t1 instanceof Element ? t1.outerHTML : String(t1);
    const s2 = t2 instanceof Element ? t2.outerHTML : String(t2);
    return s1 === s2;
  }
  var hasBeenLogged = false;
  var apps = /* @__PURE__ */ new Set();
  if (typeof window !== "undefined") {
    window.__OWL_DEVTOOLS__ ||= { apps, Fiber, RootFiber, toRaw, proxy };
  }
  var App = class _App extends TemplateSet {
    static validateTarget = validateTarget;
    static apps = apps;
    static version = version;
    name;
    scheduler = new Scheduler();
    roots = /* @__PURE__ */ new Set();
    pluginManager;
    destroyed = false;
    constructor(config3 = {}) {
      super(config3);
      this.name = config3.name || "";
      apps.add(this);
      this.pluginManager = new PluginManager(this, { config: config3.config });
      if (config3.plugins) {
        startPlugins(this.pluginManager, config3.plugins);
      } else {
        this.pluginManager.status = STATUS.MOUNTED;
      }
      if (config3.test) {
        this.dev = true;
      }
      if (this.dev && !config3.test && !hasBeenLogged) {
        console.info(`Owl is running in 'dev' mode.`);
        hasBeenLogged = true;
      }
    }
    createRoot(Root, config3 = {}) {
      const props2 = config3.props || {};
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
      });
      let node;
      let error = null;
      try {
        node = new ComponentNode(Root, props2, this, null, null);
      } catch (e) {
        error = e;
        reject(e);
      }
      let fiber = null;
      let preparedPromise = null;
      const prepare = () => {
        if (preparedPromise) {
          return preparedPromise;
        }
        if (error) {
          return Promise.reject(error);
        }
        fiber = new MountFiber(node, null);
        let handlers = nodeErrorHandlers.get(node);
        if (!handlers) {
          handlers = [];
          nodeErrorHandlers.set(node, handlers);
        }
        handlers.unshift((_, finalize) => {
          const finalError = finalize();
          reject(finalError);
        });
        const ready = new Promise((res) => {
          fiber.onPrepared = () => res();
        });
        preparedPromise = ready;
        node.mounted.push(() => {
          resolve(node.component);
          handlers.shift();
        });
        this.scheduler.addFiber(fiber);
        if (this.pluginManager.status < STATUS.MOUNTED) {
          node.willStart.unshift(() => this.pluginManager.ready);
        }
        if (node.willStart.length) {
          node.initiateRender(fiber);
        } else {
          node.fiber = fiber;
          if (node.mounted.length) {
            fiber.root.mounted.push(fiber);
          }
          try {
            fiber.render();
          } catch (e) {
            reject(e);
          }
        }
        return preparedPromise;
      };
      const mount3 = (target, options) => {
        if (error) {
          return promise;
        }
        _App.validateTarget(target);
        prepare();
        fiber.commit(target, options);
        return promise;
      };
      const root = {
        node,
        promise,
        prepare,
        mount: mount3,
        destroy: () => {
          this.roots.delete(root);
          node?.destroy();
          this.scheduler.processTasks();
        }
      };
      this.roots.add(root);
      return root;
    }
    destroy() {
      for (let root of this.roots) {
        root.destroy();
      }
      this.pluginManager.destroy();
      this.scheduler.processTasks();
      apps.delete(this);
      this.destroyed = true;
    }
    _handleError(error) {
      throw error;
    }
  };
  async function mount2(C, target, config3 = {}) {
    const app = new App(config3);
    const root = app.createRoot(C, config3);
    return root.mount(target, config3);
  }
  var mainEventHandler = (data, ev, currentTarget) => {
    const { data: _data, modifiers } = filterOutModifiersFromData(data);
    data = _data;
    let stopped = false;
    if (modifiers.length) {
      let selfMode = false;
      const isSelf = ev.target === currentTarget;
      for (const mod of modifiers) {
        switch (mod) {
          case "self":
            selfMode = true;
            if (isSelf) {
              continue;
            } else {
              return stopped;
            }
          case "prevent":
            if (selfMode && isSelf || !selfMode) ev.preventDefault();
            continue;
          case "stop":
            if (selfMode && isSelf || !selfMode) ev.stopPropagation();
            stopped = true;
            continue;
        }
      }
    }
    if (Object.hasOwnProperty.call(data, 0)) {
      const handler = data[0];
      if (typeof handler !== "function") {
        throw new OwlError(`Invalid handler (expected a function, received: '${handler}')`);
      }
      let node = data[1] ? data[1].__owl__ : null;
      if (node ? node.status === STATUS.MOUNTED : true) {
        handler(data[1], ev);
      }
    }
    return stopped;
  };
  function onWillStart(fn) {
    const scope = useScope();
    scope.willStart.push(scope.decorate(fn, "onWillStart"));
  }
  function onWillUpdateProps(fn) {
    const scope = getComponentScope();
    function swapped(s, nextProps) {
      return fn.call(this, nextProps, s);
    }
    scope.willUpdateProps.push(scope.decorate(swapped, "onWillUpdateProps"));
  }
  function onMounted(fn) {
    const scope = getComponentScope();
    scope.mounted.push(scope.decorate(fn, "onMounted"));
  }
  function onWillPatch(fn) {
    const scope = getComponentScope();
    scope.willPatch.unshift(scope.decorate(fn, "onWillPatch"));
  }
  function onPatched(fn) {
    const scope = getComponentScope();
    scope.patched.push(scope.decorate(fn, "onPatched"));
  }
  function onWillUnmount(fn) {
    const scope = getComponentScope();
    scope.willUnmount.unshift(scope.decorate(fn, "onWillUnmount"));
  }
  function onWillDestroy(fn) {
    const scope = useScope();
    scope.onDestroy(scope.decorate(fn, "onWillDestroy"));
  }
  function onError(callback) {
    const scope = getComponentScope();
    let handlers = nodeErrorHandlers.get(scope);
    if (!handlers) {
      handlers = [];
      nodeErrorHandlers.set(scope, handlers);
    }
    handlers.push(callback.bind(scope.component));
  }
  function componentType() {
    return constructorType(Component);
  }
  var types2 = { ...types, component: componentType };
  function validateDefaults(schema) {
    const validation = {};
    if (Array.isArray(schema)) {
      for (const key of schema) {
        if (key.endsWith("?")) {
          validation[key] = types2.any();
        }
      }
    } else {
      for (const key in schema) {
        if (key.endsWith("?")) {
          validation[key] = schema[key];
        }
      }
    }
    return types2.strictObject(validation);
  }
  function props(type, defaults) {
    const node = getComponentScope();
    const { app, componentName } = node;
    if (defaults) {
      node.defaultProps = Object.assign(node.defaultProps || {}, defaults);
    }
    function getProp(key) {
      if (node.props[key] === void 0 && defaults) {
        return defaults[key];
      }
      return node.props[key];
    }
    const result = /* @__PURE__ */ Object.create(null);
    function applyPropGetters(keys) {
      for (const key of keys) {
        Reflect.defineProperty(result, key, {
          enumerable: true,
          get: getProp.bind(null, key)
        });
      }
    }
    if (type) {
      const keys = (Array.isArray(type) ? type : Object.keys(type)).map(
        (key) => key.endsWith("?") ? key.slice(0, -1) : key
      );
      applyPropGetters(keys);
      if (app.dev) {
        if (defaults) {
          assertType(defaults, validateDefaults(type), `Invalid component default props (${componentName})`);
        }
        const validation = types2.object(type);
        assertType(node.props, validation, `Invalid component props (${componentName})`);
        node.willUpdateProps.push((np) => {
          assertType(np, validation, `Invalid component props (${componentName})`);
        });
      }
    } else {
      const getKeys = (props2) => {
        const keys2 = [];
        for (const k in props2) {
          if (k.charCodeAt(0) !== 1) {
            keys2.push(k);
          }
        }
        if (defaults) {
          for (const k in defaults) {
            if (!(k in props2)) {
              keys2.push(k);
            }
          }
        }
        return keys2;
      };
      let keys = getKeys(node.props);
      applyPropGetters(keys);
      node.willUpdateProps.push((np) => {
        for (const key of keys) {
          Reflect.deleteProperty(result, key);
        }
        keys = getKeys(np);
        applyPropGetters(keys);
      });
    }
    return result;
  }
  var ErrorBoundary = class extends Component {
    static template = xml`
    <t t-if="this.props.error()">
      <t t-call-slot="fallback"/>
    </t>
    <t t-else="">
      <t t-call-slot="default"/>
    </t>
  `;
    props = props({ "error?": types2.signal() }, { error: signal(null) });
    setup() {
      onError((e) => this.props.error.set(e));
    }
  };
  function useEffect(fn) {
    onWillDestroy(effect(fn));
  }
  function useListener(target, eventName, handler, eventParams) {
    if (typeof target === "function") {
      useEffect(() => {
        const el = target();
        if (el) {
          el.addEventListener(eventName, handler, eventParams);
          return () => el.removeEventListener(eventName, handler, eventParams);
        }
        return;
      });
    } else {
      target.addEventListener(eventName, handler, eventParams);
      onWillDestroy(() => target.removeEventListener(eventName, handler, eventParams));
    }
  }
  function useApp() {
    return useScope().app;
  }
  var PortalContent = class extends Component {
    static template = xml`<t t-call-slot="default"/>`;
  };
  var Portal = class extends Component {
    static template = xml``;
    props = props({
      slots: types2.object(["default"]),
      target: types2.or([types2.string(), types2.signal(types2.instanceOf(HTMLElement)), types2.instanceOf(HTMLElement)])
    });
    setup() {
      const portalNode = this.__owl__;
      const app = portalNode.app;
      const slots = this.props.slots;
      let root = null;
      const tearDown = () => {
        if (root) {
          root.destroy();
          root = null;
        }
      };
      useEffect(() => {
        const target = resolveTarget(this.props.target);
        if (!target) {
          return;
        }
        root = app.createRoot(PortalContent, { props: { slots } });
        root.node.pluginManager = portalNode.pluginManager;
        nodeErrorHandlers.set(root.node, [forwardErrorToParent(portalNode)]);
        root.mount(target);
        return tearDown;
      });
      onWillDestroy(tearDown);
    }
  };
  function resolveTarget(target) {
    if (typeof target === "function") {
      target = target();
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target instanceof HTMLElement) {
      return target;
    }
    return null;
  }
  var SuspenseHost = class extends Component {
    static template = xml`<t t-call-slot="default"/>`;
  };
  var Suspense = class extends Component {
    static template = xml`
    <t t-if="!this.prepared()">
      <t t-call-slot="fallback"/>
    </t>
  `;
    props = props({ slots: types2.object(["default", "fallback?"]) });
    prepared = signal(false);
    mounted = signal(false);
    subRootMounted = false;
    setup() {
      const suspenseNode = this.__owl__;
      const root = suspenseNode.app.createRoot(SuspenseHost, {
        props: { slots: this.props.slots }
      });
      root.node.pluginManager = suspenseNode.pluginManager;
      nodeErrorHandlers.set(root.node, [forwardErrorToParent(suspenseNode)]);
      root.prepare().then(() => this.prepared.set(true));
      const fiber = root.node.fiber;
      if (fiber && fiber.counter === 0) {
        this.prepared.set(true);
      }
      onMounted(() => this.mounted.set(true));
      useEffect(() => {
        if (this.subRootMounted || !this.prepared() || !this.mounted()) {
          return;
        }
        this.subRootMounted = true;
        const anchor = suspenseNode.bdom.firstNode();
        root.mount(anchor.parentElement, { afterNode: anchor });
      });
      onWillDestroy(() => root.destroy());
    }
  };
  function prop(key, type, ...args) {
    const node = getComponentScope();
    const hasDefault = args.length > 0;
    const propValue = node.props[key];
    if (node.app.dev) {
      if (type !== void 0 && (!hasDefault || propValue !== void 0)) {
        assertType(propValue, type, `Invalid prop '${key}' in '${node.componentName}'`);
      }
      node.willUpdateProps.push((nextProps) => {
        if (nextProps[key] !== node.props[key]) {
          throw new OwlError(
            `Prop '${key}' changed in component '${node.componentName}'. Props declared with \`prop()\` are static and should not change. If the prop is a signal, pass the same signal reference (its inner value may change).`
          );
        }
      });
    }
    return propValue === void 0 && hasDefault ? args[0] : propValue;
  }
  function plugin(pluginType) {
    const scope = useScope();
    const manager = scope instanceof ComponentNode ? scope.pluginManager : scope;
    let plugin2 = manager.getPluginById(pluginType.id);
    if (!plugin2) {
      if (scope instanceof PluginManager) {
        plugin2 = manager.startPlugin(pluginType);
      } else {
        throw new OwlError(`Unknown plugin "${pluginType.id}"`);
      }
    }
    return plugin2;
  }
  function config2(name, type) {
    const scope = useScope();
    if (!(scope instanceof PluginManager)) {
      throw new OwlError("Expected to be in a plugin scope");
    }
    if (scope.app.dev && type) {
      assertType(scope.config, types2.object({ [name]: type }), "Config does not match the type");
    }
    return scope.config[name.endsWith("?") ? name.slice(0, -1) : name];
  }
  function providePlugins(pluginConstructors, config3) {
    const node = getComponentScope();
    const manager = new PluginManager(node.app, { parent: node.pluginManager, config: config3 });
    node.pluginManager = manager;
    onWillDestroy(() => manager.destroy());
    startPlugins(manager, pluginConstructors);
    if (manager.status < STATUS.MOUNTED) {
      onWillStart(() => manager.ready);
    }
  }
  config.shouldNormalizeDom = false;
  config.mainEventHandler = mainEventHandler;
  var blockDom = {
    config,
    // bdom entry points
    mount,
    patch,
    remove,
    // bdom block types
    list,
    multi,
    text,
    toggler,
    createBlock,
    html
  };
  var __info__ = {
    version: App.version,
    date: "2026-05-21T09:26:06.769Z",
    hash: "64885dbf",
    url: "https://github.com/odoo/owl"
  };

  // ../owl-compiler/dist/owl-compiler.es.js
  var RESERVED_WORDS = "true,false,NaN,null,undefined,debugger,console,window,in,instanceof,new,function,return,eval,void,Math,RegExp,Array,Object,Date,__globals__".split(
    ","
  );
  var WORD_REPLACEMENT = Object.assign(/* @__PURE__ */ Object.create(null), {
    and: "&&",
    or: "||",
    gt: ">",
    gte: ">=",
    lt: "<",
    lte: "<="
  });
  var STATIC_TOKEN_MAP = Object.assign(/* @__PURE__ */ Object.create(null), {
    "{": "LEFT_BRACE",
    "}": "RIGHT_BRACE",
    "[": "LEFT_BRACKET",
    "]": "RIGHT_BRACKET",
    ":": "COLON",
    ",": "COMMA",
    "(": "LEFT_PAREN",
    ")": "RIGHT_PAREN"
  });
  var OPERATORS = "...,.,===,==,+,!==,!=,!,||,&&,>=,>,<=,<,?,-,*,/,%,typeof ,=>,=,;,in ,new ,|,&,^,~".split(",");
  var tokenizeString = function(expr) {
    let s = expr[0];
    let start = s;
    if (s !== "'" && s !== '"' && s !== "`") {
      return false;
    }
    let i = 1;
    let cur;
    while (expr[i] && expr[i] !== start) {
      cur = expr[i];
      s += cur;
      if (cur === "\\") {
        i++;
        cur = expr[i];
        if (!cur) {
          throw new OwlError("Invalid expression");
        }
        s += cur;
      }
      i++;
    }
    if (expr[i] !== start) {
      throw new OwlError("Invalid expression");
    }
    s += start;
    if (start === "`") {
      return {
        type: "TEMPLATE_STRING",
        value: s,
        replace(replacer) {
          return s.replace(/\$\{(.*?)\}/g, (match, group) => {
            return "${" + replacer(group) + "}";
          });
        }
      };
    }
    return { type: "VALUE", value: s };
  };
  var tokenizeNumber = function(expr) {
    let s = expr[0];
    if (s && s.match(/[0-9]/)) {
      let i = 1;
      while (expr[i] && expr[i].match(/[0-9]|\./)) {
        s += expr[i];
        i++;
      }
      return { type: "VALUE", value: s };
    } else {
      return false;
    }
  };
  var tokenizeSymbol = function(expr) {
    let s = expr[0];
    if (s && s.match(/[a-zA-Z_\$]/)) {
      let i = 1;
      while (expr[i] && expr[i].match(/[\w\$]/)) {
        s += expr[i];
        i++;
      }
      if (s in WORD_REPLACEMENT) {
        return { type: "OPERATOR", value: WORD_REPLACEMENT[s], size: s.length };
      }
      return { type: "SYMBOL", value: s };
    } else {
      return false;
    }
  };
  var tokenizeStatic = function(expr) {
    const char = expr[0];
    if (char && char in STATIC_TOKEN_MAP) {
      return { type: STATIC_TOKEN_MAP[char], value: char };
    }
    return false;
  };
  var tokenizeOperator = function(expr) {
    for (let op of OPERATORS) {
      if (expr.startsWith(op)) {
        return { type: "OPERATOR", value: op };
      }
    }
    return false;
  };
  var TOKENIZERS = [
    tokenizeString,
    tokenizeNumber,
    tokenizeOperator,
    tokenizeSymbol,
    tokenizeStatic
  ];
  function tokenize(expr) {
    const result = [];
    let token = true;
    let error;
    let current = expr;
    try {
      while (token) {
        current = current.trim();
        if (current) {
          for (let tokenizer of TOKENIZERS) {
            token = tokenizer(current);
            if (token) {
              result.push(token);
              current = current.slice(token.size || token.value.length);
              break;
            }
          }
        } else {
          token = false;
        }
      }
    } catch (e) {
      error = e;
    }
    if (current.length || error) {
      throw new OwlError(`Tokenizer error: could not tokenize \`${expr}\``);
    }
    return result;
  }
  var isLeftSeparator = (token) => token && (token.type === "LEFT_BRACE" || token.type === "COMMA");
  var isRightSeparator = (token) => token && (token.type === "RIGHT_BRACE" || token.type === "COMMA");
  var paddedValues = /* @__PURE__ */ new Map([["in ", " in "]]);
  function processExpr(expr, seededLocals) {
    const scopeStack2 = [];
    if (seededLocals?.size) {
      scopeStack2.push({ vars: seededLocals, depth: -Infinity });
    }
    const tokens = tokenize(expr);
    let i = 0;
    let stack = [];
    let topLevelArrowIndex = -1;
    function isLocal(name) {
      return scopeStack2.some((s) => s.vars.has(name));
    }
    while (i < tokens.length) {
      let token = tokens[i];
      let prevToken = tokens[i - 1];
      let nextToken = tokens[i + 1];
      let groupType = stack[stack.length - 1];
      switch (token.type) {
        case "LEFT_BRACE":
        case "LEFT_BRACKET":
        case "LEFT_PAREN":
          stack.push(token.type);
          break;
        case "RIGHT_BRACE":
        case "RIGHT_BRACKET":
        case "RIGHT_PAREN":
          stack.pop();
          while (scopeStack2.length > 0 && stack.length < scopeStack2[scopeStack2.length - 1].depth) {
            scopeStack2.pop();
          }
          break;
      }
      let isVar = token.type === "SYMBOL" && !RESERVED_WORDS.includes(token.value);
      if (isVar) {
        if (prevToken) {
          if (groupType === "LEFT_BRACE" && isLeftSeparator(prevToken) && isRightSeparator(nextToken)) {
            tokens.splice(i + 1, 0, { type: "COLON", value: ":" }, { ...token });
            nextToken = tokens[i + 1];
          }
          if (prevToken.type === "OPERATOR" && prevToken.value === ".") {
            isVar = false;
          } else if (prevToken.type === "LEFT_BRACE" || prevToken.type === "COMMA") {
            if (nextToken && nextToken.type === "COLON") {
              isVar = false;
            }
          }
        }
      }
      if (token.type === "TEMPLATE_STRING") {
        const currentLocals = /* @__PURE__ */ new Set();
        for (const scope of scopeStack2) {
          for (const v of scope.vars) currentLocals.add(v);
        }
        token.value = token.replace((expr2) => compileExpr(expr2, currentLocals));
      }
      if (nextToken && nextToken.type === "OPERATOR" && nextToken.value === "=>") {
        const newScope = /* @__PURE__ */ new Set();
        if (stack.length === 0) {
          topLevelArrowIndex = i + 1;
        }
        if (token.type === "RIGHT_PAREN") {
          let j = i - 1;
          while (j > 0 && tokens[j].type !== "LEFT_PAREN") {
            if (tokens[j].type === "SYMBOL" && tokens[j].originalValue) {
              newScope.add(tokens[j].originalValue);
              tokens[j].value = `_${tokens[j].originalValue}`;
              tokens[j].isLocal = true;
            }
            j--;
          }
        } else {
          newScope.add(token.value);
        }
        scopeStack2.push({ vars: newScope, depth: stack.length });
      }
      if (isVar) {
        token.varName = token.value;
        if (!isLocal(token.value)) {
          token.originalValue = token.value;
          token.value = `ctx['${token.value}']`;
        } else {
          token.value = `_${token.value}`;
          token.isLocal = true;
        }
      }
      i++;
    }
    let freeVariables = null;
    if (topLevelArrowIndex !== -1) {
      freeVariables = [];
      const seen = /* @__PURE__ */ new Set();
      for (let i2 = topLevelArrowIndex + 1; i2 < tokens.length; i2++) {
        const t = tokens[i2];
        if (t.varName && !t.isLocal && t.varName !== "this" && !seen.has(t.varName)) {
          seen.add(t.varName);
          freeVariables.push(t.varName);
        }
      }
    }
    const compiled = tokens.map((t) => paddedValues.get(t.value) || t.value).join("");
    return { expr: compiled, freeVariables };
  }
  function compileExpr(expr, seededLocals) {
    return processExpr(expr, seededLocals).expr;
  }
  var INTERP_REGEXP = /\{\{.*?\}\}|\#\{.*?\}/g;
  function replaceDynamicParts(s, replacer) {
    let matches = s.match(INTERP_REGEXP);
    if (matches && matches[0].length === s.length) {
      return `(${replacer(s.slice(2, matches[0][0] === "{" ? -2 : -1))})`;
    }
    let r = s.replace(
      INTERP_REGEXP,
      (s2) => "${" + replacer(s2.slice(2, s2[0] === "{" ? -2 : -1)) + "}"
    );
    return "`" + r + "`";
  }
  function interpolate(s) {
    return replaceDynamicParts(s, compileExpr);
  }
  function parseXML(xml2) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml2, "text/xml");
    if (doc.getElementsByTagName("parsererror").length) {
      let msg = "Invalid XML in template.";
      const parsererrorText = doc.getElementsByTagName("parsererror")[0].textContent;
      if (parsererrorText) {
        msg += "\nThe parser has produced the following error message:\n" + parsererrorText;
        const re = /\d+/g;
        const firstMatch = re.exec(parsererrorText);
        if (firstMatch) {
          const lineNumber = Number(firstMatch[0]);
          const line = xml2.split("\n")[lineNumber - 1];
          const secondMatch = re.exec(parsererrorText);
          if (line && secondMatch) {
            const columnIndex = Number(secondMatch[0]) - 1;
            if (line[columnIndex]) {
              msg += `
The error might be located at xml line ${lineNumber} column ${columnIndex}
${line}
${"-".repeat(columnIndex - 1)}^`;
            }
          }
        }
      }
      throw new OwlError(msg);
    }
    return doc;
  }
  var ASTType = {
    Text: 0,
    DomNode: 2,
    Multi: 3,
    TIf: 4,
    TSet: 5,
    TCall: 6,
    TOut: 7,
    TForEach: 8,
    TKey: 9,
    TComponent: 10,
    TDebug: 11,
    TLog: 12,
    TCallSlot: 13,
    TCallBlock: 14,
    TTranslation: 15,
    TTranslationContext: 16
  };
  var ForEachNoFlag = {
    First: 1,
    Last: 2,
    Index: 4,
    Value: 8
  };
  var cache2 = /* @__PURE__ */ new WeakMap();
  function parse(xml2, customDir) {
    const ctx = {
      inPreTag: false,
      customDirectives: customDir
    };
    if (typeof xml2 === "string") {
      const elem = parseXML(`<t>${xml2}</t>`).firstChild;
      return _parse(elem, ctx);
    }
    let ast = cache2.get(xml2);
    if (!ast) {
      ast = _parse(xml2.cloneNode(true), ctx);
      cache2.set(xml2, ast);
    }
    return ast;
  }
  function _parse(xml2, ctx) {
    normalizeXML(xml2);
    return parseNode(xml2, ctx) || { type: ASTType.Text, value: "" };
  }
  function parseNode(node, ctx) {
    if (!(node instanceof Element)) {
      return parseTextCommentNode(node, ctx);
    }
    return parseTCustom(node, ctx) || parseTDebugLog(node, ctx) || parseTForEach(node, ctx) || parseTIf(node, ctx) || parseTTranslation(node, ctx) || parseTTranslationContext(node, ctx) || parseTCall(node, ctx) || parseTCallBlock(node, ctx) || parseTKey(node, ctx) || parseTOutNode(node, ctx) || parseTCallSlot(node, ctx) || parseComponent(node, ctx) || parseDOMNode(node, ctx) || parseTSetNode(node, ctx) || parseTNode(node, ctx);
  }
  function parseTNode(node, ctx) {
    if (node.tagName !== "t") {
      return null;
    }
    return parseChildNodes(node, ctx);
  }
  var lineBreakRE = /[\r\n]/;
  function parseTextCommentNode(node, ctx) {
    if (node.nodeType === Node.TEXT_NODE) {
      let value = node.textContent || "";
      if (!ctx.inPreTag && lineBreakRE.test(value) && !value.trim()) {
        return null;
      }
      return { type: ASTType.Text, value };
    }
    return null;
  }
  function parseTCustom(node, ctx) {
    if (!ctx.customDirectives) {
      return null;
    }
    const nodeAttrsNames = node.getAttributeNames();
    for (let attr of nodeAttrsNames) {
      if (attr === "t-custom" || attr === "t-custom-") {
        throw new OwlError("Missing custom directive name with t-custom directive");
      }
      if (attr.startsWith("t-custom-")) {
        const directiveName = attr.split(".")[0].slice(9);
        const customDirective = ctx.customDirectives[directiveName];
        if (!customDirective) {
          throw new OwlError(`Custom directive "${directiveName}" is not defined`);
        }
        const value = node.getAttribute(attr);
        const modifiers = attr.split(".").slice(1);
        node.removeAttribute(attr);
        try {
          customDirective(node, value, modifiers);
        } catch (error) {
          throw new OwlError(
            `Custom directive "${directiveName}" throw the following error: ${error}`
          );
        }
        return parseNode(node, ctx);
      }
    }
    return null;
  }
  function parseTDebugLog(node, ctx) {
    if (node.hasAttribute("t-debug")) {
      node.removeAttribute("t-debug");
      const content = parseNode(node, ctx);
      const ast = {
        type: ASTType.TDebug,
        content
      };
      if (content?.hasNoRepresentation) {
        ast.hasNoRepresentation = true;
      }
      return ast;
    }
    if (node.hasAttribute("t-log")) {
      const expr = node.getAttribute("t-log");
      node.removeAttribute("t-log");
      const content = parseNode(node, ctx);
      const ast = {
        type: ASTType.TLog,
        expr,
        content
      };
      if (content?.hasNoRepresentation) {
        ast.hasNoRepresentation = true;
      }
      return ast;
    }
    return null;
  }
  var ROOT_SVG_TAGS = /* @__PURE__ */ new Set(["svg", "g", "path"]);
  function parseDOMNode(node, ctx) {
    const { tagName } = node;
    const dynamicTag = node.getAttribute("t-tag");
    node.removeAttribute("t-tag");
    if (tagName === "t" && !dynamicTag) {
      return null;
    }
    if (tagName.startsWith("block-")) {
      throw new OwlError(`Invalid tag name: '${tagName}'`);
    }
    ctx = Object.assign({}, ctx);
    if (tagName === "pre") {
      ctx.inPreTag = true;
    }
    let ns = !ctx.nameSpace && ROOT_SVG_TAGS.has(tagName) ? "http://www.w3.org/2000/svg" : null;
    const ref2 = node.getAttribute("t-ref");
    node.removeAttribute("t-ref");
    const nodeAttrsNames = node.getAttributeNames();
    let attrs = null;
    let attrsTranslationCtx = null;
    let on = null;
    let model = null;
    for (let attr of nodeAttrsNames) {
      const value = node.getAttribute(attr);
      if (attr === "t-on" || attr === "t-on-") {
        throw new OwlError("Missing event name with t-on directive");
      }
      if (attr.startsWith("t-on-")) {
        on = on || {};
        on[attr.slice(5)] = value;
      } else if (attr.startsWith("t-model")) {
        if (!["input", "select", "textarea"].includes(tagName)) {
          throw new OwlError(
            "The t-model directive only works with <input>, <textarea> and <select>"
          );
        }
        const typeAttr = node.getAttribute("type");
        const isInput = tagName === "input";
        const isSelect = tagName === "select";
        const isCheckboxInput = isInput && typeAttr === "checkbox";
        const isRadioInput = isInput && typeAttr === "radio";
        const hasTrimMod = attr.includes(".trim");
        const hasLazyMod = hasTrimMod || attr.includes(".lazy");
        const hasNumberMod = attr.includes(".number");
        const hasProxyMod = attr.includes(".proxy");
        const eventType = isRadioInput ? "click" : isSelect || hasLazyMod ? "change" : "input";
        model = {
          expr: value,
          targetAttr: isCheckboxInput ? "checked" : "value",
          specialInitTargetAttr: isRadioInput ? "checked" : null,
          eventType,
          hasDynamicChildren: false,
          shouldTrim: hasTrimMod,
          shouldNumberize: hasNumberMod,
          isProxy: hasProxyMod
        };
        if (isSelect) {
          ctx = Object.assign({}, ctx);
          ctx.tModelInfo = model;
        }
      } else if (attr.startsWith("block-")) {
        throw new OwlError(`Invalid attribute: '${attr}'`);
      } else if (attr === "xmlns") {
        ns = value;
      } else if (attr.startsWith("t-translation-context-")) {
        const attrName = attr.slice(22);
        attrsTranslationCtx = attrsTranslationCtx || {};
        attrsTranslationCtx[attrName] = value;
      } else if (attr !== "t-name") {
        if (attr.startsWith("t-") && !attr.startsWith("t-att")) {
          throw new OwlError(`Unknown QWeb directive: '${attr}'`);
        }
        const tModel = ctx.tModelInfo;
        if (tModel && ["t-att-value", "t-attf-value"].includes(attr)) {
          tModel.hasDynamicChildren = true;
        }
        attrs = attrs || {};
        attrs[attr] = value;
      }
    }
    if (ns) {
      ctx.nameSpace = ns;
    }
    const children = parseChildren(node, ctx);
    return {
      type: ASTType.DomNode,
      tag: tagName,
      dynamicTag,
      attrs,
      attrsTranslationCtx,
      on,
      ref: ref2,
      content: children,
      model,
      ns
    };
  }
  function parseTOutNode(node, ctx) {
    if (!node.hasAttribute("t-out") && !node.hasAttribute("t-esc")) {
      return null;
    }
    if (node.hasAttribute("t-esc")) {
      console.warn(
        `t-esc has been deprecated in favor of t-out. If the value to render is not wrapped by the "markup" function, it will be escaped`
      );
    }
    const expr = node.getAttribute("t-out") || node.getAttribute("t-esc");
    node.removeAttribute("t-out");
    node.removeAttribute("t-esc");
    const tOut = { type: ASTType.TOut, expr, body: null };
    const ref2 = node.getAttribute("t-ref");
    node.removeAttribute("t-ref");
    const ast = parseNode(node, ctx);
    if (!ast) {
      return tOut;
    }
    if (ast.type === ASTType.DomNode) {
      tOut.body = ast.content.length ? ast.content : null;
      return {
        ...ast,
        ref: ref2,
        content: [tOut]
      };
    }
    return tOut;
  }
  function parseTForEach(node, ctx) {
    if (!node.hasAttribute("t-foreach")) {
      return null;
    }
    const html2 = node.outerHTML;
    const collection = node.getAttribute("t-foreach");
    node.removeAttribute("t-foreach");
    const elem = node.getAttribute("t-as") || "";
    node.removeAttribute("t-as");
    const key = node.getAttribute("t-key");
    if (!key) {
      throw new OwlError(
        `"Directive t-foreach should always be used with a t-key!" (expression: t-foreach="${collection}" t-as="${elem}")`
      );
    }
    node.removeAttribute("t-key");
    const body = parseNode(node, ctx);
    if (!body) {
      return null;
    }
    const hasNoTCall = !html2.includes("t-call");
    let noFlags = 0;
    if (hasNoTCall && !html2.includes(`${elem}_first`)) noFlags |= ForEachNoFlag.First;
    if (hasNoTCall && !html2.includes(`${elem}_last`)) noFlags |= ForEachNoFlag.Last;
    if (hasNoTCall && !html2.includes(`${elem}_index`)) noFlags |= ForEachNoFlag.Index;
    if (hasNoTCall && !html2.includes(`${elem}_value`)) noFlags |= ForEachNoFlag.Value;
    return {
      type: ASTType.TForEach,
      collection,
      elem,
      body,
      key,
      noFlags
    };
  }
  function parseTKey(node, ctx) {
    if (!node.hasAttribute("t-key")) {
      return null;
    }
    const key = node.getAttribute("t-key");
    node.removeAttribute("t-key");
    const content = parseNode(node, ctx);
    if (!content) {
      return null;
    }
    const ast = {
      type: ASTType.TKey,
      expr: key,
      content
    };
    if (content.hasNoRepresentation) {
      ast.hasNoRepresentation = true;
    }
    return ast;
  }
  function parseTCall(node, ctx) {
    if (!node.hasAttribute("t-call")) {
      return null;
    }
    if (node.tagName !== "t") {
      throw new OwlError(
        `Directive 't-call' can only be used on <t> nodes (used on a <${node.tagName}>)`
      );
    }
    const subTemplate = node.getAttribute("t-call");
    const context = node.getAttribute("t-call-context");
    node.removeAttribute("t-call");
    node.removeAttribute("t-call-context");
    let attrs = null;
    let attrsTranslationCtx = null;
    for (let attributeName of node.getAttributeNames()) {
      const value = node.getAttribute(attributeName);
      if (attributeName.startsWith("t-translation-context-")) {
        const attrName = attributeName.slice(22);
        attrsTranslationCtx = attrsTranslationCtx || {};
        attrsTranslationCtx[attrName] = value;
      } else {
        attrs = attrs || {};
        attrs[attributeName] = value;
      }
    }
    const body = parseChildNodes(node, ctx);
    return {
      type: ASTType.TCall,
      name: subTemplate,
      attrs,
      attrsTranslationCtx,
      body,
      context
    };
  }
  function parseTCallBlock(node, ctx) {
    if (!node.hasAttribute("t-call-block")) {
      return null;
    }
    const name = node.getAttribute("t-call-block");
    return {
      type: ASTType.TCallBlock,
      name
    };
  }
  function parseTIf(node, ctx) {
    if (!node.hasAttribute("t-if")) {
      return null;
    }
    const condition = node.getAttribute("t-if");
    node.removeAttribute("t-if");
    const content = parseNode(node, ctx) || { type: ASTType.Text, value: "" };
    let nextElement = node.nextElementSibling;
    const tElifs = [];
    while (nextElement && nextElement.hasAttribute("t-elif")) {
      const condition2 = nextElement.getAttribute("t-elif");
      nextElement.removeAttribute("t-elif");
      const tElif = parseNode(nextElement, ctx);
      const next = nextElement.nextElementSibling;
      nextElement.remove();
      nextElement = next;
      if (tElif) {
        tElifs.push({ condition: condition2, content: tElif });
      }
    }
    let tElse = null;
    if (nextElement && nextElement.hasAttribute("t-else")) {
      nextElement.removeAttribute("t-else");
      tElse = parseNode(nextElement, ctx);
      nextElement.remove();
    }
    return {
      type: ASTType.TIf,
      condition,
      content,
      tElif: tElifs.length ? tElifs : null,
      tElse
    };
  }
  function parseTSetNode(node, ctx) {
    if (!node.hasAttribute("t-set")) {
      return null;
    }
    const name = node.getAttribute("t-set");
    const value = node.getAttribute("t-value") || null;
    const defaultValue = node.innerHTML === node.textContent ? node.textContent || null : null;
    let body = null;
    if (node.textContent !== node.innerHTML) {
      body = parseChildren(node, ctx);
    }
    return { type: ASTType.TSet, name, value, defaultValue, body, hasNoRepresentation: true };
  }
  var directiveErrorMap = /* @__PURE__ */ new Map([
    [
      "t-ref",
      "t-ref is no longer supported on components. Consider exposing only the public part of the component's API through a callback prop."
    ],
    ["t-att", "t-att makes no sense on component: props are already treated as expressions"],
    [
      "t-attf",
      "t-attf is not supported on components: use template strings for string interpolation in props"
    ]
  ]);
  function parseComponent(node, ctx) {
    let name = node.tagName;
    const firstLetter = name[0];
    let isDynamic = node.hasAttribute("t-component");
    if (isDynamic && name !== "t") {
      throw new OwlError(
        `Directive 't-component' can only be used on <t> nodes (used on a <${name}>)`
      );
    }
    if (!(firstLetter === firstLetter.toUpperCase() || isDynamic)) {
      return null;
    }
    if (isDynamic) {
      name = node.getAttribute("t-component");
      node.removeAttribute("t-component");
    }
    const dynamicProps = node.getAttribute("t-props");
    node.removeAttribute("t-props");
    const defaultSlotScope = node.getAttribute("t-slot-scope");
    node.removeAttribute("t-slot-scope");
    let on = null;
    let props2 = null;
    let propsTranslationCtx = null;
    for (let name2 of node.getAttributeNames()) {
      const value = node.getAttribute(name2);
      if (name2.startsWith("t-translation-context-")) {
        const attrName = name2.slice(22);
        propsTranslationCtx = propsTranslationCtx || {};
        propsTranslationCtx[attrName] = value;
      } else if (name2.startsWith("t-")) {
        if (name2.startsWith("t-on-")) {
          on = on || {};
          on[name2.slice(5)] = value;
        } else {
          const message = directiveErrorMap.get(name2.split("-").slice(0, 2).join("-"));
          throw new OwlError(message || `unsupported directive on Component: ${name2}`);
        }
      } else {
        props2 = props2 || {};
        props2[name2] = value;
      }
    }
    let slots = null;
    if (node.hasChildNodes()) {
      const clone = node.cloneNode(true);
      const slotNodes = Array.from(clone.querySelectorAll("[t-set-slot]"));
      for (let slotNode of slotNodes) {
        if (slotNode.tagName !== "t") {
          throw new OwlError(
            `Directive 't-set-slot' can only be used on <t> nodes (used on a <${slotNode.tagName}>)`
          );
        }
        const name2 = slotNode.getAttribute("t-set-slot");
        let el = slotNode.parentElement;
        let isInSubComponent = false;
        while (el && el !== clone) {
          if (el.hasAttribute("t-component") || el.tagName[0] === el.tagName[0].toUpperCase()) {
            isInSubComponent = true;
            break;
          }
          el = el.parentElement;
        }
        if (isInSubComponent || !el) {
          continue;
        }
        slotNode.removeAttribute("t-set-slot");
        slotNode.remove();
        const slotAst = parseNode(slotNode, ctx);
        let on2 = null;
        let attrs = null;
        let attrsTranslationCtx = null;
        let scope = null;
        for (let attributeName of slotNode.getAttributeNames()) {
          const value = slotNode.getAttribute(attributeName);
          if (attributeName === "t-slot-scope") {
            scope = value;
            continue;
          } else if (attributeName.startsWith("t-translation-context-")) {
            const attrName = attributeName.slice(22);
            attrsTranslationCtx = attrsTranslationCtx || {};
            attrsTranslationCtx[attrName] = value;
          } else if (attributeName.startsWith("t-on-")) {
            on2 = on2 || {};
            on2[attributeName.slice(5)] = value;
          } else {
            attrs = attrs || {};
            attrs[attributeName] = value;
          }
        }
        slots = slots || {};
        slots[name2] = { content: slotAst, on: on2, attrs, attrsTranslationCtx, scope };
      }
      const defaultContent = parseChildNodes(clone, ctx);
      slots = slots || {};
      if (defaultContent && !slots.default) {
        slots.default = {
          content: defaultContent,
          on: null,
          attrs: null,
          attrsTranslationCtx: null,
          scope: defaultSlotScope
        };
      }
    }
    return {
      type: ASTType.TComponent,
      name,
      isDynamic,
      dynamicProps,
      props: props2,
      propsTranslationCtx,
      slots,
      on
    };
  }
  function parseTCallSlot(node, ctx) {
    if (!node.hasAttribute("t-call-slot") && !node.hasAttribute("t-slot")) {
      return null;
    }
    if (node.hasAttribute("t-slot")) {
      console.warn(`t-slot has been renamed t-call-slot.`);
    }
    const name = node.getAttribute("t-call-slot") || node.getAttribute("t-slot");
    node.removeAttribute("t-call-slot");
    node.removeAttribute("t-slot");
    let attrs = null;
    let attrsTranslationCtx = null;
    let on = null;
    for (let attributeName of node.getAttributeNames()) {
      const value = node.getAttribute(attributeName);
      if (attributeName.startsWith("t-on-")) {
        on = on || {};
        on[attributeName.slice(5)] = value;
      } else if (attributeName.startsWith("t-translation-context-")) {
        const attrName = attributeName.slice(22);
        attrsTranslationCtx = attrsTranslationCtx || {};
        attrsTranslationCtx[attrName] = value;
      } else {
        attrs = attrs || {};
        attrs[attributeName] = value;
      }
    }
    return {
      type: ASTType.TCallSlot,
      name,
      attrs,
      attrsTranslationCtx,
      on,
      defaultContent: parseChildNodes(node, ctx)
    };
  }
  function wrapInTTranslationAST(r) {
    const ast = { type: ASTType.TTranslation, content: r };
    if (r?.hasNoRepresentation) {
      ast.hasNoRepresentation = true;
    }
    return ast;
  }
  function parseTTranslation(node, ctx) {
    if (node.getAttribute("t-translation") !== "off") {
      return null;
    }
    node.removeAttribute("t-translation");
    const result = parseNode(node, ctx);
    if (result?.type === ASTType.Multi) {
      const children = result.content.map(wrapInTTranslationAST);
      return makeASTMulti(children);
    }
    return wrapInTTranslationAST(result);
  }
  function wrapInTTranslationContextAST(r, translationCtx) {
    const ast = {
      type: ASTType.TTranslationContext,
      content: r,
      translationCtx
    };
    if (r?.hasNoRepresentation) {
      ast.hasNoRepresentation = true;
    }
    return ast;
  }
  function parseTTranslationContext(node, ctx) {
    const translationCtx = node.getAttribute("t-translation-context");
    if (!translationCtx) {
      return null;
    }
    node.removeAttribute("t-translation-context");
    const result = parseNode(node, ctx);
    if (result?.type === ASTType.Multi) {
      const children = result.content.map((c) => wrapInTTranslationContextAST(c, translationCtx));
      return makeASTMulti(children);
    }
    return wrapInTTranslationContextAST(result, translationCtx);
  }
  function parseChildren(node, ctx) {
    const children = [];
    for (let child of node.childNodes) {
      const childAst = parseNode(child, ctx);
      if (childAst) {
        if (childAst.type === ASTType.Multi) {
          children.push(...childAst.content);
        } else {
          children.push(childAst);
        }
      }
    }
    return children;
  }
  function makeASTMulti(children) {
    const ast = { type: ASTType.Multi, content: children };
    if (children.every((c) => c.hasNoRepresentation)) {
      ast.hasNoRepresentation = true;
    }
    return ast;
  }
  function parseChildNodes(node, ctx) {
    const children = parseChildren(node, ctx);
    switch (children.length) {
      case 0:
        return null;
      case 1:
        return children[0];
      default:
        return makeASTMulti(children);
    }
  }
  function normalizeTIf(el) {
    let tbranch = el.querySelectorAll("[t-elif], [t-else]");
    for (let i = 0, ilen = tbranch.length; i < ilen; i++) {
      let node = tbranch[i];
      let prevElem = node.previousElementSibling;
      let pattr = (name) => prevElem.getAttribute(name);
      let nattr = (name) => +!!node.getAttribute(name);
      if (prevElem && (pattr("t-if") || pattr("t-elif"))) {
        if (pattr("t-foreach")) {
          throw new OwlError(
            "t-if cannot stay at the same level as t-foreach when using t-elif or t-else"
          );
        }
        if (["t-if", "t-elif", "t-else"].map(nattr).reduce(function(a, b) {
          return a + b;
        }) > 1) {
          throw new OwlError("Only one conditional branching directive is allowed per node");
        }
        let textNode;
        while ((textNode = node.previousSibling) !== prevElem) {
          if (textNode.nodeValue.trim().length && textNode.nodeType !== 8) {
            throw new OwlError("text is not allowed between branching directives");
          }
          textNode.remove();
        }
      } else {
        throw new OwlError(
          "t-elif and t-else directives must be preceded by a t-if or t-elif directive"
        );
      }
    }
  }
  function normalizeTOut(el) {
    const elements = [...el.querySelectorAll(`[t-out]`)].filter(
      (el2) => el2.tagName[0] === el2.tagName[0].toUpperCase() || el2.hasAttribute("t-component")
    );
    for (const el2 of elements) {
      if (el2.childNodes.length) {
        throw new OwlError(`Cannot have t-out on a component that already has content`);
      }
      const value = el2.getAttribute("t-out");
      el2.removeAttribute("t-out");
      const t = el2.ownerDocument.createElement("t");
      if (value != null) {
        t.setAttribute("t-out", value);
      }
      el2.appendChild(t);
    }
  }
  function normalizeXML(el) {
    normalizeTIf(el);
    normalizeTOut(el);
  }
  var zero = /* @__PURE__ */ Symbol("zero");
  var whitespaceRE = /\s+/g;
  var xmlDoc;
  if (typeof document !== "undefined") {
    xmlDoc = document.implementation.createDocument(null, null, null);
  }
  var MODS = /* @__PURE__ */ new Set(["stop", "capture", "prevent", "self", "synthetic", "passive"]);
  var nextDataIds = {};
  function generateId(prefix = "") {
    nextDataIds[prefix] = (nextDataIds[prefix] || 0) + 1;
    return prefix + nextDataIds[prefix];
  }
  function isProp(tag, key) {
    switch (tag) {
      case "input":
        return key === "checked" || key === "indeterminate" || key === "value" || key === "readonly" || key === "readOnly" || key === "disabled";
      case "option":
        return key === "selected" || key === "disabled";
      case "textarea":
        return key === "value" || key === "readonly" || key === "readOnly" || key === "disabled";
      case "select":
        return key === "value" || key === "disabled";
      case "button":
      case "optgroup":
        return key === "disabled";
    }
    return false;
  }
  function toStringExpression(str) {
    return `\`${str.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$\{/, "\\${")}\``;
  }
  var BlockDescription = class _BlockDescription {
    static nextBlockId = 1;
    varName;
    blockName;
    dynamicTagName = null;
    isRoot = false;
    hasDynamicChildren = false;
    children = [];
    data = [];
    dom;
    currentDom;
    childNumber = 0;
    target;
    type;
    parentVar = "";
    id;
    constructor(target, type) {
      this.id = _BlockDescription.nextBlockId++;
      this.varName = "b" + this.id;
      this.blockName = "block" + this.id;
      this.target = target;
      this.type = type;
    }
    insertData(str, prefix = "d") {
      const id = generateId(prefix);
      this.target.addLine(`let ${id} = ${str};`);
      return this.data.push(id) - 1;
    }
    insert(dom) {
      if (this.currentDom) {
        this.currentDom.appendChild(dom);
      } else {
        this.dom = dom;
      }
    }
    generateExpr(expr) {
      if (this.type === "block") {
        const hasChildren = this.children.length;
        let params = this.data.length ? `[${this.data.join(", ")}]` : hasChildren ? "[]" : "";
        if (hasChildren) {
          params += ", [" + this.children.map((c) => c.varName).join(", ") + "]";
        }
        if (this.dynamicTagName) {
          return `toggler(${this.dynamicTagName}, ${this.blockName}(${this.dynamicTagName})(${params}))`;
        }
        return `${this.blockName}(${params})`;
      } else if (this.type === "list") {
        return `list(c_block${this.id})`;
      }
      return expr;
    }
    asXmlString() {
      const t = xmlDoc.createElement("t");
      t.appendChild(this.dom);
      return t.innerHTML;
    }
  };
  function createContext2(parentCtx, params) {
    return Object.assign(
      {
        block: null,
        index: 0,
        forceNewBlock: true,
        translate: parentCtx.translate,
        translationCtx: parentCtx.translationCtx,
        tKeyExpr: null,
        nameSpace: parentCtx.nameSpace,
        tModelSelectedExpr: parentCtx.tModelSelectedExpr
      },
      params
    );
  }
  var CodeTarget = class {
    name;
    indentLevel = 0;
    loopLevel = 0;
    loopCtxVars = [];
    tSetVars = /* @__PURE__ */ new Map();
    code = [];
    hasRoot = false;
    deferReturn = false;
    needsScopeProtection = false;
    on;
    constructor(name, on) {
      this.name = name;
      this.on = on || null;
    }
    addLine(line, idx) {
      const prefix = new Array(this.indentLevel + 2).join("  ");
      if (idx === void 0) {
        this.code.push(prefix + line);
      } else {
        this.code.splice(idx, 0, prefix + line);
      }
    }
    generateCode() {
      let result = [];
      result.push(`function ${this.name}(ctx, node, key = "") {`);
      if (this.needsScopeProtection) {
        result.push(`  ctx = Object.create(ctx);`);
      }
      for (let line of this.code) {
        result.push(line);
      }
      if (!this.hasRoot) {
        result.push(`return text('');`);
      }
      result.push(`}`);
      return result.join("\n  ");
    }
    currentKey(ctx) {
      let key = this.loopLevel ? `key${this.loopLevel}` : "key";
      if (ctx.tKeyExpr) {
        key = `${ctx.tKeyExpr} + ${key}`;
      }
      return key;
    }
  };
  var TRANSLATABLE_ATTRS = [
    "alt",
    "aria-label",
    "aria-placeholder",
    "aria-roledescription",
    "aria-valuetext",
    "label",
    "placeholder",
    "title"
  ];
  var translationRE = /^(\s*)([\s\S]+?)(\s*)$/;
  var CodeGenerator = class {
    blocks = [];
    nextBlockId = 1;
    isDebug = false;
    targets = [];
    target = new CodeTarget("template");
    templateName;
    dev;
    translateFn;
    translatableAttributes = TRANSLATABLE_ATTRS;
    ast;
    staticDefs = [];
    slotNames = /* @__PURE__ */ new Set();
    helpers = /* @__PURE__ */ new Set();
    constructor(ast, options) {
      this.translateFn = options.translateFn || ((s) => s);
      if (options.translatableAttributes) {
        const attrs = new Set(TRANSLATABLE_ATTRS);
        for (let attr of options.translatableAttributes) {
          if (attr.startsWith("-")) {
            attrs.delete(attr.slice(1));
          } else {
            attrs.add(attr);
          }
        }
        this.translatableAttributes = [...attrs];
      }
      this.dev = options.dev || false;
      this.ast = ast;
      this.templateName = options.name;
      if (options.name) {
        if (options.name.startsWith("__")) {
          this.target.name = options.name;
        } else {
          this.target.name = `template_${options.name.replace(/[^a-zA-Z0-9_$]/g, "_")}`;
        }
      }
      if (options.hasGlobalValues) {
        this.helpers.add("__globals__");
      }
    }
    generateCode() {
      const ast = this.ast;
      this.isDebug = ast.type === ASTType.TDebug;
      BlockDescription.nextBlockId = 1;
      nextDataIds = {};
      this.compileAST(ast, {
        block: null,
        index: 0,
        forceNewBlock: false,
        translate: true,
        translationCtx: "",
        tKeyExpr: null
      });
      let mainCode = [`  let { text, createBlock, list, multi, html, toggler } = bdom;`];
      if (this.helpers.size) {
        mainCode.push(`let { ${[...this.helpers].join(", ")} } = helpers;`);
      }
      if (this.templateName) {
        mainCode.push(`// Template name: "${this.templateName}"`);
      }
      for (let { id, expr } of this.staticDefs) {
        mainCode.push(`const ${id} = ${expr};`);
      }
      if (this.blocks.length) {
        mainCode.push(``);
        for (let block of this.blocks) {
          if (block.dom) {
            let xmlString = toStringExpression(block.asXmlString());
            if (block.dynamicTagName) {
              xmlString = xmlString.replace(/^`<\w+/, `\`<\${tag || '${block.dom.nodeName}'}`);
              xmlString = xmlString.replace(/\w+>`$/, `\${tag || '${block.dom.nodeName}'}>\``);
              mainCode.push(`let ${block.blockName} = tag => createBlock(${xmlString});`);
            } else {
              mainCode.push(`let ${block.blockName} = createBlock(${xmlString});`);
            }
          }
        }
      }
      if (this.targets.length) {
        for (let fn of this.targets) {
          mainCode.push("");
          mainCode = mainCode.concat(fn.generateCode());
        }
      }
      mainCode.push("");
      mainCode = mainCode.concat("return " + this.target.generateCode());
      const code = mainCode.join("\n  ");
      if (this.isDebug) {
        const msg = `[Owl Debug]
${code}`;
        console.log(msg);
      }
      return code;
    }
    compileInNewTarget(prefix, ast, ctx, on) {
      const name = generateId(prefix);
      const initialTarget = this.target;
      const target = new CodeTarget(name, on);
      this.targets.push(target);
      this.target = target;
      this.compileAST(ast, createContext2(ctx));
      this.target = initialTarget;
      return name;
    }
    addLine(line, idx) {
      this.target.addLine(line, idx);
    }
    define(varName, expr) {
      this.addLine(`const ${varName} = ${expr};`);
    }
    insertAnchor(block, index = block.children.length) {
      const tag = `block-child-${index}`;
      const anchor = xmlDoc.createElement(tag);
      block.insert(anchor);
    }
    createBlock(parentBlock, type, ctx) {
      const hasRoot = this.target.hasRoot;
      const block = new BlockDescription(this.target, type);
      if (!hasRoot) {
        this.target.hasRoot = true;
        block.isRoot = true;
      }
      if (parentBlock) {
        parentBlock.children.push(block);
        if (parentBlock.type === "list") {
          block.parentVar = `c_block${parentBlock.id}`;
        }
      }
      return block;
    }
    insertBlock(expression, block, ctx) {
      let blockExpr = block.generateExpr(expression);
      if (block.parentVar) {
        let key = this.target.currentKey(ctx);
        this.helpers.add("withKey");
        this.addLine(`${block.parentVar}[${ctx.index}] = withKey(${blockExpr}, ${key});`);
        return;
      }
      if (ctx.tKeyExpr) {
        blockExpr = `toggler(${ctx.tKeyExpr}, ${blockExpr})`;
      }
      if (block.isRoot && !this.target.deferReturn) {
        if (this.target.on) {
          blockExpr = this.wrapWithEventCatcher(blockExpr, this.target.on);
        }
        this.addLine(`return ${blockExpr};`);
      } else {
        this.define(block.varName, blockExpr);
      }
    }
    translate(str, translationCtx) {
      const match = translationRE.exec(str);
      return match[1] + this.translateFn(match[2], translationCtx) + match[3];
    }
    /**
     * @returns the newly created block name, if any
     */
    compileAST(ast, ctx) {
      switch (ast.type) {
        case ASTType.Text:
          return this.compileText(ast, ctx);
        case ASTType.DomNode:
          return this.compileTDomNode(ast, ctx);
        case ASTType.TOut:
          return this.compileTOut(ast, ctx);
        case ASTType.TIf:
          return this.compileTIf(ast, ctx);
        case ASTType.TForEach:
          return this.compileTForeach(ast, ctx);
        case ASTType.TKey:
          return this.compileTKey(ast, ctx);
        case ASTType.Multi:
          return this.compileMulti(ast, ctx);
        case ASTType.TCall:
          return this.compileTCall(ast, ctx);
        case ASTType.TCallBlock:
          return this.compileTCallBlock(ast, ctx);
        case ASTType.TSet:
          return this.compileTSet(ast, ctx);
        case ASTType.TComponent:
          return this.compileComponent(ast, ctx);
        case ASTType.TDebug:
          return this.compileDebug(ast, ctx);
        case ASTType.TLog:
          return this.compileLog(ast, ctx);
        case ASTType.TCallSlot:
          return this.compileTCallSlot(ast, ctx);
        case ASTType.TTranslation:
          return this.compileTTranslation(ast, ctx);
        case ASTType.TTranslationContext:
          return this.compileTTranslationContext(ast, ctx);
      }
    }
    compileDebug(ast, ctx) {
      this.addLine(`debugger;`);
      if (ast.content) {
        return this.compileAST(ast.content, ctx);
      }
      return null;
    }
    compileLog(ast, ctx) {
      this.addLine(`console.log(${compileExpr(ast.expr)});`);
      if (ast.content) {
        return this.compileAST(ast.content, ctx);
      }
      return null;
    }
    compileText(ast, ctx) {
      let { block, forceNewBlock } = ctx;
      let value = ast.value;
      if (value && ctx.translate !== false) {
        value = this.translate(value, ctx.translationCtx);
      }
      if (!ctx.inPreTag) {
        value = value.replace(whitespaceRE, " ");
      }
      if (!block || forceNewBlock) {
        block = this.createBlock(block, "text", ctx);
        this.insertBlock(`text(${toStringExpression(value)})`, block, {
          ...ctx,
          forceNewBlock: forceNewBlock && !block
        });
      } else {
        const createFn = ast.type === ASTType.Text ? xmlDoc.createTextNode : xmlDoc.createComment;
        block.insert(createFn.call(xmlDoc, value));
      }
      return block.varName;
    }
    generateHandlerCode(rawEvent, handler) {
      const modifiers = rawEvent.split(".").slice(1).map((m) => {
        if (!MODS.has(m)) {
          throw new OwlError(`Unknown event modifier: '${m}'`);
        }
        return `"${m}"`;
      });
      let modifiersCode = "";
      if (modifiers.length) {
        modifiersCode = `${modifiers.join(",")}, `;
      }
      const compiled = compileExpr(handler);
      if (!compiled.trim()) {
        return `[${modifiersCode}, ctx]`;
      }
      let hoistedExpr;
      const arrowMatch = compiled.match(/^(\([^)]*\))\s*=>/);
      const bareArrowMatch = !arrowMatch && compiled.match(/^([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=>/);
      if (arrowMatch) {
        const inner = arrowMatch[1].slice(1, -1).trim();
        const rest = compiled.slice(arrowMatch[0].length);
        hoistedExpr = inner ? `(ctx,${inner})=>${rest}` : `(ctx)=>${rest}`;
      } else if (bareArrowMatch) {
        const rest = compiled.slice(bareArrowMatch[0].length);
        hoistedExpr = `(ctx,${bareArrowMatch[1]})=>${rest}`;
      } else {
        this.helpers.add("callHandler");
        hoistedExpr = `(ctx, ev) => callHandler(${compiled}, ctx, ev)`;
      }
      const id = generateId("hdlr_fn");
      this.staticDefs.push({ id, expr: hoistedExpr });
      return `[${modifiersCode}${id}, ctx]`;
    }
    compileTDomNode(ast, ctx) {
      let { block, forceNewBlock } = ctx;
      const isNewBlock = !block || forceNewBlock || ast.dynamicTag !== null || ast.ns;
      let codeIdx = this.target.code.length;
      if (isNewBlock) {
        if ((ast.dynamicTag || ctx.tKeyExpr || ast.ns) && ctx.block) {
          this.insertAnchor(ctx.block);
        }
        block = this.createBlock(block, "block", ctx);
        this.blocks.push(block);
        if (ast.dynamicTag) {
          const tagExpr = generateId("tag");
          this.define(tagExpr, compileExpr(ast.dynamicTag));
          block.dynamicTagName = tagExpr;
        }
      }
      const attrs = {};
      for (let key in ast.attrs) {
        let expr, attrName;
        if (key.startsWith("t-attf")) {
          expr = interpolate(ast.attrs[key]);
          const idx = block.insertData(expr, "attr");
          attrName = key.slice(7);
          attrs["block-attribute-" + idx] = attrName;
        } else if (key.startsWith("t-att")) {
          attrName = key === "t-att" ? null : key.slice(6);
          expr = compileExpr(ast.attrs[key]);
          if (attrName && isProp(ast.tag, attrName)) {
            if (attrName === "readonly") {
              attrName = "readOnly";
            }
            if (attrName === "value") {
              expr = `new String((${expr}) === 0 ? 0 : ((${expr}) || ""))`;
            } else {
              expr = `new Boolean(${expr})`;
            }
            const idx = block.insertData(expr, "prop");
            attrs[`block-property-${idx}`] = attrName;
          } else {
            const idx = block.insertData(expr, "attr");
            if (key === "t-att") {
              attrs[`block-attributes`] = String(idx);
            } else {
              attrs[`block-attribute-${idx}`] = attrName;
            }
          }
        } else if (this.translatableAttributes.includes(key)) {
          const attrTranslationCtx = ast.attrsTranslationCtx?.[key] || ctx.translationCtx;
          attrs[key] = this.translateFn(ast.attrs[key], attrTranslationCtx);
        } else {
          expr = `"${ast.attrs[key]}"`;
          attrName = key;
          attrs[key] = ast.attrs[key];
        }
        if (attrName === "value" && ctx.tModelSelectedExpr) {
          let selectedId = block.insertData(`${ctx.tModelSelectedExpr} === ${expr}`, "attr");
          attrs[`block-attribute-${selectedId}`] = "selected";
        }
      }
      let tModelSelectedExpr;
      if (ast.model) {
        const {
          hasDynamicChildren,
          expr,
          eventType,
          shouldNumberize,
          shouldTrim,
          targetAttr,
          specialInitTargetAttr,
          isProxy
        } = ast.model;
        let readExpr;
        let writeExpr;
        if (isProxy) {
          const expression = compileExpr(expr);
          readExpr = expression;
          writeExpr = (value) => `${expression} = ${value}`;
        } else {
          const exprId = generateId("expr");
          const expression = compileExpr(expr);
          this.helpers.add("modelExpr");
          this.define(exprId, `modelExpr(${expression})`);
          readExpr = `${exprId}()`;
          writeExpr = (value) => `${exprId}.set(${value})`;
        }
        let idx;
        if (specialInitTargetAttr) {
          let targetExpr = targetAttr in attrs && `'${attrs[targetAttr]}'`;
          if (!targetExpr && ast.attrs) {
            const dynamicTgExpr = ast.attrs[`t-att-${targetAttr}`];
            if (dynamicTgExpr) {
              targetExpr = compileExpr(dynamicTgExpr);
            }
          }
          idx = block.insertData(`${readExpr} === ${targetExpr}`, "prop");
          attrs[`block-property-${idx}`] = specialInitTargetAttr;
        } else if (hasDynamicChildren) {
          const bValueId = generateId("bValue");
          tModelSelectedExpr = `${bValueId}`;
          this.define(tModelSelectedExpr, readExpr);
        } else {
          idx = block.insertData(readExpr, "prop");
          attrs[`block-property-${idx}`] = targetAttr;
        }
        this.helpers.add("toNumber");
        let valueCode = `ev.target.${targetAttr}`;
        valueCode = shouldTrim ? `${valueCode}.trim()` : valueCode;
        valueCode = shouldNumberize ? `toNumber(${valueCode})` : valueCode;
        const handler = `[(ctx, ev) => { ${writeExpr(valueCode)}; }, ctx]`;
        idx = block.insertData(handler, "hdlr");
        attrs[`block-handler-${idx}`] = eventType;
      }
      for (let ev in ast.on) {
        const name = this.generateHandlerCode(ev, ast.on[ev]);
        const idx = block.insertData(name, "hdlr");
        attrs[`block-handler-${idx}`] = ev;
      }
      if (ast.ref) {
        const refExpr = compileExpr(ast.ref);
        this.helpers.add("createRef");
        const setRefStr = `createRef(${refExpr})`;
        const idx = block.insertData(setRefStr, "ref");
        attrs["block-ref"] = String(idx);
      }
      const nameSpace = ast.ns || ctx.nameSpace;
      const dom = nameSpace ? xmlDoc.createElementNS(nameSpace, ast.tag) : xmlDoc.createElement(ast.tag);
      for (const [attr, val] of Object.entries(attrs)) {
        if (!(attr === "class" && val === "")) {
          dom.setAttribute(attr, val);
        }
      }
      block.insert(dom);
      if (ast.content.length) {
        const initialDom = block.currentDom;
        block.currentDom = dom;
        const children = ast.content;
        for (let i = 0; i < children.length; i++) {
          const child = ast.content[i];
          const subCtx = createContext2(ctx, {
            block,
            index: block.childNumber,
            forceNewBlock: false,
            tKeyExpr: ctx.tKeyExpr,
            nameSpace,
            tModelSelectedExpr,
            inPreTag: ctx.inPreTag || ast.tag === "pre"
          });
          this.compileAST(child, subCtx);
        }
        block.currentDom = initialDom;
      }
      if (isNewBlock) {
        this.insertBlock(`${block.blockName}(ddd)`, block, ctx);
        if (block.children.length && block.hasDynamicChildren) {
          const code = this.target.code;
          const children = block.children.slice();
          let current = children.shift();
          for (let i = codeIdx; i < code.length; i++) {
            if (code[i].trimStart().startsWith(`const ${current.varName} `)) {
              code[i] = code[i].replace(`const ${current.varName}`, current.varName);
              current = children.shift();
              if (!current) break;
            }
          }
          this.addLine(`let ${block.children.map((c) => c.varName).join(", ")};`, codeIdx);
        }
      }
      return block.varName;
    }
    compileZero() {
      this.helpers.add("zero");
      const isMultiple = this.slotNames.has(zero);
      this.slotNames.add(zero);
      let key = this.target.loopLevel ? `key${this.target.loopLevel}` : "key";
      if (isMultiple) {
        key = this.generateComponentKey(key);
      }
      return `ctx[zero]?.(node, ${key}) || text("")`;
    }
    compileTOut(ast, ctx) {
      let { block } = ctx;
      if (block) {
        this.insertAnchor(block);
      }
      block = this.createBlock(block, "html", ctx);
      let blockStr;
      if (ast.expr === "0") {
        blockStr = this.compileZero();
      } else if (ast.body) {
        let bodyValue = null;
        bodyValue = BlockDescription.nextBlockId;
        const subCtx = createContext2(ctx);
        this.compileAST({ type: ASTType.Multi, content: ast.body }, subCtx);
        this.helpers.add("safeOutput");
        blockStr = `safeOutput(${compileExpr(ast.expr)}, b${bodyValue})`;
      } else {
        this.helpers.add("safeOutput");
        blockStr = `safeOutput(${compileExpr(ast.expr)})`;
      }
      this.insertBlock(blockStr, block, ctx);
      return block.varName;
    }
    compileTIfBranch(content, block, ctx) {
      this.target.indentLevel++;
      let childN = block.children.length;
      this.compileAST(content, createContext2(ctx, { block, index: ctx.index }));
      if (block.children.length > childN) {
        this.insertAnchor(block, childN);
      }
      this.target.indentLevel--;
    }
    compileTIf(ast, ctx, nextNode) {
      let { block, forceNewBlock } = ctx;
      const codeIdx = this.target.code.length;
      const isNewBlock = !block || block.type !== "multi" && forceNewBlock;
      if (block) {
        block.hasDynamicChildren = true;
      }
      if (!block || block.type !== "multi" && forceNewBlock) {
        block = this.createBlock(block, "multi", ctx);
      }
      this.addLine(`if (${compileExpr(ast.condition)}) {`);
      this.compileTIfBranch(ast.content, block, ctx);
      if (ast.tElif) {
        for (let clause of ast.tElif) {
          this.addLine(`} else if (${compileExpr(clause.condition)}) {`);
          this.compileTIfBranch(clause.content, block, ctx);
        }
      }
      if (ast.tElse) {
        this.addLine(`} else {`);
        this.compileTIfBranch(ast.tElse, block, ctx);
      }
      this.addLine("}");
      if (isNewBlock) {
        if (block.children.length) {
          const code = this.target.code;
          const children = block.children.slice();
          let current = children.shift();
          for (let i = codeIdx; i < code.length; i++) {
            if (code[i].trimStart().startsWith(`const ${current.varName} `)) {
              code[i] = code[i].replace(`const ${current.varName}`, current.varName);
              current = children.shift();
              if (!current) break;
            }
          }
          this.addLine(`let ${block.children.map((c) => c.varName).join(", ")};`, codeIdx);
        }
        const args = block.children.map((c) => c.varName).join(", ");
        this.insertBlock(`multi([${args}])`, block, ctx);
      }
      return block.varName;
    }
    compileTForeach(ast, ctx) {
      let { block } = ctx;
      if (block) {
        this.insertAnchor(block);
      }
      block = this.createBlock(block, "list", ctx);
      this.target.loopLevel++;
      const loopVar = `i${this.target.loopLevel}`;
      const ctxVar = generateId("ctx");
      this.addLine(`const ${ctxVar} = ctx;`);
      this.target.loopCtxVars.push(ctxVar);
      const vals = `v_block${block.id}`;
      const keys = `k_block${block.id}`;
      const l = `l_block${block.id}`;
      const c = `c_block${block.id}`;
      this.helpers.add("prepareList");
      this.define(`[${keys}, ${vals}, ${l}, ${c}]`, `prepareList(${compileExpr(ast.collection)});`);
      if (this.dev) {
        this.define(`keys${block.id}`, `new Set()`);
      }
      this.addLine(`for (let ${loopVar} = 0; ${loopVar} < ${l}; ${loopVar}++) {`);
      this.target.indentLevel++;
      this.addLine(`let ctx = Object.create(${ctxVar});`);
      this.addLine(`ctx[\`${ast.elem}\`] = ${keys}[${loopVar}];`);
      if (!(ast.noFlags & ForEachNoFlag.First)) {
        this.addLine(`ctx[\`${ast.elem}_first\`] = ${loopVar} === 0;`);
      }
      if (!(ast.noFlags & ForEachNoFlag.Last)) {
        this.addLine(`ctx[\`${ast.elem}_last\`] = ${loopVar} === ${keys}.length - 1;`);
      }
      if (!(ast.noFlags & ForEachNoFlag.Index)) {
        this.addLine(`ctx[\`${ast.elem}_index\`] = ${loopVar};`);
      }
      if (!(ast.noFlags & ForEachNoFlag.Value)) {
        this.addLine(`ctx[\`${ast.elem}_value\`] = ${vals}[${loopVar}];`);
      }
      this.define(`key${this.target.loopLevel}`, ast.key ? compileExpr(ast.key) : loopVar);
      if (this.dev) {
        this.helpers.add("OwlError");
        this.addLine(
          `if (keys${block.id}.has(String(key${this.target.loopLevel}))) { throw new OwlError(\`Got duplicate key in t-foreach: \${key${this.target.loopLevel}}\`)}`
        );
        this.addLine(`keys${block.id}.add(String(key${this.target.loopLevel}));`);
      }
      const subCtx = createContext2(ctx, { block, index: loopVar });
      this.compileAST(ast.body, subCtx);
      this.target.indentLevel--;
      this.target.loopLevel--;
      this.target.loopCtxVars.pop();
      this.addLine(`}`);
      this.insertBlock("l", block, ctx);
      return block.varName;
    }
    compileTKey(ast, ctx) {
      const tKeyExpr = generateId("tKey_");
      this.define(tKeyExpr, compileExpr(ast.expr));
      ctx = createContext2(ctx, {
        tKeyExpr,
        block: ctx.block,
        index: ctx.index
      });
      return this.compileAST(ast.content, ctx);
    }
    compileMulti(ast, ctx) {
      let { block, forceNewBlock } = ctx;
      const isNewBlock = !block || forceNewBlock;
      let codeIdx = this.target.code.length;
      if (isNewBlock) {
        const n = ast.content.filter((c) => !c.hasNoRepresentation).length;
        let result = null;
        if (n <= 1) {
          const shouldDefer = !this.target.hasRoot && ast.content[ast.content.length - 1].hasNoRepresentation;
          if (shouldDefer) {
            this.target.deferReturn = true;
          }
          for (let child of ast.content) {
            const blockName = this.compileAST(child, ctx);
            result = result || blockName;
          }
          if (shouldDefer) {
            this.target.deferReturn = false;
            this.addLine(`return ${result};`);
          }
          return result;
        }
        block = this.createBlock(block, "multi", ctx);
      }
      let index = 0;
      for (let i = 0, l = ast.content.length; i < l; i++) {
        const child = ast.content[i];
        const forceNewBlock2 = !child.hasNoRepresentation;
        const subCtx = createContext2(ctx, {
          block,
          index,
          forceNewBlock: forceNewBlock2
        });
        this.compileAST(child, subCtx);
        if (forceNewBlock2) {
          index++;
        }
      }
      if (isNewBlock) {
        if (block.hasDynamicChildren && block.children.length) {
          const code = this.target.code;
          const children = block.children.slice();
          let current = children.shift();
          for (let i = codeIdx; i < code.length; i++) {
            if (code[i].trimStart().startsWith(`const ${current.varName} `)) {
              code[i] = code[i].replace(`const ${current.varName}`, current.varName);
              current = children.shift();
              if (!current) break;
            }
          }
          this.addLine(`let ${block.children.map((c) => c.varName).join(", ")};`, codeIdx);
        }
        const args = block.children.map((c) => c.varName).join(", ");
        this.insertBlock(`multi([${args}])`, block, ctx);
      }
      return block.varName;
    }
    compileTCall(ast, ctx) {
      let { block, forceNewBlock } = ctx;
      const attrs = ast.attrs ? this.formatPropObject(ast.attrs, ast.attrsTranslationCtx, ctx.translationCtx) : [];
      const isDynamic = INTERP_REGEXP.test(ast.name);
      const subTemplate = isDynamic ? interpolate(ast.name) : "`" + ast.name + "`";
      if (block && !forceNewBlock) {
        this.insertAnchor(block);
      }
      block = this.createBlock(block, "multi", ctx);
      if (ast.body) {
        const name = this.compileInNewTarget("callBody", ast.body, ctx);
        const zeroStr = generateId("lazyBlock");
        this.define(zeroStr, `${name}.bind(this, ctx)`);
        this.helpers.add("zero");
        attrs.push(`[zero]: ${zeroStr}`);
      }
      let ctxExpr;
      const ctxString = `{${attrs.join(", ")}}`;
      if (ast.context) {
        const dynCtxVar = generateId("ctx");
        this.addLine(`const ${dynCtxVar} = ${compileExpr(ast.context)};`);
        if (ast.attrs) {
          ctxExpr = `Object.assign({}, ${dynCtxVar}, {this: ${dynCtxVar}}${attrs.length ? ", " + ctxString : ""})`;
        } else {
          const thisCtx = `{this: ${dynCtxVar}}`;
          ctxExpr = `Object.assign({}, ${dynCtxVar}, ${thisCtx}${attrs.length ? ", " + ctxString : ""})`;
        }
      } else {
        if (attrs.length === 0) {
          ctxExpr = "ctx";
        } else {
          ctxExpr = `Object.assign(Object.create(ctx), ${ctxString})`;
        }
      }
      const key = this.generateComponentKey();
      this.helpers.add("callTemplate");
      this.insertBlock(`callTemplate(${subTemplate}, this, app, ${ctxExpr}, node, ${key})`, block, {
        ...ctx,
        forceNewBlock: !block
      });
      return block.varName;
    }
    compileTCallBlock(ast, ctx) {
      let { block, forceNewBlock } = ctx;
      if (block) {
        if (!forceNewBlock) {
          this.insertAnchor(block);
        }
      }
      block = this.createBlock(block, "multi", ctx);
      this.insertBlock(compileExpr(ast.name), block, { ...ctx, forceNewBlock: !block });
      return block.varName;
    }
    compileTSet(ast, ctx) {
      const expr = ast.value ? compileExpr(ast.value || "") : "null";
      const isOuterScope = this.target.loopLevel === 0;
      const defLevel = this.target.tSetVars.get(ast.name);
      const isReassignment = defLevel !== void 0 && this.target.loopLevel > defLevel;
      if (ast.body) {
        this.helpers.add("LazyValue");
        const bodyAst = { type: ASTType.Multi, content: ast.body };
        const name = this.compileInNewTarget("value", bodyAst, ctx);
        let key = this.target.currentKey(ctx);
        let value = `new LazyValue(${name}, ctx, this, node, ${key})`;
        value = ast.value ? value ? `withDefault(${expr}, ${value})` : expr : value;
        this.helpers.add("withDefault");
        if (isReassignment) {
          const ctxVar = this.target.loopCtxVars[defLevel];
          this.addLine(`${ctxVar}[\`${ast.name}\`] = ${value};`);
        } else if (isOuterScope) {
          this.target.needsScopeProtection = true;
          this.addLine(`ctx[\`${ast.name}\`] = ${value};`);
          this.target.tSetVars.set(ast.name, 0);
        } else {
          this.addLine(`ctx[\`${ast.name}\`] = ${value};`);
          this.target.tSetVars.set(ast.name, this.target.loopLevel);
        }
      } else {
        let value;
        if (ast.defaultValue) {
          const defaultValue = toStringExpression(
            ctx.translate ? this.translate(ast.defaultValue, ctx.translationCtx) : ast.defaultValue
          );
          if (ast.value) {
            this.helpers.add("withDefault");
            value = `withDefault(${expr}, ${defaultValue})`;
          } else {
            value = defaultValue;
          }
        } else {
          value = expr;
        }
        if (isReassignment) {
          const ctxVar = this.target.loopCtxVars[defLevel];
          this.addLine(`${ctxVar}["${ast.name}"] = ${value};`);
        } else if (isOuterScope) {
          this.target.needsScopeProtection = true;
          this.addLine(`ctx["${ast.name}"] = ${value};`);
          this.target.tSetVars.set(ast.name, 0);
        } else {
          this.addLine(`ctx["${ast.name}"] = ${value};`);
          this.target.tSetVars.set(ast.name, this.target.loopLevel);
        }
      }
      return null;
    }
    generateComponentKey(currentKey = "key") {
      const parts = [generateId("__")];
      for (let i = 0; i < this.target.loopLevel; i++) {
        parts.push(`\${key${i + 1}}`);
      }
      return `${currentKey} + \`${parts.join("__")}\``;
    }
    generateSignalCacheKey() {
      const parts = [generateId("__sig_")];
      for (let i = 0; i < this.target.loopLevel; i++) {
        parts.push(`\${key${i + 1}}`);
      }
      return `\`${parts.join("__")}\``;
    }
    /**
     * Formats a prop name and value into a string suitable to be inserted in the
     * generated code. For example:
     *
     * Name              Value            Result
     * ---------------------------------------------------------
     * "number"          "state"          "number: ctx['state']"
     * "something"       ""               "something: undefined"
     * "some-prop"       "state"          "'some-prop': ctx['state']"
     * "onClick.bind"    "onClick"        "onClick: bind(ctx, ctx['onClick'])"
     */
    formatProp(name, value, attrsTranslationCtx, translationCtx) {
      if (name.endsWith(".translate")) {
        const attrTranslationCtx = attrsTranslationCtx?.[name] || translationCtx;
        value = toStringExpression(this.translateFn(value, attrTranslationCtx));
      } else {
        value = compileExpr(value);
      }
      if (name.includes(".")) {
        let [_name, suffix] = name.split(".");
        name = _name;
        switch (suffix) {
          case "bind":
            value = `(${value}).bind(this)`;
            break;
          case "alike":
          case "translate":
            break;
          default:
            throw new OwlError(`Invalid prop suffix: ${suffix}`);
        }
      }
      name = /^[a-z_]+$/i.test(name) ? name : `'${name}'`;
      return `${name}: ${value || void 0}`;
    }
    formatPropObject(obj, attrsTranslationCtx, translationCtx) {
      return Object.entries(obj).map(
        ([k, v]) => this.formatProp(k, v, attrsTranslationCtx, translationCtx)
      );
    }
    getPropString(props2, dynProps) {
      let propString = `{${props2.join(",")}}`;
      if (dynProps) {
        propString = `Object.assign({}, ${compileExpr(dynProps)}${props2.length ? ", " + propString : ""})`;
      }
      return propString;
    }
    compileComponent(ast, ctx) {
      let { block } = ctx;
      const hasSlotsProp = "slots" in (ast.props || {});
      const props2 = [];
      const propList = [];
      for (let p in ast.props || {}) {
        let [name, suffix] = p.split(".");
        if (suffix === "signal") {
          const compiledValue2 = compileExpr(ast.props[p]);
          const propName2 = /^[a-z_]+$/i.test(name) ? name : `'${name}'`;
          this.helpers.add("toSignal");
          const cacheKey = this.generateSignalCacheKey();
          props2.push(`${propName2}: toSignal(node, ${cacheKey}, ${compiledValue2})`);
          continue;
        }
        if (suffix) {
          props2.push(this.formatProp(p, ast.props[p], ast.propsTranslationCtx, ctx.translationCtx));
          continue;
        }
        const { expr: compiledValue, freeVariables } = processExpr(ast.props[p]);
        const propName = /^[a-z_]+$/i.test(name) ? name : `'${name}'`;
        props2.push(`${propName}: ${compiledValue || void 0}`);
        if (freeVariables) {
          for (const varName of freeVariables) {
            const syntheticKey = `${name}.${varName}`;
            propList.push(`"${syntheticKey}"`);
            props2.push(`"${syntheticKey}": ctx['${varName}']`);
          }
        } else {
          propList.push(`"${name}"`);
        }
      }
      let slotDef = "";
      if (ast.slots) {
        let slotStr = [];
        for (let slotName in ast.slots) {
          const slotAst = ast.slots[slotName];
          const params = [];
          if (slotAst.content) {
            const name = this.compileInNewTarget("slot", slotAst.content, ctx, slotAst.on);
            params.push(`__render: ${name}.bind(this), __ctx: ctx`);
          }
          const scope = ast.slots[slotName].scope;
          if (scope) {
            params.push(`__scope: "${scope}"`);
          }
          if (ast.slots[slotName].attrs) {
            params.push(
              ...this.formatPropObject(
                ast.slots[slotName].attrs,
                ast.slots[slotName].attrsTranslationCtx,
                ctx.translationCtx
              )
            );
          }
          const slotInfo = `{${params.join(", ")}}`;
          slotStr.push(`'${slotName}': ${slotInfo}`);
        }
        slotDef = `{${slotStr.join(", ")}}`;
      }
      if (slotDef && !(ast.dynamicProps || hasSlotsProp)) {
        this.helpers.add("markRaw");
        props2.push(`slots: markRaw(${slotDef})`);
      }
      let propString = this.getPropString(props2, ast.dynamicProps);
      let propVar;
      if (slotDef && (ast.dynamicProps || hasSlotsProp) || this.dev) {
        propVar = generateId("props");
        this.define(propVar, propString);
        propString = propVar;
      }
      if (slotDef && (ast.dynamicProps || hasSlotsProp)) {
        this.helpers.add("markRaw");
        this.addLine(`${propVar}.slots = markRaw(Object.assign(${slotDef}, ${propVar}.slots))`);
      }
      let expr;
      if (ast.isDynamic) {
        expr = generateId("Comp");
        this.define(expr, compileExpr(ast.name));
      } else {
        expr = `\`${ast.name}\``;
      }
      if (block && (ctx.forceNewBlock === false || ctx.tKeyExpr)) {
        this.insertAnchor(block);
      }
      let keyArg = this.generateComponentKey();
      if (ctx.tKeyExpr) {
        keyArg = `${ctx.tKeyExpr} + ${keyArg}`;
      }
      let id = generateId("comp");
      this.helpers.add("createComponent");
      this.staticDefs.push({
        id,
        expr: `createComponent(app, ${ast.isDynamic ? null : expr}, ${!ast.isDynamic}, ${!!ast.slots}, ${!!ast.dynamicProps}, [${propList}])`
      });
      if (ast.isDynamic) {
        keyArg = `(${expr}).name + ${keyArg}`;
      }
      let blockExpr = `${id}(${propString}, ${keyArg}, node, this, ${ast.isDynamic ? expr : null})`;
      if (ast.isDynamic) {
        blockExpr = `toggler(${expr}, ${blockExpr})`;
      }
      if (ast.on) {
        blockExpr = this.wrapWithEventCatcher(blockExpr, ast.on);
      }
      block = this.createBlock(block, "multi", ctx);
      this.insertBlock(blockExpr, block, ctx);
      return block.varName;
    }
    wrapWithEventCatcher(expr, on) {
      this.helpers.add("createCatcher");
      let name = generateId("catcher");
      let spec = {};
      let handlers = [];
      for (let ev in on) {
        let handlerId = generateId("hdlr");
        let idx = handlers.push(handlerId) - 1;
        spec[ev] = idx;
        const handler = this.generateHandlerCode(ev, on[ev]);
        this.define(handlerId, handler);
      }
      this.staticDefs.push({ id: name, expr: `createCatcher(${JSON.stringify(spec)})` });
      return `${name}(${expr}, [${handlers.join(",")}])`;
    }
    compileTCallSlot(ast, ctx) {
      this.helpers.add("callSlot");
      let { block } = ctx;
      let blockString;
      let slotName;
      let dynamic = false;
      let isMultiple = false;
      if (ast.name.match(INTERP_REGEXP)) {
        dynamic = true;
        isMultiple = true;
        slotName = interpolate(ast.name);
      } else {
        slotName = "'" + ast.name + "'";
        isMultiple = isMultiple || this.slotNames.has(ast.name);
        this.slotNames.add(ast.name);
      }
      const attrs = { ...ast.attrs };
      const dynProps = attrs["t-props"];
      delete attrs["t-props"];
      let key = this.target.loopLevel ? `key${this.target.loopLevel}` : "key";
      if (isMultiple) {
        key = this.generateComponentKey(key);
      }
      const props2 = ast.attrs ? this.formatPropObject(attrs, ast.attrsTranslationCtx, ctx.translationCtx) : [];
      const scope = this.getPropString(props2, dynProps);
      if (ast.defaultContent) {
        const name = this.compileInNewTarget("defaultContent", ast.defaultContent, ctx);
        blockString = `callSlot(ctx, node, ${key}, ${slotName}, ${dynamic}, ${scope}, ${name}.bind(this))`;
      } else {
        if (dynamic) {
          let name = generateId("slot");
          this.define(name, slotName);
          blockString = `toggler(${name}, callSlot(ctx, node, ${key}, ${name}, ${dynamic}, ${scope}))`;
        } else {
          blockString = `callSlot(ctx, node, ${key}, ${slotName}, ${dynamic}, ${scope})`;
        }
      }
      if (ast.on) {
        blockString = this.wrapWithEventCatcher(blockString, ast.on);
      }
      if (block) {
        this.insertAnchor(block);
      }
      block = this.createBlock(block, "multi", ctx);
      this.insertBlock(blockString, block, { ...ctx, forceNewBlock: false });
      return block.varName;
    }
    compileTTranslation(ast, ctx) {
      if (ast.content) {
        return this.compileAST(ast.content, Object.assign({}, ctx, { translate: false }));
      }
      return null;
    }
    compileTTranslationContext(ast, ctx) {
      if (ast.content) {
        return this.compileAST(
          ast.content,
          Object.assign({}, ctx, { translationCtx: ast.translationCtx })
        );
      }
      return null;
    }
  };
  function compile(template, options = {
    hasGlobalValues: false
  }) {
    const ast = parse(template, options.customDirectives);
    const codeGenerator = new CodeGenerator(ast, options);
    const code = codeGenerator.generateCode();
    try {
      return new Function("app, bdom, helpers", code);
    } catch (originalError) {
      const { name } = options;
      const nameStr = name ? `template "${name}"` : "anonymous template";
      const err = new OwlError(
        `Failed to compile ${nameStr}: ${originalError.message}

generated code:
function(app, bdom, helpers) {
${code}
}`
      );
      err.cause = originalError;
      throw err;
    }
  }

  // src/index.ts
  TemplateSet.prototype._compileTemplate = function _compileTemplate(name, template) {
    return compile(template, {
      name,
      dev: this.dev,
      translateFn: this.translateFn,
      translatableAttributes: this.translatableAttributes,
      customDirectives: this.customDirectives,
      hasGlobalValues: this.hasGlobalValues
    });
  };
  TemplateSet.prototype._parseXML = function _parseXML(xml2) {
    return parseXML(xml2);
  };
  return __toCommonJS(index_exports);
})();

owl = {...owl};
