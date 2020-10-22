odoo.define('web_editor.jabberwock', (function(require) {
'use strict';
(function (exports, owl) {
    'use strict';

    class Dispatcher {
        constructor(editor) {
            this.__nextHandlerTokenID = 0;
            this.commands = {};
            this.commandHooks = {};
            this.editor = editor;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Call all hooks registred for the command `id`.
         *
         * @param commandId The identifier of the command.
         * @param params The parameters of the command.
         */
        async dispatch(commandId, params = {}) {
            var _a, _b;
            const commands = this.commands[commandId];
            let result;
            if (commands) {
                const [command, context] = this.editor.contextManager.match(commands, params.context);
                if (command) {
                    // Update command arguments with the computed execution context.
                    params = Object.assign(Object.assign({}, params), { context });
                    // Call command handler.
                    result = await command.handler(params);
                }
            }
            else if (commandId[0] !== '@') {
                console.warn(`Command '${commandId}' not found.`);
            }
            await this._dispatchHooks(commandId, params);
            if ((_b = (_a = params.context) === null || _a === void 0 ? void 0 : _a.range) === null || _b === void 0 ? void 0 : _b.temporary) {
                params.context.range.remove();
            }
            return result;
        }
        /**
         * Register all handlers declared in a plugin, and match them with their
         * corresponding command.
         *
         */
        registerCommand(id, impl) {
            if (!this.commands[id]) {
                this.commands[id] = [impl];
            }
            else {
                this.commands[id].push(impl);
            }
        }
        /**
         * Register a callback that will be executed for each `execCommand` call.
         *
         * @param id The identifier of the command to hook.
         * @param hook The callback that will be executed.
         */
        registerCommandHook(id, hook) {
            if (!this.commandHooks[id]) {
                this.commandHooks[id] = [];
            }
            this.commandHooks[id].push(hook);
        }
        /**
         * Remove a callback that will be executed for each `execCommand` call.
         *
         * @param id The identifier of the command to hook.
         * @param hook The callback that will be removed.
         */
        removeCommandHook(id, hook) {
            if (this.commandHooks[id]) {
                const index = this.commandHooks[id].indexOf(hook);
                if (index !== -1) {
                    this.commandHooks[id].splice(index, 1);
                }
            }
        }
        /**
         * Dispatch to all registred `commandHooks`.
         */
        async _dispatchHooks(signal, args) {
            const hooks = this.commandHooks[signal] || [];
            const globalHooks = this.commandHooks['*'] || [];
            for (const hookCallback of [...hooks, ...globalHooks]) {
                await hookCallback(args, signal);
            }
        }
    }

    class JWPlugin {
        constructor(editor, configuration = {}) {
            this.editor = editor;
            this.configuration = configuration;
            this.dependencies = new Map();
            this.loaders = {};
            this.loadables = {};
            this.commands = {};
            this.commandHooks = {};
            // Populate instantiated dependencies.
            for (const Dependency of this.constructor.dependencies) {
                this.dependencies.set(Dependency, editor.plugins.get(Dependency));
            }
        }
        /**
         * Start the plugin. Called when the editor starts.
         */
        async start() {
            // This is where plugins can do asynchronous work when the editor is
            // starting (e.g. retrieve data from a server, render stuff, etc).
        }
        /**
         * Stop the plugin. Called when the editor stops.
         */
        async stop() {
            // This is where plugins can do asynchronous work when the editor is
            // stopping (e.g. save on a server, close connections, etc).
            this.dependencies.clear();
            this.editor = null;
        }
    }
    JWPlugin.dependencies = [];

    var RelativePosition;
    (function (RelativePosition) {
        RelativePosition["BEFORE"] = "BEFORE";
        RelativePosition["AFTER"] = "AFTER";
        RelativePosition["INSIDE"] = "INSIDE";
    })(RelativePosition || (RelativePosition = {}));
    /**
     * Return true if the given node is a leaf in the VDocument, that is a node that
     * has no children.
     *
     * @param node node to check
     */
    function isLeaf(node) {
        return !node.hasChildren();
    }

    /**
     * Creates an instance representing a custom error adapting to the constructor
     * name of the custom error and taking advantage of `captureStackTrace` of V8.
     *
     * Source:
     * http://developer.mozilla.org/docs/JavaScript/Reference/Global_Objects/Error
     */
    class CustomError extends Error {
        constructor(...params) {
            super(...params);
            this.name = this.constructor.name;
            // Maintains proper stack trace for where our error was thrown.
            if (Error.captureStackTrace) {
                // This is only available on V8.
                Error.captureStackTrace(this, this.constructor);
            }
        }
    }
    /**
     * Creates an instance representing an error that occurs when a function only
     * allowed to be called in a specific mode is called in a different mode.
     */
    class StageError extends CustomError {
        constructor(stage, ...params) {
            super(...params);
            this.message = `This operation is only allowed in ${stage} stage.`;
        }
    }
    /**
     * Creates an instance representing an error that occurs when a VNode given as
     * child function parameter is actually not a child of the current VNode.
     */
    class ChildError extends CustomError {
        constructor(thisNode, node, ...params) {
            super(...params);
            this.message = `${node.name} is not a child of ${thisNode.name}`;
        }
    }
    /**
     * Creates an instance representing an error that occurs when an action would
     * violate the atomicity of a VNode.
     */
    class AtomicityError extends CustomError {
        constructor(node, ...params) {
            super(...params);
            this.message = `${node.name} is atomic.`;
        }
    }

    const memoryProxyNotVersionableKey = Symbol('jabberwockMemoryNotVersionable');
    const memoryProxyPramsKey = Symbol('jabberwockMemoryParams');
    const removedItem = Symbol('jabberwockMemoryRemovedItem');
    const symbolVerify = Symbol('jabberwockMemoryVerify');
    /**
     * Creates an instance representing an error that occurs when theyr are any
     * error in the memory feature or with the integration of the memory.
     */
    class MemoryError extends CustomError {
        constructor(message, ...params) {
            super(message, ...params);
            this.message = message || 'Jabberwok error in memory feature';
        }
    }
    class NotVersionableError extends MemoryError {
        constructor() {
            super();
            this.message =
                'You can only link to the memory the instance of VersionableObject, VersionableArray or VersionableSet.' +
                    "\nIf that's not possible, then you can also use makeVersionable method on your custom object." +
                    '\nIf you do not want to make versionable this object, indicate it using MarkNotVersionable method' +
                    '\nPlease read the Jabberwock documentation.';
        }
    }
    class VersionableAllreadyVersionableError extends MemoryError {
        constructor() {
            super();
            this.message =
                'This object was already update and a proxy was create to be versionable.' +
                    '\nPlease use it instead of the source object.';
        }
    }
    class FrozenError extends MemoryError {
        constructor() {
            super();
            this.message =
                'This memory is frozen and immutable.' +
                    '\nYou can not update a memory version who content memory dependencies';
        }
    }

    const classGettersSetters = new WeakMap();
    const rootPrototype = Object.getPrototypeOf({});
    function getPrototypeGettersSetters(obj) {
        let gettersSetters = classGettersSetters.get(obj.constructor);
        if (gettersSetters) {
            return gettersSetters;
        }
        gettersSetters = {
            getters: {},
            setters: {},
        };
        classGettersSetters.set(obj.constructor, gettersSetters);
        obj = Object.getPrototypeOf(obj);
        do {
            const descs = Object.getOwnPropertyDescriptors(obj);
            Object.keys(descs).forEach(propName => {
                const desc = descs[propName];
                if (!gettersSetters.getters[propName] && desc.get) {
                    gettersSetters.getters[propName] = desc.get;
                }
                if (!gettersSetters.setters[propName] && desc.set) {
                    gettersSetters.setters[propName] = desc.set;
                }
            });
        } while ((obj = Object.getPrototypeOf(obj)) && obj !== rootPrototype);
        return gettersSetters;
    }
    const proxyObjectHandler = {
        set(obj, prop, value, proxy) {
            // Object.assign might try to set the value of the paramsKey. We
            // obviously don't want that. Let it think it succeeded (returning false
            // will throw an error, which is not what we want here.)
            if (prop === memoryProxyPramsKey) {
                return true;
            }
            if (prop === symbolVerify) {
                obj[symbolVerify] = value;
                return true;
            }
            const params = obj[memoryProxyPramsKey];
            const memory = params.memory;
            if (!memory && value === removedItem) {
                // "synchronize" the delete
                delete obj[prop];
                return true;
            }
            // if the property is a method of the class or prototype.
            const protoMethod = params.proto.setters[prop];
            if (protoMethod) {
                protoMethod.call(proxy, value);
                return true;
            }
            // if the property is a getter
            const desc = Object.getOwnPropertyDescriptor(obj, prop);
            if (desc === null || desc === void 0 ? void 0 : desc.set) {
                desc.set.call(proxy, value);
                return true;
            }
            _checkVersionable(value);
            // if not linked to memory
            if (!memory) {
                obj[prop] = value;
                return true;
            }
            if (memory.isFrozen()) {
                throw new FrozenError();
            }
            const oldValue = obj[prop];
            // The value is the same, or we are deleting a value that was not
            // already there in the first place.
            if (oldValue === value || (value === removedItem && !(prop in obj))) {
                return true;
            }
            const slice = memory.getSlice();
            let memoryObject = slice[params.ID];
            if (!memoryObject) {
                slice[params.ID] = memoryObject = new params.MemoryType();
            }
            const memoryObjectProps = memoryObject.props;
            let memoryItem = value;
            if (value !== null && typeof value === 'object' && !value[memoryProxyNotVersionableKey]) {
                // if object, the stored value needs to be "converted" (see Set)
                memory.linkToMemory(value);
                const newParams = value && value[memoryProxyPramsKey];
                memoryItem = newParams.ID;
                memory.addSliceProxyParent(newParams.ID, params.ID, prop);
            }
            // if the old value was a versionable as well, sever its link to its parent
            const oldParams = oldValue && typeof oldValue === 'object' && oldValue[memoryProxyPramsKey];
            if (oldParams) {
                memory.deleteSliceProxyParent(oldParams.ID, params.ID, prop);
            }
            if (value === removedItem) {
                memoryObjectProps[prop] = removedItem; // notify that the deletion happened in this slice
                delete obj[prop];
            }
            else {
                memoryObjectProps[prop] = memoryItem;
                obj[prop] = value;
            }
            memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
            return true;
        },
        deleteProperty(obj, prop) {
            // `removedItem` is a marker to notify that there was something here but
            // it got removed
            this.set(obj, prop, removedItem);
            delete obj[prop];
            return true;
        },
    };
    function _proxifyObject(obj) {
        const proxy = new Proxy(obj, proxyObjectHandler);
        obj[memoryProxyPramsKey] = {
            ID: generateVersionableID(),
            linkCallback: linkVersionable,
            synchronize: proxifySyncObject,
            MemoryType: MemoryTypeObject,
            verify: verify,
            proxy: proxy,
            object: obj,
            proto: getPrototypeGettersSetters(obj),
        };
        const keys = Object.keys(obj);
        for (let k = 0, len = keys.length; k < len; k++) {
            const key = keys[k];
            const value = obj[key];
            _stackedProxify(value, newValue => {
                if (newValue !== value) {
                    obj[key] = newValue;
                }
            });
        }
        return proxy;
    }
    function verify(proxy) {
        const params = this;
        const obj = params.object;
        proxy[symbolVerify] = true;
        const value = obj[symbolVerify];
        obj[symbolVerify] = false;
        return value;
    }
    function proxifySyncObject() {
        // Synchronization function
        // Most methods of the "proxy" will call this synchronization function, even
        // if it is not yet linked to a memory !
        const params = this;
        const memory = params.memory;
        const memoryObject = memory.getSliceValue(params.ID);
        const memoryObjectProps = (memoryObject && memoryObject.props) || {};
        // Clear keys that do not exist anymore
        let keys = Object.keys(params.object);
        let key;
        while ((key = keys.pop())) {
            // if the object is not present in this slice or it does not have this key
            if (!(key in memoryObjectProps)) {
                delete params.object[key];
            }
        }
        if (!memoryObject) {
            return;
        }
        // Update values according to what is stored
        keys = Object.keys(memoryObjectProps);
        while ((key = keys.pop())) {
            let value = memoryObjectProps[key];
            if (value instanceof VersionableID) {
                // Convert proxy references to actual proxy
                value = memory.getProxy(value);
            }
            params.object[key] = value;
        }
    }
    function linkVersionable(memory) {
        const params = this;
        params.memory = memory;
        const slice = params.memory.getSlice();
        const obj = params.object;
        const ID = params.ID;
        const keys = Object.keys(obj);
        if (keys.length) {
            const memoryObjectProps = Object.assign({}, obj);
            let key;
            while ((key = keys.pop())) {
                const value = obj[key];
                // Some of the values in the original object may be versionable and
                // need to be converted
                const valueParams = value !== null && typeof value === 'object' && value[memoryProxyPramsKey];
                if (valueParams) {
                    memory.linkToMemory(value);
                    memory.addSliceProxyParent(valueParams.ID, ID, key);
                    memoryObjectProps[key] = valueParams.ID;
                }
            }
            const memoryObject = new params.MemoryType();
            memoryObject.props = memoryObjectProps;
            slice[ID] = memoryObject; // store the "pure" value in memory
        }
        memory.markDirty(ID);
    }
    class VersionableObject {
        constructor(obj) {
            if (obj) {
                const keys = Object.keys(obj);
                let key;
                while ((key = keys.pop())) {
                    this[key] = obj[key];
                }
            }
            return _proxifyObject(this);
        }
    }

    // People can override the set methods. They will be called from the proxy, but
    // sometimes we want to call the true original methods, not the override of the
    // user. This is how we do it.
    const genericSet = new Set();
    const genericSetPrototype = Set.prototype;
    function setPrototype(proxy, obj) {
        do {
            // This function loops on the prototypes of the object. This is what
            // stops it.
            // TODO refactor: while !== genericSetPrototype
            if (obj === genericSetPrototype) {
                break;
            }
            const op = Object.getOwnPropertyNames(obj);
            for (let i = 0; i < op.length; i++) {
                const prop = op[i]; // propName
                if (!proxy[prop]) {
                    proxy[prop] = obj[prop];
                }
            }
        } while ((obj = Object.getPrototypeOf(obj)));
    }
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    function nothing() { }
    class VersionableSet extends Set {
        constructor(params) {
            super();
            let set; // original set (won't be synced, it's just for its method ex: overrides)
            let size = 0;
            if (!params) {
                set = genericSet;
            }
            else if (params instanceof Array) {
                set = genericSet;
                params.forEach(value => {
                    size++;
                    _stackedProxify(value, newValue => {
                        set.add.call(this, newValue);
                    });
                });
            }
            else {
                if (params instanceof VersionableSet) {
                    set = params[memoryProxyPramsKey].object;
                }
                else {
                    set = params;
                }
                params.forEach(value => {
                    size++;
                    _stackedProxify(value, newValue => {
                        set.add.call(this, newValue);
                    });
                });
                setPrototype(this, set);
            }
            this[memoryProxyPramsKey] = {
                ID: generateVersionableID(),
                linkCallback: linkVersionable$1,
                synchronize: nothing,
                MemoryType: MemoryTypeSet,
                verify: (proxy) => proxy === this,
                size: size,
                object: set,
                proxy: this,
            };
        }
        add(item) {
            // For Set specifically, this line will never actually *proxify* per se.
            // It will either work if the item is already proxified, or throw an
            // error if it is not.
            _checkVersionable(item);
            const params = this[memoryProxyPramsKey];
            const memory = params.memory;
            if (memory && memory.isFrozen()) {
                throw new FrozenError();
            }
            const check = this.has(item);
            if (!check) {
                params.object.add.call(this, item);
            }
            if (check || !memory) {
                // Nothing changed. Either the item was already there, or we don't
                // care because we are not linked to memory.
                return this;
            }
            let memoryItem = item;
            if (item !== null && typeof item === 'object' && !item[memoryProxyNotVersionableKey]) {
                // The item is versionable, great, but it is not versioned yet !
                // This call versions it into the memory.
                memory.linkToMemory(item);
                const itemParams = item[memoryProxyPramsKey];
                memoryItem = itemParams.ID;
                memory.addSliceProxyParent(itemParams.ID, params.ID, undefined);
            }
            // Get current slice.
            const slice = memory.getSlice();
            let memorySet = slice[params.ID]; // read the pure value stored in memory
            if (!memorySet) {
                slice[params.ID] = memorySet = new MemoryTypeSet();
                // Mark the set as being modified in this slice (not necesarilly "dirty")
                memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
            }
            // Update the stored changes for this slice
            memorySet.add.add(memoryItem);
            memorySet.delete.delete(memoryItem);
            return this;
        }
        delete(item) {
            const params = this[memoryProxyPramsKey];
            const memory = params.memory;
            if (memory && memory.isFrozen()) {
                throw new FrozenError();
            }
            const check = this.has(item);
            if (check) {
                params.object.delete.call(this, item);
            }
            if (!check || !memory) {
                return check;
            }
            let memoryItem = item;
            const itemParams = item && typeof item === 'object' && item[memoryProxyPramsKey];
            if (itemParams) {
                memoryItem = itemParams.ID;
                memory.deleteSliceProxyParent(itemParams.ID, params.ID, undefined);
            }
            const slice = memory.getSlice();
            let memorySet = slice[params.ID];
            if (!memorySet) {
                slice[params.ID] = memorySet = new MemoryTypeSet();
            }
            memorySet.delete.add(memoryItem);
            memorySet.add.delete(memoryItem);
            memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
            return check;
        }
        clear() {
            const params = this[memoryProxyPramsKey];
            const memory = params.memory;
            if (memory && memory.isFrozen()) {
                throw new FrozenError();
            }
            if (this.size === 0) {
                return this;
            }
            if (!memory) {
                params.object.clear.call(this);
                return this;
            }
            const slice = memory.getSlice();
            let memorySet = slice[params.ID];
            if (!memorySet) {
                slice[params.ID] = memorySet = new params.MemoryType();
            }
            params.object.forEach.call(this, (item) => {
                const itemParams = item && typeof item === 'object' && item[memoryProxyPramsKey];
                if (itemParams) {
                    item = itemParams.ID;
                    memory.deleteSliceProxyParent(itemParams.ID, params.ID, undefined);
                }
                memorySet.delete.add(item);
                memorySet.add.delete(item);
            });
            params.object.clear.call(this);
            memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
            return this;
        }
        has(item) {
            const params = this[memoryProxyPramsKey];
            return params.object.has.call(this, item);
        }
        values() {
            const params = this[memoryProxyPramsKey];
            return params.object.values.call(this);
        }
        keys() {
            const params = this[memoryProxyPramsKey];
            return params.object.keys.call(this);
        }
        forEach(callback) {
            const params = this[memoryProxyPramsKey];
            return params.object.forEach.call(this, callback);
        }
        entries() {
            const params = this[memoryProxyPramsKey];
            return params.object.entries.call(this);
        }
    }
    function proxifySyncSet() {
        // Synchronization function
        // Most methods of the "proxy" will call this synchronization function, even
        // if it is not yet linked to a memory !
        const params = this;
        const memory = params.memory;
        const object = params.object;
        const proxy = params.proxy;
        // get current object state in memory
        const memorySet = memory.getSliceValue(params.ID);
        // reset all keys (+ explanation of best/worst case scenario)
        object.clear.call(proxy);
        if (!memorySet) {
            return;
        }
        // Update values according to what is stored
        memorySet.forEach(item => {
            if (item instanceof VersionableID) {
                item = memory.getProxy(item);
            }
            object.add.call(proxy, item);
        });
    }
    // This will be set on the versionable params object and called with the params
    // as the value of `this`. It is created here so that it is created only once !
    function linkVersionable$1(memory) {
        const params = this;
        params.memory = memory;
        params.synchronize = proxifySyncSet;
        memory.markDirty(params.ID);
        if (!params.proxy.size) {
            return;
        }
        const slice = memory.getSlice();
        const memorySet = new params.MemoryType();
        slice[params.ID] = memorySet; // store the "pure" value in memory
        params.object.forEach.call(params.proxy, (value) => {
            const valueParams = value !== null && typeof value === 'object' && value[memoryProxyPramsKey];
            if (valueParams) {
                // If object is versionable then link it to memory as well
                memory.linkToMemory(value);
                memory.addSliceProxyParent(valueParams.ID, params.ID, undefined);
                memorySet.add.add(valueParams.ID);
            }
            else {
                memorySet.add.add(value);
            }
        });
    }
    function _proxifySet(set) {
        const versionableSet = new VersionableSet(set);
        set[memoryProxyPramsKey] = versionableSet[memoryProxyPramsKey];
        return versionableSet;
    }

    class VersionableID extends Number {
    }
    VersionableID.prototype[memoryProxyNotVersionableKey] = true;
    let MemoryID = 0;
    function generateVersionableID() {
        return new VersionableID(++MemoryID);
    }
    // queue of stuff to proxify
    const toProxify = new Map();
    /**
     * Take an object and return a versionable proxy to this object.
     *
     * @param object
     */
    function makeVersionable(object) {
        const params = object[memoryProxyPramsKey];
        if (params) {
            if (params.object === object) {
                throw new VersionableAllreadyVersionableError();
            }
            if (params && params.verify(object)) {
                return object;
            }
        }
        const proxy = _proxify(object);
        toProxify.forEach((callbacks, torototo) => {
            toProxify.delete(torototo);
            const proxy = _proxify(torototo);
            callbacks.forEach(callback => callback(proxy));
        });
        return proxy;
    }
    /**
     * Mark the current object as not versionable in memory.
     * A non versionable object is not linked to the memory. The memory does not
     * take care of the change inside this object, and this object is nerver
     * immutable.
     *
     * @param object
     */
    function markNotVersionable(object) {
        object[memoryProxyNotVersionableKey] = true;
    }
    /**
     * Throw an error if the given object is not a versionable.
     *
     * @param object
     */
    function _checkVersionable(object) {
        if (typeof object !== 'object' ||
            object === null ||
            object[memoryProxyNotVersionableKey] // this is set by the user
        ) {
            return;
        }
        const params = object[memoryProxyPramsKey];
        if (params) {
            if (params.object === object) {
                throw new VersionableAllreadyVersionableError();
            }
            if (params.verify(object)) {
                // Already versioned ! (we could have inherited from the `params` of
                // another, already versioned object, but we might not)
                return;
            }
        }
        throw new NotVersionableError();
    }
    // Recursive proxification is very limited because of callback depth. To
    // circumvent this issue, we queue the proxification of children.
    function _stackedProxify(customClass, callback) {
        if (!customClass ||
            typeof customClass !== 'object' ||
            customClass[memoryProxyNotVersionableKey]) {
            callback(customClass);
            return;
        }
        const params = customClass[memoryProxyPramsKey];
        if (params) {
            callback(params.proxy);
        }
        const callbacks = toProxify.get(customClass) || [];
        toProxify.set(customClass, callbacks);
        callbacks.push(callback);
    }
    function _proxify(customClass) {
        const params = customClass[memoryProxyPramsKey];
        if (params && params.verify(customClass)) {
            return params.proxy;
        }
        let proxy;
        if (customClass instanceof Set) {
            proxy = _proxifySet(customClass);
        }
        else if (customClass instanceof Array) {
            proxy = _proxifyArray(customClass);
        }
        else {
            proxy = _proxifyObject(customClass);
        }
        return proxy;
    }

    // MemoryType
    // MemoryType for Object
    // Type that the memory handles in practice. This is how it is stored in memory.
    class MemoryTypeObject {
        constructor() {
            this.props = {};
        }
    }
    // MemoryType for Array
    // Type that the memory handles in practice. This is how it is stored in memory.
    class MemoryTypeArray extends MemoryTypeObject {
        constructor() {
            super(...arguments);
            this.patch = {};
        }
    }
    // Output of memory given to proxy to operate
    class MemoryArrayCompiledWithPatch {
        // the proxy has to differentiate between what was already there and what is
        // being done in the current slice because deleting a key does not yield the
        // same result if the key was already there before this slice or not (it
        // would be marked as "removed" or ignored if wasn't already there.)
        constructor(
        // array as it appears in the slice right before the current one "array as of t-1"
        compiledValues, 
        // very last patch at current time t
        newValues, 
        // new properties on the array at current time t
        props) {
            this.compiledValues = compiledValues;
            this.newValues = newValues;
            this.props = props;
        }
    }
    // MemoryType for Set
    // Type that the memory handles in practice. This is how it is stored in memory.
    class MemoryTypeSet {
        constructor() {
            this.add = new Set();
            this.delete = new Set();
        }
    }
    const parentedPathSeparator = '•';
    function markAsDiffRoot(obj) {
        obj[memoryProxyPramsKey].isDiffRoot = true;
    }
    let memoryID = 0;
    const memoryRootSliceName = '';
    const regExpoSnapshotOrigin = /^.*\[snapshot from (.*)\]$/;
    class MemorySlice {
        constructor(name, parent) {
            this.children = [];
            this.data = {}; // registry of values
            this.linkedParentOfProxy = {};
            this.invalidCache = {}; // paths that have been changed in given memory slice (when switching slice, this set is loaded in _invalidateCache)
            this.ids = new Set();
            this.name = name;
            this.parent = parent;
        }
        getPrevious() {
            return this.snapshotOrigin ? this.snapshotOrigin.parent : this.parent;
        }
    }
    class Memory {
        constructor() {
            this._slices = {}; // Record<children, parent>
            this._proxies = {};
            this._rootProxies = {};
            this._numberOfFlatSlices = 40;
            this._numberOfSlicePerSnapshot = 8;
            this._autoSnapshotCheck = 0;
            this._id = ++memoryID;
            this.create(memoryRootSliceName);
            this.switchTo(memoryRootSliceName);
            this._memoryWorker = {
                ID: this._id,
                getProxy: (ID) => this._proxies[ID],
                getSlice: () => this._currentSlice.data,
                getSliceValue: (ID) => this._getValue(this._sliceKey, ID),
                isFrozen: this.isFrozen.bind(this),
                // Mark as "modified" in this slice
                markDirty: (ID) => (this._currentSlice.invalidCache[ID] = true),
                // I am the proxy, I tell you I synchornized the value
                deleteSliceProxyParent: this._deleteSliceProxyParent.bind(this),
                addSliceProxyParent: this._addSliceProxyParent.bind(this),
                linkToMemory: this._linkToMemory.bind(this),
            };
            Object.freeze(this._memoryWorker);
        }
        get sliceKey() {
            return this._sliceKey;
        }
        /**
         * Create a memory slice.
         * Modifications and changes (of objects bound to memory) are all recorded
         * in these slices. The new slice created will be noted as being the
         * continuation (or the child) of the current one.
         *
         * A slice with "children" is immutable. The modifications are therefore
         * blocked and an error will be triggered if a code tries to modify one of
         * these objects. To be able to edit again, you must destroy the "child"
         * slices or change the memory slice.
         *
         * @param sliceKey
         */
        create(sliceKey) {
            this._create(sliceKey, this._sliceKey);
            return this;
        }
        /**
         * Change the working memory slice (this must be created beforehand).
         *
         * @param sliceKey
         */
        switchTo(sliceKey) {
            if (!(sliceKey in this._slices)) {
                throw new MemoryError('You must create the "' + sliceKey + '" slice before switch on it');
            }
            if (sliceKey === this._sliceKey) {
                return;
            }
            const invalidCache = this._aggregateInvalidCaches(this._sliceKey, sliceKey);
            this._currentSlice = this._slices[sliceKey];
            this._sliceKey = sliceKey;
            for (const key of invalidCache) {
                const proxy = this._proxies[key];
                const params = proxy[memoryProxyPramsKey];
                params.synchronize();
            }
            this._autoSnapshotCheck++;
            if (!(this._autoSnapshotCheck % this._numberOfSlicePerSnapshot)) {
                this._autoSnapshot();
            }
            return this;
        }
        /**
         * Attach a versionable to memory.
         * The versionable will then be versioned and its modifications will be
         * recorded in the corresponding memory slots.
         * All other versionables linked to given versionable attached to memory
         * are automatically linked to memory.
         *
         * (Items bound to memory by this function will be noted as part of the
         * root of changes @see getRoots )
         *
         * @param versionable
         */
        attach(versionable) {
            const params = versionable[memoryProxyPramsKey];
            if (!params) {
                throw new NotVersionableError();
            }
            if (params.object === versionable) {
                throw new VersionableAllreadyVersionableError();
            }
            if (!params.verify(versionable)) {
                throw new NotVersionableError();
            }
            if (this.isFrozen()) {
                throw new FrozenError();
            }
            if (!params.memory || params.memory !== this._memoryWorker) {
                params.isDiffRoot = true;
                this._linkToMemory(versionable);
            }
            this._rootProxies[params.ID] = true;
        }
        /**
         * Returns the parents of the object.
         *
         * Example: p = {}; v = {point: p} axis = {origin: p}
         * The parents of p are [[v, ['point']], [axis, ['origin']]]
         *
         * @param versionable
         */
        getParents(versionable) {
            const pathChanges = new Map();
            const nodeID = versionable[memoryProxyPramsKey].ID;
            const pathList = [[nodeID, []]];
            while (pathList.length) {
                const path = pathList.pop();
                const [nodeID, pathToNode] = path;
                const parentProxy = this._proxies[nodeID];
                let paths = pathChanges.get(parentProxy);
                if (!paths) {
                    paths = [];
                    pathChanges.set(parentProxy, paths);
                }
                paths.push(path[1]);
                if (this._rootProxies[nodeID]) {
                    continue;
                }
                this._getProxyParentedPath(this._sliceKey, nodeID).forEach(path => {
                    const parentNodeID = path.split(parentedPathSeparator, 1)[0];
                    const partPath = path.slice(parentNodeID.length + 1);
                    pathList.push([+parentNodeID, [partPath].concat(pathToNode)]);
                });
            }
            return pathChanges;
        }
        /**
         * Return the location of the changes.
         *
         * @param from
         * @param to
         */
        getChangesLocations(from, to) {
            const diff = {
                add: [],
                move: [],
                remove: [],
                update: [],
            };
            const ancestorKey = this._getCommonAncestor(from, to);
            const refs = this._getChangesPath(from, to, ancestorKey);
            if (from === ancestorKey && from !== to) {
                refs.shift();
            }
            const removeFromUpdate = new Set();
            let previous;
            let ref;
            while ((ref = refs.pop())) {
                const linkedParentOfProxy = ref.linkedParentOfProxy;
                for (const ID in linkedParentOfProxy) {
                    const proxy = this._proxies[ID];
                    if (linkedParentOfProxy[ID].length) {
                        if (ref.ids.has(+ID)) {
                            if (ref.parent === previous) {
                                diff.remove.push(proxy);
                            }
                            else {
                                diff.add.push(proxy);
                            }
                            removeFromUpdate.add(proxy);
                        }
                        else {
                            diff.move.push(proxy);
                        }
                    }
                    else {
                        if (ref.parent === previous) {
                            diff.add.push(proxy);
                        }
                        else {
                            diff.remove.push(proxy);
                        }
                        removeFromUpdate.add(proxy);
                    }
                }
                if (ref.parent === previous) {
                    for (const ID of previous.ids) {
                        const proxy = this._proxies[ID];
                        diff.remove.push(proxy);
                        removeFromUpdate.add(proxy);
                    }
                }
                const slice = ref.data;
                Object.keys(slice).forEach(ID => {
                    const id = +ID;
                    const memoryItem = slice[id];
                    const proxy = this._proxies[ID];
                    if (removeFromUpdate.has(proxy)) {
                        return;
                    }
                    else if (memoryItem instanceof MemoryTypeArray) {
                        const keys = Object.keys(memoryItem.props);
                        if (keys.length) {
                            diff.update.push([proxy, keys]);
                        }
                        const params = proxy[memoryProxyPramsKey];
                        const uniqIDs = params.uniqIDs;
                        const len = uniqIDs.length;
                        const half = Math.ceil(len / 2);
                        const indexes = [];
                        for (const i in memoryItem.patch) {
                            let index = half;
                            let step = half;
                            while (step) {
                                const value = uniqIDs[index];
                                if (value === i) {
                                    break;
                                }
                                else if (value > i) {
                                    index -= step;
                                    if (index < 0) {
                                        index = 0;
                                    }
                                }
                                else {
                                    index += step;
                                    if (index >= len) {
                                        index = len - 1;
                                    }
                                }
                                if (step > 1) {
                                    step = Math.ceil(step / 2);
                                }
                                else {
                                    const value = uniqIDs[index];
                                    step = 0;
                                    if (value < i && uniqIDs[index + 1] > i) {
                                        index++;
                                    }
                                }
                            }
                            if (!indexes.includes(index)) {
                                indexes.push(index);
                            }
                        }
                        if (indexes.length) {
                            diff.update.push([proxy, indexes]);
                        }
                    }
                    else if (memoryItem instanceof MemoryTypeSet) {
                        diff.update.push([proxy, null]);
                    }
                    else {
                        const keys = Object.keys(memoryItem.props);
                        if (keys.length) {
                            diff.update.push([proxy, keys]);
                        }
                    }
                });
                previous = ref;
            }
            return diff;
        }
        /**
         * Get if the current memory slice are imutable or not.
         *
         */
        isFrozen() {
            return this._currentSlice.children.length > 0;
        }
        /**
         * Remove a memory slice.
         * The current slice cannot be the one being deleted or one of its children.
         *
         * @param sliceKey
         */
        remove(sliceKey) {
            if (!(sliceKey in this._slices)) {
                return this;
            }
            if (sliceKey === memoryRootSliceName) {
                throw new MemoryError('You should not remove the original memory slice');
            }
            let ref = this._slices[this._sliceKey];
            while (ref) {
                if (ref.name === sliceKey) {
                    throw new MemoryError('Please switch to a non-children slice before remove it');
                }
                ref = ref.parent;
            }
            const IDs = this._remove(sliceKey);
            // check if the IDs are linked evrywere
            Object.values(this._slices).forEach(reference => {
                const linkedParentOfProxy = reference.linkedParentOfProxy;
                IDs.forEach(ID => {
                    if (ID in linkedParentOfProxy) {
                        IDs.delete(ID);
                    }
                });
            });
            // remove unlinked items
            IDs.forEach(ID => {
                delete this._proxies[ID];
                delete this._rootProxies[ID];
            });
            return this;
        }
        /**
         * Return ancestor versionables noted as roots.
         *
         * There are two ways for a versionable to be root, either via the
         * 'linkToMemory' method, or with the 'markAsDiffRoot' utility function.
         *
         * @param proxy
         */
        getRoots(proxy) {
            const roots = new Set();
            const nodeID = proxy[memoryProxyPramsKey].ID;
            const pathList = [[nodeID, []]];
            while (pathList.length) {
                const path = pathList.pop();
                const [nodeID, pathToNode] = path;
                if (this._rootProxies[nodeID]) {
                    roots.add(this._proxies[nodeID]);
                    continue;
                }
                this._getProxyParentedPath(this._sliceKey, nodeID).forEach(path => {
                    const parentNodeID = path.split(parentedPathSeparator, 1)[0];
                    const partPath = path.slice(parentNodeID.length + 1);
                    pathList.push([+parentNodeID, [partPath].concat(pathToNode)]);
                });
            }
            return roots;
        }
        /**
         * Return the list of names of all previous memory slice of the given
         * memory slice.
         *
         * @param sliceKey
         * @param withoutSnapshot
         */
        getPath(sliceKey, withoutSnapshot) {
            const sliceKeys = [];
            let ref = this._slices[sliceKey];
            while (ref && ref.name) {
                sliceKeys.push(ref.name);
                ref = withoutSnapshot ? ref.getPrevious() : ref.parent;
            }
            return sliceKeys;
        }
        /**
         * Create the snapshot of different memory slices (use the path between the
         * memory slice to get all changes) and merge the changes into a new
         * destination slice.
         *
         * @param fromSliceKey
         * @param unitSliceKey
         * @param newSliceKey
         */
        snapshot(fromSliceKey, unitSliceKey, newSliceKey) {
            const refs = this._slices;
            const fromRref = refs[fromSliceKey];
            const untilRref = refs[unitSliceKey];
            const newRef = this._create(newSliceKey, fromRref.parent && fromRref.parent.name);
            this._squashInto(fromSliceKey, unitSliceKey, newRef.name);
            untilRref.children.forEach(child => {
                child.parent = newRef;
            });
            newRef.children = untilRref.children;
            untilRref.children = [];
            untilRref.snapshot = newRef;
            newRef.snapshotOrigin = untilRref;
        }
        /**
         * Compress all changes between two parented memory slices and remove all
         * children memory slice.
         *
         * @param fromSliceKey
         * @param unitSliceKey
         */
        compress(fromSliceKey, unitSliceKey) {
            const refs = this._slices;
            const fromRref = refs[fromSliceKey];
            const untilRref = refs[unitSliceKey];
            const toRemove = fromRref.children.slice().map(ref => ref.name);
            fromRref.children = untilRref.children.splice(0);
            this._squashInto(fromSliceKey, unitSliceKey, fromSliceKey);
            let key;
            while ((key = toRemove.pop())) {
                this._remove(key);
            }
            return true;
        }
        /**
         * Debug tools to get the list of memory slice and changes from a
         * versionable in order to be able to trace his evolution.
         *
         * @param versionable
         */
        getSliceAndChanges(versionable) {
            let id;
            if (typeof versionable === 'number' || versionable instanceof VersionableID) {
                id = +versionable;
                versionable = this._proxies[id];
            }
            else {
                for (const key in this._proxies) {
                    if (this._proxies[key] === versionable) {
                        id = +key;
                        break;
                    }
                }
            }
            const res = [];
            const slices = Object.values(this._slices).filter(slice => slice.data[id]);
            for (const slice of slices) {
                let changes;
                if (versionable instanceof Set) {
                    const data = slice.data[id];
                    changes = {
                        add: new Set(data.add),
                        delete: new Set(data.delete),
                    };
                }
                else if (versionable instanceof Array) {
                    const data = slice.data[id];
                    changes = {
                        props: Object.assign({}, data.props),
                        patch: Object.assign({}, data.patch),
                    };
                }
                else {
                    const data = slice.data[id];
                    changes = {
                        props: Object.assign({}, data.props),
                    };
                }
                res.push({ sliceKey: slice.name, versionableId: id, changes: changes });
            }
            return res;
        }
        /////////////////////////////////////////////////////
        // private
        /////////////////////////////////////////////////////
        _addSliceProxyParent(ID, parentID, attributeName) {
            const sliceKey = this._sliceKey;
            const sliceLinkedParentOfProxy = this._slices[sliceKey].linkedParentOfProxy;
            const path = parentID +
                (attributeName === undefined
                    ? memoryRootSliceName
                    : parentedPathSeparator + attributeName);
            let parents = sliceLinkedParentOfProxy[ID];
            if (!parents) {
                const parented = this._getProxyParentedPath(sliceKey, ID);
                parents = sliceLinkedParentOfProxy[ID] = parented
                    ? parented.slice()
                    : [];
            }
            parents.push(path);
        }
        _deleteSliceProxyParent(ID, parentID, attributeName) {
            const sliceKey = this._sliceKey;
            const sliceLinkedParentOfProxy = this._slices[sliceKey].linkedParentOfProxy;
            const path = parentID +
                (attributeName === undefined
                    ? memoryRootSliceName
                    : parentedPathSeparator + attributeName);
            let parents = this._getProxyParentedPath(sliceKey, ID);
            const index = parents.indexOf(path);
            if (!sliceLinkedParentOfProxy[ID]) {
                parents = sliceLinkedParentOfProxy[ID] = parents.slice();
            }
            parents.splice(index, 1);
        }
        _compiledArrayPatches(patches) {
            const props = {};
            const valueBySeq = {};
            while (patches.length) {
                const patch = patches.pop();
                const step = patch.value;
                Object.assign(props, step.props);
                Object.assign(valueBySeq, step.patch);
            }
            return {
                patch: valueBySeq,
                props: props,
            };
        }
        _compiledSetPatches(patches) {
            const obj = new Set();
            while (patches.length) {
                const patch = patches.pop();
                const step = patch.value;
                step.add.forEach((item) => obj.add(item));
                step.delete.forEach((item) => obj.delete(item));
            }
            return obj;
        }
        _compiledObjectPatches(patches) {
            const obj = new MemoryTypeObject();
            const props = obj.props;
            while (patches.length) {
                const patch = patches.pop();
                const step = patch.value;
                Object.assign(props, step.props);
            }
            Object.keys(props).forEach(key => {
                if (props[key] === removedItem) {
                    delete props[key];
                }
            });
            return obj;
        }
        _create(sliceKey, fromSliceKey) {
            const refs = this._slices;
            if (refs[sliceKey]) {
                throw new Error('The memory slice "' + sliceKey + '" already exists');
            }
            const parent = refs[fromSliceKey];
            const ref = (refs[sliceKey] = new MemorySlice(sliceKey, parent));
            if (parent) {
                parent.children.push(ref);
            }
            return ref;
        }
        _getChangesPath(fromSliceKey, toSliceKey, ancestorKey) {
            const fromPath = [];
            let ref = this._slices[fromSliceKey];
            while (ref) {
                fromPath.push(ref);
                if (ref.name === ancestorKey) {
                    break;
                }
                ref = ref.getPrevious();
            }
            const toPath = [];
            ref = this._slices[toSliceKey];
            while (ref) {
                if (ref.name === ancestorKey) {
                    break;
                }
                toPath.push(ref);
                ref = ref.getPrevious();
            }
            toPath.reverse();
            return fromPath.concat(toPath);
        }
        _getCommonAncestor(sliceKeyA, sliceKeyB) {
            const rootB = this._slices[sliceKeyB];
            let refA = this._slices[sliceKeyA];
            while (refA) {
                let refB = rootB;
                while (refB) {
                    if (refA.name === refB.name) {
                        return refA.name;
                    }
                    refB = refB.getPrevious();
                }
                refA = refA.getPrevious();
            }
        }
        _getProxyParentedPath(sliceKey, ID) {
            // bubbling up magic for proxyParents
            let ref = this._slices[sliceKey];
            while (ref) {
                const slice = ref.linkedParentOfProxy;
                const path = slice && slice[ID];
                if (path) {
                    return path;
                }
                ref = ref.parent;
            }
            return [];
        }
        _getValue(sliceKey, ID) {
            const patch = this._getPatches(undefined, sliceKey, ID);
            if (!patch) {
                return;
            }
            if (patch.type === 'set') {
                return this._compiledSetPatches(patch.patches);
            }
            else if (patch.type === 'array') {
                return this._getValueArray(sliceKey, ID, patch.patches);
            }
            else {
                return this._compiledObjectPatches(patch.patches);
            }
        }
        _getValueArray(sliceKey, ID, patches) {
            const ref = this._slices[sliceKey];
            let owner;
            if (ref.data[ID]) {
                owner = patches.shift().value;
            }
            const value = this._compiledArrayPatches(patches);
            return new MemoryArrayCompiledWithPatch(value.patch, owner || new MemoryTypeArray(), value.props);
        }
        _getPatches(fromSliceKey, toSliceKey, ID) {
            let ref = this._slices[toSliceKey];
            let type;
            const patches = [];
            while (ref && ref.name !== fromSliceKey) {
                const slice = ref.data;
                const value = slice && slice[ID];
                if (!value) {
                    ref = ref.parent;
                    continue;
                }
                if (!type) {
                    if (value instanceof MemoryTypeArray) {
                        type = 'array';
                    }
                    else if (value instanceof MemoryTypeSet) {
                        type = 'set';
                    }
                    else {
                        type = 'object';
                    }
                }
                patches.push({
                    sliceKey: ref.name,
                    value: value,
                });
                ref = ref.parent;
            }
            if (!type) {
                return;
            }
            return {
                patches: patches,
                type: type,
            };
        }
        _aggregateInvalidCaches(from, to) {
            const invalidCache = new Set();
            if (from === to) {
                return invalidCache;
            }
            const ancestorKey = this._getCommonAncestor(from, to);
            const refs = this._getChangesPath(from, to, ancestorKey);
            if (this._sliceKey === ancestorKey) {
                refs.shift();
            }
            while (refs.length) {
                const ref = refs.pop();
                Object.keys(ref.invalidCache).forEach(key => {
                    // It was invalid before, it is still invalid now since it wasn't yet read
                    invalidCache.add(+key);
                });
            }
            return invalidCache;
        }
        _linkToMemory(proxy) {
            const params = proxy[memoryProxyPramsKey];
            if (params.memory) {
                if (params.memory !== this._memoryWorker) {
                    throw new MemoryError('This object is already linked to a other memory');
                }
                return;
            }
            const ID = params.ID;
            params.memory = this._memoryWorker;
            params.linkCallback(this._memoryWorker);
            this._proxies[ID] = proxy;
            if (params.isDiffRoot) {
                this._rootProxies[ID] = true;
            }
            this._currentSlice.ids.add(+ID);
        }
        _remove(sliceKey) {
            const IDs = [];
            let ref = this._slices[sliceKey];
            const index = ref.parent.children.indexOf(ref);
            ref.parent.children.splice(index, 1);
            const refs = [ref];
            while ((ref = refs.pop())) {
                const sliceKey = ref.name;
                ref.children.forEach(ref => refs.push(ref));
                Object.keys(ref.linkedParentOfProxy).forEach(ID => IDs.push(+ID));
                delete this._slices[sliceKey];
            }
            return new Set(IDs);
        }
        _squashInto(fromSliceKey, unitSliceKey, intoSliceKey) {
            const refs = this._slices;
            const fromRref = refs[fromSliceKey];
            const untilRref = refs[unitSliceKey];
            const intoRef = refs[intoSliceKey];
            const references = [];
            let ref = untilRref;
            while (ref) {
                references.push(ref);
                if (ref === fromRref) {
                    break;
                }
                ref = ref.parent;
            }
            if (!ref) {
                throw new Error('Can not merge the slices');
            }
            const intoLinkedParentOfProxy = refs[intoSliceKey].linkedParentOfProxy;
            const intoInvalidCache = refs[intoSliceKey].invalidCache;
            const intoSlices = intoRef.data;
            while ((ref = references.pop())) {
                const LinkedParentOfProxy = ref.linkedParentOfProxy;
                Object.keys(LinkedParentOfProxy).forEach(ID => {
                    intoLinkedParentOfProxy[ID] = LinkedParentOfProxy[ID].slice();
                });
                Object.keys(ref.invalidCache).forEach(link => {
                    intoInvalidCache[link] = true;
                });
                const slice = ref.data;
                Object.keys(slice).forEach(ID => {
                    const id = +ID;
                    const memoryItem = slice[id];
                    if (memoryItem instanceof MemoryTypeArray) {
                        let intoItem = intoSlices[id];
                        if (!intoItem) {
                            intoItem = intoSlices[id] = new MemoryTypeArray();
                        }
                        Object.assign(intoItem.patch, memoryItem.patch);
                        Object.assign(intoItem.props, memoryItem.props);
                    }
                    else if (memoryItem instanceof MemoryTypeSet) {
                        let intoItem = intoSlices[id];
                        if (!intoItem) {
                            intoItem = intoSlices[id] = new MemoryTypeSet();
                        }
                        memoryItem.add.forEach(item => {
                            if (!intoItem.delete.has(item)) {
                                intoItem.add.add(item);
                            }
                            else {
                                intoItem.delete.delete(item);
                            }
                        });
                        memoryItem.delete.forEach(item => {
                            if (!intoItem.add.has(item)) {
                                intoItem.delete.add(item);
                            }
                            else {
                                intoItem.add.delete(item);
                            }
                        });
                    }
                    else {
                        let intoItem = intoSlices[id];
                        if (!intoItem) {
                            intoItem = intoSlices[id] = new MemoryTypeObject();
                        }
                        Object.assign(intoItem.props, memoryItem.props);
                    }
                });
            }
        }
        _autoSnapshot() {
            const refs = [];
            let ref = this._currentSlice;
            while (ref && ref.name) {
                refs.push(ref);
                ref = ref.parent;
            }
            if (refs.length > this._numberOfFlatSlices + this._numberOfSlicePerSnapshot) {
                const fromSliceKey = refs[refs.length - 1].name;
                const unitSliceKey = refs[refs.length - 1 - this._numberOfSlicePerSnapshot].name;
                const newSliceKey = unitSliceKey +
                    '[snapshot from ' +
                    fromSliceKey.replace(regExpoSnapshotOrigin, '$1') +
                    ']';
                this.snapshot(fromSliceKey, unitSliceKey, newSliceKey);
            }
        }
    }

    const Undefined = Symbol('jabberwockMemoryUndefined');
    const proxyArrayHandler = {
        get(array, prop, proxy) {
            if (typeof prop === 'symbol' || !isNaN(prop)) {
                return array[prop];
            }
            const params = array[memoryProxyPramsKey];
            if (!params.memory) {
                return array[prop];
            }
            switch (prop) {
                case 'indexOf':
                    return indexOf.bind(proxy, params);
                case 'includes':
                    return includes.bind(proxy, params);
                case 'splice':
                    return splice.bind(proxy, params);
                case 'push':
                    return array[prop];
                case 'unshift':
                    return unshift.bind(proxy, params);
                case 'shift':
                    return shift.bind(proxy, params);
                case 'pop':
                    return pop.bind(proxy, params);
                case 'forEach':
                    return forEach.bind(proxy, params);
                case 'map':
                    return map.bind(proxy, params);
                case 'filter':
                    return filter.bind(proxy, params);
                default:
                    return array[prop];
            }
        },
        set(proxyObject, prop, value, proxy) {
            const params = proxyObject[memoryProxyPramsKey];
            const array = params.object;
            if (typeof prop === 'symbol' ||
                !params.memory ||
                (prop !== 'length' && isNaN(prop))) {
                return proxyObjectHandler.set(array, prop, value, proxy);
            }
            const index = +prop;
            const memory = params.memory;
            if (memory.isFrozen()) {
                throw new FrozenError();
            }
            const oldValue = array[prop];
            if (oldValue === value || (value === removedItem && !(prop in array))) {
                // no change
                return true;
            }
            const slice = memory.getSlice();
            let memoryArray = slice[params.ID];
            if (!memoryArray) {
                slice[params.ID] = memoryArray = new params.MemoryType();
            }
            if (slice !== params.syncSlice) {
                // allready sync, the current value (before update) is the previous value
                params.syncSlice = slice;
                params.previousSliceValues = {};
                array.forEach((value, index) => {
                    params.previousSliceValues[params.uniqIDs[index]] = value;
                });
            }
            if (prop === 'length') {
                const length = +value;
                for (let index = length; index < array.length; index++) {
                    const val = array[index];
                    const oldParams = typeof val === 'object' && val[memoryProxyPramsKey];
                    if (oldParams) {
                        memory.deleteSliceProxyParent(oldParams.ID, params.ID, '´' + params.uniqIDs[index]);
                    }
                    const uid = params.uniqIDs[index];
                    if (params.previousSliceValues[uid] === removedItem ||
                        !(uid in params.previousSliceValues)) {
                        delete memoryArray.patch[uid];
                    }
                    else {
                        memoryArray.patch[uid] = removedItem;
                    }
                }
                array.length = length;
                memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
                return true;
            }
            let newParams;
            if (value !== null && typeof value === 'object' && !value[memoryProxyNotVersionableKey]) {
                _checkVersionable(value);
                memory.linkToMemory(value);
                newParams = value[memoryProxyPramsKey];
            }
            array[prop] = value;
            if (oldValue === Undefined) {
                const uid = params.uniqIDs[index];
                if (newParams) {
                    memoryArray.patch[uid] = newParams.ID;
                    memory.addSliceProxyParent(newParams.ID, params.ID, '´' + uid);
                }
                else {
                    memoryArray.patch[uid] = value;
                }
                params.map.set(value, uid);
            }
            else {
                const uniqIDs = params.uniqIDs;
                const uid = uniqIDs[index];
                // begin with remove previous
                if (uid) {
                    const mapUID = params.map.get(oldValue);
                    if (mapUID === uid) {
                        params.map.delete(oldValue);
                        const otherIndex = array.indexOf(oldValue);
                        if (otherIndex !== -1) {
                            params.map.set(oldValue, uniqIDs[otherIndex]);
                        }
                    }
                    if (params.previousSliceValues[uid] === removedItem ||
                        !(uid in params.previousSliceValues)) {
                        delete memoryArray.patch[uid];
                    }
                    else {
                        memoryArray.patch[uid] = removedItem;
                    }
                    const oldParams = oldValue && typeof oldValue === 'object' && oldValue[memoryProxyPramsKey];
                    if (oldParams) {
                        memory.deleteSliceProxyParent(oldParams.ID, params.ID, '´' + uid);
                    }
                }
                if (value === removedItem) {
                    memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
                    return true;
                }
                // and then we add item
                if (!uid && index > uniqIDs.length) {
                    // add fake undefined values (don't add undefined in array)
                    for (let k = uniqIDs.length; k < index; k++) {
                        const newUniqID = generateUid(params.sequences, uniqIDs[k - 1]);
                        uniqIDs.push(newUniqID);
                        memoryArray.patch[newUniqID] = Undefined;
                    }
                }
                const isEnd = index >= uniqIDs.length;
                const nearest = isEnd ? undefined : uniqIDs[index];
                const newUniqID = generateUid(params.sequences, nearest, isEnd);
                uniqIDs[index] = newUniqID;
                if (newParams) {
                    memory.addSliceProxyParent(newParams.ID, params.ID, '´' + newUniqID);
                    memoryArray.patch[newUniqID] = newParams.ID;
                }
                else {
                    memoryArray.patch[newUniqID] = value;
                }
                if (!params.map.has(oldValue)) {
                    params.map.set(value, newUniqID);
                }
            }
            memory.markDirty(params.ID); // mark the cache as invalid when change the slide memory
            return true;
        },
        deleteProperty(obj, prop) {
            // `removedItem` is a marker to notify that there was something here but
            // it got removed
            this.set(obj, prop, removedItem);
            delete obj[prop];
            return true;
        },
    };
    function _proxifyArray(array) {
        const proxyObject = _proxifyObject(array);
        const proxy = new Proxy(proxyObject, proxyArrayHandler);
        const params = proxyObject[memoryProxyPramsKey];
        params.proxy = proxy;
        params.linkCallback = linkVersionable$2;
        params.MemoryType = MemoryTypeArray;
        params.map = new Map();
        params.uniqIDs = [];
        params.sequences = [];
        return proxy;
    }
    function unshift(params, ...items) {
        for (let k = 0, len = items.length; k < len; k++) {
            const item = items[k];
            params.object.unshift(Undefined);
            params.uniqIDs.unshift(generateUid(params.sequences, undefined));
            this[0] = item;
        }
        return params.object.length;
    }
    function shift(params) {
        const value = params.object[0];
        this['0'] = removedItem;
        params.object.shift();
        params.uniqIDs.shift();
        return value;
    }
    function pop(params) {
        const lastIndex = params.object.length - 1;
        const value = params.object[lastIndex];
        this.length = lastIndex;
        return value;
    }
    function splice(params, index, nb, ...items) {
        const array = params.object;
        const uniqIDs = params.uniqIDs;
        const len = array.length;
        if (index < 0) {
            index = len + index;
        }
        if (nb === undefined) {
            nb = len - index;
        }
        const value = new array.constructor();
        if (nb > 0) {
            for (let i = 0; i < nb; i++) {
                value.push(array[i + index]);
            }
            for (let i = 0; i < nb; i++) {
                this[(i + index).toString()] = removedItem;
            }
            array.splice(index, nb);
            uniqIDs.splice(index, nb);
        }
        for (let key = 0, len = items.length; key < len; key++) {
            const item = items[key];
            const i = key + index;
            array.splice(i, 0, Undefined);
            const nearest = uniqIDs[i - 1];
            uniqIDs.splice(i, 0, generateUid(params.sequences, nearest));
            this[i] = item;
        }
        return value;
    }
    function forEach(params, callback) {
        const array = params.object;
        for (let index = 0, len = array.length; index < len; index++) {
            callback(array[index], index, this);
        }
    }
    function map(params, callback) {
        const result = [];
        const array = params.object;
        for (let index = 0, len = array.length; index < len; index++) {
            result.push(callback(array[index], index, this));
        }
        return result;
    }
    function filter(params, callback) {
        const result = [];
        const array = params.object;
        for (let index = 0, len = array.length; index < len; index++) {
            const value = array[index];
            if (callback(value, index, this)) {
                result.push(value);
            }
        }
        return result;
    }
    function indexOf(params, item) {
        return params.object.indexOf(item);
    }
    function includes(params, item) {
        return params.object.includes(item);
    }
    function proxifySyncArray() {
        // Synchronization function
        // Most methods of the "proxy" will call this synchronization function, even
        // if it is not yet linked to a memory !
        const params = this;
        const memory = params.memory;
        // empties the array
        params.uniqIDs.length = 0;
        params.object.length = 0;
        // Clear props
        const keys = Object.keys(params.object);
        let key;
        while ((key = keys.pop())) {
            delete params.object[key];
        }
        const rawValues = memory.getSliceValue(params.ID);
        if (!rawValues) {
            return;
        }
        const values = Object.assign({}, rawValues.compiledValues, rawValues.newValues.patch);
        const sequences = Object.keys(values);
        sequences.sort();
        proxifySyncArrayItems(memory, sequences, values, params.object, params.uniqIDs);
        const props = Object.assign({}, rawValues.props, rawValues.newValues.props);
        proxifySyncArrayItems(memory, Object.keys(props), props, params.object);
        params.syncSlice = memory.getSlice();
        params.previousSliceValues = rawValues.compiledValues;
        params.sequences = sequences;
        params.map.clear();
        params.object.forEach((item, i) => {
            params.map.set(item, params.uniqIDs[i]);
        });
    }
    function proxifySyncArrayItems(memory, keys, values, array, uniqIDs) {
        let index = 0;
        for (let k = 0, len = keys.length; k < len; k++) {
            const key = keys[k];
            let value = values[key];
            if (value === removedItem) {
                continue;
            }
            if (value instanceof VersionableID) {
                value = memory.getProxy(value);
            }
            if (uniqIDs) {
                if (value !== Undefined) {
                    array[index] = value;
                }
                uniqIDs.push(key);
                index++;
            }
            else {
                array[key] = value;
            }
        }
    }
    function linkVersionable$2(memory) {
        const params = this;
        params.memory = memory;
        params.synchronize = proxifySyncArray;
        const slice = memory.getSlice();
        const array = params.object;
        const keys = Object.keys(array);
        const len = keys.length;
        const ID = params.ID;
        if (len === 0) {
            memory.markDirty(ID);
            return;
        }
        const memoryArray = (slice[ID] = new params.MemoryType());
        const props = memoryArray.props;
        const patch = memoryArray.patch;
        const uniqIDs = params.uniqIDs;
        const sequences = params.sequences;
        let arrayIndex = -1;
        for (let k = 0; k < len; k++) {
            const key = keys[k];
            const index = +key;
            const value = array[key];
            const valueParams = value !== null && typeof value === 'object' && value[memoryProxyPramsKey];
            if (valueParams) {
                memory.linkToMemory(value);
            }
            if (isNaN(index)) {
                if (valueParams) {
                    props[key] = valueParams.ID;
                    memory.addSliceProxyParent(valueParams.ID, ID, key);
                }
                else {
                    props[key] = value;
                }
            }
            else {
                arrayIndex++;
                while (arrayIndex < index) {
                    const newUniqID = generateUid(sequences, undefined, true);
                    uniqIDs[arrayIndex] = newUniqID;
                    patch[newUniqID] = Undefined;
                    arrayIndex++;
                }
                const newUniqID = generateUid(sequences, undefined, true);
                uniqIDs[index] = newUniqID;
                if (valueParams) {
                    patch[newUniqID] = valueParams.ID;
                    memory.addSliceProxyParent(valueParams.ID, ID, '´' + newUniqID);
                }
                else {
                    patch[newUniqID] = value;
                }
            }
        }
        params.map.clear();
        array.forEach((item, i) => {
            if (!params.map.has(item)) {
                params.map.set(item, uniqIDs[i]);
            }
        });
        memory.markDirty(ID);
    }
    // IDs
    function allocUid(min, max) {
        const step = 4;
        if (!min && !max) {
            return [128];
        }
        min = min || [];
        max = max || [];
        const res = [];
        let minSeq = 0;
        let maxSeq = max[0];
        for (let index = 0, len = Math.max(min.length, max.length); index < len; index++) {
            minSeq = min[index] | 0;
            maxSeq = index in max ? max[index] : 4096;
            if (minSeq === 4095 && maxSeq === 4096) {
                res.push(minSeq);
            }
            else if (minSeq === maxSeq) {
                res.push(minSeq);
            }
            else if (minSeq === maxSeq - 1 && len > index - 1) {
                res.push(minSeq);
            }
            else {
                break;
            }
        }
        const diff = (maxSeq - minSeq) >> 1;
        if (diff === 0) {
            res.push(min.length ? 128 : 2048);
        }
        else if (minSeq === 0) {
            res.push(maxSeq - Math.min(diff, step));
        }
        else {
            res.push(minSeq + Math.min(diff, step));
        }
        return res;
    }
    function hexaToSeq(str) {
        const seq = [];
        for (let k = 0, len = str.length; k < len; k += 3) {
            seq.push(parseInt(str.slice(k, k + 3), 16));
        }
        return seq;
    }
    function SeqToHexa(seq) {
        let str = '';
        const len = seq.length;
        for (let k = 0; k < len; k++) {
            const n = seq[k];
            if (n === 0) {
                str += '000';
            }
            else if (n < 16) {
                str += '00' + n.toString(16);
            }
            else if (n < 256) {
                str += '0' + n.toString(16);
            }
            else {
                str += n.toString(16);
            }
        }
        return str;
    }
    function generateUid(sortedUniqIDs, min, isEnd) {
        let max;
        if (isEnd) {
            min = sortedUniqIDs[sortedUniqIDs.length - 1];
        }
        else if (min) {
            max = sortedUniqIDs[sortedUniqIDs.indexOf(min) + 1];
        }
        else {
            max = sortedUniqIDs[0];
        }
        const minSeq = min && hexaToSeq(min);
        const maxSeq = max && hexaToSeq(max);
        const newUniqID = SeqToHexa(allocUid(minSeq, maxSeq));
        if (isEnd) {
            sortedUniqIDs.push(newUniqID);
        }
        else {
            const sortedIndex = min ? sortedUniqIDs.indexOf(min) : -1;
            if (sortedIndex === -1) {
                sortedUniqIDs.unshift(newUniqID);
            }
            else {
                sortedUniqIDs.splice(sortedIndex + 1, 0, newUniqID);
            }
        }
        return newUniqID;
    }
    class VersionableArray extends Array {
        constructor(...items) {
            super(...items);
            return _proxifyArray(this);
        }
    }

    /**
     * Abstract class to add event mechanism.
     */
    class EventMixin {
        /**
         * Subscribe to an event with a callback.
         *
         * @param eventName
         * @param callback
         */
        on(eventName, callback) {
            if (!this._eventCallbacks) {
                this._eventCallbacks = makeVersionable({});
            }
            if (!this._eventCallbacks[eventName]) {
                this._eventCallbacks[eventName] = new VersionableArray();
            }
            this._eventCallbacks[eventName].push(callback);
        }
        /**
         * Unsubscribe to an event (with a callback).
         *
         * @param eventName
         * @param callback
         */
        off(eventName, callback) {
            var _a;
            const callbacks = (_a = this._eventCallbacks) === null || _a === void 0 ? void 0 : _a[eventName];
            if (callback) {
                const index = callbacks === null || callbacks === void 0 ? void 0 : callbacks.findIndex(eventCallback => eventCallback === callback);
                if (callbacks && index !== -1) {
                    this._eventCallbacks[eventName].splice(index, 1);
                    if (!this._eventCallbacks.length) {
                        delete this._eventCallbacks[eventName];
                    }
                }
            }
            else if (this._eventCallbacks) {
                delete this._eventCallbacks[eventName];
            }
            if (this._eventCallbacks && !Object.keys(this._eventCallbacks).length) {
                delete this._eventCallbacks;
            }
        }
        /**
         * Fire an event for of this object and all ancestors.
         *
         * @param eventName
         * @param args
         */
        trigger(eventName, args) {
            var _a;
            if ((_a = this._eventCallbacks) === null || _a === void 0 ? void 0 : _a[eventName]) {
                if (!this._callbackWorking) {
                    this._callbackWorking = new VersionableSet();
                }
                for (const callback of this._eventCallbacks[eventName]) {
                    if (!this._callbackWorking.has(callback)) {
                        this._callbackWorking.add(callback);
                        callback(args);
                        this._callbackWorking.delete(callback);
                    }
                }
            }
        }
    }

    var ModifierLevel;
    (function (ModifierLevel) {
        ModifierLevel[ModifierLevel["LOW"] = 0] = "LOW";
        ModifierLevel[ModifierLevel["MEDIUM"] = 1] = "MEDIUM";
        ModifierLevel[ModifierLevel["HIGH"] = 2] = "HIGH";
    })(ModifierLevel || (ModifierLevel = {}));
    class Modifier extends EventMixin {
        constructor() {
            super();
            this.preserveAfterNode = true; // True to preserve modifier after the node that holds it.
            this.preserveAfterParagraphBreak = true; // True to preserve modifier after a paragraph break.
            this.preserveAfterLineBreak = true; // True to preserve modifier after a line break.
            this.level = ModifierLevel.MEDIUM;
            return makeVersionable(this);
        }
        get name() {
            return '';
        }
        toString() {
            return this.name;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        applyTo(node) {
            node.modifiers.prepend(this);
        }
        isSameAs(otherModifier) {
            return this === otherModifier;
        }
        clone() {
            return new this.constructor();
        }
    }

    class CssStyle extends EventMixin {
        constructor(style) {
            super();
            if (style) {
                this.reset(style);
            }
            return makeVersionable(this);
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * Return the number of styles in the set.
         */
        get length() {
            return this._style ? Object.keys(this._style).length : 0;
        }
        /**
         * Return a textual representation of the CSS declaration block.
         */
        get cssText() {
            if (!this._style) {
                return;
            }
            const keys = Object.keys(this._style);
            if (!Object.keys(this._style).length)
                return;
            const valueRepr = [];
            for (const key of keys) {
                valueRepr.push(`${key}: ${this._style[key]}`);
            }
            let result = valueRepr.join('; ');
            if (valueRepr.length) {
                result += ';';
            }
            return result;
        }
        /**
         * Reinitialize the record with a new record of styles, from a string to
         * parse.
         */
        set cssText(cssText) {
            this.reset(cssText);
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new record of styles, parsed from a cssText string.
         *
         * @param className
         */
        parseCssText(cssText) {
            const style = {};
            const css = cssText
                .split(';')
                .map(style => style.trim())
                .filter(style => style.length)
                .reduce((accumulator, value) => {
                const [key, ...v] = value.split(':');
                style[key.trim()] = v.join(':').trim();
                return accumulator;
            }, style);
            this.trigger('update');
            return css;
        }
        /**
         * Return a clone of this record.
         */
        clone() {
            const clone = new CssStyle();
            if (this._style) {
                clone._style = makeVersionable(Object.assign({}, this._style));
            }
            return clone;
        }
        /**
         * Return the style value as record.
         */
        toJSON() {
            const style = {};
            const _style = this._style;
            for (const key in _style) {
                style[key] = _style[key];
            }
            return style;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if the record has the given style, false otherwise.
         *
         * @param key
         */
        has(key) {
            var _a;
            return !!((_a = this._style) === null || _a === void 0 ? void 0 : _a[key]);
        }
        /**
         * Return an array containing all the keys in the record.
         */
        keys() {
            return this._style ? Object.keys(this._style) : [];
        }
        /**
         * Return an array containing all the values in the record.
         */
        values() {
            return this._style ? Object.values(this._style) : [];
        }
        /**
         * Return the record matching the given name.
         *
         * @param name
         */
        get(name) {
            var _a;
            return (_a = this._style) === null || _a === void 0 ? void 0 : _a[name];
        }
        set(pairsOrName, value) {
            if (!this._style) {
                this._style = makeVersionable({});
            }
            if (typeof pairsOrName === 'string') {
                this._style[pairsOrName] = value;
                this.trigger('update');
            }
            else {
                const names = Object.keys(pairsOrName);
                for (const name of names) {
                    this._style[name] = pairsOrName[name];
                }
                if (names.length) {
                    this.trigger('update');
                }
            }
        }
        /**
         * Remove the record(s) with the given name(s).
         *
         * @param name
         */
        remove(...names) {
            if (this._style) {
                for (const name of names) {
                    delete this._style[name];
                }
            }
            if (names.length) {
                this.trigger('update');
            }
        }
        /**
         * Clear the record of all its styles.
         */
        clear() {
            delete this._style;
            this.trigger('update');
        }
        /**
         * Reinitialize the record with a new record of styles (empty if no argument
         * is passed). The argument can be a record of styles or a string to parse.
         *
         * @param style
         */
        reset(style = '') {
            if (typeof style === 'object') {
                if (Object.keys(style).length) {
                    this._style = makeVersionable(style);
                    this.trigger('update');
                }
                else {
                    delete this._style;
                    this.trigger('update');
                }
            }
            else if (style.length) {
                this._style = makeVersionable(this.parseCssText(style));
            }
            else {
                delete this._style;
                this.trigger('update');
            }
        }
    }

    class ClassList extends EventMixin {
        constructor(...classList) {
            super();
            for (const className of classList) {
                this.add(className);
            }
            return makeVersionable(this);
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * Return the number of classes in the set.
         */
        get length() {
            return this._classList ? this.items().length : 0;
        }
        /**
         * Return a textual representation of the set.
         */
        get className() {
            if (!this.length)
                return;
            return this.items().join(' ');
        }
        /**
         * Reinitialize the set with a new set of classes, from a string to parse.
         */
        set className(className) {
            this.reset(className);
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new set of classes, parsed from a className string.
         *
         * @param className
         */
        parseClassName(className) {
            const classList = new Set(className
                .trim()
                .split(/\s+/)
                .filter(c => c.length));
            this.trigger('update');
            return classList;
        }
        /**
         * Return a clone of this list.
         */
        clone() {
            const clone = new ClassList();
            // TODO: Maybe this should copy the entire history rather than only the
            // currently active classes ?
            clone.add(...this.items());
            return clone;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if the set has the given class, false otherwise.
         *
         * @param name
         */
        has(name) {
            var _a;
            return ((_a = this._classList) === null || _a === void 0 ? void 0 : _a[name]) || false;
        }
        /**
         * Return an array containing all the items in the list.
         */
        items() {
            return this._classList
                ? Object.keys(this._classList).filter(key => this._classList[key])
                : [];
        }
        /**
         * Return a record containing all the past and current classes. Classes that
         * are not active anymore have their value set to `false`.
         *
         */
        history() {
            return Object.assign(Object.assign({}, this._classList) || {});
        }
        /**
         * Add the given class(es) to the set.
         *
         * @param classNames
         */
        add(...classNames) {
            if (!this._classList) {
                this._classList = new VersionableObject();
            }
            for (const className of classNames) {
                if (className) {
                    const classes = this.parseClassName(className);
                    for (const name of classes) {
                        this._classList[name] = true;
                    }
                }
            }
            if (classNames.length) {
                this.trigger('update');
            }
        }
        /**
         * Remove the given class(es) from the set.
         *
         * @param classNames
         */
        remove(...classNames) {
            if (!this._classList)
                return;
            for (const className of classNames) {
                if (className) {
                    const classes = this.parseClassName(className);
                    for (const name of classes) {
                        this._classList[name] = false;
                    }
                }
            }
            if (classNames.length) {
                this.trigger('update');
            }
        }
        /**
         * Clear the set of all its classes.
         */
        clear() {
            delete this._classList;
            this.trigger('update');
        }
        /**
         * Reinitialize the set with a new set of classes (empty if no argument is
         * passed). The argument can be a set of classes or a string to parse.
         *
         * @param classList
         */
        reset(...classList) {
            delete this._classList;
            for (const className of classList) {
                this.add(className);
            }
            if (classList.length) {
                this.trigger('update');
            }
        }
        /**
         * For each given class, add it to the set if it doesn't have it yet,
         * otherwise remove it.
         *
         * @param classes
         */
        toggle(...classes) {
            if (!this._classList) {
                this._classList = new VersionableObject();
            }
            for (const className of classes) {
                if (className) {
                    const parsed = this.parseClassName(className);
                    for (const name of parsed) {
                        if (this._classList[name]) {
                            this._classList[name] = false;
                        }
                        else {
                            this._classList[name] = true;
                        }
                    }
                }
            }
            if (classes.length) {
                this.trigger('update');
            }
        }
    }

    class Attributes extends Modifier {
        constructor(attributes) {
            super();
            this.level = ModifierLevel.LOW;
            this.style = new CssStyle();
            // Avoid copiying FontAwesome classes on paragraph break.
            // TODO : need to be improved to better take care of color classes, etc.
            this.preserveAfterParagraphBreak = false;
            this.classList = new ClassList();
            this.style.on('update', this._triggerUpdate.bind(this));
            this.classList.on('update', this._triggerUpdate.bind(this));
            if (attributes instanceof Attributes) {
                for (const key of attributes.keys()) {
                    this.set(key, attributes.get(key));
                }
            }
            else if (attributes instanceof NamedNodeMap) {
                for (const attribute of Array.from(attributes)) {
                    this.set(attribute.name, attribute.value);
                }
            }
            else if (attributes) {
                for (const key of Object.keys(attributes)) {
                    this.set(key, attributes[key]);
                }
            }
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        get length() {
            return this.keys().length;
        }
        get name() {
            const name = [];
            for (const attributeName of this.keys()) {
                name.push(`${attributeName}: "${this.get(attributeName)}"`);
            }
            return `{${name.join(', ')}}`;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a clone of this record.
         */
        clone() {
            const clone = new this.constructor();
            if (this._record) {
                clone._record = makeVersionable(Object.assign({}, this._record));
            }
            if (this.style.length) {
                clone.style = this.style.clone();
            }
            if (this.classList.length) {
                clone.classList = this.classList.clone();
            }
            return clone;
        }
        /**
         * Return a string representing the attributes.
         */
        toString() {
            if (!this.length)
                return `${this.constructor.name}: {}`;
            const valueRepr = [];
            for (const key of this.keys()) {
                valueRepr.push(`${key}: "${this.get(key)}"`);
            }
            return `${this.constructor.name}: { ${valueRepr.join(', ')} }`;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if the record has the given key, false otherwise.
         *
         * @param key
         */
        has(key) {
            return this.keys().includes(key.toLowerCase());
        }
        /**
         * Return an array containing all the keys in the record.
         */
        keys() {
            const keys = this._record
                ? Object.keys(this._record).filter(key => {
                    return ((key !== 'style' || !!this.style.length) &&
                        (key !== 'class' || !!this.classList.length));
                })
                : [];
            if (this.classList.length && !keys.includes('class')) {
                // The node was not parsed with a class attribute, add it in place.
                // Use `get` for its value but record its position in the record.
                keys.push('class');
            }
            if (this.style.length && !keys.includes('style')) {
                // The node was not parsed with a style attribute, keep it always at
                // the end of the attributes list.
                keys.push('style');
            }
            return keys;
        }
        /**
         * Return an array containing all the values in the record.
         */
        values() {
            return this.keys().map(key => this.get(key));
        }
        /**
         * Return the record matching the given name.
         *
         * @param name
         */
        get(name) {
            var _a, _b, _c;
            name = name.toLowerCase();
            if (name === 'style') {
                return (_a = this.style) === null || _a === void 0 ? void 0 : _a.cssText;
            }
            else if (name === 'class') {
                return (_b = this.classList) === null || _b === void 0 ? void 0 : _b.className;
            }
            else {
                return (_c = this._record) === null || _c === void 0 ? void 0 : _c[name];
            }
        }
        /**
         * Set the record with the given name to the given value.
         *
         * @param name
         * @param value
         */
        set(name, value) {
            name = name.toLowerCase();
            if (!this._record) {
                this._record = makeVersionable({});
            }
            if (name === 'style') {
                if (this.style) {
                    this.style.reset(value);
                }
                else {
                    this.style = new CssStyle();
                    this.style.on('update', this._triggerUpdate.bind(this));
                }
                // Use `get` for its value but record its position in the record.
                this._record.style = null;
            }
            else if (name === 'class') {
                this.classList.reset(value);
                // Use `get` for its value but record its position in the record.
                this._record.class = null;
            }
            else {
                this._record[name] = value;
            }
            this.trigger('update');
        }
        /**
         * Remove the records with the given names.
         *
         * @param names
         */
        remove(...names) {
            for (let name of names) {
                name = name.toLowerCase();
                if (name === 'style') {
                    this.style.clear();
                }
                else if (name === 'class') {
                    this.classList.clear();
                }
                else if (this._record) {
                    delete this._record[name];
                }
            }
            if (names.length) {
                this.trigger('update');
            }
        }
        clear() {
            delete this._record;
            this.style.clear();
            this.classList.clear();
            this.trigger('update');
        }
        /**
         * Return true if the given attributes are the same as the ones in this
         * record.
         *
         * @param otherAttributes
         */
        isSameAs(otherAttributes) {
            if (otherAttributes) {
                return (this.length === otherAttributes.length &&
                    this.keys().every(key => {
                        return this.get(key) === otherAttributes.get(key);
                    }));
            }
            else {
                return !this.length;
            }
        }
        /**
         * @override
         */
        off(eventName, callback) {
            super.off(eventName, callback);
            this.classList.off(eventName, callback);
            this.style.off(eventName, callback);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _triggerUpdate() {
            this.trigger('update');
        }
    }

    /**
     * Return whether the given constructor is a constructor of given superClass.
     *
     * @param constructor
     * @param superClass
     */
    function isConstructor(constructor, superClass) {
        return constructor.prototype instanceof superClass || constructor === superClass;
    }
    /**
     * Return true if the node or modifier has a modifier with the `contentEditable`
     * attribute.
     *
     * @param nodeOrModifier
     */
    function hasContentEditable(nodeOrModifier) {
        var _a;
        if ('modifiers' in nodeOrModifier) {
            return ((_a = nodeOrModifier.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.has('contentEditable')) || false;
        }
    }
    /**
     * Return true if the node or modifier has a modifier with the `contentEditable`
     * attribute set to true. This implies that its children are editable but it is
     * not necessarily itself editable.
     *
     * TODO: unbind from `Attributes`.
     */
    function isContentEditable(nodeOrModifier) {
        var _a;
        if ('modifiers' in nodeOrModifier) {
            const editable = (_a = nodeOrModifier.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.get('contentEditable');
            return editable === '' || (editable === null || editable === void 0 ? void 0 : editable.toLowerCase()) === 'true' || false;
        }
    }
    /**
     * Creates a new array with all sub-array elements concatenated into it.
     */
    function flat(arr) {
        return [].concat(...arr);
    }
    /**
     * Return the length of a DOM Node.
     *
     * @param node
     */
    function nodeLength(node) {
        const content = isInstanceOf(node, Text) ? node.nodeValue : node.childNodes;
        return content.length;
    }
    /**
     * Return a duplicate-free version of an array.
     *
     * @param array
     */
    function distinct(array) {
        return Array.from(new Set(array));
    }
    /**
     * Return the uppercase name of the given DOM node.
     *
     * @param node
     */
    function nodeName(node) {
        return node === null || node === void 0 ? void 0 : node.nodeName.toUpperCase();
    }
    /**
     * Check if the editor selection is in a textual context, meaning that it either
     * contains text or is collapsed (in which case text can be inserted).
     */
    function isInTextualContext(editor) {
        const range = editor.selection.range;
        if (range.isCollapsed()) {
            return true;
        }
        else {
            const end = range.end.nextLeaf();
            let node = range.start.nextLeaf();
            while (node && node !== end) {
                if (node.textContent.length) {
                    return true;
                }
                else {
                    node = node.nextLeaf();
                }
            }
            return false;
        }
    }
    function getDocument(node) {
        let root;
        while (node && !root) {
            if (node instanceof Document || node instanceof ShadowRoot) {
                root = node;
            }
            else {
                node = node.parentNode;
            }
        }
        return root || document;
    }
    function isInstanceOf(instance, Class) {
        if (!instance || !Class)
            return false;
        if (instance instanceof Class)
            return true;
        let proto = Object.getPrototypeOf(instance);
        while (proto) {
            if (proto.constructor.name === Class.name)
                return true;
            proto = Object.getPrototypeOf(proto);
        }
        return false;
    }

    class Modifiers extends EventMixin {
        constructor(...modifiers) {
            super();
            const clonedModifiers = modifiers.map(mod => {
                return mod instanceof Modifier ? mod.clone() : mod;
            });
            this.append(...clonedModifiers);
            return makeVersionable(this);
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * Return the length of the array.
         */
        get length() {
            var _a;
            return ((_a = this._contents) === null || _a === void 0 ? void 0 : _a.length) || 0;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new instance of the Modifiers class containing the same
         * modifiers.
         */
        clone() {
            if (this._contents) {
                return new Modifiers(...this._contents);
            }
            else {
                return new Modifiers();
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Append one or more modifiers to the array. If one of the given modifiers
         * is a modifier class constructor, instantiate it.
         *
         * @param modifiers
         */
        append(...modifiers) {
            if (modifiers.length && !this._contents) {
                this._contents = new VersionableArray();
            }
            for (const modifier of modifiers) {
                const newModifier = modifier instanceof Modifier ? modifier : new modifier();
                newModifier.on('update', () => this.trigger('update'));
                this._contents.push(newModifier);
            }
            if (modifiers.length) {
                this.trigger('update');
            }
        }
        /**
         * Prepend one or more modifiers to the array. If one of the given modifiers
         * is a modifier class constructor, instantiate it.
         *
         * @param modifiers
         */
        prepend(...modifiers) {
            if (modifiers.length && !this._contents) {
                this._contents = new VersionableArray();
            }
            for (const modifier of [...modifiers].reverse()) {
                const newModifier = modifier instanceof Modifier ? modifier : new modifier();
                newModifier.on('update', () => this.trigger('update'));
                this._contents.unshift(newModifier);
            }
            if (modifiers.length) {
                this.trigger('update');
            }
        }
        find(modifier) {
            if (!this._contents) {
                return;
            }
            else if (modifier instanceof Modifier) {
                // `modifier` is an instance of `Modifier` -> find it in the array.
                return this._contents.find(instance => instance === modifier);
            }
            else if (isConstructor(modifier, Modifier)) {
                // `modifier` is a `Modifier` class -> find its first instance in
                // the array.
                return this._contents.find(mod => mod.constructor.name === modifier.name);
            }
            else if (modifier instanceof Function) {
                // `modifier` is a callback -> call `find` natively on the array.
                return this._contents.find(modifier);
            }
        }
        /**
         * Return the first modifier in the array that is an instance of the given
         * modifier class or create one, append it and return it.
         * If the modifier passed is a modifier instance, return it if it was
         * present in the array.
         *
         * @param modifier
         */
        get(modifier) {
            let found = this.find(modifier);
            if (!found && isConstructor(modifier, Modifier)) {
                found = new modifier();
                this.append(found);
            }
            return found;
        }
        filter(modifier, 
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        thisArg) {
            if (!this._contents) {
                return [];
            }
            else if (isConstructor(modifier, Modifier)) {
                // `modifier` is a `Modifier` class -> return all instances of it in
                // the array.
                return this._contents.filter(m => m instanceof modifier);
            }
            else {
                // `modifier` is a callback -> call `filter` natively on the array.
                return this._contents.filter(modifier, thisArg);
            }
        }
        /**
         * Remove the first modifier in the array that is an instance of the given
         * modifier class. If a modifier instance is given, remove that particuar
         * instance from the array. Return true if a modifier was removed, false
         * otherwise.
         *
         * @param modifier
         */
        remove(modifier) {
            if (!this._contents) {
                return false;
            }
            const modifierIndex = this._contents.findIndex(modifierInstance => {
                if (modifier instanceof Modifier) {
                    return modifierInstance === modifier;
                }
                else {
                    return modifierInstance instanceof modifier;
                }
            });
            if (modifierIndex === -1) {
                return false;
            }
            else {
                this._contents[modifierIndex].off('update');
                this._contents.splice(modifierIndex, 1);
                this.trigger('update');
                return true;
            }
        }
        /**
         * Replace the first modifier in the array that is an instance of the given
         * modifier class or that matches the particular instance passed with the
         * given modifier instance. If the new modifier passed is a class,
         * instantiate it. If no modifier was found, simply push the new modifier on
         * the array.
         *
         * Return true if a modifier was replaced, false if the modifier was simply
         * added.
         *
         * @param oldModifier
         * @param newModifier
         */
        replace(oldModifier, newModifier) {
            var _a;
            const oldModifierIndex = (_a = this._contents) === null || _a === void 0 ? void 0 : _a.findIndex(modifierInstance => {
                if (oldModifier instanceof Modifier) {
                    return modifierInstance === oldModifier;
                }
                else {
                    return modifierInstance instanceof oldModifier;
                }
            });
            if (!this._contents || oldModifierIndex === -1) {
                this.append(newModifier);
                return false;
            }
            else {
                const modifier = newModifier instanceof Modifier ? newModifier : new newModifier();
                modifier.on('update', () => this.trigger('update'));
                this._contents[oldModifierIndex].off('update');
                this._contents[oldModifierIndex] = modifier;
                this.trigger('update');
                return true;
            }
        }
        /**
         * Set the given modifiers on this Modifiers instance. Replace the modifiers
         * with same constructor if they exist, otherwise append the modifiers.
         *
         * @param modfiers
         */
        set(...modifiers) {
            for (const modifier of modifiers) {
                if (modifier instanceof Modifier) {
                    this.replace(modifier.constructor, modifier);
                }
                else {
                    this.replace(modifier, modifier);
                }
            }
        }
        /**
         * Remove the first modifier in the array that is an instance of the given
         * modifier class or that matches the particular instance passed.
         * If no modifier was found, add the given modifier instead.
         * If the given new modifier is a class, instantiate it.
         *
         * @param modifier
         */
        toggle(modifier) {
            this.remove(modifier) || this.append(modifier);
        }
        /**
         * Return true if the modifiers in this array are the same as the modifiers
         * in the given array (as defined by the `isSameAs` methods of the
         * modifiers).
         *
         * @param otherModifiers
         */
        areSameAs(otherModifiers) {
            var _a;
            const modifiersMap = new Map(((_a = this._contents) === null || _a === void 0 ? void 0 : _a.map(a => [a, otherModifiers.find(b => a.isSameAs(b))])) || []);
            const aModifiers = Array.from(modifiersMap.keys());
            const bModifiers = Array.from(modifiersMap.values());
            const allAinB = aModifiers.every(a => a.isSameAs(modifiersMap.get(a)));
            const allBinA = otherModifiers.every(b => bModifiers.includes(b) || b.isSameAs(this.find(b)));
            return allAinB && allBinA;
        }
        /**
         * Remove all modifiers.
         */
        empty() {
            if (this._contents) {
                for (const modifier of this._contents) {
                    modifier.off('update');
                }
                this._contents.length = 0;
                this.trigger('update');
            }
        }
        /**
         * Proxy for the native `some` method of `Array`, called on `this._contents`.
         *
         * @see Array.some
         * @param callbackfn
         */
        some(callbackfn) {
            var _a;
            return ((_a = this._contents) === null || _a === void 0 ? void 0 : _a.some(callbackfn)) || false;
        }
        /**
         * Proxy for the native `every` method of `Array`, called on `this._contents`.
         *
         * @see Array.every
         * @param callbackfn
         */
        every(callbackfn) {
            return this._contents ? this._contents.every(callbackfn) : true;
        }
        /**
         * Proxy for the native `map` method of `Array`, called on `this._contents`.
         *
         * @see Array.map
         * @param callbackfn
         */
        map(callbackfn) {
            var _a;
            return ((_a = this._contents) === null || _a === void 0 ? void 0 : _a.map(callbackfn)) || [];
        }
        /**
         * @override
         */
        off(eventName, callback) {
            super.off(eventName, callback);
            if (this._contents) {
                for (const modifier of this._contents) {
                    modifier.off(eventName, callback);
                }
            }
        }
    }

    let id = 0;
    class AbstractNode extends EventMixin {
        constructor(params) {
            super();
            this.id = id;
            /**
             * True If the node will have a representation in the dom. Eg: markers are
             * not tangible.
             */
            this.tangible = true;
            /**
             * True if the node can be split.
             * Can be overridden with a `Mode`.
             */
            this.breakable = true;
            id++;
            this.modifiers = new Modifiers();
            if (params === null || params === void 0 ? void 0 : params.modifiers) {
                if (params.modifiers instanceof Modifiers) {
                    this.modifiers = params.modifiers;
                }
                else {
                    this.modifiers.append(...params.modifiers);
                }
            }
            const node = makeVersionable(this);
            markAsDiffRoot(node);
            return node;
        }
        /**
         * True if the node is editable. Propagates to the children.
         * A node that is editable can have its modifiers edited, be moved, removed,
         * and a selection can be made within it.
         * Can be overridden with a `Mode`.
         */
        get editable() {
            if (this._editable === false)
                return false;
            const modifiers = this.modifiers.filter(mod => 'modifiers' in mod);
            const lastModifierWithContentEditable = modifiers.reverse().find(modifier => {
                return hasContentEditable(modifier);
            });
            if (lastModifierWithContentEditable) {
                return isContentEditable(lastModifierWithContentEditable);
            }
            return (!this.parent ||
                (hasContentEditable(this.parent)
                    ? isContentEditable(this.parent)
                    : this.parent.editable));
        }
        set editable(state) {
            this._editable = state;
        }
        /**
         * Return whether the given predicate is a constructor of a VNode class.
         *
         * @param predicate The predicate to check.
         */
        static isConstructor(predicate) {
            return predicate.prototype instanceof AbstractNode;
        }
        get modifiers() {
            return this._modifiers;
        }
        set modifiers(modifiers) {
            if (this._modifiers) {
                this._modifiers.off('update');
            }
            this._modifiers = modifiers;
            this._modifiers.on('update', () => this.trigger('modifierUpdate'));
        }
        get name() {
            return this.constructor.name;
        }
        /**
         * Return the text content of this node.
         */
        get textContent() {
            return this.children()
                .map(child => child.textContent)
                .join('');
        }
        /**
         * @override
         */
        toString() {
            return this.name;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Transform the given DOM location into its VDocument counterpart.
         *
         * @param domNode DOM node corresponding to this VNode
         * @param offset The offset of the location in the given domNode
         */
        locate(domNode, offset) {
            // Position `BEFORE` is preferred over `AFTER`, unless the offset
            // overflows the children list, in which case `AFTER` is needed.
            let position = RelativePosition.BEFORE;
            const domNodeLength = nodeLength(domNode);
            if (domNodeLength && offset >= domNodeLength) {
                position = RelativePosition.AFTER;
            }
            return [this, position];
        }
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(params) {
            const clone = new this.constructor(params);
            clone.modifiers = this.modifiers.clone();
            return clone;
        }
        /**
         * Replace this VNode with the given VNode.
         *
         * @param node
         */
        replaceWith(node) {
            this.before(node);
            this.mergeWith(node);
        }
        //--------------------------------------------------------------------------
        // Properties
        //--------------------------------------------------------------------------
        /**
         * Return the length of this VNode.
         */
        get length() {
            return this.children().length;
        }
        /**
         * Test this node against the given predicate.
         *
         * If the predicate is falsy, return true. If the predicate is a constructor
         * of a VNode class, return whether this node is an instance of that class.
         * If the predicate is a standard function, return the result of this
         * function when called with the node as parameter.
         *
         *
         * @param predicate The predicate to test this node against.
         */
        test(predicate) {
            if (!predicate) {
                return true;
            }
            else if (AbstractNode.isConstructor(predicate)) {
                return this instanceof predicate;
            }
            else {
                return predicate(this);
            }
        }
        /**
         * Return true if this VNode comes before the given VNode in the pre-order
         * traversal.
         *
         * @param vNode
         */
        isBefore(vNode) {
            const thisPath = [this, ...this.ancestors()];
            const nodePath = [vNode, ...vNode.ancestors()];
            // Find the last distinct ancestors in the path to the root.
            let thisAncestor;
            let nodeAncestor;
            do {
                thisAncestor = thisPath.pop();
                nodeAncestor = nodePath.pop();
            } while (thisAncestor && nodeAncestor && thisAncestor === nodeAncestor);
            if (thisAncestor && nodeAncestor) {
                const thisParent = thisAncestor.parent;
                const nodeParent = nodeAncestor.parent;
                if (thisParent && thisParent === nodeParent) {
                    // Compare the indices of both ancestors in their shared parent.
                    const thisIndex = thisParent.childVNodes.indexOf(thisAncestor);
                    const nodeIndex = nodeParent.childVNodes.indexOf(nodeAncestor);
                    return thisIndex < nodeIndex;
                }
                else {
                    // The very first ancestor of both nodes are different so
                    // they actually come from two different trees altogether.
                    return false;
                }
            }
            else {
                // One of the nodes was in the ancestors path of the other.
                return !thisAncestor && !!nodeAncestor;
            }
        }
        /**
         * Return true if this VNode comes after the given VNode in the pre-order
         * traversal.
         *
         * @param vNode
         */
        isAfter(vNode) {
            return vNode.isBefore(this);
        }
        closest(predicate) {
            if (this.test(predicate)) {
                return this;
            }
            else {
                return this.ancestor(predicate);
            }
        }
        ancestor(predicate) {
            let ancestor = this.parent;
            while (ancestor && !ancestor.test(predicate)) {
                ancestor = ancestor.parent;
            }
            return ancestor;
        }
        ancestors(predicate) {
            const ancestors = [];
            let parent = this.parent;
            while (parent) {
                if (parent.test(predicate)) {
                    ancestors.push(parent);
                }
                parent = parent.parent;
            }
            return ancestors;
        }
        commonAncestor(node, predicate) {
            if (!this.parent) {
                return;
            }
            else if (this.parent === node.parent && this.parent.test(predicate)) {
                return this.parent;
            }
            const thisPath = [this, ...this.ancestors(predicate)];
            const nodePath = [node, ...node.ancestors(predicate)];
            let commonAncestor;
            while (thisPath[thisPath.length - 1] === nodePath.pop()) {
                commonAncestor = thisPath.pop();
            }
            return commonAncestor;
        }
        siblings(predicate) {
            const siblings = [];
            let sibling = this.previousSibling();
            while (sibling) {
                if (sibling.test(predicate)) {
                    siblings.unshift(sibling);
                }
                sibling = sibling.previousSibling();
            }
            sibling = this.nextSibling();
            while (sibling) {
                if (sibling.test(predicate)) {
                    siblings.push(sibling);
                }
                sibling = sibling.nextSibling();
            }
            return siblings;
        }
        adjacents(predicate) {
            const adjacents = [];
            let sibling = this.previousSibling();
            while (sibling && sibling.test(predicate)) {
                adjacents.unshift(sibling);
                sibling = sibling.previousSibling();
            }
            if (this.test(predicate)) {
                adjacents.push(this);
            }
            sibling = this.nextSibling();
            while (sibling && sibling.test(predicate)) {
                adjacents.push(sibling);
                sibling = sibling.nextSibling();
            }
            return adjacents;
        }
        previousSibling(predicate) {
            if (!this.parent)
                return;
            const index = this.parent.childVNodes.indexOf(this);
            let sibling = this.parent.childVNodes[index - 1];
            // Skip ignored siblings and those failing the predicate test.
            while (sibling && !(sibling.tangible && sibling.test(predicate))) {
                sibling = sibling.previousSibling();
            }
            return sibling;
        }
        nextSibling(predicate) {
            if (!this.parent)
                return;
            const index = this.parent.childVNodes.indexOf(this);
            let sibling = this.parent.childVNodes[index + 1];
            // Skip ignored siblings and those failing the predicate test.
            while (sibling && !(sibling.tangible && sibling.test(predicate))) {
                sibling = sibling.nextSibling();
            }
            return sibling;
        }
        previous(predicate) {
            let previous = this.previousSibling();
            if (previous) {
                // The previous node is the last leaf of the previous sibling.
                previous = previous.lastLeaf();
            }
            else {
                // If it has no previous sibling then climb up to the parent.
                previous = this.parent;
            }
            while (previous && !previous.test(predicate)) {
                previous = previous.previous();
            }
            return previous;
        }
        next(predicate) {
            // The node after node is its first child.
            let next = this.firstChild();
            if (!next) {
                // If it has no children then it is its next sibling.
                next = this.nextSibling();
            }
            if (!next) {
                // If it has no siblings either then climb up to the closest parent
                // which has a next sibiling.
                let ancestor = this.parent;
                while (ancestor && !ancestor.nextSibling()) {
                    ancestor = ancestor.parent;
                }
                next = ancestor && ancestor.nextSibling();
            }
            while (next && !next.test(predicate)) {
                next = next.next();
            }
            return next;
        }
        previousLeaf(predicate) {
            return this.previous((node) => {
                return isLeaf(node) && node.test(predicate);
            });
        }
        nextLeaf(predicate) {
            return this.next((node) => {
                return isLeaf(node) && node.test(predicate);
            });
        }
        previousSiblings(predicate) {
            const previousSiblings = [];
            let sibling = this.previousSibling();
            while (sibling) {
                if (sibling.test(predicate)) {
                    previousSiblings.push(sibling);
                }
                sibling = sibling.previousSibling();
            }
            return previousSiblings;
        }
        nextSiblings(predicate) {
            const nextSiblings = [];
            let sibling = this.nextSibling();
            while (sibling) {
                if (sibling.test(predicate)) {
                    nextSiblings.push(sibling);
                }
                sibling = sibling.nextSibling();
            }
            return nextSiblings;
        }
        //--------------------------------------------------------------------------
        // Updating
        //--------------------------------------------------------------------------
        /**
         * Insert the given VNode before this VNode.
         *
         * @param node
         */
        before(node) {
            if (!this.parent) {
                throw new Error('Cannot insert a VNode before a VNode with no parent.');
            }
            this.parent.insertBefore(node, this);
        }
        /**
         * Insert the given VNode after this VNode.
         *
         * @param node
         */
        after(node) {
            if (!this.parent) {
                throw new Error('Cannot insert a VNode after a VNode with no parent.');
            }
            this.parent.insertAfter(node, this);
        }
        /**
         * Wrap this node in the given node by inserting the given node at this
         * node's position in its parent and appending this node to the given node.
         *
         * @param node
         */
        wrap(node) {
            this.before(node);
            node.append(this);
        }
        /**
         * Remove this node.
         */
        remove() {
            if (this.parent) {
                this.parent.removeChild(this);
            }
        }
        /**
         * Remove this node in forward direction. (e.g. `Delete` key)
         */
        removeForward() {
            this.remove();
        }
        /**
         * Remove this node in backward direction. (e.g. `Backspace` key)
         */
        removeBackward() {
            this.remove();
        }
        //--------------------------------------------------------------------------
        // Events.
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        async trigger(eventName, args) {
            super.trigger(eventName, args);
            if (this.parent) {
                await this.parent.trigger(eventName, args);
            }
        }
        //--------------------------------------------------------------------------
        // Private.
        //--------------------------------------------------------------------------
        /**
         * Return a convenient string representation of this node and its
         * descendants.
         *
         * @param __repr
         * @param level
         */
        _repr(__repr = '', level = 0) {
            __repr += Array(level * 4 + 1).join(' ') + this.name + ' (' + this.id + ')' + '\n';
            this.childVNodes.forEach(child => {
                __repr = child._repr(__repr, level + 1);
            });
            return __repr;
        }
    }

    /**
     * This class provides typing overrides for multiple VNode methods which are
     * supposed to take parameters but that are unused in the case of atomic nodes.
     */
    /* eslint-disable @typescript-eslint/no-unused-vars */
    class AtomicNode extends AbstractNode {
        get childVNodes() {
            return [];
        }
        children(predicate) {
            return [];
        }
        /**
         * See {@link AbstractNode.hasChildren}.
         *
         * @return Returns `false` since an atomic node cannot have children.
         */
        hasChildren() {
            return false;
        }
        /**
         * See {@link AbstractNode.nthChild}.
         *
         * @return Returns `undefined` since an atomic node cannot have children.
         */
        nthChild(n) {
            return undefined;
        }
        firstChild(predicate) {
            return undefined;
        }
        lastChild(predicate) {
            return undefined;
        }
        firstLeaf(predicate) {
            return this;
        }
        lastLeaf(predicate) {
            return this;
        }
        firstDescendant(predicate) {
            return undefined;
        }
        lastDescendant(predicate) {
            return undefined;
        }
        descendants(predicate) {
            return [];
        }
        //--------------------------------------------------------------------------
        // Updating children.
        //--------------------------------------------------------------------------
        /**
         * See {@link AbstractNode.prepend}.
         *
         * @throws AtomicityError An atomic node cannot have children.
         */
        prepend(...children) {
            throw new AtomicityError(this);
        }
        /**
         * See {@link AbstractNode.prepend}.
         *
         * @throws AtomicityError An atomic node cannot have children.
         */
        append(...children) {
            throw new AtomicityError(this);
        }
        /**
       /**
         * See {@link AbstractNode.insertBefore}.
         *
         * @throws AtomicityError An atomic node cannot have children.
         */
        insertBefore(node, reference) {
            throw new AtomicityError(this);
        }
        /**
         * See {@link AbstractNode.insertAfter}.
         *
         * @throws AtomicityError An atomic node cannot have children.
         */
        insertAfter(node, reference) {
            throw new AtomicityError(this);
        }
        /**
         * See {@link AbstractNode.empty}.
         */
        empty() {
            return;
        }
        /**
         * See {@link AbstractNode.removeChild}.
         *
         * @throws AtomicityError An atomic node cannot have children.
         */
        removeChild(child) {
            throw new AtomicityError(this);
        }
        /**
         * See {@link AbstractNode.splitAt}.
         *
         * @throws AtomicityError An atomic node cannot be split.
         */
        splitAt(child) {
            throw new AtomicityError(this);
        }
        /**
         * See {@link AbstractNode.mergeWith}.
         */
        mergeWith(newContainer) {
            return;
        }
        /**
         * See {@link AbstractNode.unwrap}.
         */
        unwrap() {
            return;
        }
    }

    class MarkerNode extends AtomicNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.tangible = false;
        }
    }
    MarkerNode.atomic = true;

    class ContainerNode extends AbstractNode {
        constructor() {
            super(...arguments);
            this.childVNodes = new VersionableArray();
            // Set to false if the container is not allowed to have other containers as
            // children.
            this.mayContainContainers = true;
        }
        children(predicate) {
            const children = [];
            this.childVNodes.forEach(child => {
                if (child.tangible && (!predicate || child.test(predicate))) {
                    children.push(child);
                }
            });
            return children;
        }
        /**
         * See {@link AbstractNode.hasChildren}.
         */
        hasChildren() {
            return !!this.childVNodes.find(child => child.tangible);
        }
        /**
         * See {@link AbstractNode.nthChild}.
         */
        nthChild(n) {
            return this.children()[n - 1];
        }
        firstChild(predicate) {
            let child = this.childVNodes[0];
            while (child && !(child.tangible && (!predicate || child.test(predicate)))) {
                child = child.nextSibling();
            }
            return child;
        }
        lastChild(predicate) {
            let child = this.childVNodes[this.childVNodes.length - 1];
            while (child && !(child.tangible && (!predicate || child.test(predicate)))) {
                child = child.previousSibling();
            }
            return child;
        }
        firstLeaf(predicate) {
            const isValidLeaf = (node) => {
                return isLeaf(node) && (!predicate || node.test(predicate));
            };
            if (isValidLeaf(this)) {
                return this;
            }
            else {
                return this.firstDescendant((node) => isValidLeaf(node));
            }
        }
        lastLeaf(predicate) {
            const isValidLeaf = (node) => {
                return isLeaf(node) && (!predicate || node.test(predicate));
            };
            if (isValidLeaf(this)) {
                return this;
            }
            else {
                return this.lastDescendant((node) => isValidLeaf(node));
            }
        }
        firstDescendant(predicate) {
            let firstDescendant = this.firstChild();
            while (firstDescendant && predicate && !firstDescendant.test(predicate)) {
                firstDescendant = this._descendantAfter(firstDescendant);
            }
            return firstDescendant;
        }
        lastDescendant(predicate) {
            let lastDescendant = this.lastChild();
            while (lastDescendant && lastDescendant.hasChildren()) {
                lastDescendant = lastDescendant.lastChild();
            }
            while (lastDescendant && predicate && !lastDescendant.test(predicate)) {
                lastDescendant = this._descendantBefore(lastDescendant);
            }
            return lastDescendant;
        }
        descendants(predicate) {
            const descendants = [];
            const stack = [...this.childVNodes];
            while (stack.length) {
                const node = stack.shift();
                if (node.tangible && (!predicate || node.test(predicate))) {
                    descendants.push(node);
                }
                if (node instanceof ContainerNode) {
                    stack.unshift(...node.childVNodes);
                }
            }
            return descendants;
        }
        //--------------------------------------------------------------------------
        // Updating
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(deepClone, params) {
            const clone = super.clone(params);
            if (deepClone) {
                for (const child of this.childVNodes) {
                    clone.append(child.clone(true));
                }
            }
            return clone;
        }
        /**
         * See {@link AbstractNode.prepend}.
         */
        prepend(...children) {
            for (const child of children) {
                this._insertAtIndex(child, 0);
            }
            if (children.find(child => child.tangible)) {
                this.trigger('childList');
            }
        }
        /**
         * See {@link AbstractNode.append}.
         */
        append(...children) {
            for (const child of children) {
                this._insertAtIndex(child, this.childVNodes.length);
            }
            if (children.find(child => child.tangible)) {
                this.trigger('childList');
            }
        }
        /**
         * See {@link AbstractNode.insertBefore}.
         */
        insertBefore(node, reference) {
            const index = this.childVNodes.indexOf(reference);
            if (index < 0) {
                throw new ChildError(this, node);
            }
            this._insertAtIndex(node, index);
            if (node.tangible) {
                this.trigger('childList');
            }
        }
        /**
         * See {@link AbstractNode.insertAfter}.
         */
        insertAfter(node, reference) {
            const index = this.childVNodes.indexOf(reference);
            if (index < 0) {
                throw new ChildError(this, node);
            }
            this._insertAtIndex(node, index + 1);
            if (node.tangible) {
                this.trigger('childList');
            }
        }
        /**
         * See {@link AbstractNode.empty}.
         */
        empty() {
            for (const child of [...this.childVNodes]) {
                child.remove();
            }
        }
        /**
         * See {@link AbstractNode.removeChild}.
         */
        removeChild(child) {
            const index = this.childVNodes.indexOf(child);
            if (index < 0) {
                throw new ChildError(this, child);
            }
            this._removeAtIndex(index);
        }
        /**
         * See {@link AbstractNode.splitAt}.
         */
        splitAt(child) {
            if (child.parent !== this) {
                throw new ChildError(this, child);
            }
            const duplicate = this.clone();
            const index = this.childVNodes.indexOf(child);
            const children = this.childVNodes.splice(index);
            duplicate.childVNodes.push(...children);
            for (const child of children) {
                child.parent = duplicate;
            }
            this.after(duplicate);
            return duplicate;
        }
        /**
         * See {@link AbstractNode.mergeWith}.
         */
        mergeWith(newContainer) {
            if (newContainer !== this) {
                if (newContainer.childVNodes.includes(this)) {
                    for (const child of this.childVNodes.slice()) {
                        newContainer.insertBefore(child, this);
                    }
                }
                else {
                    newContainer.append(...this.childVNodes);
                }
                this.remove();
            }
        }
        /**
         * See {@link AbstractNode.unwrap}.
         */
        unwrap() {
            for (const child of this.childVNodes.slice()) {
                this.before(child);
            }
            this.remove();
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return the descendant of this node that directly precedes the given node
         * in depth-first pre-order traversal.
         *
         * @param node
         */
        _descendantBefore(node) {
            let previous = node.previousSibling();
            if (previous) {
                // The node before node is the last leaf of its previous sibling.
                previous = previous.lastLeaf();
            }
            else if (node.parent !== this) {
                // If it has no previous sibling then climb up to the parent.
                // This is similar to `previous` but can't go further than `this`.
                previous = node.parent;
            }
            return previous;
        }
        /**
         * Return the descendant of this node that directly follows the given node
         * in depth-first pre-order traversal.
         *
         * @param node
         */
        _descendantAfter(node) {
            // The node after node is its first child.
            let next = node.firstChild();
            if (!next) {
                // If it has no children then it is its next sibling.
                next = node.nextSibling();
            }
            if (!next) {
                // If it has no siblings either then climb up to the closest parent
                // which has a next sibiling.
                // This is similar to `next` but can't go further than `this`.
                let ancestor = node.parent;
                while (ancestor !== this && !ancestor.nextSibling()) {
                    ancestor = ancestor.parent;
                }
                if (ancestor !== this) {
                    next = ancestor.nextSibling();
                }
            }
            return next;
        }
        /**
         * Insert a VNode at the given index within this VNode's children.
         *
         * @param child
         * @param index The index at which the insertion must take place within this
         * VNode's parent, holding marker nodes into account.
         */
        _insertAtIndex(child, index) {
            // TODO: checking `this.parent` is a hack so it will go directly to
            // `else` when parsing.
            if (this.parent && !this.mayContainContainers && child instanceof ContainerNode) {
                if (!this.parent) {
                    console.warn(`Cannot insert a container within a ${this.name}. ` +
                        'This container having no parent, can also not be split.');
                    return;
                }
                if (this.hasChildren()) {
                    const childAtIndex = this.childVNodes[index];
                    const duplicate = childAtIndex && this.splitAt(childAtIndex);
                    if (!this.hasChildren()) {
                        this.replaceWith(child);
                    }
                    else if (duplicate && !duplicate.hasChildren()) {
                        duplicate.replaceWith(child);
                    }
                    else {
                        this.after(child);
                    }
                }
                else {
                    this.replaceWith(child);
                }
            }
            else {
                if (child.parent) {
                    const currentIndex = child.parent.childVNodes.indexOf(child);
                    if (index && child.parent === this && currentIndex < index) {
                        index--;
                    }
                    child.parent.removeChild(child);
                }
                this.childVNodes.splice(index, 0, child);
                child.parent = this;
            }
        }
        /**
         * Remove the nth child from this node.
         *
         * @param index The index of the child to remove including marker nodes.
         */
        _removeAtIndex(index) {
            const child = this.childVNodes.splice(index, 1)[0];
            if (child.tangible) {
                this.trigger('childList');
            }
            child.modifiers.off('update');
            child.parent = undefined;
        }
    }

    class FragmentNode extends ContainerNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
        set parent(parent) {
            this.mergeWith(parent);
            parent.removeChild(this);
        }
    }

    class TagNode extends ContainerNode {
        constructor(params) {
            super();
            this.htmlTag = params.htmlTag;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(deepClone, params) {
            const defaults = {
                htmlTag: this.htmlTag,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
    }

    class TableRowNode extends TagNode {
        constructor(params) {
            super({ htmlTag: 'TR' });
            this.breakable = false;
            this.header = (params === null || params === void 0 ? void 0 : params.header) || false;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         *
         *  @override
         */
        clone(deepClone, params) {
            const defaults = {
                header: this.header,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        get name() {
            return super.name + (this.header ? ': header' : '');
        }
        /**
         * Return the index of this row in the table.
         */
        get rowIndex() {
            return this.ancestor(TableNode)
                .children(TableRowNode)
                .indexOf(this);
        }
        /**
         * Remove managment of colspan & rowspan for the remove cell.
         *
         * @override
         */
        _removeAtIndex(index) {
            const cell = this.childVNodes[index];
            if (cell instanceof TableCellNode) {
                cell.unmerge();
            }
            super._removeAtIndex(index);
        }
    }

    class TableNode extends TagNode {
        constructor(params) {
            super({ htmlTag: 'TABLE' });
            this.breakable = false;
            if (params && params.rowCount && params.columnCount) {
                this.reset(params.rowCount, params.columnCount);
            }
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        get name() {
            return super.name + ': ' + this.rowCount + 'x' + this.columnCount;
        }
        /**
         * Return an array of rows in this table, as arrays of cells.
         */
        get rows() {
            return this.children(TableRowNode).map(row => row.children(TableCellNode));
        }
        /**
         * Return an array of columns in this table, as arrays of cells.
         */
        get columns() {
            const columns = new Array(this.columnCount).fill(undefined);
            return columns.map((_, columnIndex) => this.children(TableRowNode).map(row => row.children(TableCellNode)[columnIndex]));
        }
        /**
         * Return the number of rows in this table.
         */
        get rowCount() {
            return this.children(TableRowNode).length;
        }
        /**
         * Return the number of columns in this table.
         */
        get columnCount() {
            return this.firstChild(TableRowNode).children(TableCellNode).length;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return the cell of this table that can be found at the given coordinates,
         * if any.
         *
         * @param rowIndex
         * @param columnIndex
         */
        getCellAt(rowIndex, columnIndex) {
            return this.children(TableRowNode)[rowIndex].children(TableCellNode)[columnIndex];
        }
        /**
         * Add a new row above the reference row (the row of the given reference
         * cell). Copy the styles and colspans of the cells of the reference row. If
         * the reference row traverses a rowspan, extend that rowspan.
         * If no `referenceCell` was passed, add a row on top of the table.
         *
         * @param [referenceCell]
         */
        addRowAbove(referenceCell) {
            if (!referenceCell) {
                referenceCell = this.firstDescendant(TableCellNode);
            }
            const referenceRow = referenceCell.ancestor(TableRowNode);
            const newRow = referenceRow.clone();
            referenceRow.before(newRow);
            for (const cell of referenceRow.children(TableCellNode)) {
                const clone = cell.clone();
                newRow.append(clone);
                // Handle managers.
                const manager = cell.managerCell;
                if (manager) {
                    if (manager.rowIndex === referenceRow.rowIndex) {
                        // If the current cell's manager is in the reference row,
                        // the clone's manager should be that manager's clone.
                        const managerClone = this.getCellAt(newRow.rowIndex, manager.columnIndex);
                        clone.mergeWith(managerClone);
                    }
                    else {
                        clone.mergeWith(manager);
                    }
                }
            }
        }
        /**
         * Add a new row below the reference row (the row of the given reference
         * cell). Copy the styles and colspans of the cells of the reference row. If
         * the reference row traverses a rowspan, extend that rowspan.
         * If no `referenceCell` was passed, add a row at the bottom of the table.
         * Note: a rowspan ending at the reference cell is not extended.
         *
         * @param [referenceCell]
         */
        addRowBelow(referenceCell) {
            if (!referenceCell) {
                referenceCell = this.lastDescendant(TableCellNode);
            }
            const rowIndex = referenceCell.rowIndex + referenceCell.rowspan - 1;
            const referenceRow = this.children(TableRowNode)[rowIndex];
            const newRow = referenceRow.clone();
            referenceRow.after(newRow);
            for (const cell of referenceRow.children(TableCellNode)) {
                const clone = cell.clone();
                newRow.append(clone);
                // Handle managers.
                if (cell.managerCell) {
                    const manager = cell.managerCell;
                    const managerEndRow = manager.rowIndex + manager.rowspan - 1;
                    if (managerEndRow === rowIndex && manager.columnIndex !== cell.columnIndex) {
                        // Take the new row equivalent of the above cell's manager
                        // (copy colspan).
                        clone.mergeWith(this.getCellAt(newRow.rowIndex, manager.columnIndex));
                    }
                    else if (managerEndRow !== rowIndex) {
                        // Take the manager cell of the above cell (extend rowspan),
                        // only if said manager's rowspan is not ending with the
                        // above cell.
                        clone.mergeWith(manager);
                    }
                }
                else if (cell.rowspan > 1) {
                    // If the cell has a rowspan, extend it.
                    clone.mergeWith(cell);
                }
            }
        }
        /**
         * Add a new column before the reference column (the column of the given
         * reference cell). Copy the styles and rowspans of the cells of the
         * reference column. If the reference column traverses a colspan, extend
         * that colspan.
         * If no `referenceCell` was passed, add a column to the left of the table.
         *
         * @param [referenceCell]
         */
        addColumnBefore(referenceCell) {
            if (!referenceCell) {
                referenceCell = this.firstDescendant(TableCellNode);
            }
            const referenceColumn = referenceCell.column;
            for (const cell of referenceColumn) {
                const clone = cell.clone();
                cell.before(clone);
                // Handle managers.
                const manager = cell.managerCell;
                if (manager) {
                    if (manager.columnIndex === referenceCell.columnIndex) {
                        // If the current cell's manager is in the reference column,
                        // the clone's manager should be that manager's clone.
                        const managerClone = this.getCellAt(manager.rowIndex, clone.columnIndex);
                        clone.mergeWith(managerClone);
                    }
                    else {
                        clone.mergeWith(manager);
                    }
                }
            }
        }
        /**
         * Add a new column after the reference column (the column of the given
         * reference cell). Copy the styles and rowspans of the cells of the
         * reference column. If the reference column traverses a colpan, extend that
         * colspan.
         * If no `referenceCell` was passed, add a column to the right of the table.
         * Note: a colspan ending at the reference cell is not extended.
         *
         * @param [referenceCell]
         */
        addColumnAfter(referenceCell) {
            if (!referenceCell) {
                referenceCell = this.lastDescendant(TableCellNode);
            }
            const columnIndex = referenceCell.columnIndex + referenceCell.colspan - 1;
            const referenceColumn = this.columns[columnIndex];
            for (const cell of referenceColumn) {
                const clone = cell.clone();
                cell.after(clone);
                // Handle managers.
                if (cell.managerCell) {
                    const manager = cell.managerCell;
                    const managerEndColumn = manager.columnIndex + manager.colspan - 1;
                    if (managerEndColumn === columnIndex && manager.rowIndex !== cell.rowIndex) {
                        // Take the new column equivalent of the previous cell's
                        // manager (copy rowspan).
                        clone.mergeWith(this.getCellAt(manager.rowIndex, clone.columnIndex));
                    }
                    else if (managerEndColumn !== columnIndex) {
                        // Take the manager cell of the previous cell (extend
                        // colspan), only if said manager's colspan is not ending
                        // with the previous cell.
                        clone.mergeWith(manager);
                    }
                }
                else if (cell.colspan > 1) {
                    // If the cell has a colspan, extend it.
                    clone.mergeWith(cell);
                }
            }
        }
        /**
         * Empty this table and refill it with the given number of rows and columns.
         *
         * @param rowCount
         * @param columnCount
         */
        reset(rowCount, columnCount) {
            this.empty();
            const rows = [];
            for (let rowNumber = 0; rowNumber < rowCount; rowNumber += 1) {
                rows.push(new TableRowNode());
            }
            for (const row of rows) {
                const cells = [];
                for (let colNumber = 0; colNumber < columnCount; colNumber += 1) {
                    cells.push(new TableCellNode());
                }
                row.append(...cells);
            }
            this.append(...rows);
        }
        /**
         * Remove managment of colspan & rowspan for the remove cell.
         *
         * @override
         */
        _removeAtIndex(index) {
            const row = this.childVNodes[index];
            if (row instanceof TableRowNode) {
                row.children(TableCellNode).forEach(cell => cell.unmerge());
            }
            super._removeAtIndex(index);
        }
    }

    class TableCellNode extends ContainerNode {
        constructor(params) {
            super(params);
            this.breakable = false;
            this._managedCells = new VersionableSet();
            this.header = (params === null || params === void 0 ? void 0 : params.header) || false;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         *
         *  @override
         */
        clone(deepClone, params) {
            const defaults = {
                header: this.header,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        get name() {
            let coordinatesRepr = ' <(' + this.rowIndex + ', ' + this.columnIndex + ')';
            if (this.colspan > 1 || this.rowspan > 1) {
                const endRow = this.rowIndex + this.rowspan - 1;
                const endColumn = this.columnIndex + this.colspan - 1;
                coordinatesRepr += ':(' + endRow + ', ' + endColumn + ')';
            }
            coordinatesRepr += '>';
            return (super.name +
                coordinatesRepr +
                (this.header ? ': header' : '') +
                (this.isActive() ? '' : ' (inactive)'));
        }
        /**
         * Return the cell that manages this cell, if any.
         */
        get managerCell() {
            return this._managerCell;
        }
        /**
         * Return the set of cells that this cell manages.
         */
        get managedCells() {
            return new Set(this._managedCells);
        }
        /**
         * Return the computed column span of this cell, in function of its managed
         * cells.
         */
        get colspan() {
            const cellsArray = Array.from(this.managedCells);
            const sameRowCells = cellsArray.filter(cell => cell.rowIndex === this.rowIndex);
            return 1 + sameRowCells.length;
        }
        /**
         * Return the computed row span of this cell, in function of its managed
         * cells.
         */
        get rowspan() {
            const cellsArray = Array.from(this.managedCells);
            const sameColumnCells = cellsArray.filter(cell => cell.columnIndex === this.columnIndex);
            return 1 + sameColumnCells.length;
        }
        /**
         * Return the row to which this cell belongs.
         */
        get row() {
            return this.ancestor(TableRowNode).children(TableCellNode);
        }
        /**
         * Return the column to which this cell belongs, as an array of cells.
         */
        get column() {
            return this.ancestor(TableNode).columns[this.columnIndex];
        }
        /**
         * Return the index of the row to which this cell belongs.
         */
        get rowIndex() {
            return this.ancestor(TableRowNode).rowIndex;
        }
        /**
         * Return the index of the column to which this cell belongs.
         */
        get columnIndex() {
            return this.parent.children(TableCellNode).indexOf(this);
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if this cell is active (ie not managed by another cell).
         */
        isActive() {
            return !this.managerCell;
        }
        /**
         * Set the given cell as manager of this cell.
         * Note: A cell managed by another cell also copies its manager's attributes
         * and properties and hands over its children to its manager.
         *
         * @override
         */
        mergeWith(newManager) {
            const thisTable = this.ancestor(TableNode);
            const otherTable = newManager.ancestor(TableNode);
            if (!(newManager instanceof TableCellNode) || thisTable !== otherTable)
                return;
            this._managerCell = newManager;
            newManager.manage(this);
        }
        /**
         * Unmerge this cell from its manager.
         */
        unmerge() {
            const manager = this._managerCell;
            if (manager) {
                this._managerCell = null;
                // If we just removed this cell's manager, also remove this cell
                // from the old manager's managed cells.
                manager.unmanage(this);
            }
        }
        /**
         * Set the given cell as managed by this cell.
         * Note: A cell managed by another cell also copies its manager's modifiers
         * and properties and hands over its children to its manager.
         *
         * @param cell
         */
        manage(cell) {
            this._managedCells.add(cell);
            // Copy the manager's modifiers and properties.
            cell.modifiers = this.modifiers.clone();
            cell.header = this.header;
            // Move the children to the manager.
            this.append(...cell.childVNodes);
            // Hand the managed cells over to the manager.
            for (const managedCell of cell.managedCells) {
                managedCell.mergeWith(this);
                cell.unmanage(managedCell);
            }
            // Copy the manager's row if an entire row was merged
            const row = cell.ancestor(TableRowNode);
            if (row) {
                const cells = row.children(TableCellNode);
                const rowIsMerged = cells.every(rowCell => rowCell.managerCell === this);
                if (rowIsMerged) {
                    const managerRow = cell.managerCell.ancestor(TableRowNode);
                    row.header = managerRow.header;
                    row.modifiers = managerRow.modifiers.clone();
                }
            }
            // Ensure reciprocity.
            if (cell.managerCell !== this) {
                cell.mergeWith(this);
            }
        }
        /**
         * Restore the independence of the given cell.
         *
         * @param cell
         */
        unmanage(cell) {
            this._managedCells.delete(cell);
            // Ensure reciprocity.
            if (cell.managerCell === this) {
                cell.unmerge();
            }
        }
    }

    /**
     * Class that rank a hierarchy of vnode through a "specificity" algorithm.
     *
     * Specificity level is defined with:
     * - `lvl2`: if the last predicate of an item selector is deeper in the tree
     *   than the last predicate of another item selector; the first item have
     *   more specificity
     * - `lvl1`: if two or more items have the same `lvl2` specificity; the
     *   command with the longest selector will have more specificity
     * - `lvl0`: if the item has no selector (an empty list), there is no
     *   specificity
     * ```
     */
    class ContextManager {
        constructor(editor, execCommand) {
            this.editor = editor;
            this.defaultContext = {
                range: this.editor.selection.range,
                execCommand: execCommand,
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Test all contextuals against a hierarchy of VNodes and return the result
         * ordered by specificity.
         */
        static getRankedMatches(hierarchy, contextuals) {
            const matches = [];
            for (let index = 0; index < contextuals.length; index++) {
                const contextual = contextuals[index];
                const match = ContextManager._matchNodes(hierarchy, contextual.selector);
                if (match) {
                    matches.push({
                        lvl1Score: match[1].length,
                        lvl2Score: match[0],
                        matched: match[1],
                        index: index,
                        entry: contextual,
                    });
                }
            }
            // Sort the matches:
            // - from highest to lowest score
            // - when the score is the same, from highest to lowest index
            const rankedMatch = matches.sort(function (a, b) {
                if (b.lvl2Score === a.lvl2Score && b.lvl1Score === a.lvl1Score) {
                    return b.index - a.index;
                }
                else if (b.lvl2Score === a.lvl2Score) {
                    return b.lvl1Score - a.lvl1Score;
                }
                else {
                    return b.lvl2Score - a.lvl2Score;
                }
            });
            return rankedMatch;
        }
        /**
         * Match items selector depending on the editor current context range and
         * return the most specific item.
         *
         * @param items
         * @param paramsContext
         */
        match(items, paramsContext) {
            const context = Object.assign(Object.assign({}, this.defaultContext), paramsContext);
            const start = context.range.start;
            const hierarchy = start.ancestors();
            const node = start.previousSibling() || start.nextSibling();
            if (node) {
                hierarchy.unshift(node);
            }
            const entries = items.map(item => {
                const entry = {
                    selector: item.selector || [],
                    value: item,
                };
                return entry;
            });
            const matches = ContextManager.getRankedMatches(hierarchy, entries);
            const match = matches.find(match => {
                return (!match.entry.value.check ||
                    match.entry.value.check(Object.assign(Object.assign({}, context), { selector: match.matched })));
            });
            return [match === null || match === void 0 ? void 0 : match.entry.value, context];
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Check whether a hierarchy of `VNode` match with `selector`.
         *
         * The `hierarchy` is an array from the deepest node in a tree to the
         * shallowest.
         *
         * Return a tuple with the first value being level of specificity lvl2 and
         * the second value being the VNnode that matched with a selector
         * (specificity lvl1).
         */
        static _matchNodes(hierarchy, selector) {
            const matches = [];
            const maximumDepth = hierarchy.length - 1;
            let firstMatchDepth = -1;
            let index = 0;
            for (const predicate of [...selector].reverse()) {
                let matchFound = false;
                while (!matchFound && index < hierarchy.length) {
                    if (hierarchy[index].test(predicate)) {
                        matchFound = true;
                        matches.unshift(hierarchy[index]);
                        if (firstMatchDepth === -1) {
                            // Deeper match has higher specificity. So lower
                            // index in ancestors, means higher specificity.
                            firstMatchDepth = maximumDepth - index;
                        }
                    }
                    index++;
                }
                // Stop checking the predicates of this particular command
                // since at least one of them don't match the context.
                if (!matchFound)
                    break;
            }
            return matches.length === selector.length && [firstMatchDepth, matches];
        }
    }

    /**
     * Properties of a `VNode` that can be modified by a mode.
     */
    var RuleProperty;
    (function (RuleProperty) {
        RuleProperty["EDITABLE"] = "editable";
        RuleProperty["BREAKABLE"] = "breakable";
        RuleProperty["ALLOW_EMPTY"] = "allowEmpty";
    })(RuleProperty || (RuleProperty = {}));
    class Mode {
        constructor(mode) {
            this.id = mode.id;
            this.rules = mode.rules;
            // Convert the rules into an object describing them for each property.
            const ruleEntries = {};
            this._entries = this.rules.reduce((accumulator, rule) => {
                for (const property of Object.keys(rule.properties)) {
                    const entry = {
                        selector: rule.selector,
                        value: rule.properties[property],
                    };
                    if (!ruleEntries[property])
                        ruleEntries[property] = [];
                    ruleEntries[property].push(entry);
                }
                return accumulator;
            }, ruleEntries);
        }
        /**
         * Return true if this mode defines the given node's property as true. If
         * the mode does not define a value for the given node's property then
         * return true if the actual value of the property on the node itself is
         * true.
         *
         * @param node
         * @param property
         */
        is(node, property) {
            const hierarchy = [node, ...node.ancestors()];
            const entries = this._entries[property] || [];
            const result = ContextManager.getRankedMatches(hierarchy, entries);
            // For each result from a non-cascading rule property, keep only the
            // ones that match the given node, not one of its ancestors.
            const filteredResults = result.filter(r => r.entry.value.cascading || r.matched.some(match => match === node));
            if (filteredResults.length) {
                return filteredResults[0].entry.value.value;
            }
            else {
                return node[property];
            }
        }
    }

    /**
     * This class represents an atomic node that is used as a content separator.
     */
    class SeparatorNode extends AtomicNode {
    }

    class VRange {
        constructor(editor, boundaryPoints, options = {}) {
            this.editor = editor;
            this.start = new MarkerNode();
            this.end = new MarkerNode();
            this.temporary = !!options.temporary;
            this._mode = options.mode;
            // If a range context is given, adapt this range to match it.
            if (boundaryPoints) {
                const [start, end] = boundaryPoints;
                const [startNode, startPosition] = start;
                const [endNode, endPosition] = end;
                if (endPosition === RelativePosition.AFTER) {
                    this.setEnd(endNode, endPosition);
                    this.setStart(startNode, startPosition);
                }
                else {
                    this.setStart(startNode, startPosition);
                    this.setEnd(endNode, endPosition);
                }
            }
        }
        /**
         * Return the context of a collapsed range at the given location, targetting
         * a reference VNode and specifying the position relative to that VNode.
         *
         * @param reference
         * @param position
         */
        static at(reference, position = RelativePosition.BEFORE) {
            return VRange.selecting(reference, position, reference, position);
        }
        /**
         * Return the context of a range at the location of the given range.
         *
         * @param range
         */
        static clone(range) {
            return [
                [range.start, RelativePosition.BEFORE],
                [range.end, RelativePosition.AFTER],
            ];
        }
        static selecting(startNode, startPosition = RelativePosition.BEFORE, endNode = startNode, endPosition = RelativePosition.AFTER) {
            if (startPosition instanceof AbstractNode) {
                endNode = startPosition;
                startPosition = RelativePosition.BEFORE;
            }
            return [
                [startNode, startPosition],
                [endNode, endPosition],
            ];
        }
        get mode() {
            return this._mode || this.editor.mode;
        }
        /**
         * Each time the selection changes, we reset its format and style.
         * Get the modifiers for the next insertion.
         */
        get modifiers() {
            if (this._modifiers === undefined) {
                this._updateModifiers();
            }
            return this._modifiers;
        }
        set modifiers(modifiers) {
            this._modifiers = modifiers;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        get startContainer() {
            return this.start.parent;
        }
        get endContainer() {
            return this.end.parent;
        }
        /**
         * Return true if the range is collapsed.
         */
        isCollapsed() {
            if (!this.startContainer || !this.endContainer)
                return;
            const childVNodes = this.start.parent.childVNodes;
            let index = childVNodes.indexOf(this.end);
            while (index > 0) {
                index--;
                const sibling = childVNodes[index];
                if (sibling === this.start) {
                    return true;
                }
                if (sibling.tangible) {
                    break;
                }
            }
            return false;
        }
        /**
         * Return true if the start or end of the range is contained within the
         * given container.
         *
         * @param container
         */
        isIn(container) {
            let startAncestor = this.start;
            let endAncestor = this.end;
            while (startAncestor || endAncestor) {
                if (startAncestor === container || endAncestor === container) {
                    return true;
                }
                startAncestor = startAncestor === null || startAncestor === void 0 ? void 0 : startAncestor.parent;
                endAncestor = endAncestor === null || endAncestor === void 0 ? void 0 : endAncestor.parent;
            }
            return false;
        }
        selectedNodes(predicate) {
            const selectedNodes = [];
            let node = this.start;
            const bound = this.end.next();
            const endContainers = this.end.ancestors();
            while ((node = node.next()) && node !== bound) {
                if (!endContainers.includes(node) &&
                    !(node instanceof FragmentNode) &&
                    this.mode.is(node, RuleProperty.EDITABLE) && (node === null || node === void 0 ? void 0 : node.test(predicate))) {
                    selectedNodes.push(node);
                }
            }
            const alreadyTested = new Set();
            for (const selectedNode of selectedNodes) {
                // Find the next ancestor whose children are all selected
                // and add it to the list.
                // TODO: Ideally, selected nodes should be returned in DFS order.
                const ancestor = selectedNode.parent;
                if (ancestor && !alreadyTested.has(ancestor)) {
                    alreadyTested.add(ancestor);
                    const allChildrenSelected = ancestor
                        .children()
                        .every(child => selectedNodes.includes(child));
                    if (allChildrenSelected &&
                        !selectedNodes.includes(ancestor) &&
                        !(ancestor instanceof FragmentNode) &&
                        this.mode.is(ancestor, RuleProperty.EDITABLE) &&
                        ancestor.test(predicate)) {
                        selectedNodes.push(ancestor);
                    }
                }
            }
            return selectedNodes;
        }
        targetedNodes(predicate) {
            const targetedNodes = this.traversedNodes(predicate);
            if (!this.end.previousSibling() &&
                targetedNodes.length &&
                targetedNodes[targetedNodes.length - 1] === this.endContainer) {
                // When selecting a container and the space between it and the next
                // one (eg. triple click), don't return the next container as well.
                targetedNodes.pop();
            }
            const closestStartAncestor = this.start.ancestor(predicate);
            if (closestStartAncestor && this.mode.is(closestStartAncestor, RuleProperty.EDITABLE)) {
                targetedNodes.unshift(closestStartAncestor);
            }
            else if (closestStartAncestor) {
                const children = [...closestStartAncestor.childVNodes].reverse();
                for (const child of children) {
                    if (!targetedNodes.includes(child) &&
                        this.mode.is(child, RuleProperty.EDITABLE) &&
                        child.test(predicate)) {
                        targetedNodes.unshift(child);
                    }
                }
            }
            return targetedNodes;
        }
        traversedNodes(predicate) {
            const traversedNodes = [];
            let node = this.start;
            const bound = this.end.next();
            while ((node = node.next()) && node !== bound) {
                if (this.mode.is(node, RuleProperty.EDITABLE) && node.test(predicate)) {
                    traversedNodes.push(node);
                }
            }
            return traversedNodes;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Collapse the range.
         *
         * @param [edge] range edge on which to collapse
         */
        collapse(edge = this.start) {
            if (edge === this.start) {
                this.setEnd(edge);
            }
            else if (edge === this.end) {
                this.setStart(edge);
            }
        }
        /**
         * Set the range's start point (in traversal order) at the given location,
         * targetting a `reference` VNode and specifying the `position` in reference
         * to that VNode ('BEFORE', 'AFTER'), like in an `xpath.
         *
         * @param reference
         * @param [position]
         */
        setStart(reference, position = RelativePosition.BEFORE) {
            if (position === RelativePosition.BEFORE) {
                reference = reference.firstLeaf();
            }
            else if (position === RelativePosition.AFTER) {
                reference = reference.lastLeaf();
            }
            if (reference instanceof ContainerNode && !reference.hasChildren()) {
                reference.prepend(this.start);
            }
            else if (position === RelativePosition.AFTER && reference !== this.end) {
                // We check that `reference` isn't `this.end` to avoid a backward
                // collapsed range.
                reference.after(this.start);
            }
            else if (position === RelativePosition.INSIDE) {
                reference.append(this.start);
            }
            else {
                reference.before(this.start);
            }
            this.modifiers = undefined;
        }
        /**
         * Set the range's end point (in traversal order) at the given location,
         * targetting a `reference` VNode and specifying the `position` in reference
         * to that VNode ('BEFORE', 'AFTER'), like in an `xpath.
         *
         * @param reference
         * @param [position]
         */
        setEnd(reference, position = RelativePosition.AFTER) {
            if (position === RelativePosition.BEFORE) {
                reference = reference.firstLeaf();
            }
            else if (position === RelativePosition.AFTER) {
                reference = reference.lastLeaf();
            }
            if (reference instanceof ContainerNode && !reference.hasChildren()) {
                reference.append(this.end);
            }
            else if (position === RelativePosition.BEFORE && reference !== this.start) {
                // We check that `reference` isn't `this.start` to avoid a backward
                // collapsed range.
                reference.before(this.end);
            }
            else if (position === RelativePosition.INSIDE) {
                reference.append(this.end);
            }
            else {
                reference.after(this.end);
            }
            this.modifiers = undefined;
        }
        /**
         * Extend this range in such a way that it includes the given node.
         *
         * This method moves the boundary marker that is closest to the given node
         * up or down the tree in order to include the given node into the range.
         * Because of that, calling this method will always result in a range that
         * is at least the size that it was prior to calling it, and usually bigger.
         *
         * @param targetNode The node to extend the range to.
         */
        extendTo(targetNode) {
            let position;
            if (targetNode.isBefore(this.start)) {
                targetNode = targetNode.previous();
                if (targetNode.hasChildren()) {
                    targetNode = targetNode.firstLeaf();
                    position = RelativePosition.BEFORE;
                }
                else {
                    position = RelativePosition.AFTER;
                }
                if (targetNode && this.end.nextSibling() !== targetNode) {
                    this.setStart(targetNode, position);
                }
            }
            else if (targetNode.isAfter(this.end)) {
                if (targetNode.hasChildren()) {
                    targetNode = targetNode.next();
                    position = RelativePosition.BEFORE;
                }
                else {
                    position = RelativePosition.AFTER;
                }
                if (targetNode) {
                    this.setEnd(targetNode, position);
                }
            }
        }
        /**
         * Split the range containers up to their common ancestor. Return all
         * children of the common ancestor that are targeted by the range after the
         * split. If a predicate is given, splitting continues up to and including
         * the node closest to the common ancestor that matches the predicate.
         *
         * @param predicate
         */
        split(predicate) {
            const ancestor = this.startContainer.commonAncestor(this.endContainer);
            const closest = ancestor.closest(predicate);
            const container = closest ? closest.parent : ancestor;
            // Split the start ancestors.
            let start = this.start;
            do {
                let startAncestor = start.parent;
                // Do not split at the start edge of a node.
                if (start.previousSibling() && this.mode.is(startAncestor, RuleProperty.BREAKABLE)) {
                    startAncestor = startAncestor.splitAt(start);
                }
                start = startAncestor;
            } while (start.parent !== container);
            // Split the end ancestors.
            let end = this.end;
            do {
                const endAncestor = end.parent;
                // Do not split at the end edge of a node.
                if (end.nextSibling() && this.mode.is(endAncestor, RuleProperty.BREAKABLE)) {
                    endAncestor.splitAt(end);
                    endAncestor.append(end);
                }
                end = endAncestor;
            } while (end.parent !== container);
            // Return all top-most split nodes between and including start and end.
            const nodes = [];
            let node = start;
            while (node !== end) {
                nodes.push(node);
                node = node.nextSibling();
            }
            nodes.push(end);
            return nodes;
        }
        /**
         * Empty the range by removing selected nodes and collapsing it by merging
         * nodes between start and end.
         */
        empty() {
            // Compute the current modifiers so they are preserved after empty.
            this._updateModifiers();
            const removableNodes = this.selectedNodes(node => {
                // TODO: Replace Table check with complex table selection support.
                return this.mode.is(node, RuleProperty.EDITABLE) && !(node instanceof TableCellNode);
            });
            // Remove selected nodes without touching the start range's ancestors.
            const startAncestors = this.start.ancestors();
            for (const node of removableNodes.filter(node => !startAncestors.includes(node))) {
                node.remove();
            }
            // Collapse the range by merging nodes between start and end, if it
            // doesn't traverse an unbreakable node.
            if (this.startContainer !== this.endContainer) {
                const commonAncestor = this.start.commonAncestor(this.end);
                const unbreakableStartAncestor = this.start.ancestor(this._isUnbreakable.bind(this));
                const traversedUnbreakables = this.traversedNodes(this._isUnbreakable.bind(this));
                if (unbreakableStartAncestor &&
                    !this.end.ancestor(node => node === unbreakableStartAncestor)) {
                    traversedUnbreakables.unshift(unbreakableStartAncestor);
                }
                let ancestor = this.endContainer.parent;
                while (ancestor && ancestor !== commonAncestor) {
                    if (traversedUnbreakables.length === 0 &&
                        ancestor.children().length > 1 &&
                        this.endContainer.parent === ancestor &&
                        this.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        this.mode.is(this.startContainer, RuleProperty.EDITABLE) &&
                        this.mode.is(this.startContainer, RuleProperty.BREAKABLE)) {
                        ancestor.splitAt(this.endContainer);
                    }
                    if (traversedUnbreakables.length === 0 &&
                        this.mode.is(this.endContainer, RuleProperty.EDITABLE) &&
                        this.mode.is(this.endContainer, RuleProperty.BREAKABLE) &&
                        this.mode.is(ancestor, RuleProperty.EDITABLE) &&
                        this.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        this.mode.is(this.startContainer, RuleProperty.EDITABLE) &&
                        this.mode.is(this.startContainer, RuleProperty.BREAKABLE)) {
                        this.endContainer.mergeWith(ancestor);
                    }
                    ancestor = ancestor.parent;
                }
                if (traversedUnbreakables.length === 0 &&
                    this.mode.is(this.startContainer, RuleProperty.BREAKABLE) &&
                    this.mode.is(this.endContainer, RuleProperty.BREAKABLE) &&
                    this.mode.is(this.startContainer, RuleProperty.EDITABLE) &&
                    this.mode.is(this.endContainer, RuleProperty.EDITABLE)) {
                    this.endContainer.mergeWith(this.startContainer);
                }
                this.collapse();
            }
        }
        /**
         * Remove this range from its VDocument.
         */
        remove() {
            this.start.remove();
            this.end.remove();
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the given node is unbreakable.
         *
         * @param node
         */
        _isUnbreakable(node) {
            return !this.mode.is(node, RuleProperty.BREAKABLE);
        }
        /**
         * Update the `_modifiers` cache by recomputing their current state based on
         * the surroundings of the current range.
         */
        _updateModifiers() {
            let nodeToCopyModifiers;
            if (this.isCollapsed()) {
                nodeToCopyModifiers =
                    this.start.previousSibling() ||
                        this.start.nextSibling();
            }
            else {
                nodeToCopyModifiers = this.start.nextSibling();
            }
            let modifiers = new Modifiers();
            if (nodeToCopyModifiers) {
                modifiers = nodeToCopyModifiers.modifiers.clone();
            }
            if (this.isCollapsed()) {
                // Only preserved modifiers are applied at the start of a container.
                const previousSibling = this.start.previousSibling();
                const nextSibling = this.end.nextSibling();
                const isAfterLineBreak = previousSibling instanceof SeparatorNode;
                const preservedModifiers = modifiers === null || modifiers === void 0 ? void 0 : modifiers.filter(mod => {
                    var _a;
                    if (isAfterLineBreak) {
                        return mod.preserveAfterLineBreak;
                    }
                    else if (previousSibling) {
                        return (mod.preserveAfterNode || ((_a = nextSibling === null || nextSibling === void 0 ? void 0 : nextSibling.modifiers) === null || _a === void 0 ? void 0 : _a.some(otherMod => otherMod.isSameAs(mod))));
                    }
                    else {
                        return mod.preserveAfterParagraphBreak;
                    }
                });
                if (preservedModifiers === null || preservedModifiers === void 0 ? void 0 : preservedModifiers.length) {
                    modifiers = new Modifiers(...preservedModifiers);
                }
                else {
                    modifiers = new Modifiers();
                }
            }
            this._modifiers = modifiers;
        }
    }

    var Direction;
    (function (Direction) {
        Direction["BACKWARD"] = "BACKWARD";
        Direction["FORWARD"] = "FORWARD";
    })(Direction || (Direction = {}));
    class VSelection {
        constructor(editor) {
            this.editor = editor;
            this.range = new VRange(this.editor);
            this._direction = Direction.FORWARD;
        }
        get anchor() {
            return this.direction === Direction.FORWARD ? this.range.start : this.range.end;
        }
        get focus() {
            return this.direction === Direction.FORWARD ? this.range.end : this.range.start;
        }
        get direction() {
            return this._direction;
        }
        isCollapsed() {
            return this.range.isCollapsed();
        }
        /**
         * Update the selection according to the given description.
         *
         * @param selection
         */
        set(selection) {
            this._direction = selection.direction;
            this.select(selection.anchorNode, selection.anchorPosition, selection.focusNode, selection.focusPosition);
        }
        /**
         * Set a collapsed selection at the given location, targetting a `reference`
         * VNode and specifying the `position` in reference to that VNode ('BEFORE',
         * 'AFTER'), like in an `xpath`.
         *
         * @param position
         * @param reference
         */
        setAt(reference, position = RelativePosition.BEFORE) {
            this.setAnchor(reference, position);
            this.collapse();
        }
        select(anchorNode, anchorPosition = RelativePosition.BEFORE, focusNode = anchorNode, focusPosition = RelativePosition.AFTER) {
            if (anchorPosition instanceof AbstractNode) {
                focusNode = anchorPosition;
                anchorPosition = RelativePosition.BEFORE;
            }
            if (focusPosition === RelativePosition.AFTER) {
                this.setFocus(focusNode, focusPosition);
                this.setAnchor(anchorNode, anchorPosition);
            }
            else {
                this.setAnchor(anchorNode, anchorPosition);
                this.setFocus(focusNode, focusPosition);
            }
        }
        /**
         * Set the anchor of the selection by targetting a `reference` VNode and
         * specifying the `position` in reference to that VNode ('BEFORE', 'AFTER'),
         * like in an `xpath`. If no relative position if given, include the
         * reference node in the selection.
         *
         * @param reference
         * @param [position]
         */
        setAnchor(reference, position = RelativePosition.BEFORE) {
            if (this.direction === Direction.FORWARD) {
                this.range.setStart(reference, position);
            }
            else {
                this.range.setEnd(reference, position);
            }
        }
        /**
         * Set the focus of the selection by targetting a `reference` VNode and
         * specifying the `position` in reference to that VNode ('BEFORE', 'AFTER'),
         * like in an `xpath`. If no relative position if given, include the
         * reference node in the selection.
         *
         * @param reference
         * @param [position]
         */
        setFocus(reference, position = RelativePosition.AFTER) {
            if (this.direction === Direction.FORWARD) {
                this.range.setEnd(reference, position);
            }
            else {
                this.range.setStart(reference, position);
            }
        }
        /**
         * Extend the selection from its anchor to the given location, targetting a
         * `reference` VNode and specifying the `direction` of the extension.
         *
         * @param reference
         * @param [direction] default: Direction.FORWARD
         */
        extendTo(reference, direction = Direction.FORWARD) {
            let position;
            if (direction === Direction.FORWARD) {
                if (reference.hasChildren()) {
                    reference = reference.next();
                    reference = reference.firstLeaf();
                    position = RelativePosition.BEFORE;
                }
                else {
                    position = RelativePosition.AFTER;
                }
            }
            else {
                reference = reference.previous();
                if (reference.hasChildren()) {
                    reference = reference.firstLeaf();
                    position = RelativePosition.BEFORE;
                }
                else {
                    position = RelativePosition.AFTER;
                }
            }
            if (reference) {
                this.setFocus(reference, position);
            }
        }
        /**
         * Collapse the selection on its anchor.
         *
         */
        collapse() {
            this.range.collapse(this.anchor);
        }
    }

    class Core extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                insert: {
                    handler: this.insert,
                },
                insertParagraphBreak: {
                    handler: this.insertParagraphBreak,
                },
                setSelection: {
                    handler: this.setSelection,
                },
                deleteBackward: {
                    handler: this.deleteBackward,
                },
                deleteForward: {
                    handler: this.deleteForward,
                },
                deleteWord: {
                    handler: this.deleteWord,
                },
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Insert a paragraph break.
         */
        insertParagraphBreak(params) {
            const range = params.context.range;
            // Remove the contents of the range if needed.
            if (!range.isCollapsed()) {
                range.empty();
            }
            if (range.mode.is(range.startContainer, RuleProperty.BREAKABLE)) {
                range.startContainer.splitAt(range.start);
            }
            else {
                // Use a separator to break paragraphs in an unbreakable.
                const Separator = this.editor.configuration.defaults.Separator;
                range.start.before(new Separator());
            }
        }
        /**
         * Insert a VNode at the current position of the selection.
         *
         * @param params
         */
        insert(params) {
            // Remove the contents of the range if needed.
            if (!params.context.range.isCollapsed()) {
                params.context.range.empty();
            }
            params.context.range.start.before(params.node);
        }
        /**
         * Delete in the backward direction (backspace key expected behavior).
         */
        deleteBackward(params) {
            const range = params.context.range;
            if (range.isCollapsed()) {
                // Basic case: remove the node directly preceding the range.
                const previousSibling = range.start.previousSibling();
                if (previousSibling && range.mode.is(previousSibling, RuleProperty.EDITABLE)) {
                    if (previousSibling instanceof AtomicNode) {
                        previousSibling.removeBackward();
                    }
                    else {
                        const startContainer = range.startContainer;
                        const index = startContainer.childVNodes.indexOf(range.start);
                        let node = startContainer.childVNodes[index];
                        while (node && node instanceof AtomicNode) {
                            previousSibling.append(node);
                            // The index does not need to be incremented because the
                            // line above just removed one node from the container.
                            node = startContainer.childVNodes[index];
                        }
                    }
                }
                else if (range.mode.is(range.startContainer, RuleProperty.BREAKABLE) &&
                    range.mode.is(range.startContainer, RuleProperty.EDITABLE)) {
                    // Otherwise set range start at previous valid leaf.
                    let ancestor = range.start.parent;
                    while (ancestor &&
                        range.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        range.mode.is(ancestor, RuleProperty.EDITABLE) &&
                        !ancestor.previousSibling()) {
                        ancestor = ancestor.parent;
                    }
                    if (ancestor &&
                        range.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        range.mode.is(ancestor, RuleProperty.EDITABLE)) {
                        const previousSibling = ancestor.previousSibling();
                        if (previousSibling instanceof AtomicNode) {
                            ancestor.mergeWith(previousSibling.parent);
                        }
                        else {
                            const previousLeaf = previousSibling.lastLeaf();
                            if (previousSibling && !previousSibling.hasChildren()) {
                                // If the previous sibling is empty, remove it.
                                previousSibling.removeBackward();
                            }
                            else if (previousLeaf) {
                                range.setStart(previousLeaf, RelativePosition.AFTER);
                                range.empty();
                            }
                        }
                    }
                }
            }
            else {
                range.empty();
            }
        }
        /**
         * Delete in the forward direction (delete key expected behavior).
         */
        deleteForward(params) {
            const range = params.context.range;
            if (range.isCollapsed()) {
                // Basic case: remove the node directly following the range.
                const nextSibling = range.end.nextSibling();
                if (nextSibling && range.mode.is(nextSibling, RuleProperty.EDITABLE)) {
                    nextSibling.removeForward();
                }
                else if (range.mode.is(range.endContainer, RuleProperty.BREAKABLE) &&
                    range.mode.is(range.endContainer, RuleProperty.EDITABLE)) {
                    // Otherwise set range end at next valid leaf.
                    let ancestor = range.end.parent;
                    while (ancestor &&
                        range.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        range.mode.is(ancestor, RuleProperty.EDITABLE) &&
                        !ancestor.nextSibling()) {
                        ancestor = ancestor.parent;
                    }
                    if (ancestor &&
                        range.mode.is(ancestor, RuleProperty.BREAKABLE) &&
                        range.mode.is(ancestor, RuleProperty.EDITABLE)) {
                        const nextSibling = ancestor.nextSibling();
                        if (nextSibling instanceof AtomicNode) {
                            let next = nextSibling;
                            while (next && next instanceof AtomicNode) {
                                ancestor.append(next);
                                next = ancestor.nextSibling();
                            }
                        }
                        else {
                            const next = nextSibling.firstLeaf();
                            if (next && !range.endContainer.hasChildren()) {
                                // If the current container is empty, remove it.
                                range.endContainer.removeForward();
                                range.setStart(next, RelativePosition.BEFORE);
                                range.setEnd(next, RelativePosition.BEFORE);
                            }
                            else if (next) {
                                range.setEnd(next, RelativePosition.BEFORE);
                                range.empty();
                            }
                        }
                    }
                }
            }
            else {
                range.empty();
            }
        }
        async deleteWord(params) {
            const range = params.context.range;
            if (params.direction === Direction.FORWARD) {
                const text = Array.from(params.text);
                if (text[text.length - 1] === ' ') {
                    // TODO: The normalizer should be able to detect where to put
                    // the space according to the range and the removal direction.
                    // Make sure to handle a space _before_ the word.
                    text.unshift(text.pop());
                }
                let end = range.end;
                while (end && text.length) {
                    const next = end.nextSibling();
                    if ((next === null || next === void 0 ? void 0 : next.textContent) === text.shift()) {
                        end = next;
                    }
                }
                const context = {
                    range: new VRange(this.editor, VRange.selecting(range.start, end), {
                        temporary: true,
                    }),
                };
                await params.context.execCommand('deleteForward', { context });
            }
            else {
                let start = range.start;
                const text = Array.from(params.text);
                if (text[0] === ' ') {
                    // TODO: The normalizer should be able to detect where to put
                    // the space according to the range and the removal direction.
                    // Make sure to treat a space _before_ the word.
                    text.push(text.shift());
                }
                while (start && text.length) {
                    const previous = start.previousSibling();
                    if ((previous === null || previous === void 0 ? void 0 : previous.textContent) === text.pop()) {
                        start = previous;
                    }
                }
                const context = {
                    range: new VRange(this.editor, VRange.selecting(start, range.end), {
                        temporary: true,
                    }),
                };
                await params.context.execCommand('deleteBackward', { context });
            }
        }
        /**
         * Navigate to a given range.
         *
         * @param params
         */
        setSelection(params) {
            this.editor.selection.set(params.vSelection);
        }
    }

    var Platform;
    (function (Platform) {
        Platform["MAC"] = "mac";
        Platform["PC"] = "pc";
    })(Platform || (Platform = {}));
    var LEVEL;
    (function (LEVEL) {
        LEVEL[LEVEL["DEFAULT"] = 0] = "DEFAULT";
        LEVEL[LEVEL["USER"] = 1] = "USER";
    })(LEVEL || (LEVEL = {}));
    /**
     * Keymap allow to add and remove shortucts and provide a function to match a
     * keyboard event with the registered shortcuts patterns.
     *
     * ## Adding shortcuts
     * The expression to describe a shortuct is zero or more `modifiers` and one
     * `hotkey` joined with the symbol `+`.
     *
     * ### Modifiers
     * - SHIFT
     * - ALT
     * - CTRL
     * - META
     * - CMD (alias of META)
     *
     * Example:
     * ```typescript
     * // using a modifier and one key
     * keymap.bind('CTRL+A', 'commandIdentifier')
     * // using multiples modifiers and one key
     * keymap.bind('CTRL+ALT+A', 'commandIdentifier')
     * ```
     *
     * ### Hotkeys
     * A hotkey can be wether a `key` or `code`.
     *
     * #### Key
     * The syntax to describe a `key` is to write the `key` as it is. The convention
     * is to write it in uppercase.
     *
     * Example:
     * ```typescript
     * keymap.bind('CTRL+A', 'commandIdentifier')
     * ```
     * The list of possible `key` values are defined in the following link:
     * https://www.w3.org/TR/uievents/#dom-keyboardevent-key
     *
     * #### Code
     * The syntax to describe a `code` is to write `<code>` (surrounded by "<" and
     * ">").
     *
     * Example:
     * ```typescript
     * keymap.bind('CTRL+<KeyA>', 'commandIdentifier')
     * ```
     *
     * The list of possible `code` values are defined in the following link:
     * https://www.w3.org/TR/uievents/#dom-keyboardevent-key
     *
     * ## Removing shortucts
     * To remove a shortuct, call `bind` without specifying a commandIdentifier.
     *
     * Example:
     * ```typescript
     * keymap.bind('CTRL+<KeyA>')
     * ```
     */
    class Keymap extends JWPlugin {
        constructor(editor, config) {
            super(editor, config);
            this.editor = editor;
            this.config = config;
            this.loaders = {
                shortcuts: this._loadShortcuts,
            };
            this.mappings = [...new Array(LEVEL.USER + 1)].map(() => []);
            this.defaultMappings = [];
            this.userMappings = [];
            if (!config.platform) {
                const isMac = navigator.platform.match(/Mac/);
                config.platform = isMac ? Platform.MAC : Platform.PC;
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Bind a shortuct.
         *
         * If there is no `command.commandId`, it means that we want nothing to
         * execute, thus replacing the command originally bound on this shortcut.
         *
         * @param pattern
         * @param command
         */
        bind(pattern, command, level = LEVEL.DEFAULT) {
            this.mappings[level].push({
                pattern: this.parsePattern(pattern),
                configuredCommand: command,
            });
        }
        /**
         * Return all configured commands which shortcut match the given `keyEvent`.
         *
         * @param keyEvent
         */
        match(keyEvent) {
            var _a;
            const matchingCommands = [];
            for (let level = LEVEL.USER; level >= 0; level--) {
                for (const shortcut of this.mappings[level]) {
                    const modifiers = shortcut.pattern.modifiers;
                    let match;
                    if ('code' in shortcut.pattern) {
                        match = shortcut.pattern.code === keyEvent.code;
                    }
                    else {
                        // In rare case the KeyboardEvent `key` is undefined.
                        match = shortcut.pattern.key === ((_a = keyEvent.key) === null || _a === void 0 ? void 0 : _a.toUpperCase());
                    }
                    match =
                        match &&
                            modifiers.has('CTRL') === keyEvent.ctrlKey &&
                            modifiers.has('SHIFT') === keyEvent.shiftKey &&
                            modifiers.has('META') === keyEvent.metaKey &&
                            modifiers.has('ALT') === keyEvent.altKey;
                    if (match) {
                        if (!shortcut.configuredCommand.commandId) {
                            // An `undefined` command unbounds the other commands
                            // previously registered on this shortcut.
                            matchingCommands.length = 0;
                        }
                        matchingCommands.push(shortcut.configuredCommand);
                    }
                }
                if (matchingCommands.length) {
                    // Matches were found at this level so do not look lower.
                    break;
                }
            }
            return matchingCommands;
        }
        /**
         * Parse a string that represents a pattern and return a `ShortuctPattern`.
         * Supported pattern is: [modifier+]*[<code>|key]
         *
         * @param pattern
         */
        parsePattern(pattern) {
            const tokens = pattern
                .replace(/cmd/gi, 'META')
                .split(/[+]/)
                .map(token => token.trim());
            const keyCode = tokens.pop();
            const modifiers = new Set(tokens.map(token => token.toUpperCase()));
            if (!keyCode) {
                throw new Error('You must have at least one key or code.');
            }
            // There are two ways to specify a shortcut hotkey : key or code
            // - "CTRL+1" is the modifier CTRL with the event.key "1".
            // - "CTRL+<Key1>" is the modifier CTRL with the event.code "Key1"
            const codeMatch = keyCode.match(/^<(\w+)>$/);
            if (codeMatch && codeMatch.length > 1) {
                return { code: codeMatch[1], modifiers };
            }
            else {
                return { key: keyCode.toUpperCase(), modifiers };
            }
        }
        /**
         * Take a `ShortuctPattern` and return a string that represents a pattern,
         * in the form [modifier+]*[<code>|key].
         *
         * @param pattern
         */
        stringifyPattern(pattern) {
            const parts = Array.from(pattern.modifiers);
            if ('code' in pattern) {
                parts.push(pattern.code);
            }
            else if ('key' in pattern) {
                parts.push(pattern.key);
            }
            return parts.join('+');
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Load a shortcut in the keymap depending on the platform.
         *
         * - If the shortuct has no platform property; load the shortuct in both
         *   platform ('mac' and 'pc').
         * - If the shortuct has no platform property and the current platform is
         *   mac, modify the ctrl key to meta key.
         * - If the shortuct has a platform property, only load the shortcut for
         *   that platform.
         * - If no `mapping.commandId` is declared, it means removing the shortcut.
         *
         * @param shortcuts The shortuct definitions.
         * @param source The source of the shortcuts.
         */
        _loadShortcuts(shortcuts, source) {
            for (const shortcut of [...shortcuts]) {
                // A shortcut is a configured command on which the properties
                // `pattern`, and optionally `platform`, were set.
                const platform = shortcut.platform;
                if (!platform || platform === this.config.platform) {
                    let pattern = shortcut.pattern;
                    const command = shortcut;
                    // Patterns using the CTRL modifier target CMD instead for Mac.
                    if (!platform && this.config.platform === Platform.MAC) {
                        pattern = shortcut.pattern.replace(/ctrl/gi, 'CMD');
                    }
                    if (source instanceof JWPlugin) {
                        this.bind(pattern, command, LEVEL.DEFAULT);
                    }
                    else {
                        this.bind(pattern, command, LEVEL.USER);
                    }
                }
            }
        }
    }

    var EditorStage;
    (function (EditorStage) {
        EditorStage["CONFIGURATION"] = "configuration";
        EditorStage["STARTING"] = "starting";
        EditorStage["EDITION"] = "edition";
    })(EditorStage || (EditorStage = {}));
    class JWEditor {
        constructor() {
            this._stage = EditorStage.CONFIGURATION;
            this.plugins = new Map();
            this.configuration = {
                defaults: {
                    Container: ContainerNode,
                    Atomic: AtomicNode,
                    Separator: SeparatorNode,
                },
                plugins: [],
                loadables: {},
                deadlockTimeout: 10000,
            };
            this._memoryID = 0;
            this.loaders = {};
            this._mutex = Promise.resolve();
            this.modes = {
                default: new Mode({
                    id: 'default',
                    rules: [],
                }),
            };
            this.mode = this.modes.default;
            this.dispatcher = new Dispatcher(this);
            this.plugins = new Map();
            this.selection = new VSelection(this);
            this.contextManager = new ContextManager(this, this._execSubCommand.bind(this));
            // Core is a special mandatory plugin that handles the matching between
            // the commands supported in the core of the editor and the VDocument.
            this.load(Core);
            this.load(Keymap);
        }
        /**
         * Set the current mode of the editor.
         */
        setMode(modeIdentifier) {
            this.mode = this.modes[modeIdentifier];
        }
        /**
         * Start the editor on the editable DOM node set on this editor instance.
         */
        async start() {
            this._stage = EditorStage.STARTING;
            this._loadPlugins();
            // Load editor-level loadables.
            if (this.configuration.loadables) {
                for (const loadableId of Object.keys(this.loaders)) {
                    const loadable = this.configuration.loadables[loadableId];
                    if (loadable) {
                        this.loaders[loadableId](loadable, this.configuration);
                    }
                }
            }
            for (const mode of this.configuration.modes || []) {
                this.modes[mode.id] = new Mode(mode);
            }
            if (this.configuration.mode) {
                this.setMode(this.configuration.mode);
            }
            // create memory
            this.memory = new Memory();
            this.memory.attach(this.selection.range.start);
            this.memory.attach(this.selection.range.end);
            this.memoryInfo = makeVersionable({ commandNames: [], uiCommand: false });
            this.memory.attach(this.memoryInfo);
            this.memory.create(this._memoryID.toString());
            // Start all plugins in the first memory slice.
            const startPlugins = async () => {
                for (const plugin of this.plugins.values()) {
                    await plugin.start();
                }
            };
            await this.execCommand(startPlugins);
            this._stage = EditorStage.EDITION;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if the target node is within an editable context.
         *
         * @param target
         */
        isInEditable(node) {
            return isContentEditable(node) || this.mode.is(node, RuleProperty.EDITABLE);
        }
        load(PluginOrLoadables, config) {
            // Actual loading is deferred to `start`.
            if (this._stage !== EditorStage.CONFIGURATION) {
                throw new StageError(EditorStage.CONFIGURATION);
            }
            else if (isConstructor(PluginOrLoadables, JWPlugin)) {
                // Add the plugin to the configuration.
                const Plugin = PluginOrLoadables;
                const plugins = this.configuration.plugins;
                const index = plugins.findIndex(([p]) => p === Plugin);
                if (index !== -1) {
                    // Remove this module from the config to avoid loading it twice.
                    plugins.splice(index, 1);
                }
                plugins.push([Plugin, config || {}]);
            }
            else {
                // Add the loadables to the configuration.
                const configuredLoadables = this.configuration.loadables;
                for (const loadableIdentifier of Object.keys(PluginOrLoadables)) {
                    const loadables = PluginOrLoadables[loadableIdentifier];
                    if (configuredLoadables[loadableIdentifier]) {
                        configuredLoadables[loadableIdentifier].push(...loadables);
                    }
                    else {
                        configuredLoadables[loadableIdentifier] = [...loadables];
                    }
                }
            }
        }
        /**
         * Load the plugins specified in the editor configuration.
         *
         */
        _loadPlugins() {
            // Resolve dependencies.
            const Plugins = [...this.configuration.plugins];
            for (let offset = 1; offset <= Plugins.length; offset++) {
                const index = Plugins.length - offset;
                const [Plugin] = Plugins[index];
                for (const Dependency of [...Plugin.dependencies].reverse()) {
                    const depIndex = Plugins.findIndex(([P]) => P === Dependency);
                    if (depIndex === -1) {
                        // Load the missing dependency with no config parameters.
                        Plugins.splice(index, 0, [Dependency, {}]);
                    }
                    else if (depIndex > index) {
                        // Load the dependency before the plugin depending on it.
                        const [[Dep, config]] = Plugins.splice(depIndex, 1);
                        Plugins.splice(index, 0, [Dep, config]);
                        offset--;
                    }
                }
            }
            // Load plugins.
            for (const [PluginClass, configuration] of Plugins) {
                const plugin = new PluginClass(this, configuration);
                this.plugins.set(PluginClass, plugin);
                // Register the commands of this plugin.
                Object.keys(plugin.commands).forEach(key => {
                    const implementation = Object.assign({}, plugin.commands[key]);
                    // Bind handlers to the plugin itself. This preserves the
                    // typing of the handler parameters which would be lost if
                    // the binding was done in the plugin definition.
                    implementation.handler = implementation.handler.bind(plugin);
                    this.dispatcher.registerCommand(key, implementation);
                });
                // Register the hooks of this plugin.
                for (const [id, hook] of Object.entries(plugin.commandHooks)) {
                    this.dispatcher.registerCommandHook(id, hook.bind(plugin));
                }
                // Load loaders.
                for (const loadableId of Object.keys(plugin.loaders)) {
                    if (this.loaders[loadableId]) {
                        throw new Error(`Multiple loaders for '${loadableId}'.`);
                    }
                    else {
                        // Bind loaders to the plugin itself. This preserves the
                        // typing of the loader parameters which would be lost if
                        // the binding was done in the plugin definition.
                        const loader = plugin.loaders[loadableId];
                        this.loaders[loadableId] = loader.bind(plugin);
                    }
                }
            }
            // Load loadables.
            for (const loadableIdentifier of Object.keys(this.loaders)) {
                for (const plugin of this.plugins.values()) {
                    const loadableArray = plugin.loadables[loadableIdentifier];
                    if (loadableArray) {
                        this.loaders[loadableIdentifier](loadableArray, plugin);
                    }
                }
            }
        }
        configure(PluginOrEditorConfig, pluginConfig) {
            if (this._stage !== EditorStage.CONFIGURATION) {
                throw new StageError(EditorStage.CONFIGURATION);
            }
            else if (isConstructor(PluginOrEditorConfig, JWPlugin)) {
                // Configure the plugin.
                const Plugin = PluginOrEditorConfig;
                const conf = this.configuration.plugins.find(([P]) => P === Plugin);
                if (conf) {
                    // Update the previous config if the plugin was already added.
                    conf[1] = Object.assign(Object.assign({}, conf[1]), pluginConfig);
                }
                else {
                    // Add the new plugin constructor and his configuration.
                    this.configuration.plugins.push([Plugin, pluginConfig]);
                }
            }
            else {
                // Configure the editor.
                const preconf = this.configuration;
                const conf = PluginOrEditorConfig;
                this.configuration = Object.assign(Object.assign({}, preconf), conf);
                // Merge special `defaults` configuration key.
                if (conf.defaults) {
                    this.configuration.defaults = Object.assign(Object.assign({}, preconf.defaults), conf.defaults);
                }
                // Handle special `plugins` configuration key through `load`.
                if (conf.plugins) {
                    this.configuration.plugins = [...preconf.plugins];
                    for (const [Plugin, pluginConfiguration] of conf.plugins) {
                        this.load(Plugin, pluginConfiguration || {});
                    }
                }
                // Handle special `loadables` configuration key through `load`.
                if (conf.loadables) {
                    this.configuration.loadables = Object.assign({}, preconf.loadables);
                    this.load(conf.loadables);
                }
            }
        }
        async nextEventMutex(next) {
            return (this._mutex = this._mutex.then(next.bind(undefined, this._withOpenMemory.bind(this))));
        }
        /**
         * Execute the command or arbitrary code in `callback` in memory.
         * The call to execCommand are executed into a mutex. Every plugin can
         * launch subcommands with the 'JWPlugin.execCommand' method instead.
         *
         * TODO: create memory for each plugin who use the command then use
         * squashInto(winnerSliceKey, winnerSliceKey, newMasterSliceKey)
         *
         * @param commandName name identifier of the command to execute or callback
         * @param params arguments object of the command to execute
         */
        async execCommand(commandName, params) {
            return this.nextEventMutex(async () => {
                return this._withOpenMemory(commandName, params);
            });
        }
        async execWithRange(bounds, commandName, params, mode) {
            const callback = async () => {
                this.memoryInfo.commandNames.push('@withRange');
                let range;
                if (typeof commandName === 'function') {
                    range = new VRange(this, bounds, { mode: params });
                    this.memoryInfo.commandNames.push('@custom' + (commandName.name ? ':' + commandName.name : ''));
                    await commandName(Object.assign(Object.assign({}, this.contextManager.defaultContext), { range }));
                }
                else {
                    range = new VRange(this, bounds, { mode });
                    this.memoryInfo.commandNames.push(commandName);
                    const newParam = Object.assign({ context: {} }, params);
                    newParam.context.range = range;
                    await this.dispatcher.dispatch(commandName, newParam);
                }
                range.remove();
            };
            if (this.memory.isFrozen()) {
                await this.execCommand(callback);
            }
            else {
                await callback();
            }
        }
        /**
         * Stop this editor instance.
         */
        async stop() {
            if (this.memory) {
                this.memory.create('stop');
                this.memory.switchTo('stop'); // Unfreeze the memory.
            }
            for (const plugin of this.plugins.values()) {
                await plugin.stop();
            }
            if (this.memory) {
                this.memory.create('stopped'); // Freeze the memory.
                this.memory = null;
            }
            this.plugins.clear();
            this.dispatcher = new Dispatcher(this);
            this.selection = new VSelection(this);
            this.contextManager = new ContextManager(this, this._execSubCommand);
            // Clear loaders.
            this.loaders = {};
            this._stage = EditorStage.CONFIGURATION;
        }
        async _withOpenMemory(commandName, params) {
            if (!this.memory.isFrozen()) {
                console.error('You are trying to call the external editor' +
                    ' execCommand method from within an execCommand. ' +
                    'Use the `execCommand` method of your plugin instead.');
                return;
            }
            let execCommandTimeout;
            // Switch to the next memory slice (unfreeze the memory).
            const origin = this.memory.sliceKey;
            const memorySlice = this._memoryID.toString();
            this.memory.switchTo(memorySlice);
            this.memoryInfo.commandNames = new VersionableArray();
            this.memoryInfo.uiCommand = false;
            let commandNames = this.memoryInfo.commandNames;
            try {
                const exec = async () => {
                    // Execute command.
                    if (typeof commandName === 'function') {
                        const name = '@custom' + (commandName.name ? ':' + commandName.name : '');
                        this.memoryInfo.commandNames.push(name);
                        await commandName(this.contextManager.defaultContext);
                        if (this.memory.sliceKey !== memorySlice) {
                            // Override by the current commandName if the slice changed.
                            commandNames = [name];
                        }
                    }
                    else {
                        this.memoryInfo.commandNames.push(commandName);
                        await this.dispatcher.dispatch(commandName, params);
                        if (this.memory.sliceKey !== memorySlice) {
                            // Override by the current commandName if the slice changed.
                            commandNames = [commandName];
                        }
                    }
                };
                await new Promise((resolve, reject) => {
                    execCommandTimeout = window.setTimeout(() => {
                        reject({
                            name: 'deadlock',
                            message: 'An execCommand call is taking more than 10 seconds to finish. It might be caused by a deadlock.\n' +
                                'Verify that you do not call editor.execCommand inside another editor.execCommand, ' +
                                'or that a command does not resolve the returned promise.',
                        });
                    }, this.configuration.deadlockTimeout);
                    exec().then(resolve, reject);
                });
                // Prepare nex slice and freeze the memory.
                this._memoryID++;
                const nextMemorySlice = this._memoryID.toString();
                this.memory.create(nextMemorySlice);
                // Send the commit message with a frozen memory.
                const changesLocations = this.memory.getChangesLocations(memorySlice, this.memory.sliceKey);
                await this.dispatcher.dispatch('@commit', {
                    changesLocations: changesLocations,
                    commandNames: [...commandNames],
                });
                clearTimeout(execCommandTimeout);
            }
            catch (error) {
                clearTimeout(execCommandTimeout);
                if (this._stage !== EditorStage.EDITION) {
                    throw error;
                }
                console.error(error);
                await this.dispatcher.dispatch('@error', {
                    message: error.message,
                    stack: error.stack,
                });
                const failedSlice = this.memory.sliceKey;
                // When an error occurs, we go back to part of the functional memory.
                this.memory.switchTo(origin);
                try {
                    // Send the commit message with a frozen memory.
                    const changesLocations = this.memory.getChangesLocations(failedSlice, origin);
                    await this.dispatcher.dispatch('@commit', {
                        changesLocations: changesLocations,
                        commandNames: commandNames,
                    });
                }
                catch (revertError) {
                    if (this._stage !== EditorStage.EDITION) {
                        throw revertError;
                    }
                    await this.dispatcher.dispatch('@error', {
                        message: error.message,
                        stack: error.stack,
                    });
                    console.error(revertError);
                }
                return {
                    error: {
                        name: error.name,
                        message: error.message,
                    },
                };
            }
        }
        /**
         * Execute the command or arbitrary code in `callback` in memory.
         *
         * @param commandName name identifier of the command to execute or callback
         * @param params arguments object of the command to execute
         */
        async _execSubCommand(commandName, params) {
            if (typeof commandName === 'function') {
                this.memoryInfo.commandNames.push('@custom' + (commandName.name ? ':' + commandName.name : ''));
                await commandName(this.contextManager.defaultContext);
            }
            else {
                this.memoryInfo.commandNames.push(commandName);
                await this.dispatcher.dispatch(commandName, params);
            }
        }
    }

    class Parser extends JWPlugin {
        constructor() {
            super(...arguments);
            this.engines = {};
            this.loaders = {
                parsingEngines: this.loadParsingEngines,
                parsers: this.loadParsers,
            };
        }
        async parse(engineId, ...items) {
            const engine = this.engines[engineId];
            if (!engine) {
                throw new Error(`No parsing engine for ${engineId} installed.`);
            }
            return engine.parse(...items);
        }
        loadParsingEngines(parsingEngines) {
            for (const EngineClass of parsingEngines) {
                const id = EngineClass.id;
                if (this.engines[id]) {
                    throw new Error(`Parsing engine ${id} already registered.`);
                }
                const engine = new EngineClass(this.editor);
                this.engines[id] = engine;
            }
        }
        loadParsers(parsers) {
            parsers = [...parsers].reverse();
            for (const ParserClass of parsers) {
                for (const id in this.engines) {
                    const parsingEngine = this.engines[id];
                    const supportedTypes = [id, ...parsingEngine.constructor.extends];
                    if (supportedTypes.includes(ParserClass.id)) {
                        parsingEngine.register(ParserClass);
                    }
                }
            }
        }
    }

    class Renderer extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loaders = {
                renderingEngines: this.loadRenderingEngines,
                renderers: this.loadRenderers,
            };
            this.engines = {};
        }
        /**
         * @override
         */
        stop() {
            this.engines = {};
            return super.stop();
        }
        async render(renderingId, nodes) {
            const engine = this.engines[renderingId];
            if (!engine) {
                // The caller might want to fallback on another rendering.
                return;
            }
            if (nodes instanceof Array) {
                const cache = await engine.render(nodes);
                return nodes.map(node => cache.renderings.get(node));
            }
            else {
                const cache = await engine.render([nodes]);
                return cache.renderings.get(nodes);
            }
        }
        loadRenderingEngines(renderingEngines) {
            for (const EngineClass of renderingEngines) {
                const id = EngineClass.id;
                if (this.engines[id]) {
                    throw new Error(`Rendering engine ${id} already registered.`);
                }
                const engine = new EngineClass(this.editor);
                this.engines[id] = engine;
            }
        }
        loadRenderers(renderers) {
            renderers = [...renderers].reverse();
            for (const RendererClass of renderers) {
                if (!RendererClass.id) {
                    throw new Error('Missing rendering engine ID.');
                }
                for (const id in this.engines) {
                    const renderingEngine = this.engines[id];
                    const supportedTypes = [id, ...renderingEngine.constructor.extends];
                    if (supportedTypes.includes(RendererClass.id)) {
                        renderingEngine.register(RendererClass);
                    }
                }
            }
        }
    }

    class ParsingEngine {
        constructor(editor) {
            this.parsers = [];
            this.parsingMap = new Map();
            this.editor = editor;
            const defaultParser = new this.constructor.defaultParser(this);
            if (defaultParser.predicate) {
                throw new Error(`Default renderer cannot have a predicate.`);
            }
            else {
                this.parsers.push(defaultParser);
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Register the given parser by instantiating it with this parser engine.
         *
         * @param ParserClass
         */
        register(ParserClass) {
            if (ParserClass.id === this.constructor.id) {
                this.parsers.unshift(new ParserClass(this));
            }
            else {
                const supportedTypes = [this.constructor.id, ...this.constructor.extends];
                const priorParserIds = supportedTypes.slice(0, supportedTypes.indexOf(ParserClass.id));
                const postParserIndex = this.parsers.findIndex(parser => !priorParserIds.includes(parser.constructor.id));
                this.parsers.splice(postParserIndex, 0, new ParserClass(this));
            }
        }
        /**
         * Parse items into the editor's virtual `VNode` representation.
         *
         * @param items the items to parse
         * @returns Promise resolved by the element parsed into the editor virtual
         * VNode representation
         */
        async parse(...items) {
            const nodes = [];
            const childPromises = items.map(node => this._parseItem(node));
            const resList = await Promise.all(childPromises);
            for (const res of resList) {
                nodes.push(...res);
            }
            return nodes;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Parse an item into the editor's virtual representation.
         *
         */
        async _parseItem(item) {
            let nodes;
            for (const parser of this.parsers) {
                if (!parser.predicate || parser.predicate(item)) {
                    nodes = await parser.parse(item);
                    break;
                }
            }
            if (nodes.length >= 1) {
                this.parsingMap.set(item, nodes);
            }
            return nodes;
        }
    }
    ParsingEngine.extends = [];

    class AbstractParser {
        constructor(engine) {
            this.engine = engine;
        }
    }

    class DefaultXmlDomParser extends AbstractParser {
        async parse(item) {
            // If the node could not be parsed, create a generic element node with
            // the HTML tag of the DOM Node. This way we may not support the node
            // but we don't break it either.
            const element = new TagNode({ htmlTag: nodeName(item) });
            if (item instanceof Element) {
                const attributes = this.engine.parseAttributes(item);
                if (attributes.length) {
                    element.modifiers.append(attributes);
                }
            }
            const nodes = await this.engine.parse(...item.childNodes);
            element.append(...nodes);
            return [element];
        }
    }
    DefaultXmlDomParser.id = 'dom/xml';

    class XmlDomParsingEngine extends ParsingEngine {
        /**
         * Parse a node's attributes and return them.
         *
         * @param node
         */
        parseAttributes(node) {
            return new Attributes(node.attributes);
        }
    }
    XmlDomParsingEngine.id = 'dom/xml';
    XmlDomParsingEngine.defaultParser = DefaultXmlDomParser;

    class SuperModifierRenderer {
        constructor(renderer) {
            this.renderer = renderer;
        }
        /**
         * Render the given modifier and return a list of DomObject witch
         * the applied modifier. The list can have an other len of the given
         * list of DomObject.
         *
         * @param modifier
         * @param contents
         * @param batch
         */
        render(modifier, contents, batch, worker) {
            const nextRenderer = worker.getCompatibleModifierRenderer(modifier, this.renderer);
            return nextRenderer === null || nextRenderer === void 0 ? void 0 : nextRenderer.render(modifier, contents, batch, worker);
        }
    }
    class ModifierRenderer {
        constructor(engine) {
            this.engine = engine;
            this.super = new SuperModifierRenderer(this);
        }
    }

    class SuperRenderer {
        constructor(renderer) {
            this.renderer = renderer;
        }
        /**
         * Render the given node.
         *
         * @param node
         */
        render(node, worker) {
            const nextRenderer = worker.getCompatibleRenderer(node, this.renderer);
            return nextRenderer === null || nextRenderer === void 0 ? void 0 : nextRenderer.render(node, worker);
        }
        /**
         * Render the given group of nodes.
         *
         * @param node
         */
        async renderBatch(nodes, worker) {
            await Promise.all(worker.renderBatched(nodes, this.renderer));
            return nodes.map(node => worker.getRendering(node));
        }
    }
    class NodeRenderer {
        constructor(engine) {
            this.engine = engine;
            this.super = new SuperRenderer(this);
        }
        /**
         * Render the given group of nodes.
         * The indices of the DomObject list match the indices of the given nodes
         * list.
         *
         * @param node
         */
        renderBatch(nodes, worker) {
            return Promise.all(nodes.map(node => this.render(node, worker)));
        }
    }

    class RenderingEngineCache {
        constructor(engine) {
            // Rendering created by a VNode.
            this.renderings = new Map();
            // Promise resolved when the renderings is ready. We can have a value in renderings before the
            // promise is resolved but it's not the complete value (for eg: we create the node and an other
            // renderer add the attributes on this node)
            this.renderingPromises = new Map();
            // VNodes locations in a rendering (by default the rendering is equal to the location).
            this.locations = new Map();
            // List of VNode and Modifiers linked to a rendering.
            // When the rendering is invalidated every VNode or Modifier will be invalidated.
            this.renderingDependent = new Map();
            // When the VNode or Modifier is invalidated every rendering will be invalidated.
            this.nodeDependent = new Map();
            // When the dependency is invalidated every dependents will be invalidated.
            this.linkedNodes = new Map();
            // Cache for founded renderer.
            this.cachedCompatibleRenderer = new Map();
            this.cachedCompatibleModifierRenderer = new Map();
            // Cache to compare modifiers.
            this.cachedModifierId = new Map();
            this.cachedIsSameAsModifier = {};
            // Used to invalidate the cachedIsSameAsModifier values.
            this.cachedIsSameAsModifierIds = {};
            this.optimizeModifiersRendering = true;
            this.worker = {
                depends: engine.depends.bind(engine, this),
                renderBatched: engine.renderBatched.bind(engine, this),
                getCompatibleRenderer: engine.getCompatibleRenderer.bind(engine, this),
                getCompatibleModifierRenderer: engine.getCompatibleModifierRenderer.bind(engine, this),
                locate: engine.locate.bind(engine, this),
                getRendering: (node) => this.renderings.get(node),
                render: async (nodes) => {
                    await engine.render(nodes, this);
                    return nodes.map(node => this.renderings.get(node));
                },
            };
        }
    }

    let modifierId = 0;
    class RenderingEngine {
        constructor(editor) {
            this.renderers = [];
            this.modifierRenderers = [];
            this.editor = editor;
            if (this.constructor.defaultRenderer) {
                const defaultRenderer = new this.constructor.defaultRenderer(this);
                if (defaultRenderer.predicate) {
                    throw new Error(`Default renderer cannot have a predicate.`);
                }
                else {
                    this.renderers.push(defaultRenderer);
                }
            }
            if (this.constructor.defaultModifierRenderer) {
                const defaultModifierRenderer = new this.constructor.defaultModifierRenderer(this);
                if (defaultModifierRenderer.predicate) {
                    throw new Error(`Default renderer cannot have a predicate.`);
                }
                else {
                    this.modifierRenderers.push(defaultModifierRenderer);
                }
            }
        }
        /**
         * Register the given renderer by instantiating it with this rendering
         * engine. The renderer constructor will receive a special second parameter
         * which is a magic renderer whose `render` method will call the next
         * compatible renderer in line for the given node.
         *
         * @param RendererClass
         */
        register(RendererClass) {
            // Both input parameter types have the same features with respect to
            // what we are doing in this function. However, Typescript requires a
            // stronger typing for inserting them into an array. We chose to use a
            // blind, somewhat wrong, typecast to reduce the scope of the types
            // in order to avoid duplicating the logic of this function.
            const renderers = (isConstructor(RendererClass, NodeRenderer)
                ? this.renderers
                : this.modifierRenderers);
            RendererClass = RendererClass;
            if (RendererClass.id === this.constructor.id) {
                renderers.unshift(new RendererClass(this));
            }
            else {
                const supportedTypes = [this.constructor.id, ...this.constructor.extends];
                const priorRendererIds = supportedTypes.slice(0, supportedTypes.indexOf(RendererClass.id));
                const postRendererIndex = renderers.findIndex(parser => !priorRendererIds.includes(parser.constructor.id));
                renderers.splice(postRendererIndex, 0, new RendererClass(this));
            }
        }
        /**
         * Render the given node. If a prior rendering already exists for this node
         * in this run, return it directly.
         * The cache are automaticaly invalidate if the nodes are not linked to the
         * memory (linked to a layout root for eg)
         *
         * @param nodes
         */
        async render(nodes, cache, optimizeModifiersRendering) {
            if (!cache) {
                cache = new RenderingEngineCache(this);
            }
            if (typeof optimizeModifiersRendering === 'boolean') {
                cache.optimizeModifiersRendering = optimizeModifiersRendering;
            }
            const promises = this.renderBatched(cache, nodes.filter(node => !cache.renderingPromises.get(node)));
            await Promise.all(promises); // wait the newest promises
            await Promise.all(nodes.map(node => cache.renderingPromises.get(node))); // wait indifidual promise
            return cache;
        }
        /**
         * Indicates the location of the nodes in the rendering performed.
         *
         * For example, if you avec a 2 charNodes (X, Y) seperate by a linebreak
         * but, you want to display one text node, you can have a text node equal
         * to 'x_y' and indicate that it's [charNode, LineBreak, CharNode].
         * Or you want to display the Linebreak twice: 'x_y_' and indicate this
         * [charNode, LineBreak, CharNode, LineBreak]
         *
         * @param nodes
         * @param rendering
         */
        locate(cache, nodes, value) {
            cache.locations.set(value, nodes);
        }
        /**
         * Group the nodes and call the renderer 'renderBatch' method with the
         * different groups of nodes. By default each group is composed with only
         * one node.
         * The indices of the DomObject list match the indices of the given nodes
         * list.
         *
         * @see renderBatch
         *
         * @param nodes
         * @param rendered
         */
        renderBatched(cache, nodes, rendered) {
            const promises = [];
            for (const node of nodes) {
                const renderer = cache.worker.getCompatibleRenderer(node, rendered);
                const renderings = renderer.renderBatch(nodes, cache.worker);
                const promise = renderings.then(values => {
                    const value = values[0];
                    this.depends(cache, node, value);
                    this.depends(cache, value, node);
                    this._addDefaultLocation(cache, node, value);
                    cache.renderings.set(node, value);
                });
                cache.renderingPromises.set(node, promise);
                promises.push(promise);
            }
            return promises;
        }
        /**
         * Return the the first matching Renderer for this VNode, starting from the
         * previous renderer.
         *
         * @param node
         * @param previousRenderer
         */
        getCompatibleRenderer(cache, node, previousRenderer) {
            let cacheCompatible = cache.cachedCompatibleRenderer.get(node);
            if (!cacheCompatible) {
                cacheCompatible = new Map();
                cache.cachedCompatibleRenderer.set(node, cacheCompatible);
            }
            else if (cacheCompatible.get(previousRenderer)) {
                return cacheCompatible.get(previousRenderer);
            }
            let nextRendererIndex = this.renderers.indexOf(previousRenderer) + 1;
            let nextRenderer;
            do {
                nextRenderer = this.renderers[nextRendererIndex];
                nextRendererIndex++;
            } while (nextRenderer && !node.test(nextRenderer.predicate));
            cacheCompatible.set(previousRenderer, nextRenderer);
            return nextRenderer;
        }
        /**
         * Return the the first matching Renderer for this VNode, starting from the
         * previous renderer.
         *
         * @param node
         * @param previousRenderer
         */
        getCompatibleModifierRenderer(cache, modifier, previousRenderer) {
            let cacheCompatible = cache.cachedCompatibleModifierRenderer.get(modifier);
            if (!cacheCompatible) {
                cacheCompatible = new Map();
                cache.cachedCompatibleModifierRenderer.set(modifier, cacheCompatible);
            }
            else if (cacheCompatible.get(previousRenderer)) {
                return cacheCompatible.get(previousRenderer);
            }
            let nextRendererIndex = this.modifierRenderers.indexOf(previousRenderer) + 1;
            let nextRenderer;
            do {
                nextRenderer = this.modifierRenderers[nextRendererIndex];
                nextRendererIndex++;
            } while (nextRenderer.predicate &&
                !(isConstructor(nextRenderer.predicate, Modifier)
                    ? modifier instanceof nextRenderer.predicate
                    : nextRenderer.predicate(modifier)));
            cacheCompatible.set(previousRenderer, nextRenderer);
            return nextRenderer;
        }
        depends(cache, dependent, dependency) {
            let dNode;
            let dRendering;
            let dyNode;
            let dyRendering;
            if (dependent instanceof AbstractNode || dependent instanceof Modifier) {
                dNode = dependent;
            }
            else {
                dRendering = dependent;
            }
            if (dependency instanceof AbstractNode || dependency instanceof Modifier) {
                dyNode = dependency;
            }
            else {
                dyRendering = dependency;
            }
            if (dNode) {
                if (dyNode) {
                    const linked = cache.linkedNodes.get(dyNode);
                    if (linked) {
                        linked.add(dNode);
                    }
                    else {
                        cache.linkedNodes.set(dyNode, new Set([dNode]));
                    }
                }
                else {
                    const from = cache.renderingDependent.get(dyRendering);
                    if (from) {
                        from.add(dNode);
                    }
                    else {
                        cache.renderingDependent.set(dyRendering, new Set([dNode]));
                    }
                }
            }
            else if (dyNode) {
                const linked = cache.nodeDependent.get(dyNode);
                if (linked) {
                    linked.add(dRendering);
                }
                else {
                    cache.nodeDependent.set(dyNode, new Set([dRendering]));
                }
            }
        }
        _addDefaultLocation(cache, node, value) {
            cache.locations.set(value, [node]);
        }
        _modifierIsSameAs(cache, modifierA, modifierB) {
            if (modifierA === modifierB) {
                return true;
            }
            let idA = modifierA ? cache.cachedModifierId.get(modifierA) : 'null';
            if (!idA) {
                idA = ++modifierId;
                cache.cachedModifierId.set(modifierA, idA);
            }
            let idB = modifierB ? cache.cachedModifierId.get(modifierB) : 'null';
            if (!idB) {
                idB = ++modifierId;
                cache.cachedModifierId.set(modifierB, idB);
            }
            const key = idA > idB ? idA + '-' + idB : idB + '-' + idA;
            if (key in cache.cachedIsSameAsModifier) {
                return cache.cachedIsSameAsModifier[key];
            }
            const isSame = (!modifierA || modifierA.isSameAs(modifierB)) &&
                (!modifierB || modifierB.isSameAs(modifierA));
            cache.cachedIsSameAsModifier[key] = isSame;
            if (!cache.cachedIsSameAsModifierIds[idA]) {
                cache.cachedIsSameAsModifierIds[idA] = [key];
            }
            else {
                cache.cachedIsSameAsModifierIds[idA].push(key);
            }
            if (!cache.cachedIsSameAsModifierIds[idB]) {
                cache.cachedIsSameAsModifierIds[idB] = [key];
            }
            else {
                cache.cachedIsSameAsModifierIds[idB].push(key);
            }
            return isSame;
        }
    }
    RenderingEngine.extends = [];

    class AtomicTagNode extends AtomicNode {
        constructor(params) {
            super();
            this.htmlTag = params.htmlTag;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(params) {
            const defaults = {
                htmlTag: this.htmlTag,
            };
            return super.clone(Object.assign(Object.assign({}, defaults), params));
        }
    }

    class DefaultDomObjectRenderer extends NodeRenderer {
        async render(node) {
            let domObject;
            if (node.tangible) {
                if (node instanceof AtomicTagNode && node.htmlTag[0] !== '#') {
                    domObject = {
                        tag: node.htmlTag,
                    };
                }
                else if (node instanceof TagNode && node.htmlTag[0] !== '#') {
                    domObject = {
                        tag: node.htmlTag,
                        children: await this.engine.renderChildren(node),
                    };
                }
                else if (node instanceof FragmentNode) {
                    domObject = {
                        children: await this.engine.renderChildren(node),
                    };
                }
                else if (node instanceof AtomicNode) {
                    domObject = { children: [] };
                }
                else {
                    domObject = {
                        tag: node.name,
                        attributes: {
                            id: node.id.toString(),
                        },
                        children: await this.engine.renderChildren(node),
                    };
                }
            }
            else {
                domObject = { children: [] };
            }
            return domObject;
        }
    }
    DefaultDomObjectRenderer.id = 'object/html';

    class DefaultDomObjectModifierRenderer extends ModifierRenderer {
        /**
         * Default rendering for Modifier.
         *
         * @param modifier
         * @param contents
         */
        async render(modifier, contents) {
            return contents;
        }
    }
    DefaultDomObjectModifierRenderer.id = 'object/html';

    class DomObjectRenderingEngine extends RenderingEngine {
        /**
         * Render the attributes of the given VNode onto the given DOM Element.
         *
         * @param Class
         * @param node
         * @param element
         */
        renderAttributes(Class, node, item, worker) {
            if ('tag' in item) {
                if (!item.attributes)
                    item.attributes = {};
                const attributes = node.modifiers.find(Class);
                if (attributes) {
                    const attr = item.attributes;
                    for (const name of attributes.keys()) {
                        if (name === 'class') {
                            if (!attr.class)
                                attr.class = new Set();
                            for (const className of attributes.classList.items()) {
                                attr.class.add(className);
                            }
                        }
                        else if (name === 'style') {
                            attr.style = Object.assign({}, attributes.style.toJSON(), attr.style);
                        }
                        else {
                            attr[name] = attributes.get(name);
                        }
                    }
                    worker.depends(item, attributes);
                }
            }
        }
        /**
         * @overwrite
         */
        async renderChildren(node) {
            const children = node.children();
            if (!children.length && this.editor.mode.is(node, RuleProperty.ALLOW_EMPTY) !== true) {
                children.push({ tag: 'BR' });
            }
            return children;
        }
        /**
         * Render a placeholder for the given child node.
         *
         * @param child
         */
        renderPlaceholder(child) {
            const placeholder = document.createElement('jw-domobject-vnode');
            placeholder.id = child.id.toString();
            return placeholder;
        }
        /**
         * Convert every VNode children into domObjects
         *
         * @param domObject
         */
        async resolveChildren(domObject, worker) {
            const stack = [domObject];
            for (const domObject of stack) {
                if ('children' in domObject) {
                    const children = [];
                    const childNodes = domObject.children.filter(child => child instanceof AbstractNode);
                    const domObjects = await worker.render(childNodes);
                    for (const index in domObject.children) {
                        const child = domObject.children[index];
                        let childObject;
                        if (child instanceof AbstractNode) {
                            childObject = domObjects.shift();
                        }
                        else {
                            childObject = child;
                        }
                        if (!stack.includes(childObject)) {
                            children.push(childObject);
                            stack.push(childObject);
                        }
                    }
                    domObject.children = children;
                }
            }
        }
        /**
         * Group the nodes by renderer, siblings and format.
         *
         * @override
         */
        renderBatched(cache, nodes, rendered) {
            const renderingUnits = this._getRenderingUnits(cache, nodes, rendered);
            return this._renderBatched(cache, renderingUnits);
        }
        /**
         * Group the nodes by format and by renderer and call 'renderBatch' with
         * the different group. Wrap the created domObject into the fromated
         * domObjectElement if needed.
         * Return a list of the rendered vNode and list of DomObjects. The indices
         * of the DomObject list match the indices of the given nodes
         * list.
         *
         * @param renderingUnits
         */
        _renderBatched(cache, renderingUnits) {
            var _a;
            const batchPromises = [];
            for (let unitIndex = 0; unitIndex < renderingUnits.length; unitIndex++) {
                let nextUnitIndex = unitIndex;
                const unit = renderingUnits[unitIndex];
                if (unit && unit[1].length) {
                    // Group same formating.
                    const modifier = unit[1][0];
                    let lastUnit = [unit[0], unit[1].slice(1), unit[2]];
                    const newRenderingUnits = [lastUnit];
                    let nextUnit;
                    while ((nextUnit = renderingUnits[nextUnitIndex + 1]) &&
                        lastUnit[0].parent === nextUnit[0].parent &&
                        nextUnit[1].length &&
                        this._modifierIsSameAs(cache, modifier, (_a = nextUnit[1]) === null || _a === void 0 ? void 0 : _a[0])) {
                        nextUnitIndex++;
                        lastUnit = renderingUnits[nextUnitIndex];
                        newRenderingUnits.push([lastUnit[0], lastUnit[1].slice(1), lastUnit[2]]);
                    }
                    // Render wrapped nodes.
                    const promises = this._renderBatched(cache, newRenderingUnits);
                    const nodes = newRenderingUnits.map(u => u[0]);
                    const modifierPromise = Promise.all(promises).then(async () => {
                        const domObjects = [];
                        for (const domObject of nodes.map(node => cache.renderings.get(node))) {
                            if (!domObjects.includes(domObject)) {
                                domObjects.push(domObject);
                            }
                        }
                        // Create format.
                        const modifierRenderer = this.getCompatibleModifierRenderer(cache, modifier);
                        const wraps = await modifierRenderer.render(modifier, domObjects, nodes, cache.worker);
                        // Add origins.
                        for (const wrap of wraps) {
                            const stack = [wrap];
                            for (const domObject of stack) {
                                const origins = cache.renderingDependent.get(domObject);
                                if (origins) {
                                    for (const origin of origins) {
                                        this.depends(cache, origin, wrap);
                                        this.depends(cache, wrap, origin);
                                    }
                                }
                                if ('children' in domObject) {
                                    for (const child of domObject.children) {
                                        if (!(child instanceof AbstractNode)) {
                                            stack.push(child);
                                        }
                                    }
                                }
                            }
                            this.depends(cache, modifier, wrap);
                            this.depends(cache, wrap, modifier);
                        }
                        // Update the renderings promise.
                        for (const node of nodes) {
                            const wrap = wraps.find(wrap => { var _a; return (_a = cache.renderingDependent.get(wrap)) === null || _a === void 0 ? void 0 : _a.has(node); });
                            cache.renderings.set(node, wrap);
                        }
                    });
                    for (const node of nodes) {
                        cache.renderingPromises.set(node, modifierPromise);
                    }
                    batchPromises.push(modifierPromise);
                }
                else {
                    // Render each node.
                    let currentRenderer;
                    let renderingUnit;
                    const siblings = [];
                    while ((renderingUnit = renderingUnits[nextUnitIndex]) &&
                        (!currentRenderer ||
                            (!renderingUnit[1].length &&
                                currentRenderer === renderingUnit[2] &&
                                (!siblings.length ||
                                    siblings[siblings.length - 1].parent === renderingUnit[0].parent)))) {
                        nextUnitIndex++;
                        siblings.push(renderingUnit[0]);
                        currentRenderer = renderingUnit[2];
                    }
                    if (currentRenderer) {
                        const promise = new Promise(resolve => {
                            Promise.resolve().then(() => {
                                currentRenderer.renderBatch(siblings, cache.worker).then(domObjects => {
                                    // Set the value, add origins and locations.
                                    for (const index in siblings) {
                                        const node = siblings[index];
                                        const value = domObjects[index];
                                        this.depends(cache, node, value);
                                        this.depends(cache, value, node);
                                        this._addDefaultLocation(cache, node, value);
                                        cache.renderings.set(node, value);
                                    }
                                    resolve();
                                });
                            });
                        });
                        for (const sibling of siblings) {
                            cache.renderingPromises.set(sibling, promise);
                        }
                        batchPromises.push(promise);
                        nextUnitIndex--;
                    }
                }
                unitIndex = nextUnitIndex;
            }
            return batchPromises;
        }
        /**
         * Compute list of nodes, format and rendering.
         * Add the siblings node into the list for future grouping for 'renderBatch'
         * method.
         *
         * @param nodes
         * @param rendered
         */
        _getRenderingUnits(cache, nodes, rendered) {
            // Consecutive char nodes are rendered in same time.
            const renderingUnits = [];
            const setNodes = new Set(nodes); // Use set for perf.
            const selected = new Set();
            for (const node of nodes) {
                if (selected.has(node)) {
                    continue;
                }
                const parent = node.parent;
                if (parent) {
                    const markers = [];
                    parent.childVNodes.forEach(sibling => {
                        // Filter and sort the nodes.
                        if (setNodes.has(sibling)) {
                            if (sibling.tangible) {
                                renderingUnits.push(this._createUnit(cache, sibling, rendered));
                            }
                            else {
                                // Not tangible node are add after other nodes (don't cut text node).
                                markers.push(sibling);
                            }
                            selected.add(sibling);
                        }
                        else if (sibling.tangible) {
                            renderingUnits.push(null);
                        }
                    });
                    for (const marker of markers) {
                        renderingUnits.push(this._createUnit(cache, marker, rendered));
                    }
                }
                else {
                    renderingUnits.push(this._createUnit(cache, node, rendered));
                }
            }
            if (cache.optimizeModifiersRendering) {
                this._optimizeModifiersRendering(cache, renderingUnits);
            }
            return renderingUnits;
        }
        /**
         * The modifiers will be sorted to be rendererd with the minimum of tag and keep the hight
         * modifier level.
         *
         * Eg: change this (without space of course):
         *      <b>
         *          <i>
         *              _
         *              <a href="#">__</a>
         *          </i>
         *          <a href="#">_</a>
         *          <i>
         *              <a href="#">__</a>
         *          </i>
         *      </b>
         * Into this to keep the link:
         *      <b>
         *          <i>_</i>
         *          <a href="#">
         *              <i>__</i>
         *              _
         *              <i>__</i>
         *          </a>
         *      </b>
         *
         * @param cache
         * @param renderingUnits
         */
        _optimizeModifiersRendering(cache, renderingUnits) {
            // Clone to use pop after and create the intervales.
            const unitToModifiers = new Map();
            for (const renderingUnit of renderingUnits) {
                if (renderingUnit) {
                    unitToModifiers.set(renderingUnit, [...renderingUnit[1]]);
                }
            }
            // Group by same modifier, then order the modifiers and take care of the level.
            // Create modifiers interval (Modifier, level, index begin, index end).
            const intervals = [];
            for (let i = 0; i < renderingUnits.length; i++) {
                const renderingUnit = renderingUnits[i];
                const unitModifiers = unitToModifiers.get(renderingUnit);
                if (unitModifiers) {
                    while (unitModifiers.length) {
                        // Take the first modifier and group.
                        const modifierToSort = unitModifiers.pop();
                        const level = modifierToSort.level;
                        if (!level) {
                            continue;
                        }
                        const modifiers = [modifierToSort];
                        const groupIndexes = [0];
                        let next;
                        let nextIndex = i + 1;
                        while ((next = renderingUnits[nextIndex]) && unitToModifiers.get(next)) {
                            const modifierIndex = unitToModifiers
                                .get(next)
                                .findIndex(modifier => this._modifierIsSameAs(cache, modifierToSort, modifier));
                            if (modifierIndex === -1) {
                                break;
                            }
                            else {
                                const modifier = unitToModifiers.get(next)[modifierIndex];
                                groupIndexes.push(next[1].indexOf(modifier));
                                modifiers.push(modifier);
                                unitToModifiers.get(next).splice(modifierIndex, 1);
                                nextIndex++;
                            }
                        }
                        intervals.push([modifiers, level, i, nextIndex - 1]);
                    }
                }
            }
            // Split interval if break an interval with greatest level.
            for (let i = 0; i < intervals.length; i++) {
                const self = intervals[i];
                // Use the same length because the newest are already splitted for this loop.
                const len = intervals.length;
                for (let u = 0; u < len; u++) {
                    if (u === i) {
                        continue;
                    }
                    const other = intervals[u];
                    if (self[1] > other[1] ||
                        (self[1] === other[1] && self[3] - self[2] > other[3] - other[2])) {
                        // If greatest level or greatest number of VNodes split other modifiers.
                        if (self[2] > other[2] && self[2] <= other[3] && self[3] > other[3]) {
                            intervals.push([
                                other[0].splice(0, other[3] - self[2] + 1),
                                other[1],
                                self[2],
                                other[3],
                            ]);
                            other[3] = self[2] - 1;
                        }
                        else if (self[3] >= other[2] && self[3] < other[3] && self[2] < other[2]) {
                            intervals.push([
                                other[0].splice(0, self[3] - other[2] + 1),
                                other[1],
                                other[2],
                                self[3],
                            ]);
                            other[2] = self[3] + 1;
                        }
                    }
                }
            }
            // Sort by largest interval.
            intervals.sort((a, b) => a[3] - a[2] - b[3] + b[2]);
            // Sort the modifiers in unit from the interval order.
            for (const interval of intervals) {
                const nodes = [];
                for (let i = interval[2]; i <= interval[3]; i++) {
                    const modifer = interval[0][i - interval[2]];
                    const modifiers = renderingUnits[i][1];
                    modifiers.splice(modifiers.indexOf(modifer), 1);
                    modifiers.unshift(modifer);
                    nodes.push(renderingUnits[i][0]);
                }
            }
        }
        _createUnit(cache, node, rendered) {
            const renderer = cache.worker.getCompatibleRenderer(node, rendered);
            // Remove modifier who render nothing.
            const modifiers = node.modifiers.filter(modifer => !this._modifierIsSameAs(cache, modifer, null));
            return [node, modifiers, renderer];
        }
        _addDefaultLocation(cache, node, domObject) {
            let located = false;
            const stack = [domObject];
            for (const object of stack) {
                if (cache.locations.get(object)) {
                    located = true;
                    break;
                }
                if ('children' in object) {
                    for (const child of object.children) {
                        if (!(child instanceof AbstractNode)) {
                            if (stack.includes(child)) {
                                throw new Error('Loop in rendering object.');
                            }
                            stack.push(child);
                        }
                    }
                }
            }
            if (!located) {
                cache.locations.set(domObject, [node]);
            }
        }
    }
    DomObjectRenderingEngine.id = 'object/html';
    DomObjectRenderingEngine.defaultRenderer = DefaultDomObjectRenderer;
    DomObjectRenderingEngine.defaultModifierRenderer = DefaultDomObjectModifierRenderer;

    class AttributesDomObjectModifierRenderer extends ModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = Attributes;
        }
        /**
         * Rendering for Format Modifier.
         *
         * @param format
         * @param contents
         */
        async render(modifier, contents) {
            const keys = modifier.keys();
            const classHistory = modifier.classList.history();
            if (keys.length || Object.keys(classHistory).length) {
                const attributes = {};
                for (const name of keys) {
                    if (name === 'class') {
                        // This is going to use the class history feature anyway.
                        // TODO: This entire file should probably be reorganized to
                        // avoid using a `DomObjectAttributes` object in between.
                        attributes.class = new Set();
                    }
                    else if (name === 'style') {
                        attributes.style = modifier.style.toJSON();
                    }
                    else {
                        attributes[name] = modifier.get(name);
                    }
                }
                const newContents = [];
                for (let index = 0; index < contents.length; index++) {
                    let content = contents[index];
                    if ('tag' in content) {
                        this._applyAttributes(content, attributes, classHistory);
                    }
                    else if ('children' in content &&
                        !content.children.find(domObject => !('tag' in domObject) &&
                            !('text' in domObject && domObject.text === '\u200b'))) {
                        for (const child of content.children) {
                            if ('tag' in child) {
                                this._applyAttributes(child, attributes, classHistory);
                            }
                        }
                    }
                    else {
                        const children = [];
                        let newIndex = index;
                        while (newIndex <= contents.length &&
                            ('text' in content ||
                                'dom' in content ||
                                ('children' in content && content.children.length))) {
                            if (!children.includes(content)) {
                                children.push(content);
                            }
                            newIndex++;
                        }
                        if (children.length) {
                            content = {
                                tag: 'SPAN',
                                attributes: Object.assign({}, attributes),
                                children: children,
                            };
                        }
                    }
                    newContents.push(content);
                }
                contents = newContents;
            }
            return contents;
        }
        _applyAttributes(content, attributes, classHistory) {
            if (!content.attributes)
                content.attributes = {};
            const attr = content.attributes;
            for (const name in attributes) {
                if (name === 'class') {
                    this._applyClassHistory(content, classHistory);
                }
                else if (name === 'style') {
                    attr.style = Object.assign({}, attributes.style, attr.style);
                }
                else {
                    attr[name] = attributes[name];
                }
            }
        }
        /**
         * Apply the history of the class attributes stored in the given Record to
         * the given DomObject. Basically, if the DomObject is restoring a class
         * that used to be present in the class history, it will be reordered to
         * match its original position.
         *
         * @param content
         * @param classHistory
         */
        _applyClassHistory(content, classHistory) {
            var _a;
            // Reorganize `class` set to restore order thanks to ClassList history.
            const classNames = new Set();
            if (content.attributes.class) {
                for (const className of content.attributes.class) {
                    if (classHistory[className] !== false) {
                        classNames.add(className);
                    }
                }
            }
            for (const className in classHistory) {
                if (classHistory[className] || ((_a = content.attributes.class) === null || _a === void 0 ? void 0 : _a.has(className))) {
                    classNames.add(className);
                }
            }
            content.attributes.class = classNames;
        }
    }
    AttributesDomObjectModifierRenderer.id = DomObjectRenderingEngine.id;

    class Xml extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsingEngines: [XmlDomParsingEngine],
                renderers: [AttributesDomObjectModifierRenderer],
            };
        }
    }
    Xml.dependencies = [Parser, Renderer];

    class Format extends Modifier {
        constructor(htmlTag) {
            super();
            this.modifiers = new Modifiers();
            if (htmlTag) {
                this.htmlTag = htmlTag;
            }
        }
        get name() {
            return this.htmlTag.toLowerCase();
        }
        get modifiers() {
            return this._modifiers;
        }
        set modifiers(modifiers) {
            if (this._modifiers) {
                this._modifiers.off('update');
            }
            this._modifiers = modifiers;
            this._modifiers.on('update', () => this.trigger('modifierUpdate'));
        }
        toString() {
            const nonEmptyAttributes = this.modifiers.filter(modifier => !(modifier instanceof Attributes) || !!modifier.length);
            if (nonEmptyAttributes.length) {
                const modifiersRepr = [];
                for (const modifier of nonEmptyAttributes) {
                    modifiersRepr.push(modifier.toString());
                }
                return `${this.name}[${modifiersRepr.join(', ')}]`;
            }
            else {
                return this.name;
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        clone() {
            const clone = new this.constructor();
            clone.htmlTag = this.htmlTag;
            clone.modifiers = this.modifiers.clone();
            return clone;
        }
        isSameAs(otherFormat) {
            const aModifiers = this.modifiers;
            const bModifiers = otherFormat === null || otherFormat === void 0 ? void 0 : otherFormat.modifiers;
            return otherFormat instanceof this.constructor && aModifiers.areSameAs(bModifiers);
        }
    }

    class FormatDomObjectModifierRenderer extends ModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = Format;
        }
        /**
         * Rendering for Format Modifier.
         *
         * @param format
         * @param contents
         */
        async render(format, contents) {
            const domObject = {
                tag: format.htmlTag.toUpperCase(),
                children: contents,
            };
            const attributes = format.modifiers.find(Attributes);
            const keys = attributes === null || attributes === void 0 ? void 0 : attributes.keys();
            if (keys === null || keys === void 0 ? void 0 : keys.length) {
                domObject.attributes = {};
                const attr = domObject.attributes;
                for (const name of keys) {
                    if (name === 'class') {
                        if (!attr.class)
                            attr.class = new Set();
                        for (const className of attributes.classList.items()) {
                            attr.class.add(className);
                        }
                    }
                    else if (name === 'style') {
                        attr.style = Object.assign({}, attributes.style.toJSON(), attr.style);
                    }
                    else {
                        attr[name] = attributes.get(name);
                    }
                }
            }
            return [domObject];
        }
    }
    FormatDomObjectModifierRenderer.id = DomObjectRenderingEngine.id;

    class DomObjectRenderer extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                renderingEngines: [DomObjectRenderingEngine],
                renderers: [FormatDomObjectModifierRenderer],
            };
        }
    }
    DomObjectRenderer.dependencies = [Parser, Renderer, Xml];

    const autoCloseTag = [
        'AREA',
        'BASE',
        'BR',
        'COL',
        'EMBED',
        'HR',
        'IMG',
        'INPUT',
        'KEYGEN',
        'LINK',
        'META',
        'PARAM',
        'SOURCE',
        'TRACK',
        'WBR',
    ];
    const autoCloseRegExp = new RegExp('<((' + autoCloseTag.join('|') + ')(\\s[^>]*)?)>', 'gi');
    class DefaultHtmlTextParser extends AbstractParser {
        async parse(item) {
            const domParser = new DOMParser();
            let template = item;
            // Parse as xml, we must escape "<" & ">" in attributes.
            let inTag = false;
            let attributeQuote = '"';
            let attributeIndex = -1;
            for (let i = 0; i < template.length; i++) {
                if (inTag && (template[i] === '"' || template[i] === "'")) {
                    if (attributeIndex === -1) {
                        attributeIndex = i;
                        attributeQuote = template[i];
                    }
                    else if (attributeQuote === template[i]) {
                        const attribute = template.slice(attributeIndex, i + 1);
                        const fixed = attribute.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        template = template.slice(0, attributeIndex) + fixed + template.slice(i + 1);
                        attributeIndex = -1;
                        i += fixed.length - attribute.length;
                    }
                }
                if (attributeIndex === -1) {
                    if (template[i] === '<') {
                        inTag = true;
                    }
                    else if (template[i] === '>') {
                        inTag = false;
                    }
                }
            }
            // Auto close tags.
            template = template.replace(autoCloseRegExp, match => match[match.length - 2] === '/' ? match : match.slice(0, -1) + '/>');
            // Unescape spaces.
            template = template.replace(/&nbsp;/g, '\u00A0');
            const xmlDoc = domParser.parseFromString('<t>' + template + '</t>', 'text/xml');
            const parser = this.engine.editor.plugins.get(Parser);
            return parser.parse('dom/xml', ...xmlDoc.firstChild.childNodes);
        }
    }
    DefaultHtmlTextParser.id = 'text/html';

    class HtmlTextParsingEngine extends ParsingEngine {
    }
    HtmlTextParsingEngine.id = 'text/html';
    HtmlTextParsingEngine.defaultParser = DefaultHtmlTextParser;

    class HtmlDomParsingEngine extends XmlDomParsingEngine {
    }
    HtmlDomParsingEngine.id = 'dom/html';
    HtmlDomParsingEngine.extends = [XmlDomParsingEngine.id];

    class DefaultHtmlDomRenderer extends NodeRenderer {
        async render(node) {
            const renderer = this.engine.editor.plugins.get(Renderer);
            const objectEngine = renderer.engines['object/html'];
            const cache = await objectEngine.render([node]);
            const domNodes = [];
            for (const [, domObject] of cache.renderings) {
                await objectEngine.resolveChildren(domObject, cache.worker);
                const domNode = this._objectToDom(domObject);
                if (domNode instanceof DocumentFragment) {
                    domNodes.push(...domNode.childNodes);
                }
                else {
                    domNodes.push(domNode);
                }
            }
            return domNodes;
        }
        _objectToDom(domObject) {
            let domNode;
            if ('tag' in domObject) {
                const element = document.createElement(domObject.tag);
                const attributes = domObject.attributes;
                if (attributes) {
                    for (const name in attributes) {
                        if (name === 'style') {
                            element.setAttribute('style', Object.keys(attributes.style)
                                .map(styleName => `${styleName}: ${attributes.style[styleName]};`)
                                .join(''));
                        }
                        else if (name === 'class') {
                            const classList = attributes[name];
                            for (const className of classList) {
                                element.classList.add(className);
                            }
                        }
                        else {
                            const value = attributes[name];
                            if (typeof value === 'string') {
                                element.setAttribute(name, value);
                            }
                        }
                    }
                }
                if (domObject.children) {
                    for (const child of domObject.children) {
                        if (!(child instanceof AbstractNode)) {
                            element.appendChild(this._objectToDom(child));
                        }
                    }
                }
                // Implement attach & detach: domObject into html.
                element.addEventListener('detach', () => {
                    [...element.children].forEach(childElement => {
                        childElement.dispatchEvent(new CustomEvent('detach'));
                    });
                    if (domObject.detach) {
                        domObject.detach(element);
                    }
                });
                if (domObject.attach) {
                    domObject.attach(element);
                }
                domNode = element;
            }
            else if ('text' in domObject) {
                domNode = document.createTextNode(domObject.text);
            }
            else if ('children' in domObject) {
                domNode = document.createDocumentFragment();
                for (const child of domObject.children) {
                    if (!(child instanceof AbstractNode)) {
                        domNode.appendChild(this._objectToDom(child));
                    }
                }
            }
            else {
                domNode = document.createDocumentFragment();
                for (const domObjectNode of domObject.dom) {
                    domNode.appendChild(domObjectNode);
                }
            }
            return domNode;
        }
    }
    DefaultHtmlDomRenderer.id = 'dom/html';

    class DefaultHtmlDomModifierRenderer extends ModifierRenderer {
        /**
         * Default rendering for Format.
         *
         * @param modifier
         * @param contents
         */
        async render(modifier, contents) {
            return contents;
        }
    }
    DefaultHtmlDomModifierRenderer.id = 'dom/html';

    class HtmlDomRenderingEngine extends RenderingEngine {
    }
    HtmlDomRenderingEngine.id = 'dom/html';
    HtmlDomRenderingEngine.defaultRenderer = DefaultHtmlDomRenderer;
    HtmlDomRenderingEngine.defaultModifierRenderer = DefaultHtmlDomModifierRenderer;

    class HtmlTextRendereringEngine extends RenderingEngine {
        constructor() {
            super(...arguments);
            this.correspondingObjectRenderingId = DomObjectRenderingEngine.id;
        }
        /**
         * @override
         */
        async render(nodes, cache) {
            cache = cache || new RenderingEngineCache(this);
            const renderer = this.editor.plugins.get(Renderer);
            const objectEngine = renderer.engines[this.correspondingObjectRenderingId];
            const cacheDomObject = await objectEngine.render(nodes);
            for (const node of nodes) {
                const domObject = cacheDomObject.renderings.get(node);
                await objectEngine.resolveChildren(domObject, cacheDomObject.worker);
                const value = await this.domObjectToHtml(cache, domObject);
                cache.renderings.set(node, value);
            }
            return cache;
        }
        /**
         * Convert a domObject record into a string.
         *
         * @param domObject
         */
        async domObjectToHtml(cache, domObject) {
            let html = '';
            if ('tag' in domObject) {
                const tag = domObject.tag.toLocaleLowerCase();
                html += '<' + tag;
                if (domObject.attributes) {
                    for (const name in domObject.attributes) {
                        const value = domObject.attributes[name];
                        if (name === 'style') {
                            if (Object.keys(value).length) {
                                html += ' style="';
                                for (const key in value) {
                                    html += key + ':' + value[key] + ';';
                                }
                                html += '"';
                            }
                        }
                        else if (name === 'class') {
                            if (value.size) {
                                html +=
                                    ' class="' +
                                        [...value]
                                            .map(val => val.replace('"', '&quot;'))
                                            .join(' ') +
                                        '"';
                            }
                        }
                        else {
                            html += ' ' + name + '="' + value.replace('"', '&quot;') + '"';
                        }
                    }
                }
                if (domObject.children) {
                    html += '>';
                    for (const child of domObject.children) {
                        if (child instanceof AbstractNode) {
                            const renderings = await this.render([child], cache);
                            html += renderings[0];
                        }
                        else {
                            html += await this.domObjectToHtml(cache, child);
                        }
                    }
                    html += '</' + tag + '>';
                }
                else if (autoCloseTag.includes(domObject.tag)) {
                    html += '/>';
                }
                else {
                    html += '></' + tag + '>';
                }
            }
            else if ('text' in domObject) {
                html = domObject.text.replace('<', '&lt;').replace('>', '&gt;');
            }
            else if ('children' in domObject) {
                for (const child of domObject.children) {
                    if (child instanceof AbstractNode) {
                        const renderings = await this.render([child], cache);
                        html += renderings[0];
                    }
                    else {
                        html += await this.domObjectToHtml(cache, child);
                    }
                }
            }
            else {
                for (const domNode of domObject.dom) {
                    if (domNode instanceof Element) {
                        html += domNode.outerHTML;
                    }
                    else {
                        html = domNode.textContent.replace('<', '&lt;').replace('>', '&gt;');
                    }
                }
            }
            return html;
        }
        /**
         * Register is not available for this rendering engine.
         *
         * @override
         */
        register() {
            // TODO: Textual rendering engines are not true rendering engine. Maybe
            // outputing as text should be an option when rendering using the object
            // engines ?
            throw new Error('You can not add renderers to this engine. Please add the renderer as "' +
                this.correspondingObjectRenderingId +
                '".');
        }
    }
    HtmlTextRendereringEngine.id = 'text/html';

    class HtmlNode extends AtomicNode {
        constructor(params) {
            super();
            this.domNode = params.domNode;
        }
    }

    class HtmlDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = HtmlNode;
        }
        async render(node) {
            const domObject = { dom: [node.domNode()] };
            return domObject;
        }
    }
    HtmlDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Html extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsingEngines: [HtmlDomParsingEngine, HtmlTextParsingEngine],
                renderingEngines: [HtmlDomRenderingEngine, HtmlTextRendereringEngine],
                renderers: [HtmlDomObjectRenderer],
            };
        }
    }
    Html.dependencies = [Parser, DomObjectRenderer, Xml];

    class InlineNode extends AtomicNode {
    }

    class CharNode extends InlineNode {
        constructor(params) {
            super(params);
            if (params.char.length !== 1) {
                throw new Error('Cannot make a CharNode out of anything else than a string of length 1.');
            }
            this.char = params.char;
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        get name() {
            return this.char;
        }
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         *
         * @override
         */
        clone(params) {
            const defaults = {
                char: this.char,
                modifiers: this.modifiers.clone(),
            };
            return super.clone(Object.assign(Object.assign({}, defaults), params));
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return the length of this VNode.
         */
        get length() {
            return 1;
        }
        /**
         * Return the text content of this node.
         *
         * @override
         */
        get textContent() {
            return this.char;
        }
        /**
         * Return true if `a` has the same format properties as `b`.
         *
         * @param a
         * @param b
         */
        isSameTextNode(node) {
            if (node instanceof CharNode) {
                // Char VNodes are the same text node if they have the same
                // modifiers.
                return this.modifiers.areSameAs(node.modifiers);
            }
            else {
                // Nodes that are not valid in a text node must end the text node.
                return false;
            }
        }
    }
    CharNode.atomic = true;

    class ActionableNode extends AtomicNode {
        constructor(params) {
            super(params);
            this.actionName = params.name;
            this.label = params.label;
            this.commandId = params.commandId;
            this.commandArgs = params.commandArgs && makeVersionable(params.commandArgs);
            if (params.selected) {
                this.selected = params.selected;
            }
            if (params.enabled) {
                this.enabled = params.enabled;
            }
            if (params.visible) {
                this.visible = params.visible;
            }
            if (params.htmlTag) {
                this.htmlTag = params.htmlTag;
            }
        }
        get name() {
            return super.name + ': ' + this.actionName;
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        selected(editor) {
            return false;
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        enabled(editor) {
            return true;
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        visible(editor) {
            return true;
        }
    }

    class Inline extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                toggleFormat: {
                    handler: this.toggleFormat,
                },
                removeFormat: {
                    handler: this.removeFormat,
                },
            };
            this.loadables = {
                components: [
                    {
                        id: 'RemoveFormatButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'removeFormat',
                                label: 'Remove format',
                                commandId: 'removeFormat',
                                commandArgs: {},
                                visible: isInTextualContext,
                                selected: () => false,
                                modifiers: [new Attributes({ class: 'fa fa-eraser fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['RemoveFormatButton', ['actionables']]],
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Apply the `format` to the range.
         *
         * @param params
         */
        toggleFormat(params) {
            var _a;
            const range = params.context.range;
            const FormatClass = params.FormatClass;
            if (range.isCollapsed()) {
                const format = (_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(FormatClass);
                if (format) {
                    range.modifiers.remove(format);
                }
                else {
                    if (!range.modifiers) {
                        range.modifiers = new Modifiers();
                    }
                    range.modifiers.prepend(FormatClass);
                }
            }
            else {
                const selectedInlines = range.selectedNodes(InlineNode);
                // If every char in the range has the format `FormatClass`, remove
                // the format for all of them.
                const allHaveFormat = selectedInlines.every(inline => {
                    return !!inline.modifiers.find(FormatClass);
                });
                if (allHaveFormat) {
                    for (const inline of selectedInlines) {
                        const format = inline.modifiers.find(FormatClass);
                        // Apply the attributes of the format we're about to remove
                        // to the inline itself.
                        const attributes = inline.modifiers.get(Attributes);
                        const matchingFormatAttributes = format.modifiers.find(Attributes);
                        if (matchingFormatAttributes) {
                            for (const key of matchingFormatAttributes.keys()) {
                                attributes.set(key, matchingFormatAttributes.get(key));
                            }
                        }
                        // Remove the format.
                        inline.modifiers.remove(format);
                    }
                }
                else {
                    // If there is at least one char in the range without the format
                    // `FormatClass`, set the format for all nodes.
                    for (const inline of selectedInlines) {
                        if (!inline.modifiers.find(FormatClass)) {
                            new FormatClass().applyTo(inline);
                        }
                    }
                }
            }
        }
        isAllFormat(FormatClass, range = this.editor.selection.range) {
            var _a;
            if (range.isCollapsed()) {
                return !!((_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(FormatClass));
            }
            else {
                const selectedInlines = range.selectedNodes(InlineNode);
                for (const char of selectedInlines) {
                    if (!char.modifiers.find(FormatClass)) {
                        return false;
                    }
                }
                return !!selectedInlines.length;
            }
        }
        /**
         * Remove the formatting of the nodes in the range.
         *
         * @param params
         */
        removeFormat(params) {
            const nodes = params.context.range.selectedNodes();
            for (const node of nodes) {
                // TODO: some formats might be on the parent...
                node.modifiers.empty();
            }
        }
    }

    class CharDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = CharNode;
        }
        async render(charNode, worker) {
            return this._renderText([charNode], worker);
        }
        async renderBatch(charNodes, worker) {
            const domObjects = [];
            const domObject = this._renderText(charNodes, worker);
            for (let i = 0; i < charNodes.length; i++)
                domObjects.push(domObject);
            return domObjects;
        }
        _renderText(charNodes, worker) {
            // Create textObject.
            const texts = [];
            for (const charNode of charNodes) {
                // Same text node.
                if (charNode.char === ' ' && texts[texts.length - 1] === ' ') {
                    // Browsers don't render consecutive space chars otherwise.
                    texts.push('\u00A0');
                }
                else {
                    texts.push(charNode.char);
                }
            }
            // Render block edge spaces as non-breakable space (otherwise browsers
            // won't render them).
            const previous = charNodes[0].previousSibling();
            if (!previous || !(previous instanceof InlineNode)) {
                texts[0] = texts[0].replace(/^ /g, '\u00A0');
            }
            const next = charNodes[charNodes.length - 1].nextSibling();
            if (!next || !(next instanceof InlineNode)) {
                texts[texts.length - 1] = texts[texts.length - 1].replace(/^ /g, '\u00A0');
            }
            const textObject = { text: texts.join('') };
            worker.locate(charNodes, textObject);
            return textObject;
        }
    }
    CharDomObjectRenderer.id = DomObjectRenderingEngine.id;

    /**
     * The following is a complete list of all HTML "block-level" elements.
     *
     * Source:
     * https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
     *
     * */
    const blockTagNames = [
        'ADDRESS',
        'ARTICLE',
        'ASIDE',
        'BLOCKQUOTE',
        'DETAILS',
        'DIALOG',
        'DD',
        'DIV',
        'DL',
        'DT',
        'FIELDSET',
        'FIGCAPTION',
        'FIGURE',
        'FOOTER',
        'FORM',
        'H1',
        'H2',
        'H3',
        'H4',
        'H5',
        'H6',
        'HEADER',
        'HGROUP',
        'HR',
        'LI',
        'MAIN',
        'NAV',
        'OL',
        'P',
        'PRE',
        'SECTION',
        'TABLE',
        'UL',
        // The following elements are not in the W3C list, for some reason.
        'TR',
        'TD',
        'TBODY',
        'THEAD',
        'TH',
    ];
    const computedStyles = new WeakMap();
    /**
     * Return true if the given node is a block-level element, false otherwise.
     *
     * @param node
     */
    function isBlock(node) {
        let result;
        if (node instanceof Element) {
            const tagName = nodeName(node);
            // Every custom jw-* node will be considered as blocks.
            if (tagName.startsWith('JW-') || tagName === 'T') {
                return true;
            }
            // The node might not be in the DOM, in which case it has no CSS values.
            if (window.document !== node.ownerDocument) {
                return blockTagNames.includes(tagName);
            }
            // We won't call `getComputedStyle` more than once per node.
            let style = computedStyles.get(node);
            if (!style) {
                style = window.getComputedStyle(node);
                computedStyles.set(node, style);
            }
            if (style.display) {
                result = !style.display.includes('inline') && style.display !== 'contents';
            }
            else {
                result = blockTagNames.includes(tagName);
            }
        }
        else {
            result = false;
        }
        return result;
    }

    const spaceBeforeNewline = /([ \t])*(\n)/g;
    const spaceAfterNewline = /(\n)([ \t])*/g;
    const tabs = /\t/g;
    const newlines = /\n/g;
    const onlyTabsSpacesAndNewLines = /^[\t \n]*$/g;
    const consecutiveSpace = /  */g;
    const endWithSpace = /[ \t\n]$/g;
    const startSpace = /^ */g;
    const endSpace = /[ \u3000]*$/g;
    /**
     * Return a string with the value of a text node stripped of its formatting
     * space, applying the w3 rules for white space processing
     * TODO: decide what exactly to do with formatting spaces:
     * remove, keep, recompute?
     *
     * @see https://www.w3.org/TR/css-text-3/#white-space-processing
     * @returns {string}
     */
    function removeFormattingSpace(node) {
        var _a;
        // TODO: check the value of the `white-space` property
        const text = node.textContent;
        if ((_a = node.parentElement) === null || _a === void 0 ? void 0 : _a.closest('PRE, TEXTAREA')) {
            return text;
        }
        // (Comments refer to the w3 link provided above.)
        // Phase I: Collapsing and Transformation
        let newText = text
            // 1. All spaces and tabs immediately preceding or following a
            //    segment break are removed.
            .replace(spaceBeforeNewline, '$2')
            .replace(spaceAfterNewline, '$1')
            // 2. Segment breaks are transformed for rendering according to the
            //    segment break transformation rules.
            .replace(newlines, ' ')
            // 3. Every tab is converted to a space (U+0020).
            .replace(tabs, ' ')
            // 4. Any space immediately following another collapsible space —
            //    even one outside the boundary of the inline containing that
            //    space, provided both spaces are within the same inline
            //    formatting context—is collapsed to have zero advance width.
            //    (It is invisible, but retains its soft wrap opportunity, if
            //    any.)
            .replace(consecutiveSpace, ' ');
        // Phase II: Trimming and Positioning
        // 1. A sequence of collapsible spaces at the beginning of a line
        //    (ignoring any intervening inline box boundaries) is removed.
        // 1.2. The space at the beginning of the line is collapsed if
        //    a space is present in the previous inline siblings node
        //    see : https://www.w3.org/TR/css-text-3/#collapse
        if (_isAtSegmentBreak(node, 'start') || _followsInlineSpace(node)) {
            newText = newText.replace(startSpace, '');
        }
        // 2. If the tab size is zero, tabs are not rendered. Otherwise, each
        //    tab is rendered as a horizontal shift that lines up the start edge
        //    of the next glyph with the next tab stop. If this distance is less
        //    than 0.5ch, then the subsequent tab stop is used instead. Tab
        //    stops occur at points that are multiples of the tab size from the
        //    block’s starting content edge. The tab size is given by the
        //    tab-size property.
        // TODO
        // 3. A sequence at the end of a line (ignoring any intervening inline
        //    box boundaries) of collapsible spaces (U+0020) and/or ideographic
        //    spaces (U+3000) whose white-space value collapses spaces is
        //    removed.
        if (_isAtSegmentBreak(node, 'end')) {
            newText = newText.replace(endSpace, '');
        }
        return newText;
    }
    /**
     * Return true if the given node is immediately folowing a space inside the same inline context,
     * to see if its frontal space must be removed.
     *
     * @param {Element} node
     * @returns {boolean}
     */
    function _followsInlineSpace(node) {
        let sibling = node && node.previousSibling;
        if (isInstanceOf(node, Text) && !sibling) {
            sibling = node.parentElement.previousSibling;
        }
        if (!sibling || isBlock(sibling))
            return false;
        return !!sibling.textContent.match(endWithSpace);
    }
    /**
     * Return true if the given node is immediately preceding (`side` === 'end')
     * or following (`side` === 'start') a segment break, to see if its edge
     * space must be removed.
     * A segment break is a sort of line break, not considering automatic breaks
     * that are function of the screen size. In this context, a segment is what
     * you see when you triple click in text in the browser.
     * Eg: `<div><p>◆one◆</p>◆two◆<br>◆three◆</div>` where ◆ = segment breaks.
     *
     * @param {Element} node
     * @param {'start'|'end'} side
     * @returns {boolean}
     */
    function _isAtSegmentBreak(node, side) {
        const siblingSide = side === 'start' ? 'previousSibling' : 'nextSibling';
        const sibling = node && node[siblingSide];
        const isAgainstAnotherSegment = _isAgainstAnotherSegment(node, side);
        const isAtEdgeOfOwnSegment = _isBlockEdge(node, side);
        // In the DOM, a space before a BR is rendered but a space after a BR isn't.
        const isBeforeBR = side === 'end' && sibling && nodeName(sibling) === 'BR';
        return (isAgainstAnotherSegment && !isBeforeBR) || isAtEdgeOfOwnSegment;
    }
    /**
     * Return true if the given node is just before or just after another segment.
     * Eg: <div>abc<div>def</div></div> -> abc is before another segment (div).
     * Eg: <div><a>abc</a>     <div>def</div></div> -> abc is before another segment
     * (div).
     *
     * @param {Node} node
     * @param {'start'|'end'} side
     * @returns {boolean}
     */
    function _isAgainstAnotherSegment(node, side) {
        const siblingSide = side === 'start' ? 'previousSibling' : 'nextSibling';
        const sibling = node && node[siblingSide];
        if (sibling) {
            return sibling && _isSegment(sibling);
        }
        else {
            // Look further (eg.: `<div><a>abc</a>     <div>def</div></div>`: the
            // space should be removed).
            let ancestor = node;
            while (ancestor && !ancestor[siblingSide]) {
                ancestor = ancestor.parentNode;
            }
            let cousin = ancestor && !_isSegment(ancestor) && ancestor.nextSibling;
            while (cousin && isInstanceOf(cousin, Text)) {
                cousin = cousin.nextSibling;
            }
            return cousin && _isSegment(cousin);
        }
    }
    /**
     * Return true if the node is a segment according to W3 formatting model.
     *
     * @param node to check
     */
    function _isSegment(node) {
        if (node.nodeType !== Node.ELEMENT_NODE) {
            // Only proper elements can be a segment.
            return false;
        }
        else if (nodeName(node) === 'BR') {
            // Break (BR) tags end a segment.
            return true;
        }
        else {
            // The W3 specification has many specific cases that defines what is
            // or is not a segment. For the moment, we only handle display: block.
            return isBlock(node);
        }
    }
    /**
     * Return true if the node is at the given edge of a block.
     *
     * @param node to check
     * @param side of the block to check ('start' or 'end')
     */
    function _isBlockEdge(node, side) {
        const ancestorsUpToBlock = [];
        // Move up to the first block ancestor
        let ancestor = node;
        while (ancestor && (isInstanceOf(ancestor, Text) || !_isSegment(ancestor))) {
            ancestorsUpToBlock.push(ancestor);
            ancestor = ancestor.parentElement;
        }
        // Return true if no ancestor up to the first block ancestor has a
        // sibling on the specified side
        const siblingSide = side === 'start' ? 'previousSibling' : 'nextSibling';
        return ancestorsUpToBlock.every(ancestor => {
            let sibling = ancestor[siblingSide];
            while (sibling &&
                isInstanceOf(sibling, Text) &&
                sibling.textContent.match(onlyTabsSpacesAndNewLines)) {
                sibling = sibling[siblingSide];
            }
            return !sibling;
        });
    }

    class CharXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => isInstanceOf(item, Text);
        }
        async parse(item) {
            const nodes = [];
            const text = removeFormattingSpace(item);
            for (let i = 0; i < text.length; i++) {
                const char = text.charAt(i);
                let parsedVNode;
                if (char === '\n') {
                    parsedVNode = new this.engine.editor.configuration.defaults.Separator();
                }
                else {
                    parsedVNode = new CharNode({ char: char });
                }
                nodes.push(parsedVNode);
            }
            return nodes;
        }
    }
    CharXmlDomParser.id = XmlDomParsingEngine.id;

    class Char extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [CharXmlDomParser],
                renderers: [CharDomObjectRenderer],
            };
            this.commands = {
                insertText: {
                    handler: this.insertText,
                },
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Insert text at the current position of the selection.
         *
         * If the selection is collapsed, add `text` to the vDocument and copy the
         * formating of the previous char or the next char.
         *
         * If the selection is not collapsed, replace the text with the formating
         * that was present in the selection.
         *
         * @param params
         */
        insertText(params) {
            const range = params.context.range;
            const text = params.text;
            // Remove the contents of the range if needed.
            if (!range.isCollapsed()) {
                range.empty();
            }
            if (params.formats) {
                range.modifiers.set(...params.formats.map(format => format.clone()));
            }
            // Split the text into CHAR nodes and insert them at the range.
            const characters = text.split('');
            const charNodes = characters.map(char => {
                if (range.modifiers.length) {
                    return new CharNode({ char: char, modifiers: range.modifiers.clone() });
                }
                else {
                    return new CharNode({ char: char });
                }
            });
            charNodes.forEach(charNode => {
                range.start.before(charNode);
            });
            if (params.select && charNodes.length) {
                this.editor.selection.select(charNodes[0], charNodes[charNodes.length - 1]);
            }
            if (params.formats) {
                // Invalidate the cache.
                range.modifiers = undefined;
            }
        }
    }
    Char.dependencies = [Inline];

    class LineBreakNode extends SeparatorNode {
        get name() {
            return '↲';
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Transform the given DOM location into its VDocument counterpart.
         *
         * @override
         * @param domNode DOM node corresponding to this VNode
         * @param offset The offset of the location in the given domNode
         */
        locate(domNode, offset) {
            const location = super.locate(domNode, offset);
            // When clicking on a trailing line break, we need to target after the
            // line break. The DOM represents these as 2 <br> so this is a special
            // case.
            if (!this.nextSibling() && !domNode.nextSibling) {
                location[1] = RelativePosition.AFTER;
            }
            return location;
        }
    }

    class LineBreakXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'BR';
            };
        }
        async parse(item) {
            if (this._isInvisibleBR(item)) {
                return [];
            }
            const lineBreak = new LineBreakNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                lineBreak.modifiers.append(attributes);
            }
            return [lineBreak];
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the given <br/> node is invisible. A <br/> at the end edge
         * of a block or before another block is there only to make its parent
         * visible. Consume it since it was just parsed as its parent element node.
         * TODO: account for formatting space.
         *
         * @param node
         */
        _isInvisibleBR(node) {
            // Search for another non-block cousin in the same block parent.
            while (node &&
                !this._nextVisibleSibling(node) &&
                node.parentNode &&
                !isBlock(node.parentNode)) {
                node = node.parentNode;
            }
            const nextVisibleSibling = this._nextVisibleSibling(node);
            return !node || !nextVisibleSibling || isBlock(nextVisibleSibling);
        }
        /**
         * Return the given node's next sibling that is not pure formatting space.
         *
         * @param node
         */
        _nextVisibleSibling(node) {
            let sibling = node.nextSibling;
            while (sibling && isInstanceOf(sibling, Text) && !removeFormattingSpace(sibling).length) {
                sibling = sibling.nextSibling;
            }
            return sibling;
        }
    }
    LineBreakXmlDomParser.id = XmlDomParsingEngine.id;

    class LineBreakDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = LineBreakNode;
        }
        /**
         * Render the VNode to the given format.
         */
        async render(node, worker) {
            const br = { tag: 'BR' };
            worker.locate([node], br);
            if (!node.nextSibling()) {
                // If a LineBreakNode has no next sibling, it must be rendered
                // as two BRs in order for it to be visible.
                const br2 = { tag: 'BR' };
                const domObject = { children: [br, br2] };
                worker.locate([node], br2);
                return domObject;
            }
            return br;
        }
    }
    LineBreakDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class LineBreak extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [LineBreakXmlDomParser],
                renderers: [LineBreakDomObjectRenderer],
            };
            this.commands = {
                insertLineBreak: {
                    handler: this.insertLineBreak,
                },
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Insert a line break node at range.
         */
        async insertLineBreak(params) {
            const modifiers = params.context.range.modifiers;
            const nodeParams = {};
            if (modifiers === null || modifiers === void 0 ? void 0 : modifiers.length) {
                nodeParams.modifiers = modifiers.clone();
            }
            await params.context.execCommand('insert', {
                node: new LineBreakNode(nodeParams),
            });
        }
    }

    class HeadingNode extends TagNode {
        constructor(params) {
            super({ htmlTag: 'H' + params.level });
            this.mayContainContainers = false;
            this.level = params.level;
        }
        get name() {
            return super.name + ': ' + this.level;
        }
        clone(deepClone, params) {
            const defaults = {
                level: this.level,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
    }

    const HeadingTags = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];
    class HeadingXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && HeadingTags.includes(nodeName(item));
            };
        }
        async parse(item) {
            const heading = new HeadingNode({ level: parseInt(nodeName(item)[1], 10) });
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                heading.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            heading.append(...nodes);
            return [heading];
        }
    }
    HeadingXmlDomParser.id = XmlDomParsingEngine.id;

    class ParagraphNode extends TagNode {
        constructor() {
            super({ htmlTag: 'P' });
            this.mayContainContainers = false;
        }
    }

    class ParagraphXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'P';
            };
        }
        async parse(item) {
            const paragraph = new ParagraphNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                paragraph.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            paragraph.append(...nodes);
            return [paragraph];
        }
    }
    ParagraphXmlDomParser.id = XmlDomParsingEngine.id;

    class Paragraph extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ParagraphXmlDomParser],
            };
        }
    }

    class PreNode extends ContainerNode {
        constructor() {
            super(...arguments);
            this.mayContainContainers = false;
        }
    }

    class PreXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'PRE';
            };
        }
        async parse(item) {
            const pre = new PreNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                pre.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            pre.append(...children);
            return [pre];
        }
    }
    PreXmlDomParser.id = XmlDomParsingEngine.id;

    class PreDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = PreNode;
        }
        /**
         * Render the VNode to the given format.
         */
        async render(node) {
            const pre = {
                tag: 'PRE',
                children: await this.engine.renderChildren(node),
            };
            return pre;
        }
    }
    PreDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class PreCharDomObjectRenderer extends CharDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (item) => item instanceof CharNode && !!item.ancestor(PreNode);
        }
        async render(charNode, worker) {
            const domObject = await super.render(charNode, worker);
            this._renderInPre([domObject]);
            return domObject;
        }
        /**
         * Render the CharNode and convert unbreakable spaces into normal spaces.
         */
        async renderBatch(charNodes, worker) {
            const domObjects = await super.renderBatch(charNodes, worker);
            this._renderInPre(domObjects);
            return domObjects;
        }
        _renderInPre(domObjects) {
            const stack = [...domObjects];
            for (const domObject of stack) {
                if ('text' in domObject) {
                    domObject.text = domObject.text
                        .replace(/\u00A0/g, ' ')
                        .replace(/\u2003/g, '\u0009');
                }
                if ('children' in domObject) {
                    for (const child of domObject.children) {
                        if (!(child instanceof AbstractNode)) {
                            stack.push(child);
                        }
                    }
                }
            }
        }
    }

    class PreSeparatorDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                const DefaultSeparator = this.engine.editor.configuration.defaults.Separator;
                return item instanceof DefaultSeparator && !!item.ancestor(PreNode);
            };
        }
        /**
         * Render the VNode.
         */
        async render(node, worker) {
            const separator = (await this.super.render(node, worker));
            let rendering;
            if ('tag' in separator) {
                rendering = { text: '\n' };
            }
            else {
                rendering = { text: '\n\n' };
                worker.locate([node, node], rendering);
            }
            return rendering;
        }
    }
    PreSeparatorDomObjectRenderer.id = DomObjectRenderingEngine.id;

    function isInPre(range) {
        const startPre = !!range.start.closest(PreNode);
        if (!startPre || range.isCollapsed()) {
            return startPre;
        }
        else {
            return !!range.end.closest(PreNode);
        }
    }
    class Pre extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                applyPreStyle: {
                    handler: this.applyPreStyle,
                },
            };
            this.loadables = {
                parsers: [PreXmlDomParser],
                renderers: [PreDomObjectRenderer, PreSeparatorDomObjectRenderer, PreCharDomObjectRenderer],
                components: [
                    {
                        id: 'PreButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'pre',
                                label: 'Pre',
                                commandId: 'applyPreStyle',
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    return isInPre(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'pre' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['PreButton', ['actionables']]],
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Change the formatting of the nodes in given range to Pre.
         *
         * @param params
         */
        applyPreStyle(params) {
            for (const node of params.context.range.targetedNodes(ContainerNode)) {
                const pre = new PreNode();
                pre.modifiers = node.modifiers.clone();
                node.replaceWith(pre);
            }
        }
    }

    class BlockquoteNode extends TagNode {
        constructor() {
            super({ htmlTag: 'BLOCKQUOTE' });
        }
    }

    function isInHeading(range, level) {
        var _a, _b;
        const startIsHeading = ((_a = range.start.closest(HeadingNode)) === null || _a === void 0 ? void 0 : _a.level) === level;
        if (!startIsHeading || range.isCollapsed()) {
            return startIsHeading;
        }
        else {
            return ((_b = range.end.closest(HeadingNode)) === null || _b === void 0 ? void 0 : _b.level) === level;
        }
    }
    function headingButton(level) {
        return {
            id: 'Heading' + level + 'Button',
            async render() {
                const button = new ActionableNode({
                    name: 'heading' + level,
                    label: 'Heading' + level,
                    commandId: 'applyHeadingStyle',
                    commandArgs: { level: level },
                    visible: isInTextualContext,
                    selected: (editor) => {
                        return isInHeading(editor.selection.range, level);
                    },
                    modifiers: [new Attributes({ class: 'h' + level })],
                });
                return [button];
            },
        };
    }
    class Heading extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                applyHeadingStyle: {
                    handler: this.applyHeadingStyle,
                },
                insertParagraphBreak: {
                    selector: [
                        (node) => node instanceof HeadingNode &&
                            this.editor.mode.is(node, RuleProperty.BREAKABLE),
                    ],
                    check: (context) => {
                        const range = context.range;
                        return range.isCollapsed() && !range.start.nextSibling();
                    },
                    handler: this.insertParagraphBreak,
                },
            };
            this.loadables = {
                parsers: [HeadingXmlDomParser],
                shortcuts: [0, 1, 2, 3, 4, 5, 6].map(level => {
                    return {
                        pattern: 'CTRL+SHIFT+<Digit' + level + '>',
                        commandId: 'applyHeadingStyle',
                        commandArgs: { level: level },
                    };
                }),
                components: [
                    {
                        id: 'ParagraphButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'paragraph',
                                label: 'Paragraph',
                                commandId: 'applyHeadingStyle',
                                commandArgs: { level: 0 },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    const range = editor.selection.range;
                                    if (range.start.parent) {
                                        const startIsDefault = !!range.start.closest(ancestor => ancestor instanceof editor.configuration.defaults.Container);
                                        if (!startIsDefault || range.isCollapsed()) {
                                            return startIsDefault;
                                        }
                                        else {
                                            return !!range.end.closest(ancestor => ancestor instanceof
                                                editor.configuration.defaults.Container);
                                        }
                                    }
                                    else {
                                        return true;
                                    }
                                },
                                modifiers: [new Attributes({ class: 'p' })],
                            });
                            return [button];
                        },
                    },
                    ...[1, 2, 3, 4, 5, 6].map(headingButton),
                ],
                componentZones: [
                    ['ParagraphButton', ['actionables']],
                    ['Heading1Button', ['actionables']],
                    ['Heading2Button', ['actionables']],
                    ['Heading3Button', ['actionables']],
                    ['Heading4Button', ['actionables']],
                    ['Heading5Button', ['actionables']],
                    ['Heading6Button', ['actionables']],
                ],
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Change the formatting of the nodes in given range to Heading.
         *
         * @param params
         */
        applyHeadingStyle(params) {
            for (const node of params.context.range.targetedNodes(node => node instanceof HeadingNode ||
                node instanceof ParagraphNode ||
                node instanceof PreNode ||
                node instanceof BlockquoteNode)) {
                const heading = this._createHeadingContainer(params.level);
                heading.modifiers = node.modifiers.clone();
                node.replaceWith(heading);
            }
        }
        /**
         * Inserting a paragraph break at the end of a heading exits the heading.
         *
         * @param params
         */
        insertParagraphBreak(params) {
            const range = params.context.range;
            const heading = range.targetedNodes(HeadingNode)[0];
            const duplicate = heading.splitAt(range.start);
            const newContainer = new ParagraphNode();
            duplicate.replaceWith(newContainer);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return a heading node or a base container based on the given level.
         *
         * @param level
         */
        _createHeadingContainer(level) {
            if (level === 0) {
                return new ParagraphNode();
            }
            else {
                return new HeadingNode({ level: level });
            }
        }
    }
    Heading.dependencies = [Paragraph, Pre];

    var ListType;
    (function (ListType) {
        ListType["ORDERED"] = "ORDERED";
        ListType["UNORDERED"] = "UNORDERED";
        ListType["CHECKLIST"] = "CHECKLIST";
    })(ListType || (ListType = {}));
    class IsChecked extends Modifier {
    }
    class ListNode extends ContainerNode {
        constructor(params) {
            super(params);
            this.listType = params.listType;
        }
        // Typescript currently doesn't support using enum as keys in interfaces.
        // Source: https://github.com/microsoft/TypeScript/issues/13042
        static ORDERED(node) {
            return node && node instanceof ListNode && node.listType === ListType.ORDERED;
        }
        static UNORDERED(node) {
            return node && node instanceof ListNode && node.listType === ListType.UNORDERED;
        }
        static CHECKLIST(node) {
            return node && node instanceof ListNode && node.listType === ListType.CHECKLIST;
        }
        get name() {
            return super.name + ': ' + this.listType;
        }
        /**
         * Return true if the given node is a checked checklist or checklist item.
         *
         * @param node
         */
        static isChecked(node) {
            if (ListNode.CHECKLIST(node) && node.hasChildren()) {
                // If the node is a populated checklist, it is checked in the case
                // that every one of its children is checked.
                return node.children().every(ListNode.isChecked);
            }
            else {
                const indentedChild = node.nextSibling();
                if (ListNode.CHECKLIST(indentedChild)) {
                    // If the next list item is a checklist, this list item is its
                    // title, which is checked if said checklist's children are
                    // checked.
                    return ListNode.isChecked(indentedChild);
                }
                else {
                    return !!node.modifiers.find(IsChecked);
                }
            }
        }
        /**
         * Set the given nodes as checked.
         *
         * @param nodes
         */
        static check(...nodes) {
            for (const node of nodes) {
                if (node instanceof ListNode) {
                    // Check the list's children.
                    ListNode.check(...node.children());
                }
                else {
                    // Check the node itself otherwise.
                    node.modifiers.set(IsChecked);
                    // Propagate to next indented list if any.
                    const indentedChild = node.nextSibling();
                    if (indentedChild && indentedChild instanceof ListNode) {
                        ListNode.check(indentedChild);
                    }
                }
            }
        }
        /**
         * Set the given nodes as unchecked.
         *
         * @param nodes
         */
        static uncheck(...nodes) {
            for (const node of nodes) {
                if (node instanceof ListNode) {
                    // Uncheck the list's children.
                    ListNode.uncheck(...node.children());
                }
                else {
                    // Uncheck the node.
                    node.modifiers.remove(IsChecked);
                    // Propagate to next indented list.
                    const indentedChild = node.nextSibling();
                    if (indentedChild && indentedChild instanceof ListNode) {
                        ListNode.uncheck(indentedChild);
                    }
                }
            }
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         *
         *  @override
         */
        clone(deepClone, params) {
            const defaults = {
                listType: this.listType,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
    }

    class DividerNode extends TagNode {
        constructor() {
            super({ htmlTag: 'DIV' });
        }
    }

    class ListItemAttributes extends Attributes {
    }
    const SUB_LISTS_TAGS = ['OL', 'UL'];
    class ListItemXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'LI';
            };
        }
        /**
         * Parse a list element (LI).
         *
         * @param context
         */
        async parse(item) {
            const children = Array.from(item.childNodes);
            const nodes = [];
            let inlinesContainer;
            // Parse the list item's attributes into the node's ListItemAttributes,
            // which will be read only by ListItemDomRenderer.
            const itemModifiers = new Modifiers();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                itemModifiers.append(attributes);
            }
            const Container = this.engine.editor.configuration.defaults.Container;
            const isInline = children.map(child => this._isInlineListItem(child));
            // Wrap inline nodes if the LI only contains inline nodes or sublists.
            const allInline = isInline.every(isChildInline => isChildInline);
            const hasSubList = children.some(child => SUB_LISTS_TAGS.includes(nodeName(child)));
            // Having a sublist will trigger a split of the content of the li to
            // allow multi indentation, so in this case a wrap is required.
            const wrapInlines = allInline || hasSubList;
            for (let childIndex = 0; childIndex < children.length; childIndex++) {
                const domChild = children[childIndex];
                const parsedChild = await this.engine.parse(domChild);
                if (parsedChild.length) {
                    if (isInline[childIndex] && wrapInlines) {
                        // Contiguous inline elements in a list item should be
                        // wrapped together in a base container.
                        if (!inlinesContainer) {
                            inlinesContainer = new Container();
                            const attributes = itemModifiers.get(Attributes);
                            attributes.remove('value');
                            inlinesContainer.modifiers.append(new ListItemAttributes(attributes));
                            nodes.push(inlinesContainer);
                        }
                        inlinesContainer.append(...parsedChild);
                    }
                    else {
                        if (inlinesContainer && !SUB_LISTS_TAGS.includes(nodeName(domChild))) {
                            inlinesContainer.append(...parsedChild);
                        }
                        else {
                            inlinesContainer = null; // Close the inlinesContainer.
                            if (!isInline[childIndex]) {
                                for (const child of parsedChild) {
                                    const attributes = itemModifiers.get(Attributes);
                                    attributes.remove('value');
                                    child.modifiers.set(new ListItemAttributes(attributes));
                                }
                            }
                            nodes.push(...parsedChild);
                        }
                    }
                }
            }
            if (nodes.length === 0) {
                // A list item with children but whose parsing returned nothing
                // should be parsed as an empty base container. Eg: <li><br/></li>:
                // li has a child so it will not return [] above (and therefore be
                // ignored), but br will parse to nothing because it's a placeholder
                // br, not a real line break. We cannot ignore that li because it
                // does in fact exist so we parse it as an empty base container.
                const container = new Container();
                container.modifiers.append(new ListItemAttributes(itemModifiers.get(Attributes)));
                container.append(...nodes);
                return [container];
            }
            else if ((nodes.length === 1 &&
                // TODO: we need some sort of PhrasingContainer class for this.
                (nodes[0] instanceof ParagraphNode ||
                    nodes[0] instanceof HeadingNode ||
                    nodes[0] instanceof PreNode)) ||
                nodes.filter(node => node instanceof ListNode).length > 0) {
                // Having a sub-list is also a special case where the sub lits gets
                // its own list item rather than wrapping in a container.
                // TODO: We should not remove the P we actually parsed it as is.
                return nodes;
            }
            else {
                // A list item with different container children is represented by
                // a DividerNode.
                // TODO: we need a default FlowContainer constructor.
                const divider = new DividerNode();
                divider.modifiers.append(new ListItemAttributes(attributes));
                divider.append(...nodes);
                return [divider];
            }
        }
        /**
         * Return true if the given node is an inline list item.
         *
         * @param item
         */
        _isInlineListItem(item) {
            return item && (!isBlock(item) || nodeName(item) === 'BR');
        }
    }
    ListItemXmlDomParser.id = XmlDomParsingEngine.id;

    class ListDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ListNode;
        }
        async render(listNode, worker) {
            const list = {
                tag: listNode.listType === ListType.ORDERED ? 'OL' : 'UL',
                children: [],
            };
            if (ListNode.CHECKLIST(listNode)) {
                list.attributes = { class: new Set(['checklist']) };
            }
            const children = listNode.children();
            const domObjects = await worker.render(children);
            for (const index in children) {
                list.children.push(this._renderLi(listNode, children[index], domObjects[index], worker));
            }
            return list;
        }
        _renderLi(listNode, listItem, rendering, worker) {
            let li;
            // The node was wrapped in a "LI" but needs to be rendered as well.
            if ('tag' in rendering &&
                (rendering.tag === 'P' || rendering.tag === 'DIV') &&
                !rendering.shadowRoot) {
                // Direct ListNode's TagNode children "P" are rendered as "LI"
                // while other nodes will be rendered inside the "LI".
                li = rendering;
                li.tag = 'LI';
            }
            else if ('dom' in rendering && rendering.dom[0].nodeName === 'LI') {
                // If there is no child-specific renderer, the default renderer
                // is used. This takes the result of the Dom renderer which
                // itself wrap the children in LI.
                rendering.dom = [...rendering.dom[0].childNodes];
                li = {
                    tag: 'LI',
                    children: [rendering],
                };
                // Mark as origin. If the listItem or the listNode change, the other are invalidate.
                worker.depends(listItem, li);
                worker.depends(li, listItem);
            }
            else {
                li = {
                    tag: 'LI',
                    children: [listItem],
                };
                // Mark as dependent. If the listItem change, the listNode are invalidate. But if the
                // list change, the listItem will not invalidate.
                worker.depends(li, listItem);
            }
            worker.depends(li, listNode);
            worker.depends(listNode, li);
            // Render the node's attributes that were stored on the technical key
            // that specifies those attributes belong on the list item.
            this.engine.renderAttributes(ListItemAttributes, listItem, li, worker);
            if (listNode.listType === ListType.ORDERED) {
                // Adapt numbering to skip previous list item
                // Source: https://stackoverflow.com/a/12860083
                const previousIdentedList = listItem.previousSibling();
                if (previousIdentedList instanceof ListNode) {
                    const previousLis = previousIdentedList.previousSiblings(sibling => !(sibling instanceof ListNode));
                    const value = Math.max(previousLis.length, 1) + 1;
                    li.attributes.value = value.toString();
                }
            }
            if (listItem instanceof ListNode) {
                const style = li.attributes.style || {};
                if (!style['list-style']) {
                    style['list-style'] = 'none';
                }
                li.attributes.style = style;
                if (ListNode.CHECKLIST(listItem)) {
                    const prev = listItem.previousSibling();
                    if (prev && !ListNode.CHECKLIST(prev)) {
                        // Add dependencie to check/uncheck with previous checklist item used as title.
                        worker.depends(prev, listItem);
                        worker.depends(listItem, prev);
                    }
                }
            }
            else if (ListNode.CHECKLIST(listNode)) {
                // Add dependencie because the modifier on the listItem change the li rendering.
                worker.depends(li, listItem);
                worker.depends(listItem, listNode);
                const className = ListNode.isChecked(listItem) ? 'checked' : 'unchecked';
                if (li.attributes.class) {
                    li.attributes.class.add(className);
                }
                else {
                    li.attributes.class = new Set([className]);
                }
                // Handle click in the checkbox.
                const handlerMouseDown = (ev) => {
                    if (ev.offsetX < 0) {
                        ev.stopImmediatePropagation();
                        ev.preventDefault();
                        this.engine.editor.execWithRange(VRange.at(listItem.firstChild() || listItem), 'toggleChecked');
                    }
                };
                li.attach = (el) => {
                    el.addEventListener('mousedown', handlerMouseDown);
                };
                li.detach = (el) => {
                    el.removeEventListener('mousedown', handlerMouseDown);
                };
            }
            return li;
        }
    }
    ListDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ListItemAttributesDomObjectModifierRenderer extends ModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ListItemAttributes;
        }
        /**
         * Rendering for ListItemAttributes Modifier.
         *
         * @param format
         * @param contents
         */
        async render(format, contents) {
            return contents;
        }
    }
    ListItemAttributesDomObjectModifierRenderer.id = DomObjectRenderingEngine.id;

    const listTags = ['UL', 'OL'];
    class ListXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && listTags.includes(nodeName(item));
            };
        }
        /**
         * Parse a list (UL, OL) and its children list elements (LI).
         *
         * @param context
         */
        async parse(item) {
            // Get the list's type (ORDERED, UNORDERED, CHECKLIST).
            let type;
            if (item.className.match(/(^| )checklist( |$)/i)) {
                type = ListType.CHECKLIST;
            }
            else {
                type = nodeName(item) === 'UL' ? ListType.UNORDERED : ListType.ORDERED;
            }
            // Create the list node and parse its children and attributes.
            const list = new ListNode({ listType: type });
            const attributes = this.engine.parseAttributes(item);
            if (type === ListType.CHECKLIST) {
                attributes.classList.remove('checklist');
            }
            if (attributes.length) {
                list.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            list.append(...children);
            // In the case of a checklist, parse their checked/unchecked status and
            // ensure vertical propagation.
            if (type === ListType.CHECKLIST) {
                for (const child of children) {
                    const liAttributes = child.modifiers.find(ListItemAttributes);
                    if (liAttributes) {
                        // Parse the list item's checked status.
                        if (liAttributes.classList.has('checked')) {
                            ListNode.check(child);
                        }
                        // Remove the checklist-related classes from `liAttributes`.
                        liAttributes.classList.remove('checklist checked unchecked');
                    }
                }
            }
            return [list];
        }
    }
    ListXmlDomParser.id = XmlDomParsingEngine.id;

    class List extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                toggleList: {
                    title: 'Toggle list',
                    handler: this.toggleList,
                },
                indent: {
                    title: 'Indent list items',
                    selector: [ListNode],
                    handler: this.indent,
                },
                outdent: {
                    title: 'Outdent list items',
                    selector: [ListNode],
                    handler: this.outdent,
                },
                insertParagraphBreak: {
                    selector: [ListNode, List.isListItem],
                    check: (context) => {
                        const [list, listItem] = context.selector;
                        return !listItem.hasChildren() && listItem === list.lastChild();
                    },
                    handler: this.insertParagraphBreak,
                },
                toggleChecked: {
                    title: 'Check or uncheck list items',
                    selector: [ListNode.CHECKLIST],
                    handler: this.toggleChecked,
                },
            };
            this.commandHooks = {
                // TODO: replace this with `onSiblingsChange` when we introduce events.
                deleteBackward: this.rejoin.bind(this),
                deleteForward: this.rejoin.bind(this),
            };
            this.loadables = {
                parsers: [ListXmlDomParser, ListItemXmlDomParser],
                renderers: [ListDomObjectRenderer, ListItemAttributesDomObjectModifierRenderer],
                shortcuts: [
                    {
                        pattern: 'CTRL+SHIFT+<Digit7>',
                        commandId: 'toggleList',
                        commandArgs: { type: ListType.ORDERED },
                    },
                    {
                        pattern: 'CTRL+SHIFT+<Digit8>',
                        commandId: 'toggleList',
                        commandArgs: { type: ListType.UNORDERED },
                    },
                    {
                        pattern: 'CTRL+SHIFT+<Digit9>',
                        commandId: 'toggleList',
                        commandArgs: { type: ListType.CHECKLIST },
                    },
                    {
                        pattern: 'CTRL+<Space>',
                        commandId: 'toggleChecked',
                    },
                    {
                        pattern: 'Backspace',
                        selector: [List.isListItem],
                        check: (context) => {
                            const range = context.range;
                            const [listItem] = context.selector;
                            return (range.isCollapsed() &&
                                (!listItem.hasChildren() ||
                                    listItem.firstLeaf() === range.start.nextSibling()));
                        },
                        commandId: 'outdent',
                    },
                ],
                components: [
                    {
                        id: 'OrderedListButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'ordered',
                                label: 'Toggle ordered list',
                                commandId: 'toggleList',
                                commandArgs: { type: ListType.ORDERED },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    const range = editor.selection.range;
                                    const startIsList = List.isInList(ListType.ORDERED, range.start);
                                    if (!startIsList || range.isCollapsed()) {
                                        return startIsList;
                                    }
                                    else {
                                        return List.isInList(ListType.ORDERED, range.end);
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-list-ol fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'UnorderedListButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'unordered',
                                label: 'Toggle unordered list',
                                commandId: 'toggleList',
                                commandArgs: { type: ListType.UNORDERED },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    const range = editor.selection.range;
                                    const startIsList = List.isInList(ListType.UNORDERED, range.start);
                                    if (!startIsList || range.isCollapsed()) {
                                        return startIsList;
                                    }
                                    else {
                                        return List.isInList(ListType.UNORDERED, range.end);
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-list-ul fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'ChecklistButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'checkbox',
                                label: 'Toggle checkbox list',
                                commandId: 'toggleList',
                                commandArgs: { type: ListType.CHECKLIST },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    const range = editor.selection.range;
                                    const startIsList = List.isInList(ListType.CHECKLIST, range.start);
                                    if (!startIsList || range.isCollapsed()) {
                                        return startIsList;
                                    }
                                    else {
                                        return List.isInList(ListType.CHECKLIST, range.end);
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa far fa-check-square fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [
                    ['OrderedListButton', ['actionables']],
                    ['UnorderedListButton', ['actionables']],
                    ['ChecklistButton', ['actionables']],
                ],
            };
        }
        static isListItem(node) {
            return node.parent && node.parent instanceof ListNode;
        }
        static isInList(type, node) {
            var _a;
            return ((_a = node === null || node === void 0 ? void 0 : node.ancestor(ListNode)) === null || _a === void 0 ? void 0 : _a.listType) === type;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Insert/remove a list at range.
         *
         * @param params
         */
        toggleList(params) {
            const type = params.type;
            const bounds = VRange.clone(params.context.range);
            const range = new VRange(this.editor, bounds);
            // Extend the range to cover the entirety of its containers.
            if (range.startContainer.hasChildren()) {
                range.setStart(range.startContainer.firstChild());
            }
            if (range.endContainer.hasChildren()) {
                range.setEnd(range.endContainer.lastChild());
            }
            // If all targeted nodes are within a list of given type then unlist
            // them. Otherwise, convert them to the given list type.
            const targetedNodes = range.targetedNodes();
            const ancestors = targetedNodes.map(node => node.closest(ListNode));
            const targetedLists = ancestors.filter(list => !!list);
            if (targetedLists.length === targetedNodes.length &&
                targetedLists.every(list => list.listType === type)) {
                // Unlist the targeted nodes from all its list ancestors.
                while (range.start.ancestor(ListNode)) {
                    const nodesToUnlist = range.split(ListNode);
                    for (const list of nodesToUnlist) {
                        for (const child of list.childVNodes) {
                            // TODO: automatically invalidate `li-attributes`.
                            child.modifiers.remove(ListItemAttributes);
                        }
                        list.unwrap();
                    }
                }
            }
            else if (targetedLists.length === targetedNodes.length) {
                // If all nodes are in lists, convert the targeted list
                // nodes to the given list type.
                const lists = distinct(targetedLists);
                const listsToConvert = lists.filter(l => l.listType !== type);
                for (const list of listsToConvert) {
                    let newList = new ListNode({ listType: type });
                    list.replaceWith(newList);
                    // If the new list is after or before a list of the same
                    // type, merge them. Example:
                    // <ol><li>a</li></ol><ol><li>b</li></ol>
                    // => <ol><li>a</li><li>b</li></ol>).
                    const previousSibling = newList.previousSibling();
                    if (previousSibling && ListNode[type](previousSibling)) {
                        newList.mergeWith(previousSibling);
                        newList = previousSibling;
                    }
                    const nextSibling = newList.nextSibling();
                    if (nextSibling && ListNode[type](nextSibling)) {
                        nextSibling.mergeWith(newList);
                    }
                }
            }
            else {
                // If only some nodes are in lists and other aren't then only
                // wrap the ones that were not already in a list into a list of
                // the given type.
                let newList = new ListNode({ listType: type });
                const nodesToConvert = range.split(ListNode);
                for (const node of nodesToConvert) {
                    // Merge top-level lists instead of nesting them.
                    if (node instanceof ListNode) {
                        node.mergeWith(newList);
                    }
                    else {
                        node.wrap(newList);
                    }
                }
                // If the new list is after or before a list of the same type,
                // merge them. Example:
                // <ol><li>a</li></ol><ol><li>b</li></ol>
                // => <ol><li>a</li><li>b</li></ol>).
                const previousSibling = newList.previousSibling();
                if (previousSibling && ListNode[type](previousSibling)) {
                    newList.mergeWith(previousSibling);
                    newList = previousSibling;
                }
                const nextSibling = newList.nextSibling();
                if (nextSibling && ListNode[type](nextSibling)) {
                    nextSibling.mergeWith(newList);
                }
            }
            range.remove();
        }
        /**
         * Indent one or more list items.
         *
         * @param params
         */
        indent(params) {
            const range = params.context.range;
            const items = range.targetedNodes(node => node.parent instanceof ListNode);
            // Do not indent items of a targeted nested list, since they
            // will automatically be indented with their list ancestor.
            const itemsToIndent = items.filter(item => {
                return !items.includes(item.ancestor(ListNode));
            });
            for (const item of itemsToIndent) {
                const prev = item.previousSibling();
                const next = item.nextSibling();
                // Indent the item by putting it into a pre-existing list sibling.
                if (prev && prev instanceof ListNode) {
                    prev.append(item);
                    // The two list siblings might be rejoinable now that the lower
                    // level item breaking them into two different lists is no more.
                    const listType = prev.listType;
                    if (ListNode[listType](next) && !itemsToIndent.includes(next)) {
                        next.mergeWith(prev);
                    }
                }
                else if (next instanceof ListNode && !itemsToIndent.includes(next)) {
                    next.prepend(item);
                }
                else {
                    // If no other candidate exists then wrap it in a new ListNode.
                    const listType = item.ancestor(ListNode).listType;
                    item.wrap(new ListNode({ listType: listType }));
                }
            }
        }
        /**
         * Outdent one or more list items.
         *
         * @param params
         */
        outdent(params) {
            const range = params.context.range;
            const items = range.targetedNodes(node => node.parent instanceof ListNode);
            // Do not outdent items of a targeted nested list, since they
            // will automatically be outdented with their list ancestor.
            const itemsToOutdent = items.filter(item => {
                return !items.includes(item.ancestor(ListNode));
            });
            for (const item of itemsToOutdent) {
                const list = item.ancestor(ListNode);
                const previousSibling = item.previousSibling();
                const nextSibling = item.nextSibling();
                if (this.editor.mode.is(list, RuleProperty.BREAKABLE)) {
                    if (previousSibling && nextSibling) {
                        const splitList = item.parent.splitAt(item);
                        splitList.before(item);
                    }
                    else if (previousSibling) {
                        list.after(item);
                    }
                    else if (nextSibling) {
                        list.before(item);
                    }
                    else {
                        for (const child of list.childVNodes) {
                            // TODO: automatically invalidate `li-attributes`.
                            child.modifiers.remove(ListItemAttributes);
                        }
                        list.unwrap();
                    }
                }
            }
        }
        /**
         * Insert a paragraph break in the last empty item of a list by unwrapping
         * the list item from the list, thus becoming the new paragraph.
         *
         * @param params
         */
        insertParagraphBreak(params) {
            const range = params.context.range;
            const listItem = range.startContainer;
            const listNode = listItem.ancestor(ListNode);
            if (listNode.children().length === 1) {
                listNode.unwrap();
            }
            else {
                listNode.after(listItem);
            }
        }
        /**
         * Rejoin same type lists that are now direct siblings after the remove.
         *
         * @param params
         */
        rejoin(params) {
            const range = params.context.range;
            const listAncestors = range.start.ancestors(ListNode);
            if (listAncestors.length) {
                let list = listAncestors[listAncestors.length - 1];
                let nextSibling = list && list.nextSibling();
                while (list &&
                    nextSibling &&
                    list instanceof ListNode &&
                    ListNode[list.listType](nextSibling)) {
                    const nextList = list.lastChild();
                    const nextListSibling = nextSibling.firstChild();
                    nextSibling.mergeWith(list);
                    list = nextList;
                    nextSibling = nextListSibling;
                }
            }
        }
        /**
         * Check or uncheck the list items at range.
         *
         * @param params
         */
        toggleChecked(params) {
            const range = params.context.range;
            const items = range.targetedNodes(node => ListNode.CHECKLIST(node.parent));
            const areAllChecked = items.every(ListNode.isChecked);
            for (const item of items) {
                if (areAllChecked) {
                    ListNode.uncheck(item);
                }
                else {
                    ListNode.check(item);
                }
            }
        }
    }

    class Indent extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                indent: {
                    title: 'Indent chars',
                    handler: this.indent,
                },
                outdent: {
                    title: 'Outdent chars',
                    handler: this.outdent,
                },
            };
            this.loadables = {
                shortcuts: [
                    {
                        pattern: 'TAB',
                        commandId: 'indent',
                    },
                    {
                        pattern: 'SHIFT+TAB',
                        commandId: 'outdent',
                    },
                ],
                components: [
                    {
                        id: 'IndentButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'indent',
                                label: 'Indent',
                                commandId: 'indent',
                                visible: isInTextualContext,
                                modifiers: [new Attributes({ class: 'fa fa-indent fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OutdentButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'outdent',
                                label: 'Outdent',
                                commandId: 'outdent',
                                visible: isInTextualContext,
                                modifiers: [new Attributes({ class: 'fa fa-outdent fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [
                    ['IndentButton', ['actionables']],
                    ['OutdentButton', ['actionables']],
                ],
            };
            this.tab = '\u2003'; // `&emsp;` ("em space")
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Indent text or lines.
         *
         * - If there is more than one line selected in range, indent each lines.
         * - Otherwise, insert 4 spaces.
         */
        async indent(params) {
            const range = params.context.range;
            const segmentBreaks = range.traversedNodes(this._isSegmentBreak);
            // Only indent when there is at leat two lines selected, that is when
            // at least one segment break could be identified in the selection.
            if (range.isCollapsed() || !segmentBreaks.length) {
                await params.context.execCommand('insertText', {
                    text: this.tab,
                    context: Object.assign(Object.assign({}, params.context), { range }),
                });
            }
            else {
                // The first line of the selection is neither fully selected nor
                // traversed so its segment break was not in `range.traversedNodes`.
                const nextSegmentBreak = range.start.previous(this._isSegmentBreak);
                if (nextSegmentBreak) {
                    segmentBreaks.unshift(nextSegmentBreak);
                }
                for (const segmentBreak of segmentBreaks) {
                    // Insert 4 spaces at the start of next segment.
                    const [node, position] = this._nextSegmentStart(segmentBreak);
                    await this.editor.execWithRange(VRange.at(node, position), 'insertText', {
                        text: this.tab,
                    });
                }
            }
        }
        /**
         * Outdent lines.
         *
         * If there is more than one line selected, for each of the lines, remove up
         * to 4 spaces in the beggining of the line.
         */
        outdent(params) {
            const range = params.context.range;
            const segmentBreaks = range.traversedNodes(this._isSegmentBreak);
            // The first line of the selection is neither fully selected nor
            // traversed so its segment break was not in `range.traversedNodes`.
            const previousSegmentBreak = range.start.previous(this._isSegmentBreak);
            if (previousSegmentBreak) {
                segmentBreaks.unshift(previousSegmentBreak);
            }
            // Only outdent when there is at leat two lines selected, that is when
            // at least one segment break could be identified in the selection.
            if (segmentBreaks.length) {
                segmentBreaks.forEach(segmentBreak => {
                    for (let i = 0; i < this.tab.length; i++) {
                        const space = this._nextIndentationSpace(segmentBreak);
                        if (space) {
                            space.remove();
                        }
                    }
                });
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the given VNode can be considered to be a segment break.
         *
         * @param params
         */
        _isSegmentBreak(node) {
            return node instanceof ContainerNode || node instanceof LineBreakNode;
        }
        /**
         * Return the next segment start point after the given segment break.
         *
         * @param segmentBreak
         */
        _nextSegmentStart(segmentBreak) {
            let reference = segmentBreak;
            let position = RelativePosition.BEFORE;
            if (segmentBreak instanceof AtomicNode) {
                reference = segmentBreak.nextSibling();
            }
            else if (segmentBreak.hasChildren()) {
                reference = segmentBreak.firstChild();
            }
            else {
                position = RelativePosition.INSIDE;
            }
            return [reference, position];
        }
        /**
         * Return true if the given VNode is a CharNode containing a space.
         *
         * @param node
         */
        _isSpace(node) {
            return node instanceof CharNode && /^\s$/g.test(node.char);
        }
        /**
         * Return true if the given VNode can be considered to be a segment break.
         *
         * @param segmentBreak
         */
        _nextIndentationSpace(segmentBreak) {
            let space;
            if (segmentBreak instanceof AtomicNode) {
                space = segmentBreak.nextSibling();
            }
            else {
                space = segmentBreak.firstChild();
            }
            return space && space.test(this._isSpace) && space;
        }
    }
    Indent.dependencies = [Char, LineBreak];

    class FormatXmlDomParser extends AbstractParser {
        /**
         * Parse a span node.
         *
         * @param nodes
         */
        applyFormat(format, nodes) {
            for (const node of nodes) {
                format.clone().applyTo(node);
            }
        }
    }
    FormatXmlDomParser.id = XmlDomParsingEngine.id;

    class SpanFormat extends Format {
        constructor(htmlTag = 'SPAN') {
            super(htmlTag);
        }
    }

    class SpanXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && (nodeName(item) === 'SPAN' || nodeName(item) === 'FONT');
            };
        }
        /**
         * Parse a span node.
         *
         * @param item
         */
        async parse(item) {
            const span = new SpanFormat(nodeName(item));
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                span.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            // Handle empty spans.
            if (!children.length) {
                children.push(new InlineNode());
            }
            this.applyFormat(span, children);
            return children;
        }
    }

    class Span extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [SpanXmlDomParser],
            };
        }
    }
    Span.dependencies = [Inline];

    class BoldFormat extends Format {
        constructor(htmlTag = 'B') {
            super(htmlTag);
        }
    }

    class BoldXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && (nodeName(item) === 'B' || nodeName(item) === 'STRONG');
            };
        }
        /**
         * Parse a bold node.
         *
         * @param item
         */
        async parse(item) {
            const bold = new BoldFormat(nodeName(item));
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                bold.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(bold, children);
            return children;
        }
    }

    class Bold extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [BoldXmlDomParser],
                shortcuts: [
                    {
                        pattern: 'CTRL+B',
                        commandId: 'toggleFormat',
                        commandArgs: { FormatClass: BoldFormat },
                    },
                ],
                components: [
                    {
                        id: 'BoldButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'bold',
                                label: 'Toggle bold',
                                commandId: 'toggleFormat',
                                commandArgs: { FormatClass: BoldFormat },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    var _a, _b, _c;
                                    const range = editor.selection.range;
                                    if (range.isCollapsed()) {
                                        return !!((_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(BoldFormat));
                                    }
                                    else {
                                        const startIsFormated = !!((_b = range.start
                                            .nextSibling(InlineNode)) === null || _b === void 0 ? void 0 : _b.modifiers.find(BoldFormat));
                                        if (!startIsFormated || range.isCollapsed()) {
                                            return startIsFormated;
                                        }
                                        else {
                                            return !!((_c = range.end
                                                .previousSibling(InlineNode)) === null || _c === void 0 ? void 0 : _c.modifiers.find(BoldFormat));
                                        }
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-bold fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['BoldButton', ['actionables']]],
            };
        }
    }
    Bold.dependencies = [Inline];

    class ItalicFormat extends Format {
        constructor(htmlTag = 'I') {
            super(htmlTag);
        }
    }

    class ItalicXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && (nodeName(item) === 'I' || nodeName(item) === 'EM');
            };
        }
        /**
         * Parse an italic node.
         *
         * @param item
         */
        async parse(item) {
            const italic = new ItalicFormat(nodeName(item));
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                italic.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(italic, children);
            return children;
        }
    }

    class Italic extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ItalicXmlDomParser],
                shortcuts: [
                    {
                        pattern: 'CTRL+I',
                        commandId: 'toggleFormat',
                        commandArgs: { FormatClass: ItalicFormat },
                    },
                ],
                components: [
                    {
                        id: 'ItalicButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'italic',
                                label: 'Toggle italic',
                                commandId: 'toggleFormat',
                                commandArgs: { FormatClass: ItalicFormat },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    var _a, _b, _c;
                                    const range = editor.selection.range;
                                    if (range.isCollapsed()) {
                                        return !!((_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(ItalicFormat));
                                    }
                                    else {
                                        const startIsFormated = !!((_b = range.start
                                            .nextSibling(InlineNode)) === null || _b === void 0 ? void 0 : _b.modifiers.find(ItalicFormat));
                                        if (!startIsFormated || range.isCollapsed()) {
                                            return startIsFormated;
                                        }
                                        else {
                                            return !!((_c = range.end
                                                .previousSibling(InlineNode)) === null || _c === void 0 ? void 0 : _c.modifiers.find(ItalicFormat));
                                        }
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-italic fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['ItalicButton', ['actionables']]],
            };
        }
    }
    Italic.dependencies = [Inline];

    class UnderlineFormat extends Format {
        constructor() {
            super(...arguments);
            this.htmlTag = 'U';
        }
    }

    class UnderlineXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'U';
            };
        }
        /**
         * Parse an underline node.
         *
         * @param item
         */
        async parse(item) {
            const underline = new UnderlineFormat();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                underline.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(underline, children);
            return children;
        }
    }

    class Underline extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [UnderlineXmlDomParser],
                shortcuts: [
                    {
                        pattern: 'CTRL+U',
                        commandId: 'toggleFormat',
                        commandArgs: { FormatClass: UnderlineFormat },
                    },
                ],
                components: [
                    {
                        id: 'UnderlineButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'underline',
                                label: 'Toggle underline',
                                commandId: 'toggleFormat',
                                commandArgs: { FormatClass: UnderlineFormat },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    var _a, _b, _c;
                                    const range = editor.selection.range;
                                    if (range.isCollapsed()) {
                                        return !!((_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(UnderlineFormat));
                                    }
                                    else {
                                        const startIsFormated = !!((_b = range.start
                                            .nextSibling(InlineNode)) === null || _b === void 0 ? void 0 : _b.modifiers.find(UnderlineFormat));
                                        if (!startIsFormated || range.isCollapsed()) {
                                            return startIsFormated;
                                        }
                                        else {
                                            return !!((_c = range.end
                                                .previousSibling(InlineNode)) === null || _c === void 0 ? void 0 : _c.modifiers.find(UnderlineFormat));
                                        }
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-underline fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['UnderlineButton', ['actionables']]],
            };
        }
    }
    Underline.dependencies = [Inline];

    class LinkFormat extends Format {
        constructor(url = '#', target = '') {
            super('A');
            this.preserveAfterNode = false;
            this.preserveAfterParagraphBreak = false;
            this.preserveAfterLineBreak = true;
            this.level = ModifierLevel.HIGH;
            this.url = url;
            if (target) {
                this.target = target;
            }
        }
        // TODO: Attributes on Link should reactively read the values set on the
        // node itself rather than having to manually synchronize them.
        get url() {
            var _a;
            return (_a = this.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.get('href');
        }
        set url(url) {
            this.modifiers.get(Attributes).set('href', url);
        }
        get target() {
            var _a;
            return ((_a = this.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.get('target')) || '';
        }
        set target(target) {
            if (target.length) {
                this.modifiers.get(Attributes).set('target', target);
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        clone() {
            const clone = super.clone();
            clone.url = this.url;
            return clone;
        }
    }

    class LinkXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'A';
            };
        }
        async parse(item) {
            const link = new LinkFormat(item.getAttribute('href'));
            // TODO: Link should not have an `Attributes` modifier outside of XML.
            // In XML context we need to conserve the order of attributes.
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                link.modifiers.replace(Attributes, attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(link, children);
            return children;
        }
    }

    class Layout extends JWPlugin {
        constructor() {
            super(...arguments);
            this.engines = {};
            this.loaders = {
                layoutEngines: this.loadEngines,
                components: this.loadComponents,
                componentZones: this.loadComponentsZones,
            };
            this.commands = {
                show: {
                    title: 'Show a layout component',
                    handler: this.show.bind(this),
                },
                hide: {
                    title: 'Hide a layout component',
                    handler: this.hide.bind(this),
                },
            };
        }
        async start() {
            this.loadComponents(this.configuration.components || []);
            this.loadComponentsZones(this.configuration.componentZones || []);
        }
        /**
         * Prepend a Component in a zone.
         *
         * @param componentId
         * @param zoneId
         * @param props
         */
        async prepend(componentId, zoneId = 'default', props) {
            const engines = Object.values(this.engines);
            await Promise.all(engines.map(engine => engine.prepend(componentId, zoneId, props)));
        }
        /**
         * Append a Component in a zone.
         *
         * @param componentId
         * @param zoneId
         */
        async append(componentId, zoneId = 'default', props) {
            const engines = Object.values(this.engines);
            await Promise.all(engines.map(engine => engine.append(componentId, zoneId, props)));
        }
        /**
         * Clear a zone content.
         *
         * @param zoneId
         */
        async clear(zoneId) {
            const engines = Object.values(this.engines);
            await Promise.all(engines.map(engine => engine.clear(zoneId)));
        }
        /**
         * Remove a component (instance or clonse) from the zone.
         *
         * @param componentId
         * @param zoneId specifying a zone if it is necessary to remove the
         *      component from this zone only
         */
        async remove(componentId, zoneId) {
            const promises = [];
            for (const layoutEngine of Object.values(this.engines)) {
                promises.push(layoutEngine.remove(componentId, zoneId));
            }
            await Promise.all(promises);
        }
        /**
         * Show component (instance or clonse) inside the zone.
         *
         * @param params
         */
        async show(params) {
            const promises = [];
            for (const layoutEngine of Object.values(this.engines)) {
                promises.push(layoutEngine.show(params.componentId));
            }
            await Promise.all(promises);
        }
        /**
         * Hide component (instance or clonse) inside the zone.
         *
         * @param params
         */
        async hide(params) {
            const promises = [];
            for (const layoutEngine of Object.values(this.engines)) {
                promises.push(layoutEngine.hide(params.componentId));
            }
            await Promise.all(promises);
        }
        /**
         * Load layout engines.
         *
         * @param layoutEngines
         */
        loadEngines(layoutEngines) {
            for (const EngineClass of layoutEngines) {
                const engine = new EngineClass(this.editor);
                if (this.engines[engine.constructor.id]) {
                    throw new Error(`Rendering engine ${EngineClass.name} already registered.`);
                }
                this.engines[engine.constructor.id] = engine;
            }
        }
        /**
         * Load components into all layout engines.
         *
         * @param Components
         */
        loadComponents(Components) {
            for (const Component of Components) {
                for (const layoutEngine of Object.values(this.engines)) {
                    layoutEngine.loadComponent(Component);
                }
            }
        }
        /**
         * Load component zones into all layout engines.
         *
         * @param componentsZones
         */
        loadComponentsZones(componentsZones) {
            const zones = {};
            for (const [id, zone] of componentsZones) {
                zones[id] = zone;
            }
            for (const layoutEngine of Object.values(this.engines)) {
                layoutEngine.loadComponentZones(zones);
            }
        }
    }

    var linkForm = {"templates":{"div":{"_attributes":{"t-name":"link"},"h2":{"_text":"Insert a link"},"table":{"_attributes":{"class":"form-table"},"tr":[{"td":[{"label":{"_attributes":{"for":"linkUrl"},"_text":"URL "}},{"input":{"_attributes":{"type":"text","id":"linkUrl","name":"url","t-model":"state.url"}}}]},{"_attributes":{"t-if":"state.replaceSelection"},"td":[{"label":{"_attributes":{"for":"linkLabel"},"_text":"Label "}},{"input":{"_attributes":{"type":"text","id":"linkLabel","name":"label","t-model":"state.label"}}}]}]},"br":{},"button":[{"_attributes":{"name":"save","t-on-click":"saveLink()"},"_text":"Save"},{"_attributes":{"name":"save","t-on-click":"cancel()"},"_text":"Cancel"}]}}};

    class OwlNode extends AtomicNode {
        constructor(params) {
            super(params);
            markNotVersionable(params);
            this.params = params;
        }
        get name() {
            return super.name + ': ' + this.params.Component.name;
        }
    }

    class OwlComponent extends owl.Component {
        constructor() {
            super(...arguments);
            this._storageKeyPrefix = 'OwlUI' + this.constructor.name + ':';
            // State items which names are listed in the localStorage property will be
            // read from the localStorage during the willStart of the component, and
            // wrote back to the localStorage whenever the state changes.
            this.localStorage = [];
        }
        /**
         * Owl hook called exactly once before the initial rendering.
         */
        willStart() {
            if (this.state) {
                this._importStateFromStorage(localStorage, this.localStorage);
                this.state = owl.useState(this.state);
            }
            return super.willStart();
        }
        /**
         * Called by the Owl state observer every time the state changes.
         *
         * @param force see Owl Component
         */
        render(force = false) {
            if (this.state) {
                this._exportStateToStorage(localStorage, this.localStorage);
            }
            return super.render(force);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Read the given storable state items from the given `storage` and write
         * the items as the key of the `state` property.
         *
         * @param storage from which to read the state items
         * @param storableItems names of the state items to read from storage
         */
        _importStateFromStorage(storage, storableItems) {
            storableItems.forEach(itemName => {
                const storageKey = this._storageKeyPrefix + itemName;
                const value = storage.getItem(storageKey);
                // The value of items that were not yet set in storage is null.
                if (value !== null) {
                    // Otherwise, the value was stored as a string in the storage.
                    // Convert it to the type of the default value for the state.
                    try {
                        this.state[itemName] = JSON.parse(value);
                    }
                    catch (e) {
                        // Stored item is not parseable. Keep the default value.
                        console.warn(`Storage: Ignoring state.${itemName} stored value.\n` +
                            `${e.name}: ${e.message}\n` +
                            `Stored value: ${value}`);
                    }
                }
            });
        }
        /**
         * For every key in the property `state`, write it back to `storage`
         * Write the given storable state items to the given storage.
         *
         * @param storage to write the state items to
         * @param storableItems names of the state items to write to storage
         */
        _exportStateToStorage(storage, storableItems) {
            storableItems.forEach(itemName => {
                const storageKey = this._storageKeyPrefix + itemName;
                // Storage require items to be stored as strings.
                try {
                    const serializedValue = JSON.stringify(this.state[itemName]);
                    storage.setItem(storageKey, serializedValue);
                }
                catch (e) {
                    // State item is not serializable. Skip storing it.
                    console.warn(`Storage: Unserializable state.${itemName} value.\n` +
                        `${e.name}: ${e.message}`);
                }
            });
        }
    }

    class LinkComponent extends OwlComponent {
        constructor() {
            var _a, _b, _c, _d;
            super(...arguments);
            this.state = owl.useState({
                replaceSelection: !!((_a = this.props) === null || _a === void 0 ? void 0 : _a.replaceSelection),
                url: ((_b = this.props) === null || _b === void 0 ? void 0 : _b.url) || '',
                label: (((_c = this.state) === null || _c === void 0 ? void 0 : _c.replaceSelection) && ((_d = this.props) === null || _d === void 0 ? void 0 : _d.label)) || '',
            });
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        async saveLink() {
            await this.env.editor.execCommand(async (context) => {
                const params = {
                    url: this.state.url,
                    label: this.state.label,
                };
                await context.execCommand('link', params);
                this.env.editor.plugins.get(Layout).remove('link');
            });
            this.destroy();
        }
        async cancel() {
            await this.env.editor.execCommand(async () => {
                this.env.editor.plugins.get(Layout).remove('link');
            });
            this.destroy();
        }
    }
    LinkComponent.components = {};
    LinkComponent.template = 'link';

    class DefaultMailObjectRenderer extends DefaultDomObjectRenderer {
    }
    DefaultMailObjectRenderer.id = 'object/mail';

    class MetadataNode extends MarkerNode {
        constructor(params) {
            super(params);
            this.contents = '';
            this.htmlTag = params.htmlTag;
        }
        get name() {
            return this.constructor.name + ': ' + this.htmlTag;
        }
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(params) {
            const defaults = {
                htmlTag: this.htmlTag,
            };
            return super.clone(Object.assign(Object.assign({}, defaults), params));
        }
    }
    MetadataNode.atomic = true;

    // See https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Content_categories#Metadata_content
    const METADATA_NODENAMES = [
        'BASE',
        'COMMAND',
        'LINK',
        'META',
        'NOSCRIPT',
        'SCRIPT',
        'STYLE',
        'TITLE',
    ];
    class MetadataXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && METADATA_NODENAMES.includes(nodeName(item));
            };
        }
        async parse(item) {
            const technical = new MetadataNode({ htmlTag: nodeName(item) });
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                technical.modifiers.append(attributes);
            }
            technical.contents = item.innerHTML;
            return [technical];
        }
    }
    MetadataXmlDomParser.id = XmlDomParsingEngine.id;

    class MetadataDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = MetadataNode;
        }
        async render(node) {
            const meta = {
                tag: node.htmlTag,
                children: [{ text: node.contents }],
            };
            return meta;
        }
    }
    MetadataDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Metadata extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [MetadataXmlDomParser],
                renderers: [MetadataDomObjectRenderer],
            };
        }
    }

    class Stylesheet extends JWPlugin {
        constructor() {
            super(...arguments);
            this.rulesCache = new Map();
        }
        /**
         * Returns the css rules which applies on an node.
         *
         * @param {DOMElement} Node
         * @returns {Object} css property name -> css property value
         */
        getStyleFromCSSRules(node) {
            const el = isInstanceOf(node, Element) ? node : node.parentElement;
            return this.getFilteredStyleFromCSSRules(selector => el.matches(selector), node.ownerDocument);
        }
        getFilteredStyleFromCSSRules(filter, doc = document) {
            const ruleList = [];
            for (const rule of this._getMatchedCSSRules(doc)) {
                if (filter(rule.selector)) {
                    ruleList.push(rule);
                }
            }
            return this._rulesToStyle(ruleList);
        }
        _rulesToStyle(ruleList) {
            ruleList.sort((a, b) => {
                return this._specificity(a.selector) - this._specificity(b.selector);
            });
            const style = {};
            for (const rule of ruleList) {
                for (const prop in rule.style) {
                    const value = rule.style[prop];
                    if (prop.indexOf('-webkit') === -1 &&
                        (!style[prop] ||
                            style[prop].indexOf('important') === -1 ||
                            value.indexOf('important') !== -1)) {
                        style[prop] = value;
                    }
                }
            }
            for (const prop in style) {
                const value = style[prop];
                if (value.indexOf('important') !== -1) {
                    style[prop] = value.slice(0, value.length - 11);
                }
            }
            // The css generates all the attributes separately and not in simplified form.
            // In order to have a better compatibility (outlook for example) we simplify the css tags.
            // e.g. border-left-style: none; border-bottom-s .... will be simplified in border-style = none
            const props = [
                { property: 'margin' },
                { property: 'padding' },
                { property: 'border', propertyEnd: '-style', defaultValue: 'none' },
            ];
            for (const propertyInfo of props) {
                const p = propertyInfo.property;
                const e = propertyInfo.propertyEnd || '';
                const defVal = propertyInfo.defaultValue || 0;
                if (style[p + '-top' + e] ||
                    style[p + '-right' + e] ||
                    style[p + '-bottom' + e] ||
                    style[p + '-left' + e]) {
                    if (style[p + '-top' + e] === style[p + '-right' + e] &&
                        style[p + '-top' + e] === style[p + '-bottom' + e] &&
                        style[p + '-top' + e] === style[p + '-left' + e]) {
                        // keep => property: [top/right/bottom/left value];
                        style[p + e] = style[p + '-top' + e];
                    }
                    else {
                        // keep => property: [top value] [right value] [bottom value] [left value];
                        style[p + e] =
                            (style[p + '-top' + e] || defVal) +
                                ' ' +
                                (style[p + '-right' + e] || defVal) +
                                ' ' +
                                (style[p + '-bottom' + e] || defVal) +
                                ' ' +
                                (style[p + '-left' + e] || defVal);
                        if (style[p + e].indexOf('inherit') !== -1 ||
                            style[p + e].indexOf('initial') !== -1) {
                            // keep => property-top: [top value]; property-right: [right value]; property-bottom: [bottom value]; property-left: [left value];
                            delete style[p + e];
                            continue;
                        }
                    }
                    delete style[p + '-top' + e];
                    delete style[p + '-right' + e];
                    delete style[p + '-bottom' + e];
                    delete style[p + '-left' + e];
                }
            }
            if (style['border-bottom-left-radius']) {
                style['border-radius'] = style['border-bottom-left-radius'];
                delete style['border-bottom-left-radius'];
                delete style['border-bottom-right-radius'];
                delete style['border-top-left-radius'];
                delete style['border-top-right-radius'];
            }
            // if the border styling is initial we remove it to simplify the css tags for compatibility.
            // Also, since we do not send a css style tag, the initial value of the border is useless.
            for (const prop in Object.keys(style)) {
                if (prop.indexOf('border') !== -1 && style[prop] === 'initial') {
                    delete style[prop];
                }
            }
            // text-decoration rule is decomposed in -line, -color and -style. This is
            // however not supported by many browser/mail clients and the editor does
            // not allow to change -color and -style rule anyway
            if (style['text-decoration-line']) {
                style['text-decoration'] = style['text-decoration-line'];
                delete style['text-decoration-line'];
                delete style['text-decoration-color'];
                delete style['text-decoration-style'];
            }
            return style;
        }
        _specificity(selector) {
            // http://www.w3.org/TR/css3-selectors/#specificity
            let a = 0;
            let b = 0;
            let c = 0;
            selector
                .replace(/#[a-z0-9_-]+/gi, function () {
                a++;
                return '';
            })
                .replace(/(\.[a-z0-9_-]+)|(\[.*?\])/gi, function () {
                b++;
                return '';
            })
                .replace(/(^|\s+|:+)[a-z0-9_-]+/gi, function (a) {
                if (a.indexOf(':not(') === -1)
                    c++;
                return '';
            });
            return a * 100 + b * 10 + c;
        }
        _getMatchedCSSRules(doc) {
            var _a;
            let rulesCache = this.rulesCache.get(doc);
            if (!rulesCache) {
                rulesCache = [];
                const sheets = [];
                for (const sheet of doc.styleSheets) {
                    if (sheet instanceof CSSStyleSheet) {
                        try {
                            // try...catch because browser may not able to enumerate rules for cross-domain sheets
                            if (!sheet.rules)
                                continue;
                        }
                        catch (e) {
                            console.warn("Can't read the css rules of: " + sheet.href, e);
                            continue;
                        }
                        sheets.push(sheet);
                    }
                }
                for (const sheet of sheets) {
                    for (const rule of sheet.rules) {
                        if (rule instanceof CSSStyleRule && ((_a = rule.selectorText) === null || _a === void 0 ? void 0 : _a.indexOf("'")) === -1) {
                            // We don't parse CSSMediaRule or CSSKeyframesRule.
                            // TODO: add better parser for quote inside selector.
                            const fullSelectors = rule.selectorText;
                            const style = {};
                            for (let i = 0; i < rule.style.length; i++) {
                                const prop = rule.style[i];
                                const value = rule.style[prop];
                                if (prop.indexOf('animation') !== -1) {
                                    continue;
                                }
                                style[prop] =
                                    style[prop.replace(/-(.)/g, function (a, b) {
                                        return b.toUpperCase();
                                    })];
                                if (new RegExp(prop + 's*:[^:;]+!important').test(rule.cssText)) {
                                    style[prop] += ' !important';
                                }
                                style[prop] = value;
                            }
                            for (const selector of fullSelectors.split(',')) {
                                rulesCache.push({ selector: selector, style: style });
                            }
                        }
                    }
                }
                this.rulesCache.set(doc, rulesCache);
            }
            return rulesCache;
        }
    }
    Stylesheet.dependencies = [Metadata];

    class ShadowNode extends ContainerNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
    }

    class MailRenderingEngineCache extends RenderingEngineCache {
        constructor(engine) {
            super(engine);
            this.shadowRoots = new Map();
            this.inheritedStyling = new Map();
            this.parented = new Map();
            this.promiseHierarchy = new Map();
            this.defaultFontSize = {};
            this.worker.getStyleFromCSSRules = engine.getStyleFromCSSRules.bind(engine, this);
        }
    }

    const TagWithBrowserCustomFontSize = [
        'BUTTON',
        'CODE',
        'H1',
        'H2',
        'H3',
        'H5',
        'H6',
        'KBD',
        'PRE',
        'SAMP',
        'SMALL',
        'SUB',
        'SUP',
    ];
    const StyleSelectorParsingRegExp = /(.[\w-]*)$/;
    /**
     * Converts css style to inline style (leave the classes on elements but forces
     * the style they give as inline style).
     */
    class MailObjectRenderingEngine extends DomObjectRenderingEngine {
        /**
         * Render the given node and every children. Begin the rendering from the
         * shadowNode ancestor.
         * The shadow nodes must be rendered into the domLayout.
         *
         * @param node
         */
        async render(nodes, cache) {
            cache = cache || new MailRenderingEngineCache(this);
            if (!nodes.find(node => !cache.renderingPromises.get(node))) {
                return super.render(nodes, cache);
            }
            const ancestors = new Set(nodes);
            let shadows = [];
            for (let node of nodes) {
                let shadow;
                while (!shadow && node.parent && !ancestors.has(node.parent)) {
                    node = node.parent;
                    ancestors.add(node);
                    if (node instanceof ShadowNode && !shadows.includes(node)) {
                        shadow = node;
                    }
                }
                if (shadow) {
                    shadows.push(shadow);
                }
                else if (!ancestors.has(node.parent)) {
                    throw new Error('The content to render into mail/html formatting must be in at least shadow node.');
                }
            }
            // Get the ShadowRoot of all shadowNode.
            for (const shadow of shadows) {
                if (!cache.shadowRoots.has(shadow)) {
                    // TODO: load stylesheet without the dom in Stylesheet.
                    const domLayout = this.editor.plugins.get(Layout).engines.dom;
                    const [shadowNode] = domLayout.getDomNodes(shadow);
                    const shadowRoot = shadowNode.shadowRoot;
                    cache.shadowRoots.set(shadow, shadowRoot);
                }
            }
            // Get all children in order.
            shadows = shadows.filter(shadow => !shadow.ancestors(ShadowNode).find(ancestor => shadows.includes(ancestor)));
            const nodesToRender = shadows.map(shadow => [shadow]);
            for (const nodes of nodesToRender) {
                for (let index = 0; index < nodes.length; index++) {
                    const node = nodes[index];
                    if (node instanceof ContainerNode) {
                        nodes.splice(index + 1, 0, ...node.childVNodes);
                    }
                }
            }
            // Apply style of nodes.
            for (const [shadow, ...nodes] of nodesToRender) {
                // Render the shadowNode and all children.
                await super.render(nodes, cache);
                await this._applyStyleFromRules(cache, shadow, nodes);
            }
            return cache;
        }
        /**
         * Returns the css rules which applies on an node. Tweaked so that they are
         * browser/mail client ok.
         *
         * @param {VNode} Node
         * @param {DomObject} rendering Value of the renderer result.
         * @param {DomObject} domObject DomObject returned into the rendering (can be the same object)
         * @param {DomObject} rendering DomObject returned by the renderer
         */
        async getStyleFromCSSRules(cache, node, domObject, rendering) {
            if (cache.inheritedStyling.get(domObject)) {
                return cache.inheritedStyling.get(domObject);
            }
            if (!rendering) {
                rendering = domObject;
            }
            const shadow = node.ancestor(ShadowNode);
            const shadowRoot = cache.shadowRoots.get(shadow);
            const hierarchy = await this._getHierarchy(cache, node, domObject, rendering);
            const styling = await this._getStyleFromCSSRules(cache, domObject, shadowRoot, hierarchy);
            // Remove this current referencie for renderings call, to recompute it after.
            cache.inheritedStyling.delete(domObject);
            cache.promiseHierarchy.delete(domObject);
            cache.promiseHierarchy.delete(node);
            cache.parented.delete(domObject);
            cache.parented.delete(node);
            return styling;
        }
        async _applyStyleFromRules(cache, shadow, nodes) {
            const shadowRoot = cache.shadowRoots.get(shadow);
            const alreadyConverted = new Set();
            for (const node of nodes) {
                const rendering = await cache.renderings.get(node);
                const renderings = [rendering];
                for (const domObject of renderings) {
                    if (!alreadyConverted.has(rendering)) {
                        alreadyConverted.add(rendering);
                        const hierarchy = await this._getHierarchy(cache, node, domObject, rendering);
                        if ('tag' in domObject) {
                            const styling = await this._getStyleFromCSSRules(cache, domObject, shadowRoot, hierarchy);
                            if (!domObject.attributes) {
                                domObject.attributes = {};
                            }
                            else {
                                delete domObject.attributes.contentEditable;
                            }
                            domObject.attributes.style = styling.current;
                        }
                    }
                }
            }
        }
        async _getStyleFromCSSRules(cache, domObject, shadowRoot, ancestors) {
            var _a, _b, _c, _d;
            if (cache.inheritedStyling.get(domObject)) {
                return cache.inheritedStyling.get(domObject);
            }
            const parentStyling = ancestors.length &&
                (await this._getStyleFromCSSRules(cache, ancestors[0].domObject, shadowRoot, ancestors.slice(1)));
            const inherit = Object.assign({}, parentStyling === null || parentStyling === void 0 ? void 0 : parentStyling.inherit);
            for (const prop in parentStyling === null || parentStyling === void 0 ? void 0 : parentStyling.current) {
                const value = parentStyling.current[prop];
                if ((value === null || value === void 0 ? void 0 : value.includes('important')) || !((_a = inherit[prop]) === null || _a === void 0 ? void 0 : _a.includes('important'))) {
                    inherit[prop] = value;
                }
            }
            let style;
            if ('tag' in domObject) {
                const tag = domObject.tag.toUpperCase();
                const stylesheet = this.editor.plugins.get(Stylesheet);
                style = stylesheet.getFilteredStyleFromCSSRules(selector => this._selectorMatchesDomObject(domObject, selector, ancestors), shadowRoot);
                style = Object.assign(style, (_b = domObject.attributes) === null || _b === void 0 ? void 0 : _b.style);
                if (!style['font-size'] && TagWithBrowserCustomFontSize.includes(tag)) {
                    const rootFontSize = this._getDefaultFontSize(cache, 'p');
                    const em = this._getDefaultFontSize(cache, tag) / rootFontSize;
                    style['font-size'] = em + 'em';
                }
                for (const prop in style) {
                    const value = style[prop];
                    if ((_c = inherit[prop]) === null || _c === void 0 ? void 0 : _c.includes('important')) {
                        delete style[prop];
                    }
                    else if (value === 'inherit') {
                        // Take the inherit value.
                        if (inherit[prop]) {
                            style[prop] = inherit[prop];
                        }
                        else {
                            delete style[prop];
                        }
                    }
                    else if (/[0-9]/.test(value)) {
                        // For numeric value, compute in px.
                        // Numeric value => all, vertical & horizontal, top & right & bottom & left.
                        const subValues = value.split(' ');
                        for (const index in subValues) {
                            const subValue = subValues[index];
                            const numeric = parseFloat(subValue);
                            if (!isNaN(numeric) && subValue.includes('em')) {
                                // Convert 'em' and 'rem' values into 'px' values.
                                let previous;
                                if (!subValue.includes('rem') && inherit['font-size']) {
                                    previous = parseFloat(inherit['font-size']);
                                }
                                else {
                                    previous = this._getDefaultFontSize(cache, ((_d = ancestors[0]) === null || _d === void 0 ? void 0 : _d.domObject.tag) || 'p');
                                }
                                subValues[index] =
                                    numeric * previous +
                                        'px' +
                                        (value.includes('important') ? '!important' : '');
                            }
                        }
                        style[prop] = subValues.join(' ');
                    }
                }
                if (style.display === 'block') {
                    delete style.display;
                }
            }
            else {
                style = {};
            }
            cache.inheritedStyling.set(domObject, { current: style, inherit });
            return cache.inheritedStyling.get(domObject);
        }
        _getDefaultFontSize(cache, tag) {
            if (cache.defaultFontSize[tag]) {
                return cache.defaultFontSize[tag];
            }
            else {
                // Default value in the browser.
                const container = document.createElement('div');
                container.attachShadow({ mode: 'open' });
                const p = document.createElement(tag);
                container.shadowRoot.appendChild(p);
                document.body.appendChild(container);
                const size = parseFloat(window.getComputedStyle(p)['font-size']);
                document.body.removeChild(container);
                cache.defaultFontSize[tag] = size;
                return size;
            }
        }
        /**
         * Check if the css rule selector match with the current domObject.
         * (eg: div#id span.toto > a )
         *
         * @param domObject
         * @param selector
         * @param ancestors
         */
        _selectorMatchesDomObject(domObject, selector, ancestors) {
            if (selector.includes(':hover') ||
                selector.includes(':before') ||
                selector.includes(':after') ||
                selector.includes(':active') ||
                selector.includes(':link') ||
                selector.includes('::')) {
                // This cannot be translated to a style attribute on an html node.
                return;
            }
            if (selector.includes('[') || selector.includes(':')) {
                // TODO: add support to select attributes and pseudo-classes.
                return false;
            }
            if (selector.includes('~') || selector.includes('+')) {
                // TODO: add support for all combinators.
                return false;
            }
            const parts = selector.split(' ');
            const part = parts.pop();
            if (!this._basicSelectorMatchesDomObject(domObject, part)) {
                return;
            }
            const origins = ancestors.map(ancestor => ancestor.domObject);
            origins.unshift(domObject);
            let availableOrigin = origins;
            while (parts.length) {
                let part = parts.pop();
                const newOrigins = [];
                if (part === '>') {
                    part = parts.pop();
                    for (const origin of availableOrigin) {
                        const ancestor = origins[origins.indexOf(origin) + 1];
                        if (ancestor && this._basicSelectorMatchesDomObject(ancestor, part)) {
                            newOrigins.push(ancestor);
                        }
                    }
                }
                else {
                    for (const origin of availableOrigin) {
                        const ancestors = origins.slice(origins.indexOf(origin) + 1);
                        for (const ancestor of ancestors) {
                            if (ancestor && this._basicSelectorMatchesDomObject(ancestor, part)) {
                                newOrigins.push(ancestor);
                            }
                        }
                    }
                }
                if (!newOrigins.length) {
                    // No parent to validate the selector.
                    return;
                }
                availableOrigin = newOrigins;
            }
            return true;
        }
        /**
         * Check if the part of css rule selector match with the current domObject.
         * (eg: div#id )
         *
         * @param domObject
         * @param selector
         */
        _basicSelectorMatchesDomObject(domObject, selector) {
            var _a, _b;
            let selectorPart = selector.toUpperCase();
            while (selectorPart) {
                const part = selectorPart.match(StyleSelectorParsingRegExp)[1];
                selectorPart = selectorPart.slice(0, -part.length);
                if (part[0] === '.') {
                    if (!((_a = domObject.attributes) === null || _a === void 0 ? void 0 : _a.class)) {
                        return false;
                    }
                    const className = part.slice(1).toLowerCase();
                    if (!domObject.attributes.class.has(className)) {
                        return false;
                    }
                }
                else if (part[0] === '#') {
                    if (!((_b = domObject.attributes) === null || _b === void 0 ? void 0 : _b.id)) {
                        return false;
                    }
                    const id = part.slice(1).toUpperCase();
                    if (domObject.attributes.id.toUpperCase() !== id) {
                        return false;
                    }
                }
                else if (part !== '*' && part.toUpperCase() !== domObject.tag.toUpperCase()) {
                    return false;
                }
            }
            return true;
        }
        /**
         * Get the parented object.
         *
         * @param node
         * @param domObject
         * @param rendering
         */
        _getHierarchy(cache, node, domObject, rendering) {
            if (cache.promiseHierarchy.get(domObject || node)) {
                return cache.promiseHierarchy.get(domObject || node);
            }
            if (node instanceof ShadowNode) {
                return Promise.resolve([]);
            }
            const promise = this.__getHierarchy(cache, node, domObject, rendering);
            if (domObject) {
                cache.promiseHierarchy.set(domObject, promise);
            }
            if (!domObject || domObject === rendering) {
                cache.promiseHierarchy.set(node, promise);
            }
            return cache.promiseHierarchy.get(domObject || node);
        }
        async __getHierarchy(cache, node, rendering, domObject) {
            if (!domObject) {
                domObject = rendering;
            }
            let rootNode;
            let rootRendering;
            if (domObject === rendering) {
                rootNode = node.parent;
                if (!(rootNode instanceof ShadowNode)) {
                    await Promise.resolve(); // Avoid cycle in render process.
                    await super.render([rootNode], cache);
                    await this._applyStyleFromRules(cache, rootNode.ancestor(ShadowNode), [rootNode]);
                    rootRendering = cache.renderings.get(rootNode);
                }
            }
            else {
                rootNode = node;
                rootRendering = rendering;
            }
            const ancestors = rootRendering
                ? this._getPath(rootRendering, domObject, node).filter(ancestor => 'tag' in ancestor)
                : [];
            const hierarchy = ancestors
                .map(domObject => {
                return {
                    domObject: domObject,
                    node: rootNode,
                };
            })
                .concat(await this._getHierarchy(cache, node.parent));
            if (domObject) {
                cache.parented.set(domObject, hierarchy);
            }
            if (!domObject || domObject === rendering) {
                cache.parented.set(node, hierarchy);
            }
            return hierarchy;
        }
        _getPath(root, item, node) {
            if ('children' in root) {
                if (root.children.includes(item) || root.children.includes(node)) {
                    return [root];
                }
                else {
                    for (const child of root.children) {
                        if (!(child instanceof AbstractNode)) {
                            const path = this._getPath(child, item, node);
                            if (path.length) {
                                return path.concat([root]);
                            }
                        }
                    }
                }
            }
            return [];
        }
    }
    MailObjectRenderingEngine.id = 'object/mail';
    MailObjectRenderingEngine.defaultRenderer = DefaultMailObjectRenderer;
    MailObjectRenderingEngine.extends = [DomObjectRenderingEngine.id];

    class BootstrapButtonLinkMailObjectModifierRenderer extends ModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (modifier) => {
                if (!(modifier instanceof LinkFormat)) {
                    return false;
                }
                const classList = modifier.modifiers.find(Attributes).classList;
                return classList.has('btn') && !classList.has('btn-link');
            };
        }
        /**
         * Rendering for Outlook mail client of link with bootstrap btn format.
         * (use table to keep button background color, margin, padding and border-radius)
         *
         * @param modifier
         * @param renderings
         * @param batch
         */
        async render(modifier, renderings, batch, worker) {
            const [linkObject] = (await this.super.render(modifier, renderings, batch, worker));
            const styleFromRules = await worker.getStyleFromCSSRules(batch[0], linkObject);
            linkObject.attributes.style = styleFromRules.current;
            const table = {
                tag: 'TABLE',
                attributes: {
                    style: {
                        'display': 'inline-table',
                        'vertical-align': 'middle',
                    },
                    cellpadding: '0',
                    cellspacing: '0',
                },
                children: [
                    {
                        tag: 'TBODY',
                        children: [
                            {
                                tag: 'TR',
                                children: [
                                    {
                                        tag: 'TD',
                                        attributes: {
                                            style: {
                                                'text-align': styleFromRules.current['text-align'] ||
                                                    styleFromRules.inherit['text-align'] ||
                                                    'left',
                                                'margin': styleFromRules.current.padding ||
                                                    styleFromRules.inherit.padding ||
                                                    '0px',
                                                'border-radius': styleFromRules.current['border-radius'] ||
                                                    styleFromRules.inherit['border-radius'] ||
                                                    'left',
                                                'background-color': styleFromRules.current['background-color'] ||
                                                    styleFromRules.inherit['background-color'] ||
                                                    'transparent',
                                            },
                                        },
                                        children: [linkObject],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            };
            return [table];
        }
    }
    BootstrapButtonLinkMailObjectModifierRenderer.id = MailObjectRenderingEngine.id;

    function isInLink(range) {
        const node = range.start.nextSibling() || range.start.previousSibling();
        return node && node instanceof InlineNode && !!node.modifiers.find(LinkFormat);
    }
    class Link extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                link: {
                    handler: this.link,
                },
                unlink: {
                    handler: this.unlink,
                },
            };
            this.loadables = {
                parsers: [LinkXmlDomParser],
                renderers: [BootstrapButtonLinkMailObjectModifierRenderer],
                shortcuts: [
                    {
                        pattern: 'CTRL+K',
                        selector: [(node) => !Link.isLink(node)],
                        commandId: 'link',
                    },
                    {
                        pattern: 'CTRL+K',
                        selector: [Link.isLink],
                        commandId: 'unlink',
                    },
                ],
                components: [
                    {
                        id: 'link',
                        async render(editor, props) {
                            return [new OwlNode({ Component: LinkComponent, props: props })];
                        },
                    },
                    {
                        id: 'LinkButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'link',
                                label: 'Insert link',
                                commandId: 'link',
                                selected: (editor) => {
                                    return isInLink(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'fa fa-link fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'UnlinkButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'unlink',
                                label: 'Remove link',
                                commandId: 'unlink',
                                enabled: (editor) => {
                                    return isInLink(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'fa fa-unlink fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [
                    ['link', ['float']],
                    ['LinkButton', ['actionables']],
                    ['UnlinkButton', ['actionables']],
                ],
                owlTemplates: [linkForm],
            };
        }
        static isLink(link, node) {
            if (link instanceof AbstractNode) {
                node = link;
            }
            const format = node instanceof InlineNode && node.modifiers.find(LinkFormat);
            return link instanceof AbstractNode ? !!format : link.isSameAs(format);
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        async link(params) {
            var _a, _b;
            // If the url is undefined, ask the user to provide one.
            const range = params.context.range;
            const replaceSelection = range.isCollapsed() || !!((_a = params.label) === null || _a === void 0 ? void 0 : _a.length);
            if (!params.url || (replaceSelection && !((_b = params.label) === null || _b === void 0 ? void 0 : _b.length))) {
                const selectedInlines = range.selectedNodes(InlineNode);
                const firstLink = selectedInlines.find(node => node.modifiers.find(LinkFormat));
                const link = firstLink && firstLink.modifiers.find(LinkFormat);
                const url = (link === null || link === void 0 ? void 0 : link.url) || '';
                const layout = this.editor.plugins.get(Layout);
                await layout.remove('link');
                const prop = {
                    replaceSelection: replaceSelection,
                    label: params.label,
                    url: url,
                };
                return layout.append('link', undefined, prop);
            }
            // Otherwise create a link and insert it.
            const link = new LinkFormat(params.url);
            if (params.target) {
                link.modifiers.get(Attributes).set('target', params.target);
            }
            if (replaceSelection) {
                await params.context.execCommand('insertText', {
                    text: params.label || link.url,
                    formats: new Modifiers(link),
                    context: params.context,
                });
            }
            else {
                const selectedInlines = range.selectedNodes(InlineNode);
                selectedInlines.forEach(node => {
                    const currentLink = node.modifiers.find(LinkFormat);
                    if (currentLink) {
                        node.modifiers.remove(currentLink);
                    }
                    node.modifiers.append(link);
                });
                range.collapse(range.end);
            }
        }
        unlink(params) {
            const range = params.context.range;
            if (range.isCollapsed()) {
                // If no range is selected and we are in a Link : remove the complete link.
                const previousNode = range.start.previousSibling();
                const nextNode = range.start.nextSibling();
                const node = Link.isLink(previousNode) ? previousNode : nextNode;
                if (!Link.isLink(node))
                    return;
                const link = node.modifiers.find(LinkFormat);
                const sameLink = Link.isLink.bind(Link, link);
                this._removeLinkOnNodes([node, ...node.adjacents(sameLink)]);
            }
            else {
                // If a range is selected : remove any link on the selected range.
                const selectedNodes = range.selectedNodes(InlineNode);
                // Remove the format 'LinkFormat' for all nodes.
                this._removeLinkOnNodes(selectedNodes);
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Remove all link modifiers on the provided nodes.
         * This method is mainly use by the unlink function of the editor.
         */
        _removeLinkOnNodes(nodes) {
            for (const node of nodes) {
                node.modifiers.remove(LinkFormat);
            }
        }
    }
    Link.dependencies = [Inline];

    class DividerXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'DIV';
            };
        }
        async parse(item) {
            const divider = new DividerNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                divider.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            divider.append(...nodes);
            return [divider];
        }
    }
    DividerXmlDomParser.id = XmlDomParsingEngine.id;

    class Divider extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [DividerXmlDomParser],
            };
        }
    }

    class ImageNode extends InlineNode {
    }
    ImageNode.atomic = true;

    class ImageXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'IMG';
            };
        }
        async parse(item) {
            const image = new ImageNode();
            image.modifiers.append(this.engine.parseAttributes(item));
            return [image];
        }
    }
    ImageXmlDomParser.id = XmlDomParsingEngine.id;

    class ImageDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ImageNode;
        }
        async render(node, worker) {
            const select = async (ev) => {
                ev.preventDefault();
                const selectImage = async () => {
                    return this.engine.editor.selection.select(node, node);
                };
                await this.engine.editor.execCommand(selectImage);
            };
            const image = {
                tag: 'IMG',
                attach: (el) => {
                    el.addEventListener('mouseup', select, true);
                },
                detach: (el) => {
                    el.removeEventListener('mouseup', select, true);
                },
            };
            const isSelected = this.engine.editor.selection.range.selectedNodes(selectedNode => selectedNode === node).length;
            if (isSelected) {
                image.attributes = { class: new Set(['jw_selected_image']) };
            }
            worker.locate([node], image);
            return image;
        }
    }
    ImageDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ImageMailObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ImageNode;
        }
        /**
         * Special rendering for mail clients.
         *
         * @override
         */
        async render(img, worker) {
            var _a, _b;
            const imgObject = (await this.super.render(img, worker));
            // Center image on Outlook.
            if (((_a = imgObject.attributes) === null || _a === void 0 ? void 0 : _a.class.has('mx-auto')) && ((_b = imgObject.attributes) === null || _b === void 0 ? void 0 : _b.class.has('d-block'))) {
                return {
                    tag: 'P',
                    attributes: {
                        style: { 'text-align': 'center', 'margin': '0' },
                    },
                    children: [imgObject],
                };
            }
            return imgObject;
        }
    }
    ImageMailObjectRenderer.id = MailObjectRenderingEngine.id;

    class Image extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ImageXmlDomParser],
                renderers: [ImageDomObjectRenderer, ImageMailObjectRenderer],
            };
        }
    }

    class SubscriptFormat extends Format {
        constructor() {
            super('SUB');
        }
    }

    class SubscriptXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'SUB';
            };
        }
        /**
         * Parse a span node.
         *
         * @param item
         */
        async parse(item) {
            const subscript = new SubscriptFormat();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                subscript.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(subscript, children);
            return children;
        }
    }

    class Subscript extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [SubscriptXmlDomParser],
            };
        }
    }
    Subscript.dependencies = [Inline];

    class SuperscriptFormat extends Format {
        constructor() {
            super('SUP');
        }
    }

    class SuperscriptXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'SUP';
            };
        }
        /**
         * Parse a span node.
         *
         * @param item
         */
        async parse(item) {
            const superscript = new SuperscriptFormat();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                superscript.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(superscript, children);
            return children;
        }
    }

    class Superscript extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [SuperscriptXmlDomParser],
            };
        }
    }
    Superscript.dependencies = [Inline];

    class BlockquoteXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'BLOCKQUOTE';
            };
        }
        async parse(item) {
            const blockquote = new BlockquoteNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                blockquote.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            blockquote.append(...nodes);
            return [blockquote];
        }
    }
    BlockquoteXmlDomParser.id = XmlDomParsingEngine.id;

    function isInBlockquote(range) {
        const startBlockquote = !!range.start.closest(BlockquoteNode);
        if (!startBlockquote || range.isCollapsed()) {
            return startBlockquote;
        }
        else {
            return !!range.end.closest(BlockquoteNode);
        }
    }
    class Blockquote extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                applyBlockquoteStyle: {
                    handler: this.applyBlockquoteStyle,
                },
            };
            this.loadables = {
                parsers: [BlockquoteXmlDomParser],
                components: [
                    {
                        id: 'BlockquoteButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'blockquote',
                                label: 'Blockquote',
                                commandId: 'applyBlockquoteStyle',
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    return isInBlockquote(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'blockquote' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['BlockquoteButton', ['actionables']]],
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Change the formatting of the nodes in given range to Blockquote.
         *
         * @param params
         */
        applyBlockquoteStyle(params) {
            for (const node of params.context.range.targetedNodes(node => node instanceof HeadingNode ||
                node instanceof ParagraphNode ||
                node instanceof PreNode)) {
                const blockquote = new BlockquoteNode();
                blockquote.modifiers = node.modifiers.clone();
                node.replaceWith(blockquote);
            }
        }
    }

    class YoutubeNode extends InlineNode {
    }
    YoutubeNode.atomic = true;

    class YoutubeXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                const isYoutubeVideo = item instanceof Element &&
                    nodeName(item) === 'IFRAME' &&
                    item.getAttribute('src') &&
                    item.getAttribute('src').includes('youtu');
                return isYoutubeVideo;
            };
        }
        async parse(item) {
            const youtube = new YoutubeNode();
            youtube.modifiers.append(this.engine.parseAttributes(item));
            return [youtube];
        }
    }
    YoutubeXmlDomParser.id = XmlDomParsingEngine.id;

    class YoutubeDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = YoutubeNode;
        }
        async render() {
            const youtube = {
                tag: 'IFRAME',
            };
            return youtube;
        }
    }
    YoutubeDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Youtube extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [YoutubeXmlDomParser],
                renderers: [YoutubeDomObjectRenderer],
            };
        }
    }

    class TableXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return nodeName(item) === 'TABLE';
            };
        }
        /**
         * Parse a table node.
         *
         * @param item
         */
        async parse(item) {
            // Parse the table itself and its attributes.
            const table = new TableNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                table.modifiers.append(attributes);
            }
            // Parse the contents of the table.
            const children = await this.engine.parse(...item.childNodes);
            // Build the grid.
            const dimensions = this._getTableDimensions(item);
            const parsedRows = children.filter(row => row instanceof TableRowNode);
            const grid = this._createTableGrid(dimensions, parsedRows);
            // Append the cells to the rows.
            const rows = new Array(dimensions[0]);
            for (let rowIndex = 0; rowIndex < grid.length; rowIndex += 1) {
                rows[rowIndex] = parsedRows[rowIndex];
                const cells = grid[rowIndex];
                let row = rows[rowIndex];
                if (!row) {
                    row = new TableRowNode();
                }
                row.append(...cells);
            }
            // Append the rows and other children to the table.
            let rowIndex = 0;
            for (let childIndex = 0; childIndex < children.length; childIndex += 1) {
                const child = children[childIndex];
                if (child instanceof TableRowNode) {
                    const row = rows[rowIndex];
                    table.append(row);
                    rowIndex += 1;
                }
                else {
                    table.append(children[childIndex]);
                }
            }
            return [table];
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return a tuple with the row length and the column length of the given DOM
         * table element.
         *
         * @param domTable
         */
        _getTableDimensions(domTable) {
            const domRows = Array.from(domTable.querySelectorAll('tr'));
            const domTableRows = domRows.filter(row => row.closest('table') === domTable);
            let columnCount = 0;
            if (domTableRows.length) {
                const domCells = Array.from(domTableRows[0].querySelectorAll('td, th'));
                const domTableCells = domCells.filter(cell => cell.closest('table') === domTable);
                for (const domChild of domTableCells) {
                    columnCount += parseInt(domChild.getAttribute('colSpan') || '1', 10);
                }
            }
            return [domTableRows.length, columnCount];
        }
        /**
         * Build and return the grid (2D array: rows of cells) that will be used to
         * create the table. We want all the rows to have the same number of cells,
         * and all the columns to have the same number of cells.
         *
         * @param dimensions
         * @param rows
         */
        _createTableGrid(dimensions, rows) {
            const [rowCount, columnCount] = dimensions;
            // Initialize the grid (2D array: rows of cells).
            const grid = Array.from(Array(rowCount), () => new Array(columnCount));
            // Move every parsed child row to its place in the grid, and create
            // placeholder cells where there aren't any, accounting for column spans
            // and row spans.
            for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
                const row = rows[rowIndex];
                const cells = row.children(TableCellNode).slice();
                for (let domCellIndex = 0; domCellIndex < cells.length; domCellIndex += 1) {
                    const cell = cells[domCellIndex];
                    // If there is a cell at this grid position already, it means we
                    // added it there when handling another cell, ie. it's a
                    // placeholder cell, managed by a previously handled cell.
                    // The current cell needs to be added at the next available slot
                    // instead.
                    let columnIndex = domCellIndex;
                    while (grid[rowIndex][columnIndex]) {
                        columnIndex += 1;
                    }
                    // Check traversing colspan and rowspan to insert placeholder
                    // cells where necessary. Consume these attributes as they will
                    // be replaced with getters.
                    const attributes = cell.modifiers.find(Attributes);
                    let colspan = 1;
                    let rowspan = 1;
                    if (attributes) {
                        colspan = parseInt(attributes.get('colspan'), 10) || 1;
                        rowspan = parseInt(attributes.get('rowspan'), 10) || 1;
                        attributes.remove('colspan');
                        attributes.remove('rowspan');
                    }
                    for (let i = rowIndex; i < rowIndex + rowspan; i += 1) {
                        for (let j = columnIndex; j < columnIndex + colspan; j += 1) {
                            if (i === rowIndex && j === columnIndex) {
                                // Add the current cell to the grid.
                                grid[i][j] = cell;
                            }
                            else {
                                // Add a placeholder cell to the grid.
                                const placeholderCell = new TableCellNode();
                                placeholderCell.mergeWith(cell);
                                grid[i][j] = placeholderCell;
                            }
                        }
                    }
                }
            }
            // Insert empty cells in every undefined element of the grid.
            return grid.map(row => Array.from(row, cell => cell || new TableCellNode()));
        }
    }
    TableXmlDomParser.id = XmlDomParsingEngine.id;

    class TableSectionAttributes extends Attributes {
    }
    class TableRowXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                const name = nodeName(item);
                return name === 'THEAD' || name === 'TBODY' || name === 'TR';
            };
        }
        /**
         * Parse a row node or a table section node.
         *
         * @param item
         */
        async parse(item) {
            if (this._isTableSection(item)) {
                return this.parseTableSection(item);
            }
            else if (nodeName(item) === 'TR') {
                const row = new TableRowNode();
                const attributes = this.engine.parseAttributes(item);
                if (attributes.length) {
                    row.modifiers.append(attributes);
                }
                const cells = await this.engine.parse(...item.childNodes);
                row.append(...cells);
                return [row];
            }
        }
        /**
         * Parse a <tbody> or a <thead> into an array of table rows with their
         * `header` property set in function of whether they are contained in a
         * <tbody> or a <thead>.
         *
         * @param tableSection
         */
        async parseTableSection(tableSection) {
            const parsedNodes = [];
            // Parse the section's children.
            for (const child of tableSection.childNodes) {
                parsedNodes.push(...(await this.engine.parse(child)));
            }
            // Parse the <tbody> or <thead>'s modifiers.
            const attributes = this.engine.parseAttributes(tableSection);
            // Apply the attributes, style and `header` property of the container to
            // each row.
            const name = nodeName(tableSection);
            for (const parsedNode of parsedNodes) {
                if (parsedNode instanceof TableRowNode) {
                    parsedNode.header = name === 'THEAD';
                    parsedNode.modifiers.replace(TableSectionAttributes, new TableSectionAttributes(attributes));
                }
            }
            return parsedNodes;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the given item is a table section element.
         *
         * @param item
         */
        _isTableSection(item) {
            const name = nodeName(item);
            return name === 'THEAD' || name === 'TBODY';
        }
    }
    TableRowXmlDomParser.id = XmlDomParsingEngine.id;

    class TableCellXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                const name = nodeName(item);
                return name === 'TD' || name === 'TH';
            };
        }
        /**
         * Parse a table cell node.
         *
         * @param item
         */
        async parse(item) {
            const cell = new TableCellNode({ header: nodeName(item) === 'TH' });
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                cell.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            cell.append(...children);
            return [cell];
        }
    }
    TableCellXmlDomParser.id = XmlDomParsingEngine.id;

    class TableDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableNode;
        }
        /**
         * Render the TableNode along with its contents (TableRowNodes).
         */
        async render(table, worker) {
            const objectTable = {
                tag: 'TABLE',
                children: [],
            };
            const objectHead = {
                tag: 'THEAD',
                children: [],
            };
            let objectBody = {
                tag: 'TBODY',
                children: [],
            };
            for (const child of table.children()) {
                if (child instanceof TableRowNode) {
                    // If the child is a row, append it to its containing section.
                    const tableSection = child.header ? objectHead : objectBody;
                    tableSection.children.push(child);
                    this.engine.renderAttributes(TableSectionAttributes, child, tableSection, worker);
                    if (!objectTable.children.includes(tableSection)) {
                        objectTable.children.push(tableSection);
                    }
                }
                else {
                    objectTable.children.push(child);
                    // Create a new <tbody> so the rest of the rows, if any, get
                    // appended to it, after this element.
                    objectBody = {
                        tag: 'TBODY',
                        children: [],
                    };
                }
            }
            return objectTable;
        }
    }
    TableDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class TableRowDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableRowNode;
        }
        /**
         * Render the TableRowNode along with its contents.
         */
        async render(row) {
            const objectRow = {
                tag: 'TR',
                children: row.children(),
            };
            return objectRow;
        }
    }
    TableRowDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class TableCellDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableCellNode;
        }
        async render(cell) {
            // If the cell is not active, do not render it (it means it is
            // represented by its manager cell's colspan or rowspan: it was merged).
            // TODO: remove `TableNode` check: it's a temporary fix for the memory
            // system, which should not try to render the cell if it's not in the
            // VDocument.
            if (!cell.isActive() || !cell.ancestor(TableNode))
                return { children: [] };
            // Render the cell and its contents.
            const domObject = {
                tag: cell.header ? 'TH' : 'TD',
                attributes: {},
                children: await this.engine.renderChildren(cell),
            };
            // Colspan and rowspan are handled differently from other attributes:
            // they are automatically calculated in function of the cell's managed
            // cells. Render them here. If their value is 1 or less, they are
            // insignificant so no need to render them.
            if (cell.colspan > 1) {
                domObject.attributes.colspan = cell.colspan.toString();
            }
            if (cell.rowspan > 1) {
                domObject.attributes.rowspan = cell.rowspan.toString();
            }
            return domObject;
        }
    }
    TableCellDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class TableSectionAttributesDomObjectModifierRenderer extends ModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableSectionAttributes;
        }
        /**
         * Rendering for TableSectionAttributes Modifier.
         *
         * @param format
         * @param contents
         */
        async render(format, contents) {
            return contents;
        }
    }
    TableSectionAttributesDomObjectModifierRenderer.id = DomObjectRenderingEngine.id;

    class TableCellMailObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableCellNode;
        }
        /**
         * Special rendering for mail clients.
         *
         * @override
         */
        async render(cell, worker) {
            var _a, _b;
            const cellObject = (await this.super.render(cell, worker));
            const styleFromRules = await worker.getStyleFromCSSRules(cell, cellObject);
            // Text-align inheritance does not seem to get past <td> elements.
            const textAlign = ((_b = (_a = cellObject.attributes) === null || _a === void 0 ? void 0 : _a.style) === null || _b === void 0 ? void 0 : _b['text-align']) || styleFromRules.current['text-align'];
            if (!textAlign || (textAlign === 'inherit' && styleFromRules.inherit['text-align'])) {
                cellObject.attributes = cellObject.attributes || {};
                cellObject.attributes.style = cellObject.attributes.style || {};
                cellObject.attributes.style['text-align'] = styleFromRules.inherit['text-align'];
            }
            // Empty td are not displayed on Apple Mail.
            if (!cell.hasChildren()) {
                cellObject.children = [{ text: '&nbsp;' }];
            }
            return cellObject;
        }
    }
    TableCellMailObjectRenderer.id = MailObjectRenderingEngine.id;

    class TablePickerNode extends TableNode {
        constructor(params) {
            super(params);
            this.modifiers.get(Attributes).classList.add('table-picker');
        }
    }

    class TablePickerDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TablePickerNode;
        }
        async render(tablePicker, worker) {
            const domObject = (await this.super.render(tablePicker, worker));
            const tablePlugin = this.engine.editor.plugins.get(Table);
            const layout = this.engine.editor.plugins.get(Layout).engines.dom;
            let attach;
            const close = async () => {
                this.engine.editor.execCommand(async () => {
                    this.engine.editor.memoryInfo.uiCommand = true;
                    if (attach &&
                        tablePlugin.isTablePickerOpen &&
                        layout.components.TablePicker.length) {
                        await layout.remove('TablePicker');
                    }
                });
            };
            domObject.attach = () => {
                attach = true;
                tablePlugin.isTablePickerOpen = true;
                window.addEventListener('click', close, true);
            };
            domObject.detach = () => {
                attach = false;
                tablePlugin.isTablePickerOpen = false;
                window.removeEventListener('click', close, true);
            };
            return domObject;
        }
    }
    TablePickerDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class TablePickerCellDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (node) => { var _a; return node instanceof TableCellNode && ((_a = node.parent) === null || _a === void 0 ? void 0 : _a.parent) instanceof TablePickerNode; };
        }
        async render(tablePickerCell, worker) {
            const domObject = (await this.super.render(tablePickerCell, worker));
            domObject.attributes = Object.assign(Object.assign({}, domObject.attributes), {
                'data-rowCount': '' + (tablePickerCell.rowIndex + 1),
                'data-columnCount': '' + (tablePickerCell.columnIndex + 1),
            });
            const tablePlugin = this.engine.editor.plugins.get(Table);
            const minRowCount = tablePlugin.minRowCount;
            const minColumnCount = tablePlugin.minColumnCount;
            const onMouseOver = (ev) => {
                const table = ev.target.closest('table.table-picker');
                for (const cell of table.querySelectorAll('td')) {
                    const rowIndex = +cell.getAttribute('data-rowCount') - 1;
                    const columnIndex = +cell.getAttribute('data-columnCount') - 1;
                    if (rowIndex <= tablePickerCell.rowIndex &&
                        columnIndex <= tablePickerCell.columnIndex) {
                        cell.classList.add('highlight');
                    }
                    else {
                        cell.classList.remove('highlight');
                    }
                }
                const tablePicker = tablePickerCell.ancestor(TableNode);
                if (tablePickerCell.rowIndex >= tablePicker.rowCount - 1 ||
                    tablePicker.rowCount > minRowCount ||
                    tablePickerCell.columnIndex >= tablePicker.columnCount - 1 ||
                    tablePicker.columnCount > minColumnCount) {
                    this.engine.editor.execCommand(() => {
                        this.engine.editor.memoryInfo.uiCommand = true;
                        const toRedraw = new Set();
                        // Add/remove rows.
                        if (tablePickerCell.rowIndex >= tablePicker.rowCount - 1) {
                            // Add.
                            const newRow = new TableRowNode();
                            toRedraw.add(newRow);
                            tablePicker.append(newRow);
                            for (let cellIndex = 0; cellIndex < tablePicker.columnCount; cellIndex++) {
                                const newCell = new TableCellNode();
                                newRow.append(newCell);
                                toRedraw.add(newCell);
                            }
                        }
                        else if (tablePicker.rowCount > minRowCount) {
                            // Remove.
                            const rows = tablePicker.children(child => child instanceof TableRowNode &&
                                child.rowIndex >= minRowCount &&
                                child.rowIndex > tablePickerCell.rowIndex + 1);
                            for (const row of rows) {
                                for (const rowCell of row.children(TableCellNode)) {
                                    rowCell.remove();
                                }
                                row.remove();
                            }
                            if (rows.length)
                                toRedraw.add(tablePicker);
                        }
                        // Add/remove Columns.
                        if (tablePickerCell.columnIndex >= tablePicker.columnCount - 1) {
                            // Add.
                            for (const row of tablePicker.children(TableRowNode)) {
                                const newCell = new TableCellNode();
                                row.append(newCell);
                                toRedraw.add(newCell);
                            }
                        }
                        else if (tablePicker.columnCount > minColumnCount) {
                            // Remove.
                            const cellsToRemove = tablePicker.descendants(descendant => descendant instanceof TableCellNode &&
                                descendant.columnIndex >= minColumnCount &&
                                descendant.columnIndex > tablePickerCell.columnIndex + 1);
                            for (const cellToRemove of cellsToRemove) {
                                toRedraw.add(cellToRemove.parent);
                                cellToRemove.remove();
                            }
                            if (cellsToRemove.length)
                                toRedraw.add(tablePicker);
                        }
                    });
                }
            };
            const onPickCell = async (ev) => {
                const cell = ev.target;
                await this.engine.editor.execCommand('insertTable', {
                    rowCount: cell.getAttribute('data-rowCount'),
                    columnCount: cell.getAttribute('data-columnCount'),
                });
            };
            domObject.attach = (el) => {
                el.addEventListener('mouseover', onMouseOver);
                el.addEventListener('mousedown', onPickCell);
            };
            domObject.detach = (el) => {
                el.removeEventListener('mouseover', onMouseOver);
                el.removeEventListener('mousedown', onPickCell);
            };
            return domObject;
        }
    }
    TablePickerCellDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Table extends JWPlugin {
        constructor(editor, config) {
            super(editor, config);
            this.editor = editor;
            this.config = config;
            this.loadables = {
                parsers: [TableXmlDomParser, TableRowXmlDomParser, TableCellXmlDomParser],
                renderers: [
                    TablePickerDomObjectRenderer,
                    TablePickerCellDomObjectRenderer,
                    TableDomObjectRenderer,
                    TableRowDomObjectRenderer,
                    TableCellDomObjectRenderer,
                    TableCellMailObjectRenderer,
                    TableSectionAttributesDomObjectModifierRenderer,
                ],
                components: [
                    {
                        id: 'TableButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'tableButton',
                                label: 'Pick the size of the table you want to insert',
                                commandId: 'insertTable',
                                visible: isInTextualContext,
                                selected: (editor) => editor.plugins.get(Table).isTablePickerOpen,
                                modifiers: [new Attributes({ class: 'fa fa-table fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'TablePicker',
                        async render(editor) {
                            const tablePlugin = editor.plugins.get(Table);
                            const table = new TablePickerNode({
                                rowCount: tablePlugin.minRowCount,
                                columnCount: tablePlugin.minColumnCount,
                            });
                            return [table];
                        },
                    },
                ],
                componentZones: [['TableButton', ['actionables']]],
            };
            this.commands = {
                insertTable: {
                    handler: this.insertTable.bind(this),
                },
                addRowAbove: {
                    handler: this.addRowAbove.bind(this),
                },
                addRowBelow: {
                    handler: this.addRowBelow.bind(this),
                },
                addColumnBefore: {
                    handler: this.addColumnBefore.bind(this),
                },
                addColumnAfter: {
                    handler: this.addColumnAfter.bind(this),
                },
                deleteRow: {
                    handler: this.deleteRow.bind(this),
                },
                deleteColumn: {
                    handler: this.deleteColumn.bind(this),
                },
                deleteTable: {
                    handler: this.deleteTable.bind(this),
                },
                mergeCells: {
                    handler: this.mergeCells.bind(this),
                },
                unmergeCells: {
                    handler: this.unmergeCells.bind(this),
                },
            };
            this.isTablePickerOpen = false;
            /**
             * The minimum row count for the table picker (default: 5).
             */
            this.minRowCount = 5;
            /**
             * The minimum column count for the table picker (default: 5).
             */
            this.minColumnCount = 5;
            /**
             * If true, add UI buttons inline in the table on render to add/remove
             * columns/rows.
             */
            this.inlineUI = false;
            if (config.minRowCount) {
                this.minRowCount = config.minRowCount;
            }
            if (config.minColumnCount) {
                this.minColumnCount = config.minColumnCount;
            }
            this.inlineUI = !!config.inlineUI;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Insert a table at range. If no dimensions are given for the table, open
         * the table picker in order to ask the user for dimensions.
         *
         * @param params
         */
        async insertTable(params) {
            const layout = this.editor.plugins.get(Layout);
            if (this.isTablePickerOpen) {
                await layout.remove('TablePicker');
            }
            if (!params.rowCount || !params.columnCount) {
                this.editor.memoryInfo.uiCommand = true;
                if (!this.isTablePickerOpen) {
                    await layout.append('TablePicker', 'TableButton');
                }
            }
            else {
                const range = params.context.range;
                range.empty();
                if (range.startContainer) {
                    const table = new TableNode(params);
                    range.start.before(table);
                    table.firstLeaf().prepend(range.start);
                    range.collapse();
                }
            }
        }
        /**
         * Add a row above the cell at given range start.
         *
         * @param params
         */
        addRowAbove(params) {
            const range = params.context.range;
            const cell = range.start.ancestor(TableCellNode);
            if (!cell)
                return;
            cell.ancestor(TableNode).addRowAbove(cell);
        }
        /**
         * Add a row below the cell at given range start.
         *
         * @param params
         */
        addRowBelow(params) {
            const range = params.context.range;
            const row = range.start.ancestor(TableCellNode);
            if (!row)
                return;
            row.ancestor(TableNode).addRowBelow(row);
        }
        /**
         * Add a column before the cell at given range start.
         *
         * @param params
         */
        addColumnBefore(params) {
            const range = params.context.range;
            const cell = range.start.ancestor(TableCellNode);
            if (!cell)
                return;
            cell.ancestor(TableNode).addColumnBefore(cell);
        }
        /**
         * Add a column after the cell at given range start.
         *
         * @param params
         */
        addColumnAfter(params) {
            const range = params.context.range;
            const cell = range.start.ancestor(TableCellNode);
            if (!cell)
                return;
            cell.ancestor(TableNode).addColumnAfter(cell);
        }
        /**
         * Delete the row at given range start.
         *
         * @param params
         */
        deleteRow(params) {
            const range = params.context.range;
            const cell = range.start.ancestor(TableCellNode);
            if (!cell)
                return;
            const row = cell.ancestor(TableRowNode);
            const nextRow = row.nextSibling(TableRowNode) || row.previousSibling(TableRowNode);
            const nextCell = nextRow && nextRow.children(TableCellNode)[cell.columnIndex];
            if (nextCell) {
                const nextRowIndex = nextCell.rowIndex;
                // Handle rowspans.
                const cells = row.children(TableCellNode);
                for (const cell of cells) {
                    if (cell.rowspan > 1) {
                        // Cells managed by this cell will now be managed by the
                        // cell below (or above if there is none below) instead.
                        const belowCell = Array.from(cell.managedCells).find(managedCell => managedCell.rowIndex === nextRowIndex);
                        if (belowCell) {
                            belowCell.unmerge();
                            for (const managedCell of cell.managedCells) {
                                if (managedCell !== belowCell) {
                                    managedCell.mergeWith(belowCell);
                                }
                            }
                        }
                    }
                    else if (!cell.isActive()) {
                        // If this cell is inactive, unmerge it so its manager
                        // doesn't believe it still manages it.
                        cell.unmerge();
                    }
                }
                // Remove the row.
                row.remove();
                // The place where the range used to live was just demolished. Give
                // it shelter within the next active cell.
                const nextActiveCell = nextCell.managerCell || nextCell;
                range.setStart(nextActiveCell.firstLeaf(), RelativePosition.BEFORE);
                range.collapse();
            }
            else {
                // If there is no `nextCell`, we're trying to delete the only row in
                // this table so just remove the table.
                this.deleteTable(params);
            }
        }
        /**
         * Delete the column at given range start.
         *
         * @param params
         */
        deleteColumn(params) {
            const range = params.context.range;
            const cell = range.start.ancestor(TableCellNode);
            if (!cell)
                return;
            const column = cell.column;
            const nextCell = cell.nextSibling(TableCellNode) || cell.previousSibling(TableCellNode);
            if (nextCell) {
                const nextColumnIndex = nextCell.columnIndex;
                // Handle colspans and cell removal.
                for (const cell of column) {
                    if (cell.colspan > 1) {
                        // Cells managed by this cell will now be managed by the
                        // cell after (or before if there is none after) instead.
                        const afterCell = Array.from(cell.managedCells).find(managedCell => managedCell.columnIndex === nextColumnIndex);
                        if (afterCell) {
                            afterCell.unmerge();
                            for (const managedCell of cell.managedCells) {
                                if (managedCell !== afterCell) {
                                    managedCell.mergeWith(afterCell);
                                }
                            }
                        }
                    }
                    else if (!cell.isActive()) {
                        // If this cell is inactive, unmerge it so its manager
                        // doesn't believe it still manages it.
                        cell.unmerge();
                    }
                    // Remove the cell.
                    cell.remove();
                    // The place where the range used to live was just demolished.
                    // Give it shelter within the next active cell.
                    const nextManagerCell = nextCell.managerCell || nextCell;
                    range.setStart(nextManagerCell.firstLeaf(), RelativePosition.BEFORE);
                    range.collapse();
                }
            }
            else {
                // If there is no `nextCell`, we're trying to delete the only column
                // in this table so just remove the table.
                this.deleteTable(params);
            }
        }
        /**
         * Delete the table at given range start.
         *
         * @param params
         */
        deleteTable(params) {
            const range = params.context.range;
            const table = range.start.ancestor(TableNode);
            if (!table)
                return;
            const nextSibling = table.nextSibling();
            const previousSibling = table.previousSibling();
            if (nextSibling) {
                range.setStart(nextSibling.firstLeaf(), RelativePosition.BEFORE);
                range.collapse();
            }
            else if (previousSibling) {
                range.setStart(previousSibling.lastLeaf(), RelativePosition.AFTER);
                range.collapse();
            }
            table.remove();
        }
        /**
         * Merge the cells at given range into the first cell at given range.
         *
         * @param params
         */
        mergeCells(params) {
            const range = params.context.range;
            const cells = range.targetedNodes(TableCellNode);
            if (this._isRectangle(cells)) {
                // Only merge the cells if they would not imply to merge
                // unrelated cells, ie. the selected cells form a rectangle.
                const managerCell = cells.shift();
                const Separator = this.editor.configuration.defaults.Separator;
                for (const cell of cells) {
                    if (managerCell.hasChildren()) {
                        managerCell.append(new Separator());
                    }
                    cell.mergeWith(managerCell);
                }
            }
        }
        /**
         * Unmerge previously merged cells at given range.
         *
         * @param params
         */
        unmergeCells(params) {
            const range = params.context.range;
            const cells = range.targetedNodes(TableCellNode);
            for (const cell of cells) {
                for (const managedCell of cell.managedCells) {
                    managedCell.unmerge();
                }
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the given array of cells forms a rectangle in the table
         * grid.
         *
         * @param cells
         */
        _isRectangle(cells) {
            cells = [...cells];
            // Add managed cells to the list.
            for (const cell of [...cells]) {
                if (cell.managedCells.size) {
                    cells.push(...cell.managedCells);
                }
            }
            cells = distinct(cells);
            // Compute the row/column index extrema.
            const rowIndices = cells.map(cell => cell.rowIndex);
            const columnIndices = cells.map(cell => cell.columnIndex);
            const minRowIndex = Math.min(...rowIndices);
            const minColumnIndex = Math.min(...columnIndices);
            const maxRowIndex = Math.max(...rowIndices);
            const maxColumnIndex = Math.max(...columnIndices);
            // If a cell between the extrema cannot be found in the list, the
            // selected cells do not form a rectangle.
            for (let rowIndex = minRowIndex; rowIndex <= maxRowIndex; rowIndex++) {
                for (let columnIndex = minColumnIndex; columnIndex <= maxColumnIndex; columnIndex++) {
                    const cell = cells.find(cell => {
                        return cell.rowIndex === rowIndex && cell.columnIndex === columnIndex;
                    });
                    if (!cell) {
                        return false;
                    }
                }
            }
            return true;
        }
    }

    var AlignType;
    (function (AlignType) {
        AlignType["LEFT"] = "left";
        AlignType["CENTER"] = "center";
        AlignType["RIGHT"] = "right";
        AlignType["JUSTIFY"] = "justify";
    })(AlignType || (AlignType = {}));
    class Align extends JWPlugin {
        constructor() {
            super(...arguments);
            this.commands = {
                align: {
                    handler: this.align.bind(this),
                },
            };
            this.loadables = {
                components: [
                    {
                        id: 'AlignLeftButton',
                        async render() {
                            return [alignButton(AlignType.LEFT)];
                        },
                    },
                    {
                        id: 'AlignCenterButton',
                        async render() {
                            return [alignButton(AlignType.CENTER)];
                        },
                    },
                    {
                        id: 'AlignRightButton',
                        async render() {
                            return [alignButton(AlignType.RIGHT)];
                        },
                    },
                    {
                        id: 'AlignJustifyButton',
                        async render() {
                            return [alignButton(AlignType.JUSTIFY)];
                        },
                    },
                ],
                componentZones: [
                    ['AlignLeftButton', ['actionables']],
                    ['AlignCenterButton', ['actionables']],
                    ['AlignRightButton', ['actionables']],
                    ['AlignJustifyButton', ['actionables']],
                ],
            };
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return true if the given node has the given alignment style. If no type
         * is passed, return true if the given node has an alignment style at all.
         *
         * @param node
         * @param [type]
         */
        static isAligned(node, type) {
            var _a;
            const align = (_a = node.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.style.get('text-align');
            return type ? align === null || align === void 0 ? void 0 : align.includes(type) : !!align;
        }
        /**
         * Align text.
         */
        align(params) {
            var _a, _b;
            const range = params.context.range;
            const nodes = range.targetedNodes();
            const type = params.type;
            for (const node of nodes.filter(node => !nodes.includes(node.parent))) {
                const alignedAncestor = node.closest(Align.isAligned);
                // Compute current alignment.
                const currentAlignment = (_b = (_a = alignedAncestor === null || alignedAncestor === void 0 ? void 0 : alignedAncestor.modifiers) === null || _a === void 0 ? void 0 : _a.find(Attributes)) === null || _b === void 0 ? void 0 : _b.style.get('text-align');
                if (!alignedAncestor || currentAlignment !== type) {
                    node.modifiers.get(Attributes).style.set('text-align', type.toLowerCase());
                }
            }
        }
    }
    Align.dependencies = [];
    function alignButton(type) {
        function isAligned(node, type) {
            const alignedAncestor = node.closest(Align.isAligned);
            return Align.isAligned(alignedAncestor || node, type);
        }
        const button = new ActionableNode({
            name: 'align' + type,
            label: 'Align ' + type,
            commandId: 'align',
            commandArgs: { type: type },
            selected: (editor) => {
                const range = editor.selection.range;
                const ancestor = range.start.closest(ContainerNode);
                const startIsAligned = ancestor && isAligned(ancestor, type);
                if (!startIsAligned || range.isCollapsed()) {
                    return startIsAligned;
                }
                else {
                    const ancestor = range.end.closest(ContainerNode);
                    return ancestor && isAligned(ancestor, type);
                }
            },
        });
        button.modifiers.append(new Attributes({
            class: 'fa fa-align-' + type + ' fa-fw',
        }));
        return button;
    }

    class Color extends JWPlugin {
        hasColor(color, node) {
            var _a;
            if (color instanceof AbstractNode) {
                node = color;
            }
            const nodeColor = (_a = node.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.style.get(this.styleName);
            if (color instanceof AbstractNode) {
                return !!nodeColor;
            }
            else {
                return nodeColor === color;
            }
        }
        /**
         * Apply the given color to the range.
         *
         * @param params
         */
        color(params) {
            var _a;
            const color = params.color;
            const range = params.context.range;
            if (range.isCollapsed()) {
                // Set the style cache.
                if (!range.modifiers) {
                    range.modifiers = new Modifiers();
                }
                const currentCache = (_a = range.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.style;
                // Convert CssStyle class into a true object for spread operator.
                const currentCacheObject = (currentCache === null || currentCache === void 0 ? void 0 : currentCache.toJSON()) || {};
                range.modifiers.get(Attributes).style = new CssStyle(Object.assign(Object.assign({}, currentCacheObject), { [this.styleName]: color }));
            }
            else {
                let selectedNodes = range.selectedNodes();
                selectedNodes = selectedNodes.filter(node => !selectedNodes.includes(node.parent));
                // Color the highest ancestor.
                for (const node of selectedNodes) {
                    // Color the highest fully selected format if any.
                    const fullySelectedFormats = this._newFormats(node).filter(format => {
                        // This format is started by this node. Now find out if we
                        // end it within the selection.
                        return selectedNodes.includes(this._lastNodeWithFormat(node, format));
                    });
                    if (fullySelectedFormats.length) {
                        const highestFullFormat = fullySelectedFormats.pop();
                        const pairs = selectedNodes.map(selectedNode => {
                            const format = this._findFormat(selectedNode, highestFullFormat);
                            if (format) {
                                return [this._inheritsColorFrom(selectedNode, color), format];
                            }
                        });
                        for (const pair of pairs) {
                            if (pair === null || pair === void 0 ? void 0 : pair[1]) {
                                // Color the formats.
                                if (pair[0]) {
                                    // If the node inherited the color, remove the
                                    // inherited color.
                                    this._removeColor(pair[0]);
                                }
                                this._applyColor(pair[1], color);
                            }
                        }
                    }
                    else if (!this._inheritsColorFrom(node, color)) {
                        // Skip if the node already has the right color, through an
                        // ancestor or a format.
                        this._applyColor(node, color);
                    }
                }
            }
        }
        /**
         * Remove the current color from the range. If the color was applied to
         * an ancestor, apply the default color to its relevant inline descendants.
         *
         * @param params
         */
        uncolor(params) {
            var _a, _b, _c, _d, _e, _f, _g;
            const range = params.context.range;
            const defaultColor = this.configuration.defaultColor;
            const hasColor = this.hasColor.bind(this);
            if (range.isCollapsed()) {
                if (range.start.ancestor(hasColor)) {
                    // Set the color style cache to the default color.
                    if (!range.modifiers) {
                        range.modifiers = new Modifiers();
                    }
                    range.modifiers.get(Attributes).style.set(this.styleName, defaultColor);
                }
                else if ((_b = (_a = range.modifiers) === null || _a === void 0 ? void 0 : _a.find(Attributes)) === null || _b === void 0 ? void 0 : _b.style.length) {
                    // Unset the color style cache.
                    (_c = range.modifiers) === null || _c === void 0 ? void 0 : _c.find(Attributes).style.remove(this.styleName);
                }
            }
            else {
                for (const node of params.context.range.selectedNodes()) {
                    const target = this._nodeOrFirstFormat(node);
                    const currentColor = (_d = target.modifiers.find(Attributes)) === null || _d === void 0 ? void 0 : _d.style.get(this.styleName);
                    if (!currentColor || currentColor === defaultColor || node.ancestor(hasColor)) {
                        // Set the color to the default color.
                        target.modifiers.get(Attributes).style.set(this.styleName, defaultColor);
                    }
                    else {
                        // Remove the color.
                        (_e = target.modifiers.find(Attributes)) === null || _e === void 0 ? void 0 : _e.style.remove(this.styleName);
                    }
                    // Uncolor the children and their formats as well.
                    for (const child of node.children()) {
                        (_f = child.modifiers.find(Attributes)) === null || _f === void 0 ? void 0 : _f.style.remove(this.styleName);
                        if (child instanceof InlineNode) {
                            for (const format of child.modifiers.filter(Format)) {
                                (_g = format.modifiers.find(Attributes)) === null || _g === void 0 ? void 0 : _g.style.remove(this.styleName);
                            }
                        }
                    }
                }
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return the node's first format if any, itself otherwise.
         *
         * @param node
         */
        _nodeOrFirstFormat(node) {
            return node.modifiers.filter(Format)[0] || node;
        }
        /**
         * Return true if all the children of the given node have the given color.
         *
         * @param node
         * @param color
         */
        _isAllColored(node, color) {
            return node.children().every(child => this.hasColor(color, child));
        }
        /**
         * Return the first format that matches the given format, on the given node.
         *
         * @param node
         * @param format
         */
        _findFormat(node, format) {
            return node.modifiers.filter(Format).find(nodeFormat => nodeFormat.isSameAs(format));
        }
        /**
         * Return the last consecutive node to have the given format (assumed to be
         * held by the given node too).
         *
         * @param node
         * @param format
         */
        _lastNodeWithFormat(node, format) {
            let current = node;
            let next = node.nextSibling();
            while (this._findFormat(next, format)) {
                current = next;
                next = current.nextSibling();
            }
            return current;
        }
        /**
         * Return all formats that are started by the given node.
         *
         * @param node
         */
        _newFormats(node) {
            const formats = node.modifiers.filter(Format);
            const previous = node.previousSibling();
            // A new format is starting if the previous sibling doesn't have it.
            if (!previous)
                return formats;
            return formats.filter(format => !this._findFormat(previous, format));
        }
        /**
         * If the given node inherits the given color through an ancestor of a
         * format, or if it simply has it itself, return the node or format it
         * inherits it from.
         *
         * @param node
         * @param color
         */
        _inheritsColorFrom(node, color) {
            if (this.hasColor(color, node)) {
                return node;
            }
            const colorAncestor = node.ancestor(this.hasColor.bind(this));
            if (colorAncestor && this.hasColor(color, colorAncestor)) {
                return colorAncestor;
            }
            for (const format of node.modifiers.filter(Format)) {
                if (this.hasColor(color, format)) {
                    return format;
                }
            }
        }
        _applyColor(node, color) {
            node.modifiers.get(Attributes).style.set(this.styleName, color);
        }
        _removeColor(node) {
            node.modifiers.get(Attributes).style.remove(this.styleName);
        }
    }

    class TextColor extends Color {
        constructor() {
            super(...arguments);
            this.styleName = 'color';
            this.configuration = Object.assign({ defaultColor: 'black' }, this.configuration);
            this.commands = {
                colorText: {
                    handler: this.color,
                },
                uncolorText: {
                    handler: this.uncolor,
                },
            };
            this.loadables = {
                shortcuts: [
                    {
                        pattern: 'CTRL+G',
                        commandId: 'colorText',
                        // TODO: use dialog to get params
                        commandArgs: {
                            color: 'red',
                        },
                    },
                    {
                        pattern: 'CTRL+SHIFT+G',
                        commandId: 'uncolorText',
                    },
                ],
            };
        }
    }

    class BackgroundColor extends Color {
        constructor() {
            super(...arguments);
            this.styleName = 'background-color';
            this.configuration = Object.assign({ defaultColor: 'white' }, this.configuration);
            this.commands = {
                colorBackground: {
                    handler: this.color,
                },
                uncolorBackground: {
                    handler: this.uncolor,
                },
            };
            this.loadables = {
                shortcuts: [
                    {
                        pattern: 'CTRL+H',
                        commandId: 'colorBackground',
                        // TODO: use dialog to get params
                        commandArgs: {
                            color: 'yellow',
                        },
                    },
                    {
                        pattern: 'CTRL+SHIFT+H',
                        commandId: 'uncolorBackground',
                    },
                ],
            };
        }
    }

    class ZoneNode extends ContainerNode {
        constructor(params) {
            super(params);
            this.editable = false;
            this.breakable = false;
            this.managedZones = makeVersionable(params.managedZones);
        }
        get name() {
            return super.name + ': ' + this.managedZones.join();
        }
        hide(child) {
            if (!this.hidden) {
                this.hidden = makeVersionable({});
            }
            this.hidden[child.id] = true;
            return;
        }
        show(child) {
            var _a;
            const id = child.id;
            if ((_a = this.hidden) === null || _a === void 0 ? void 0 : _a[id]) {
                this.hidden[id] = false;
            }
            const parentZone = this.ancestor(ZoneNode);
            if (parentZone) {
                parentZone.show(this);
            }
        }
        _removeAtIndex(index) {
            const child = this.childVNodes[index];
            super._removeAtIndex(index);
            if (this.hidden) {
                delete this.hidden[child.id];
            }
        }
    }

    class LayoutEngine {
        constructor(editor) {
            this.editor = editor;
            this.componentDefinitions = {};
            this.componentZones = {};
            this.root = new ZoneNode({ managedZones: ['root'] });
            this.components = new VersionableObject();
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Automatically intanciate the components in available zones.
         */
        async start() {
            let allZones = [this.root, ...this.root.descendants(ZoneNode)];
            await this.fillZones(allZones);
            allZones = [this.root, ...this.root.descendants(ZoneNode)];
            if (!allZones.find(zone => zone.managedZones.includes('default'))) {
                // Add into the default zone if no valid zone could be found.
                throw new Error('Please define a "default" zone in your template.');
            }
            this.editor.memory.attach(this.root);
            this.editor.memory.attach(this.components);
        }
        /**
         * Hide all components.
         */
        async stop() {
            for (const id in this.components) {
                for (const node of this.components[id]) {
                    const zone = node.ancestor(ZoneNode);
                    if (zone) {
                        zone.hide(node);
                    }
                }
            }
            this.componentDefinitions = {};
            this.componentZones = {};
            this.components = {};
            this.root.empty();
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Load the given Component in this layout engine.
         *
         * @param componentDefinition
         */
        loadComponent(componentDefinition) {
            this.componentDefinitions[componentDefinition.id] = componentDefinition;
        }
        /**
         * Load component zones in this layout engine.
         *
         * @param componentZones
         */
        loadComponentZones(componentZones) {
            Object.assign(this.componentZones, componentZones);
        }
        /**
         * Prepend the given node in the given zone if it exists. Otherwise, add it in
         * the default zone.
         * Return every created instance
         *
         * @param componentId
         * @param zoneId
         * @param props
         */
        async prepend(componentId, zoneId, props) {
            const allZones = [this.root, ...this.root.descendants(ZoneNode)];
            let matchingZones = allZones.filter(node => node.managedZones.includes(zoneId));
            if (!matchingZones.length) {
                matchingZones = allZones.filter(zone => zone.managedZones.includes('default'));
            }
            const componentDefinition = this.componentDefinitions[componentId];
            const newComponents = await this._instantiateComponent(componentDefinition, matchingZones, props, true);
            return this.fillZones(newComponents);
        }
        /**
         * Append the given node in the given zone if it exists. Otherwise, add it in
         * the default zone.
         * Return every created instance
         *
         * @param componentDefinition
         * @param zoneId
         */
        async append(componentId, zoneId, props) {
            const allZones = [this.root, ...this.root.descendants(ZoneNode)];
            let matchingZones = allZones.filter(node => node.managedZones.includes(zoneId));
            if (!matchingZones.length) {
                matchingZones = allZones.filter(zone => zone.managedZones.includes('default'));
            }
            const componentDefinition = this.componentDefinitions[componentId];
            const newComponents = await this._instantiateComponent(componentDefinition, matchingZones, props);
            return this.fillZones(newComponents);
        }
        /**
         *
         * Remove the component identified by the given reference from all zones.
         *
         * @param componentId
         * @param zoneId specifying a zone if it is necessary to remove the
         *      component from this zone only
         */
        async remove(componentId, zoneId) {
            const components = [...(this.components[componentId] || [])];
            const zones = [];
            let component;
            while ((component = components.pop())) {
                // filter by zone if needed
                if (!zoneId ||
                    component.ancestor(ancestor => ancestor instanceof ZoneNode && ancestor.managedZones.includes(zoneId))) {
                    // Remove all instances in the zone children.
                    this._clear(component);
                    // Remove the instance.
                    const zone = component.ancestor(ZoneNode);
                    if (zone && !zones.includes(zone)) {
                        zones.push(zone);
                    }
                    component.remove();
                }
            }
            return zones;
        }
        async clear(zoneId) {
            const zones = this.root
                .descendants(ZoneNode)
                .filter(zone => zone.managedZones.includes(zoneId));
            for (const zone of zones) {
                this._clear(zone);
            }
            return zones;
        }
        /**
         *
         * Show the components corresponding to given ref. Return the updated zones.
         *
         * @param componentId
         */
        async show(componentId) {
            const components = this.components[componentId];
            if (!(components === null || components === void 0 ? void 0 : components.length)) {
                console.warn('No component to show. Prepend or append it in a zone first.');
            }
            else {
                for (const component of components) {
                    const zone = component.ancestor(ZoneNode);
                    zone.show(component);
                }
            }
            return components || [];
        }
        /**
         *
         * Hide the components corresponding to given ref. Return the updated zones.
         *
         * @param componentId
         */
        async hide(componentId) {
            const components = this.components[componentId];
            if (!(components === null || components === void 0 ? void 0 : components.length)) {
                console.warn('No component to hide. Prepend or append it in a zone first.');
            }
            else {
                for (const component of components) {
                    const zone = component.ancestor(ZoneNode);
                    zone.hide(component);
                }
            }
            return components || [];
        }
        /**
         * Check if the string is a zone id where at leat one component will be
         * automatically added.
         *
         * @param zoneId
         */
        hasConfiguredComponents(zoneId) {
            var _a;
            // Check the zone list.
            for (const componentId in this.componentZones) {
                if ((_a = this.componentZones[componentId]) === null || _a === void 0 ? void 0 : _a.includes(zoneId)) {
                    return true;
                }
            }
            // The components all have at least one zone equal to their id.
            return !!this.componentDefinitions[zoneId];
        }
        /**
         * Search into this new nodes if they are some ZoneNode and automatically
         * fill it by the components which match with this zones.
         *
         * @param nodes
         */
        async fillZones(nodes) {
            const newComponents = [];
            const stack = [...nodes];
            while (stack.length) {
                const node = stack.pop();
                const zones = node.descendants(ZoneNode);
                if (node instanceof ZoneNode) {
                    zones.push(node);
                }
                for (const componentId in this.componentDefinitions) {
                    const zoneIds = this.componentZones[componentId];
                    const layoutComponent = this.componentDefinitions[componentId];
                    // Filter the zones corresponding to the given identifier.
                    let matchingZones = zones.filter(zone => (zoneIds && zone.managedZones.find(zoneId => zoneIds.includes(zoneId))) ||
                        zone.managedZones.includes(componentId));
                    const components = this.components[componentId];
                    if (components) {
                        // Excluding the ones that are contained within the given node.
                        // Avoid loop with child in itself.
                        matchingZones = matchingZones.filter(zone => !zone.closest(ancestor => components.includes(ancestor)));
                    }
                    if (matchingZones.length) {
                        stack.push(...(await this._instantiateComponent(layoutComponent, matchingZones)));
                    }
                }
                newComponents.push(node);
            }
            return newComponents;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        async _instantiateComponent(componentDefinition, zones, props, prepend = false) {
            let components = this.components[componentDefinition.id];
            if (!components) {
                // Set the local reference.
                components = new VersionableArray();
                this.components[componentDefinition.id] = components;
            }
            // Add into the container.
            const newComponents = [];
            for (const zone of zones) {
                const nodes = await componentDefinition.render(this.editor, props);
                components.push(...nodes);
                newComponents.push(...nodes);
                if (prepend) {
                    zone.prepend(...nodes);
                }
                else {
                    zone.append(...nodes);
                }
            }
            // Return the components that were newly created.
            return newComponents;
        }
        _clear(component) {
            const zones = component.descendants(ZoneNode);
            if (component instanceof ZoneNode) {
                zones.push(component);
            }
            for (const zone of zones) {
                for (const child of zone.childVNodes) {
                    zone.removeChild(child);
                    for (const id in this.components) {
                        const nodes = this.components[id];
                        if (nodes.includes(child)) {
                            nodes.splice(nodes.indexOf(child), 1);
                            break;
                        }
                    }
                }
            }
        }
    }

    let diffObjectId = 0;
    /**
     * Set the style of an element keeping the "!important" css modifier in the value
     */
    function setStyle(element, name, value) {
        if (value.includes('!important')) {
            element.style.setProperty(name, value.replace('!important', ''), 'important');
        }
        else {
            element.style.setProperty(name, value);
        }
    }
    class DomReconciliationEngine {
        constructor() {
            this._objects = {};
            this._objectIds = new Map();
            this._fromItem = new Map();
            this._fromDom = new Map();
            this._renderedNodes = new Map();
            this._renderedIds = new Set();
            this._locations = new Map();
            this._items = new Map();
            // The diff is filled in update when we compare the new domObject with the
            // old one, and the diff are consumed when we redraw the node.
            this._diff = {};
            this._rendererTreated = new Set();
            this._releasedItems = new Set();
            this._domUpdated = new Set();
            this._domNodesToRedraw = new Set();
        }
        update(updatedNodes, renderings, locations, from, domNodesToRedraw = new Set()) {
            var _a;
            const renderedSet = new Set();
            for (const node of updatedNodes) {
                const rendering = renderings.get(node);
                if (rendering) {
                    renderedSet.add(rendering);
                }
            }
            const rendered = [...renderedSet];
            this._domNodesToRedraw = new Set(domNodesToRedraw);
            // Found the potential old values (they could become children of the current node).
            // In old values the renderer are may be merge some object, we want to found the
            // children object in old value to campare it with the newest.
            const mapOldIds = new Map();
            const domObjects = [];
            for (const domObject of rendered) {
                if (this._rendererTreated.has(domObject)) {
                    continue;
                }
                domObjects.push(domObject);
                let oldObjects = mapOldIds.get(domObject);
                if (!oldObjects) {
                    this._addLocations(domObject, locations, from);
                    oldObjects = new Set();
                    mapOldIds.set(domObject, oldObjects);
                }
                const nodes = this._items.get(domObject);
                for (const linkedNode of nodes) {
                    if (linkedNode instanceof AbstractNode) {
                        const ids = this._renderedNodes.get(linkedNode);
                        if (ids) {
                            for (const id of ids) {
                                if (!oldObjects.has(id)) {
                                    const object = this._objects[id].object;
                                    this._rendererTreated.delete(object);
                                    this._objectIds.delete(object);
                                    this._renderedIds.delete(id);
                                    oldObjects.add(id);
                                }
                            }
                        }
                    }
                }
                this._rendererTreated.delete(domObject);
                this._objectIds.delete(domObject);
            }
            // Make diff.
            for (const domObject of domObjects) {
                if (!this._objectIds.has(domObject)) {
                    const items = this._items.get(domObject);
                    const node = items.find(node => node instanceof AbstractNode);
                    const oldRefId = this._fromItem.get(node);
                    const oldIds = mapOldIds.get(domObject);
                    const id = this._diffObject(renderings, domObject, items, mapOldIds);
                    this._renderedIds.add(id);
                    const parentObject = (_a = this._objects[this._objects[id].parent]) === null || _a === void 0 ? void 0 : _a.object;
                    if (oldRefId !== id ||
                        !parentObject ||
                        !this._rendererTreated.has(parentObject) ||
                        oldIds.size > 1) {
                        // If the rendering change, we must check if we redraw the parent.
                        const ancestorWithRendering = node.ancestor(ancestor => !!this._fromItem.get(ancestor));
                        if (!updatedNodes.includes(ancestorWithRendering)) {
                            const ancestorObjectId = this._fromItem.get(ancestorWithRendering);
                            if (ancestorObjectId && !this._diff[ancestorObjectId]) {
                                const parentObject = this._objects[ancestorObjectId];
                                const nodes = this._items.get(parentObject.object);
                                mapOldIds.set(parentObject.object, new Set([ancestorObjectId]));
                                this._rendererTreated.delete(parentObject.object);
                                this._diffObject(renderings, parentObject.object, nodes, mapOldIds);
                            }
                        }
                    }
                }
            }
            const diffs = Object.values(this._diff);
            // Prepare path for fragment insertion in the dom.
            const objectsPath = {};
            for (const diff of diffs) {
                const object = this._objects[diff.id];
                const nodes = diff.dom.length ? diff.dom : this._getchildrenDomNodes(diff.id);
                const path = [];
                let parent = this._objects[object.parent];
                while (parent && !parent.object.tag) {
                    parent = this._objects[parent.parent];
                }
                if (!parent) {
                    let domNode = nodes[0];
                    while (domNode && domNode.parentElement && domNode !== document.body) {
                        path.push([
                            domNode.parentElement,
                            [].indexOf.call(domNode.parentElement.childNodes, domNode),
                        ]);
                        domNode = domNode.parentElement;
                    }
                }
                objectsPath[diff.id] = path;
            }
            // Select removed objects.
            const removeObjects = [];
            for (const diff of diffs) {
                for (const id of diff.removedChildren) {
                    const object = this._objects[id];
                    if (!object.parent) {
                        removeObjects.push(id);
                    }
                }
            }
            for (const id of removeObjects) {
                const object = this._objects[id];
                for (const childId of object.children) {
                    const child = this._objects[childId];
                    if ((!child.parent || child.parent === id) && !removeObjects.includes(childId)) {
                        object.parent = null;
                        removeObjects.push(childId);
                    }
                }
            }
            // Remove referencies to removed objects.
            const allOldDomNodes = [];
            for (const id of removeObjects) {
                const old = this._objects[id];
                if (typeof old.object.detach === 'function') {
                    old.object.detach(...old.dom);
                }
                for (const node of this._locations.get(old.object) || []) {
                    if (this._fromItem.get(node) === id) {
                        this._fromItem.delete(node);
                    }
                }
                for (const node of this._items.get(old.object) || []) {
                    const ids = this._renderedNodes.get(node);
                    if (ids && ids.has(id)) {
                        this._renderedNodes.delete(node);
                    }
                }
                if (old.dom) {
                    for (const domNode of old.dom) {
                        if (this._fromDom.get(domNode) === id) {
                            this._fromDom.delete(domNode);
                            this._domNodesToRedraw.add(domNode);
                            if (isInstanceOf(domNode, Element)) {
                                domNode.remove();
                            }
                            else {
                                allOldDomNodes.push(domNode);
                            }
                        }
                    }
                }
                delete this._diff[id];
                delete this._objects[id];
                this._renderedIds.delete(id);
                this._items.delete(old.object);
                this._locations.delete(old.object);
                this._rendererTreated.delete(old.object);
                const i = diffs.findIndex(diff => diff.id === id);
                if (i !== -1) {
                    diffs.splice(i, 1);
                }
            }
            // Add locations.
            for (const diff of diffs) {
                const object = this._objects[diff.id];
                const nodes = from.get(object.object);
                if (nodes) {
                    for (const node of nodes) {
                        this._fromItem.set(node, diff.id);
                    }
                }
            }
            // Unvalidate object linked to domNodesToRedraw;
            for (const domNode of domNodesToRedraw) {
                const id = this._fromDom.get(domNode);
                if (id && !removeObjects.includes(id)) {
                    if (this._diff[id]) {
                        this._diff[id].askCompleteRedrawing = true;
                    }
                    else if (this._objects[id]) {
                        const object = this._objects[id];
                        const domObject = object.object;
                        if (typeof domObject.detach === 'function') {
                            domObject.detach(...object.dom);
                        }
                        this._diff[id] = {
                            id: id,
                            attributes: {},
                            style: {},
                            classList: {},
                            dom: object.dom,
                            parentDomNode: object.parentDomNode,
                            removedChildren: [],
                            askCompleteRedrawing: true,
                        };
                        diffs.push(this._diff[id]);
                    }
                }
                allOldDomNodes.push(domNode);
                allOldDomNodes.push(...domNode.childNodes);
            }
            // Select all dom nodes.
            for (const diff of diffs) {
                allOldDomNodes.push(...diff.dom);
            }
            // Sort the diff by ancestors.
            diffs.sort((da, db) => {
                let aLen = 0;
                let a = this._objects[da.id];
                while (a === null || a === void 0 ? void 0 : a.parent) {
                    aLen++;
                    a = this._objects[a.parent];
                }
                let bLen = 0;
                let b = this._objects[db.id];
                while (b === null || b === void 0 ? void 0 : b.parent) {
                    bLen++;
                    b = this._objects[b.parent];
                }
                return aLen - bLen;
            });
            // Redraw all objects.
            const objectToInsert = [];
            for (const diff of diffs) {
                if (this._updateDom(diff.id)) {
                    objectToInsert.push(diff.id);
                }
            }
            // Insert object dom nodes which don't have direct object with nodeName
            // and not added by the updateDom because his parent have no diff.
            for (const id of objectToInsert) {
                const path = objectsPath[id] || [];
                const item = this._objects[id];
                let parent = this._objects[item.parent] || item;
                while (!parent.object.tag && parent.parent) {
                    parent = this._objects[parent.parent];
                }
                const parentDomNode = parent.dom[0];
                const domNodes = [];
                for (const childId of parent.children) {
                    domNodes.push(...this._getDomChild(childId, parentDomNode));
                }
                if (domNodes.length) {
                    if (parent !== item && parent.object.tag) {
                        this._insertDomChildren(domNodes, parentDomNode, parentDomNode.firstChild);
                    }
                    else {
                        let parentDomNode;
                        let firstDomNode;
                        while (!parentDomNode && path.length) {
                            const pathItem = path.shift();
                            const isAvailableParent = pathItem[0].ownerDocument.contains(pathItem[0]) &&
                                !domNodes.find(domNode => pathItem[0] === domNode || domNode.contains(pathItem[0]));
                            if (isAvailableParent) {
                                parentDomNode = pathItem[0];
                                firstDomNode = parentDomNode.childNodes[pathItem[1]];
                            }
                        }
                        if (parentDomNode) {
                            this._insertDomChildren(domNodes, parentDomNode, firstDomNode);
                        }
                    }
                }
            }
            // Clean/remove unused dom nodes.
            for (const domNode of allOldDomNodes) {
                if (!this._fromDom.get(domNode) && domNode.parentNode) {
                    domNode.parentNode.removeChild(domNode);
                }
            }
            // Call attach methods for the changed domNodes.
            for (const id of this._domUpdated) {
                const object = this._objects[id];
                if (typeof (object === null || object === void 0 ? void 0 : object.object.attach) === 'function') {
                    object.object.attach(...object.dom);
                }
            }
            this._domUpdated.clear();
            this._releasedItems.clear();
            this._domNodesToRedraw.clear();
        }
        /**
         * Return the VNodes linked in renderng to the given VNode.
         *
         * @param node
         */
        getRenderedWith(node) {
            const id = this._fromItem.get(node);
            if (id) {
                const object = this._objects[id];
                const locations = this._locations.get(object.object);
                return [...(locations.length ? locations : this._items.get(object.object))];
            }
            return [];
        }
        /**
         * Return the VNode(s) corresponding to the given DOM Node.
         *
         * @param domNode
         */
        fromDom(domNode) {
            let object;
            const nodes = [];
            while (!object && domNode) {
                object = this._objects[this._fromDom.get(domNode)];
                let items = [];
                while (object && items && !items.length) {
                    items = this._locations.get(object.object);
                    if (!(items === null || items === void 0 ? void 0 : items.length)) {
                        items = this._items.get(object.object);
                    }
                    object = this._objects[object.parent];
                }
                if (items === null || items === void 0 ? void 0 : items.length) {
                    for (const item of items) {
                        if (item instanceof AbstractNode) {
                            nodes.push(item);
                        }
                    }
                }
                else {
                    if (isInstanceOf(domNode, ShadowRoot)) {
                        domNode = domNode.host;
                    }
                    else if (isInstanceOf(domNode, Document)) {
                        domNode = domNode.defaultView.frameElement;
                    }
                    else {
                        domNode = domNode.parentNode;
                    }
                }
            }
            return [...new Set(nodes)];
        }
        /**
         * Return the DOM Node corresponding to the given VNode.
         *
         * @param node
         */
        toDom(node) {
            const id = this._fromItem.get(node);
            const object = this._objects[id];
            if (!object) {
                return [];
            }
            else if (object.dom.length) {
                return [...object.dom];
            }
            else {
                return this._getchildrenDomNodes(id);
            }
        }
        /**
         * Return a position in the VNodes as a tuple containing a reference
         * node and a relative position with respect to this node ('BEFORE' or
         * 'AFTER'). The position is always given on the leaf.
         *
         * @param container
         * @param offset
         */
        locate(domNode, domOffset) {
            let forceAfter = false;
            let forcePrepend = false;
            let container = domNode;
            let offset = domOffset;
            // When targetting the end of a node, the DOM gives an offset that is
            // equal to the length of the container. In order to retrieve the last
            // descendent, we need to make sure we target an existing node, ie. an
            // existing index.
            if (!isInstanceOf(domNode, Text) && offset >= nodeLength(container)) {
                forceAfter = true;
                offset = container.childNodes.length - 1;
                while (container.childNodes.length) {
                    container = container.childNodes[offset];
                    offset = container.childNodes.length - 1;
                }
            }
            // We are targetting the deepest descendant.
            while (container.childNodes[offset]) {
                if (nodeName(container.childNodes[offset]) === 'BR' &&
                    !container.childNodes[offset].nextSibling) {
                    // Target the last br in a container.
                    forceAfter = true;
                }
                if (forceAfter) {
                    container = container.childNodes[nodeLength(container) - 1];
                    offset = nodeLength(container) - 1;
                }
                else {
                    container = container.childNodes[offset];
                    offset = 0;
                }
            }
            // Search to domObject coresponding to the dom element.
            let object;
            while (!object) {
                const id = this._fromDom.get(container);
                if (id) {
                    object = this._objects[id];
                    if (!object) {
                        throw new Error('Dom location altered.');
                    }
                }
                else if (container.previousSibling) {
                    forceAfter = true;
                    container = container.previousSibling;
                    offset = nodeLength(container) - 1;
                }
                else if (container.parentNode) {
                    forcePrepend = true;
                    offset = [].indexOf.call(container.parentNode.childNodes, container);
                    container = container.parentNode;
                }
                else {
                    return;
                }
            }
            while (object.children[offset]) {
                const childId = object.children[offset];
                object = this._objects[childId];
                if (forceAfter && this._locations.get(object.object).length) {
                    offset = this._locations.get(object.object).length - 1;
                }
                else {
                    offset = 0;
                }
            }
            // For domObjectText, add the previous text length as offset.
            if (object.object.text && isInstanceOf(domNode, Text)) {
                const texts = object.dom;
                let index = texts.indexOf(domNode);
                while (index > 0) {
                    index--;
                    offset += texts[index].textContent.length;
                }
            }
            let objectChild = object;
            while (!this._locations.get(object.object).length) {
                const parent = this._objects[object.parent];
                const index = parent.children.indexOf(object.id);
                if (index > 0) {
                    object = this._objects[parent.children[index - 1]];
                    offset = object.children.length - 1;
                    const locations = this._locations.get(object.object);
                    if (locations.length) {
                        return [locations[locations.length - 1], RelativePosition.AFTER];
                    }
                }
                else {
                    offset = parent.children.indexOf(objectChild.id);
                    object = parent;
                    objectChild = object;
                    forcePrepend = true;
                    const locations = this._locations.get(parent.object);
                    if (locations.length === 1) {
                        offset = 0;
                        if (offset > parent.children.length / 2) {
                            forceAfter = true;
                        }
                    }
                }
            }
            const locations = this._locations.get(object.object);
            if (!locations[offset]) {
                return [locations[locations.length - 1], RelativePosition.AFTER];
            }
            else if (forcePrepend && locations[offset] instanceof ContainerNode) {
                return [locations[offset], RelativePosition.INSIDE];
            }
            else if (forceAfter) {
                return [locations[offset], RelativePosition.AFTER];
            }
            else {
                return [locations[offset], RelativePosition.BEFORE];
            }
        }
        /**
         * Clear the map of all correspondances.
         *
         */
        clear() {
            for (const objectMap of Object.values(this._objects)) {
                if (typeof objectMap.object.detach === 'function') {
                    objectMap.object.detach(...objectMap.dom);
                }
            }
            for (const fromDom of this._fromDom) {
                const domNode = fromDom[0];
                if (domNode.parentNode) {
                    domNode.parentNode.removeChild(domNode);
                }
            }
            this._objects = {};
            this._fromItem.clear();
            this._fromDom.clear();
            this._renderedNodes.clear();
            this._renderedIds.clear();
            this._objectIds.clear();
            this._locations.clear();
            this._items.clear();
            this._rendererTreated.clear();
            this._domUpdated.clear();
        }
        /**
         * Return the location in the DOM corresponding to the location in the
         * VDocument of the given VNode. The location in the DOM is expressed as a
         * tuple containing a reference Node and a relative position with respect to
         * the reference Node.
         *
         * @param node
         */
        getLocations(node) {
            let reference = node.previousSibling();
            let position = RelativePosition.AFTER;
            if (!reference || reference.hasChildren()) {
                reference = node.nextSibling();
                position = RelativePosition.BEFORE;
                if (reference) {
                    reference = reference.firstLeaf();
                }
            }
            if (!reference) {
                reference = node.parent;
                position = RelativePosition.INSIDE;
                if (!reference) {
                    return;
                }
            }
            let object;
            let locations;
            // use the location
            let domNodes;
            let isText = true;
            const alreadyCheck = new Set();
            while (!domNodes && reference) {
                alreadyCheck.add(reference);
                const ids = this._renderedNodes.get(reference);
                if (ids) {
                    for (let id of ids) {
                        object = this._objects[id];
                        locations = this._locations.get(object.object);
                        if (!locations.includes(reference)) {
                            let hasLocate;
                            const ids = [id];
                            while (ids.length && (!hasLocate || position === RelativePosition.AFTER)) {
                                const id = ids.pop();
                                const child = this._objects[id];
                                if (this._locations.get(child.object).includes(reference)) {
                                    hasLocate = id;
                                }
                                if (child.children) {
                                    ids.push(...[...child.children].reverse());
                                }
                            }
                            id = hasLocate;
                            object = this._objects[id];
                            locations = this._locations.get(object.object);
                        }
                        if (object.dom.length) {
                            if (!domNodes)
                                domNodes = [];
                            domNodes.push(...object.dom);
                        }
                        else {
                            if (!domNodes)
                                domNodes = [];
                            domNodes.push(...this._getchildrenDomNodes(id));
                        }
                        if (domNodes.length && (object.object.tag || object.object.dom)) {
                            isText = false;
                        }
                    }
                }
                if (!(domNodes === null || domNodes === void 0 ? void 0 : domNodes.length) || !domNodes[0].parentNode) {
                    const next = reference.nextLeaf();
                    if (next && !alreadyCheck.has(next)) {
                        position = RelativePosition.BEFORE;
                        reference = next;
                    }
                    else {
                        position = RelativePosition.INSIDE;
                        reference = reference.parent;
                    }
                    domNodes = null;
                }
            }
            let domNode;
            let offset = position === RelativePosition.AFTER
                ? locations.lastIndexOf(reference)
                : locations.indexOf(reference);
            if (isText) {
                let index = 0;
                while (offset >= domNodes[index].textContent.length) {
                    offset -= domNodes[index].textContent.length;
                    if (domNodes[index + 1]) {
                        index++;
                    }
                    else {
                        break;
                    }
                }
                domNode = domNodes[index];
                if (position === RelativePosition.AFTER) {
                    // Increment the offset to be positioned after the reference node.
                    offset += 1;
                }
            }
            else if (position === RelativePosition.INSIDE) {
                domNode = domNodes[offset];
                offset = 0;
            }
            else {
                if (position === RelativePosition.AFTER) {
                    domNode = domNodes[domNodes.length - 1];
                }
                else {
                    domNode = domNodes[0];
                }
                if (isInstanceOf(domNode, Text)) {
                    offset = domNode.textContent.length;
                }
                else {
                    // Char nodes have their offset in the corresponding text nodes
                    // registered in the map via `set` but void nodes don't. Their
                    // location need to be computed with respect to their parents.
                    const container = domNode.parentNode;
                    offset = Array.prototype.indexOf.call(container.childNodes, domNode);
                    domNode = container;
                    if (position === RelativePosition.AFTER) {
                        // Increment the offset to be positioned after the reference node.
                        offset += 1;
                    }
                }
            }
            return [domNode, offset];
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        // eslint-disable-next-line max-params
        _diffObject(nodeToDomObject, domObject, fromNodes, mapOldIds, childrenMapping) {
            let oldIds = mapOldIds.get(domObject);
            const items = this._items.get(domObject);
            if (!oldIds) {
                oldIds = new Set();
                if (items) {
                    for (const item of items) {
                        const ids = this._renderedNodes.get(item);
                        if (ids) {
                            for (const id of ids) {
                                if (!this._diff[id]) {
                                    oldIds.add(id);
                                }
                            }
                        }
                    }
                }
            }
            let hasChanged = false;
            if (oldIds.size) {
                for (const id of [...oldIds]) {
                    const old = this._objects[id];
                    if (!old || this._rendererTreated.has(old.object)) {
                        oldIds.delete(id);
                    }
                }
                if (!childrenMapping) {
                    childrenMapping = this._diffObjectAssociateChildrenMap(domObject, oldIds);
                }
                hasChanged = oldIds.size !== 1;
            }
            let id = childrenMapping === null || childrenMapping === void 0 ? void 0 : childrenMapping.get(domObject);
            if (id) {
                oldIds.add(id);
            }
            let old = this._objects[id];
            if (old && !this._rendererTreated.has(old.object)) {
                childrenMapping.delete(domObject);
                this._rendererTreated.add(old.object);
            }
            else {
                old = null;
                hasChanged = true;
                diffObjectId++;
                id = diffObjectId;
            }
            this._rendererTreated.add(domObject);
            this._objectIds.set(domObject, id);
            const removedChildren = [];
            const diffAttributes = {};
            const diffStyle = {};
            const diffClassList = {};
            const nodes = this._locations.get(domObject) || [];
            const attributes = {};
            const children = [];
            let domNodes = [];
            let allDomNodes = [];
            let domNodesChildren;
            let domNodesChildrenProcess;
            const oldChildren = (old === null || old === void 0 ? void 0 : old.children) || [];
            const newChildren = domObject.children || [];
            if (domObject.dom) {
                hasChanged = true;
                domNodes = domObject.dom;
                domNodesChildrenProcess = [];
                const placeholders = {};
                let havePlaceholder = false;
                for (const domNode of domNodes) {
                    if (isInstanceOf(domNode, Element)) {
                        if (nodeName(domNode) === 'JW-DOMOBJECT-VNODE') {
                            havePlaceholder = true;
                            placeholders[domNode.id] = domNode;
                        }
                        else {
                            const childNodes = domNode.shadowRoot
                                ? domNode.shadowRoot.querySelectorAll('jw-domobject-vnode')
                                : domNode.querySelectorAll('jw-domobject-vnode');
                            for (const dom of childNodes) {
                                havePlaceholder = true;
                                placeholders[dom.id] = dom;
                            }
                        }
                    }
                }
                if (havePlaceholder) {
                    const placeholderVNodes = [];
                    const allNodes = fromNodes.filter(item => item instanceof AbstractNode);
                    for (const node of allNodes) {
                        allNodes.push(...node.childVNodes);
                    }
                    for (const node of allNodes) {
                        const placeholder = placeholders[node.id];
                        if (placeholder) {
                            placeholderVNodes.push([placeholder, node]);
                        }
                    }
                    placeholderVNodes.reverse();
                    for (const [placeholder, node] of placeholderVNodes) {
                        let child;
                        let index = domNodes.indexOf(placeholder);
                        if (index !== -1) {
                            if (index !== domNodes.length - 1) {
                                // Eg: [PLACEHOLDER, PLACEHOLDER, <div></div>]
                                child = [domNodes[index + 1], RelativePosition.BEFORE, [node]];
                            }
                            else {
                                // Eg: [<div></div>, PLACEHOLDER, PLACEHOLDER]
                                while (!child && index > 0) {
                                    index--;
                                    if (nodeName(domNodes[index]) !== 'JW-DOMOBJECT-VNODE') {
                                        child = [domNodes[index], RelativePosition.AFTER, [node]];
                                    }
                                }
                            }
                            domNodes.splice(domNodes.indexOf(placeholder), 1);
                        }
                        else if (placeholder.nextSibling) {
                            // Eg: [<div>PLACEHOLDER<i></i></div>]
                            child = [placeholder.nextSibling, RelativePosition.BEFORE, [node]];
                        }
                        else if (placeholder.parentNode) {
                            // Eg: [<div><i></i>PLACEHOLDER</div>]
                            child = [placeholder.parentNode, RelativePosition.INSIDE, [node]];
                        }
                        if (child) {
                            const next = domNodesChildrenProcess.find(next => next[0] === child[0] && next[1] === child[1]);
                            if (next) {
                                next[2].unshift(node);
                            }
                            else {
                                domNodesChildrenProcess.push(child);
                            }
                        }
                        newChildren.push(node);
                        placeholder.remove();
                    }
                    if (!domNodesChildrenProcess.length) {
                        // Every domNodes are placeholder. It's like children only.
                        domNodesChildrenProcess = null;
                    }
                }
                // Add all nodes as mapping to avoid association by children.
                allDomNodes = [];
                const allNodes = [...domNodes];
                while (allNodes.length) {
                    const domNode = allNodes.pop();
                    allDomNodes.push(domNode);
                    if (isInstanceOf(domNode, Element)) {
                        allNodes.push(...domNode.childNodes);
                    }
                }
            }
            for (const child of newChildren) {
                let childId;
                if (child instanceof AbstractNode) {
                    const domObject = nodeToDomObject.get(child);
                    let oldChildId = this._objectIds.get(domObject) || this._fromItem.get(child);
                    if (!oldChildId) {
                        const oldChildIds = this._renderedNodes.get(child);
                        if (oldChildIds === null || oldChildIds === void 0 ? void 0 : oldChildIds.size) {
                            oldChildId = [...oldChildIds][0];
                        }
                    }
                    const nodes = this._items.get(domObject);
                    if (this._rendererTreated.has(domObject)) {
                        childId = oldChildId;
                    }
                    else if (!domObject) {
                        if (oldChildId) {
                            childId = oldChildId;
                        }
                        else {
                            console.error('No rendering for the node(' + child.id + '): ' + child.name);
                        }
                    }
                    else {
                        childId = this._diffObject(nodeToDomObject, domObject, nodes, mapOldIds);
                        this._renderedIds.add(childId);
                    }
                }
                else if (this._rendererTreated.has(child)) {
                    childId = this._objectIds.get(child);
                }
                else {
                    childId = this._diffObject(nodeToDomObject, child, nodes, mapOldIds, childrenMapping);
                }
                if (childId) {
                    this._objects[childId].parent = id;
                    if (!children.includes(childId)) {
                        children.push(childId);
                    }
                }
            }
            if (children.join() !== oldChildren.join()) {
                hasChanged = true;
                for (const childId of oldChildren) {
                    if (!children.includes(childId)) {
                        if (this._objects[childId].parent === id) {
                            this._objects[childId].parent = null;
                        }
                        removedChildren.push(childId);
                    }
                }
            }
            if (domNodesChildrenProcess) {
                domNodesChildren = [];
                for (const [ref, position, nodes] of domNodesChildrenProcess) {
                    const nodeIds = nodes
                        .map(node => this._fromItem.get(node))
                        .filter(id => id);
                    domNodesChildren.push([ref, position, nodeIds]);
                }
            }
            if (!domNodes.length && domObject.tag) {
                if (!old || domObject.tag !== old.object.tag) {
                    hasChanged = true;
                }
                // Update attributes.
                const newAttributes = domObject.attributes || {};
                const oldAttributes = (old === null || old === void 0 ? void 0 : old.object.attributes) || {};
                for (const name in oldAttributes) {
                    if (!newAttributes[name]) {
                        hasChanged = true;
                        if (name === 'style') {
                            for (const key in oldAttributes[name]) {
                                diffStyle[key] = null;
                            }
                        }
                        else if (name === 'class') {
                            for (const className of oldAttributes[name]) {
                                diffClassList[className] = false;
                            }
                        }
                        else {
                            diffAttributes[name] = null;
                        }
                    }
                }
                for (const name in newAttributes) {
                    if (name === 'style') {
                        const newStyle = newAttributes[name];
                        const oldStyle = oldAttributes[name];
                        if (oldStyle) {
                            for (const key in oldStyle) {
                                if (!newStyle[key]) {
                                    hasChanged = true;
                                    diffStyle[key] = null;
                                }
                            }
                        }
                        for (const key in newStyle) {
                            if (newStyle[key] !== (oldStyle === null || oldStyle === void 0 ? void 0 : oldStyle[key])) {
                                hasChanged = true;
                                diffStyle[key] = newStyle[key];
                            }
                        }
                    }
                    else if (name === 'class') {
                        const newClassNames = newAttributes[name];
                        const oldClassNames = oldAttributes[name];
                        if (oldClassNames) {
                            for (const className of oldClassNames) {
                                if (className && !newClassNames.has(className)) {
                                    hasChanged = true;
                                    diffClassList[className] = false;
                                }
                            }
                        }
                        for (const className of newClassNames) {
                            if (className && !(oldClassNames === null || oldClassNames === void 0 ? void 0 : oldClassNames.has(className))) {
                                hasChanged = true;
                                diffClassList[className] = true;
                            }
                        }
                    }
                    else {
                        const value = newAttributes[name];
                        if (value !== oldAttributes[name]) {
                            hasChanged = true;
                            diffAttributes[name] = value;
                        }
                    }
                    attributes[name] = newAttributes[name];
                }
            }
            else if (!domNodes.length && domObject.text) {
                if (!old || domObject.text !== old.object.text) {
                    hasChanged = true;
                }
            }
            else if (!domNodes.length && (old === null || old === void 0 ? void 0 : old.dom.length)) {
                hasChanged = true;
            }
            // remove old referencies
            const oldIdsToRelease = [];
            if (items && oldIds.size) {
                oldIdsToRelease.push(...oldIds);
            }
            if (old) {
                oldIdsToRelease.push(old.id);
                if (typeof old.object.detach === 'function') {
                    old.object.detach(...old.dom);
                }
            }
            for (const id of oldIdsToRelease) {
                const old = this._objects[id];
                for (const item of this._items.get(old.object)) {
                    const ids = this._renderedNodes.get(item);
                    if (ids && ids.has(id)) {
                        if (!this._releasedItems.has(item)) {
                            this._releasedItems.add(item);
                            this._renderedNodes.delete(item);
                        }
                    }
                }
            }
            // Add new referencies.
            for (const node of nodes) {
                this._fromItem.set(node, id);
            }
            if (items) {
                for (const item of new Set([...items, ...this._items.get(domObject)])) {
                    let ids = this._renderedNodes.get(item);
                    if (!ids) {
                        ids = new Set();
                        this._renderedNodes.set(item, ids);
                    }
                    ids.add(id);
                }
            }
            if (!this._locations.get(domObject)) {
                this._locations.set(domObject, []);
            }
            this._objects[id] = {
                id: id,
                object: domObject,
                parent: old === null || old === void 0 ? void 0 : old.parent,
                children: children,
                dom: domNodes,
                domNodes: allDomNodes,
                domNodesChildren: domNodesChildren,
                parentDomNode: old === null || old === void 0 ? void 0 : old.parentDomNode,
            };
            if (hasChanged) {
                const oldDomNodes = (old === null || old === void 0 ? void 0 : old.dom) ? [...old.dom] : [];
                if (oldIds) {
                    for (const id of oldIds) {
                        for (const domNode of this._objects[id].dom) {
                            if (!oldDomNodes.includes(domNode)) {
                                oldDomNodes.push(domNode);
                            }
                        }
                    }
                }
                this._diff[id] = {
                    id: id,
                    attributes: diffAttributes,
                    style: diffStyle,
                    classList: diffClassList,
                    dom: oldDomNodes,
                    parentDomNode: old === null || old === void 0 ? void 0 : old.parentDomNode,
                    removedChildren: removedChildren,
                };
            }
            else {
                this._objects[id].dom = old.dom;
                if (typeof domObject.attach === 'function') {
                    domObject.attach(...old.dom);
                }
            }
            return id;
        }
        _diffObjectAssociateChildrenMap(objectA, objectIdsB) {
            const map = new Map();
            if (!objectIdsB.size) {
                return map;
            }
            const allChildrenA = [objectA];
            for (const domObject of allChildrenA) {
                if (domObject.children) {
                    for (const child of domObject.children) {
                        if (!(child instanceof AbstractNode)) {
                            allChildrenA.push(child);
                        }
                    }
                }
            }
            const allChildrenB = [...objectIdsB];
            for (const id of allChildrenB) {
                const objB = this._objects[id];
                this._rendererTreated.delete(objB.object);
                if (objB === null || objB === void 0 ? void 0 : objB.children) {
                    for (const id of objB.children) {
                        if (this._objects[id] && !this._renderedIds.has(id)) {
                            allChildrenB.push(id);
                        }
                    }
                }
            }
            const mapRatios = this._diffObjectAssociateChildren(allChildrenA, allChildrenB);
            mapRatios.sort((a, b) => b[0] - a[0]);
            const used = new Set();
            for (const [, childRef, id] of mapRatios) {
                if (!map.get(childRef) && !used.has(id)) {
                    map.set(childRef, id);
                    used.add(id);
                }
            }
            return map;
        }
        _diffObjectAssociateChildren(arrayA, arrayB) {
            const mapRatios = [];
            for (const objectA of arrayA) {
                for (const idB of arrayB) {
                    const itemB = this._objects[idB];
                    const objectB = itemB.object;
                    let currentRatio = 0;
                    if (objectA.tag) {
                        if (objectA.tag === objectB.tag) {
                            const attrA = objectA.attributes || {};
                            const attrB = objectB.attributes;
                            // add some points for attributes matching
                            let max = 0;
                            let same = 0;
                            for (const name in attrA) {
                                if (name === 'style') {
                                    const styleA = attrA[name];
                                    const styleB = attrB === null || attrB === void 0 ? void 0 : attrB[name];
                                    if (styleA) {
                                        for (const key in styleA) {
                                            max++;
                                            if (styleA[key] === (styleB === null || styleB === void 0 ? void 0 : styleB[key])) {
                                                same++;
                                            }
                                        }
                                    }
                                }
                                else if (name === 'class') {
                                    const classA = attrA[name];
                                    const classB = attrB === null || attrB === void 0 ? void 0 : attrB[name];
                                    if (classA) {
                                        for (const c of classA) {
                                            max++;
                                            if (classB === null || classB === void 0 ? void 0 : classB.has(c)) {
                                                same++;
                                            }
                                        }
                                    }
                                }
                                else {
                                    max++;
                                    if (attrA[name] === (attrB === null || attrB === void 0 ? void 0 : attrB[name])) {
                                        same++;
                                    }
                                }
                            }
                            for (const name in attrB) {
                                if (name === 'style') {
                                    const styleA = attrA === null || attrA === void 0 ? void 0 : attrA[name];
                                    const styleB = attrB[name];
                                    if (styleB) {
                                        for (const key in styleB) {
                                            if (!styleA || !(key in styleA)) {
                                                max++;
                                            }
                                        }
                                    }
                                }
                                else if (name === 'class') {
                                    const classA = attrA === null || attrA === void 0 ? void 0 : attrA[name];
                                    const classB = attrB[name];
                                    if (classB) {
                                        for (const c of classB) {
                                            if (!(classA === null || classA === void 0 ? void 0 : classA.has(c))) {
                                                max++;
                                            }
                                        }
                                    }
                                }
                                else if (!attrA || !(name in attrA)) {
                                    max++;
                                }
                            }
                            currentRatio = 1 + same / (max || 1);
                        }
                    }
                    else if (objectA.text) {
                        if (objectB.text) {
                            currentRatio = 1;
                        }
                    }
                    else if (objectA.dom) {
                        if (itemB.dom.length && !objectB.tag && !objectB.text) {
                            currentRatio = 1;
                        }
                    }
                    else if (objectA.children) {
                        if (itemB.children && !objectB.text && !objectB.tag) {
                            currentRatio = 1;
                        }
                    }
                    if (currentRatio >= 1) {
                        // The best have at leat on node in common or the twice does not have node.
                        const itemsA = this._items.get(objectA);
                        const itemsB = this._items.get(objectB);
                        // Some points for children nodes.
                        let matchNode = 0;
                        let maxNode = 0;
                        for (const node of itemsA) {
                            if (node instanceof AbstractNode) {
                                maxNode++;
                                if (itemsB.includes(node)) {
                                    matchNode++;
                                }
                            }
                        }
                        for (const node of itemsB) {
                            if (node instanceof AbstractNode) {
                                if (!itemsB.includes(node)) {
                                    maxNode++;
                                }
                            }
                        }
                        const nodeRatio = maxNode ? matchNode / maxNode : 1;
                        if (nodeRatio > 0) {
                            currentRatio += nodeRatio;
                            // The best candidate must have the most common located nodes.
                            const locA = this._locations.get(objectA);
                            const locB = this._locations.get(objectB);
                            let match = 0;
                            let max = 0;
                            for (const node of locA) {
                                max++;
                                if (locB.includes(node)) {
                                    match++;
                                }
                            }
                            for (const node of locB) {
                                if (!locA.includes(node)) {
                                    max++;
                                }
                            }
                            currentRatio += max ? match / max : 0;
                            // The best candidate must have the most common modifiers.
                            let matchModifier = 0;
                            let maxModifier = 0;
                            for (const node of itemsA) {
                                if (!(node instanceof AbstractNode)) {
                                    maxModifier++;
                                    if (itemsB.includes(node)) {
                                        matchModifier++;
                                    }
                                }
                            }
                            for (const node of itemsB) {
                                if (!(node instanceof AbstractNode)) {
                                    if (!itemsB.includes(node)) {
                                        maxModifier++;
                                    }
                                }
                            }
                            currentRatio += (maxModifier ? matchModifier / maxModifier : 0) / 10;
                            mapRatios.push([currentRatio, objectA, idB]);
                        }
                    }
                }
            }
            return mapRatios;
        }
        _addLocations(domObject, locations, from) {
            const allItems = [];
            const items = from.get(domObject);
            if (items) {
                for (const item of items) {
                    if (!allItems.includes(item)) {
                        allItems.push(item);
                    }
                }
            }
            const nodes = locations.get(domObject);
            if (nodes) {
                this._locations.set(domObject, nodes ? Array.from(nodes) : []);
                for (const node of nodes) {
                    if (!allItems.includes(node)) {
                        allItems.push(node);
                    }
                }
            }
            else {
                this._locations.set(domObject, []);
            }
            if (domObject.children) {
                for (const index in domObject.children) {
                    const child = domObject.children[index];
                    if (!(child instanceof AbstractNode)) {
                        for (const node of this._addLocations(child, locations, from)) {
                            allItems.push(node);
                        }
                    }
                }
            }
            this._items.set(domObject, allItems);
            return allItems;
        }
        _updateDom(id) {
            var _a, _b;
            const diff = this._diff[id];
            if (!diff) {
                return;
            }
            const object = this._objects[id];
            const domObject = object.object;
            let newNode = false;
            if (domObject.tag) {
                let domNode = this._getAvailableElement(id);
                if (domNode && !domObject.shadowRoot !== !domNode.shadowRoot) {
                    domNode = null;
                }
                let attributes;
                if (domNode) {
                    if (diff.askCompleteRedrawing) {
                        for (const attr of domNode.attributes) {
                            const value = (_a = domObject.attributes) === null || _a === void 0 ? void 0 : _a[attr.name];
                            if (typeof value === 'undefined') {
                                domNode.removeAttribute(attr.name);
                            }
                        }
                        attributes = domObject.attributes;
                    }
                    else {
                        attributes = diff.attributes;
                    }
                    if (!diff.askCompleteRedrawing) {
                        for (const name in diff.style) {
                            setStyle(domNode, name, diff.style[name] || '');
                        }
                        for (const name in diff.classList) {
                            if (diff.classList[name]) {
                                domNode.classList.add(name);
                            }
                            else {
                                domNode.classList.remove(name);
                            }
                        }
                    }
                }
                else {
                    domNode = document.createElement(domObject.tag);
                    attributes = domObject.attributes;
                    if (domObject.shadowRoot) {
                        domNode.attachShadow({ mode: 'open' });
                    }
                }
                for (const name in attributes) {
                    if (name === 'style') {
                        const style = attributes[name];
                        for (const name in style) {
                            setStyle(domNode, name, style[name]);
                        }
                        // Now we set the attribute again to keep order.
                        const styleInline = domNode.getAttribute('style');
                        if (styleInline) {
                            domNode.setAttribute('style', styleInline);
                        }
                    }
                    else if (name === 'class') {
                        const classList = attributes[name];
                        for (const className of classList) {
                            domNode.classList.add(className);
                        }
                        // Now we set the attribute again to keep order.
                        const classInline = domNode.getAttribute('class');
                        if (classInline) {
                            domNode.setAttribute('class', classInline);
                        }
                    }
                    else {
                        const value = attributes[name];
                        if (typeof value === 'string') {
                            domNode.setAttribute(name, value);
                        }
                        else if (!value) {
                            domNode.removeAttribute(name);
                        }
                    }
                }
                if (domNode.getAttribute('class') === '') {
                    domNode.removeAttribute('class');
                }
                if (domNode.getAttribute('style') === '') {
                    domNode.removeAttribute('style');
                }
                object.dom = [domNode];
            }
            else if (domObject.text) {
                object.dom = this._redrawAndAssociateText(id);
            }
            else if (object.domNodesChildren && object.dom.length) {
                for (const domNode of object.dom) {
                    if (this._fromDom.get(domNode) !== id) {
                        this._fromDom.set(domNode, id);
                        newNode = true;
                    }
                }
                // Add all nodes as mapping to avoid association by children.
                for (const domNode of object.domNodes) {
                    this._fromDom.set(domNode, id);
                }
                // Insert children in the dom which locate with the placeholder.
                for (const [ref, position, childIds] of object.domNodesChildren) {
                    if (position === RelativePosition.INSIDE) {
                        const childDomNodes = flat(childIds.map(childId => this._getDomChild(childId, ref)));
                        for (const domNode of childDomNodes) {
                            ref.appendChild(domNode);
                        }
                    }
                    else {
                        const childDomNodes = flat(childIds.map(childId => this._getDomChild(childId, ref.parentElement)));
                        if (position === RelativePosition.BEFORE) {
                            for (const domNode of childDomNodes) {
                                ref.parentElement.insertBefore(domNode, ref);
                            }
                        }
                        else if (ref.nextSibling) {
                            const next = ref.nextSibling;
                            for (const domNode of childDomNodes) {
                                ref.parentElement.insertBefore(domNode, next);
                            }
                        }
                        else {
                            ref.parentElement.append(...childDomNodes);
                        }
                    }
                }
                // Remove protected mapping.
                for (const domNode of object.domNodes) {
                    this._fromDom.delete(domNode);
                    this._domNodesToRedraw.add(domNode);
                }
                for (const domNode of object.dom) {
                    this._fromDom.set(domNode, id);
                }
                // TODO remove ?
                let item = (_b = diff.dom) === null || _b === void 0 ? void 0 : _b[0];
                const parent = item === null || item === void 0 ? void 0 : item.parentNode;
                if (parent) {
                    for (const domNode of object.dom) {
                        if (!item) {
                            parent.appendChild(domNode);
                        }
                        else if (domNode !== item) {
                            parent.insertBefore(domNode, item);
                        }
                        else {
                            item = domNode.nextSibling;
                        }
                    }
                }
            }
            for (const domNode of diff.dom) {
                if (this._fromDom.get(domNode) === id && !object.dom.includes(domNode)) {
                    this._fromDom.delete(domNode);
                    this._domNodesToRedraw.add(domNode);
                }
            }
            for (const domNode of object.dom) {
                if (this._fromDom.get(domNode) !== id || !domNode.parentNode) {
                    this._fromDom.set(domNode, id);
                    newNode = true;
                }
            }
            if (!object.domNodesChildren && object.children.length) {
                let parentDomNode = object.parentDomNode;
                if (domObject.tag) {
                    parentDomNode = object.dom[0];
                    if (domObject.shadowRoot) {
                        parentDomNode = parentDomNode.shadowRoot;
                    }
                }
                const domNodes = [];
                for (const childId of object.children) {
                    domNodes.push(...this._getDomChild(childId, parentDomNode));
                }
                if (domNodes.length) {
                    if (domObject.tag) {
                        const swapNode = domNodes.find(domNode => domNode.contains(parentDomNode));
                        if (swapNode) {
                            parentDomNode.parentNode.removeChild(parentDomNode);
                        }
                        this._insertDomChildren(domNodes, parentDomNode, parentDomNode.firstChild);
                    }
                    else {
                        newNode = true;
                    }
                }
            }
            delete this._diff[id];
            this._domUpdated.add(id);
            return newNode;
        }
        _getDomChild(id, parentDomNode) {
            // Apply diff for descendents if needed.
            const descendents = [id];
            for (const id of descendents) {
                const descendent = this._objects[id];
                descendent.parentDomNode = parentDomNode;
                if (this._diff[id]) {
                    this._updateDom(id);
                }
                else if (!('tag' in descendent.object) && descendent.children) {
                    // Get children if it's a fragment.
                    descendents.push(...descendent.children);
                }
            }
            // Get the dom representing this child.
            let domNodes = [];
            const child = this._objects[id];
            if (child.dom.length) {
                domNodes = child.dom;
            }
            else {
                domNodes = this._getchildrenDomNodes(id);
            }
            return domNodes;
        }
        _redrawAndAssociateText(id) {
            var _a;
            const domObject = this._objects[id].object;
            const textContent = domObject.text;
            let textNodes = this._getAvailableTextNodes(id);
            if (textNodes) {
                const chars = [];
                for (const textNode of textNodes) {
                    const split = textNode.textContent.split('');
                    if (split.length) {
                        for (let i = 0; i < split.length; i++) {
                            chars.push([split[i], textNode, i]);
                        }
                    }
                    else {
                        chars.push(['', textNode, 0]);
                    }
                }
                const len = textContent.length;
                const charLen = chars.length;
                const maxLen = Math.max(len, charLen);
                let index = 0;
                let indexFirstChange = null; // index from begin
                let indexLastChange = null; // index from end
                while ((indexFirstChange === null || indexLastChange === null) && index < maxLen) {
                    if (indexFirstChange === null) {
                        const char = textContent[index];
                        const old = chars[index];
                        if (!old || char !== old[0]) {
                            indexFirstChange = index;
                        }
                    }
                    if (indexLastChange === null) {
                        const char = textContent[len - 1 - index];
                        const old = chars[charLen - 1 - index];
                        if (!old || char !== old[0]) {
                            indexLastChange = index;
                        }
                    }
                    index++;
                }
                if (indexFirstChange !== null) {
                    let textBegin;
                    let textEnd;
                    let first;
                    let center;
                    let last;
                    const charBegin = chars[indexFirstChange];
                    if (charBegin) {
                        textBegin = textEnd = charBegin[1];
                        first = textBegin.textContent.slice(0, charBegin[2]);
                        const charEnd = chars[charLen - indexLastChange];
                        if (indexFirstChange >= len - indexLastChange || !charEnd) {
                            // The indexes of the destination text cross, it is that
                            // the end and the beginning are just. Certain
                            // characters should be removed and replce by the and
                            // of the needed textContent. If there is no ending
                            // change, every ending chars are false and will be
                            // removed and replace by the new ending text.
                            // Please note that you must keep the existing text
                            // nodes. And therefore remove the character in the
                            // text nodes present in the dom.
                            const charEnd = chars[charLen - indexLastChange + 1] || chars[charLen - 1];
                            indexLastChange = charLen;
                            textEnd = charEnd[1];
                            center = '';
                            last = textContent.slice(indexFirstChange);
                        }
                        else {
                            // The indexes, do not cross, so we will add the
                            // missing piece and remove the erroneous characters.
                            textEnd = charEnd[1];
                            last = textEnd.textContent.slice(charEnd[2]);
                            center = textContent.slice(indexFirstChange, len - indexLastChange);
                        }
                    }
                    else {
                        // If there is no start of change, this implies that only
                        // characters must be added.
                        const char = chars[indexFirstChange - 1];
                        textBegin = textEnd = char[1];
                        first = textBegin.textContent;
                        center = textContent.slice(indexFirstChange);
                        last = '';
                    }
                    // Search every text nodes between the begin and end of the
                    // changes. This text nodes will be removed.
                    const textsBetweenStartEnd = [];
                    for (let index = indexFirstChange; index < indexLastChange; index++) {
                        const text = (_a = chars[index]) === null || _a === void 0 ? void 0 : _a[1];
                        if (text &&
                            text !== textBegin &&
                            text !== textEnd &&
                            !textsBetweenStartEnd.includes(text)) {
                            textsBetweenStartEnd.push(text);
                        }
                    }
                    // Update the dom with the minimum of mutations.
                    if (textBegin === textEnd) {
                        if (first === '' && center === '' && last === '') {
                            textsBetweenStartEnd.push(textBegin);
                        }
                        else if (textBegin.textContent !== first + center + last) {
                            textBegin.textContent = first + center + last;
                        }
                    }
                    else {
                        if (first === '' && center === '') {
                            textsBetweenStartEnd.push(textBegin);
                        }
                        else if (textBegin.textContent !== first + center) {
                            textBegin.textContent = first + center;
                        }
                        if (last === '') {
                            textsBetweenStartEnd.push(textEnd);
                        }
                        else if (textEnd.textContent !== last) {
                            textEnd.textContent = last;
                        }
                    }
                    // Removes text nodes between the begin and end, and may be
                    // remove an other text node, if it's replace by an empty string.
                    for (const domNode of textsBetweenStartEnd) {
                        textNodes.splice(textNodes.indexOf(domNode), 1);
                        domNode.parentNode.removeChild(domNode);
                    }
                }
            }
            else {
                textNodes = [document.createTextNode(textContent)];
            }
            return textNodes;
        }
        /**
         * Insert missing domNodes in this element.
         */
        _insertDomChildren(domNodes, parentNode, insertBefore) {
            // Keep the order of unknown nodes.
            while (insertBefore &&
                !this._domNodesToRedraw.has(insertBefore) &&
                !this._fromDom.get(insertBefore)) {
                insertBefore = insertBefore.nextSibling;
            }
            // Insert the node.
            for (const domNode of domNodes) {
                if (insertBefore) {
                    if (insertBefore === domNode) {
                        insertBefore = insertBefore.nextSibling;
                    }
                    else {
                        parentNode.insertBefore(domNode, insertBefore);
                    }
                }
                else {
                    parentNode.appendChild(domNode);
                }
            }
        }
        _getAvailableElement(id) {
            const object = this._objects[id];
            const domObject = object.object;
            const tagName = domObject.tag.toUpperCase();
            const diff = this._diff[id];
            if (object.parentDomNode) {
                for (const domNode of object.parentDomNode.childNodes) {
                    if (tagName === nodeName(domNode) && this.isAvailableNode(id, domNode)) {
                        return domNode;
                    }
                }
            }
            if (diff) {
                for (const domNode of diff.dom) {
                    if (tagName === nodeName(domNode) && this.isAvailableNode(id, domNode)) {
                        return domNode;
                    }
                }
            }
        }
        _getAvailableTextNodes(id) {
            const object = this._objects[id];
            const diff = this._diff[id];
            let textNode;
            if (object.parentDomNode) {
                for (const domNode of object.parentDomNode.childNodes) {
                    if (isInstanceOf(domNode, Text) && this.isAvailableNode(id, domNode)) {
                        textNode = domNode;
                    }
                }
            }
            if (!textNode && diff) {
                for (const domNode of diff.dom) {
                    if (isInstanceOf(domNode, Text) && this.isAvailableNode(id, domNode)) {
                        textNode = domNode;
                    }
                }
            }
            if (textNode) {
                // Get all free text nodes.
                const textNodes = [textNode];
                let text = textNode;
                while (text.previousSibling &&
                    isInstanceOf(text.previousSibling, Text) &&
                    this.isAvailableNode(id, text.previousSibling)) {
                    text = text.previousSibling;
                    textNodes.unshift(text);
                }
                text = textNode;
                while (text.nextSibling &&
                    isInstanceOf(text.nextSibling, Text) &&
                    this.isAvailableNode(id, text.nextSibling)) {
                    text = text.nextSibling;
                    textNodes.push(text);
                }
                return textNodes;
            }
        }
        /**
         * Check if the domNode are already associate to an other domObject and
         * this object don't need to be redrawed. The additional checking for the
         * diff is't use to associate the domNodecreate by a split from the browser.
         * The browser can add the new domNode after or before the split.
         */
        isAvailableNode(id, domNode) {
            var _a;
            const linkedId = this._fromDom.get(domNode);
            if (!linkedId) {
                if (domNode.nodeType === Node.TEXT_NODE || this._domNodesToRedraw.has(domNode)) {
                    // The browser can separate an item and keep all attributes on the
                    // clone. In the event of a new element to be associated, a
                    // complete redrawing is requested.
                    this._diff[id].askCompleteRedrawing = true;
                    return true;
                }
            }
            if (linkedId === id) {
                return true;
            }
            if ((_a = this._diff[linkedId]) === null || _a === void 0 ? void 0 : _a.askCompleteRedrawing) {
                // The browser can add the new domNode after or before the split.
                // In this case, there is a change in both elements. In the case of
                // text it is important to keep the dom intact in order to guarantee
                // the operation of the spell checkers. It is also important to keep
                // order for the parents of these texts, but by doing this, we are
                // forced to reset the content, animations may be lost.
                this._diff[id].askCompleteRedrawing = true;
                return true;
            }
        }
        _getchildrenDomNodes(id) {
            const object = this._objects[id];
            const domNodes = [];
            const treatedObject = [];
            if (object.children) {
                for (const childId of object.children) {
                    const child = this._objects[childId];
                    if (child && !treatedObject.includes(childId)) {
                        treatedObject.push(childId);
                        let childDomNodes;
                        if (child.dom.length) {
                            childDomNodes = child.dom;
                        }
                        else {
                            childDomNodes = this._getchildrenDomNodes(childId);
                        }
                        for (const node of childDomNodes) {
                            if (!domNodes.includes(node)) {
                                domNodes.push(node);
                            }
                        }
                    }
                }
            }
            return domNodes;
        }
    }

    class LayoutContainer extends ContainerNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
    }

    class DomLayoutEngine extends LayoutEngine {
        constructor() {
            super(...arguments);
            this._domReconciliationEngine = new DomReconciliationEngine();
            // used only to develop and avoid wrong promise from commands
            this._currentlyRedrawing = false;
            this.renderingMap = {};
            this._markedForRedraw = new Set();
            this.locations = {};
            this.defaultRootComponent = {
                id: 'editor',
                async render() {
                    const editor = new TagNode({ htmlTag: 'JW-EDITOR' });
                    editor.append(new ZoneNode({ managedZones: ['main'] }));
                    editor.append(new ZoneNode({ managedZones: ['default'] }));
                    return [editor];
                },
            };
        }
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        async start() {
            for (const componentId in this.locations) {
                this.renderingMap[componentId] = [];
                this.componentZones[componentId] = ['root'];
                if (!this.componentDefinitions[componentId]) {
                    throw new Error('Layout component "' + componentId + '" not found.');
                }
            }
            if (!flat(Object.values(this.componentZones)).includes('root')) {
                this.componentDefinitions.editor = this.defaultRootComponent;
                this.componentZones.editor = ['root'];
            }
            for (const componentId in this.componentDefinitions) {
                this._prepareLayoutContainerAndLocation(this.componentDefinitions[componentId]);
            }
            await super.start();
        }
        async stop() {
            for (const componentId in this.componentDefinitions) {
                const location = this.locations[componentId];
                if (location) {
                    const nodes = this.components[componentId];
                    for (const node of nodes) {
                        const domNodes = this._domReconciliationEngine.toDom(node);
                        if (location[1] === 'replace') {
                            // Undo the replace that was done by the layout engine.
                            let first = domNodes && domNodes[0];
                            if (!first) {
                                first = this.renderingMap[componentId][0];
                            }
                            if (first && first.parentNode) {
                                first.parentNode.insertBefore(location[0], first);
                            }
                        }
                    }
                }
            }
            this.renderingMap = {};
            this._markedForRedraw = new Set();
            this.location = null;
            this.locations = {};
            this._rendererCache = null;
            this._domReconciliationEngine.clear();
            return super.stop();
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Return the VNode(s) corresponding to the given DOM Node.
         *
         * @param Node
         */
        getNodes(domNode) {
            return this._domReconciliationEngine.fromDom(domNode);
        }
        /**
         * Return the DOM Node(s) corresponding to the given VNode.
         *
         * @param node
         */
        getDomNodes(node) {
            return this._domReconciliationEngine.toDom(node);
        }
        async redraw(params) {
            if (this._currentlyRedrawing) {
                throw new Error('Double redraw detected');
            }
            this._currentlyRedrawing = true;
            return this._redraw(params)
                .then(() => {
                this._currentlyRedrawing = false;
            })
                .catch(error => {
                this._currentlyRedrawing = false;
                throw error;
            });
        }
        /**
         * Parse the dom selection into the description of a VSelection.
         *
         * @param selection
         * @param [direction]
         */
        parseSelection(selection) {
            const start = this._domReconciliationEngine.locate(selection.anchorNode, selection.anchorOffset);
            if (!start) {
                return;
            }
            const end = this._domReconciliationEngine.locate(selection.focusNode, selection.focusOffset);
            if (!end) {
                return;
            }
            const [startVNode, startPosition] = start;
            const [endVNode, endPosition] = end;
            let direction;
            if (selection instanceof Selection) {
                const domRange = selection.rangeCount && selection.getRangeAt(0);
                if (domRange.startContainer === selection.anchorNode &&
                    domRange.startOffset === selection.anchorOffset) {
                    direction = Direction.FORWARD;
                }
                else {
                    direction = Direction.BACKWARD;
                }
            }
            else {
                direction = selection.direction;
            }
            return {
                anchorNode: startVNode,
                anchorPosition: startPosition,
                focusNode: endVNode,
                focusPosition: endPosition,
                direction: direction,
            };
        }
        markForRedraw(domNodes) {
            for (const domNode of domNodes) {
                this._markedForRedraw.add(domNode);
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        async _redraw(params = {
            add: [],
            move: [],
            remove: [],
            update: [],
        }) {
            const updatedNodes = [...this._getInvalidNodes(params)];
            const layout = this.editor.plugins.get(Renderer);
            const engine = layout.engines['object/html'];
            const cache = (this._rendererCache = await engine.render(updatedNodes, this._rendererCache, !!this._rendererCache));
            this._domReconciliationEngine.update(updatedNodes, cache.renderings, cache.locations, cache.renderingDependent, this._markedForRedraw);
            this._markedForRedraw = new Set();
            // Append in dom if needed.
            for (const componentId in this.locations) {
                const nodes = this.components[componentId];
                const needInsert = nodes.find(node => {
                    const domNodes = this._domReconciliationEngine.toDom(node);
                    return !domNodes.length || domNodes.some(node => !node.parentNode);
                });
                if (needInsert) {
                    this._appendComponentInDom(componentId);
                }
            }
            this._renderSelection();
        }
        /**
         * Get the invalidated nodes in the rendering.
         * Clear the renderer in cache for this node or modifier. The cache
         * renderer is added only for performance at redrawing time. The
         * invalidation are automatically made from memory changes.
         */
        _getInvalidNodes(diff) {
            const cache = this._rendererCache;
            const remove = new Set();
            const update = new Set();
            const updatedModifiers = new Set();
            const updatedSiblings = new Set();
            const add = new Set();
            // Add new nodes for redrawing it.
            for (const object of diff.add) {
                if (object instanceof AbstractNode) {
                    add.add(object);
                }
                else if (object instanceof Modifier) {
                    updatedModifiers.add(object);
                }
            }
            // Add re-inserted nodes (after unfo for eg) for redrawing it.
            // Can be marked as moved because its elements still contain references.
            for (const object of diff.move) {
                if (object instanceof AbstractNode &&
                    object.parent &&
                    !add.has(object) &&
                    !(cache === null || cache === void 0 ? void 0 : cache.renderings.get(object))) {
                    add.add(object);
                    for (const child of object.descendants()) {
                        add.add(child);
                    }
                }
            }
            for (const node of add) {
                if (!node.parent) {
                    add.delete(node);
                    remove.add(node);
                    if (node.childVNodes) {
                        for (const child of node.descendants()) {
                            add.delete(node);
                            remove.add(child);
                        }
                    }
                }
            }
            if (cache) {
                // Select the removed VNode and Modifiers.
                const allRemove = new Set(diff.remove);
                for (const object of diff.remove) {
                    if (object instanceof AbstractNode) {
                        remove.add(object);
                    }
                    else {
                        if (object instanceof Modifier) {
                            updatedModifiers.add(object);
                        }
                        for (const [parent] of this.editor.memory.getParents(object)) {
                            if (parent instanceof AbstractNode) {
                                update.add(parent);
                            }
                            else if (parent instanceof Modifier) {
                                updatedModifiers.add(parent);
                            }
                        }
                    }
                }
                const filterd = this._filterInRoot(new Set(remove));
                for (const node of filterd.remove) {
                    update.delete(node);
                    remove.add(node);
                    if (node.childVNodes) {
                        for (const child of node.descendants()) {
                            remove.add(child);
                        }
                    }
                }
                for (const node of filterd.keep) {
                    update.add(node); // TODO: memory change to have real add and not add + move.
                }
                const needSiblings = new Set();
                // Filter to keep only update not added or removed nodes.
                const paramsUpdate = [];
                diff.update.filter(up => {
                    const object = up[0];
                    if (up[1] && object instanceof AbstractNode && !object.parent) {
                        remove.add(object);
                        for (const child of object.descendants()) {
                            remove.add(child);
                        }
                    }
                    else if (!remove.has(object)) {
                        paramsUpdate.push(up);
                    }
                });
                const mayBeAlreadyRemoved = [];
                // Select the updated VNode and Modifiers and the VNode siblings.
                // From the parent, select the removed VNode siblings.
                for (const [object, changes] of paramsUpdate) {
                    if (allRemove.has(object) ||
                        remove.has(object) ||
                        update.has(object) ||
                        updatedModifiers.has(object)) {
                        continue;
                    }
                    if (object instanceof AbstractNode) {
                        update.add(object);
                        needSiblings.add(object);
                        mayBeAlreadyRemoved.push(object);
                    }
                    else {
                        if (object instanceof Modifier) {
                            updatedModifiers.add(object);
                        }
                        for (const [parent, parentProp] of this.editor.memory.getParents(object)) {
                            if (parent instanceof AbstractNode) {
                                if (remove.has(parent)) ;
                                else if (!parent.parent) {
                                    // An old removed node can change. For eg: move a children
                                    // into the active VDocument.
                                    remove.add(parent);
                                    for (const child of parent.descendants()) {
                                        remove.add(child);
                                        update.delete(child);
                                    }
                                }
                                else if (changes &&
                                    parentProp[0][0] === 'childVNodes' &&
                                    typeof changes[0] === 'number') {
                                    // If change a children (add or remove) redraw the node and
                                    // siblings.
                                    const childVNodes = parent.childVNodes;
                                    for (let i = 0; i < changes.length; i++) {
                                        const index = changes[i];
                                        const child = childVNodes[index];
                                        if (child) {
                                            if (!add.has(child)) {
                                                update.add(child);
                                                mayBeAlreadyRemoved.push(child);
                                            }
                                            if (changes[i - 1] !== index - 1) {
                                                const previous = child.previousSibling();
                                                if (previous &&
                                                    !add.has(previous) &&
                                                    !update.has(previous)) {
                                                    updatedSiblings.add(previous);
                                                    mayBeAlreadyRemoved.push(previous);
                                                }
                                            }
                                            if (changes[i + 1] !== index + 1) {
                                                const next = child.nextSibling();
                                                if (next && !add.has(next) && !update.has(next)) {
                                                    if (next) {
                                                        updatedSiblings.add(next);
                                                        mayBeAlreadyRemoved.push(next);
                                                    }
                                                }
                                            }
                                        }
                                        else {
                                            const children = parent.children();
                                            if (children.length) {
                                                const last = children[children.length - 1];
                                                if (last && !add.has(last) && !update.has(last)) {
                                                    updatedSiblings.add(last);
                                                    mayBeAlreadyRemoved.push(last);
                                                }
                                            }
                                        }
                                    }
                                    update.add(parent);
                                    mayBeAlreadyRemoved.push(parent);
                                }
                                else {
                                    update.add(parent);
                                    needSiblings.add(parent);
                                    mayBeAlreadyRemoved.push(parent);
                                }
                            }
                            else if (parent instanceof Modifier) {
                                updatedModifiers.add(parent);
                            }
                        }
                    }
                }
                for (const node of this._filterInRoot(new Set(mayBeAlreadyRemoved)).remove) {
                    update.delete(node);
                    remove.add(node);
                    add.delete(node);
                    needSiblings.delete(node);
                    updatedSiblings.delete(node);
                }
                // If any change invalidate the siblings.
                for (const node of needSiblings) {
                    const next = node.nextSibling();
                    if (next)
                        updatedSiblings.add(next);
                    const previous = node.previousSibling();
                    if (previous)
                        updatedSiblings.add(previous);
                }
                // Invalidate compatible renderer cache.
                for (const node of update) {
                    cache.cachedCompatibleRenderer.delete(node);
                }
                for (const node of remove) {
                    cache.cachedCompatibleRenderer.delete(node);
                }
                // Add removed nodes modifiers for invalidation.
                for (const node of remove) {
                    if (node.modifiers) {
                        // If the node is created after this memory slice (undo),
                        // the node has no values, no id, no modifiers... But the
                        // modifiers is inside the list of removed objects.
                        node.modifiers.map(modifier => updatedModifiers.add(modifier));
                    }
                }
                // Invalidate compatible renderer cache and modifier compare cache.
                for (const modifier of updatedModifiers) {
                    cache.cachedCompatibleModifierRenderer.delete(modifier);
                    const id = cache.cachedModifierId.get(modifier);
                    if (id) {
                        const keys = cache.cachedIsSameAsModifierIds[id];
                        if (keys) {
                            for (const key of keys) {
                                delete cache.cachedIsSameAsModifier[key];
                            }
                            delete cache.cachedIsSameAsModifierIds[id];
                        }
                    }
                }
                // Add the siblings to invalidate the sibling groups.
                for (const sibling of updatedSiblings) {
                    update.add(sibling);
                }
                // Get all linked and dependent VNodes and Modifiers to invalidate cache.
                const treated = new Set();
                const nodesOrModifiers = [...update, ...remove, ...updatedModifiers];
                const treatedItem = new Set(nodesOrModifiers);
                for (const nodeOrModifier of nodesOrModifiers) {
                    const linkedRenderings = cache.nodeDependent.get(nodeOrModifier);
                    if (linkedRenderings) {
                        for (const link of linkedRenderings) {
                            if (!treated.has(link)) {
                                treated.add(link);
                                const from = cache.renderingDependent.get(link);
                                if (from) {
                                    for (const n of from) {
                                        if (!treatedItem.has(n)) {
                                            // Add to invalid domObject origin nodes or modifiers.
                                            nodesOrModifiers.push(n);
                                            treatedItem.add(n);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    const linkedNodes = cache.linkedNodes.get(nodeOrModifier);
                    if (linkedNodes) {
                        for (const node of linkedNodes) {
                            if (!treatedItem.has(node)) {
                                // Add to invalid linked nodes of linkes nodes.
                                nodesOrModifiers.push(node);
                                treatedItem.add(node);
                            }
                        }
                    }
                    if (nodeOrModifier instanceof AbstractNode) {
                        update.add(nodeOrModifier);
                    }
                    else {
                        updatedModifiers.add(nodeOrModifier);
                    }
                }
                // Remove all removed children from node to update.
                for (const node of remove) {
                    update.delete(node);
                }
                // Invalidate VNode cache origin, location and linked.
                for (const node of [...update, ...remove]) {
                    cache.renderingPromises.delete(node);
                    const item = cache.renderings.get(node);
                    if (item) {
                        const items = [item];
                        for (const item of items) {
                            cache.renderingDependent.delete(item);
                            cache.locations.delete(item);
                            if ('children' in item) {
                                for (const child of item.children) {
                                    if (!(child instanceof AbstractNode)) {
                                        items.push(child);
                                    }
                                }
                            }
                        }
                    }
                    cache.renderings.delete(node);
                    cache.nodeDependent.delete(node);
                    cache.linkedNodes.delete(node);
                }
                // Invalidate Modifiers cache linked.
                for (const modifier of updatedModifiers) {
                    cache.nodeDependent.delete(modifier);
                }
            }
            for (const node of add) {
                update.add(node);
            }
            // Render nodes.
            return update;
        }
        _filterInRoot(nodes) {
            const inRoot = new Set([this.root]);
            const notRoot = new Set();
            const nodesInRoot = new Set();
            const nodesInNotRoot = new Set();
            for (const node of nodes) {
                const parents = [];
                let ancestor = node;
                while (ancestor) {
                    parents.push(ancestor);
                    if (inRoot.has(ancestor)) {
                        // The VNode is in the domLayout.
                        nodesInRoot.add(node);
                        break;
                    }
                    ancestor = ancestor.parent;
                    if (!ancestor || !ancestor.id || notRoot.has(ancestor)) {
                        // A VNode without an id does not exist yet/anymore in the
                        // current memory slice.
                        // The VNode is not in the domLayout.
                        nodesInNotRoot.add(node);
                        break;
                    }
                }
                if (nodesInRoot.has(node)) {
                    for (const parent of parents) {
                        inRoot.add(parent);
                    }
                }
                else {
                    for (const parent of parents) {
                        notRoot.add(parent);
                    }
                }
            }
            return { keep: nodesInRoot, remove: nodesInNotRoot };
        }
        /**
         * Render the given VSelection as a DOM selection in the given target.
         *
         * @param selection
         * @param target
         */
        _renderSelection() {
            const selection = this.editor.selection;
            const range = selection.range;
            const activeNodeName = document.activeElement && nodeName(document.activeElement);
            if (activeNodeName === 'INPUT' || activeNodeName === 'TEXTAREA') {
                // Do not change the selection if the focus is set within an input
                // or a textarea so as not to lose that focus.
                return;
            }
            if (selection.range.isCollapsed()) {
                // Prevent rendering a collapsed selection in a non-editable context.
                const target = range.start.previousSibling() || range.end.nextSibling() || range.startContainer;
                const isEditable = this.editor.mode.is(target, RuleProperty.EDITABLE);
                const isInMain = target.ancestor(node => node instanceof ZoneNode && node.managedZones.includes('main'));
                if ((!isEditable && !isContentEditable(target)) || !isInMain) {
                    document.getSelection().removeAllRanges();
                    return;
                }
            }
            const domNodes = this._domReconciliationEngine.toDom(selection.anchor.parent);
            if (!domNodes.length) {
                document.getSelection().removeAllRanges();
                return;
            }
            if (selection.anchor.ancestors().pop() !== this.root ||
                selection.focus.ancestors().pop() !== this.root) {
                console.warn('Cannot render a selection that is outside the Layout.');
                document.getSelection().removeAllRanges();
            }
            const anchor = this._domReconciliationEngine.getLocations(selection.anchor);
            const focus = this._domReconciliationEngine.getLocations(selection.focus);
            const doc = anchor[0].ownerDocument;
            const domSelection = doc.getSelection();
            if (domSelection.anchorNode === anchor[0] &&
                domSelection.anchorOffset === anchor[1] &&
                domSelection.focusNode === focus[0] &&
                domSelection.focusOffset === focus[1]) {
                return;
            }
            const domRange = doc.createRange();
            if (selection.direction === Direction.FORWARD) {
                domRange.setStart(anchor[0], anchor[1]);
                domRange.collapse(true);
            }
            else {
                domRange.setEnd(anchor[0], anchor[1]);
                domRange.collapse(false);
            }
            domSelection.removeAllRanges();
            domSelection.addRange(domRange);
            domSelection.extend(focus[0], focus[1]);
        }
        _appendComponentInDom(id) {
            var _a;
            let [target, position] = this.locations[id];
            const nodes = this.renderingMap[id];
            const first = nodes.find(node => node.parentNode && node.ownerDocument.body.contains(node));
            if (first === null || first === void 0 ? void 0 : first.previousSibling) {
                target = first.previousSibling;
                position = 'after';
            }
            else if ((_a = first === null || first === void 0 ? void 0 : first.parentNode) === null || _a === void 0 ? void 0 : _a.parentNode) {
                target = first.parentNode;
                position = 'prepend';
            }
            else {
                let previous = id;
                while ((previous = this._getPreviousComponentId(previous))) {
                    const last = this.renderingMap[previous][this.renderingMap[previous].length - 1];
                    if (last && last.ownerDocument.body.contains(last)) {
                        target = last;
                        position = 'after';
                    }
                }
            }
            if (position === 'after' && !target.parentNode) {
                throw new Error('Impossible to render a component after an element with no parent.');
            }
            if (position === 'replace' && !target.parentNode) {
                throw new Error('Impossible to replace an element without any parent.');
            }
            const domNodes = [];
            for (const node of this.components[id]) {
                domNodes.push(...this._domReconciliationEngine.toDom(node));
            }
            if (!domNodes.length && this.locations[id][1] === 'replace') {
                throw new Error('Impossible to replace a element with an empty template.');
            }
            if (position === 'after') {
                if (target.nextSibling) {
                    for (const domNode of domNodes) {
                        target.parentNode.insertBefore(domNode, target.nextSibling);
                    }
                }
                else {
                    for (const domNode of domNodes) {
                        target.parentNode.appendChild(domNode);
                    }
                }
            }
            else if (position === 'prepend') {
                let item = target.firstChild;
                for (const domNode of domNodes) {
                    if (!item) {
                        target.appendChild(domNode);
                    }
                    else if (domNode !== item) {
                        target.insertBefore(domNode, item);
                    }
                    else {
                        item = domNode.nextSibling;
                    }
                }
            }
            else if (position === 'replace') {
                for (const domNode of domNodes) {
                    target.parentNode.insertBefore(domNode, target);
                }
                target.parentNode.removeChild(target);
            }
            else {
                for (const domNode of domNodes) {
                    target.appendChild(domNode);
                }
            }
            for (const node of this.renderingMap[id]) {
                if (node.parentNode && !domNodes.includes(node)) {
                    node.parentNode.removeChild(node);
                }
            }
            this.renderingMap[id] = domNodes;
        }
        _getPreviousComponentId(id) {
            const [target, position] = this.locations[id];
            const locations = Object.values(this.locations);
            const componentIds = Object.keys(this.locations);
            const index = componentIds.indexOf(id);
            if (position === 'after') {
                for (let u = index - 1; u >= 0; u--) {
                    const [otherTarget, otherPosition] = locations[u];
                    if (target === otherTarget &&
                        (otherPosition === 'after' || otherPosition === 'replace')) {
                        return componentIds[u];
                    }
                }
                for (let u = locations.length - 1; u > index; u--) {
                    const [otherTarget, otherPosition] = locations[u];
                    if (target === otherTarget && otherPosition === 'replace') {
                        return componentIds[u];
                    }
                }
            }
            else if (position === 'replace') {
                for (let u = index - 1; u >= 0; u--) {
                    const [otherTarget, otherPosition] = locations[u];
                    if (target === otherTarget && otherPosition === 'replace') {
                        return componentIds[u];
                    }
                }
            }
        }
        _prepareLayoutContainerAndLocation(componentDefinition) {
            const zone = this.componentZones[componentDefinition.id];
            if (zone === null || zone === void 0 ? void 0 : zone.includes('root')) {
                // automatically wrap the child into a layoutContainer to keep location of all nodes
                // when update the template and redraw
                this.componentDefinitions[componentDefinition.id] = {
                    id: componentDefinition.id,
                    async render(editor) {
                        const nodes = await componentDefinition.render(editor);
                        const layoutContainer = new LayoutContainer();
                        layoutContainer.append(...nodes);
                        return [layoutContainer];
                    },
                };
                if (this.location) {
                    if (!this.locations[componentDefinition.id]) {
                        this.locations[componentDefinition.id] = this.location;
                        this.renderingMap[componentDefinition.id] = [];
                    }
                }
            }
        }
    }
    DomLayoutEngine.id = 'dom';

    class ZoneDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ZoneNode;
        }
        async render(node, worker) {
            var _a;
            const children = node.childVNodes;
            const domObject = { children: [] };
            for (let index = 0, len = children.length; index < len; index++) {
                const child = children[index];
                if (!((_a = node.hidden) === null || _a === void 0 ? void 0 : _a[child.id])) {
                    domObject.children.push(child);
                }
                worker.depends(child, node);
            }
            return domObject;
        }
    }
    ZoneDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ZoneXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T' && !!item.getAttribute('t-zone');
            };
        }
        async parse(item) {
            const zone = new ZoneNode({ managedZones: [item.getAttribute('t-zone')] });
            const nodes = await this.engine.parse(...item.childNodes);
            zone.append(...nodes);
            return [zone];
        }
    }
    ZoneXmlDomParser.id = XmlDomParsingEngine.id;

    class LayoutContainerDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = LayoutContainer;
        }
        async render(node) {
            return {
                children: [...node.childVNodes],
            };
        }
    }
    LayoutContainerDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ActionableDomObjectRenderer extends NodeRenderer {
        constructor(engine) {
            super(engine);
            this.predicate = ActionableNode;
            this.actionableNodes = new Map();
            this.engine.editor.dispatcher.registerCommandHook('@commit', this._updateActionables.bind(this));
        }
        async render(button, 
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        worker) {
            let clickHandler;
            let mousedownHandler;
            const objectButton = {
                tag: button.htmlTag || 'JW-BUTTON',
                attributes: {
                    name: button.actionName,
                },
                handler: () => {
                    if (button.commandId) {
                        this.engine.editor.execCommand(button.commandId, button.commandArgs);
                    }
                },
                attach: (el) => {
                    clickHandler = (ev) => {
                        ev.stopImmediatePropagation();
                        ev.stopPropagation();
                        ev.preventDefault();
                        objectButton.handler();
                    };
                    mousedownHandler = (ev) => {
                        ev.stopImmediatePropagation();
                        ev.stopPropagation();
                        ev.preventDefault();
                    };
                    el.addEventListener('click', clickHandler);
                    el.addEventListener('mousedown', mousedownHandler);
                    this.actionableNodes.set(button, el);
                },
                detach: (el) => {
                    el.removeEventListener('click', clickHandler);
                    el.removeEventListener('mousedown', mousedownHandler);
                    this.actionableNodes.delete(button);
                },
            };
            const attributes = button.modifiers.find(Attributes);
            const className = attributes === null || attributes === void 0 ? void 0 : attributes.get('class');
            if (className === null || className === void 0 ? void 0 : className.includes(' fa-')) {
                if (!attributes.get('title')) {
                    objectButton.attributes.title = button.label;
                }
            }
            else {
                objectButton.children = [{ text: button.label }];
            }
            return objectButton;
        }
        /**
         * Update button rendering after the command if the value of selected,
         * enabled or visible changed.
         */
        _updateActionables() {
            const pluginConfig = this.engine.editor.plugins.get(DomLayout).configuration;
            const pressedActionablesClassName = pluginConfig.pressedActionablesClassName
                ? pluginConfig.pressedActionablesClassName
                : 'pressed';
            for (const [actionable, element] of this.actionableNodes) {
                const editor = this.engine.editor;
                const select = !!actionable.selected(editor);
                const enable = !!actionable.enabled(editor);
                const visible = !!actionable.visible(editor);
                const attrSelected = element.getAttribute('aria-pressed');
                if (select.toString() !== attrSelected) {
                    element.setAttribute('aria-pressed', select.toString());
                    if (select) {
                        element.classList.add(pressedActionablesClassName);
                    }
                    else {
                        element.classList.remove(pressedActionablesClassName);
                    }
                }
                const domEnable = !element.getAttribute('disabled');
                if (enable !== domEnable) {
                    if (enable) {
                        element.removeAttribute('disabled');
                    }
                    else {
                        element.setAttribute('disabled', 'true');
                    }
                }
                const domVisible = element.style.display !== 'none';
                if (visible !== domVisible) {
                    if (visible) {
                        element.style.display = '';
                    }
                    else {
                        element.style.display = 'none';
                    }
                }
                if (select) {
                    const domSelect = element.closest('jw-select');
                    if (domSelect) {
                        domSelect.querySelector('jw-button').innerHTML = element.innerHTML;
                    }
                }
            }
        }
    }
    ActionableDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ActionableGroupNode extends ContainerNode {
        constructor(params) {
            super(params);
            this.groupName = params === null || params === void 0 ? void 0 : params.name;
        }
    }

    class ActionableGroupDomObjectRenderer extends NodeRenderer {
        constructor(engine) {
            super(engine);
            this.predicate = ActionableGroupNode;
            this.actionableGroupNodes = new Map();
            this.engine.editor.dispatcher.registerCommandHook('@commit', this._updateActionableGroups.bind(this));
        }
        async render(group) {
            if (!group.descendants(node => !(node instanceof ActionableGroupNode) && node.tangible)
                .length) {
                return { children: [] };
            }
            else if (group.ancestor(ActionableGroupNode)) {
                return this._renderBlockSelect(group);
            }
            else {
                return this._renderGroup(group);
            }
        }
        _renderBlockSelect(group) {
            const mousedownHandler = (ev) => ev.preventDefault();
            let clickHandler;
            let open = false;
            const objectSelect = {
                tag: 'JW-SELECT',
                children: [
                    { tag: 'JW-BUTTON', children: [{ text: '\u00A0' }] },
                    { tag: 'JW-GROUP', children: group.children() },
                ],
                attach: (el) => {
                    clickHandler = (ev) => {
                        const inSelect = ev.target.nodeType === Node.ELEMENT_NODE &&
                            ev.target.closest('jw-select') === el;
                        if ((!inSelect && open) || ev.currentTarget !== document) {
                            open = !open;
                            el.setAttribute('aria-pressed', open.toString());
                        }
                    };
                    el.addEventListener('mousedown', mousedownHandler);
                    el.addEventListener('click', clickHandler);
                    document.addEventListener('click', clickHandler);
                    this.actionableGroupNodes.set(group, el);
                },
                detach: (el) => {
                    el.removeEventListener('mousedown', mousedownHandler);
                    el.removeEventListener('click', clickHandler);
                    document.removeEventListener('click', clickHandler);
                    this.actionableGroupNodes.delete(group);
                },
            };
            return objectSelect;
        }
        _renderGroup(group) {
            const objectGroup = {
                tag: 'JW-GROUP',
                attributes: { name: group.groupName },
                children: group.children(),
            };
            return objectGroup;
        }
        /**
         * Update option rendering after the command if the value of visible
         * changed.
         *
         * @param actionable
         * @param element
         */
        _updateActionableGroups() {
            for (const [actionable, element] of this.actionableGroupNodes) {
                const editor = this.engine.editor;
                const invisible = actionable
                    .descendants(ActionableNode)
                    .every(n => n.visible && !n.visible(editor));
                const domInvisible = element.style.display === 'none';
                if (invisible !== domInvisible) {
                    if (invisible) {
                        element.style.display = 'none';
                    }
                    else {
                        element.style.display = '';
                    }
                }
            }
        }
    }
    ActionableGroupDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class LabelNode extends AtomicNode {
        constructor(params) {
            super();
            this.label = params.label;
        }
    }

    class LabelDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = LabelNode;
        }
        async render(label) {
            const objectLabel = {
                tag: 'SPAN',
                attributes: { class: new Set(['label']) },
                children: [{ text: label.label }],
            };
            return objectLabel;
        }
    }
    LabelDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class ToolbarNode extends ContainerNode {
    }

    class SeparatorDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (node) => node instanceof SeparatorNode && !!node.ancestor(ToolbarNode);
        }
        async render() {
            const objectSeparator = {
                tag: 'JW-SEPARATOR',
                attributes: { role: 'separator' },
            };
            return objectSeparator;
        }
    }
    SeparatorDomObjectRenderer.id = DomObjectRenderingEngine.id;

    const FocusAndBlurEvents = ['selectionchange', 'blur', 'focus', 'mousedown', 'touchstart'];
    class DomLayout extends JWPlugin {
        constructor(editor, configuration) {
            super(editor, configuration);
            this.loadables = {
                renderers: [
                    ZoneDomObjectRenderer,
                    LayoutContainerDomObjectRenderer,
                    ActionableGroupDomObjectRenderer,
                    ActionableDomObjectRenderer,
                    LabelDomObjectRenderer,
                    SeparatorDomObjectRenderer,
                ],
                parsers: [ZoneXmlDomParser],
                layoutEngines: [],
                components: [],
            };
            this.loaders = {
                domLocations: this._loadComponentLocations,
            };
            this.commandHooks = {
                '@commit': this._redraw,
            };
            this.loadables.layoutEngines.push(DomLayoutEngine);
            this.processKeydown = this.processKeydown.bind(this);
            let debounceEvent;
            const debouncedCheckFocusChanged = this._checkFocusChanged.bind(this);
            this._checkFocusChanged = (ev) => {
                if (debounceEvent && 'tagName' in debounceEvent.target) {
                    return;
                }
                clearTimeout(this._debounce);
                debounceEvent = ev;
                this._debounce = setTimeout(() => {
                    clearTimeout(this._debounce);
                    debounceEvent = null;
                    debouncedCheckFocusChanged(ev);
                });
            };
        }
        async start() {
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            FocusAndBlurEvents.forEach(eventName => {
                window.addEventListener(eventName, this._checkFocusChanged, true);
                window.addEventListener(eventName + '-iframe', this._checkFocusChanged, true);
            });
            for (const component of this.configuration.components || []) {
                domLayoutEngine.loadComponent(component);
            }
            const zones = {};
            for (const [id, zone] of this.configuration.componentZones || []) {
                zones[id] = zone;
            }
            domLayoutEngine.loadComponentZones(zones);
            this._loadComponentLocations(this.configuration.locations || []);
            domLayoutEngine.location = this.configuration.location;
            await domLayoutEngine.start();
            window.addEventListener('keydown', this.processKeydown, true);
            window.addEventListener('keydown-iframe', this.processKeydown, true);
        }
        async stop() {
            clearTimeout(this._debounce);
            FocusAndBlurEvents.forEach(eventName => {
                window.removeEventListener(eventName, this._checkFocusChanged, true);
                window.removeEventListener(eventName + '-iframe', this._checkFocusChanged, true);
            });
            window.removeEventListener('keydown', this.processKeydown, true);
            window.removeEventListener('keydown-iframe', this.processKeydown, true);
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            await domLayoutEngine.stop();
            return super.stop();
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * KeyboardEvent listener to be added to the DOM that calls `execCommand` if
         * the keys pressed match one of the shortcut registered in the keymap.
         *
         * @param event
         */
        async processKeydown(event, processingContext = this.editor) {
            if (this.focusedNode &&
                ['INPUT', 'SELECT', 'TEXTAREA'].includes(nodeName(this.focusedNode))) {
                // Don't process if use write into an input, select or textarea.
                return;
            }
            // If target == null we bypass the editable zone check.
            // This should only occurs when we receive an inferredKeydownEvent
            // created from an InputEvent send by a mobile device.
            if (!this.focusedNode && event.target && !this.isInEditable(event.target)) {
                // Don't process keydown if the user is outside the current editor editable Zone and
                // the current event does not target an editable node (for testing or external methods
                // and library).
                return;
            }
            const keymap = this.dependencies.get(Keymap);
            const commands = keymap.match(event);
            const [command, context] = this.editor.contextManager.match(commands);
            if (command && command.commandId) {
                const params = Object.assign({ context }, command.commandArgs);
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                await Promise.all([
                    this.editor.dispatcher.dispatch('@preKeydownCommand', {}),
                    processingContext.execCommand(command.commandId, params),
                ]);
                return command.commandId;
            }
        }
        /**
         * Return true if the target node is inside Jabberwock's main editable Zone
         * and within an editable context.
         *
         * @param target
         */
        isInEditable(target) {
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            target = this._getDeepestTarget(target);
            let nodes = domLayoutEngine.getNodes(target);
            while (!nodes.length && target) {
                if (target.previousSibling) {
                    target = target.previousSibling;
                }
                else {
                    target = target.parentNode;
                }
                nodes = domLayoutEngine.getNodes(target);
            }
            const node = nodes === null || nodes === void 0 ? void 0 : nodes.pop();
            // We cannot always expect a 'contentEditable' attribute on the main
            // ancestor. So we expect to find the main editor ZoneNode if we are in
            // the editable part of Jabberwock.
            return (node &&
                this.editor.isInEditable(node) &&
                !!node.ancestor(node => node instanceof ZoneNode && node.managedZones.includes('main')));
        }
        /**
         * Return true if the target node is inside a Jabberwock's editor componant.
         *
         * @param target: Node
         */
        isInEditor(target) {
            var _a;
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            target = this._getDeepestTarget(target);
            return !!((_a = domLayoutEngine.getNodes(target)) === null || _a === void 0 ? void 0 : _a.length);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _loadComponentLocations(locations) {
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            for (const [id, location] of locations) {
                domLayoutEngine.locations[id] = location;
            }
        }
        /**
         * Return the deepest target, based on the given target and the current
         * selection. The selection can be used only if it is indeed contained
         * within the target.
         *
         * @param target
         */
        _getDeepestTarget(target) {
            var _a;
            const selection = (_a = target.ownerDocument) === null || _a === void 0 ? void 0 : _a.getSelection();
            const anchorNode = selection === null || selection === void 0 ? void 0 : selection.anchorNode;
            let node = anchorNode;
            let isAnchorDescendantOfTarget = false;
            while (node) {
                if (node === target) {
                    isAnchorDescendantOfTarget = true;
                    break;
                }
                node = node.parentElement;
            }
            return isAnchorDescendantOfTarget ? anchorNode : target;
        }
        async _redraw(params) {
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            await domLayoutEngine.redraw(params.changesLocations);
        }
        _checkFocusChanged(ev) {
            const layout = this.dependencies.get(Layout);
            const domLayoutEngine = layout.engines.dom;
            let focus;
            let iframe;
            if (isInstanceOf(document.activeElement, HTMLIFrameElement)) {
                iframe = document.activeElement;
            }
            else if (isInstanceOf(ev.target, HTMLIFrameElement)) {
                iframe = ev.target;
            }
            let root = document;
            if (isInstanceOf(ev.target, Element) && ev.target.shadowRoot) {
                root = ev.target.shadowRoot;
            }
            if (iframe) {
                const iframeDoc = iframe.contentDocument;
                const domSelection = iframeDoc.getSelection();
                if (isInstanceOf(domSelection.anchorNode, HTMLBodyElement)) {
                    if (domSelection.anchorNode.contains(this.focusedNode)) {
                        // On chrome, when the user  mousedown and grow the selection,
                        // then value of getSelection() doesn't change. We keep the
                        // previous selection if it's inside the current iframe.
                        focus = this.focusedNode;
                    }
                    else if (domLayoutEngine.getNodes(iframe).length) {
                        focus = iframe;
                    }
                }
                else if (domLayoutEngine.getNodes(domSelection.anchorNode).length) {
                    focus = domSelection.anchorNode;
                }
                else if (domLayoutEngine.getNodes(iframeDoc.activeElement).length) {
                    focus = iframeDoc.activeElement;
                }
                else if (domLayoutEngine.getNodes(iframe).length) {
                    focus = iframeDoc.activeElement;
                }
            }
            else {
                const domSelection = root.getSelection
                    ? root.getSelection()
                    : root.ownerDocument.getSelection();
                if (ev.type === 'selectionchange' && !domSelection.anchorNode) {
                    // When the dom are redrawed, the selection can be removed, it's not a blur/focus.
                    return;
                }
                let ancestor = domSelection.anchorNode;
                while (ancestor &&
                    ancestor.parentNode &&
                    ancestor !== document.activeElement &&
                    ancestor !== root.activeElement) {
                    if (isInstanceOf(ancestor.parentNode, ShadowRoot)) {
                        ancestor = ancestor.parentNode.host;
                    }
                    else if (isInstanceOf(ancestor.parentNode, Document)) {
                        ancestor = ancestor.parentNode.defaultView.frameElement;
                    }
                    else {
                        ancestor = ancestor.parentNode;
                    }
                }
                if ((ancestor === root.activeElement || ancestor === document.activeElement) &&
                    domLayoutEngine.getNodes(domSelection.anchorNode).length) {
                    focus = domSelection.anchorNode;
                }
                else if (domLayoutEngine.getNodes(document.activeElement).length) {
                    focus = document.activeElement;
                }
                else if (ev.target && domLayoutEngine.getNodes(ev.target).length) {
                    focus = ev.target;
                }
            }
            if (focus && !this.focusedNode) {
                this.editor.dispatcher.dispatch('@focus');
            }
            else if (!focus && this.focusedNode) {
                this.editor.dispatcher.dispatch('@blur');
            }
            this.focusedNode = focus;
        }
    }
    DomLayout.dependencies = [DomObjectRenderer, Parser, Renderer, Layout, Keymap];

    class MutationNormalizer {
        constructor() {
            /**
             * The MutationObserver used by the normalizer to watch the nodes that are
             * being modified since the normalizer creation until it is drestroyed.
             */
            this._observers = [];
        }
        attach(node) {
            const observer = new MutationObserver(this._onMutation.bind(this));
            observer.observe(node, {
                characterDataOldValue: true,
                characterData: true,
                childList: true,
                subtree: true,
            });
            this._observers.push(observer);
        }
        start() {
            this._listen = true;
            this._mutations = [];
        }
        /**
         * Extract a mapping of the separate characters, their corresponding text
         * nodes and their offsets in said nodes from the given node's subtree.
         *
         * @private
         * @param charMutations
         * @returns { previous, current }
         */
        getCharactersMapping(mutations) {
            const before = new Set();
            const add = new Set();
            const current = new Set();
            const textMutations = [];
            // Gather all modified nodes to notify the listener.
            function getSelfAndAllChildren(target) {
                const texts = [target];
                target.childNodes.forEach(target => {
                    texts.push(...getSelfAndAllChildren(target));
                });
                return texts;
            }
            function isTextNode(target) {
                return isInstanceOf(target, Text) || nodeName(target) === 'BR';
            }
            mutations.forEach(record => {
                const targetMutation = record.target;
                const targetIsAdded = add.has(targetMutation);
                if (!targetIsAdded) {
                    before.add(targetMutation);
                }
                if (record.type === 'characterData') {
                    current.add(targetMutation);
                    textMutations.push({
                        target: targetMutation,
                        old: record.oldValue.replace(/\u00A0/g, ' '),
                        current: targetMutation.textContent.replace(/\u00A0/g, ' '),
                    });
                }
                else {
                    record.addedNodes.forEach(node => {
                        getSelfAndAllChildren(node).forEach(child => {
                            if (!before.has(child)) {
                                add.add(child);
                            }
                            current.add(child);
                            if (!isTextNode(child)) {
                                return;
                            }
                            textMutations.push({
                                target: child,
                                old: '',
                                current: isInstanceOf(child, Text)
                                    ? child.textContent.replace(/\u00A0/g, ' ')
                                    : '\n',
                            });
                        });
                    });
                    record.removedNodes.forEach(node => {
                        getSelfAndAllChildren(node).forEach(child => {
                            if (current.has(child)) {
                                current.delete(child);
                            }
                            if (targetIsAdded) {
                                add.add(child);
                            }
                            if (!add.has(child)) {
                                before.add(child);
                            }
                            if (!isTextNode(child)) {
                                return;
                            }
                            textMutations.push({
                                target: child,
                                old: isInstanceOf(child, Text)
                                    ? child.textContent.replace(/\u00A0/g, ' ')
                                    : '\n',
                                current: '',
                            });
                        });
                    });
                }
            });
            const already = new Map();
            const charMutations = [];
            textMutations.forEach(textMutation => {
                const target = textMutation.target;
                let mutation = already.get(target);
                if (mutation) {
                    if (current.has(target) && !mutation.current.length) {
                        mutation.current = textMutation.current;
                    }
                    return;
                }
                if (current.has(target)) {
                    mutation = {
                        target: target,
                        old: before.has(target) ? textMutation.old : '',
                        current: textMutation.current,
                    };
                    charMutations.push(mutation);
                }
                else if (before.has(target)) {
                    mutation = {
                        target: target,
                        old: textMutation.old,
                        current: '',
                    };
                    charMutations.push(mutation);
                }
                already.set(target, mutation);
            });
            const currentLinked = this._getCharLinked(charMutations, 'current');
            const previousLinked = this._getCharLinked(charMutations, 'old');
            const oldText = previousLinked.chars;
            const currentText = currentLinked.chars;
            if (oldText === currentText) {
                return {
                    index: -1,
                    insert: '',
                    remove: '',
                    previous: previousLinked,
                    current: currentLinked,
                };
            }
            const changePosition = this._changedOffset(oldText, currentText);
            const minLength = Math.min(oldText.length, currentText.length);
            let insertByChange;
            const unknownPosition = changePosition.left > minLength - changePosition.right;
            if (unknownPosition) {
                const maxLength = Math.max(oldText.length, currentText.length);
                const len = maxLength - minLength;
                insertByChange = currentText.slice(currentText.length - changePosition.right);
                for (let k = 0; k + len < minLength; k++) {
                    if (insertByChange[k - 1] === ' ') {
                        insertByChange = insertByChange.slice(k);
                        break;
                    }
                }
                insertByChange = insertByChange.slice(0, len);
                const removeByChange = oldText.slice(oldText.length - changePosition.right - len, oldText.length - changePosition.right);
                return {
                    index: -1,
                    insert: insertByChange,
                    remove: removeByChange,
                    previous: previousLinked,
                    current: currentLinked,
                };
            }
            else {
                insertByChange = currentText.slice(changePosition.left, currentText.length - changePosition.right);
            }
            let fineChangePosition;
            let insertedWordAnalysed;
            if (textMutations.length > 1) {
                let alreadyFound = false;
                for (let k = textMutations.length - 1; k >= 0; k--) {
                    const charMutation = textMutations[k];
                    if (charMutation.old.length >= charMutation.current.length) {
                        continue;
                    }
                    let currentChange;
                    if (charMutation.old !== '') {
                        if (alreadyFound) {
                            continue;
                        }
                        const oldTextMutation = charMutation.old;
                        const currentTextMutation = charMutation.current;
                        const resMutation = this._changedOffset(oldTextMutation, currentTextMutation);
                        currentChange = currentTextMutation.slice(resMutation.left, currentTextMutation.length - resMutation.right);
                    }
                    else if (charMutation.current === currentText) {
                        continue;
                    }
                    else {
                        currentChange = charMutation.current;
                    }
                    const changeIndex = currentChange.indexOf(insertByChange);
                    if (changeIndex === -1) {
                        continue;
                    }
                    const indexStart = currentText.indexOf(currentChange);
                    const indexEnd = indexStart + currentChange.length;
                    const rangeChangeStart = changePosition.left - changeIndex;
                    const rangeChangeEnd = currentText.length - changePosition.right;
                    if ((rangeChangeStart >= indexStart && rangeChangeStart < indexEnd) ||
                        (rangeChangeEnd > indexStart && rangeChangeEnd <= indexEnd) ||
                        (rangeChangeEnd >= indexEnd && rangeChangeStart <= indexStart)) {
                        fineChangePosition = {
                            left: indexStart,
                            right: currentText.length - indexEnd,
                        };
                        insertedWordAnalysed = currentChange;
                        alreadyFound = true;
                        if (charMutation.old === '') {
                            break;
                        }
                    }
                }
            }
            if (typeof insertedWordAnalysed === 'undefined') {
                insertedWordAnalysed = insertByChange;
                let beforeIndex = insertedWordAnalysed.indexOf(insertByChange);
                if (insertByChange === '') {
                    beforeIndex = insertedWordAnalysed.length;
                }
                else {
                    beforeIndex = 0;
                }
                fineChangePosition = {
                    left: changePosition.left - beforeIndex,
                    right: changePosition.right,
                };
            }
            const removedWordAnalysed = oldText.slice(fineChangePosition.left, oldText.length - fineChangePosition.right);
            return {
                index: fineChangePosition.left,
                insert: insertedWordAnalysed,
                remove: removedWordAnalysed,
                previous: previousLinked,
                current: currentLinked,
            };
        }
        getMutatedElements(mutations) {
            const elements = new Set();
            mutations.forEach(MutationRecord => {
                if (MutationRecord.type === 'characterData') {
                    elements.add(MutationRecord.target);
                }
                else {
                    MutationRecord.addedNodes.forEach(target => elements.add(target));
                    MutationRecord.removedNodes.forEach(target => elements.add(target));
                }
            });
            return elements;
        }
        stop() {
            this._listen = false;
        }
        /**
         * Called when destroy the mutation normalizer.
         * Remove all added handlers.
         *
         */
        destroy() {
            for (const observer of this._observers) {
                observer.disconnect();
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _getCharLinked(charMutations, type) {
            const mapNodeValue = new WeakMap();
            const obj = {
                chars: '',
                nodes: [],
                offsets: [],
            };
            charMutations.forEach(charMutation => {
                mapNodeValue.set(charMutation.target, charMutation[type]);
                const len = charMutation[type].length;
                if (obj.nodes.length) {
                    const charParented = new Set();
                    let node = charMutation.target;
                    while (node &&
                        (!isInstanceOf(node, Element) || !node.getAttribute('contentEditable'))) {
                        charParented.add(node);
                        node = node.parentNode;
                    }
                    let first = obj.nodes[0];
                    while (first &&
                        (!isInstanceOf(first, Element) || !first.getAttribute('contentEditable'))) {
                        if (charParented.has(first.previousSibling)) {
                            obj.chars = charMutation[type] + obj.chars;
                            obj.nodes.unshift(...new Array(len).fill(charMutation.target));
                            obj.offsets.unshift(...Array(len).keys());
                            return;
                        }
                        first = first.parentNode;
                    }
                }
                obj.chars += charMutation[type];
                obj.nodes.push(...new Array(len).fill(charMutation.target));
                obj.offsets.push(...Array(len).keys());
            });
            obj.chars = obj.chars.replace(/\u00A0/g, ' ');
            return obj;
        }
        _changedOffset(old, current) {
            // In the optimal case where both the range is correctly placed and the
            // data property of the composition event is correctly set, the above
            // analysis is capable of finding the precise text that was inserted.
            // However, if any of these two conditions are not met, the results
            // might be spectacularly wrong. For example, spell checking suggestions
            // on MacOS are displayed while hovering the mispelled word, regardless
            // of the current position of the range, and the correction does not
            // trigger an update of the range position either after correcting.
            // Example (`|` represents the text cursor):
            //   Previous content: 'My friend Christofe was here.|'
            //   Current content:  'My friend Christophe Matthieu was here.|'
            //   Actual text inserted by the keyboard: 'Christophe Matthieu'
            //   Result if data is set to 'Christophe' (length: 10): 'e was here'
            //   Result if data is not set (regardless of the range): ''
            //
            // Because the first analysis might not be enough in some cases, a
            // second analysis must be performed. This analysis aims at precisely
            // identifying the offset of the actual change in the text by comparing
            // the previous content with the current one from left to right to find
            // the start of the change and from right to left to find its end.
            // Example (`|` represents the text cursor):
            //   Previous content: 'My friend Christofe| was here.'
            //   Current content:  'My friend Christophe Matthieu| was here.'
            //   Observed change:  'My friend Christo[fe => phe Matthieu] was here.'
            //   Change offsets in the current content: {left: 17, right: 29}
            const oldText = old;
            const currentText = current;
            const maxLength = Math.max(oldText.length, currentText.length);
            let left = 0;
            for (; left < maxLength; left++) {
                if (oldText[left] !== currentText[left]) {
                    break;
                }
            }
            let right = 0;
            for (; right < maxLength; right++) {
                if (oldText[oldText.length - 1 - right] !== currentText[currentText.length - 1 - right]) {
                    break;
                }
            }
            return { left, right };
        }
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onMutation(mutationsList) {
            if (this._listen) {
                // we push the mutation because some browser (e.g. safari) separate mutations with
                // microtask.
                this._mutations.push(...mutationsList);
            }
        }
    }

    /**
     * Return the deepest child of a given container at a given offset, and its
     * adapted offset.
     *
     * @param container
     * @param offset
     */
    function targetDeepest(container, offset) {
        while (container.hasChildNodes()) {
            let childNodes;
            if (isInstanceOf(container, Element) && container.shadowRoot) {
                childNodes = container.shadowRoot.childNodes;
            }
            else {
                childNodes = container.childNodes;
            }
            if (offset >= childNodes.length) {
                container = container.lastChild;
                // The new container might be a text node, so considering only
                // the `childNodes` property would be wrong.
                offset = nodeLength$1(container);
            }
            else {
                container = childNodes[offset];
                offset = 0;
            }
        }
        return [container, offset];
    }
    /**
     * Return the length of a DOM Node.
     *
     * @param node
     */
    function nodeLength$1(node) {
        if (isInstanceOf(node, Text)) {
            return node.nodeValue.length;
        }
        else if (isInstanceOf(node, Element) && node.shadowRoot) {
            return node.shadowRoot.childNodes.length;
        }
        else {
            return node.childNodes.length;
        }
    }

    function elementFromPoint(x, y, root = document) {
        let element = root.elementFromPoint(x, y);
        if (element) {
            root = element.ownerDocument;
            while (element.shadowRoot) {
                root = element.shadowRoot;
                element = root.elementFromPoint(x, y);
                if (element.shadowRoot === root) {
                    if (root.firstElementChild) {
                        element = root.lastElementChild;
                        if (element.getBoundingClientRect().x > x) {
                            element = root.firstElementChild;
                        }
                    }
                    else {
                        break;
                    }
                }
            }
            if (isInstanceOf(element, HTMLIFrameElement)) {
                const rect = element.getBoundingClientRect();
                return elementFromPoint(x - rect.x, y - rect.y, element.contentDocument);
            }
            return element;
        }
    }
    function caretPositionFromPoint(x, y, root = document) {
        if ((!x && x !== 0) || (!y && y !== 0))
            return;
        // There is no cross-browser function for this, but the three functions below
        // cover all modern browsers as well as the shadow DOM.
        let caretPosition;
        const element = elementFromPoint(x, y, root);
        if (!element) {
            return;
        }
        root = getDocument(element);
        if (root.caretPositionFromPoint) {
            caretPosition = root.caretPositionFromPoint(x, y);
        }
        // Firefox can return an object with offsetNode = null.
        if (!(caretPosition === null || caretPosition === void 0 ? void 0 : caretPosition.offsetNode) && root instanceof ShadowRoot) {
            // Find the nearest node leaf or char in leaf.
            const position = caretPositionFromPointInShadowDom(x, y, element);
            if (position) {
                caretPosition = {
                    offsetNode: position.node,
                    offset: position.offset,
                };
            }
        }
        if (!(caretPosition === null || caretPosition === void 0 ? void 0 : caretPosition.offsetNode) && root.caretRangeFromPoint) {
            const caretRange = root.caretRangeFromPoint(x, y);
            caretPosition = caretRange && {
                offsetNode: caretRange.startContainer,
                offset: caretRange.startOffset,
            };
        }
        if (caretPosition === null || caretPosition === void 0 ? void 0 : caretPosition.offsetNode) {
            const [offsetNode, offset] = targetDeepest(caretPosition.offsetNode, caretPosition.offset);
            return { offsetNode, offset };
        }
    }
    function caretPositionFromPointInShadowDom(x, y, element) {
        const range = document.createRange();
        let distX = Infinity;
        let distY = Infinity;
        let node;
        let offset;
        const leafs = [];
        const elements = [element];
        while (elements.length) {
            const element = elements.shift();
            if (element.childNodes.length) {
                elements.push(...element.childNodes);
            }
            else {
                leafs.push(element);
            }
        }
        // Find the nearest node leaf.
        for (const leaf of leafs) {
            let box;
            if (isInstanceOf(leaf, Element)) {
                box = leaf.getBoundingClientRect();
            }
            else {
                range.setStart(leaf, 0);
                range.setEnd(leaf, leaf.textContent.length);
                box = range.getBoundingClientRect();
            }
            if (box.y + box.height < y) {
                continue;
            }
            let currentOffset = 0;
            let newDistY;
            if (box.y <= y && box.y + box.height >= y) {
                newDistY = 0;
                if (isInstanceOf(leaf, Text)) {
                    currentOffset = getNearestCharOffset(x, y, leaf);
                    range.setStart(leaf, currentOffset);
                    range.setEnd(leaf, currentOffset);
                    box = range.getBoundingClientRect();
                }
            }
            else {
                newDistY = Math.abs(box.y + box.height / 2 - y);
            }
            let newDistX;
            if (box.x <= x && box.x + box.width >= x) {
                newDistX = 0;
            }
            else {
                newDistX = Math.abs(box.x + box.width / 2 - x);
            }
            if (newDistY < distY) {
                distY = newDistY;
                distX = newDistX;
                node = leaf;
                offset = currentOffset;
            }
            else if (newDistY === distY &&
                ((newDistY === 0 && newDistX <= distX) || (newDistY !== 0 && newDistX > distX))) {
                distY = newDistY;
                distX = newDistX;
                node = leaf;
                offset = currentOffset;
            }
            if (distX === 0 && distY === 0) {
                break;
            }
        }
        return node && { node, offset };
    }
    function getNearestCharOffset(x, y, text) {
        // Search with a pseudo dichotomic for performance.
        const range = document.createRange();
        const posToTest = [[0, text.textContent.length]];
        const verticalMatches = [];
        while (posToTest.length) {
            const pos = posToTest.pop();
            range.setStart(text, pos[0]);
            range.setEnd(text, pos[1]);
            const box = range.getBoundingClientRect();
            if (box.y <= y && box.y + box.height >= y) {
                if (box.x <= x && box.x + box.width >= x) {
                    if (pos[1] - pos[0] <= 1) {
                        return box.x + box.width / 2 <= x ? pos[1] : pos[0];
                    }
                    const alf = Math.floor((pos[0] + pos[1]) / 2);
                    posToTest.push([pos[0], alf], [alf, pos[1]]);
                }
                else {
                    verticalMatches.push(pos);
                }
            }
        }
        // Did not found the char, eg: user click on left above the container like
        // the browser we get the nearest char at the same cursor of the pointer.
        let dist = Infinity;
        let offset = 0;
        for (const pos of verticalMatches.reverse()) {
            for (let i = pos[0]; i < pos[1]; i++) {
                range.setStart(text, i);
                range.setEnd(text, i + 1);
                const box = range.getBoundingClientRect();
                const dx = box.x + box.width / 2;
                const dy = box.y + box.height / 2;
                const delta = Math.pow(dx - x, 2) + Math.pow(dy - y, 4);
                if (delta <= dist) {
                    dist = delta;
                    offset = i + (dx < x ? 1 : 0);
                }
            }
        }
        return offset;
    }

    const navigationKey = new Set([
        'ArrowUp',
        'ArrowDown',
        'ArrowLeft',
        'ArrowRight',
        'PageUp',
        'PageDown',
        'End',
        'Home',
    ]);
    const trailingSpace = /\s*$/g;
    const inputTypeCommands = new Set([
        'historyUndo',
        'historyRedo',
        'formatBold',
        'formatItalic',
        'formatUnderline',
        'formatStrikeThrough',
        'formatSuperscript',
        'formatSubscript',
        'formatJustifyFull',
        'formatJustifyCenter',
        'formatJustifyRight',
        'formatJustifyLeft',
        'formatIndent',
        'formatOutdent',
        'formatRemove',
        'formatSetBlockTextDirection',
        'formatSetInlineTextDirection',
        'formatBackColor',
        'formatFontColor',
        'formatFontName',
    ]);
    /*
     * Regexp to test if a character is within an alphabet known by us.
     *
     * Note: Not all alphabets are taken into consideration and this RegExp is subject to be completed
     *       as more alphabets will be covered.
     *
     * Unicode range source:
     * - wikipedia
     * - google translate
     * - https://jrgraphix.net/r/Unicode/
     *
     * Tool to generate RegExp range:
     * - https://apps.timwhitlock.info/js/regex
     *
     * The strategy is to separate any word by selecting subsequent characters of a common alphabet.
     */
    const alphabetsContainingSpaces = new RegExp('(' +
        [
            '[а-яА-ЯЀ-ӿԀ-ԯ]+',
            '[Ͱ-Ͼἀ-῾]+',
            '[\u0530-\u058F]+',
            '[\u0600-۾ݐ-ݾ\u08a0-\u08fe]+',
            '[\u0900-\u0DFF]+',
            '[a-zA-Z]+',
            '[a-zA-ZÀ-ÿ]+',
            '[a-zA-ZĀ-ſ]+',
            '[a-zA-Zƀ-ɏ]+',
        ].join('|') +
        ')$');
    /**
     * These javascript event types might, in case of safari or spell-checking
     * keyboard, trigger dom events in multiple javascript stacks. They will require
     * to observe events during two ticks rather than after a single tick.
     */
    const MultiStackEventTypes = ['input', 'compositionend', 'selectAll'];
    /**
     * Create a promise that resolve once a timeout finish or when calling
     * `executeAndClear`.
     */
    class Timeout {
        constructor(fn, interval = 0) {
            this.fn = fn;
            this.pending = true;
            this.promise = new Promise((resolve) => {
                this._resolve = resolve;
                this.id = window.setTimeout(() => {
                    this.pending = false;
                    resolve(fn());
                }, interval);
            });
        }
        fire(result) {
            clearTimeout(this.id);
            this.pending = false;
            if (result) {
                this._resolve(result);
            }
            else {
                this._resolve(this.fn());
            }
        }
    }
    /**
     * ## The problems the normalizer solve
     * Browser and virtual keyboards on mobile does not implement properly the w3c
     * contenteditable specification and are inconsistent.
     *
     * ## Goal of the normalizer
     * 1. Hook any change that happend in an element called the `editable`.
     * 2. Trigger the same event for the same action accross all browsers and
     *    devices.
     *
     * ## Strategy
     * Hook all javascript events that modify the `editable` element. Then, trigger
     * normalized events.
     *
     * ## How to use this normalizer?
     * 1. Javascript Events occurs
     * 2. Normalize javascript one or more `Event` to one or more
     *    `NormalizedAction`.
     * 3. Update our `VDocument` in regard of triggered normalized actions.
     * 4. Render what changed in the `VDocument` HTML in the `editable`.
     *
     * The normalizer does not preventDefault most of the change in the editable
     * happen (the exception for "paste" and "drop" javascript event).
     *
     *
     * ## Handeling javascript events
     * A javascript event is almost never prevented and almost always alter the
     * editable in the DOM.
     *
     * The reason that we do not prevent default is because we need more
     * informations. The information modified in the dom (by observing observing
     * mutations).
     *
     * There is an exception for the event 'paste' and 'drop'.
     *
     * The reason to preventDefault 'paste' is because most of the time, browsers
     * paste content that need to be cleaned. For that reason we prevent it from
     * being inserted in the editable element but the informations can be found in
     * the triggered normalized events actions.
     *
     * The reason to preventDefault 'drop' is because some browsers change page when
     * dropping an image or an url that comes from the address bar (e.g. chrome).
     *
     * ## Supported browser and virtual keyboard
     * - Mac
     *   - Chrome
     *   - Firefox
     *   - Edge
     *   - Safari
     * - Windows
     *   - Chrome
     *   - Firefox
     *   - Edge
     *   - Safari
     * - Linux
     *   - Chrome
     *   - Firefox
     * - Android
     *   - Chrome
     *   - Firefox
     *   - Google keyboard
     *   - Swift keyboard
     * - IOS
     *   - Safari
     *   - Chrome
     *   - Firefox
     */
    class EventNormalizer {
        /**
         *
         * @param _isInEditable Callback to check if the node is in editable.
         * @param _triggerEventBatchOutside Callback to trigger for each user action.
         */
        constructor(_isInEditable, _isInEditor, _triggerEventBatchOutside) {
            this._isInEditable = _isInEditable;
            this._isInEditor = _isInEditor;
            this._triggerEventBatchOutside = _triggerEventBatchOutside;
            /**
             * Event listeners that are bound in the DOM by the normalizer on creation
             * and unbound on destroy.
             */
            this._eventListeners = [];
            /**
             * The MutationNormalizer used by the normalizer to watch the nodes that are
             * being modified since the normalizer creation until it is drestroyed.
             */
            this._mutationNormalizer = new MutationNormalizer();
            /**
             * Cache the state of modifiers keys on each keystrokes.
             */
            this._modifierKeys = {
                ctrlKey: false,
                altKey: false,
                metaKey: false,
                shiftKey: false,
            };
            /**
             * The current selection has to be observed as a result of a mousedown,
             * mousemove or mouseup or a nagivation key being triggered. However, this
             * cannot be done at the time of the mousedown itself since the browser
             * hasn't updated the selection in the DOM yet.  This observation is thus
             * deferred inside a `setTimeout`. If the browser gets overloaded, it might
             * fire the timeout after other events have happened, thus rendering the
             * observation meaningless since the selection would have changed yet again.
             * The observation timeout is stored in this variable in order to manually
             * fire its execution when an event that might change the selection is
             * triggered before the browser executed the timer.
             */
            this._selectionTimeouts = [];
            /**
             * This is a cache of the selection state used only for determining whether
             * a particular deleteContent is actually a deleteWord using the SwiftKey
             * mobile keyboard or not.
             */
            this._swiftKeyDeleteWordSelectionCache = [];
            /**
             * Normalised document and shadow root.
             */
            this._normalizedRoot = new Set();
            /**
             * Track if the mouse is currently down regardless of wether the mouse is in
             * the editable or not.
             */
            this._mousedown = false;
            this._processEventsUpUntilMoveEvent();
            this._bindDocumentEvent(document);
            // Create EventNormalizer for all already loaded iframes.
            for (const iframe of document.querySelectorAll('iframe')) {
                this._enableNormalizer(iframe);
            }
        }
        /**
         * Called when destroy the event normalizer.
         * Remove all added handlers.
         *
         */
        destroy() {
            this._mutationNormalizer.destroy();
            this._normalizedRoot.clear();
            this._unbindEvents();
            this._triggerEventBatch = null;
            this._isInEditable = null;
        }
        /**
         * Process the event timeouts.
         *
         * When an event will happen outside the editor in concurency settings, we
         * might need to capture the selection before the external event happen.
         * Otherwise the external event could be triggered on a wrong selection.
         * Also, we need to slice the `_currentStackObservation` to let characters
         * typed after the external command being sent after the external command.
         */
        processEventTimeouts() {
            // Set to false because it will not be a selectAll.
            this._followsPointerAction = false;
            this._processEventsUpUntilMoveEvent();
            // When the external event will be triggered, we do not know what kind
            // of change it has made in the document. We save the information by
            // setting the lastAction being undefined.
            this._lastAction = undefined;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Handler for document, iframe document or shadow dom.
         * If an event is triggered inside a shadow dom or an iframe, we add
         * handler in the shadow dom.
         *
         * @param root
         */
        _bindDocumentEvent(root) {
            this._normalizedRoot.add(root);
            this._bindEvent(root, 'selectionchange', this._onSelectionChange);
            this._bindEvent(root, 'load-iframe', this._onEventEnableNormalizer, true);
            this._bindEvent(root, 'mousedown', this._onEventEnableNormalizer, true);
            this._bindEvent(root, 'touchstart', this._onEventEnableNormalizer, true);
            if (isInstanceOf(root, Document)) {
                this._bindEvent(root, 'mousedown', this._onPointerDown);
                this._bindEvent(root, 'mousemove', this._onPointerMove);
                this._bindEvent(root, 'touchstart', this._onPointerDown);
                this._bindEvent(root, 'mouseup', this._onPointerUp);
                this._bindEvent(root, 'touchmove', this._onPointerMove);
                this._bindEvent(root, 'touchend', this._onPointerUp);
                this._bindEventInEditable(root, 'contextmenu', this._onContextMenu);
            }
            this._bindEvent(root, 'onkeyup', this._updateModifiersKeys);
            this._bindEventInEditable(root, 'keydown', this._onKeyDownOrKeyPress);
            this._bindEventInEditable(root, 'keypress', this._onKeyDownOrKeyPress);
            this._bindEventInEditable(root, 'compositionstart', this._registerEvent);
            this._bindEventInEditable(root, 'compositionupdate', this._registerEvent);
            this._bindEventInEditable(root, 'compositionend', this._registerEvent);
            this._bindEventInEditable(root, 'beforeinput', this._registerEvent);
            this._bindEventInEditable(root, 'input', this._registerEvent);
            this._bindEventInEditable(root, 'cut', this._onClipboard);
            this._bindEventInEditable(root, 'paste', this._onClipboard);
            this._bindEventInEditable(root, 'dragstart', this._onDragStart);
            this._bindEventInEditable(root, 'drop', this._onDrop);
            this._mutationNormalizer.attach(isInstanceOf(root, Document) ? root.body : root);
        }
        /**
         * Bind the occurence of given even type on the given target element to the
         * given listener function. See _unbindEvents to unbind all events bound by
         * calling this function.
         *
         * @param target element on which to listen for events
         * @param type of the event to listen
         * @param listener to call when the even occurs on the target
         */
        _bindEvent(target, type, listener, capture = true) {
            const boundListener = listener.bind(this);
            this._eventListeners.push({
                target: target,
                type: type,
                listener: boundListener,
                capture: capture,
            });
            target.addEventListener(type, boundListener, capture);
        }
        /**
         * Filter event from editable.
         *
         * @see _bindEvent
         *
         * @param target element on which to listen for events
         * @param type of the event to listen
         * @param listener to call when the even occurs on the target
         */
        _bindEventInEditable(target, type, listener) {
            const boundEditableListener = (ev) => {
                let eventTarget = 'target' in ev && ev.target;
                if (isInstanceOf(eventTarget, Element) &&
                    (eventTarget.shadowRoot || nodeName(eventTarget) === 'IFRAME')) {
                    this._enableNormalizer(eventTarget);
                }
                else {
                    const TouchEvent = window.TouchEvent; // Add the reference for firefox.
                    if (eventTarget && isInstanceOf(ev, MouseEvent)) {
                        eventTarget = this._getEventTarget(this._getPointerEventPosition(ev));
                    }
                    else if (eventTarget && isInstanceOf(ev, TouchEvent)) {
                        eventTarget = this._getEventTarget(this._getPointerEventPosition(ev));
                    }
                    else if (this._isInEditable(eventTarget)) {
                        eventTarget = eventTarget === null || eventTarget === void 0 ? void 0 : eventTarget.ownerDocument.getSelection().focusNode;
                    }
                    if (eventTarget && this._isInEditable(eventTarget)) {
                        listener.call(this, ev);
                    }
                    else {
                        this._mutationNormalizer.start();
                        this._triggerEventBatch(new Timeout(() => {
                            var _a;
                            const actions = [];
                            if ((_a = this._mutationNormalizer._mutations) === null || _a === void 0 ? void 0 : _a.length) {
                                const domNodes = [
                                    ...this._mutationNormalizer.getMutatedElements(this._mutationNormalizer._mutations),
                                ].filter(domNode => {
                                    const element = this._getClosestElement(domNode);
                                    return element === null || element === void 0 ? void 0 : element.isContentEditable;
                                });
                                actions.push({
                                    type: '@redraw',
                                    domNodes: new Set(domNodes),
                                });
                            }
                            this._mutationNormalizer.stop();
                            return { actions };
                        }).promise);
                    }
                }
            };
            this._bindEvent(target, type, boundEditableListener);
        }
        /**
         * Unbind all events bound by calls to _bindEvent.
         *
         */
        _unbindEvents() {
            this._eventListeners.forEach(({ target, type, listener, capture }) => {
                target.removeEventListener(type, listener, capture);
            });
        }
        /**
         * Register given event on the this.currentStackObservation._events queue.
         * If the queue is not yet initialized or has been cleared prior to this
         * call, re-initialize it. After a tick (setTimeout 0ms) the
         * '_processEvents' method is called. All events that happened during the
         * tick are read from the queue and the analysis tries to extract the
         * actions desired by the user such as insert, delete, backspace, spell
         * checking, special characters, etc.
         *
         * @see _processEvents
         */
        _registerEvent(ev) {
            var _a;
            this._checkMoveEvent();
            this._triggerSelectionTimeouts();
            const isNavigationEvent = ev.type === 'keydown' && navigationKey.has(ev.key);
            if (isNavigationEvent) {
                // We might need to trigger selection event before the navigation.
                this._processEventsUpUntilMoveEvent();
                // Manually triggering the processing of the current stack at this
                // point forces the rendering in the DOM of the result of the
                // observed events. This ensures that the new selection that is
                // eventually going to be set by the browser actually targets nodes
                // that are properly recognized in our abstration, which would not
                // be the case otherwise. See comment on `_stackTimeout`.
                if ((_a = this._stackTimeout) === null || _a === void 0 ? void 0 : _a.pending) {
                    this._stackTimeout.fire();
                }
                // TODO: no rendering in editable can happen before the analysis of
                // the selection. There should be a mechanism here that can be used
                // by the normalizer to block the rendering until this resolves.
                const keyboardSelectionTimeout = new Timeout(async () => {
                    return this._getSelectionBatchOnce();
                });
                this._triggerEventBatch(keyboardSelectionTimeout.promise);
                this._selectionTimeouts.push(keyboardSelectionTimeout);
            }
            else {
                if (this.currentStackObservation._events.length === 0) {
                    // The queue is not initialized or has been reset, so this is a
                    // new user action. Re-initialize the queue such that the
                    // analysis is not polluted by previous observations.
                    // this.initNextObservation();
                    const stack = this.currentStackObservation;
                    // Start observing mutations.
                    this._mutationNormalizer.start();
                    stack.mutations = this._mutationNormalizer._mutations;
                    // All events of this tick will be processed in the next one.
                    this._stackTimeout = new Timeout(() => {
                        return this._processEvents(stack);
                    });
                    this._triggerEventBatch(this._stackTimeout.promise);
                }
                // It is possible to have multiples keys that must trigger multiples
                // times that are being push in the same tick. To be able to handle
                // this case in `_processEvents`, we aggregate the informations in
                // `_multiKeyStack`.
                if (['keydown', 'keypress', 'input'].includes(ev.type)) {
                    // In the multiple key case, a 'keydown' is always the first
                    // event triggered between the three (keydown, keypress, input).
                    // So we create a new map each time a 'keydown' is registred.
                    if (ev.type === 'keydown') {
                        this.currentStackObservation._multiKeyStack.push({});
                        // Drop any selection that is not the last one before input.
                        this._swiftKeyDeleteWordSelectionCache = [
                            this._swiftKeyDeleteWordSelectionCache.pop(),
                        ];
                    }
                    const lastMultiKeys = this.currentStackObservation._multiKeyStack[this.currentStackObservation._multiKeyStack.length - 1];
                    if (lastMultiKeys) {
                        lastMultiKeys[ev.type] = ev;
                    }
                }
                this.currentStackObservation._eventsMap[ev.type] = ev;
                if (ev.type.startsWith('composition')) {
                    // In most cases we only need the last composition of the
                    // registred events
                    this.currentStackObservation._eventsMap.lastComposition = ev;
                }
                this.currentStackObservation._events.push(ev);
            }
        }
        /**
         * This function is the root of the normalization for most events.
         *
         * Process the events registered with `_regiterEvent` and call
         * `_triggerEventBatch` with one or more `NormalizedEvent` when sufficient
         * information has been gathered from all registred events.
         *
         * It could take up to two tick in the browser to gather all the sufficient
         * information. (e.g. Safari)
         *
         */
        /**
         * In some cases, the observation must be delayed to the next tick. In these
         * cases, this control variable will be set to true such that the analysis
         * process knows the current event queue processing has been delayed.
         */
        async _processEvents(currentStackObservation, secondTickObservation = false) {
            var _a;
            // In some cases, for example cutting with Cmd+X on Safari, the browser
            // triggers events in two different stacks. In such cases, observing
            // events occuring during one tick is not enough so we need to delay the
            // analysis after we observe events during two ticks instead.
            const needSecondTickObservation = currentStackObservation._events.every(ev => {
                return !MultiStackEventTypes.includes(ev.type);
            });
            if (needSecondTickObservation && !secondTickObservation) {
                return await new Promise((resolve) => {
                    setTimeout(() => {
                        resolve(this._processEvents(currentStackObservation, true));
                    });
                });
            }
            let normalizedActions = [];
            const keydownEvent = currentStackObservation._eventsMap.keydown;
            const keypressEvent = currentStackObservation._eventsMap.keypress;
            const inputEvent = currentStackObservation._eventsMap.input;
            const keyboardSelectAllEvent = currentStackObservation._eventsMap.keyboardSelectAll;
            const compositionEvent = currentStackObservation._eventsMap.lastComposition;
            const cutEvent = currentStackObservation._eventsMap.cut;
            const dropEvent = currentStackObservation._eventsMap.drop;
            const pasteEvent = currentStackObservation._eventsMap.paste;
            const compositionData = this._getCompositionData(currentStackObservation.mutations, compositionEvent, inputEvent);
            const isGoogleKeyboardBackspace = compositionData &&
                compositionData.compositionFrom.slice(0, -1) === compositionData.compositionTo &&
                keydownEvent &&
                keydownEvent.key === 'Unidentified';
            const inferredKeydownEvent = keydownEvent &&
                keydownEvent.key === 'Unidentified' &&
                this._inferKeydownEvent(inputEvent);
            //
            // First pass to get the informations
            //
            const key = (keypressEvent &&
                keypressEvent.key !== 'Unidentified' &&
                keypressEvent.key !== 'Dead' &&
                keypressEvent.key) ||
                (inputEvent && ((_a = inputEvent.data) === null || _a === void 0 ? void 0 : _a.length) === 1 && inputEvent.data) ||
                (keydownEvent &&
                    keydownEvent.key !== 'Unidentified' &&
                    keydownEvent.key !== 'Dead' &&
                    keydownEvent.key) ||
                (isGoogleKeyboardBackspace && 'Backspace') ||
                (keydownEvent &&
                    keydownEvent.key === 'Unidentified' &&
                    inferredKeydownEvent &&
                    inferredKeydownEvent.code);
            const inputType = (cutEvent && 'deleteByCut') ||
                (dropEvent && 'insertFromDrop') ||
                (pasteEvent && 'insertFromPaste') ||
                (key === 'Enter' && (inputEvent === null || inputEvent === void 0 ? void 0 : inputEvent.inputType) === 'insertText' && 'insertLineBreak') ||
                (inputEvent && inputEvent.inputType);
            // In case of accent inserted from a Mac, check that the char before was
            // one of the special accent temporarily inserted in the DOM (e.g. '^',
            // '`', ...).
            //
            const compositionReplaceOneChar = compositionData &&
                compositionData.compositionFrom.length === 1 &&
                compositionData.compositionTo.length === 1;
            const compositionAddOneChar = compositionData &&
                compositionData.compositionFrom === '' &&
                compositionData.compositionTo.length === 1;
            const isCompositionKeyboard = compositionAddOneChar || compositionReplaceOneChar;
            const isVirtualKeyboard = compositionEvent && key && key.length !== 1;
            // Compute the set of mutated elements accross all observed events.
            const mutatedElements = this._mutationNormalizer.getMutatedElements(currentStackObservation.mutations);
            this._mutationNormalizer.stop();
            // When the browser trigger multiples keydown at once, for each keydown
            // there is always also a keypress and an input that must be present.
            const possibleMultiKeydown = currentStackObservation._multiKeyStack.every(keydownMap => keydownMap.keydown &&
                keydownMap.keydown.key !== 'Unidentified' &&
                (keydownMap.input || keydownMap.keydown.key.length > 1));
            // if there is only one _multiKeyMap, it means that there is no
            // multiples keys pushed.
            if (currentStackObservation._multiKeyStack.length > 1 && possibleMultiKeydown) {
                currentStackObservation._multiKeyStack.map(keydownMap => {
                    const keyboardAction = this._getKeyboardAction(currentStackObservation.mutations, keydownMap.keydown.key, (keydownMap.input && keydownMap.input.inputType) || '', !!mutatedElements.size);
                    if (keyboardAction) {
                        normalizedActions.push(keyboardAction);
                    }
                });
            }
            else if (cutEvent) {
                const deleteContentAction = {
                    type: 'deleteContent',
                    direction: Direction.FORWARD,
                };
                // remove previously parsed keyboard action as we only want to remove
                normalizedActions.push(deleteContentAction);
            }
            else if (dropEvent) {
                normalizedActions.push(...this._getDropActions(dropEvent));
            }
            else if (pasteEvent) {
                normalizedActions.push(this._getDataTransferAction(pasteEvent));
            }
            else if (keyboardSelectAllEvent) {
                const selectAllAction = {
                    type: 'selectAll',
                };
                normalizedActions.push(selectAllAction);
            }
            else if (normalizedActions.length === 0 &&
                ((!compositionEvent && key) || isCompositionKeyboard || isVirtualKeyboard)) {
                const keyboardAction = this._getKeyboardAction(currentStackObservation.mutations, key, inputType, !!mutatedElements.size, keydownEvent);
                if (keyboardAction) {
                    normalizedActions.push(keyboardAction);
                }
                if (compositionReplaceOneChar) {
                    normalizedActions = compositionData.actions;
                }
            }
            else if (normalizedActions.length === 0 && compositionData) {
                normalizedActions.push(...compositionData.actions);
            }
            if (inputEvent && inputEvent.inputType && inputEvent.inputType.indexOf('format') === 0) {
                const formatName = inputEvent.inputType.replace('format', '').toLowerCase();
                const applyFormatAction = {
                    type: 'applyFormat',
                    format: formatName,
                    data: inputEvent.data,
                };
                normalizedActions.push(applyFormatAction);
            }
            else if (inputEvent && ['historyUndo', 'historyRedo'].includes(inputEvent.inputType)) {
                const historyAction = {
                    type: inputEvent.inputType,
                };
                normalizedActions.push(historyAction);
            }
            this.processEventTimeouts();
            if (normalizedActions.length > 0) {
                const batch = {
                    actions: normalizedActions,
                    mutatedElements,
                };
                if (inferredKeydownEvent) {
                    batch.inferredKeydownEvent = inferredKeydownEvent;
                }
                return batch;
            }
            return { actions: [] };
        }
        /**
         * Process the click, navigation, keydown event and beggin a new
         * `currentStackObservation` to separate it from the previous one.
         *
         * When the system is under pressure, the events will be triggered on the
         * same tick. We need reset the normalizer stack `currentStackObservation`
         * check if there was a move event before and trigger all the timeout.
         */
        _processEventsUpUntilMoveEvent(check = true) {
            var _a;
            if (check)
                this._checkMoveEvent();
            this._triggerSelectionTimeouts();
            // See comment on `_stackTimeout`.
            if ((_a = this._stackTimeout) === null || _a === void 0 ? void 0 : _a.pending) {
                this._stackTimeout.fire();
            }
            this.currentStackObservation = {
                _events: [],
                _multiKeyStack: [],
                _eventsMap: {},
                mutations: undefined,
            };
        }
        _getCompositionData(mutations, compositionEvent, inputEvent) {
            if (compositionEvent && inputEvent) {
                let compositionDataString = compositionEvent.data;
                // Specific case for SwiftKey. Swiftkey add a space in the
                // inputEvent but not in the composition event.
                const isSwiftKeyAutocorrect = inputEvent.inputType === 'insertText' &&
                    inputEvent.data &&
                    inputEvent.data.length === 1 &&
                    inputEvent.data !== compositionDataString &&
                    inputEvent.data === ' ';
                if (isSwiftKeyAutocorrect) {
                    compositionDataString += ' ';
                }
                return this._getCompositionFromString(mutations, compositionDataString);
            }
            else if (inputEvent && inputEvent.inputType === 'insertReplacementText') {
                // safari trigger an input with 'insertReplacementText' when it
                // correct a word.
                return this._getCompositionFromString(mutations, inputEvent.data);
            }
        }
        /**
         * Infer a `KeyboardEvent` `code` from an `InputEvent`
         */
        _inferKeydownEvent(inputEvent) {
            let code;
            if (inputEvent.inputType === 'insertParagraph') {
                code = 'Enter';
            }
            else if (inputEvent.inputType === 'deleteContentBackward') {
                code = 'Backspace';
            }
            else if (inputEvent.inputType === 'deleteContentForward') {
                code = 'Delete';
            }
            if (code) {
                return Object.assign(Object.assign({}, this._modifierKeys), { key: code, code: code });
            }
        }
        /**
         * Get a keyboard action if something has happned in the DOM (insert,
         * delete, navigation).
         *
         * @param key
         * @param inputType
         * @param hasMutataedElements
         * @param isMultiKey
         */
        _getKeyboardAction(mutations, key, inputType, hasMutatedElements, keydownEvent) {
            const isInsertOrRemoveAction = hasMutatedElements && !inputTypeCommands.has(inputType);
            if (isInsertOrRemoveAction) {
                if (key === 'Backspace' || key === 'Delete') {
                    return this._getRemoveAction(mutations, key, inputType, keydownEvent);
                }
                else if (key === 'Enter') {
                    if (inputType === 'insertLineBreak') {
                        const insertLineBreakAction = {
                            type: 'insertLineBreak',
                        };
                        return insertLineBreakAction;
                    }
                    else {
                        const insertParagraphAction = {
                            type: 'insertParagraphBreak',
                        };
                        return insertParagraphAction;
                    }
                }
                else if (key.length === 1) {
                    const insertTextAction = {
                        type: 'insertText',
                        text: key,
                    };
                    return insertTextAction;
                }
            }
        }
        /**
         * Get the actions for a event `ev` of type drop.
         *
         * @param ev
         */
        _getDropActions(ev) {
            const actions = [];
            if (ev.draggingFromEditable && !ev.files.length) {
                const selection = document.getSelection();
                if (!selection.isCollapsed) {
                    const deleteContentAction = {
                        type: 'deleteContent',
                        direction: Direction.FORWARD,
                    };
                    actions.push(deleteContentAction);
                }
            }
            const setSelectionAction = {
                type: 'setSelection',
                domSelection: ev.selection,
            };
            actions.push(setSelectionAction);
            actions.push(this._getDataTransferAction(ev));
            return actions;
        }
        /**
         * Extract informations from dataTranser to know what has been done in the
         * DOM and return it a normalizedAction.
         *
         * when drag and dropping, most browsers wrap the element with tags and
         * styles.  And when dropping in the (same or different) browser, there is
         * many differents behavior.
         *
         * Some browser reload the page when dropping (img or link (from status
         * bar)).  For this reason, we block all the content from being added in the
         * editable. (otherwise reloading happen).
         *
         * Note: The user can drag and drop a link or an img, from the browser
         * navigation bar.
         *
         */
        _getDataTransferAction(dataTransfer) {
            if (dataTransfer.files.length) {
                const insertFilesAction = {
                    type: 'insertFiles',
                    files: dataTransfer.files,
                };
                return insertFilesAction;
            }
            const uri = dataTransfer['text/uri-list'];
            // eslint-disable-next-line no-control-regex
            const html = dataTransfer['text/html'].replace(/\x00/g, ''); // replace for drag&drop from firefox to chrome
            const text = dataTransfer['text/plain'];
            if (html && uri) {
                const temp = document.createElement('temp');
                temp.innerHTML = html;
                const element = temp.querySelector('a, img');
                if (element) {
                    if (!dataTransfer.draggingFromEditable &&
                        nodeName(element) === 'A' &&
                        element.innerHTML === '') {
                        // add default content if it's external link
                        element.innerHTML = uri;
                    }
                    const insertHtmlAction = {
                        type: 'insertHtml',
                        html: element.outerHTML,
                        text: uri,
                    };
                    return insertHtmlAction;
                }
                else {
                    const insertHtmlAction = {
                        type: 'insertHtml',
                        html: html,
                        text: uri,
                    };
                    return insertHtmlAction;
                }
            }
            else if (html) {
                const insertHtmlAction = {
                    type: 'insertHtml',
                    // Cross browser drag & drop will add useless meta tag at the
                    // beginning of the html.
                    html: html && html.replace(/^<meta[^>]+>/, ''),
                    text: text,
                };
                return insertHtmlAction;
            }
            else if (uri) {
                const insertHtmlAction = {
                    type: 'insertHtml',
                    html: '<a href="' + uri + '">' + uri + '</a>',
                    text: uri,
                };
                return insertHtmlAction;
            }
            else {
                const insertTextAction = {
                    type: 'insertText',
                    text: text,
                };
                return insertTextAction;
            }
        }
        /**
         * Process the composition to identify the text that was inserted.
         *
         * Attention, there is a case impossible to retrieve the complete
         * information. In the case of we don't have the event data and mutation
         * and we might have "a b" change from a composition to "a c". We receive
         * the word change "b" to "c" instead of "a b" to "a c".
         *
         */
        _getCompositionFromString(mutations, compositionData) {
            const charMap = this._mutationNormalizer.getCharactersMapping(mutations);
            // The goal of this function is to precisely find what was inserted by
            // a keyboard supporting spell-checking and suggestions.
            // Example (`|` represents the text cursor):
            //   Previous content: 'My friend Christofe| was here.'
            //   Current content:  'My friend Christophe Matthieu| was here.'
            //   Actual text inserted by the keyboard: 'Christophe Matthieu'
            let index = charMap.index;
            let insert = charMap.insert;
            let remove = charMap.remove;
            if (insert === remove && compositionData) {
                insert = compositionData;
                remove = compositionData;
            }
            // In mutation:
            // - we get the changes
            // - try to extract the word or a part of the word (with or without
            //   position)
            // - locate: where the change has been made
            const selection = this._getSelection();
            // if index === -1 it means we could not find the position in the mutated elements
            if (index === -1) {
                // It is possible that the index of the observed change are
                // undefined
                // Example (`|` represents the collapsed selection):
                //   Previous content: 'aa aa aa| aa aa'
                //   Current content:  'aa aa aa aa| aa aa'
                //   Actual text inserted by the keyboard: 'aa '
                //   Observed change:  'aa ]aa aa aa aa[ aa'
                // TODO CHM: the below min/max does not cover all cases
                // With most spell-checking mobile keyboards, the range is set right
                // after the inserted text. It can then be used as a marker to
                // identify the end of the change.
                let insertEnd = 0;
                // The text has been flattened in the characters mapping. When
                // the index of the node has been found, use the range offset
                // to find the index of the character proper.
                insertEnd += selection.focusOffset;
                index = insertEnd - insert.length;
            }
            else {
                let offset = index + insert.length - 1;
                if (charMap.current.nodes[offset] &&
                    (selection.focusNode !== charMap.current.nodes[offset] ||
                        selection.focusOffset !== charMap.current.offsets[offset] + 1)) {
                    offset++;
                    while (charMap.current.nodes[offset] &&
                        (selection.focusNode !== charMap.current.nodes[offset] ||
                            selection.focusOffset > charMap.current.offsets[offset])) {
                        const text = charMap.current.chars[offset];
                        insert += text;
                        remove += text;
                        offset++;
                    }
                }
            }
            const before = charMap.previous.chars.slice(0, index);
            const match = before.match(alphabetsContainingSpaces);
            if (match &&
                (insert === '' || alphabetsContainingSpaces.test(insert)) &&
                (remove === '' || alphabetsContainingSpaces.test(remove))) {
                // the word is write in a alphabet which contain space, search
                // to complete the change and include the rest of the word
                const beginWord = match[1];
                remove = beginWord + remove;
                insert = beginWord + insert;
                index -= beginWord.length;
                // Some virtual keyboards (e.g. SwiftKey) add a space at the end of
                // each composition such that the insert is ' '. We filter out those
                // events.
            }
            else if (compositionData &&
                insert &&
                (remove || insert !== ' ') &&
                compositionData !== insert) {
                const charIndex = compositionData.lastIndexOf(insert);
                if (charIndex !== -1) {
                    index -= charIndex;
                    insert = compositionData;
                    const len = remove.length + charIndex;
                    remove = charMap.previous.chars.slice(index, index + len + 1);
                }
            }
            // Trim the trailing space added by some virtual keyboards (e.g.
            // SwiftKey).
            const removedEndSpace = remove[remove.length - 1] === ' ';
            const insertedEndSpace = insert[insert.length - 1] === ' ';
            let rawRemove = remove;
            let rawInsert = insert;
            if (insertedEndSpace && removedEndSpace) {
                rawRemove = rawRemove.slice(0, -1);
            }
            if (insertedEndSpace) {
                rawInsert = rawInsert.slice(0, -1);
            }
            const previousNodes = charMap.previous.nodes;
            const previousOffsets = charMap.previous.offsets;
            const lastPreviousNode = previousNodes[previousNodes.length - 1];
            const lastPreviousOffset = previousOffsets[previousOffsets.length - 1] + 1;
            const offsetEnd = index + rawRemove.length;
            const setSelectionAction = {
                type: 'setSelection',
                domSelection: {
                    anchorNode: previousNodes[index] || lastPreviousNode,
                    anchorOffset: index in previousOffsets ? previousOffsets[index] : lastPreviousOffset,
                    focusNode: previousNodes[offsetEnd] || lastPreviousNode,
                    focusOffset: offsetEnd in previousOffsets ? previousOffsets[offsetEnd] : lastPreviousOffset,
                    direction: Direction.FORWARD,
                },
            };
            const insertTextAction = {
                type: 'insertText',
                text: rawInsert,
            };
            const actions = [setSelectionAction, insertTextAction];
            if (insertedEndSpace) {
                if (removedEndSpace) {
                    index += rawRemove.length;
                    const setSelectionAction = {
                        type: 'setSelection',
                        domSelection: {
                            anchorNode: previousNodes[index],
                            anchorOffset: previousOffsets[index],
                            focusNode: previousNodes[offsetEnd],
                            focusOffset: previousOffsets[index + 1],
                            direction: Direction.FORWARD,
                        },
                    };
                    actions.push(setSelectionAction);
                }
                const insertTextAction = {
                    type: 'insertText',
                    text: ' ',
                };
                actions.push(insertTextAction);
            }
            return {
                compositionFrom: remove,
                compositionTo: insert,
                actions: actions,
            };
        }
        /**
         * Process the given compiled event as a backspace/delete to identify the
         * text that was removed and return an array of the corresponding
         * NormalizedAction.
         *
         * In the case of cut event, the direction will be `Direction.FORWARD`.
         *
         */
        _getRemoveAction(mutations, key, inputType, keydownEvent) {
            const direction = key === 'Backspace' ? Direction.BACKWARD : Direction.FORWARD;
            // Check if this is a deleteWord from the SwiftKey mobile keyboard. This
            // be triggered by long-pressing the backspace key, however SwiftKey
            // does not trigger a proper deleteWord event so we must detect it.
            // This is extremely ad-hoc for the particular case of SwiftKey and we
            // need to retrieve the selection as it was right before the deletion.
            const selection = this._swiftKeyDeleteWordSelectionCache[0];
            this._swiftKeyDeleteWordSelectionCache.length = 0;
            // Get characterMapping to retrieve which word has been deleted.
            const characterMapping = this._mutationNormalizer.getCharactersMapping(mutations);
            const isCollapsed = selection &&
                selection.anchorNode === selection.focusNode &&
                selection.anchorOffset === selection.focusOffset;
            const isSwiftKeyDeleteWord = (inputType === 'deleteContentForward' || inputType === 'deleteContentBackward') &&
                (keydownEvent === null || keydownEvent === void 0 ? void 0 : keydownEvent.key) === 'Unidentified' &&
                isCollapsed &&
                characterMapping.remove.length > 1;
            if (inputType === 'deleteWordForward' ||
                inputType === 'deleteWordBackward' ||
                isSwiftKeyDeleteWord) {
                const deleteWordAction = {
                    type: 'deleteWord',
                    direction: direction,
                    text: characterMapping.remove,
                };
                return deleteWordAction;
            }
            if (inputType === 'deleteHardLineForward' ||
                inputType === 'deleteHardLineBackward' ||
                inputType === 'deleteSoftLineForward' ||
                inputType === 'deleteSoftLineBackward') {
                const deleteHardLineAction = {
                    type: 'deleteHardLine',
                    direction: direction,
                    domSelection: {
                        anchorNode: characterMapping.previous.nodes[characterMapping.index],
                        anchorOffset: characterMapping.previous.offsets[characterMapping.index],
                        focusNode: characterMapping.previous.nodes[characterMapping.index + characterMapping.remove.length - 1],
                        focusOffset: characterMapping.previous.offsets[characterMapping.index + characterMapping.remove.length - 1] + 1,
                        direction: direction,
                    },
                };
                return deleteHardLineAction;
            }
            const deleteContentAction = {
                type: 'deleteContent',
                direction: direction,
            };
            return deleteContentAction;
        }
        /**
         * Return true if the given node can be considered a textual node, that is
         * a text node or a BR node.
         *
         * @param node
         */
        _isTextualNode(node) {
            return isInstanceOf(node, Text) || nodeName(node) === 'BR';
        }
        /**
         * Get the current selection from the DOM. If an event is given, then the
         * selection must be at least partially contained in the target of the
         * event, otherwise it means it took no part in it. In this case, return the
         * selection from the caret position.
         *
         * @param [ev]
         */
        _getSelection(ev) {
            var _a;
            let selectionDescription;
            let target;
            let root;
            if (ev) {
                target = this._getEventTarget(ev);
                root = getDocument(target);
            }
            else if ((_a = this._initialCaretPosition) === null || _a === void 0 ? void 0 : _a.offsetNode) {
                root = getDocument(this._initialCaretPosition.offsetNode);
            }
            else {
                root = document;
            }
            const selection = root.getSelection
                ? root.getSelection()
                : root.ownerDocument.getSelection();
            let forward;
            if (selection && selection.rangeCount !== 0) {
                // The selection direction is sorely missing from the DOM api.
                const nativeRange = selection.getRangeAt(0);
                if (selection.anchorNode === selection.focusNode) {
                    forward = selection.anchorOffset <= selection.focusOffset;
                }
                else {
                    forward = selection.anchorNode === nativeRange.startContainer;
                }
                selectionDescription = {
                    anchorNode: selection.anchorNode,
                    anchorOffset: selection.anchorOffset,
                    focusNode: selection.focusNode,
                    focusOffset: selection.focusOffset,
                    direction: forward ? Direction.FORWARD : Direction.BACKWARD,
                };
            }
            // If an event is given, then the range must be at least partially
            // contained in the target of the event, otherwise it means it took no
            // part in it. In this case, consider the caret position instead.
            // This can happen when target is an input or a contenteditable=false.
            if (target && target.nodeType) {
                const caretPosition = this._getEventCaretPosition(ev);
                if (selectionDescription &&
                    !target.contains(selectionDescription.anchorNode) &&
                    !target.contains(selectionDescription.focusNode) &&
                    caretPosition.offsetNode === target) {
                    selectionDescription = {
                        anchorNode: caretPosition.offsetNode,
                        anchorOffset: caretPosition.offset,
                        focusNode: caretPosition.offsetNode,
                        focusOffset: caretPosition.offset,
                        direction: Direction.FORWARD,
                    };
                }
            }
            return selectionDescription;
        }
        /**
         * Check if the given range is selecting the whole editable.
         *
         * @param selection
         */
        _isSelectAll(selection) {
            // The selection from the context menu or a shortcut never have
            // direction forward.
            if (selection.direction === Direction.BACKWARD) {
                return false;
            }
            let startContainer = selection.anchorNode;
            let startOffset = selection.anchorOffset;
            let endContainer = selection.focusNode;
            let endOffset = selection.focusOffset;
            const doc = startContainer.ownerDocument;
            // The selection might still be on a node which has since been removed.
            let invalidStart = true;
            let domNode = startContainer;
            while (domNode && invalidStart) {
                if (isInstanceOf(domNode, ShadowRoot) && domNode.host) {
                    domNode = domNode.host;
                }
                else if (doc.body.contains(domNode)) {
                    invalidStart = false;
                }
                else {
                    domNode = domNode.parentNode;
                }
            }
            let invalidEnd = true;
            domNode = endContainer;
            while (domNode && invalidEnd) {
                if (isInstanceOf(domNode, ShadowRoot) && domNode.host) {
                    domNode = domNode.host;
                }
                else if (doc.body.contains(domNode)) {
                    invalidEnd = false;
                }
                else {
                    domNode = domNode.parentNode;
                }
            }
            const invalidSelection = invalidStart || invalidEnd;
            // The selection might be collapsed in which case there is no selection.
            const onlyOneNodeSelected = startContainer === endContainer;
            const noCharacterSelected = startOffset === endOffset;
            const isCollapsed = onlyOneNodeSelected && noCharacterSelected;
            // If the selection is invalid or the selection is collapsed, it
            // definitely does not correspond to a select all action.
            if (invalidSelection || isCollapsed) {
                return false;
            }
            [startContainer, startOffset] = targetDeepest(startContainer, startOffset);
            [endContainer, endOffset] = targetDeepest(endContainer, endOffset);
            // Look for visible nodes in editable that would be outside the range.
            const startInsideEditable = this._isInEditable(startContainer);
            const endInsideEditable = this._isInEditable(endContainer);
            const endLength = isInstanceOf(endContainer, Text)
                ? removeFormattingSpace(endContainer).replace(trailingSpace, '').length
                : nodeLength(endContainer);
            if (startInsideEditable && endInsideEditable) {
                return (startOffset === 0 &&
                    this._isAtVisibleEdge(startContainer, 'start') &&
                    endOffset >= endLength &&
                    this._isAtVisibleEdge(endContainer, 'end'));
            }
            else if (startInsideEditable) {
                return startOffset === 0 && this._isAtVisibleEdge(startContainer, 'start');
            }
            else if (endInsideEditable) {
                return endOffset >= endLength && this._isAtVisibleEdge(endContainer, 'end');
            }
            else {
                return true;
            }
        }
        /**
         * Return true if the given element is at the edge of the editable node in
         * the given direction. An element is considered at the edge of the editable
         * node if there is no other visible element in editable that is located
         * beyond it in the given direction.
         *
         * @param node to check whether it is at the visible edge
         * @param side from which to look for textual nodes ('start' or 'end')
         */
        _isAtVisibleEdge(node, side) {
            const editable = this._getClosestElement(node).closest('[contentEditable=true]');
            // Start from the top and do a depth-first search trying to find a
            // visible node that would be in editable and beyond the given element.
            let currentNode = editable;
            const child = side === 'start' ? 'firstChild' : 'lastChild';
            const sibling = side === 'start' ? 'nextSibling' : 'previousSibling';
            let crossVisible = false;
            while (currentNode) {
                if (currentNode === node) {
                    // The element was reached without finding another visible node.
                    return !crossVisible;
                }
                if (this._isTextualNode(currentNode) && this._isVisible(currentNode, editable)) {
                    // There is a textual node in editable beyond the given element.
                    crossVisible = true;
                }
                // Continue the depth-first search.
                if (currentNode[child]) {
                    currentNode = currentNode[child];
                }
                else if (currentNode[sibling]) {
                    currentNode = currentNode[sibling];
                }
                else if (currentNode.parentNode === editable) {
                    // Depth-first search has checked all elements in editable.
                    return true;
                }
                else {
                    let ancestor = currentNode.parentNode;
                    currentNode = ancestor[sibling];
                    // When checking from the end we need to go up the ancestors
                    // tree to find one which does have a previous sibling.
                    while (!currentNode && side === 'end') {
                        ancestor = ancestor.parentNode;
                        currentNode = ancestor[sibling];
                    }
                }
            }
            return false;
        }
        /**
         * Determine if a node is considered visible.
         */
        _isVisible(el, editable) {
            if (el === document) {
                return false;
            }
            if (el === editable) {
                // The editable node was reached without encountering a hidden
                // container. The editable node is supposed to be visible.
                return true;
            }
            // A <br> element with no next sibling is never visible.
            if (nodeName(el) === 'BR' && !el.nextSibling) {
                return false;
            }
            const style = window.getComputedStyle(this._getClosestElement(el));
            if (style.display === 'none' || style.visibility === 'hidden') {
                return false;
            }
            return this._isVisible(el.parentNode, editable);
        }
        /**
         * Return the node and offset targeted by a event, including if the target
         * is inside a shadow element
         *
         * @param ev
         */
        _getEventCaretPosition(ev) {
            const target = ev.target;
            let caretPosition = caretPositionFromPoint(ev.x, ev.y, target.ownerDocument);
            if (!caretPosition) {
                caretPosition = { offsetNode: ev.target, offset: 0 };
            }
            return caretPosition;
        }
        /**
         * Use the position to get the target from the event (including the target
         * in shadow element)
         *
         * @param ev
         */
        _getEventTarget(ev) {
            const target = ev.target;
            return elementFromPoint(ev.x, ev.y, target.ownerDocument) || target;
        }
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Catch setSelection and selectAll actions
         *
         * @param {MouseEvent} ev
         */
        _onContextMenu(ev) {
            this._preProcessPointerEvent(this._getPointerEventPosition(ev));
            // The _clickedInEditable property is used to assess whether the user is
            // currently changing the selection by using the mouse. If the context
            // menu ends up opening, the user is definitely not selecting.
            this._mousedownInEditable = false;
        }
        /**
         * Catch Enter, Backspace, Delete and insert actions
         *
         * @param {KeyboardEvent} ev
         */
        _onKeyDownOrKeyPress(ev) {
            this._updateModifiersKeys(ev);
            this._registerEvent(ev);
            const selection = this._getSelection();
            if (!selection) {
                this._initialCaretPosition = undefined;
                return;
            }
            const [offsetNode, offset] = targetDeepest(selection.anchorNode, selection.anchorOffset);
            this._initialCaretPosition = { offsetNode, offset };
        }
        /**
         * Set internal properties of the pointer down event to retrieve them later
         * on when the user stops dragging its selection and the selection has
         * changed.
         *
         * @param {MouseEvent} ev
         */
        _onPointerDown(ev) {
            // Don't trigger events on the editable if the click was done outside of
            // the editable itself or on something else than an element.
            const pointerEventPosition = this._getPointerEventPosition(ev);
            const target = this._getEventTarget(pointerEventPosition);
            const caretPosition = this._getEventCaretPosition(pointerEventPosition);
            this._mousedown = true;
            if (target && this._isInEditable(caretPosition.offsetNode)) {
                this._mousedownInEditable = true;
                this._initialCaretPosition = caretPosition;
                this._followsPointerAction = true;
                this._preProcessPointerEvent(this._getPointerEventPosition(ev));
            }
            else {
                this._mousedownInEditable = false;
                this._initialCaretPosition = undefined;
            }
        }
        /**
         * Catch setSelection actions coming from clicks.
         *
         * @param ev
         */
        _onPointerUp(ev) {
            this._lastMoveEvent = undefined;
            this._mousedown = false;
            this._preProcessPointerEvent(this._getPointerEventPosition(ev));
        }
        /**
         * When the pointer move and a click was previously in the editable, set
         * the variable _lastMoveEvent. See `_checkMoveEvent`.
         */
        _onPointerMove(ev) {
            if (this._mousedown && this._mousedownInEditable) {
                this._lastMoveEvent = this._getPointerEventPosition(ev);
            }
        }
        /**
         *  We need to check the move event for two case that happend directly after
         *  a mousemove:
         *  - An external event happen and the selection could have changed.
         *    Therefore, we need to set the position before the external event
         *    happen.
         *  - A keyboardevent happen and we need to send the last position of the
         *    pointer.
         */
        _checkMoveEvent() {
            if (this._lastMoveEvent) {
                this._preProcessPointerEvent(this._lastMoveEvent, false);
                this._lastMoveEvent = undefined;
            }
        }
        /**
         * Analyze a change of selection to trigger a pointer event for it.
         *
         * @param ev
         */
        _getSelectionBatchOnce(ev) {
            const eventBatch = {
                actions: [],
                mutatedElements: new Set([]),
            };
            const selection = this._getSelection(ev);
            if (selection) {
                const selectionAction = this._getSelectionAction(selection);
                if (selectionAction)
                    eventBatch.actions.push(selectionAction);
            }
            return eventBatch;
        }
        /**
         * Get a new selection action only if it differ from the last one.
         */
        _getSelectionAction(selection) {
            if (this._isLastSelectionDifferent(selection)) {
                const setSelectionAction = {
                    type: 'setSelection',
                    domSelection: selection,
                };
                return setSelectionAction;
            }
        }
        /**
         * Return a node's parent if it's not an instance of `Element`.
         *
         * @param node
         */
        _getClosestElement(node) {
            return isInstanceOf(node, Element) ? node : node.parentElement;
        }
        /**
         * If the drag start event is observed by the normalizer, it means the
         * dragging started in the editable itself. It means the user is dragging
         * content around in the editable zone.
         *
         */
        _onDragStart() {
            this._draggingFromEditable = true;
        }
        /**
         * Convert the drop event into a custom pre-processed format in order to
         * store additional information that are specific to this point in time,
         * such as the current range and the initial caret position.
         *
         * In some browser we need to infer the drop from other events.
         *
         * Example of droppable object are file, text, url.
         *
         * Drop event can originate from another software, outside the editor zone
         * or inside the editor zone.
         *
         * @param ev
         */
        _onDrop(ev) {
            // Prevent default behavior (e.g. prevent file from being opened in the
            // current tab).
            ev.preventDefault();
            const transfer = ev.dataTransfer;
            const files = [];
            for (const item of transfer.items) {
                if (item.kind === 'file') {
                    files.push(item.getAsFile());
                }
            }
            const caretPosition = this._getEventCaretPosition(ev);
            const dropEvent = {
                type: 'drop',
                'text/plain': transfer.getData('text/plain'),
                'text/html': transfer.getData('text/html'),
                'text/uri-list': transfer.getData('text/uri-list'),
                files: files,
                originalEvent: ev,
                selection: {
                    anchorNode: caretPosition.offsetNode,
                    anchorOffset: caretPosition.offset,
                    focusNode: caretPosition.offsetNode,
                    focusOffset: caretPosition.offset,
                    direction: Direction.FORWARD,
                },
                caretPosition: caretPosition,
                draggingFromEditable: this._draggingFromEditable,
            };
            this._registerEvent(dropEvent);
            // Dragging is over, reset this property.
            this._draggingFromEditable = false;
        }
        /**
         * Convert the clipboard event into a custom pre-processed format in order
         * to store additional information that are specific to this point in time,
         * such as the current range and the initial caret position.
         *
         * @param ev
         */
        _onClipboard(ev) {
            if (ev.type === 'paste') {
                // Prevent the default browser wild pasting behavior.
                ev.preventDefault();
            }
            const clipboard = ev.clipboardData;
            const selection = this._getSelection();
            if (!selection)
                return;
            const pasteEvent = {
                type: ev.type,
                'text/plain': clipboard.getData('text/plain'),
                'text/html': clipboard.getData('text/html'),
                'text/uri-list': clipboard.getData('text/uri-list'),
                files: [],
                originalEvent: ev,
                selection: selection,
                caretPosition: this._initialCaretPosition,
                draggingFromEditable: false,
            };
            this._registerEvent(pasteEvent);
        }
        /**
         * Update the modifiers keys to know which modifiers keys are pushed.
         *
         * @param e
         */
        _updateModifiersKeys(e) {
            this._modifierKeys = {
                ctrlKey: e.ctrlKey,
                altKey: e.altKey,
                metaKey: e.metaKey,
                shiftKey: e.shiftKey,
            };
        }
        /**
         * On each change of selection, check if it might be a "selectAll" action.
         *
         * A "selectAll" action can be triggered by:
         * - The shortcut 'CTRL+A'
         * - A user mapping of the OS or browser
         * - From the context menu
         * - Programmatically
         */
        _onSelectionChange() {
            if (!this._initialCaretPosition) {
                // Filter the events because we can have some Shadow root and each
                // normaliser bind event on document.
                return;
            }
            const selection = this._getSelection();
            if (!selection) {
                return;
            }
            this._swiftKeyDeleteWordSelectionCache.push(selection);
            const keydownEvent = this.currentStackObservation._eventsMap.keydown;
            const isNavEvent = (keydownEvent === null || keydownEvent === void 0 ? void 0 : keydownEvent.type) === 'keydown' && navigationKey.has(keydownEvent.key);
            if (isNavEvent) {
                const navTimeout = new Timeout(() => {
                    const selectionBatch = this._getSelectionBatchOnce();
                    return selectionBatch;
                });
                this._triggerEventBatch(navTimeout.promise);
                this._selectionTimeouts.push(navTimeout);
            }
            else {
                // This heuristic protects against a costly `_isSelectAll` call.
                const modifiedKeyEvent = this._modifierKeys.ctrlKey || this._modifierKeys.metaKey;
                const heuristic = modifiedKeyEvent || this._followsPointerAction;
                const isSelectAll = heuristic && this._isSelectAll(selection);
                if (isSelectAll && !this._currentlySelectingAll) {
                    if (modifiedKeyEvent) {
                        // This select all was triggered from the keyboard. Add a
                        // fake selectAll event to the queue as a marker for
                        // `_processEvents` to register that a select all was
                        // triggered in this stack.
                        this._registerEvent(new CustomEvent('keyboardSelectAll'));
                    }
                    else {
                        // The target of the select all specifies where the user caret
                        // was when the select all was triggered.
                        const selectAllAction = {
                            type: 'selectAll',
                        };
                        // We did not find any case where a select all triggered
                        // from the mouse actually resulted in a mutation, so the
                        // mutation normalizer is not listnening in this case. If it
                        // happens to be insufficient later on, the mutated elements
                        // will need to be retrieved from the mutation normalizer.
                        this._triggerEventBatch(Promise.resolve({
                            actions: [selectAllAction],
                            mutatedElements: new Set(),
                        }));
                    }
                }
                // Safari on MacOS triggers a selection change when pressing Ctrl
                // even though the selection did not actually change. This property
                // is used to store whether the current state is considered to be a
                // select all. The point is to avoid triggering a new event for a
                // selection change if everything was already selected beforehand.
                this._currentlySelectingAll = isSelectAll;
            }
        }
        /**
         * Create an instance of EventNormalizer if the pointer touch a shadow node.
         *
         * @param {MouseEvent} ev
         */
        _onEventEnableNormalizer(ev) {
            this._enableNormalizer(ev.target);
        }
        /**
         * Create an instance of EventNormalizer for the given element with shadow
         * content or iframe content.
         * To be editable an iframe cannot have src because it must be an iframe
         * with content generated by the editor.
         *
         * @param {Element} el
         */
        _enableNormalizer(el) {
            const root = el.shadowRoot ||
                (isInstanceOf(el, HTMLIFrameElement) &&
                    (!el.src || el.src === window.location.href) &&
                    el.contentWindow.document);
            if (root && !this._normalizedRoot.has(root) && this._isInEditor(el)) {
                this._bindDocumentEvent(root);
            }
        }
        /**
         * Trigger all selection timeouts. If there is more than one timeout, fire
         * all the previous one with an empty batch as the last selection is the one
         * that count.
         */
        _triggerSelectionTimeouts() {
            const lastTimeout = this._selectionTimeouts.pop();
            const emptyBatch = {
                actions: [],
            };
            for (const timeout of this._selectionTimeouts) {
                if (timeout.pending) {
                    timeout.fire(emptyBatch);
                }
            }
            if (lastTimeout) {
                lastTimeout.fire();
            }
            this._selectionTimeouts = [];
        }
        /**
         * Make a pointer event under some condition.
         */
        _preProcessPointerEvent(pointerEventPosition, check = true) {
            // Don't trigger events on the editable if the click was done outside of
            // the editable itself or on something else than an element.
            if (this._mousedownInEditable && isInstanceOf(pointerEventPosition.target, Element)) {
                try {
                    this._processEventsUpUntilMoveEvent(check);
                    // When the users clicks in the DOM, the range is set in the next
                    // tick. The observation of the resulting range must thus be delayed
                    // to the next tick as well. Store the data we have now before it
                    // gets invalidated by the redrawing of the DOM.
                    this._initialCaretPosition = this._getEventCaretPosition(pointerEventPosition);
                    const pointerSelectionTimeout = new Timeout(() => {
                        const selectionBatch = this._getSelectionBatchOnce(pointerEventPosition);
                        return selectionBatch;
                    });
                    this._triggerEventBatch(pointerSelectionTimeout.promise);
                    this._selectionTimeouts.push(pointerSelectionTimeout);
                }
                catch (e) {
                    this._mousedownInEditable = false;
                    this._initialCaretPosition = undefined;
                }
            }
            else if (isInstanceOf(pointerEventPosition.target, Element) &&
                !!pointerEventPosition.target.closest('[contentEditable=true]')) {
                // When within a contenteditable element but in a non-editable
                // context, prevent a collapsed selection by removing all ranges.
                // TODO: remove them from the VDocument as well.
                const pointerSelectionTimeout = new Timeout(() => {
                    const selection = this._getSelection();
                    if (selection) {
                        const collapsed = selection.anchorNode === selection.focusNode &&
                            selection.anchorOffset === selection.focusOffset;
                        const target = this._getClosestElement(selection.focusNode);
                        if (collapsed && !!target.closest('[contentEditable=true]')) {
                            document.getSelection().removeAllRanges();
                        }
                    }
                    return {
                        actions: [],
                    };
                });
                this._triggerEventBatch(pointerSelectionTimeout.promise);
                this._selectionTimeouts.push(pointerSelectionTimeout);
            }
        }
        /**
         * Middleware betwen the `_triggerEventBatchOutside` to always capture the
         * last action being done when sending a batch.
         */
        _triggerEventBatch(batchPromise) {
            this._triggerEventBatchOutside(batchPromise.then(batch => {
                if (batch.actions.length) {
                    this._lastAction = batch.actions[batch.actions.length - 1];
                }
                return batch;
            }));
        }
        /**
         * Check wether the last action is a selection and the selection is the
         * different than the one provided.
         */
        _isLastSelectionDifferent(selection) {
            const lastSelection = this._lastAction &&
                this._lastAction.type === 'setSelection' &&
                this._lastAction.domSelection;
            if (!lastSelection ||
                selection.anchorNode !== lastSelection.anchorNode ||
                selection.anchorOffset !== lastSelection.anchorOffset ||
                selection.direction !== lastSelection.direction ||
                selection.focusNode !== lastSelection.focusNode ||
                selection.focusOffset !== lastSelection.focusOffset) {
                return true;
            }
            return false;
        }
        /**
         * Retrieve a `PointerEventPosition` from a` MouseEvent` or a `TouchEvent`.
         */
        _getPointerEventPosition(ev) {
            const TouchEvent = window.TouchEvent; // Add the reference for firefox.
            let x;
            let y;
            if (isInstanceOf(ev, TouchEvent)) {
                const change = ev.touches[0] || ev.changedTouches[0];
                x = change.clientX;
                y = change.clientY;
            }
            else {
                x = ev.clientX;
                y = ev.clientY;
            }
            return { x, y, target: ev.target };
        }
    }

    class DomEditable extends JWPlugin {
        constructor(editor, configuration) {
            super(editor, configuration);
            this.commands = {
                selectAll: {
                    handler: this.selectAll,
                },
            };
            this.commandHooks = {
                '@preKeydownCommand': this._onPreKeydownCommand,
            };
            this._onPreKeydownCommand = this._onPreKeydownCommand.bind(this);
        }
        async start() {
            const domLayout = this.dependencies.get(DomLayout);
            this.eventNormalizer = new EventNormalizer(domLayout.isInEditable.bind(domLayout), domLayout.isInEditor.bind(domLayout), this._onNormalizedEvent.bind(this));
        }
        async stop() {
            this.eventNormalizer.destroy();
            return super.stop();
        }
        /**
         * Update the selection in such a way that it selects the entire document.
         *
         * @param params
         */
        selectAll() {
            const unbreakableAncestor = this.editor.selection.range.start.ancestor(node => !this.editor.mode.is(node, RuleProperty.BREAKABLE));
            const domEngine = this.dependencies.get(Layout).engines.dom;
            const editable = domEngine.components.editable[0];
            this.editor.selection.set({
                anchorNode: (unbreakableAncestor === null || unbreakableAncestor === void 0 ? void 0 : unbreakableAncestor.firstLeaf()) || editable.firstLeaf(),
                anchorPosition: RelativePosition.BEFORE,
                focusNode: (unbreakableAncestor === null || unbreakableAncestor === void 0 ? void 0 : unbreakableAncestor.lastLeaf()) || editable.lastLeaf(),
                focusPosition: RelativePosition.AFTER,
                direction: Direction.FORWARD,
            });
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Handle the received signal and dispatch the corresponding editor command,
         * based on the user's configuration and context.
         *
         * @param action
         */
        _matchCommand(action) {
            switch (action.type) {
                case 'insertLineBreak':
                    return ['insertLineBreak', {}];
                case 'insertText':
                case 'insertHtml': {
                    const params = { text: action.text };
                    return ['insertText', params];
                }
                case 'selectAll': {
                    const domLayout = this.dependencies.get(DomLayout);
                    return domLayout.focusedNode ? ['selectAll', {}] : null;
                }
                case 'setSelection': {
                    const layout = this.dependencies.get(Layout);
                    const domLayoutEngine = layout.engines.dom;
                    const vSelection = domLayoutEngine.parseSelection(action.domSelection);
                    if (vSelection) {
                        const vSelectionParams = { vSelection };
                        return ['setSelection', vSelectionParams];
                    }
                    else {
                        return;
                    }
                }
                case 'insertParagraphBreak':
                    return ['insertParagraphBreak', {}];
                case 'deleteWord': {
                    const params = {
                        direction: action.direction,
                        text: action.text,
                    };
                    return ['deleteWord', params];
                }
                case 'deleteContent': {
                    if (action.direction === Direction.FORWARD) {
                        return ['deleteForward', {}];
                    }
                    else {
                        return ['deleteBackward', {}];
                    }
                }
            }
        }
        /**
         * Handle the received signal and dispatch the corresponding editor command,
         * based on the user's configuration and context.
         *
         * @param batchPromise
         */
        async _onNormalizedEvent(batchPromise) {
            await this.editor.nextEventMutex(async (execCommand) => {
                const batch = await batchPromise;
                const domEngine = this.dependencies.get(Layout).engines.dom;
                if (batch.mutatedElements) {
                    domEngine.markForRedraw(batch.mutatedElements);
                }
                let processed = false;
                if (batch.inferredKeydownEvent) {
                    const domLayout = this.dependencies.get(DomLayout);
                    processed = !!(await domLayout.processKeydown(new KeyboardEvent('keydown', Object.assign(Object.assign({}, batch.inferredKeydownEvent), { key: batch.inferredKeydownEvent.key, code: batch.inferredKeydownEvent.code })), { execCommand }));
                }
                if (!processed) {
                    for (const action of batch.actions) {
                        if (action.type === '@redraw') {
                            domEngine.markForRedraw(action.domNodes);
                            await domEngine.redraw();
                        }
                        else {
                            const commandSpec = this._matchCommand(action);
                            if (commandSpec) {
                                const [commandName, commandParams] = commandSpec;
                                if (commandName) {
                                    await execCommand(commandName, commandParams);
                                }
                            }
                        }
                    }
                }
            });
        }
        /**
         * When a new event is triggered by a keypress, we need to init a new
         * observation to make chain of event properly.
         */
        _onPreKeydownCommand() {
            this.eventNormalizer.processEventTimeouts();
        }
    }
    DomEditable.dependencies = [DomLayout, Layout];

    class History extends JWPlugin {
        constructor(editor) {
            super(editor);
            this.loadables = {
                shortcuts: [
                    {
                        pattern: 'CTRL+Z',
                        commandId: 'undo',
                    },
                    {
                        pattern: 'CTRL+SHIFT+Z',
                        commandId: 'redo',
                    },
                    {
                        pattern: 'CTRL+Y',
                        commandId: 'redo',
                    },
                ],
                components: [
                    {
                        id: 'UndoButton',
                        render: async () => {
                            const button = new ActionableNode({
                                name: 'undo',
                                label: 'History undo',
                                commandId: 'undo',
                                enabled: this.canUndo.bind(this),
                                modifiers: [new Attributes({ class: 'fa fa-undo fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'RedoButton',
                        render: async () => {
                            const button = new ActionableNode({
                                name: 'redo',
                                label: 'History redo',
                                commandId: 'redo',
                                enabled: this.canRedo.bind(this),
                                modifiers: [new Attributes({ class: 'fa fa-redo fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [
                    ['UndoButton', ['actionables']],
                    ['RedoButton', ['actionables']],
                ],
            };
            this.commands = {
                undo: {
                    handler: this.undo,
                },
                redo: {
                    handler: this.redo,
                },
            };
            this.commandHooks = {
                '@commit': this._registerMemoryKey,
            };
            this._memoryKeys = [];
            this._memoryCommands = [];
            this._memoryStep = -1;
            this.loadables.components.push();
        }
        undo() {
            this._memoryStep--;
            if (this._memoryStep < 0) {
                this._memoryStep = 0;
            }
            this.editor.memory.switchTo(this._memoryKeys[this._memoryStep]);
        }
        redo() {
            this._memoryStep++;
            const max = this._memoryKeys.length - 1;
            if (this._memoryStep > max) {
                this._memoryStep = max;
            }
            this.editor.memory.switchTo(this._memoryKeys[this._memoryStep]);
        }
        canUndo() {
            return this._memoryStep > 0;
        }
        canRedo() {
            return this._memoryKeys.length - 1 > this._memoryStep;
        }
        _registerMemoryKey(commitParams) {
            const sliceKey = this.editor.memory.sliceKey;
            if (!this._memoryKeys.includes(sliceKey)) {
                const commands = commitParams.commandNames;
                if (commands.length === 1 && commands[0] === 'setSelection') {
                    return;
                }
                else if (this.editor.memoryInfo.uiCommand) {
                    return;
                }
                this._memoryStep++;
                this._memoryKeys.splice(this._memoryStep, Infinity, sliceKey);
                this._memoryCommands.splice(this._memoryStep, Infinity, [...commands]);
            }
        }
    }

    class InputNode extends TagNode {
        constructor(params = {}) {
            super({ htmlTag: 'INPUT' });
            this.inputName = params.inputName || '';
            this.inputType = params.inputType || 'text';
            this.value = params.value || '';
            if (params.change)
                this.change = params.change;
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars,@typescript-eslint/no-empty-function
        change(editor) { }
    }

    class InputXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'INPUT';
            };
        }
        async parse(item) {
            const input = new InputNode({
                inputType: item.getAttribute('type'),
                inputName: item.getAttribute('name'),
                value: item.value,
            });
            const attributes = this.engine.parseAttributes(item);
            if (attributes) {
                attributes.remove('type'); // type is on input.inputType
                attributes.remove('name'); // type is on input.inputName
            }
            if (attributes.length) {
                input.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            input.append(...nodes);
            return [input];
        }
    }
    InputXmlDomParser.id = XmlDomParsingEngine.id;

    class InputDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = InputNode;
        }
        /**
         * Render the VNode to the given format.
         */
        async render(node) {
            const input = {
                tag: 'INPUT',
                attributes: {
                    type: node.inputType,
                    name: node.inputName,
                    value: node.value,
                },
            };
            let onCommit;
            let mousedown;
            let changeHandler;
            input.attach = (el) => {
                onCommit = this._onCommit.bind(this, node, el);
                changeHandler = () => {
                    this.engine.editor.execCommand(() => {
                        node.value = el.value;
                        node.change(this.engine.editor);
                    });
                };
                mousedown = (ev) => {
                    ev.stopImmediatePropagation();
                    ev.stopPropagation();
                };
                el.addEventListener('change', changeHandler);
                el.addEventListener('mousedown', mousedown);
                this.engine.editor.dispatcher.registerCommandHook('@commit', onCommit);
            };
            input.detach = (el) => {
                el.removeEventListener('change', changeHandler);
                el.removeEventListener('mousedown', mousedown);
                this.engine.editor.dispatcher.removeCommandHook('@commit', onCommit);
            };
            return input;
        }
        /**
         * On input change handler.
         *
         * Meant to be overriden.
         */
        // eslint-disable-next-line @typescript-eslint/no-unused-vars,@typescript-eslint/no-empty-function
        _onCommit(node, el) { }
    }
    InputDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Input extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [InputXmlDomParser],
                renderers: [InputDomObjectRenderer],
            };
        }
    }

    class DialogZoneNode extends ZoneNode {
    }

    var template = {"jw-dialog":{"jw-backdrop":{"_attributes":{"class":"jw-close"}},"jw-content":{"jw-button":{"_attributes":{"class":"jw-close"},"_text":"❌"}}}};

    const container = document.createElement('jw-container');
    container.innerHTML = template;
    const dialog = container.firstElementChild;
    class DialogZoneDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = DialogZoneNode;
        }
        async render(node, worker) {
            var _a;
            const float = document.createElement('jw-dialog-container');
            for (const child of node.childVNodes) {
                if (child.tangible || child instanceof MetadataNode) {
                    if (!((_a = node.hidden) === null || _a === void 0 ? void 0 : _a[child.id])) {
                        float.appendChild(await this._renderDialog(child));
                    }
                    worker.depends(child, node);
                }
            }
            return {
                dom: float.childNodes.length ? [float] : [],
            };
        }
        async _renderDialog(node) {
            const clone = dialog.cloneNode(true);
            const content = clone.querySelector('jw-content');
            content.appendChild(this.engine.renderPlaceholder(node));
            let componentId;
            const components = this.engine.editor.plugins.get(Layout).engines.dom.components;
            for (const id in components) {
                if (components[id].includes(node)) {
                    componentId = id;
                }
            }
            clone.addEventListener('click', (ev) => {
                const target = ev.target;
                if (target.classList.contains('jw-close')) {
                    this.engine.editor.execCommand('hide', { componentId: componentId });
                }
            });
            return clone;
        }
    }
    DialogZoneDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class DialogZoneXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-DIALOG';
            };
        }
        async parse(item) {
            const zones = [];
            for (const child of item.querySelectorAll('t[t-zone]')) {
                zones.push(child.getAttribute('t-zone'));
            }
            return [new DialogZoneNode({ managedZones: zones })];
        }
    }
    DialogZoneXmlDomParser.id = XmlDomParsingEngine.id;

    class Dialog extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [DialogZoneXmlDomParser],
                renderers: [DialogZoneDomObjectRenderer],
            };
        }
    }
    Dialog.dependencies = [Parser, Renderer, DomLayout];

    class FollowRangeZoneNode extends ZoneNode {
    }

    class FollowRangeZoneNodeXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-RANGE';
            };
        }
        async parse(item) {
            const zones = [];
            for (const child of item.querySelectorAll('t[t-zone]')) {
                zones.push(child.getAttribute('t-zone'));
            }
            return [new FollowRangeZoneNode({ managedZones: zones })];
        }
    }
    FollowRangeZoneNodeXmlDomParser.id = XmlDomParsingEngine.id;

    class FollowRangeZoneDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = FollowRangeZoneNode;
        }
        async render(node) {
            if (node.hasChildren()) {
                let debounce;
                let followRangeDebounced;
                const followRange = {
                    tag: 'JW-FOLLOW-RANGE',
                    children: node.children(),
                    attributes: { style: { 'display': 'none' } },
                    attach: (el) => {
                        followRangeDebounced = () => {
                            window.clearTimeout(debounce);
                            debounce = window.setTimeout(this._followChangedSelection.bind(this, el), 3);
                        };
                        document.addEventListener('selectionchange', followRangeDebounced, false);
                        window.addEventListener('resize', followRangeDebounced);
                    },
                    detach: () => {
                        document.removeEventListener('selectionchange', followRangeDebounced, false);
                        window.removeEventListener('resize', followRangeDebounced);
                    },
                };
                return followRange;
            }
            else {
                return { children: [] };
            }
        }
        _followChangedSelection(container) {
            let selection;
            let doc = document;
            let isCollapsed = true;
            do {
                selection = doc.getSelection();
                doc = null;
                // don't use selection.isCollapsed because in shadowRoot the value
                // is every time true.
                isCollapsed =
                    selection.anchorNode === selection.focusNode &&
                        selection.anchorOffset === selection.focusOffset;
                if (selection.rangeCount && isCollapsed) {
                    const [el] = targetDeepest(selection.anchorNode, selection.anchorOffset);
                    if (isInstanceOf(el, Element) && el.shadowRoot) {
                        doc = el.shadowRoot;
                    }
                }
            } while (doc);
            const selectionIsInEditable = !!selection &&
                selection.anchorNode &&
                selection.anchorNode.parentElement &&
                selection.anchorNode.parentElement.closest('[contenteditable="true"]');
            // If the selection goes into an input inside the jw-follow-range, do nothing.
            if (document.activeElement instanceof HTMLInputElement &&
                document.activeElement.closest('JW-FOLLOW-RANGE')) {
                return;
            }
            if (selection.rangeCount && !isCollapsed && selectionIsInEditable) {
                if (container.parentElement.tagName !== 'BODY') {
                    document.body.append(container);
                }
                container.style.display = '';
                const size = container.getBoundingClientRect();
                const range = selection.getRangeAt(0);
                const box = range.getBoundingClientRect();
                let topPosition = window.scrollY + box.bottom + size.height / 2;
                topPosition = Math.max(25, topPosition);
                topPosition = Math.min(window.scrollY + window.innerHeight - 50, topPosition);
                container.style.top = topPosition + 'px';
                let leftPosition = box.left + (box.width - size.width) * 0.3;
                leftPosition = Math.max(0, leftPosition);
                container.style.left = leftPosition + 'px';
            }
            else if (container.style.display !== 'none') {
                // Use condition to have the minimum of mutations.
                container.style.display = 'none';
            }
        }
    }
    FollowRangeZoneDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class FollowRange extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [FollowRangeZoneNodeXmlDomParser],
                renderers: [FollowRangeZoneDomObjectRenderer],
            };
        }
    }
    FollowRange.dependencies = [Parser, Renderer, DomLayout, Layout];

    class ToolbarZoneXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-TOOLBAR';
            };
        }
        async parse(item) {
            var _a;
            const toolbar = new ToolbarNode();
            const nodes = await this.engine.parse(...item.childNodes);
            toolbar.append(...nodes);
            const toolbarPlugin = this.engine.editor.plugins.get(Toolbar);
            toolbar.append(...toolbarPlugin.makeToolbarNodes((_a = toolbarPlugin.configuration) === null || _a === void 0 ? void 0 : _a.layout));
            return [toolbar];
        }
    }
    ToolbarZoneXmlDomParser.id = XmlDomParsingEngine.id;

    class ToolbarZoneDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ToolbarNode;
        }
        async render(toolbar) {
            const objectToolbar = {
                tag: 'JW-TOOLBAR',
                children: toolbar.children(),
            };
            return objectToolbar;
        }
    }
    ToolbarZoneDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Toolbar extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ToolbarZoneXmlDomParser],
                renderers: [ToolbarZoneDomObjectRenderer],
                components: [
                    {
                        id: 'toolbar',
                        render: async () => {
                            var _a;
                            const toolbar = new ToolbarNode();
                            toolbar.append(...this.makeToolbarNodes(((_a = this.configuration) === null || _a === void 0 ? void 0 : _a.layout) || []));
                            return [toolbar];
                        },
                    },
                ],
                componentZones: [['toolbar', ['tools']]],
            };
            this.configuration = Object.assign({ layout: [] }, this.configuration);
        }
        makeToolbarNodes(group) {
            if (Array.isArray(group)) {
                const returnItems = [];
                for (const item of group) {
                    returnItems.push(this.makeToolbarNode(item));
                }
                return returnItems;
            }
            else {
                return Object.keys(group).map(name => this.makeToolbarNode(group[name], name));
            }
        }
        makeToolbarNode(item, name) {
            const domEngine = this.editor.plugins.get(Layout).engines.dom;
            if (typeof item === 'string') {
                if (item === '|') {
                    return new SeparatorNode();
                }
                else if (domEngine.hasConfiguredComponents(item)) {
                    return new ZoneNode({ managedZones: [item] });
                }
                else {
                    return new LabelNode({ label: item });
                }
            }
            else if (item instanceof ActionableNode) {
                return item;
            }
            else {
                const groupParams = { name };
                const group = new ActionableGroupNode(groupParams);
                group.append(...this.makeToolbarNodes(item));
                return group;
            }
        }
    }
    Toolbar.dependencies = [DomLayout];

    class TextareaNode extends AtomicNode {
        constructor(params) {
            super();
            this.value = '';
            this.value = (params && params.value) || '';
        }
    }

    class TextareaXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => item instanceof HTMLTextAreaElement;
        }
        /**
         * Parse a list (UL, OL) and its children list elements (LI).
         *
         * @param context
         */
        async parse(item) {
            const textarea = new TextareaNode({ value: item.value });
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                textarea.modifiers.append(attributes);
            }
            return [textarea];
        }
    }
    TextareaXmlDomParser.id = XmlDomParsingEngine.id;

    class TextareaDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TextareaNode;
        }
        /**
         * Render the TextareaNode.
         */
        async render(node) {
            const text = { text: node.value };
            const textarea = {
                tag: 'TEXTAREA',
                children: [text],
            };
            return textarea;
        }
    }
    TextareaDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Textarea extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [TextareaXmlDomParser],
                renderers: [TextareaDomObjectRenderer],
            };
        }
    }

    var template$1 = {"jw-editor":{"jw-header":{"t":{"_attributes":{"t-zone":"tools"}}},"jw-body":{"t":{"_attributes":{"t-zone":"main"}}},"jw-footer":{"t":[{"_attributes":{"t-zone":"status"}},{"_attributes":{"t-zone":"resizer"}}]},"t-dialog":{"t":[{"_attributes":{"t-zone":"dialog"}},{"_attributes":{"t-zone":"default"}}]},"t":{"_attributes":{"t-zone":"debug"}}}};

    class OdooFieldNode extends TagNode {
        constructor(params) {
            super(params);
            this.fieldInfo = makeVersionable(params.fieldInfo);
        }
        /**
         * Return a new VNode with the same type and attributes as this OdooFieldNode.
         */
        clone(deepClone, params) {
            const defaults = {
                htmlTag: this.htmlTag,
                fieldInfo: this.fieldInfo,
            };
            return super.clone(deepClone, Object.assign(Object.assign({}, defaults), params));
        }
    }

    class OdooFieldDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = OdooFieldNode;
        }
        async render(node) {
            const domObject = { tag: node.htmlTag };
            await this._renderValue(node, domObject);
            return domObject;
        }
        /**
         * Render the value of the given field node into the given container.
         *
         * @param node
         * @param container
         */
        async _renderValue(node, container) {
            // TODO CHM: not having default values is cumbersome
            const children = container.children || [];
            const renderedChildren = await this.engine.renderChildren(node);
            children.push(...renderedChildren);
            container.children = children;
            // TODO CHM: not having default values is cumbersome
            container.attributes = container.attributes || {};
            const classList = container.attributes.class || new Set();
            // Instances of the field containing the range are artificially focused.
            const focusedField = this.engine.editor.selection.range.start.ancestor(ancestor => ancestor instanceof OdooFieldNode &&
                ancestor.fieldInfo.value === node.fieldInfo.value);
            if (focusedField) {
                classList.add('jw-focus');
            }
            classList.add('jw-odoo-field');
            if (!node.fieldInfo.isValid.get()) {
                classList.add('jw-odoo-field-invalid');
            }
            if (!node.descendants(AtomicNode).length) {
                classList.add('jw-odoo-field-empty');
            }
            container.attributes.class = classList;
        }
    }
    OdooFieldDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class OdooFieldMap extends Map {
        static hash(field) {
            return `${field.modelId}-${field.recordId}-${field.fieldName}`;
        }
        get(key) {
            let hashedKey;
            if (typeof key === 'string') {
                hashedKey = key;
            }
            else {
                hashedKey = OdooFieldMap.hash(key);
            }
            return super.get(hashedKey);
        }
        set(key, value) {
            let hashedKey;
            if (typeof key === 'string') {
                hashedKey = key;
            }
            else {
                hashedKey = OdooFieldMap.hash(key);
            }
            super.set(hashedKey, value);
            return this;
        }
    }

    class OdooFieldXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return (item instanceof Element &&
                    item.attributes['data-oe-type'] &&
                    item.attributes['data-oe-model'] &&
                    (item.attributes['data-oe-type'].value === 'char' ||
                        item.attributes['data-oe-type'].value === 'text' ||
                        item.attributes['data-oe-type'].value === 'html' ||
                        item.attributes['data-oe-type'].value === 'float' ||
                        item.attributes['data-oe-type'].value === 'integer'));
                // TODO: Handle those fields when their dependecies are met.
                // item.attributes['data-oe-type'].value === 'many2one' ||
                // item.attributes['data-oe-type'].value === 'date' ||
                // item.attributes['data-oe-type'].value === 'datetime'
                // item.attributes['data-oe-type'].value === 'image' ||
                // item.attributes['data-oe-type'].value === 'contact'
            };
            this._reactiveChanges = new OdooFieldMap();
        }
        async parse(element) {
            const field = {
                modelId: element.attributes['data-oe-model'].value,
                recordId: element.attributes['data-oe-id'].value,
                fieldName: element.attributes['data-oe-field'].value,
            };
            // data-oe-type is kind of a widget in Odoo.
            const fieldType = element.attributes['data-oe-type'].value;
            const fieldsRegistry = this.engine.editor.plugins.get(OdooField);
            const value = this._parseValue(element);
            const fieldInfo = fieldsRegistry.register(field, fieldType, value);
            const fieldNode = await this._parseField(element, fieldInfo);
            fieldNode.modifiers.append(this.engine.parseAttributes(element));
            // TODO: Remove the mute mechanism when changes come from memory.
            // This prevent cycling when regenerating children after a value change.
            let mute = false;
            fieldNode.on('childList', async () => {
                if (mute)
                    return;
                this._reactiveChanges.set(fieldNode.fieldInfo, fieldNode);
                fieldNode.fieldInfo.value.set(this._parseValue(fieldNode));
            });
            // TODO: Replace this value listening mechanism by mirror nodes.
            fieldNode.fieldInfo.value.on('set', () => {
                // TODO: Retrieving the node that made the change is a slight hack
                // that will be removed when mirror nodes are available.
                const original = this._reactiveChanges.get(fieldNode.fieldInfo);
                if (fieldNode === original)
                    return;
                mute = true;
                fieldNode.empty();
                fieldNode.append(...original.children().map(child => child.clone(true)));
                mute = false;
            });
            return [fieldNode];
        }
        /**
         * Get an `OdooFieldNode` from an element and a ReactiveValue.
         *
         * @param element
         * @param fieldInfo
         */
        async _parseField(element, fieldInfo) {
            const fieldNode = new OdooFieldNode({ htmlTag: element.tagName, fieldInfo });
            const children = await this.engine.parse(...element.childNodes);
            fieldNode.append(...children);
            return fieldNode;
        }
        _parseValue(source) {
            if (source instanceof Element) {
                return source.innerHTML;
            }
            else {
                const chars = source.descendants(CharNode).map(child => child.char);
                return chars.join('');
            }
        }
    }
    OdooFieldXmlDomParser.id = XmlDomParsingEngine.id;

    class ReactiveValue extends EventMixin {
        constructor(_value) {
            super();
            this._value = _value;
        }
        /**
         * Set the value of this reactiveValue.
         *
         * @param {T} value The value to set.
         * @param {boolean} [fire=true] Fire an event if true.
         * @returns {Promise<void>}
         * @memberof ReactiveValue
         */
        set(value, fire = true) {
            if (value !== this._value) {
                this._value = value;
                if (fire) {
                    this.trigger('set', value);
                }
            }
        }
        /**
         * Get the value of this reactiveValue.
         *
         * @returns {T}
         * @memberof ReactiveValue
         */
        get() {
            return this._value;
        }
    }

    class ReactiveValueVersionable extends ReactiveValue {
        constructor(...args) {
            super(...args);
            return makeVersionable(this);
        }
    }

    var CurrencyPosition;
    (function (CurrencyPosition) {
        CurrencyPosition["BEFORE"] = "BEFORE";
        CurrencyPosition["AFTER"] = "AFTER";
    })(CurrencyPosition || (CurrencyPosition = {}));
    class OdooMonetaryFieldNode extends OdooFieldNode {
    }

    // TODO: retrieve the current decimal of the current lang in odoo
    // const localDecimalSeparator = '.';
    class OdooMonetaryFieldXmlDomParser extends OdooFieldXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return (item instanceof Element &&
                    item.attributes['data-oe-type'] &&
                    item.attributes['data-oe-model'] &&
                    item.attributes['data-oe-type'].value === 'monetary');
            };
        }
        async _parseField(element, fieldInfo) {
            const amountElement = element.querySelector('.oe_currency_value');
            const currencyElement = amountElement.previousSibling || amountElement.nextSibling;
            const fieldNode = new OdooMonetaryFieldNode({
                htmlTag: element.tagName,
                fieldInfo: Object.assign(Object.assign({}, fieldInfo), { currencyValue: currencyElement.textContent, currencyPosition: amountElement.previousSibling
                        ? CurrencyPosition.BEFORE
                        : CurrencyPosition.AFTER }),
            });
            const childNodesToParse = amountElement.childNodes;
            const children = await this.engine.parse(...childNodesToParse);
            fieldNode.append(...children);
            return fieldNode;
        }
        _parseValue(source) {
            if (source instanceof Element) {
                const amountElement = source.querySelector('.oe_currency_value');
                return amountElement.textContent;
            }
            else {
                return super._parseValue(source);
            }
        }
    }

    class OdooMonetaryFieldDomObjectRenderer extends OdooFieldDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = OdooMonetaryFieldNode;
        }
        async _renderValue(node, container) {
            const valueContainer = {
                tag: 'span',
                attributes: {
                    class: new Set(['oe_currency_value']),
                },
            };
            // TODO CHM: not having default values is cumbersome
            const children = container.children || [];
            children.push(valueContainer);
            const currency = { text: node.fieldInfo.currencyValue };
            if (node.fieldInfo.currencyPosition === CurrencyPosition.BEFORE) {
                children.unshift(currency);
            }
            else {
                children.push(currency);
            }
            container.children = children;
            await super._renderValue(node, valueContainer);
        }
    }

    /**
     * Regex used to validate a field.
     */
    const fieldValidators = {
        integer: /^[0-9]+$/,
        float: /^[0-9.,]+$/,
        monetary: /^[0-9.,]+$/,
    };
    class OdooField extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [OdooFieldXmlDomParser, OdooMonetaryFieldXmlDomParser],
                renderers: [OdooMonetaryFieldDomObjectRenderer, OdooFieldDomObjectRenderer],
            };
            this._registry = new OdooFieldMap();
        }
        /**
         * Register an Odoo record.
         *
         * No need to get the inforation from the network if it is already present
         * in the document when parsed by the editor.
         *
         * Create two `ReactiveValue`. One that represent the actual value of the
         * `recordDefinition` and the other represent the validity of the value.
         *
         * See `get` to retrieve the values from an `OdooFieldInfo`.
         */
        register(field, type, value) {
            if (!this._registry.get(field)) {
                // TODO: Retrieve the field from Odoo through RPC.
                const reactiveValue = new ReactiveValueVersionable();
                const isValid = new ReactiveValueVersionable(true);
                if (Object.keys(fieldValidators).includes(type)) {
                    reactiveValue.on('set', (newValue) => {
                        isValid.set(!!newValue.match(fieldValidators[type]));
                    });
                }
                reactiveValue.set(value);
                const reactiveOdooField = makeVersionable(Object.assign(Object.assign({}, field), { originalValue: value, value: reactiveValue, isValid }));
                this._registry.set(field, reactiveOdooField);
            }
            return this._registry.get(field);
        }
        /**
         * Retrieve reactive values by providing an `OdooFieldDefinition`.
         *
         * @param field
         */
        get(field) {
            const reactiveOdooField = this._registry.get(field);
            if (!reactiveOdooField) {
                // TODO: Retrieve the field from Odoo through RPC.
                throw new Error(`Impossible to find the field ${field.fieldName} for model ${field.modelId} with id ${field.modelId}.`);
            }
            return reactiveOdooField;
        }
    }

    class DomMap {
        constructor() {
            this._fromDom = new Map();
            this._toDom = new Map();
        }
        /**
         * Map the given VNode to its corresponding DOM Node and its offset in it.
         *
         * @param node
         * @param domNode
         * @param offset
         * @param method
         */
        set(node, domNode, offset = 0, method = 'push') {
            if (node instanceof LayoutContainer) {
                return;
            }
            if (this._fromDom.has(domNode)) {
                const matches = this._fromDom.get(domNode);
                if (!matches.some((match) => match.id === node.id)) {
                    matches[method](node);
                }
            }
            else {
                this._fromDom.set(domNode, [node]);
            }
            const locations = this._toDom.get(node) || [];
            locations.push([domNode, offset]);
            this._toDom.set(node, locations);
            // Set children.
            for (const renderedChild of domNode.childNodes) {
                const mapping = this.toDomPoint(node);
                if (!mapping) {
                    this.set(node, renderedChild, -1, 'unshift');
                }
            }
        }
        /**
         * Return the VNode(s) corresponding to the given DOM Node.
         *
         * @param domNode
         */
        fromDom(domNode) {
            return this._fromDom.get(domNode);
        }
        /**
         * Return the array of tuple (node, number) corresponding to the given VNode.
         *
         * @param node
         */
        toDomPoint(node) {
            return this._toDom.get(node) || [];
        }
        /**
         * Return the DOM Node corresponding to the given VNode.
         *
         * @param node
         */
        toDom(node) {
            const domNodes = [];
            for (const point of this._toDom.get(node) || []) {
                domNodes.push(point[0]);
            }
            return domNodes;
        }
        /**
         * Clear the map of all correspondances.
         *
         * @param [node]
         */
        clear(node) {
            if (node) {
                for (const point of this._toDom.get(node) || []) {
                    const nodes = this._fromDom.get(point[0]);
                    const index = nodes.indexOf(node);
                    if (index !== -1) {
                        nodes.splice(index, 0);
                    }
                    if (nodes.length === 0) {
                        this._fromDom.delete(point[0]);
                    }
                }
                this._toDom.delete(node);
            }
            else {
                this._fromDom.clear();
                this._toDom.clear();
            }
        }
    }

    async function parseElement(editor, element) {
        const parser = editor.plugins.get(Parser);
        const domParserEngine = parser.engines['dom/html'];
        if (!domParserEngine) {
            throw new Error('To use this parsing utils you must add the Html plugin.');
        }
        const parsedVNodes = await domParserEngine.parse(element);
        const domSelection = element.ownerDocument.getSelection();
        const anchorNode = domSelection.anchorNode;
        if (element === anchorNode || element.contains(anchorNode)) {
            const domMap = new DomMap();
            // Construct DOM map from the parsing in order to parse the selection.
            for (const node of parsedVNodes) {
                domMap.set(node, element);
            }
            for (const [domNode, nodes] of domParserEngine.parsingMap) {
                for (const node of nodes) {
                    domMap.set(node, domNode);
                }
            }
            const _locate = (domNode, domOffset) => {
                /**
                 * Return a position in the VNodes as a tuple containing a reference
                 * node and a relative position with respect to this node ('BEFORE' or
                 * 'AFTER'). The position is always given on the leaf.
                 *
                 * @param container
                 * @param offset
                 */
                let forceAfter = false;
                let forcePrepend = false;
                let container = domNode.childNodes[domOffset] || domNode;
                let offset = container === domNode ? domOffset : 0;
                if (container === domNode && container.childNodes.length) {
                    container = container.childNodes[container.childNodes.length - 1];
                    offset = nodeLength(container);
                    forceAfter = true;
                }
                while (!domMap.fromDom(container)) {
                    forceAfter = false;
                    forcePrepend = false;
                    if (container.previousSibling) {
                        forceAfter = true;
                        container = container.previousSibling;
                        offset = nodeLength(container);
                    }
                    else {
                        forcePrepend = true;
                        offset = [].indexOf.call(container.parentNode.childNodes, container);
                        container = container.parentNode;
                    }
                }
                // When targetting the end of a node, the DOM gives an offset that is
                // equal to the length of the container. In order to retrieve the last
                // descendent, we need to make sure we target an existing node, ie. an
                // existing index.
                const isAfterEnd = offset >= nodeLength(container);
                let index = isAfterEnd ? nodeLength(container) - 1 : offset;
                // Move to deepest child of container.
                while (container.hasChildNodes()) {
                    const child = container.childNodes[index];
                    if (!domMap.fromDom(child)) {
                        break;
                    }
                    container = child;
                    index = isAfterEnd ? nodeLength(container) - 1 : 0;
                    // Adapt the offset to be its equivalent within the new container.
                    offset = isAfterEnd ? nodeLength(container) : index;
                }
                const nodes = domMap.fromDom(container);
                // Get the VNodes matching the container.
                let reference;
                if (isInstanceOf(container, Text)) {
                    // The reference is the index-th match (eg.: text split into chars).
                    reference = forceAfter ? nodes[nodes.length - 1] : nodes[index];
                }
                else {
                    reference = nodes[0];
                }
                if (forceAfter) {
                    return [reference, RelativePosition.AFTER];
                }
                if (forcePrepend && reference instanceof ContainerNode) {
                    return [reference, RelativePosition.INSIDE];
                }
                return reference.locate(container, offset);
            };
            // Parse the dom selection into the description of a VSelection.
            const start = _locate(domSelection.anchorNode, domSelection.anchorOffset);
            const end = _locate(domSelection.focusNode, domSelection.focusOffset);
            const [startVNode, startPosition] = start;
            const [endVNode, endPosition] = end;
            let direction;
            if (domSelection instanceof Selection) {
                const domRange = domSelection.rangeCount && domSelection.getRangeAt(0);
                if (domRange.startContainer === domSelection.anchorNode &&
                    domRange.startOffset === domSelection.anchorOffset) {
                    direction = Direction.FORWARD;
                }
                else {
                    direction = Direction.BACKWARD;
                }
            }
            const selection = {
                anchorNode: startVNode,
                anchorPosition: startPosition,
                focusNode: endVNode,
                focusPosition: endPosition,
                direction: direction,
            };
            editor.selection.set(selection);
            domMap.clear();
        }
        return parsedVNodes;
    }
    async function parseEditable(editor, element, autofocus = false) {
        const nodes = await parseElement(editor, element);
        nodes[0].editable = false;
        nodes[0].breakable = false;
        nodes[0].modifiers.get(Attributes).set('contentEditable', 'true');
        if (autofocus && !editor.selection.anchor.parent) {
            if (nodes[0].hasChildren()) {
                editor.selection.setAt(nodes[0].firstChild(), RelativePosition.BEFORE);
            }
            else {
                editor.selection.setAt(nodes[0], RelativePosition.INSIDE);
            }
        }
        return nodes;
    }
    async function createEditable(editor, autofocus = false) {
        const root = new TagNode({ htmlTag: 'jw-editable' });
        // Semantic elements are inline by default.
        // We need to guarantee it's a block so it can contain
        // other blocks.
        root.modifiers.get(Attributes).set('style', 'display: block;');
        root.editable = false;
        root.breakable = false;
        root.modifiers.get(Attributes).set('contentEditable', 'true');
        if (autofocus && !editor.selection.anchor.parent) {
            editor.selection.setAt(root, RelativePosition.INSIDE);
        }
        return [root];
    }

    class FullscreenButtonDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (node) => node instanceof ActionableNode && node.actionName === 'fullscreen';
        }
        /**
         * Render the FullscreenNode.
         */
        async render(button, worker) {
            const domObject = (await this.super.render(button, worker));
            const fullscreenPlugin = this.engine.editor.plugins.get(Fullscreen);
            const domLayoutEngine = this.engine.editor.plugins.get(Layout).engines
                .dom;
            let elButton;
            domObject.handler = () => {
                var _a;
                // only one component can be display in fullscreen
                const component = (_a = domLayoutEngine.components[fullscreenPlugin.configuration.component]) === null || _a === void 0 ? void 0 : _a[0];
                if (component) {
                    // only one element can be display in fullscreen
                    const element = domLayoutEngine.getDomNodes(component)[0];
                    if (element instanceof Element) {
                        if (fullscreenPlugin.isFullscreen) {
                            element.classList.remove('jw-fullscreen');
                            elButton.classList.remove('pressed');
                            elButton.setAttribute('aria-pressed', 'false');
                        }
                        else {
                            fullscreenPlugin.isFullscreen = true;
                            document.body.classList.add('jw-fullscreen');
                            element.classList.add('jw-fullscreen');
                            elButton.classList.add('pressed');
                            elButton.setAttribute('aria-pressed', 'true');
                            window.dispatchEvent(new CustomEvent('resize'));
                            return;
                        }
                    }
                }
                if (fullscreenPlugin.isFullscreen) {
                    fullscreenPlugin.isFullscreen = false;
                    document.body.classList.remove('jw-fullscreen');
                    window.dispatchEvent(new CustomEvent('resize'));
                }
            };
            const attach = domObject.attach;
            // TODO: Replace these handlers by a `stop` mechanism for renderers.
            domObject.attach = function (el) {
                elButton = el;
                attach.call(this, el);
                if (fullscreenPlugin.isFullscreen) {
                    document.body.classList.add('jw-fullscreen');
                }
            };
            const detach = domObject.detach;
            // TODO: Replace these handlers by a `stop` mechanism for renderers.
            domObject.detach = function (el) {
                elButton = null;
                detach.call(this, el);
                document.body.classList.remove('jw-fullscreen');
            };
            return domObject;
        }
    }
    FullscreenButtonDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Fullscreen extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                renderers: [FullscreenButtonDomObjectRenderer],
                components: [
                    {
                        id: 'FullscreenButton',
                        render: async () => {
                            const button = new ActionableNode({
                                name: 'fullscreen',
                                label: 'Toggle Fullscreen',
                                selected: () => this.isFullscreen,
                                modifiers: [new Attributes({ class: 'fas fa-expand fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['FullscreenButton', ['actionables']]],
            };
            this.isFullscreen = false;
        }
    }

    class CodeViewNode extends AtomicNode {
        constructor() {
            super(...arguments);
            this.value = '';
        }
    }

    class CodeViewDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = CodeViewNode;
        }
        async render(codeView) {
            const domCodeView = document.createElement('TEXTAREA');
            domCodeView.value = codeView.value;
            domCodeView.setAttribute('style', [
                'width: 100%',
                'height: 100%',
                'background-color: black',
                'color: white',
                'padding: 5px',
                'font-family: "Courier New", Courier, "Lucida Sans Typewriter", "Lucida Typewriter", monospace;',
            ].join('; '));
            return { dom: [domCodeView] };
        }
    }
    CodeViewDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Code extends JWPlugin {
        constructor() {
            super(...arguments);
            this.codeView = new CodeViewNode();
            this.loadables = {
                renderers: [CodeViewDomObjectRenderer],
                components: [
                    {
                        id: 'CodeButton',
                        render: async () => {
                            const button = new ActionableNode({
                                name: 'code',
                                label: 'Toggle Code view',
                                commandId: 'toggleCodeView',
                                selected: () => this.active,
                                modifiers: [new Attributes({ class: 'fa fa-code fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'code',
                        render: async () => {
                            return [this.codeView];
                        },
                    },
                ],
                componentZones: [['CodeButton', ['actionables']]],
            };
            this.commands = {
                toggleCodeView: {
                    handler: this.toggle.bind(this),
                },
            };
            this.active = false;
        }
        async start() {
            await super.start();
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        async toggle(params) {
            if (this.active) {
                return this.deactivate(params);
            }
            else {
                return this.activate(params);
            }
        }
        async activate(params) {
            this.active = true;
            const domLayoutEngine = this.editor.plugins.get(Layout).engines.dom;
            const editable = domLayoutEngine.components.editable[0];
            // Update the view's contents.
            const domEditable = domLayoutEngine.getDomNodes(editable)[0];
            this.codeView.value = this._formatElementHtml(domEditable).innerHTML.trim() || '';
            // Show the code view and hide the editable.
            await this.editor.plugins.get(Layout).append('code', 'main');
            await params.context.execCommand('hide', { componentId: 'editable' });
        }
        async deactivate(params) {
            this.active = false;
            const domLayoutEngine = this.editor.plugins.get(Layout).engines.dom;
            const editable = domLayoutEngine.components.editable[0];
            // Parse the code view into the editable.
            const codeContainer = document.createElement('div');
            codeContainer.innerHTML = domLayoutEngine.getDomNodes(this.codeView)[0].value;
            const newEditable = await parseEditable(this.editor, codeContainer);
            editable.empty();
            editable.append(...newEditable[0].children());
            // Show the editable and hide the code view.
            await params.context.execCommand('show', { componentId: 'editable' });
            await this.editor.plugins.get(Layout).remove('code', 'main');
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Format an element's inner HTML by recursively adding inner indentation
         * where it is relevant.
         *
         * @param element
         * @param [_level]
         */
        _formatElementHtml(element, _level = 0) {
            element = element.cloneNode(true);
            const indentBefore = new Array(_level + 1).join('    ');
            const indentAfter = new Array(_level).join('    ');
            for (const child of element.children) {
                const isChildBlock = isBlock(child);
                if (isChildBlock) {
                    element.insertBefore(document.createTextNode('\n' + indentBefore), child);
                }
                this._formatElementHtml(child, _level + 1);
                if (isChildBlock && element.lastElementChild === child) {
                    element.appendChild(document.createTextNode('\n' + indentAfter));
                }
            }
            return element;
        }
    }

    class FontSizeDomObjectRenderer extends InputDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (node) => node instanceof InputNode && node.inputName === 'font-size';
        }
        /**
         * Render the VNode to the given format.
         */
        async render(node) {
            const input = (await super.render(node));
            const attach = input.attach;
            input.attach = (el) => {
                attach(el);
                const domVisible = el.style.display !== 'none';
                const visible = isInTextualContext(this.engine.editor);
                if (visible !== domVisible) {
                    if (visible) {
                        el.style.display = 'inline-block';
                    }
                    else {
                        el.style.setProperty('display', 'none', 'important');
                    }
                }
            };
            return input;
        }
        /**
         * @override
         */
        _onCommit(node, input) {
            super._onCommit(node, input);
            const editor = this.engine.editor;
            const range = editor.selection.range;
            // Hide the input if the range is not in text.
            // TODO: create a ActionableInputNode for this, that way the button
            // group can be hidden as well.
            const domVisible = input.style.display !== 'none';
            const visible = isInTextualContext(editor);
            if (visible !== domVisible) {
                if (visible) {
                    input.style.display = 'inline-block';
                }
                else {
                    input.style.setProperty('display', 'none', 'important');
                }
            }
            const next = range.start.nextSibling(CharNode);
            const prev = range.end.previousSibling(CharNode);
            let fontSize = '';
            if (range.isCollapsed()) {
                fontSize = (next && this._getFontSize(next)) || (prev && this._getFontSize(prev)) || '';
            }
            else {
                const nextFontSize = next && this._getFontSize(next);
                const prevFontSize = prev && this._getFontSize(prev);
                if (nextFontSize && (nextFontSize === prevFontSize || !prevFontSize)) {
                    fontSize = nextFontSize;
                }
            }
            input.value = fontSize;
        }
        _getFontSize(charNode) {
            var _a, _b;
            let fontSize = (_b = (_a = charNode.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.style) === null || _b === void 0 ? void 0 : _b.get('font-size');
            if (fontSize) {
                fontSize = parseInt(fontSize, 10).toString();
            }
            else if (charNode) {
                const layout = this.engine.editor.plugins.get(Layout);
                const domLayout = layout.engines.dom;
                const firstDomNode = domLayout.getDomNodes(charNode)[0];
                let firstDomElement;
                if (firstDomNode) {
                    firstDomElement =
                        firstDomNode instanceof HTMLElement ? firstDomNode : firstDomNode.parentElement;
                    if (firstDomElement) {
                        fontSize = parseInt(getComputedStyle(firstDomElement)['font-size'], 10).toString();
                    }
                }
            }
            return fontSize;
        }
    }
    FontSizeDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class FontSize extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                renderers: [FontSizeDomObjectRenderer],
                components: [
                    {
                        id: 'FontSizeInput',
                        async render() {
                            const input = new InputNode({
                                inputType: 'number',
                                inputName: 'font-size',
                                change: (editor) => {
                                    editor.execCommand('setFontSize', { value: parseInt(input.value) });
                                },
                            });
                            return [input];
                        },
                    },
                ],
            };
            this.commands = {
                setFontSize: {
                    handler: this.setFontSize,
                },
            };
        }
        /**
         * Set the font size of the context range
         */
        setFontSize(params) {
            let nodes = [];
            if (!params.context.range.isCollapsed()) {
                nodes = params.context.range.targetedNodes(CharNode);
            }
            for (const node of nodes) {
                node.modifiers.get(Attributes).style.set('font-size', `${params.value}px`);
            }
        }
    }
    FontSize.dependencies = [Input];

    class ButtonFormat extends Format {
        constructor() {
            super('BUTTON');
            this.preserveAfterParagraphBreak = false;
            this.preserveAfterLineBreak = false;
        }
    }

    class ButtonXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'BUTTON';
            };
        }
        /**
         * Parse a bold node.
         *
         * @param item
         */
        async parse(item) {
            const bold = new ButtonFormat();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                bold.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(bold, children);
            return children;
        }
    }

    class Button extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ButtonXmlDomParser],
            };
        }
    }
    Button.dependencies = [Inline];

    class HorizontalRuleNode extends InlineNode {
    }
    HorizontalRuleNode.atomic = true;

    class HorizontalRuleXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'HR';
            };
        }
        async parse(item) {
            const image = new HorizontalRuleNode();
            image.modifiers.append(this.engine.parseAttributes(item));
            return [image];
        }
    }
    HorizontalRuleXmlDomParser.id = XmlDomParsingEngine.id;

    class HorizontalRuleDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = HorizontalRuleNode;
        }
        async render() {
            const horizontalRule = {
                tag: 'HR',
            };
            return horizontalRule;
        }
    }
    HorizontalRuleDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class HorizontalRule extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [HorizontalRuleXmlDomParser],
                renderers: [HorizontalRuleDomObjectRenderer],
            };
        }
    }

    class StrikethroughFormat extends Format {
        constructor(htmlTag = 'S') {
            super(htmlTag);
        }
    }

    class StrikethroughXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && (nodeName(item) === 'S' || nodeName(item) === 'DEL');
            };
        }
        /**
         * Parse a strikethrough node.
         *
         * @param item
         */
        async parse(item) {
            const strikethrough = new StrikethroughFormat(nodeName(item));
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                strikethrough.modifiers.append(attributes);
            }
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(strikethrough, children);
            return children;
        }
    }

    class Strikethrough extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [StrikethroughXmlDomParser],
                shortcuts: [
                    {
                        pattern: 'ALT+SHIFT+(',
                        commandId: 'toggleFormat',
                        commandArgs: { FormatClass: StrikethroughFormat },
                    },
                ],
                components: [
                    {
                        id: 'StrikethroughButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'strikethrough',
                                label: 'Toggle strikethrough',
                                commandId: 'toggleFormat',
                                commandArgs: { FormatClass: StrikethroughFormat },
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    var _a, _b;
                                    const range = editor.selection.range;
                                    if (range.isCollapsed()) {
                                        return !!range.modifiers.find(StrikethroughFormat);
                                    }
                                    else {
                                        const startIsFormated = !!((_a = range.start
                                            .nextSibling(InlineNode)) === null || _a === void 0 ? void 0 : _a.modifiers.find(StrikethroughFormat));
                                        if (!startIsFormated || range.isCollapsed()) {
                                            return startIsFormated;
                                        }
                                        else {
                                            return !!((_b = range.end
                                                .previousSibling(InlineNode)) === null || _b === void 0 ? void 0 : _b.modifiers.find(StrikethroughFormat));
                                        }
                                    }
                                },
                                modifiers: [new Attributes({ class: 'fa fa-strikethrough fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['StrikethroughButton', ['actionables']]],
            };
        }
    }
    Strikethrough.dependencies = [Inline];

    class BasicEditor extends JWEditor {
        constructor(params) {
            super();
            this.configure({
                defaults: {
                    Container: ParagraphNode,
                    Separator: LineBreakNode,
                },
                plugins: [
                    [Parser],
                    [Renderer],
                    [Layout],
                    [Keymap],
                    [DomObjectRenderer],
                    [Html],
                    [DomLayout],
                    [DomEditable],
                    [History],
                    [Inline],
                    [Char],
                    [LineBreak],
                    [Heading],
                    [Paragraph],
                    [Textarea],
                    [List],
                    [Indent],
                    [FontSize],
                    [Span],
                    [Bold],
                    [Italic],
                    [Underline],
                    [Strikethrough],
                    [Link],
                    [Divider],
                    [HorizontalRule],
                    [Image],
                    [Subscript],
                    [Superscript],
                    [Blockquote],
                    [Youtube],
                    [Table],
                    [Metadata],
                    [Align],
                    [Pre],
                    [TextColor],
                    [BackgroundColor],
                    [Input],
                    [Dialog],
                    [FollowRange],
                    [Fullscreen, { component: 'editor' }],
                    [OdooField],
                    [Code],
                    [Button],
                ],
            });
            const config = {
                loadables: {
                    components: [
                        {
                            id: 'editor',
                            render(editor) {
                                return editor.plugins.get(Parser).parse('text/html', template$1);
                            },
                        },
                    ],
                    componentZones: [['editor', ['root']]],
                },
            };
            this.configure(config);
            this.configure(DomLayout, {
                location: (params === null || params === void 0 ? void 0 : params.editable) ? [params.editable, 'replace'] : null,
                components: [
                    {
                        id: 'editable',
                        render: async (editor) => {
                            if (params === null || params === void 0 ? void 0 : params.editable) {
                                return parseEditable(editor, params.editable);
                            }
                            else {
                                return createEditable(editor);
                            }
                        },
                    },
                ],
                componentZones: [['editable', ['main']]],
            });
            this.configure(Toolbar, {
                layout: [
                    [
                        [
                            'ParagraphButton',
                            'Heading1Button',
                            'Heading2Button',
                            'Heading3Button',
                            'Heading4Button',
                            'Heading5Button',
                            'Heading6Button',
                            'PreButton',
                        ],
                    ],
                    ['BoldButton', 'ItalicButton', 'UnderlineButton', 'RemoveFormatButton'],
                    ['AlignLeftButton', 'AlignCenterButton', 'AlignRightButton', 'AlignJustifyButton'],
                    ['OrderedListButton', 'UnorderedListButton', 'ChecklistButton'],
                    ['IndentButton', 'OutdentButton'],
                    ['LinkButton', 'UnlinkButton'],
                    ['TableButton'],
                    ['CodeButton'],
                    ['UndoButton', 'RedoButton'],
                ],
            });
        }
    }

    class OdooVideoNode extends AtomicNode {
        constructor(params) {
            super(params);
            this.src = params.src;
        }
    }

    class OdooVideoXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (node) => {
                const isVideo = node instanceof Element &&
                    nodeName(node) === 'DIV' &&
                    node.classList.contains('media_iframe_video') &&
                    node.attributes['data-oe-expression'] &&
                    node.attributes['data-oe-expression'].value;
                return isVideo;
            };
        }
        async parse(element) {
            const video = new OdooVideoNode({ src: element.attributes['data-oe-expression'].value });
            video.modifiers.append(this.engine.parseAttributes(element));
            return [video];
        }
    }
    OdooVideoXmlDomParser.id = XmlDomParsingEngine.id;

    class OdooVideoHtmlDomRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = OdooVideoNode;
        }
        async render(node) {
            const setSelection = () => {
                this.engine.editor.execCommand('setSelection', {
                    vSelection: {
                        anchorNode: node,
                        direction: Direction.FORWARD,
                    },
                });
            };
            const openMedia = () => {
                this.engine.editor.execCommand('openMedia', { media: node });
            };
            const wrapper = {
                tag: 'DIV',
                attributes: {
                    class: new Set(['media_iframe_video']),
                    'data-oe-expression': node.src,
                },
                children: [
                    {
                        tag: 'DIV',
                        attributes: { class: new Set(['css_editable_mode_display']) },
                        children: [{ text: '\u00A0' }],
                        attach: (el) => {
                            el.addEventListener('click', setSelection);
                            el.addEventListener('dblclick', openMedia);
                        },
                        detach: (el) => {
                            el.removeEventListener('click', setSelection);
                            el.removeEventListener('dblclick', openMedia);
                        },
                    },
                    {
                        tag: 'DIV',
                        attributes: { class: new Set(['media_iframe_video_size']) },
                        children: [{ text: '\u00A0' }],
                    },
                    {
                        tag: 'IFRAME',
                        attributes: {
                            src: node.src,
                            frameborder: '0',
                            allowfullscreen: 'allowfullscreen',
                        },
                    },
                ],
            };
            return wrapper;
        }
    }
    OdooVideoHtmlDomRenderer.id = DomObjectRenderingEngine.id;

    class OdooVideo extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [OdooVideoXmlDomParser],
                renderers: [OdooVideoHtmlDomRenderer],
            };
        }
    }

    class DomHelpers extends JWPlugin {
        constructor() {
            super(...arguments);
            this._specializedAttributes = new Map();
            /**
             * Return the DOM Node(s) from a position, including DOM into shadow.
             *
             * @param node
             */
            this.elementFromPoint = elementFromPoint;
        }
        async start() {
            await super.start();
            const engine = this.editor.plugins.get(Parser).engines[HtmlDomParsingEngine.id];
            for (const parser of engine.parsers) {
                if (parser.constructor === TableRowXmlDomParser) {
                    this._specializedAttributes.set(parser, TableSectionAttributes);
                }
                else if (parser.constructor === ListItemXmlDomParser) {
                    this._specializedAttributes.set(parser, ListItemAttributes);
                }
            }
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Add a class or a list of classes to a DOM node or a list of DOM nodes.
         *
         * @param params
         */
        async addClass(context, originalDomNode, className) {
            const domHelpersAddClass = async () => {
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    const classes = Array.isArray(className) ? className : [className];
                    for (const node of this.getNodes(domNode)) {
                        node.modifiers.get(Attributes).classList.add(...classes);
                    }
                }
            };
            return context.execCommand(domHelpersAddClass);
        }
        /**
         * Remove a class or a list of classes from a DOM node or a list of DOM nodes.
         *
         * @param params
         */
        async removeClass(context, originalDomNode, className) {
            const domHelpersRemoveClass = async () => {
                var _a, _b;
                const classes = Array.isArray(className) ? className : [className];
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    for (const node of this.getNodes(domNode)) {
                        (_a = node.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.classList.remove(...classes);
                        for (const modifier of node.modifiers.filter(Format)) {
                            (_b = modifier.modifiers.find(Attributes)) === null || _b === void 0 ? void 0 : _b.classList.remove(...classes);
                        }
                    }
                }
            };
            return context.execCommand(domHelpersRemoveClass);
        }
        /**
         * Add or remove a class or a list of classes from a DOM node or a list of
         * DOM nodes.
         *
         * @param params
         */
        async toggleClass(context, originalDomNode, className) {
            const domHelpersToggleClass = async () => {
                const classes = Array.isArray(className) ? className : [className];
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    for (const node of this.getNodes(domNode)) {
                        node.modifiers.get(Attributes).classList.toggle(...classes);
                    }
                }
            };
            return context.execCommand(domHelpersToggleClass);
        }
        /**
         * Set an attribute on a DOM node or a list of DOM nodes.
         *
         * @param params
         */
        async setAttribute(context, originalDomNode, name, value) {
            const domHelpersSetAttribute = async () => {
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    for (const node of this.getNodes(domNode)) {
                        node.modifiers.get(Attributes).set(name, value);
                    }
                }
            };
            return context.execCommand(domHelpersSetAttribute);
        }
        /**
         * Update the attributes with the given dictionnary and clear all previous
         * attributes.
         */
        async updateAttributes(context, originalDomNode, attributes) {
            const domHelpersUpdateAttribute = async () => {
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    for (const node of this.getNodes(domNode)) {
                        node.modifiers.get(Attributes).clear();
                        for (const [name, value] of Object.entries(attributes)) {
                            node.modifiers.get(Attributes).set(name, value);
                        }
                    }
                }
            };
            return context.execCommand(domHelpersUpdateAttribute);
        }
        /**
         * Set a style key/value pair on a DOM node or a list of DOM nodes.
         *
         * @param params
         */
        async setStyle(context, originalDomNode, name, value, important) {
            const domHelpersSetStyle = async () => {
                const domNodes = Array.isArray(originalDomNode) ? originalDomNode : [originalDomNode];
                for (const domNode of domNodes) {
                    const Attributes = this._getAttributesConstructor(domNode);
                    for (const node of this.getNodes(domNode)) {
                        value = important ? value + ' !important' : value;
                        node.modifiers.get(Attributes).style.set(name, value);
                    }
                }
            };
            return context.execCommand(domHelpersSetStyle);
        }
        /**
         * Remove a DOM node or a list of DOM nodes.
         *
         * @param params
         */
        async remove(context, domNode) {
            const domHelpersRemove = async () => {
                for (const node of this.getNodes(domNode)) {
                    node.remove();
                }
            };
            return context.execCommand(domHelpersRemove);
        }
        /**
         * Remove the contents of a DOM node or of a list of DOM nodes.
         *
         * @param params
         */
        async empty(context, domNode) {
            const domHelpersEmpty = async () => {
                for (const node of this.getNodes(domNode)) {
                    node.empty();
                }
            };
            return context.execCommand(domHelpersEmpty);
        }
        /**
         * Replace a DOM node or a list of DOM nodes with the given HTML content.
         *
         * @param params
         */
        async replace(context, domNodes, html) {
            const domHelpersReplace = async () => {
                const nodes = this.getNodes(domNodes);
                const parsedNodes = await this._parseHtmlString(html);
                const firstNode = nodes[0];
                for (const parsedNode of parsedNodes) {
                    firstNode.before(parsedNode);
                }
                for (const node of nodes) {
                    node.remove();
                }
            };
            return context.execCommand(domHelpersReplace);
        }
        /**
         * Replace a DOM node or a list of DOM nodes with the given text content.
         *
         * @param params
         */
        async text(context, domNodes, text) {
            const domHelpersReplace = async (context) => {
                const nodes = this.getNodes(domNodes);
                const range = new VRange(this.editor, [
                    [nodes[0], RelativePosition.BEFORE],
                    [nodes[nodes.length - 1], RelativePosition.AFTER],
                ], { temporary: true });
                const insertTextParams = {
                    context: { range },
                    text: text,
                };
                context.execCommand('insertText', insertTextParams);
            };
            return context.execCommand(domHelpersReplace);
        }
        /**
         * Wrap the given DOM node within the given HTML.
         *
         * @param params
         */
        async wrap(context, domNode, containerHtml) {
            const domHelpersWrap = async () => {
                const container = this.getNodes(domNode)[0];
                if (!(container instanceof ContainerNode)) {
                    throw new Error('The provided container must be a ContainerNode in the Jabberwock structure.');
                }
                const parsedNodes = await this._parseHtmlString(containerHtml);
                for (const parsedNode of parsedNodes) {
                    container.wrap(parsedNode);
                }
            };
            return context.execCommand(domHelpersWrap);
        }
        /**
         * Wrap the given DOM node's contents as deep as possible within the given HTML.
         *
         * @param params
         */
        async wrapContents(context, domNode, containerHtml) {
            let wrapper;
            const domHelpersWrapContents = async () => {
                const container = this.getNodes(domNode)[0];
                if (!(container instanceof ContainerNode)) {
                    throw new Error('The provided container must be a ContainerNode in the Jabberwock structure.');
                }
                const parsedNodes = await this._parseHtmlString(containerHtml);
                const contents = container.children();
                for (const parsedNode of parsedNodes) {
                    container.prepend(parsedNode);
                    const descendant = parsedNode.lastDescendant(ContainerNode) || parsedNode;
                    if (descendant instanceof ContainerNode) {
                        descendant.append(...contents);
                    }
                    wrapper = parsedNode;
                }
            };
            await context.execCommand(domHelpersWrapContents);
            return wrapper;
        }
        /**
         * Move a DOM Node before another.
         *
         * @param params
         */
        async moveBefore(context, fromDomNode, toDomNode) {
            const domHelpersMoveBefore = async () => {
                const toNode = this.getNodes(toDomNode)[0];
                for (const fromNode of this.getNodes(fromDomNode)) {
                    fromNode.before(toNode);
                }
            };
            return context.execCommand(domHelpersMoveBefore);
        }
        /**
         * Move a DOM Node after another.
         *
         * @param params
         */
        async moveAfter(context, fromDomNode, toDomNode) {
            const domHelpersMoveAfter = async () => {
                const toNodes = this.getNodes(toDomNode);
                const toNode = toNodes[toNodes.length - 1];
                for (const fromNode of this.getNodes(fromDomNode).reverse()) {
                    fromNode.after(toNode);
                }
            };
            return context.execCommand(domHelpersMoveAfter);
        }
        /**
         * Insert html content before, after or inside a DOM Node. If no DOM Node
         * was provided, empty the range and insert the html content before the it.
         *
         * @param params
         */
        async insertHtml(context, html, domNode, position) {
            let parsedNodes;
            const domHelpersInsertHtml = async () => {
                let nodes;
                if (domNode) {
                    nodes = this.getNodes(domNode);
                    if (!nodes.length) {
                        throw new Error('The given DOM node does not have a corresponding VNode.');
                    }
                    position = position || RelativePosition.BEFORE;
                }
                else {
                    this.editor.selection.range.empty();
                    nodes = [this.editor.selection.range.start];
                    position = RelativePosition.BEFORE;
                }
                parsedNodes = await this._parseHtmlString(html);
                switch (position.toUpperCase()) {
                    case RelativePosition.BEFORE:
                        for (const parsedNode of parsedNodes) {
                            nodes[0].before(parsedNode);
                        }
                        break;
                    case RelativePosition.AFTER:
                        for (const parsedNode of [...parsedNodes].reverse()) {
                            nodes[nodes.length - 1].after(parsedNode);
                        }
                        break;
                    case RelativePosition.INSIDE:
                        for (const parsedNode of [...parsedNodes]) {
                            nodes[nodes.length - 1].append(parsedNode);
                        }
                        break;
                }
            };
            await context.execCommand(domHelpersInsertHtml);
            return parsedNodes;
        }
        /**
         * Return the `VNode`(s) matching a DOM Node or a list of DOM Nodes.
         *
         * @param domNode
         */
        getNodes(domNode) {
            const layout = this.editor.plugins.get(Layout);
            const domEngine = layout.engines.dom;
            let nodes = [];
            if (Array.isArray(domNode)) {
                for (const oneDomNode of domNode) {
                    nodes.push(...domEngine.getNodes(oneDomNode));
                }
            }
            else {
                nodes = domEngine.getNodes(domNode);
            }
            return nodes;
        }
        /**
         * Return the DOM Node(s) matching a VNode or a list of VNodes.
         *
         * @param node
         */
        getDomNodes(node) {
            const layout = this.editor.plugins.get(Layout);
            const domEngine = layout.engines.dom;
            let domNodes = [];
            if (Array.isArray(node)) {
                for (const oneNode of node) {
                    domNodes.push(...domEngine.getDomNodes(oneNode));
                }
            }
            else {
                domNodes = domEngine.getDomNodes(node);
            }
            return domNodes;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Parse an HTML string and return the resulting `VNodes`.
         *
         * @param html
         */
        async _parseHtmlString(html) {
            const parser = this.editor.plugins.get(Parser);
            const div = document.createElement('div');
            div.innerHTML = html;
            return parser.parse('dom/html', ...div.childNodes);
        }
        _getAttributesConstructor(node) {
            for (const [parser, Attributes] of this._specializedAttributes) {
                if (parser.predicate(node)) {
                    return Attributes;
                }
            }
            return Attributes;
        }
    }
    DomHelpers.dependencies = [Parser];

    class OdooStructureNode extends TagNode {
        constructor(params) {
            super(params);
            this.breakable = false;
            this.dirty = false;
            this.xpath = params.xpath;
            this.viewId = params.viewId;
        }
    }

    class OdooStructureXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return (item instanceof Element &&
                    item.classList.contains('oe_structure') &&
                    item.attributes &&
                    item.attributes['data-oe-xpath'] &&
                    item.attributes['data-oe-id']);
            };
        }
        /**
         * Parse a structure node.
         *
         * @param item
         */
        async parse(item) {
            const odooStructure = new OdooStructureNode({
                htmlTag: nodeName(item),
                xpath: item.attributes['data-oe-xpath'].value,
                viewId: item.attributes['data-oe-id'].value,
            });
            odooStructure.modifiers.append(this.engine.parseAttributes(item));
            const children = await this.engine.parse(...item.childNodes);
            odooStructure.append(...children);
            odooStructure.on('childList', () => {
                odooStructure.dirty = true;
            });
            odooStructure.on('modifierUpdate', () => {
                odooStructure.dirty = true;
            });
            return [odooStructure];
        }
    }
    OdooStructureXmlDomParser.id = XmlDomParsingEngine.id;

    class OdooImageDomObjectRenderer extends ImageDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ImageNode;
        }
        async render(node, worker) {
            const image = await this.super.render(node, worker);
            if (image && 'tag' in image) {
                const savedAttach = image.attach;
                const savedDetach = image.detach;
                const handleClick = () => {
                    const params = { media: node };
                    this.engine.editor.execCommand('openMedia', params);
                };
                image.attach = (el) => {
                    if (savedAttach) {
                        savedAttach(el);
                    }
                    el.addEventListener('dblclick', handleClick);
                };
                image.detach = (el) => {
                    if (savedDetach) {
                        savedDetach(el);
                    }
                    el.removeEventListener('dblclick', handleClick);
                };
            }
            return image;
        }
    }

    class FontAwesomeNode extends InlineNode {
        constructor(params) {
            super(params);
            this.htmlTag = params.htmlTag;
            this.faClasses = params.faClasses;
        }
        /**
         * Return a new VNode with the same type and attributes as this VNode.
         */
        clone(params) {
            const defaults = {
                htmlTag: this.htmlTag,
                faClasses: this.faClasses,
            };
            return super.clone(Object.assign(Object.assign({}, defaults), params));
        }
    }
    FontAwesomeNode.atomic = true;

    const zeroWidthSpace = '\u200b';
    class FontAwesomeDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = FontAwesomeNode;
        }
        async render(node, worker) {
            const select = (ev) => {
                ev.preventDefault();
                const selectFontAwesome = () => {
                    this.engine.editor.selection.select(node, node);
                };
                // The normaliser wait a tick before changing the selection when the user click
                // in order to override the normalizer default behavior we also need to wait a tick
                setTimeout(() => {
                    this.engine.editor.execCommand(selectFontAwesome);
                });
            };
            const fontawesome = {
                tag: node.htmlTag,
                attributes: {
                    class: new Set(node.faClasses),
                },
                attach: (el) => {
                    el.addEventListener('mouseup', select, true);
                },
                detach: (el) => {
                    el.removeEventListener('mouseup', select, true);
                },
            };
            let domObject;
            if (this.shouldAddNavigationHelpers(node)) {
                // Surround the fontawesome with two invisible characters so the
                // selection can navigate around it.
                domObject = {
                    children: [
                        // We are targetting the invisible character BEFORE the
                        // fontawesome node.
                        // If offset 1:
                        // Moving from before the fontawesome node to after it.
                        // (DOM is `<invisible/>[]<fontawesome/><invisible/>` but
                        // should be `<invisible/><fontawesome/><invisible/>[]`).
                        // else:
                        // Stay before the fontawesome node.
                        { text: zeroWidthSpace },
                        // If we are targetting the fontawesome directyle then stay
                        // before the fontawesome node.
                        fontawesome,
                        // We are targetting the invisible character AFTER the
                        // fontawesome node.
                        // If offset 0:
                        // Moving from after the fontawesome node to before it.
                        // (DOM is `<invisible/><fontawesome/>[]<invisible/>` but
                        // should be `[]<invisible/><fontawesome/><invisible/>`).
                        // else:
                        // Stay after the fontawesome node.
                        { text: zeroWidthSpace },
                    ],
                };
                worker.locate([node], domObject.children[0]);
                worker.locate([node], domObject.children[2]);
            }
            else {
                domObject = { children: [fontawesome] };
            }
            worker.locate([node], fontawesome);
            return domObject;
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Return true if the current context justifies putting a mechanism in place
         * to permit navigation around the rendered font awesome node.
         *
         * @param node
         */
        shouldAddNavigationHelpers(node) {
            const range = this.engine.editor.selection.range;
            if (!this.engine.editor.isInEditable(node)) {
                return false;
            }
            // Is node next to range.
            if (range.start.nextSibling() === node ||
                range.start.previousSibling() === node ||
                range.end.nextSibling() === node ||
                range.end.previousSibling() === node) {
                return true;
            }
            else {
                return false;
            }
        }
    }
    FontAwesomeDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class OdooFontAwesomeDomObjectRenderer extends FontAwesomeDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = FontAwesomeNode;
        }
        async render(node, worker) {
            const domObject = await super.render(node, worker);
            if (domObject && 'children' in domObject) {
                const fa = domObject.children[1] || domObject.children[0];
                if ('tag' in fa) {
                    const dbclickCallback = () => {
                        this.engine.editor.execCommand('openMedia', { media: node });
                    };
                    const savedAttach = fa.attach;
                    fa.attach = (el) => {
                        if (savedAttach) {
                            savedAttach(el);
                        }
                        el.addEventListener('dblclick', dbclickCallback);
                    };
                    const savedDetach = fa.detach;
                    fa.detach = (el) => {
                        if (savedDetach) {
                            savedDetach(el);
                        }
                        el.removeEventListener('dblclick', dbclickCallback);
                    };
                }
            }
            return domObject;
        }
    }

    class OdooTranslationFormat extends Format {
        constructor(htmlTag, translationId) {
            super(htmlTag);
            this.breakable = false;
            this.translationId = translationId;
        }
        get name() {
            return `OdooTranslation: ${super.name}`;
        }
        // TODO: Attributes on OdooTranslation should reactively read the values set
        // on the node itself rather than having to manually synchronize them.
        get translationId() {
            var _a;
            return (_a = this.modifiers.find(Attributes)) === null || _a === void 0 ? void 0 : _a.get('data-oe-translation-id');
        }
        set translationId(translationId) {
            this.modifiers.get(Attributes).set('data-oe-translation-id', translationId);
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * @override
         */
        clone() {
            const clone = super.clone();
            clone.translationId = this.translationId;
            return clone;
        }
    }

    const selector = '[data-oe-translation-id], ' +
        '[data-oe-model][data-oe-id][data-oe-field], ' +
        '[placeholder*="data-oe-translation-id="], ' +
        '[title*="data-oe-translation-id="], ' +
        '[alt*="data-oe-translation-id="]';
    class OdooTranslationXmlDomParser extends FormatXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return (item instanceof Element &&
                    item.attributes['data-oe-translation-state'] &&
                    !item.querySelector(selector));
            };
        }
        /**
         * Parse a translation node.
         *
         * @param item
         */
        async parse(item) {
            const odooTranslation = new OdooTranslationFormat(nodeName(item), item.getAttribute('data-oe-translation-id'));
            odooTranslation.modifiers.replace(Attributes, this.engine.parseAttributes(item));
            const children = await this.engine.parse(...item.childNodes);
            this.applyFormat(odooTranslation, children);
            return children;
        }
    }
    OdooTranslationXmlDomParser.id = XmlDomParsingEngine.id;

    class NoteEditableXmlDomParser extends DividerXmlDomParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return (item instanceof Element &&
                    nodeName(item) === 'DIV' &&
                    item.classList.contains('note-editable'));
            };
        }
        async parse(item) {
            const divider = (await super.parse(item))[0];
            let looseChildren = [];
            const newChildren = [];
            for (const child of divider.childVNodes) {
                if (child instanceof AtomicNode) {
                    looseChildren.push(child);
                }
                else {
                    this.addChildren(newChildren, looseChildren);
                    looseChildren = [];
                    newChildren.push(child);
                }
            }
            this.addChildren(newChildren, looseChildren);
            divider.append(...newChildren);
            return [divider];
        }
        addChildren(mainChildren, children) {
            if (children.length) {
                const container = new this.engine.editor.configuration.defaults.Container();
                container.append(...children);
                mainChildren.push(container);
            }
        }
    }
    NoteEditableXmlDomParser.id = XmlDomParsingEngine.id;

    class OdooParallaxNode extends AtomicTagNode {
        constructor() {
            super({ htmlTag: 'SPAN' });
        }
    }

    class OdooParallaxSpanXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && item.classList.contains('s_parallax_bg');
            };
        }
        /**
         * @override
         */
        async parse(item) {
            const odooStructure = new OdooParallaxNode();
            odooStructure.modifiers.append(this.engine.parseAttributes(item));
            return [odooStructure];
        }
    }
    OdooParallaxSpanXmlDomParser.id = XmlDomParsingEngine.id;

    function getBoundingClientRect(elem) {
        const box = elem.getBoundingClientRect();
        return {
            left: box.left + window.pageXOffset,
            right: box.right + window.pageXOffset,
            top: box.top + window.pageYOffset,
            bottom: box.bottom + window.pageYOffset,
            width: box.width,
            height: box.height,
        };
    }
    const POSITIONABLE_TAG_NAME = 'jw-positionable';
    const POSITIONED_TAG_NAME = 'jw-positionned';
    class Positionable {
        constructor(options) {
            this._relativeElement = options.relativeElement;
            this._positionedElement = options.positionedElement;
            if (options.container) {
                this._container = options.container;
            }
            else {
                this._container = document.querySelector(POSITIONABLE_TAG_NAME);
                if (!this._container) {
                    this._container = document.createElement(POSITIONABLE_TAG_NAME);
                    this._container.style.display = 'block';
                    this._container.style.position = 'relative';
                }
                document.body.prepend(this._container);
            }
            this._positionedElementContainer = document.createElement(POSITIONED_TAG_NAME);
            this._positionedElementContainer.style.position = 'absolute';
            this._positionedElementContainer.style['z-index'] = '10000';
            this._positionedElementContainer.appendChild(this._positionedElement);
            this._container.appendChild(this._positionedElementContainer);
            this._onScroll = this._onScroll.bind(this);
            this.bind();
            setTimeout(this.resetPositionedElement.bind(this), 0);
        }
        resetPositionedElement() {
            const coords1 = getBoundingClientRect(this._relativeElement);
            const coords2 = getBoundingClientRect(this._positionedElement);
            // right top position
            const x = coords1.right - coords2.width;
            const y = coords1.top - coords2.height;
            this._positionedElementContainer.style.left = x + 'px';
            this._positionedElementContainer.style.top = y + 'px';
        }
        bind() {
            document.body.addEventListener('scroll', this._onScroll, true);
        }
        unbind() {
            document.body.removeEventListener('scroll', this._onScroll, true);
        }
        destroy() {
            this.unbind();
            this._positionedElementContainer.remove();
            if (this._container.classList.contains(POSITIONABLE_TAG_NAME) &&
                this._container.parentElement === document.body) {
                this._container.remove();
            }
        }
        _onScroll() {
            this.resetPositionedElement();
        }
    }

    class OdooTableDomObjectRenderer extends TableDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TableNode;
        }
        async render(node, worker) {
            const table = await this.super.render(node, worker);
            // TODO: add a condition to be in a rendering that does not show UI.
            if (table && 'tag' in table) {
                const savedAttach = table.attach;
                const savedDetach = table.detach;
                const dopdown = document.createElement('div');
                dopdown.classList.add('dropdown', 'oe_absolute_dropdown');
                dopdown.innerHTML = `
                <a href="#" role="button" data-toggle="dropdown" class="dropdown-toggle " aria-expanded="false">Table</a>
                <div role="menu" class="dropdown-menu dropdown-menu-right">
                    <a class="dropdown-item" data-command-id="deleteRow">Delete row</a>
                    <a class="dropdown-item" data-command-id="deleteColumn">Delete column</a>
                    <hr/>
                    <a class="dropdown-item" data-command-id="addRowAbove">Insert row above</a>
                    <a class="dropdown-item" data-command-id="addRowBelow">Insert row bellow</a>
                    <a class="dropdown-item" data-command-id="addColumnBefore">Insert column before</a>
                    <a class="dropdown-item" data-command-id="addColumnAfter">Insert column after</a>
                    <hr/>
                    <a class="dropdown-item" data-command-id="deleteTable">Delete Table</a>
                </div>
            `;
                const links = dopdown.querySelectorAll('.dropdown-menu a');
                for (const link of links) {
                    link.addEventListener('click', () => {
                        this.engine.editor.execCommand(link.dataset.commandId);
                    });
                }
                let positionable;
                let commitHandler;
                table.attach = (el) => {
                    if (savedAttach) {
                        savedAttach(el);
                    }
                    positionable = new Positionable({
                        relativeElement: el,
                        positionedElement: dopdown,
                    });
                    commitHandler = () => {
                        if (this.engine.editor.selection.range.start.ancestors().includes(node)) {
                            dopdown.style.display = 'block';
                            positionable.bind();
                            positionable.resetPositionedElement();
                        }
                        else {
                            dopdown.style.display = 'none';
                            positionable.unbind();
                        }
                    };
                    commitHandler();
                    this.engine.editor.dispatcher.registerCommandHook('@commit', commitHandler);
                };
                table.detach = (el) => {
                    if (savedDetach) {
                        savedDetach(el);
                    }
                    positionable.destroy();
                    this.engine.editor.dispatcher.removeCommandHook('@commit', commitHandler);
                };
            }
            return table;
        }
    }

    class LinkFormatDomObjectModifierRenderer extends FormatDomObjectModifierRenderer {
        constructor() {
            super(...arguments);
            this.predicate = LinkFormat;
        }
        /**
         * @override
         */
        async render(format, contents) {
            const domObjects = await super.render(format, contents);
            const link = domObjects[0];
            if ('tag' in link) {
                let dbclickCallback;
                const savedAttach = link.attach;
                link.attach = (el) => {
                    dbclickCallback = async (ev) => {
                        ev.preventDefault();
                        const layout = this.engine.editor.plugins.get(Layout);
                        const domEngine = layout.engines.dom;
                        const nodes = domEngine.getNodes(el);
                        await this.engine.editor.execCommand('setSelection', {
                            vSelection: {
                                anchorNode: nodes[0],
                                anchorPosition: RelativePosition.BEFORE,
                                focusNode: nodes[nodes.length - 1],
                                focusPosition: RelativePosition.AFTER,
                                direction: Direction.FORWARD,
                            },
                        });
                        this.engine.editor.execCommand('openLinkDialog');
                    };
                    if (savedAttach) {
                        savedAttach(el);
                    }
                    el.addEventListener('dblclick', dbclickCallback);
                };
                const savedDetach = link.detach;
                link.detach = (el) => {
                    if (savedDetach) {
                        savedDetach(el);
                    }
                    el.removeEventListener('dblclick', dbclickCallback);
                };
            }
            return domObjects;
        }
    }
    LinkFormatDomObjectModifierRenderer.id = DomObjectRenderingEngine.id;

    var OdooPaddingClasses;
    (function (OdooPaddingClasses) {
        OdooPaddingClasses["NONE"] = "padding-none";
        OdooPaddingClasses["SMALL"] = "padding-small";
        OdooPaddingClasses["MEDIUM"] = "padding-medium";
        OdooPaddingClasses["LARGE"] = "padding-large";
        OdooPaddingClasses["XL"] = "padding-xl";
    })(OdooPaddingClasses || (OdooPaddingClasses = {}));
    const paddingClassesLabels = {
        [OdooPaddingClasses.NONE]: 'None',
        [OdooPaddingClasses.SMALL]: 'Small',
        [OdooPaddingClasses.MEDIUM]: 'Medium',
        [OdooPaddingClasses.LARGE]: 'Large',
        [OdooPaddingClasses.XL]: 'XL',
    };
    const paddingClasses = Object.keys(paddingClassesLabels);
    var OdooMediaClasses;
    (function (OdooMediaClasses) {
        OdooMediaClasses["ROUNDED"] = "rounded";
        OdooMediaClasses["ROUNDED_CIRCLE"] = "rounded-circle";
        OdooMediaClasses["SHADOW"] = "shadow";
        OdooMediaClasses["IMG_THUMBNAIL"] = "img-thumbnail";
        OdooMediaClasses["LEFT"] = "float-left";
        OdooMediaClasses["CENTER"] = "mx-auto";
        OdooMediaClasses["RIGHT"] = "float-right";
    })(OdooMediaClasses || (OdooMediaClasses = {}));
    const mediaClassesLabels = {
        [OdooMediaClasses.ROUNDED]: 'Rounded',
        [OdooMediaClasses.ROUNDED_CIRCLE]: 'Circle',
        [OdooMediaClasses.SHADOW]: 'Shadow',
        [OdooMediaClasses.IMG_THUMBNAIL]: 'Thumbnail',
        [OdooMediaClasses.LEFT]: 'Float Left',
        [OdooMediaClasses.CENTER]: 'Center',
        [OdooMediaClasses.RIGHT]: 'Float Right',
    };
    var OdooIconClasses;
    (function (OdooIconClasses) {
        OdooIconClasses["SPIN"] = "fa-spin";
    })(OdooIconClasses || (OdooIconClasses = {}));
    const iconClassesLabels = Object.assign({
        [OdooIconClasses.SPIN]: 'Spin',
    }, mediaClassesLabels);
    /**
     * Get one image targeted within the range.
     * If more images are within the range, return undefined.
     */
    function getSingleImage(range) {
        const next = range.start.nextLeaf();
        if (next instanceof ImageNode) {
            const prev = range.end.previousLeaf();
            if (prev === next) {
                return next;
            }
        }
    }
    /**
     * Get one icon font-awsome targeted within the range.
     * If more icons are within the range, return undefined.
     */
    function getSingleIcon(range) {
        const next = range.start.nextLeaf();
        if (next instanceof FontAwesomeNode) {
            const prev = range.end.previousLeaf();
            if (prev === next) {
                return next;
            }
        }
    }
    /**
     * Check if there is exactly one image within the editor range
     */
    function isImageVisible(editor) {
        return !!getSingleImage(editor.selection.range);
    }
    /**
     * Check if there is exactly one icon font-awsome within the editor range
     */
    function isIconVisible(editor) {
        return !!getSingleIcon(editor.selection.range);
    }
    function odooHeadingToggleButton(level) {
        return {
            id: 'OdooHeading' + level + 'ToggleButton',
            async render() {
                const button = new ActionableNode({
                    name: 'heading' + level,
                    label: 'H' + level,
                    commandId: 'toggleHeadingStyle',
                    commandArgs: { level: level },
                    visible: isInTextualContext,
                    selected: (editor) => {
                        return isInHeading(editor.selection.range, level);
                    },
                });
                return [button];
            },
        };
    }
    class Odoo extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [
                    NoteEditableXmlDomParser,
                    OdooStructureXmlDomParser,
                    OdooTranslationXmlDomParser,
                    OdooParallaxSpanXmlDomParser,
                ],
                renderers: [
                    OdooImageDomObjectRenderer,
                    OdooFontAwesomeDomObjectRenderer,
                    OdooTableDomObjectRenderer,
                    LinkFormatDomObjectModifierRenderer,
                ],
                components: [
                    {
                        id: 'OdooLinkButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'link',
                                label: 'Insert link',
                                commandId: 'openLinkDialog',
                                selected: (editor) => {
                                    const range = editor.selection.range;
                                    const node = range.start.nextSibling() || range.start.previousSibling();
                                    return (node &&
                                        node instanceof InlineNode &&
                                        !!node.modifiers.find(LinkFormat));
                                },
                                modifiers: [new Attributes({ class: 'fa fa-link fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooLinkToggleButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'link',
                                label: 'Toggle link',
                                commandId: 'toggleLinkWithDialog',
                                selected: (editor) => {
                                    return isInLink(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'fa fa-link fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooMediaButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'media',
                                label: 'Media',
                                commandId: 'openMedia',
                                modifiers: [new Attributes({ class: 'fa fa-file-image-o fa-fw' })],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooTextColorButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'textcolorpicker',
                                label: 'Text Color picker',
                                commandId: 'openTextColorPicker',
                                visible: (editor) => isInTextualContext(editor) || isIconVisible(editor),
                                modifiers: [
                                    new Attributes({
                                        class: 'fa fa-font fa-fw dropdown-toggle',
                                        'data-toggle': 'dropdown',
                                    }),
                                ],
                            });
                            const dropdownContent = new DividerNode();
                            dropdownContent.modifiers.append(new Attributes({ class: 'dropdown-menu' }));
                            const dropdownContainer = new DividerNode();
                            dropdownContainer.modifiers.append(new Attributes({ class: 'dropdown jw-dropdown jw-dropdown-textcolor' }));
                            dropdownContainer.append(button);
                            dropdownContainer.append(dropdownContent);
                            return [dropdownContainer];
                        },
                    },
                    {
                        id: 'OdooBackgroundColorButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'backgroundcolorpicker',
                                label: 'Background Color picker',
                                commandId: 'openBackgroundColorPicker',
                                visible: (editor) => isInTextualContext(editor) || isIconVisible(editor),
                                modifiers: [
                                    new Attributes({
                                        class: 'fa fa-paint-brush fa-fw dropdown-toggle',
                                        'data-toggle': 'dropdown',
                                    }),
                                ],
                            });
                            const dropdownContent = new DividerNode();
                            dropdownContent.modifiers.append(new Attributes({ class: 'dropdown-menu' }));
                            const dropdownContainer = new DividerNode();
                            dropdownContainer.modifiers.append(new Attributes({
                                class: 'dropdown jw-dropdown jw-dropdown-backgroundcolor',
                            }));
                            dropdownContainer.append(button);
                            dropdownContainer.append(dropdownContent);
                            return [dropdownContainer];
                        },
                    },
                    {
                        id: 'OdooDiscardButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'discard',
                                label: 'Discard',
                                commandId: 'discardOdoo',
                                modifiers: [
                                    new Attributes({ class: 'fa fa-times fa-fw jw-danger-button' }),
                                ],
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooSaveButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'save',
                                label: 'Save',
                                commandId: 'saveOdoo',
                                modifiers: [
                                    new Attributes({ class: 'fa fa-save fa-fw jw-primary-button' }),
                                ],
                            });
                            return [button];
                        },
                    },
                    this._makeImagePaddingComponent('OdooImagePaddingNoneActionable', OdooPaddingClasses.NONE),
                    this._makeImagePaddingComponent('OdooImagePaddingSmallActionable', OdooPaddingClasses.SMALL),
                    this._makeImagePaddingComponent('OdooImagePaddingMediumActionable', OdooPaddingClasses.MEDIUM),
                    this._makeImagePaddingComponent('OdooImagePaddingLargeActionable', OdooPaddingClasses.LARGE),
                    this._makeImagePaddingComponent('OdooImagePaddingXLActionable', OdooPaddingClasses.XL),
                    this._makeImageWidthComponent('OdooImageWidthAutoActionable', 'auto'),
                    this._makeImageWidthComponent('OdooImageWidth25Actionable', '25'),
                    this._makeImageWidthComponent('OdooImageWidth50Actionable', '50'),
                    this._makeImageWidthComponent('OdooImageWidth75Actionable', '75'),
                    this._makeImageWidthComponent('OdooImageWidth100Actionable', '100'),
                    this._makeMediaClassComponent('OdooImageRoundedActionable', OdooMediaClasses.ROUNDED, 'fa-square'),
                    this._makeMediaClassComponent('OdooImageRoundedCircleActionable', OdooMediaClasses.ROUNDED_CIRCLE, 'fa-circle-o'),
                    this._makeMediaClassComponent('OdooImageRoundedShadowActionable', OdooMediaClasses.SHADOW, 'fa-sun-o'),
                    this._makeMediaClassComponent('OdooImageRoundedThumbnailActionable', OdooMediaClasses.IMG_THUMBNAIL, 'fa-picture-o'),
                    {
                        id: 'OdooCropActionable',
                        async render() {
                            const button = new ActionableNode({
                                name: 'crop-image',
                                label: 'Crop',
                                commandId: 'cropImage',
                                modifiers: [new Attributes({ class: 'fa fa-crop fa-fw' })],
                                visible: isImageVisible,
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooTransformActionable',
                        async render() {
                            const button = new ActionableNode({
                                name: 'transform-image',
                                label: 'Transform',
                                commandId: 'transformImage',
                                modifiers: [new Attributes({ class: 'fa fa-object-ungroup fa-fw' })],
                                visible: isImageVisible,
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooDescriptionActionable',
                        async render() {
                            const button = new ActionableNode({
                                name: 'describe-image',
                                label: 'Description',
                                commandId: 'describeImage',
                                visible: isImageVisible,
                            });
                            return [button];
                        },
                    },
                    ...[1, 2, 3, 4, 5].map(level => this._makeIconSizeComponent(level)),
                    this._makeIconClassComponent('OdooIconSpinThumbnailActionable', OdooIconClasses.SPIN, 'fa-refresh'),
                    this._makeMediaClassComponent('OdooMediaAlignLeftActionable', OdooMediaClasses.LEFT, 'fa-align-left'),
                    this._makeMediaClassComponent('OdooMediaAlignCenterActionable', OdooMediaClasses.CENTER, 'fa-align-center'),
                    this._makeMediaClassComponent('OdooMediaAlignRightActionable', OdooMediaClasses.RIGHT, 'fa-align-right'),
                    this._makeMediaClassComponent('OdooMediaRoundedActionable', OdooMediaClasses.ROUNDED, 'fa-square'),
                    this._makeMediaClassComponent('OdooMediaRoundedCircleActionable', OdooMediaClasses.ROUNDED_CIRCLE, 'fa-circle-o'),
                    this._makeMediaClassComponent('OdooMediaRoundedShadowActionable', OdooMediaClasses.SHADOW, 'fa-sun-o'),
                    this._makeMediaClassComponent('OdooMediaRoundedThumbnailActionable', OdooMediaClasses.IMG_THUMBNAIL, 'fa-picture-o'),
                    ...[1, 2, 3, 4, 5, 6].map(odooHeadingToggleButton),
                    {
                        id: 'OdooPreToggleButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'pre',
                                label: '<>',
                                commandId: 'togglePreStyle',
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    return isInPre(editor.selection.range);
                                },
                            });
                            return [button];
                        },
                    },
                    {
                        id: 'OdooBlockquoteToggleButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'blockquote',
                                label: 'Blockquote',
                                commandId: 'toggleBlockquoteStyle',
                                visible: isInTextualContext,
                                selected: (editor) => {
                                    return isInBlockquote(editor.selection.range);
                                },
                                modifiers: [new Attributes({ class: 'fa fa-quote-right fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [
                    ['OdooLinkButton', ['actionables']],
                    ['OdooMediaButton', ['actionables']],
                    ['OdooDiscardButton', ['actionables']],
                    ['OdooSaveButton', ['actionables']],
                ],
            };
            this.commands = {
                setImagePadding: {
                    handler: this.setImagePadding,
                },
                setImageWidth: {
                    handler: this.setImageWidth,
                },
                setMediaClass: {
                    handler: this.setMediaClass,
                },
                setIconSize: {
                    handler: this.setIconSize,
                },
                setIconClass: {
                    handler: this.setIconClass,
                },
                toggleHeadingStyle: {
                    handler: this.toggleHeadingStyle,
                },
                togglePreStyle: {
                    handler: this.togglePreStyle,
                },
                toggleBlockquoteStyle: {
                    handler: this.toggleBlockquoteStyle,
                },
                toggleLinkWithDialog: {
                    handler: this.toggleLinkWithDialog,
                },
                insertMedia: {
                    handler: this.insertMedia,
                },
            };
            this.commandHooks = {
                insertTable: async (params) => {
                    if (params.rowCount && params.columnCount) {
                        const range = params.context.range;
                        const table = range.start.ancestor(TableNode);
                        if (table) {
                            const attributes = table.modifiers.get(Attributes);
                            attributes.classList.add('table table-bordered');
                            attributes.style.set('position', 'relative');
                        }
                    }
                },
                applyHeadingStyle: async (params) => {
                    for (const node of params.context.range.targetedNodes(CharNode)) {
                        node.modifiers
                            .get(SpanFormat)
                            .modifiers.get(Attributes)
                            .style.remove('font-size');
                        node.modifiers.get(Attributes).style.remove('font-size');
                    }
                },
            };
        }
        setImagePadding(params) {
            const image = getSingleImage(params.context.range);
            if (image) {
                const classList = image.modifiers.get(Attributes).classList;
                for (const className of paddingClasses) {
                    classList.remove(className);
                }
                if (params.className === 'padding-none')
                    return;
                classList.add(params.className);
            }
        }
        setImageWidth(params) {
            const image = getSingleImage(params.context.range);
            if (image) {
                const style = image.modifiers.get(Attributes).style;
                if (params.width === 'auto') {
                    style.remove('width');
                }
                else {
                    style.set('width', params.width + '%');
                }
            }
        }
        setMediaClass(params) {
            const media = getSingleImage(params.context.range) || getSingleIcon(params.context.range);
            if (media) {
                const className = params.className;
                const classList = media.modifiers.get(Attributes).classList;
                if (!classList.has(className) &&
                    (OdooMediaClasses.LEFT === className ||
                        OdooMediaClasses.CENTER === className ||
                        OdooMediaClasses.RIGHT === className)) {
                    classList.remove(OdooMediaClasses.LEFT);
                    classList.remove(OdooMediaClasses.CENTER);
                    classList.remove(OdooMediaClasses.RIGHT);
                }
                classList.toggle(className);
            }
        }
        setIconSize(params) {
            const icon = getSingleIcon(params.context.range);
            if (icon) {
                const className = 'fa-' + params.size + 'x';
                if (icon.faClasses.includes(className)) {
                    icon.faClasses.splice(icon.faClasses.indexOf(className), 1);
                }
                else {
                    for (let i = 1; i <= 5; i++) {
                        const className = 'fa-' + i + 'x';
                        if (icon.faClasses.includes(className)) {
                            icon.faClasses.splice(icon.faClasses.indexOf(className), 1);
                        }
                    }
                    if (params.size > 1) {
                        icon.faClasses.push(className);
                    }
                }
            }
        }
        setIconClass(params) {
            const icon = getSingleIcon(params.context.range);
            if (icon) {
                if (icon.faClasses.includes(params.className)) {
                    icon.faClasses.splice(icon.faClasses.indexOf(params.className), 1);
                }
                else {
                    icon.faClasses.push(params.className);
                }
            }
        }
        /**
         * Change the formatting of the nodes in given range to Heading, or to the
         * default container if they are already in the given heading level.
         *
         * @param params
         */
        async toggleHeadingStyle(params) {
            return params.context.execCommand('applyHeadingStyle', {
                level: isInHeading(params.context.range, params.level) ? 0 : params.level,
            });
        }
        /**
         * Change the formatting of the nodes in given range to Pre, or to the
         * default container if they are already in Pre.
         *
         * @param params
         */
        async togglePreStyle(params) {
            if (isInPre(params.context.range)) {
                return params.context.execCommand('applyHeadingStyle', {
                    level: 0,
                });
            }
            else {
                return params.context.execCommand('applyPreStyle');
            }
        }
        /**
         * Change the formatting of the nodes in given range to Blockquote, or to
         * the default container if they are already in Blockquote.
         *
         * @param params
         */
        async toggleBlockquoteStyle(params) {
            if (isInBlockquote(params.context.range)) {
                return params.context.execCommand('applyHeadingStyle', {
                    level: 0,
                });
            }
            else {
                return params.context.execCommand('applyBlockquoteStyle');
            }
        }
        async toggleLinkWithDialog(params) {
            if (isInLink(params.context.range)) {
                return params.context.execCommand('unlink');
            }
            else {
                return params.context.execCommand('openLinkDialog');
            }
        }
        async insertMedia(params) {
            const media = (await this.editor.plugins.get(Parser).parse('dom/html', params.element))[0];
            const range = this.editor.selection.range;
            const oldMedia = getSingleIcon(range) || getSingleImage(range);
            if (oldMedia) {
                oldMedia.after(media);
                const oldMediaAttributes = oldMedia.modifiers.get(Attributes);
                const mediaAttributes = media.modifiers.find(Attributes);
                if (mediaAttributes) {
                    for (const key of mediaAttributes.keys()) {
                        if (key === 'style') {
                            oldMediaAttributes.style.reset(Object.assign({}, oldMediaAttributes.style.toJSON(), mediaAttributes.style.toJSON()));
                        }
                        else if (key === 'class') {
                            oldMediaAttributes.classList.add(...mediaAttributes.classList.items());
                        }
                        else {
                            oldMediaAttributes.set(key, mediaAttributes.get(key));
                        }
                    }
                }
                media.modifiers = oldMedia.modifiers;
                oldMedia.remove();
            }
            else {
                await params.context.execCommand('insert', { node: media });
            }
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _makeImagePaddingComponent(componentId, className) {
            const component = {
                id: componentId,
                async render() {
                    const params = {
                        className: className,
                    };
                    const button = new ActionableNode({
                        name: `set-${className}`,
                        label: paddingClassesLabels[className],
                        commandId: 'setImagePadding',
                        commandArgs: params,
                        visible: isImageVisible,
                        selected: (editor) => {
                            const image = getSingleImage(editor.selection.range);
                            const imageAttributes = image === null || image === void 0 ? void 0 : image.modifiers.find(Attributes);
                            if (imageAttributes) {
                                if (className === OdooPaddingClasses.NONE) {
                                    if (paddingClasses.every(className => !imageAttributes.classList.has(className))) {
                                        return true;
                                    }
                                }
                                else {
                                    imageAttributes.classList.has(className);
                                }
                            }
                            return false;
                        },
                    });
                    return [button];
                },
            };
            return component;
        }
        _makeImageWidthComponent(componentId, width) {
            const component = {
                id: componentId,
                async render() {
                    const params = {
                        width: width,
                    };
                    const button = new ActionableNode({
                        name: `set-image-width-${width}`,
                        label: width === 'auto' ? 'auto' : width + '%',
                        commandId: 'setImageWidth',
                        commandArgs: params,
                        visible: isImageVisible,
                        selected: (editor) => {
                            const image = getSingleImage(editor.selection.range);
                            if (image) {
                                const imageAttribute = image.modifiers.get(Attributes);
                                return parseInt(imageAttribute.style.get('width')) === parseInt(width);
                            }
                            return false;
                        },
                    });
                    return [button];
                },
            };
            return component;
        }
        _makeMediaClassComponent(componentId, className, faIcon) {
            const component = {
                id: componentId,
                async render() {
                    const params = { className };
                    const button = new ActionableNode({
                        name: `set-media-class-${className}`,
                        label: mediaClassesLabels[className],
                        commandId: 'setMediaClass',
                        commandArgs: params,
                        modifiers: [new Attributes({ class: `fa ${faIcon} fa-fw` })],
                        visible: (editor) => isImageVisible(editor) || isIconVisible(editor),
                        selected: (editor) => {
                            const image = getSingleImage(editor.selection.range) ||
                                getSingleIcon(editor.selection.range);
                            if (image) {
                                const imageAttribute = image.modifiers.get(Attributes);
                                return imageAttribute.classList.has(className);
                            }
                            return false;
                        },
                    });
                    return [button];
                },
            };
            return component;
        }
        _makeIconSizeComponent(level) {
            return {
                id: 'OdooIconSize' + level + 'xButton',
                async render() {
                    const button = new ActionableNode({
                        name: 'OdooIconSize' + level,
                        label: level + 'x',
                        commandId: 'setIconSize',
                        commandArgs: { size: level },
                        visible: isIconVisible,
                        selected: (editor) => {
                            const icon = getSingleIcon(editor.selection.range);
                            if (icon) {
                                if (level === 1) {
                                    return (!icon.faClasses.includes('fa-2x') &&
                                        !icon.faClasses.includes('fa-3x') &&
                                        !icon.faClasses.includes('fa-4x') &&
                                        !icon.faClasses.includes('fa-5x'));
                                }
                                return icon.faClasses.includes('fa-' + level + 'x');
                            }
                            return false;
                        },
                    });
                    return [button];
                },
            };
        }
        _makeIconClassComponent(componentId, className, faIcon) {
            const component = {
                id: componentId,
                async render() {
                    const params = { className };
                    const button = new ActionableNode({
                        name: `set-icon-class-${className}`,
                        label: iconClassesLabels[className],
                        commandId: 'setIconClass',
                        commandArgs: params,
                        modifiers: [new Attributes({ class: `fa ${faIcon} fa-fw` })],
                        visible: isIconVisible,
                        selected: (editor) => {
                            const icon = getSingleIcon(editor.selection.range);
                            return !!(icon === null || icon === void 0 ? void 0 : icon.faClasses.includes(className));
                        },
                    });
                    return [button];
                },
            };
            return component;
        }
    }
    Odoo.dependencies = [Parser, Inline, Link, Xml];

    class ShadowHtmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof HTMLElement && !!item.shadowRoot;
            };
        }
        /**
         * Parse a shadow node and extract styling from shadow root.
         *
         * @param item
         */
        async parse(item) {
            const shadowRoot = item.shadowRoot;
            const shadow = new ShadowNode();
            const childNodes = Array.from(shadowRoot.childNodes);
            const nodes = await this.engine.parse(...childNodes);
            shadow.append(...nodes);
            if (nodeName(item) === 'JW-SHADOW') {
                return [shadow];
            }
            else {
                const element = new TagNode({ htmlTag: nodeName(item) });
                const attributes = this.engine.parseAttributes(item);
                if (attributes.length) {
                    element.modifiers.append(attributes);
                }
                element.append(shadow);
                return [element];
            }
        }
    }
    ShadowHtmlDomParser.id = HtmlDomParsingEngine.id;

    class ShadowXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-SHADOW';
            };
        }
        /**
         * Parse a shadow node and extract styling.
         *
         * @param item
         */
        async parse(item) {
            const shadow = new ShadowNode();
            const attributes = this.engine.parseAttributes(item);
            if (attributes.length) {
                shadow.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            shadow.append(...nodes);
            return [shadow];
        }
    }
    ShadowXmlDomParser.id = XmlDomParsingEngine.id;

    class ShadowDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ShadowNode;
        }
        async render(shadow) {
            const domObject = {
                tag: 'JW-SHADOW',
                shadowRoot: true,
                children: shadow.childVNodes.filter(child => child.tangible || child instanceof MetadataNode),
            };
            return domObject;
        }
    }
    ShadowDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Shadow extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [ShadowXmlDomParser, ShadowHtmlDomParser],
                renderers: [ShadowDomObjectRenderer],
            };
        }
    }
    Shadow.dependencies = [Parser, Renderer];

    const FontAwesomeRegex = /(?:^|\s|\n)(fa(?:([bdlrs]?)|(-.*?)))/;
    class FontAwesomeXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return FontAwesomeXmlDomParser.isFontAwesome(item);
            };
        }
        async parse(item) {
            const attributes = this.engine.parseAttributes(item);
            // Remove fa classes to avoid having them spread to nearby nodes.
            // They will be put back at renderng time.
            const faClasses = [];
            for (const className of attributes.classList.items()) {
                if (FontAwesomeRegex.test(className)) {
                    faClasses.push(className);
                }
            }
            const fontawesome = new FontAwesomeNode({
                htmlTag: nodeName(item),
                faClasses: new VersionableArray(...faClasses),
            });
            attributes.classList.remove(...faClasses);
            // Keep the attributes even though it might be empty as it will be used
            // to restore the proper order of classes.
            fontawesome.modifiers.append(attributes);
            return [fontawesome];
        }
        /**
         * Return true if the given DOM node is a fontawesome.
         *
         * @param item
         */
        static isFontAwesome(item) {
            return item instanceof Element && FontAwesomeRegex.test(item.className);
        }
    }
    FontAwesomeXmlDomParser.id = XmlDomParsingEngine.id;

    const fontFamily = 'Font Awesome 5 Free';
    class FontAwesomeMailObjectRenderer extends NodeRenderer {
        constructor(engine) {
            super(engine);
            this.predicate = FontAwesomeNode;
            this.fontLoader = {};
            this._loadFont(fontFamily);
        }
        async render(node, worker) {
            const fontawesome = {
                tag: node.htmlTag,
                attributes: { style: {}, class: new Set(node.faClasses) },
            };
            this.engine.renderAttributes(Attributes, node, fontawesome, worker);
            const styleFromRules = await worker.getStyleFromCSSRules(node, fontawesome);
            // Get the current color.
            const color = (styleFromRules.current.color ||
                styleFromRules.inherit.color ||
                '#000000').replace(/\s/g, '');
            // Compute the current font-size.
            const size = parseInt(styleFromRules.current['font-size'] || styleFromRules.inherit['font-size'] || '14px', 10);
            const weight = styleFromRules.current['font-weight'] || styleFromRules.inherit['font-weight'] || 400;
            // Get the current font from the css stylesheet.
            const iconName = [...fontawesome.attributes.class].find(className => className.startsWith('fa-'));
            const stylesheet = this.engine.editor.plugins.get(Stylesheet);
            const styleFont = stylesheet.getFilteredStyleFromCSSRules(selector => selector.includes(iconName + '::before'));
            const font = styleFont.content.charCodeAt(1);
            let fontFamily = styleFromRules.current['font-family'];
            if (!fontFamily) {
                console.warn('Impossible to render FontAwesome: missing font-family from stylesheet.');
            }
            else if (fontFamily[0] === '"') {
                fontFamily = fontFamily.slice(1, -1);
            }
            const imgStyle = {
                'border-style': 'none',
                'vertical-align': 'text-top',
                'height': 'auto',
                'width': 'auto',
            };
            const width = styleFromRules.current.width;
            if (width) {
                const margin = (parseFloat(width) - size) / 2;
                imgStyle['margin-left'] = margin + 'px';
                imgStyle['margin-right'] = margin + 'px';
            }
            // Create image instead of the font for mail client.
            const className = [...fontawesome.attributes.class].join(' ');
            let style = '';
            for (const key in fontawesome.attributes.style) {
                style += key + ':' + fontawesome.attributes.style[key] + ';';
            }
            const iconObject = {
                tag: 'IMG',
                attributes: Object.assign({}, fontawesome.attributes, {
                    'src': await this._fontToBase64(fontFamily, font, size, color, weight),
                    // odoo url: '/web_editor/font_to_img/' + font + '/' + window.encodeURI(color) + '/' + size,
                    'data-fontname': iconName,
                    'data-charcode': font.toString(),
                    'data-size': size.toString(),
                    'data-color': color,
                    'data-class': className,
                    'data-style': style,
                    'class': new Set([...fontawesome.attributes.class].filter(className => className.startsWith('fa-'))),
                    'style': imgStyle,
                }),
            };
            return iconObject;
        }
        /**
         * Load fonts for use in canvas.
         *
         * Fonts need to be loaded once for all canvas. Load the  font on a fake
         * canvas in order to have it already loaded when actually rendering it in
         * `_fontToBase64`.
         *
         * @param fontFamily
         */
        async _loadFont(fontFamily) {
            if (!this.fontLoader[fontFamily]) {
                // Preload the font into canvas.
                const fontChar = String.fromCharCode(61770);
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 20;
                const ctx = canvas.getContext('2d');
                ctx.font = '12px "' + fontFamily + '"';
                ctx.fillStyle = '#000000';
                ctx.textBaseline = 'top';
                ctx.fillText(fontChar, 0, 0);
                // There is no way to wait for a promise for this. It is supposed
                // to only take one rendering pass (16ms) but it might take more if
                // the computer is overloaded. We arbitrarily choose to wait for 3
                // rendering passes (>48ms).
                this.fontLoader[fontFamily] = new Promise(r => setTimeout(() => {
                    r(canvas);
                }, 50));
            }
            return this.fontLoader[fontFamily];
        }
        /**
         * Create an base64 image from a font.
         *
         * @param fontFamily
         * @param font
         * @param fontSize
         * @param color
         * @param weight
         */
        async _fontToBase64(fontFamily, font, fontSize = 14, color = '#000000', weight = 400) {
            const fontChar = String.fromCharCode(font);
            const canvas = await this._loadFont(fontFamily);
            const ctx = canvas.getContext('2d');
            canvas.width = fontSize * 2;
            canvas.height = fontSize;
            // Draw the font and check the size.
            ctx.font = weight + ' ' + fontSize + 'px "' + fontFamily + '"';
            ctx.fillStyle = color;
            ctx.textBaseline = 'top';
            ctx.fillText(fontChar, 0, 0);
            const w = canvas.width;
            const h = canvas.height;
            let realWidth = 1;
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            for (let y = 0; y < h; y++) {
                for (let x = realWidth; x < w; x++) {
                    const index = (y * w + x) * 4;
                    if (imageData.data[index + 3] > 0) {
                        realWidth = x + 1;
                    }
                }
            }
            // Redraw the font with the good size.
            canvas.width = realWidth;
            ctx.font = weight + ' ' + fontSize + 'px "' + fontFamily + '"';
            ctx.fillStyle = color;
            ctx.textBaseline = 'top';
            ctx.fillText(fontChar, 0, 0);
            const image = canvas.toDataURL();
            return image;
        }
    }
    FontAwesomeMailObjectRenderer.id = MailObjectRenderingEngine.id;

    class FontAwesome extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [FontAwesomeXmlDomParser],
                renderers: [FontAwesomeDomObjectRenderer, FontAwesomeMailObjectRenderer],
            };
        }
    }

    class IframeNode extends AtomicNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
    }

    class IframeContainerNode extends ContainerNode {
        constructor(params) {
            super();
            this.editable = false;
            this.breakable = false;
            if (params === null || params === void 0 ? void 0 : params.src) {
                this.src = params.src;
            }
        }
    }

    class IframeHtmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof HTMLElement && nodeName(item) === 'IFRAME';
            };
        }
        /**
         * Parse a shadow node and extract styling from shadow root.
         *
         * @param item
         */
        async parse(item) {
            var _a, _b;
            if (item.getAttribute('name') && item.getAttribute('name') === 'jw-iframe') {
                const iframe = new IframeContainerNode();
                const attributes = this.engine.parseAttributes(item);
                if (attributes.length) {
                    iframe.modifiers.append(attributes);
                }
                const childNodes = item.src
                    ? []
                    : Array.from(((_b = (_a = item.contentWindow) === null || _a === void 0 ? void 0 : _a.document.body) === null || _b === void 0 ? void 0 : _b.childNodes) || []);
                let nodes = await this.engine.parse(...childNodes);
                nodes = flat(nodes.map(node => (node instanceof ShadowNode ? node.childVNodes : [node])));
                iframe.append(...nodes);
                return [iframe];
            }
            else {
                const iframe = new IframeNode();
                const attributes = this.engine.parseAttributes(item);
                if (attributes.length) {
                    iframe.modifiers.append(attributes);
                }
                return [iframe];
            }
        }
    }
    IframeHtmlDomParser.id = HtmlDomParsingEngine.id;

    class IframeXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-IFRAME';
            };
        }
        /**
         * Parse a shadow node and extract styling.
         *
         * @param item
         */
        async parse(item) {
            const attributes = this.engine.parseAttributes(item);
            const shadow = new IframeContainerNode({ src: attributes.get('src') });
            attributes.remove('src');
            if (attributes.length) {
                shadow.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            shadow.append(...nodes);
            return [shadow];
        }
    }
    IframeXmlDomParser.id = XmlDomParsingEngine.id;

    const EventForwarded = ['selectionchange', 'blur', 'focus', 'mousedown', 'touchstart', 'keydown'];
    const forwardEventOutsideIframe = (ev) => {
        const target = ev.target;
        let customEvent;
        let win;
        if (isInstanceOf(target, Document)) {
            win = target.defaultView;
        }
        else if (isInstanceOf(target, Node)) {
            win = target.ownerDocument.defaultView;
        }
        else if (isInstanceOf(ev.currentTarget, Node)) {
            win = ev.currentTarget.ownerDocument.defaultView;
        }
        else if (isInstanceOf(ev.currentTarget, Window) &&
            ev.currentTarget.self === ev.currentTarget) {
            win = ev.currentTarget;
        }
        else {
            win = ev.view || ev.target;
        }
        const iframe = win.frameElement;
        if (ev.type === 'mousedown') {
            const rect = iframe.getBoundingClientRect();
            customEvent = new MouseEvent(ev.type + '-iframe', {
                bubbles: true,
                composed: true,
                cancelable: true,
                clientX: ev.clientX + rect.x,
                clientY: ev.clientY + rect.y,
            });
        }
        else if (ev.type === 'touchstart') {
            const rect = iframe.getBoundingClientRect();
            customEvent = new MouseEvent('mousedown-iframe', {
                bubbles: true,
                composed: true,
                cancelable: true,
                clientX: ev.touches[0].clientX + rect.x,
                clientY: ev.touches[0].clientY + rect.y,
            });
        }
        else if (ev.type === 'keydown') {
            customEvent = new KeyboardEvent('keydown-iframe', {
                bubbles: true,
                composed: true,
                cancelable: true,
                altKey: ev.altKey,
                ctrlKey: ev.ctrlKey,
                shiftKey: ev.shiftKey,
                metaKey: ev.metaKey,
                key: ev.key,
                code: ev.code,
            });
        }
        else {
            customEvent = new CustomEvent(ev.type + '-iframe', {
                bubbles: true,
                composed: true,
                cancelable: true,
            });
        }
        const preventDefault = customEvent.preventDefault.bind(customEvent);
        customEvent.preventDefault = () => {
            ev.preventDefault();
            preventDefault();
        };
        const stopPropagation = customEvent.stopPropagation.bind(customEvent);
        customEvent.stopPropagation = () => {
            ev.stopPropagation();
            stopPropagation();
        };
        const stopImmediatePropagation = customEvent.stopImmediatePropagation.bind(customEvent);
        customEvent.stopImmediatePropagation = () => {
            ev.stopImmediatePropagation();
            stopImmediatePropagation();
        };
        iframe.dispatchEvent(customEvent);
    };
    class IframeContainerDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = IframeContainerNode;
        }
        async render(iframeNode) {
            let onload;
            const children = [];
            iframeNode.childVNodes.forEach(child => {
                if (child.tangible || child instanceof MetadataNode) {
                    children.push(child);
                }
            });
            let wrap;
            const domObject = {
                children: [
                    {
                        tag: 'JW-IFRAME',
                        shadowRoot: true,
                        children: children,
                    },
                    {
                        tag: 'IFRAME',
                        attributes: {
                            // Can not use the default href loading in testing mode because the port is
                            // used for the log, and the iframe are never loaded.
                            // Use the window.location.href to keep style, link and meta to load some
                            // data like the font-face. The style are not really used into the shadow
                            // container but we need the real url to load font-face with relative path.
                            src: window.location.href,
                            name: 'jw-iframe',
                        },
                        attach: (iframe) => {
                            const prev = iframe.previousElementSibling;
                            if (nodeName(prev) === 'JW-IFRAME') {
                                if (wrap) {
                                    wrap.replaceWith(prev);
                                }
                                else {
                                    prev.style.display = 'none';
                                }
                                wrap = prev;
                            }
                            iframe.addEventListener('load', onload);
                            (function loadWithPreloadedMeta() {
                                var _a;
                                // Remove all scripts, keep style, link and meta to load some
                                // data like the font-face. The style are not used into the
                                // shadow container.
                                if (iframe.previousElementSibling !== wrap) {
                                    return;
                                }
                                else {
                                    const doc = (_a = iframe.contentWindow) === null || _a === void 0 ? void 0 : _a.document;
                                    if (doc && (doc.head || doc.body)) {
                                        for (const meta of wrap.shadowRoot.querySelectorAll('style, link, meta')) {
                                            doc.write(meta.outerHTML);
                                        }
                                        doc.write('<body id="jw-iframe"></body>');
                                        doc.write("<script type='application/x-suppress'>");
                                        iframe.contentWindow.close();
                                        setTimeout(() => {
                                            const win = iframe.contentWindow;
                                            const doc = win.document;
                                            // Remove all attribute from the shadow container.
                                            for (const attr of [...wrap.attributes]) {
                                                wrap.removeAttribute(attr.name);
                                            }
                                            doc.body.style.margin = '0px';
                                            doc.body.innerHTML = '';
                                            doc.body.append(wrap);
                                            // Bubbles up the load-iframe event.
                                            const customEvent = new CustomEvent('load-iframe', {
                                                bubbles: true,
                                                composed: true,
                                                cancelable: true,
                                            });
                                            iframe.dispatchEvent(customEvent);
                                            EventForwarded.forEach(eventName => {
                                                win.addEventListener(eventName, forwardEventOutsideIframe, true);
                                                win.addEventListener(eventName + '-iframe', forwardEventOutsideIframe, true);
                                            });
                                        });
                                    }
                                    else {
                                        setTimeout(loadWithPreloadedMeta);
                                    }
                                }
                            })();
                        },
                        detach: (iframe) => {
                            if (iframe.contentWindow) {
                                const win = iframe.contentWindow;
                                EventForwarded.forEach(eventName => {
                                    win.removeEventListener(eventName, forwardEventOutsideIframe, true);
                                    win.removeEventListener(eventName + '-iframe', forwardEventOutsideIframe, true);
                                });
                            }
                            iframe.removeEventListener('load', onload);
                        },
                    },
                ],
            };
            return domObject;
        }
    }
    IframeContainerDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Iframe extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                parsers: [IframeXmlDomParser, IframeHtmlDomParser],
                renderers: [IframeContainerDomObjectRenderer],
            };
        }
    }
    Iframe.dependencies = [Parser, Renderer];

    class ThemeNode extends ContainerNode {
        constructor(params) {
            super();
            this.breakable = false;
            this.themeName = (params === null || params === void 0 ? void 0 : params.theme) || 'default';
        }
    }

    class ThemeXmlDomParser extends AbstractParser {
        constructor() {
            super(...arguments);
            this.predicate = (item) => {
                return item instanceof Element && nodeName(item) === 'T-THEME';
            };
        }
        /**
         * Parse a shadow node and extract styling.
         *
         * @param item
         */
        async parse(item) {
            const theme = new ThemeNode({ theme: item.getAttribute('name') });
            const attributes = this.engine.parseAttributes(item);
            attributes.remove('name');
            if (attributes.length) {
                theme.modifiers.append(attributes);
            }
            const nodes = await this.engine.parse(...item.childNodes);
            theme.append(...nodes);
            return [theme];
        }
    }
    ThemeXmlDomParser.id = XmlDomParsingEngine.id;

    class ThemeDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ThemeNode;
        }
        async render(themeNode) {
            const themePlugin = this.engine.editor.plugins.get(Theme);
            const component = themePlugin.themes[themeNode.themeName];
            const nodes = await component.render(this.engine.editor);
            const domObjectRenderingEngine = this.engine.editor.plugins.get(Renderer).engines[DomObjectRenderingEngine.id];
            const cache = await domObjectRenderingEngine.render(nodes);
            const domObjects = nodes.map(node => cache.renderings.get(node));
            for (const domObject of domObjects) {
                await this._resolvePlaceholder(themeNode, domObject, cache.worker);
            }
            return { children: domObjects };
        }
        async _resolvePlaceholder(theme, domObject, worker) {
            await this.engine.resolveChildren(domObject, worker);
            let placeholderFound = false;
            const domObjects = [domObject];
            for (const domObject of domObjects) {
                if ('tag' in domObject && domObject.tag === 'T-PLACEHOLDER') {
                    if (!placeholderFound) {
                        delete domObject.tag;
                        domObject.children = theme.children();
                        placeholderFound = true;
                    }
                }
                else if ('dom' in domObject) {
                    if (!placeholderFound) {
                        for (const domNode of domObject.dom) {
                            const placeholder = isInstanceOf(domNode, Element) &&
                                domNode.querySelector('T-PLACEHOLDER');
                            if (placeholder) {
                                for (const child of theme.children()) {
                                    placeholder.parentNode.insertBefore(this.engine.renderPlaceholder(child), placeholder);
                                }
                                placeholder.parentNode.removeChild(placeholder);
                                placeholderFound = true;
                            }
                        }
                    }
                }
                else if ('children' in domObject) {
                    // Recursively apply on children in one stack.
                    domObjects.push(...domObject.children);
                }
            }
        }
    }
    ThemeDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Theme extends JWPlugin {
        constructor(editor, configuration = {}) {
            super(editor, configuration);
            this.loadables = {
                parsers: [ThemeXmlDomParser],
                renderers: [ThemeDomObjectRenderer],
                components: [
                    {
                        id: 'ThemeButton',
                        async render() {
                            const group = new ActionableGroupNode({ name: 'themes' });
                            const zone = new ZoneNode({ managedZones: ['themeButtons'] });
                            group.append(zone);
                            return [group];
                        },
                    },
                ],
                componentZones: [['ThemeButton', ['actionables']]],
            };
            this.commands = {
                changeTheme: {
                    handler: this.changeTheme,
                },
            };
            this.themes = {
                default: {
                    id: 'default',
                    async render() {
                        return [new TagNode({ htmlTag: 'T-PLACEHOLDER' })];
                    },
                    label: 'Theme: Default',
                },
            };
            if (this.configuration.components) {
                for (const theme of this.configuration.components) {
                    this.addTheme(theme);
                }
            }
        }
        addTheme(theme) {
            this.themes[theme.id] = theme;
            this.loadables.components.push(this._createThemeButton(theme.id));
            this.loadables.componentZones.push(['Theme' + theme.id + 'Button', ['themeButtons']]);
        }
        /**
         * Create a theme button ComponentDefinition.
         *
         * @param name
         */
        _createThemeButton(name) {
            const theme = this.themes[name];
            return {
                id: 'Theme' + name + 'Button',
                async render() {
                    const button = new ActionableNode({
                        name: 'theme-' + name,
                        label: theme.label || 'Theme: ' + name,
                        commandId: 'changeTheme',
                        commandArgs: { theme: name },
                        selected: (editor) => {
                            const ancestor = editor.selection.anchor.ancestor(ThemeNode);
                            return (ancestor === null || ancestor === void 0 ? void 0 : ancestor.themeName) === name;
                        },
                        enabled: (editor) => {
                            return !!editor.selection.anchor.ancestor(ThemeNode);
                        },
                    });
                    return [button];
                },
            };
        }
        /**
         * Change the current theme and template.
         *
         * @param params
         */
        async changeTheme(params) {
            const ancestor = this.editor.selection.anchor.ancestor(ThemeNode);
            if (ancestor) {
                ancestor.themeName = params.theme;
            }
        }
    }
    Theme.dependencies = [];

    class DevicePreview extends JWPlugin {
        constructor(editor, configuration) {
            super(editor, configuration);
            this.loadables = {
                components: [
                    {
                        id: 'DevicePreviewButton',
                        async render() {
                            const button = new ActionableNode({
                                name: 'devicePreview',
                                label: 'Toggle device preview',
                                commandId: 'toggleDevicePreview',
                                selected: (editor) => !!editor.selection.anchor.ancestor(node => node instanceof ThemeNode && node.themeName.endsWith('Preview')),
                                modifiers: [new Attributes({ class: 'fa fa-mobile-alt fa-fw' })],
                            });
                            return [button];
                        },
                    },
                ],
                componentZones: [['DevicePreviewButton', ['actionables']]],
            };
            this.commands = {
                toggleDevicePreview: {
                    handler: this.toggleDevicePreview,
                },
            };
            if (!this.configuration.getTheme) {
                throw new Error('Please define the getTheme method to configure the DevicePreview plugin.');
            }
            if (!this.configuration.devices) {
                const styleSheets = [];
                for (const style of document.querySelectorAll('style, link')) {
                    styleSheets.push(style.outerHTML.replace(style.innerHTML, style.innerHTML.replace(/</, '&lt;').replace(/>/, '&gt;')));
                }
                this.configuration.devices = {
                    mobile: {
                        label: 'Mobile preview',
                        head: styleSheets.join(''),
                    },
                };
            }
        }
        /**
         * @override
         */
        start() {
            for (const deviceName in this.configuration.devices) {
                const device = this.configuration.devices[deviceName];
                this.dependencies.get(Theme).addTheme({
                    id: deviceName + 'DevicePreview',
                    label: device.label,
                    render: async (editor) => {
                        return editor.plugins
                            .get(Parser)
                            .parse('text/html', '<t-iframe id="jw-device-preview" class="device-preview-' +
                            deviceName +
                            '">' +
                            device.head +
                            '<t-placeholder/></t-iframe>');
                    },
                });
            }
            return super.start();
        }
        /**
         * Toggle the device preview.
         *
         * @param params
         */
        async toggleDevicePreview(params) {
            const theme = this.configuration.getTheme(this.editor);
            if (theme) {
                if (params.device) {
                    const device = params.device + 'DevicePreview';
                    theme.themeName = theme.themeName === device ? 'default' : device;
                }
                else {
                    const devices = ['default'].concat(Object.keys(this.configuration.devices).map(device => device + 'DevicePreview'));
                    const index = devices.indexOf(theme.themeName) + 1;
                    theme.themeName = devices[index] ? devices[index] : 'default';
                }
            }
        }
    }
    DevicePreview.dependencies = [Theme, Iframe, DomLayout];

    class TextMailRendereringEngine extends HtmlTextRendereringEngine {
        constructor() {
            super(...arguments);
            this.correspondingObjectRenderingId = MailObjectRenderingEngine.id;
        }
    }
    TextMailRendereringEngine.id = 'text/mail';

    class MarkerMailObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = MarkerNode;
        }
        /**
         * Don't render the makerNode in mail
         *
         * @override
         */
        async render() {
            return { children: [] };
        }
    }
    MarkerMailObjectRenderer.id = MailObjectRenderingEngine.id;

    class Mail extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                renderingEngines: [TextMailRendereringEngine, MailObjectRenderingEngine],
                renderers: [MarkerMailObjectRenderer],
            };
        }
    }
    Mail.dependencies = [Html, Stylesheet, Shadow, DomLayout];

    class TemplateThumbnailSelectorNode extends ZoneNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
    }

    class TemplateThumbnailSelectorDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = TemplateThumbnailSelectorNode;
        }
        async render(node) {
            const domObject = {
                tag: 'JW-TEMPLATES',
                children: [
                    {
                        tag: 'JW-LABEL',
                        children: [{ text: 'Please choose a template' }],
                    },
                    ...node.children(),
                ],
            };
            return domObject;
        }
    }
    TemplateThumbnailSelectorDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class TemplateActionableDomObjectRenderer extends ActionableDomObjectRenderer {
        constructor() {
            super(...arguments);
            this.predicate = (node) => node instanceof ActionableNode && !!node.ancestor(TemplateThumbnailSelectorNode);
        }
        async render(node, worker) {
            const domObject = await super.render(node, worker);
            const templatePlugin = this.engine.editor.plugins.get(Template);
            const name = node.actionName
                .split('-')
                .slice(1)
                .join('-');
            const template = templatePlugin.configuration.templateConfigurations[name];
            domObject.tag = 'JW-TEMPLATE';
            domObject.children = [
                {
                    tag: 'JW-LABEL',
                    attributes: { class: new Set(['label']) },
                    children: [{ text: template.label }],
                },
                {
                    tag: 'JW-THUMB',
                    attributes: { style: { 'background-image': 'url("' + template.thumbnail + '")' } },
                },
            ];
            return domObject;
        }
    }
    TemplateActionableDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Template extends JWPlugin {
        constructor(editor, configuration = {}) {
            super(editor, configuration);
            this.loadables = {
                renderers: [
                    TemplateThumbnailSelectorDomObjectRenderer,
                    TemplateActionableDomObjectRenderer,
                ],
                components: [
                    {
                        id: 'TemplateSelector',
                        async render() {
                            const group = new ActionableGroupNode({ name: 'templates' });
                            const zone = new ZoneNode({ managedZones: ['templateButtons'] });
                            group.append(zone);
                            return [group];
                        },
                    },
                ],
                componentZones: [['TemplateSelector', ['actionables']]],
            };
            this.commands = {
                applyTemplate: {
                    handler: this.applyTemplate,
                },
            };
            this.loadables.components.push(...this.configuration.components);
            const templateConfigurations = this.configuration.templateConfigurations;
            const targetedZones = new Set();
            const thumbnailZones = new Set();
            for (const config of Object.values(templateConfigurations)) {
                targetedZones.add(config.zoneId);
                config.thumbnailZoneId = config.thumbnailZoneId || config.zoneId;
                thumbnailZones.add(config.thumbnailZoneId);
            }
            for (const zoneId of targetedZones) {
                this.loadables.components.push({
                    id: 'TemplateSelector-' + zoneId,
                    async render() {
                        const group = new ActionableGroupNode({ name: 'templates' });
                        const zone = new ZoneNode({ managedZones: ['templateButtons-' + zoneId] });
                        group.append(zone);
                        return [group];
                    },
                });
            }
            for (const thumbnailZoneId of thumbnailZones) {
                this.loadables.components.push({
                    id: 'TemplateThumbnailSelector-' + thumbnailZoneId,
                    async render() {
                        return [
                            new TemplateThumbnailSelectorNode({
                                managedZones: ['templateThumbnails-' + thumbnailZoneId],
                            }),
                        ];
                    },
                });
            }
            for (const templateName in templateConfigurations) {
                const config = templateConfigurations[templateName];
                const button = this._createTemplateButton(templateName);
                this.loadables.components.push(button);
                this.loadables.componentZones.push([
                    button.id,
                    [
                        'templateButtons',
                        'templateButtons-' + config.zoneId,
                        'templateThumbnails-' + config.thumbnailZoneId,
                    ],
                ]);
            }
        }
        /**
         *
         * @@override
         */
        async start() {
            await super.start();
            const templateToSelect = new Set();
            const layout = this.dependencies.get(Layout);
            const templateConfigurations = this.configuration.templateConfigurations;
            for (const templateName in templateConfigurations) {
                const config = templateConfigurations[templateName];
                for (const engine of Object.values(layout.engines)) {
                    const zones = engine.root
                        .descendants(ZoneNode)
                        .filter(zone => zone.managedZones.includes(config.zoneId));
                    if (zones.length && !zones.find(zone => zone.firstChild())) {
                        templateToSelect.add(templateName);
                        break;
                    }
                }
            }
            const filledZone = new Set();
            for (const templateName of templateToSelect) {
                const config = templateConfigurations[templateName];
                if (!filledZone.has(config.thumbnailZoneId)) {
                    await layout.clear(config.zoneId);
                    filledZone.add(config.thumbnailZoneId);
                    await layout.prepend('TemplateThumbnailSelector-' + config.thumbnailZoneId, config.thumbnailZoneId);
                }
            }
        }
        /**
         * Create the theme button ComponentDefinition
         *
         * @param name
         */
        _createTemplateButton(name) {
            const config = this.configuration.templateConfigurations[name];
            return {
                id: 'Template' + name + 'Button',
                async render() {
                    const button = new ActionableNode({
                        name: 'template-' + name,
                        label: config.label || 'Theme: ' + name,
                        commandId: 'applyTemplate',
                        commandArgs: { template: name },
                    });
                    return [button];
                },
            };
        }
        /**
         * Change the current theme and template.
         *
         * @param params
         */
        async applyTemplate(params) {
            const layout = this.dependencies.get(Layout);
            const config = this.configuration.templateConfigurations[params.template];
            await layout.remove('TemplateThumbnailSelector-' + config.thumbnailZoneId, config.thumbnailZoneId);
            await layout.clear(config.zoneId);
            await layout.append(config.componentId, config.zoneId);
        }
    }
    Template.dependencies = [Layout, DomLayout];

    class ReactiveEditorInfo extends JWPlugin {
        constructor() {
            super(...arguments);
            this.editorInfo = new ReactiveValue({
                canUndo: false,
                canRedo: false,
            });
            this.commandHooks = {
                '@commit': this._updateInfo,
            };
        }
        /**
         * Update the information of the `editorInfo`.
         */
        _updateInfo() {
            const history = this.editor.plugins.get(History);
            this.editorInfo.set({
                canUndo: history.canUndo(),
                canRedo: history.canRedo(),
            });
        }
    }
    ReactiveEditorInfo.dependencies = [History];

    const defaultToolbarLayout = {
        text: [
            'BoldButton',
            'ItalicButton',
            'UnderlineButton',
            'StrikethroughButton',
            'OdooTextColorButton',
            'OdooBackgroundColorButton',
        ],
        heading: [
            'OdooHeading1ToggleButton',
            'OdooHeading2ToggleButton',
            'OdooPreToggleButton',
            'OdooBlockquoteToggleButton',
        ],
        list: ['UnorderedListButton', 'ChecklistButton'],
        link: ['OdooLinkToggleButton'],
        table: ['TableButton'],
        media: ['OdooMediaButton'],
    };
    class OdooWebsiteEditor extends JWEditor {
        constructor(options) {
            super();
            class CustomPlugin extends JWPlugin {
                constructor() {
                    super(...arguments);
                    this.commands = Object.assign(options.customCommands || {});
                }
            }
            this.configure({
                defaults: {
                    Container: ParagraphNode,
                    Separator: LineBreakNode,
                },
                plugins: [
                    [Parser],
                    [Renderer],
                    [Layout],
                    [Keymap],
                    [Html],
                    [Inline],
                    [Char],
                    [LineBreak],
                    [Heading],
                    [Paragraph],
                    [List],
                    [Textarea],
                    [Indent],
                    [Span],
                    [Bold],
                    [Italic],
                    [Underline],
                    [Strikethrough],
                    [Input],
                    [FontSize],
                    [Link],
                    [FontAwesome],
                    [Divider],
                    [Image],
                    [Subscript],
                    [Superscript],
                    [Blockquote],
                    [Youtube],
                    [Table],
                    [Metadata],
                    [Align],
                    [Pre],
                    [TextColor],
                    [BackgroundColor],
                    [Dialog],
                    [Shadow],
                    [Mail],
                    [DomHelpers],
                    [Odoo],
                    [OdooVideo],
                    [CustomPlugin],
                    [FollowRange],
                    [History],
                    [Iframe],
                    [Button],
                    [ReactiveEditorInfo],
                    ...(options.plugins || []),
                ],
            });
            this.configure(Toolbar, {
                layout: options.toolbarLayout || defaultToolbarLayout,
            });
            const loadables = {
                shortcuts: [
                    {
                        pattern: 'CTRL+K',
                        selector: [(node) => !Link.isLink(node)],
                        commandId: 'openLinkDialog',
                    },
                ],
            };
            this.load(loadables);
            const defaultTemplate = `
        <t-dialog><t t-zone="default"/></t-dialog>
        <div class="wrap_editor d-flex flex-column">
            <div class="d-flex flex-grow-1 flex-row overflow-auto">
                <div class="d-flex flex-column o_editor_center">
                    <div class="o_toolbar">
                        <t t-zone="tools"/>
                    </div>
                    <div class="d-flex flex-grow-1 overflow-auto">
                        <t-theme name="default">
                            <t t-zone="snippetManipulators"/>
                            <t t-zone="main"/>
                        </t-theme>
                    </div>
                </div>
                <t t-zone="main_sidebar"/>
            </div>
            <div class="o_debug_zone">
                <t t-zone="debug"/>
            </div>
        </div>
    `;
            this.configure(DomLayout, {
                components: [
                    {
                        id: 'main_template',
                        render(editor) {
                            return editor.plugins
                                .get(Parser)
                                .parse('text/html', options.interface || defaultTemplate);
                        },
                    },
                    {
                        id: 'snippet_menu',
                        render() {
                            const node = options.snippetMenuElement
                                ? new HtmlNode({ domNode: () => options.snippetMenuElement })
                                : new LineBreakNode();
                            return Promise.resolve([node]);
                        },
                    },
                    {
                        id: 'snippetManipulators',
                        render() {
                            const node = options.snippetMenuElement
                                ? new HtmlNode({ domNode: () => options.snippetManipulators })
                                : new LineBreakNode();
                            return Promise.resolve([node]);
                        },
                    },
                    {
                        id: 'main',
                        render: async () => {
                            const div = new DividerNode();
                            div.modifiers.get(Attributes).set('contentEditable', 'true');
                            div.modifiers.get(Attributes).classList.add('note-editable', 'o_editable');
                            div.modifiers.get(Attributes).style.set('width', '100%');
                            const zone = new ZoneNode({ managedZones: ['editable'] });
                            zone.editable = true;
                            div.append(zone);
                            return [div];
                        },
                    },
                    {
                        id: 'editable',
                        render: async (editor) => {
                            if (typeof options.source === 'string') {
                                let source = options.source;
                                if (!source.length && !options.templates) {
                                    source = '<p><br></p>';
                                }
                                return editor.plugins.get(Parser).parse('text/html', source);
                            }
                            else {
                                return parseEditable(editor, options.source);
                            }
                        },
                    },
                ],
                componentZones: [
                    ['main_template', ['root']],
                    ['snippet_menu', ['main_sidebar']],
                    ['snippetManipulators', ['snippetManipulators']],
                ],
                location: options.location,
                pressedActionablesClassName: 'active',
            });
            this.configure(DomEditable, {
                autoFocus: true,
                source: options.source.firstElementChild,
            });
            this.configure(Table, {
                minRowCount: 3,
                minColumnCount: 3,
                inlineUI: true,
            });
            if (options.devicePreview) {
                this.configure(DevicePreview, {
                    getTheme(editor) {
                        const layout = editor.plugins.get(Layout);
                        return layout.engines.dom.root.firstDescendant(ThemeNode);
                    },
                });
            }
            if (options.mode) {
                this.configure({
                    modes: [options.mode],
                });
                this.configure({ mode: options.mode.id });
            }
            if (options.templates) {
                this.configure(Template, {
                    components: options.templates.components,
                    templateConfigurations: options.templates.templateConfigurations,
                });
            }
            if (options.themes) {
                this.configure(Theme, {
                    components: options.themes,
                });
            }
        }
        /**
         * Get the value by rendering the "editable" component of the editor.
         */
        async getValue(format = HtmlDomRenderingEngine.id, deadlockTimeout = 5000) {
            let timeout;
            return new Promise((resolve, reject) => {
                timeout = window.setTimeout(() => {
                    reject({
                        name: 'deadlock',
                        message: 'Editor getValue call is taking too long. It might be caused by a deadlock.',
                    });
                }, deadlockTimeout);
                const renderer = this.plugins.get(Renderer);
                const layout = this.plugins.get(Layout);
                const domLayout = layout.engines.dom;
                const editable = domLayout.root.firstDescendant(node => node instanceof ZoneNode && node.managedZones.includes('editable'));
                const promise = renderer.render(format, editable);
                promise.then(value => {
                    clearTimeout(timeout);
                    resolve(value);
                }, reject);
            });
        }
    }

    class ResizerNode extends ContainerNode {
        constructor() {
            super(...arguments);
            this.editable = false;
            this.breakable = false;
        }
    }

    class ResizerDomObjectRenderer extends NodeRenderer {
        constructor() {
            super(...arguments);
            this.predicate = ResizerNode;
        }
        async render(node) {
            const objectResizer = {
                tag: 'JW-RESIZER',
            };
            // This should become obsolete when we refactor the resiser (see _initTargetToResize() comment).
            this.domEngine = this.engine.editor.plugins.get(Layout).engines.dom;
            objectResizer.attach = (el) => {
                el.addEventListener('mousedown', this.startResize.bind(this));
                el.addEventListener('touchstart', this.startResize.bind(this));
            };
            return objectResizer;
        }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Drag the Resizer to change the editor size.
         *
         * @param {MouseEvent} event
         */
        startResize(event) {
            event.preventDefault();
            this._initTargetToResize();
            if (!this.targetToResize)
                return;
            const startHeight = this.targetToResize.clientHeight;
            const startY = isInstanceOf(event, MouseEvent)
                ? event.pageY
                : event.targetTouches[0].pageY; // Y position of the mousedown
            /**
             * Perform the resizing on every mouse mouvement.
             *
             * @param e
             */
            const doResize = (e) => {
                const currentY = isInstanceOf(e, MouseEvent)
                    ? e.pageY
                    : e.targetTouches[0].pageY;
                const offset = currentY - startY;
                this._resizeTargetHeight(startHeight + offset);
            };
            /**
             * Stop resizing on mouse up.
             */
            const stopResize = () => {
                window.removeEventListener('mousemove', doResize, false);
                window.removeEventListener('mouseup', stopResize, false);
                window.removeEventListener('touchmove', doResize, false);
                window.removeEventListener('touchend', stopResize, false);
            };
            window.addEventListener('mousemove', doResize);
            window.addEventListener('mouseup', stopResize);
            window.addEventListener('touchmove', doResize);
            window.addEventListener('touchend', stopResize);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Discover the HTMLElement to resize and set it as a class property.
         */
        _initTargetToResize() {
            // This way of HTMLElement discovery is far from ideal.
            // The Resizer should never be aware of the HTMLElement.
            //
            // TODO: We should change this to use a shared variable whose value would be listen to by another plugin.
            // The other plugin can then use the shared height value to change the height of his children element.
            //
            // Result: the resizer plugin will become agnostic of the HTMLElement afected by the resize.
            // Problem: We don't yet have a way to do this properly.
            if (this.targetToResize)
                return;
            const mainZone = this.domEngine.root.descendants(node => node instanceof ZoneNode && node.managedZones.includes('main'))[0];
            const domMain = this.domEngine.getDomNodes(mainZone)[0];
            this.targetToResize = (domMain === null || domMain === void 0 ? void 0 : domMain.parentElement) || domMain;
            // Force the overflow on the targetElement.
            // Necesary to make the resizer works out of the box.
            if (this.targetToResize) {
                this.targetToResize.style.overflow = 'auto';
            }
        }
        /**
         * Change the height of the target HTMLElement.
         *
         * @param {number} height
         */
        _resizeTargetHeight(height) {
            height = Math.max(height, 50); // todo : implement a way to force the min-height with resizer parameters ?
            if (this.targetToResize) {
                this.targetToResize.style.height = height + 'px';
            }
        }
    }
    ResizerDomObjectRenderer.id = DomObjectRenderingEngine.id;

    class Resizer extends JWPlugin {
        constructor() {
            super(...arguments);
            this.loadables = {
                renderers: [ResizerDomObjectRenderer],
                components: [
                    {
                        id: 'resizer',
                        render: async () => {
                            return [new ResizerNode()];
                        },
                    },
                ],
                componentZones: [['resizer', ['resizer']]],
            };
        }
    }
    Resizer.dependencies = [DomLayout];

    exports.Attributes = Attributes;
    exports.BasicEditor = BasicEditor;
    exports.ContainerNode = ContainerNode;
    exports.DividerNode = DividerNode;
    exports.DomHelpers = DomHelpers;
    exports.DomLayoutEngine = DomLayoutEngine;
    exports.FontAwesomeNode = FontAwesomeNode;
    exports.Format = Format;
    exports.ImageNode = ImageNode;
    exports.Inline = Inline;
    exports.InlineNode = InlineNode;
    exports.Layout = Layout;
    exports.Link = Link;
    exports.LinkFormat = LinkFormat;
    exports.OdooField = OdooField;
    exports.OdooFieldNode = OdooFieldNode;
    exports.OdooStructureNode = OdooStructureNode;
    exports.OdooTranslationFormat = OdooTranslationFormat;
    exports.OdooVideoNode = OdooVideoNode;
    exports.OdooWebsiteEditor = OdooWebsiteEditor;
    exports.Parser = Parser;
    exports.ReactiveEditorInfo = ReactiveEditorInfo;
    exports.Renderer = Renderer;
    exports.Resizer = Resizer;
    exports.SeparatorNode = SeparatorNode;
    exports.TagNode = TagNode;
    exports.VRange = VRange;

}(this.jabberwock = this.jabberwock || {}, owl));
return this.jabberwock;
}).bind(window));
