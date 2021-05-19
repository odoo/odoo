(function (exports) {
    'use strict';

    /**
     * We define here a simple event bus: it can
     * - emit events
     * - add/remove listeners.
     *
     * This is a useful pattern of communication in many cases.  For OWL, each
     * components and stores are event buses.
     */
    //------------------------------------------------------------------------------
    // EventBus
    //------------------------------------------------------------------------------
    class EventBus {
        constructor() {
            this.subscriptions = {};
        }
        /**
         * Add a listener for the 'eventType' events.
         *
         * Note that the 'owner' of this event can be anything, but will more likely
         * be a component or a class. The idea is that the callback will be called with
         * the proper owner bound.
         *
         * Also, the owner should be kind of unique. This will be used to remove the
         * listener.
         */
        on(eventType, owner, callback) {
            if (!callback) {
                throw new Error("Missing callback");
            }
            if (!this.subscriptions[eventType]) {
                this.subscriptions[eventType] = [];
            }
            this.subscriptions[eventType].push({
                owner,
                callback,
            });
        }
        /**
         * Remove a listener
         */
        off(eventType, owner) {
            const subs = this.subscriptions[eventType];
            if (subs) {
                this.subscriptions[eventType] = subs.filter((s) => s.owner !== owner);
            }
        }
        /**
         * Emit an event of type 'eventType'.  Any extra arguments will be passed to
         * the listeners callback.
         */
        trigger(eventType, ...args) {
            const subs = this.subscriptions[eventType] || [];
            for (let i = 0, iLen = subs.length; i < iLen; i++) {
                const sub = subs[i];
                sub.callback.call(sub.owner, ...args);
            }
        }
        /**
         * Remove all subscriptions.
         */
        clear() {
            this.subscriptions = {};
        }
    }

    /**
     * Owl Observer
     *
     * This code contains the logic that allows Owl to observe and react to state
     * changes.
     *
     * This is a Observer class that can observe any JS values.  The way it works
     * can be summarized thusly:
     * - primitive values are not observed at all
     * - Objects and arrays are observed by replacing them with a Proxy
     * - each object/array metadata are tracked in a weakmap, and keep a revision
     *   number
     *
     * Note that this code is loosely inspired by Vue.
     */
    //------------------------------------------------------------------------------
    // Observer
    //------------------------------------------------------------------------------
    class Observer {
        constructor() {
            this.rev = 1;
            this.allowMutations = true;
            this.weakMap = new WeakMap();
        }
        notifyCB() { }
        observe(value, parent) {
            if (value === null ||
                typeof value !== "object" ||
                value instanceof Date ||
                value instanceof Promise) {
                // fun fact: typeof null === 'object'
                return value;
            }
            let metadata = this.weakMap.get(value) || this._observe(value, parent);
            return metadata.proxy;
        }
        revNumber(value) {
            const metadata = this.weakMap.get(value);
            return metadata ? metadata.rev : 0;
        }
        _observe(value, parent) {
            var self = this;
            const proxy = new Proxy(value, {
                get(target, k) {
                    const targetValue = target[k];
                    return self.observe(targetValue, value);
                },
                set(target, key, newVal) {
                    const value = target[key];
                    if (newVal !== value) {
                        if (!self.allowMutations) {
                            throw new Error(`Observed state cannot be changed here! (key: "${key}", val: "${newVal}")`);
                        }
                        self._updateRevNumber(target);
                        target[key] = newVal;
                        self.notifyCB();
                    }
                    return true;
                },
                deleteProperty(target, key) {
                    if (key in target) {
                        delete target[key];
                        self._updateRevNumber(target);
                        self.notifyCB();
                    }
                    return true;
                },
            });
            const metadata = {
                value,
                proxy,
                rev: this.rev,
                parent,
            };
            this.weakMap.set(value, metadata);
            this.weakMap.set(metadata.proxy, metadata);
            return metadata;
        }
        _updateRevNumber(target) {
            this.rev++;
            let metadata = this.weakMap.get(target);
            let parent = target;
            do {
                metadata = this.weakMap.get(parent);
                metadata.rev++;
            } while ((parent = metadata.parent) && parent !== target);
        }
    }

    /**
     * Owl QWeb Expression Parser
     *
     * Owl needs in various contexts to be able to understand the structure of a
     * string representing a javascript expression.  The usual goal is to be able
     * to rewrite some variables.  For example, if a template has
     *
     *  ```xml
     *  <t t-if="computeSomething({val: state.val})">...</t>
     * ```
     *
     * this needs to be translated in something like this:
     *
     * ```js
     *   if (context["computeSomething"]({val: context["state"].val})) { ... }
     * ```
     *
     * This file contains the implementation of an extremely naive tokenizer/parser
     * and evaluator for javascript expressions.  The supported grammar is basically
     * only expressive enough to understand the shape of objects, of arrays, and
     * various operators.
     */
    //------------------------------------------------------------------------------
    // Misc types, constants and helpers
    //------------------------------------------------------------------------------
    const RESERVED_WORDS = "true,false,NaN,null,undefined,debugger,console,window,in,instanceof,new,function,return,this,eval,void,Math,RegExp,Array,Object,Date".split(",");
    const WORD_REPLACEMENT = Object.assign(Object.create(null), {
        and: "&&",
        or: "||",
        gt: ">",
        gte: ">=",
        lt: "<",
        lte: "<=",
    });
    const STATIC_TOKEN_MAP = Object.assign(Object.create(null), {
        "{": "LEFT_BRACE",
        "}": "RIGHT_BRACE",
        "[": "LEFT_BRACKET",
        "]": "RIGHT_BRACKET",
        ":": "COLON",
        ",": "COMMA",
        "(": "LEFT_PAREN",
        ")": "RIGHT_PAREN",
    });
    // note that the space after typeof is relevant. It makes sure that the formatted
    // expression has a space after typeof
    const OPERATORS = "...,.,===,==,+,!==,!=,!,||,&&,>=,>,<=,<,?,-,*,/,%,typeof ,=>,=,;,in ".split(",");
    let tokenizeString = function (expr) {
        let s = expr[0];
        let start = s;
        if (s !== "'" && s !== '"') {
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
                    throw new Error("Invalid expression");
                }
                s += cur;
            }
            i++;
        }
        if (expr[i] !== start) {
            throw new Error("Invalid expression");
        }
        s += start;
        return { type: "VALUE", value: s };
    };
    let tokenizeNumber = function (expr) {
        let s = expr[0];
        if (s && s.match(/[0-9]/)) {
            let i = 1;
            while (expr[i] && expr[i].match(/[0-9]|\./)) {
                s += expr[i];
                i++;
            }
            return { type: "VALUE", value: s };
        }
        else {
            return false;
        }
    };
    let tokenizeSymbol = function (expr) {
        let s = expr[0];
        if (s && s.match(/[a-zA-Z_\$]/)) {
            let i = 1;
            while (expr[i] && expr[i].match(/\w/)) {
                s += expr[i];
                i++;
            }
            if (s in WORD_REPLACEMENT) {
                return { type: "OPERATOR", value: WORD_REPLACEMENT[s], size: s.length };
            }
            return { type: "SYMBOL", value: s };
        }
        else {
            return false;
        }
    };
    const tokenizeStatic = function (expr) {
        const char = expr[0];
        if (char && char in STATIC_TOKEN_MAP) {
            return { type: STATIC_TOKEN_MAP[char], value: char };
        }
        return false;
    };
    const tokenizeOperator = function (expr) {
        for (let op of OPERATORS) {
            if (expr.startsWith(op)) {
                return { type: "OPERATOR", value: op };
            }
        }
        return false;
    };
    const TOKENIZERS = [
        tokenizeString,
        tokenizeNumber,
        tokenizeOperator,
        tokenizeSymbol,
        tokenizeStatic,
    ];
    /**
     * Convert a javascript expression (as a string) into a list of tokens. For
     * example: `tokenize("1 + b")` will return:
     * ```js
     *  [
     *   {type: "VALUE", value: "1"},
     *   {type: "OPERATOR", value: "+"},
     *   {type: "SYMBOL", value: "b"}
     * ]
     * ```
     */
    function tokenize(expr) {
        const result = [];
        let token = true;
        while (token) {
            expr = expr.trim();
            if (expr) {
                for (let tokenizer of TOKENIZERS) {
                    token = tokenizer(expr);
                    if (token) {
                        result.push(token);
                        expr = expr.slice(token.size || token.value.length);
                        break;
                    }
                }
            }
            else {
                token = false;
            }
        }
        if (expr.length) {
            throw new Error(`Tokenizer error: could not tokenize "${expr}"`);
        }
        return result;
    }
    //------------------------------------------------------------------------------
    // Expression "evaluator"
    //------------------------------------------------------------------------------
    /**
     * This is the main function exported by this file. This is the code that will
     * process an expression (given as a string) and returns another expression with
     * proper lookups in the context.
     *
     * Usually, this kind of code would be very simple to do if we had an AST (so,
     * if we had a javascript parser), since then, we would only need to find the
     * variables and replace them.  However, a parser is more complicated, and there
     * are no standard builtin parser API.
     *
     * Since this method is applied to simple javasript expressions, and the work to
     * be done is actually quite simple, we actually can get away with not using a
     * parser, which helps with the code size.
     *
     * Here is the heuristic used by this method to determine if a token is a
     * variable:
     * - by default, all symbols are considered a variable
     * - unless the previous token is a dot (in that case, this is a property: `a.b`)
     * - or if the previous token is a left brace or a comma, and the next token is
     *   a colon (in that case, this is an object key: `{a: b}`)
     *
     * Some specific code is also required to support arrow functions. If we detect
     * the arrow operator, then we add the current (or some previous tokens) token to
     * the list of variables so it does not get replaced by a lookup in the context
     */
    function compileExprToArray(expr, scope) {
        scope = Object.create(scope);
        const tokens = tokenize(expr);
        for (let i = 0; i < tokens.length; i++) {
            let token = tokens[i];
            let prevToken = tokens[i - 1];
            let nextToken = tokens[i + 1];
            let isVar = token.type === "SYMBOL" && !RESERVED_WORDS.includes(token.value);
            if (token.type === "SYMBOL" && !RESERVED_WORDS.includes(token.value)) {
                if (prevToken) {
                    if (prevToken.type === "OPERATOR" && prevToken.value === ".") {
                        isVar = false;
                    }
                    else if (prevToken.type === "LEFT_BRACE" || prevToken.type === "COMMA") {
                        if (nextToken && nextToken.type === "COLON") {
                            isVar = false;
                        }
                    }
                }
            }
            if (nextToken && nextToken.type === "OPERATOR" && nextToken.value === "=>") {
                if (token.type === "RIGHT_PAREN") {
                    let j = i - 1;
                    while (j > 0 && tokens[j].type !== "LEFT_PAREN") {
                        if (tokens[j].type === "SYMBOL" && tokens[j].originalValue) {
                            tokens[j].value = tokens[j].originalValue;
                            scope[tokens[j].value] = { id: tokens[j].value, expr: tokens[j].value };
                        }
                        j--;
                    }
                }
                else {
                    scope[token.value] = { id: token.value, expr: token.value };
                }
            }
            if (isVar) {
                token.varName = token.value;
                if (token.value in scope && "id" in scope[token.value]) {
                    token.value = scope[token.value].expr;
                }
                else {
                    token.originalValue = token.value;
                    token.value = `scope['${token.value}']`;
                }
            }
        }
        return tokens;
    }
    function compileExpr(expr, scope) {
        return compileExprToArray(expr, scope)
            .map((t) => t.value)
            .join("");
    }

    const INTERP_REGEXP = /\{\{.*?\}\}/g;
    //------------------------------------------------------------------------------
    // Compilation Context
    //------------------------------------------------------------------------------
    class CompilationContext {
        constructor(name) {
            this.code = [];
            this.variables = {};
            this.escaping = false;
            this.parentNode = null;
            this.parentTextNode = null;
            this.rootNode = null;
            this.indentLevel = 0;
            this.shouldDefineParent = false;
            this.shouldDefineScope = false;
            this.protectedScopeNumber = 0;
            this.shouldDefineQWeb = false;
            this.shouldDefineUtils = false;
            this.shouldDefineRefs = false;
            this.shouldDefineResult = true;
            this.loopNumber = 0;
            this.inPreTag = false;
            this.allowMultipleRoots = false;
            this.hasParentWidget = false;
            this.hasKey0 = false;
            this.keyStack = [];
            this.rootContext = this;
            this.templateName = name || "noname";
            this.addLine("let h = this.h;");
        }
        generateID() {
            return CompilationContext.nextID++;
        }
        /**
         * This method generates a "template key", which is basically a unique key
         * which depends on the currently set keys, and on the iteration numbers (if
         * we are in a loop).
         *
         * Such a key is necessary when we need to associate an id to some element
         * generated by a template (for example, a component)
         */
        generateTemplateKey(prefix = "") {
            const id = this.generateID();
            if (this.loopNumber === 0 && !this.hasKey0) {
                return `'${prefix}__${id}__'`;
            }
            let key = `\`${prefix}__${id}__`;
            let start = this.hasKey0 ? 0 : 1;
            for (let i = start; i < this.loopNumber + 1; i++) {
                key += `\${key${i}}__`;
            }
            this.addLine(`let k${id} = ${key}\`;`);
            return `k${id}`;
        }
        generateCode() {
            if (this.shouldDefineResult) {
                this.code.unshift("    let result;");
            }
            if (this.shouldDefineScope) {
                this.code.unshift("    let scope = Object.create(context);");
            }
            if (this.shouldDefineRefs) {
                this.code.unshift("    context.__owl__.refs = context.__owl__.refs || {};");
            }
            if (this.shouldDefineParent) {
                if (this.hasParentWidget) {
                    this.code.unshift("    let parent = extra.parent;");
                }
                else {
                    this.code.unshift("    let parent = context;");
                }
            }
            if (this.shouldDefineQWeb) {
                this.code.unshift("    let QWeb = this.constructor;");
            }
            if (this.shouldDefineUtils) {
                this.code.unshift("    let utils = this.constructor.utils;");
            }
            return this.code;
        }
        withParent(node) {
            if (!this.allowMultipleRoots &&
                this === this.rootContext &&
                (this.parentNode || this.parentTextNode)) {
                throw new Error("A template should not have more than one root node");
            }
            if (!this.rootContext.rootNode) {
                this.rootContext.rootNode = node;
            }
            if (!this.parentNode && this.rootContext.shouldDefineResult) {
                this.addLine(`result = vn${node};`);
            }
            return this.subContext("parentNode", node);
        }
        subContext(key, value) {
            const newContext = Object.create(this);
            newContext[key] = value;
            return newContext;
        }
        indent() {
            this.rootContext.indentLevel++;
        }
        dedent() {
            this.rootContext.indentLevel--;
        }
        addLine(line) {
            const prefix = new Array(this.indentLevel + 2).join("    ");
            this.code.push(prefix + line);
            return this.code.length - 1;
        }
        addIf(condition) {
            this.addLine(`if (${condition}) {`);
            this.indent();
        }
        addElse() {
            this.dedent();
            this.addLine("} else {");
            this.indent();
        }
        closeIf() {
            this.dedent();
            this.addLine("}");
        }
        getValue(val) {
            return val in this.variables ? this.getValue(this.variables[val]) : val;
        }
        /**
         * Prepare an expression for being consumed at render time.  Its main job
         * is to
         * - replace unknown variables by a lookup in the context
         * - replace already defined variables by their internal name
         */
        formatExpression(expr) {
            this.rootContext.shouldDefineScope = true;
            return compileExpr(expr, this.variables);
        }
        captureExpression(expr) {
            this.rootContext.shouldDefineScope = true;
            const argId = this.generateID();
            const tokens = compileExprToArray(expr, this.variables);
            const done = new Set();
            return tokens
                .map((tok) => {
                if (tok.varName) {
                    if (!done.has(tok.varName)) {
                        done.add(tok.varName);
                        this.addLine(`const ${tok.varName}_${argId} = ${tok.value};`);
                    }
                    tok.value = `${tok.varName}_${argId}`;
                }
                return tok.value;
            })
                .join("");
        }
        /**
         * Perform string interpolation on the given string. Note that if the whole
         * string is an expression, it simply returns it (formatted and enclosed in
         * parentheses).
         * For instance:
         *   'Hello {{x}}!' -> `Hello ${x}`
         *   '{{x ? 'a': 'b'}}' -> (x ? 'a' : 'b')
         */
        interpolate(s) {
            let matches = s.match(INTERP_REGEXP);
            if (matches && matches[0].length === s.length) {
                return `(${this.formatExpression(s.slice(2, -2))})`;
            }
            let r = s.replace(/\{\{.*?\}\}/g, (s) => "${" + this.formatExpression(s.slice(2, -2)) + "}");
            return "`" + r + "`";
        }
        startProtectScope(codeBlock) {
            const protectID = this.generateID();
            this.rootContext.protectedScopeNumber++;
            this.rootContext.shouldDefineScope = true;
            const scopeExpr = `Object.create(scope);`;
            this.addLine(`let _origScope${protectID} = scope;`);
            this.addLine(`scope = ${scopeExpr}`);
            if (!codeBlock) {
                this.addLine(`scope.__access_mode__ = 'ro';`);
            }
            return protectID;
        }
        stopProtectScope(protectID) {
            this.rootContext.protectedScopeNumber--;
            this.addLine(`scope = _origScope${protectID};`);
        }
    }
    CompilationContext.nextID = 1;

    //------------------------------------------------------------------------------
    // module/props.ts
    //------------------------------------------------------------------------------
    function updateProps(oldVnode, vnode) {
        var key, cur, old, elm = vnode.elm, oldProps = oldVnode.data.props, props = vnode.data.props;
        if (!oldProps && !props)
            return;
        if (oldProps === props)
            return;
        oldProps = oldProps || {};
        props = props || {};
        for (key in oldProps) {
            if (!props[key]) {
                delete elm[key];
            }
        }
        for (key in props) {
            cur = props[key];
            old = oldProps[key];
            if (old !== cur && (key !== "value" || elm[key] !== cur)) {
                elm[key] = cur;
            }
        }
    }
    const propsModule = {
        create: updateProps,
        update: updateProps,
    };
    //------------------------------------------------------------------------------
    // module/eventlisteners.ts
    //------------------------------------------------------------------------------
    function invokeHandler(handler, vnode, event) {
        if (typeof handler === "function") {
            // call function handler
            handler.call(vnode, event, vnode);
        }
        else if (typeof handler === "object") {
            // call handler with arguments
            if (typeof handler[0] === "function") {
                // special case for single argument for performance
                if (handler.length === 2) {
                    handler[0].call(vnode, handler[1], event, vnode);
                }
                else {
                    var args = handler.slice(1);
                    args.push(event);
                    args.push(vnode);
                    handler[0].apply(vnode, args);
                }
            }
            else {
                // call multiple handlers
                for (let i = 0, iLen = handler.length; i < iLen; i++) {
                    invokeHandler(handler[i], vnode, event);
                }
            }
        }
    }
    function handleEvent(event, vnode) {
        var name = event.type, on = vnode.data.on;
        // call event handler(s) if exists
        if (on) {
            if (on[name]) {
                invokeHandler(on[name], vnode, event);
            }
            else if (on["!" + name]) {
                invokeHandler(on["!" + name], vnode, event);
            }
        }
    }
    function createListener() {
        return function handler(event) {
            handleEvent(event, handler.vnode);
        };
    }
    function updateEventListeners(oldVnode, vnode) {
        var oldOn = oldVnode.data.on, oldListener = oldVnode.listener, oldElm = oldVnode.elm, on = vnode && vnode.data.on, elm = (vnode && vnode.elm), name;
        // optimization for reused immutable handlers
        if (oldOn === on) {
            return;
        }
        // remove existing listeners which no longer used
        if (oldOn && oldListener) {
            // if element changed or deleted we remove all existing listeners unconditionally
            if (!on) {
                for (name in oldOn) {
                    // remove listener if element was changed or existing listeners removed
                    const capture = name.charAt(0) === "!";
                    name = capture ? name.slice(1) : name;
                    oldElm.removeEventListener(name, oldListener, capture);
                }
            }
            else {
                for (name in oldOn) {
                    // remove listener if existing listener removed
                    if (!on[name]) {
                        const capture = name.charAt(0) === "!";
                        name = capture ? name.slice(1) : name;
                        oldElm.removeEventListener(name, oldListener, capture);
                    }
                }
            }
        }
        // add new listeners which has not already attached
        if (on) {
            // reuse existing listener or create new
            var listener = (vnode.listener = oldVnode.listener || createListener());
            // update vnode for listener
            listener.vnode = vnode;
            // if element changed or added we add all needed listeners unconditionally
            if (!oldOn) {
                for (name in on) {
                    // add listener if element was changed or new listeners added
                    const capture = name.charAt(0) === "!";
                    name = capture ? name.slice(1) : name;
                    elm.addEventListener(name, listener, capture);
                }
            }
            else {
                for (name in on) {
                    // add listener if new listener added
                    if (!oldOn[name]) {
                        const capture = name.charAt(0) === "!";
                        name = capture ? name.slice(1) : name;
                        elm.addEventListener(name, listener, capture);
                    }
                }
            }
        }
    }
    const eventListenersModule = {
        create: updateEventListeners,
        update: updateEventListeners,
        destroy: updateEventListeners,
    };
    //------------------------------------------------------------------------------
    // attributes.ts
    //------------------------------------------------------------------------------
    const xlinkNS = "http://www.w3.org/1999/xlink";
    const xmlNS = "http://www.w3.org/XML/1998/namespace";
    const colonChar = 58;
    const xChar = 120;
    function updateAttrs(oldVnode, vnode) {
        var key, elm = vnode.elm, oldAttrs = oldVnode.data.attrs, attrs = vnode.data.attrs;
        if (!oldAttrs && !attrs)
            return;
        if (oldAttrs === attrs)
            return;
        oldAttrs = oldAttrs || {};
        attrs = attrs || {};
        // update modified attributes, add new attributes
        for (key in attrs) {
            const cur = attrs[key];
            const old = oldAttrs[key];
            if (old !== cur) {
                if (cur === true) {
                    elm.setAttribute(key, "");
                }
                else if (cur === false) {
                    elm.removeAttribute(key);
                }
                else {
                    if (key.charCodeAt(0) !== xChar) {
                        elm.setAttribute(key, cur);
                    }
                    else if (key.charCodeAt(3) === colonChar) {
                        // Assume xml namespace
                        elm.setAttributeNS(xmlNS, key, cur);
                    }
                    else if (key.charCodeAt(5) === colonChar) {
                        // Assume xlink namespace
                        elm.setAttributeNS(xlinkNS, key, cur);
                    }
                    else {
                        elm.setAttribute(key, cur);
                    }
                }
            }
        }
        // remove removed attributes
        // use `in` operator since the previous `for` iteration uses it (.i.e. add even attributes with undefined value)
        // the other option is to remove all attributes with value == undefined
        for (key in oldAttrs) {
            if (!(key in attrs)) {
                elm.removeAttribute(key);
            }
        }
    }
    const attrsModule = {
        create: updateAttrs,
        update: updateAttrs,
    };
    //------------------------------------------------------------------------------
    // class.ts
    //------------------------------------------------------------------------------
    function updateClass(oldVnode, vnode) {
        var cur, name, elm, oldClass = oldVnode.data.class, klass = vnode.data.class;
        if (!oldClass && !klass)
            return;
        if (oldClass === klass)
            return;
        oldClass = oldClass || {};
        klass = klass || {};
        elm = vnode.elm;
        for (name in oldClass) {
            if (name && !klass[name]) {
                elm.classList.remove(name);
            }
        }
        for (name in klass) {
            cur = klass[name];
            if (cur !== oldClass[name]) {
                elm.classList[cur ? "add" : "remove"](name);
            }
        }
    }
    const classModule = { create: updateClass, update: updateClass };

    /**
     * Owl VDOM
     *
     * This file contains an implementation of a virtual DOM, which is a system that
     * can generate in-memory representations of a DOM tree, compare them, and
     * eventually change a concrete DOM tree to match its representation, in an
     * hopefully efficient way.
     *
     * Note that this code is a fork of Snabbdom, slightly tweaked/optimized for our
     * needs (see https://github.com/snabbdom/snabbdom).
     *
     * The main exported values are:
     * - interface VNode
     * - h function (a helper function to generate a vnode)
     * - patch function (to apply a vnode to an actual DOM node)
     */
    function vnode(sel, data, children, text, elm) {
        let key = data === undefined ? undefined : data.key;
        return { sel, data, children, text, elm, key };
    }
    //------------------------------------------------------------------------------
    // snabbdom.ts
    //------------------------------------------------------------------------------
    function isUndef(s) {
        return s === undefined;
    }
    function isDef(s) {
        return s !== undefined;
    }
    const emptyNode = vnode("", {}, [], undefined, undefined);
    function sameVnode(vnode1, vnode2) {
        return vnode1.key === vnode2.key && vnode1.sel === vnode2.sel;
    }
    function isVnode(vnode) {
        return vnode.sel !== undefined;
    }
    function createKeyToOldIdx(children, beginIdx, endIdx) {
        let i, map = {}, key, ch;
        for (i = beginIdx; i <= endIdx; ++i) {
            ch = children[i];
            if (ch != null) {
                key = ch.key;
                if (key !== undefined)
                    map[key] = i;
            }
        }
        return map;
    }
    const hooks = ["create", "update", "remove", "destroy", "pre", "post"];
    function init(modules, domApi) {
        let i, j, cbs = {};
        const api = domApi !== undefined ? domApi : htmlDomApi;
        for (i = 0; i < hooks.length; ++i) {
            cbs[hooks[i]] = [];
            for (j = 0; j < modules.length; ++j) {
                const hook = modules[j][hooks[i]];
                if (hook !== undefined) {
                    cbs[hooks[i]].push(hook);
                }
            }
        }
        function emptyNodeAt(elm) {
            const id = elm.id ? "#" + elm.id : "";
            const c = elm.className ? "." + elm.className.split(" ").join(".") : "";
            return vnode(api.tagName(elm).toLowerCase() + id + c, {}, [], undefined, elm);
        }
        function createRmCb(childElm, listeners) {
            return function rmCb() {
                if (--listeners === 0) {
                    const parent = api.parentNode(childElm);
                    api.removeChild(parent, childElm);
                }
            };
        }
        function createElm(vnode, insertedVnodeQueue) {
            let i, iLen, data = vnode.data;
            if (data !== undefined) {
                if (isDef((i = data.hook)) && isDef((i = i.init))) {
                    i(vnode);
                    data = vnode.data;
                }
            }
            let children = vnode.children, sel = vnode.sel;
            if (sel === "!") {
                if (isUndef(vnode.text)) {
                    vnode.text = "";
                }
                vnode.elm = api.createComment(vnode.text);
            }
            else if (sel !== undefined) {
                const elm = vnode.elm ||
                    (vnode.elm =
                        isDef(data) && isDef((i = data.ns))
                            ? api.createElementNS(i, sel)
                            : api.createElement(sel));
                for (i = 0, iLen = cbs.create.length; i < iLen; ++i)
                    cbs.create[i](emptyNode, vnode);
                if (array(children)) {
                    for (i = 0, iLen = children.length; i < iLen; ++i) {
                        const ch = children[i];
                        if (ch != null) {
                            api.appendChild(elm, createElm(ch, insertedVnodeQueue));
                        }
                    }
                }
                else if (primitive(vnode.text)) {
                    api.appendChild(elm, api.createTextNode(vnode.text));
                }
                i = vnode.data.hook; // Reuse variable
                if (isDef(i)) {
                    if (i.create)
                        i.create(emptyNode, vnode);
                    if (i.insert)
                        insertedVnodeQueue.push(vnode);
                }
            }
            else {
                vnode.elm = api.createTextNode(vnode.text);
            }
            return vnode.elm;
        }
        function addVnodes(parentElm, before, vnodes, startIdx, endIdx, insertedVnodeQueue) {
            for (; startIdx <= endIdx; ++startIdx) {
                const ch = vnodes[startIdx];
                if (ch != null) {
                    api.insertBefore(parentElm, createElm(ch, insertedVnodeQueue), before);
                }
            }
        }
        function invokeDestroyHook(vnode) {
            let i, iLen, j, jLen, data = vnode.data;
            if (data !== undefined) {
                if (isDef((i = data.hook)) && isDef((i = i.destroy)))
                    i(vnode);
                for (i = 0, iLen = cbs.destroy.length; i < iLen; ++i)
                    cbs.destroy[i](vnode);
                if (vnode.children !== undefined) {
                    for (j = 0, jLen = vnode.children.length; j < jLen; ++j) {
                        i = vnode.children[j];
                        if (i != null && typeof i !== "string") {
                            invokeDestroyHook(i);
                        }
                    }
                }
            }
        }
        function removeVnodes(parentElm, vnodes, startIdx, endIdx) {
            for (; startIdx <= endIdx; ++startIdx) {
                let i, iLen, listeners, rm, ch = vnodes[startIdx];
                if (ch != null) {
                    if (isDef(ch.sel)) {
                        invokeDestroyHook(ch);
                        listeners = cbs.remove.length + 1;
                        rm = createRmCb(ch.elm, listeners);
                        for (i = 0, iLen = cbs.remove.length; i < iLen; ++i)
                            cbs.remove[i](ch, rm);
                        if (isDef((i = ch.data)) && isDef((i = i.hook)) && isDef((i = i.remove))) {
                            i(ch, rm);
                        }
                        else {
                            rm();
                        }
                    }
                    else {
                        // Text node
                        api.removeChild(parentElm, ch.elm);
                    }
                }
            }
        }
        function updateChildren(parentElm, oldCh, newCh, insertedVnodeQueue) {
            let oldStartIdx = 0, newStartIdx = 0;
            let oldEndIdx = oldCh.length - 1;
            let oldStartVnode = oldCh[0];
            let oldEndVnode = oldCh[oldEndIdx];
            let newEndIdx = newCh.length - 1;
            let newStartVnode = newCh[0];
            let newEndVnode = newCh[newEndIdx];
            let oldKeyToIdx;
            let idxInOld;
            let elmToMove;
            let before;
            while (oldStartIdx <= oldEndIdx && newStartIdx <= newEndIdx) {
                if (oldStartVnode == null) {
                    oldStartVnode = oldCh[++oldStartIdx]; // Vnode might have been moved left
                }
                else if (oldEndVnode == null) {
                    oldEndVnode = oldCh[--oldEndIdx];
                }
                else if (newStartVnode == null) {
                    newStartVnode = newCh[++newStartIdx];
                }
                else if (newEndVnode == null) {
                    newEndVnode = newCh[--newEndIdx];
                }
                else if (sameVnode(oldStartVnode, newStartVnode)) {
                    patchVnode(oldStartVnode, newStartVnode, insertedVnodeQueue);
                    oldStartVnode = oldCh[++oldStartIdx];
                    newStartVnode = newCh[++newStartIdx];
                }
                else if (sameVnode(oldEndVnode, newEndVnode)) {
                    patchVnode(oldEndVnode, newEndVnode, insertedVnodeQueue);
                    oldEndVnode = oldCh[--oldEndIdx];
                    newEndVnode = newCh[--newEndIdx];
                }
                else if (sameVnode(oldStartVnode, newEndVnode)) {
                    // Vnode moved right
                    patchVnode(oldStartVnode, newEndVnode, insertedVnodeQueue);
                    api.insertBefore(parentElm, oldStartVnode.elm, api.nextSibling(oldEndVnode.elm));
                    oldStartVnode = oldCh[++oldStartIdx];
                    newEndVnode = newCh[--newEndIdx];
                }
                else if (sameVnode(oldEndVnode, newStartVnode)) {
                    // Vnode moved left
                    patchVnode(oldEndVnode, newStartVnode, insertedVnodeQueue);
                    api.insertBefore(parentElm, oldEndVnode.elm, oldStartVnode.elm);
                    oldEndVnode = oldCh[--oldEndIdx];
                    newStartVnode = newCh[++newStartIdx];
                }
                else {
                    if (oldKeyToIdx === undefined) {
                        oldKeyToIdx = createKeyToOldIdx(oldCh, oldStartIdx, oldEndIdx);
                    }
                    idxInOld = oldKeyToIdx[newStartVnode.key];
                    if (isUndef(idxInOld)) {
                        // New element
                        api.insertBefore(parentElm, createElm(newStartVnode, insertedVnodeQueue), oldStartVnode.elm);
                        newStartVnode = newCh[++newStartIdx];
                    }
                    else {
                        elmToMove = oldCh[idxInOld];
                        if (elmToMove.sel !== newStartVnode.sel) {
                            api.insertBefore(parentElm, createElm(newStartVnode, insertedVnodeQueue), oldStartVnode.elm);
                        }
                        else {
                            patchVnode(elmToMove, newStartVnode, insertedVnodeQueue);
                            oldCh[idxInOld] = undefined;
                            api.insertBefore(parentElm, elmToMove.elm, oldStartVnode.elm);
                        }
                        newStartVnode = newCh[++newStartIdx];
                    }
                }
            }
            if (oldStartIdx <= oldEndIdx || newStartIdx <= newEndIdx) {
                if (oldStartIdx > oldEndIdx) {
                    before = newCh[newEndIdx + 1] == null ? null : newCh[newEndIdx + 1].elm;
                    addVnodes(parentElm, before, newCh, newStartIdx, newEndIdx, insertedVnodeQueue);
                }
                else {
                    removeVnodes(parentElm, oldCh, oldStartIdx, oldEndIdx);
                }
            }
        }
        function patchVnode(oldVnode, vnode, insertedVnodeQueue) {
            let i, iLen, hook;
            if (isDef((i = vnode.data)) && isDef((hook = i.hook)) && isDef((i = hook.prepatch))) {
                i(oldVnode, vnode);
            }
            const elm = (vnode.elm = oldVnode.elm);
            let oldCh = oldVnode.children;
            let ch = vnode.children;
            if (oldVnode === vnode)
                return;
            if (vnode.data !== undefined) {
                for (i = 0, iLen = cbs.update.length; i < iLen; ++i)
                    cbs.update[i](oldVnode, vnode);
                i = vnode.data.hook;
                if (isDef(i) && isDef((i = i.update)))
                    i(oldVnode, vnode);
            }
            if (isUndef(vnode.text)) {
                if (isDef(oldCh) && isDef(ch)) {
                    if (oldCh !== ch)
                        updateChildren(elm, oldCh, ch, insertedVnodeQueue);
                }
                else if (isDef(ch)) {
                    if (isDef(oldVnode.text))
                        api.setTextContent(elm, "");
                    addVnodes(elm, null, ch, 0, ch.length - 1, insertedVnodeQueue);
                }
                else if (isDef(oldCh)) {
                    removeVnodes(elm, oldCh, 0, oldCh.length - 1);
                }
                else if (isDef(oldVnode.text)) {
                    api.setTextContent(elm, "");
                }
            }
            else if (oldVnode.text !== vnode.text) {
                if (isDef(oldCh)) {
                    removeVnodes(elm, oldCh, 0, oldCh.length - 1);
                }
                api.setTextContent(elm, vnode.text);
            }
            if (isDef(hook) && isDef((i = hook.postpatch))) {
                i(oldVnode, vnode);
            }
        }
        return function patch(oldVnode, vnode) {
            let i, iLen, elm, parent;
            const insertedVnodeQueue = [];
            for (i = 0, iLen = cbs.pre.length; i < iLen; ++i)
                cbs.pre[i]();
            if (!isVnode(oldVnode)) {
                oldVnode = emptyNodeAt(oldVnode);
            }
            if (sameVnode(oldVnode, vnode)) {
                patchVnode(oldVnode, vnode, insertedVnodeQueue);
            }
            else {
                elm = oldVnode.elm;
                parent = api.parentNode(elm);
                createElm(vnode, insertedVnodeQueue);
                if (parent !== null) {
                    api.insertBefore(parent, vnode.elm, api.nextSibling(elm));
                    removeVnodes(parent, [oldVnode], 0, 0);
                }
            }
            for (i = 0, iLen = insertedVnodeQueue.length; i < iLen; ++i) {
                insertedVnodeQueue[i].data.hook.insert(insertedVnodeQueue[i]);
            }
            for (i = 0, iLen = cbs.post.length; i < iLen; ++i)
                cbs.post[i]();
            return vnode;
        };
    }
    //------------------------------------------------------------------------------
    // is.ts
    //------------------------------------------------------------------------------
    const array = Array.isArray;
    function primitive(s) {
        return typeof s === "string" || typeof s === "number";
    }
    function createElement(tagName) {
        return document.createElement(tagName);
    }
    function createElementNS(namespaceURI, qualifiedName) {
        return document.createElementNS(namespaceURI, qualifiedName);
    }
    function createTextNode(text) {
        return document.createTextNode(text);
    }
    function createComment(text) {
        return document.createComment(text);
    }
    function insertBefore(parentNode, newNode, referenceNode) {
        parentNode.insertBefore(newNode, referenceNode);
    }
    function removeChild(node, child) {
        node.removeChild(child);
    }
    function appendChild(node, child) {
        node.appendChild(child);
    }
    function parentNode(node) {
        return node.parentNode;
    }
    function nextSibling(node) {
        return node.nextSibling;
    }
    function tagName(elm) {
        return elm.tagName;
    }
    function setTextContent(node, text) {
        node.textContent = text;
    }
    const htmlDomApi = {
        createElement,
        createElementNS,
        createTextNode,
        createComment,
        insertBefore,
        removeChild,
        appendChild,
        parentNode,
        nextSibling,
        tagName,
        setTextContent,
    };
    function addNS(data, children, sel) {
        if (sel === "dummy") {
            // we do not need to add the namespace on dummy elements, they come from a
            // subcomponent, which will handle the namespace itself
            return;
        }
        data.ns = "http://www.w3.org/2000/svg";
        if (sel !== "foreignObject" && children !== undefined) {
            for (let i = 0, iLen = children.length; i < iLen; ++i) {
                const child = children[i];
                let childData = child.data;
                if (childData !== undefined) {
                    addNS(childData, child.children, child.sel);
                }
            }
        }
    }
    function h(sel, b, c) {
        var data = {}, children, text, i, iLen;
        if (c !== undefined) {
            data = b;
            if (array(c)) {
                children = c;
            }
            else if (primitive(c)) {
                text = c;
            }
            else if (c && c.sel) {
                children = [c];
            }
        }
        else if (b !== undefined) {
            if (array(b)) {
                children = b;
            }
            else if (primitive(b)) {
                text = b;
            }
            else if (b && b.sel) {
                children = [b];
            }
            else {
                data = b;
            }
        }
        if (children !== undefined) {
            for (i = 0, iLen = children.length; i < iLen; ++i) {
                if (primitive(children[i]))
                    children[i] = vnode(undefined, undefined, undefined, children[i], undefined);
            }
        }
        return vnode(sel, data, children, text, undefined);
    }

    const patch = init([eventListenersModule, attrsModule, propsModule, classModule]);

    let localStorage = null;
    const browser = {
        setTimeout: window.setTimeout.bind(window),
        clearTimeout: window.clearTimeout.bind(window),
        setInterval: window.setInterval.bind(window),
        clearInterval: window.clearInterval.bind(window),
        requestAnimationFrame: window.requestAnimationFrame.bind(window),
        random: Math.random,
        Date: window.Date,
        fetch: (window.fetch || (() => { })).bind(window),
        get localStorage() {
            return localStorage || window.localStorage;
        },
        set localStorage(newLocalStorage) {
            localStorage = newLocalStorage;
        },
    };

    /**
     * Owl Utils
     *
     * We have here a small collection of utility functions:
     *
     * - whenReady
     * - loadJS
     * - loadFile
     * - escape
     * - debounce
     */
    function whenReady(fn) {
        return new Promise(function (resolve) {
            if (document.readyState !== "loading") {
                resolve();
            }
            else {
                document.addEventListener("DOMContentLoaded", resolve, false);
            }
        }).then(fn || function () { });
    }
    const loadedScripts = {};
    function loadJS(url) {
        if (url in loadedScripts) {
            return loadedScripts[url];
        }
        const promise = new Promise(function (resolve, reject) {
            const script = document.createElement("script");
            script.type = "text/javascript";
            script.src = url;
            script.onload = function () {
                resolve();
            };
            script.onerror = function () {
                reject(`Error loading file '${url}'`);
            };
            const head = document.head || document.getElementsByTagName("head")[0];
            head.appendChild(script);
        });
        loadedScripts[url] = promise;
        return promise;
    }
    async function loadFile(url) {
        const result = await browser.fetch(url);
        if (!result.ok) {
            throw new Error("Error while fetching xml templates");
        }
        return await result.text();
    }
    function escape(str) {
        if (str === undefined) {
            return "";
        }
        if (typeof str === "number") {
            return String(str);
        }
        const p = document.createElement("p");
        p.textContent = str;
        return p.innerHTML;
    }
    /**
     * Returns a function, that, as long as it continues to be invoked, will not
     * be triggered. The function will be called after it stops being called for
     * N milliseconds. If `immediate` is passed, trigger the function on the
     * leading edge, instead of the trailing.
     *
     * Inspired by https://davidwalsh.name/javascript-debounce-function
     */
    function debounce(func, wait, immediate) {
        let timeout;
        return function () {
            const context = this;
            const args = arguments;
            function later() {
                timeout = null;
                if (!immediate) {
                    func.apply(context, args);
                }
            }
            const callNow = immediate && !timeout;
            browser.clearTimeout(timeout);
            timeout = browser.setTimeout(later, wait);
            if (callNow) {
                func.apply(context, args);
            }
        };
    }
    function shallowEqual(p1, p2) {
        for (let k in p1) {
            if (p1[k] !== p2[k]) {
                return false;
            }
        }
        return true;
    }

    var _utils = /*#__PURE__*/Object.freeze({
        __proto__: null,
        whenReady: whenReady,
        loadJS: loadJS,
        loadFile: loadFile,
        escape: escape,
        debounce: debounce,
        shallowEqual: shallowEqual
    });

    //------------------------------------------------------------------------------
    // Const/global stuff/helpers
    //------------------------------------------------------------------------------
    const TRANSLATABLE_ATTRS = ["label", "title", "placeholder", "alt"];
    const lineBreakRE = /[\r\n]/;
    const whitespaceRE = /\s+/g;
    const translationRE = /^(\s*)([\s\S]+?)(\s*)$/;
    const NODE_HOOKS_PARAMS = {
        create: "(_, n)",
        insert: "vn",
        remove: "(vn, rm)",
        destroy: "()",
    };
    function isComponent(obj) {
        return obj && obj.hasOwnProperty("__owl__");
    }
    class VDomArray extends Array {
        toString() {
            return vDomToString(this);
        }
    }
    function vDomToString(vdom) {
        return vdom
            .map((vnode) => {
            if (vnode.sel) {
                const node = document.createElement(vnode.sel);
                const result = patch(node, vnode);
                return result.elm.outerHTML;
            }
            else {
                return vnode.text;
            }
        })
            .join("");
    }
    const UTILS = {
        zero: Symbol("zero"),
        toObj(expr) {
            if (typeof expr === "string") {
                expr = expr.trim();
                if (!expr) {
                    return {};
                }
                let words = expr.split(/\s+/);
                let result = {};
                for (let i = 0; i < words.length; i++) {
                    result[words[i]] = true;
                }
                return result;
            }
            return expr;
        },
        shallowEqual,
        addNameSpace(vnode) {
            addNS(vnode.data, vnode.children, vnode.sel);
        },
        VDomArray,
        vDomToString,
        getComponent(obj) {
            while (obj && !isComponent(obj)) {
                obj = obj.__proto__;
            }
            return obj;
        },
        getScope(obj, property) {
            const obj0 = obj;
            while (obj &&
                !obj.hasOwnProperty(property) &&
                !(obj.hasOwnProperty("__access_mode__") && obj.__access_mode__ === "ro")) {
                const newObj = obj.__proto__;
                if (!newObj || isComponent(newObj)) {
                    return obj0;
                }
                obj = newObj;
            }
            return obj;
        },
    };
    function parseXML(xml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(xml, "text/xml");
        if (doc.getElementsByTagName("parsererror").length) {
            let msg = "Invalid XML in template.";
            const parsererrorText = doc.getElementsByTagName("parsererror")[0].textContent;
            if (parsererrorText) {
                msg += "\nThe parser has produced the following error message:\n" + parsererrorText;
                const re = /\d+/g;
                const firstMatch = re.exec(parsererrorText);
                if (firstMatch) {
                    const lineNumber = Number(firstMatch[0]);
                    const line = xml.split("\n")[lineNumber - 1];
                    const secondMatch = re.exec(parsererrorText);
                    if (line && secondMatch) {
                        const columnIndex = Number(secondMatch[0]) - 1;
                        if (line[columnIndex]) {
                            msg +=
                                `\nThe error might be located at xml line ${lineNumber} column ${columnIndex}\n` +
                                    `${line}\n${"-".repeat(columnIndex - 1)}^`;
                        }
                    }
                }
            }
            throw new Error(msg);
        }
        return doc;
    }
    function escapeQuotes(str) {
        return str.replace(/\'/g, "\\'");
    }
    //------------------------------------------------------------------------------
    // QWeb rendering engine
    //------------------------------------------------------------------------------
    class QWeb extends EventBus {
        constructor(config = {}) {
            super();
            this.h = h;
            // subTemplates are stored in two objects: a (local) mapping from a name to an
            // id, and a (global) mapping from an id to the compiled function.  This is
            // necessary to ensure that global templates can be called with more than one
            // QWeb instance.
            this.subTemplates = {};
            this.isUpdating = false;
            this.templates = Object.create(QWeb.TEMPLATES);
            if (config.templates) {
                this.addTemplates(config.templates);
            }
            if (config.translateFn) {
                this.translateFn = config.translateFn;
            }
        }
        static addDirective(directive) {
            if (directive.name in QWeb.DIRECTIVE_NAMES) {
                throw new Error(`Directive "${directive.name} already registered`);
            }
            QWeb.DIRECTIVES.push(directive);
            QWeb.DIRECTIVE_NAMES[directive.name] = 1;
            QWeb.DIRECTIVES.sort((d1, d2) => d1.priority - d2.priority);
            if (directive.extraNames) {
                directive.extraNames.forEach((n) => (QWeb.DIRECTIVE_NAMES[n] = 1));
            }
        }
        static registerComponent(name, Component) {
            if (QWeb.components[name]) {
                throw new Error(`Component '${name}' has already been registered`);
            }
            QWeb.components[name] = Component;
        }
        /**
         * Register globally a template.  All QWeb instances will obtain their
         * templates from their own template map, and then, from the global static
         * TEMPLATES property.
         */
        static registerTemplate(name, template) {
            if (QWeb.TEMPLATES[name]) {
                throw new Error(`Template '${name}' has already been registered`);
            }
            const qweb = new QWeb();
            qweb.addTemplate(name, template);
            QWeb.TEMPLATES[name] = qweb.templates[name];
        }
        /**
         * Add a template to the internal template map.  Note that it is not
         * immediately compiled.
         */
        addTemplate(name, xmlString, allowDuplicate) {
            if (allowDuplicate && name in this.templates) {
                return;
            }
            const doc = parseXML(xmlString);
            if (!doc.firstChild) {
                throw new Error("Invalid template (should not be empty)");
            }
            this._addTemplate(name, doc.firstChild);
        }
        /**
         * Load templates from a xml (as a string or xml document).  This will look up
         * for the first <templates> tag, and will consider each child of this as a
         * template, with the name given by the t-name attribute.
         */
        addTemplates(xmlstr) {
            const doc = typeof xmlstr === "string" ? parseXML(xmlstr) : xmlstr;
            const templates = doc.getElementsByTagName("templates")[0];
            if (!templates) {
                return;
            }
            for (let elem of templates.children) {
                const name = elem.getAttribute("t-name");
                this._addTemplate(name, elem);
            }
        }
        _addTemplate(name, elem) {
            if (name in this.templates) {
                throw new Error(`Template ${name} already defined`);
            }
            this._processTemplate(elem);
            const template = {
                elem,
                fn: function (context, extra) {
                    const compiledFunction = this._compile(name);
                    template.fn = compiledFunction;
                    return compiledFunction.call(this, context, extra);
                },
            };
            this.templates[name] = template;
        }
        _processTemplate(elem) {
            let tbranch = elem.querySelectorAll("[t-elif], [t-else]");
            for (let i = 0, ilen = tbranch.length; i < ilen; i++) {
                let node = tbranch[i];
                let prevElem = node.previousElementSibling;
                let pattr = function (name) {
                    return prevElem.getAttribute(name);
                };
                let nattr = function (name) {
                    return +!!node.getAttribute(name);
                };
                if (prevElem && (pattr("t-if") || pattr("t-elif"))) {
                    if (pattr("t-foreach")) {
                        throw new Error("t-if cannot stay at the same level as t-foreach when using t-elif or t-else");
                    }
                    if (["t-if", "t-elif", "t-else"].map(nattr).reduce(function (a, b) {
                        return a + b;
                    }) > 1) {
                        throw new Error("Only one conditional branching directive is allowed per node");
                    }
                    // All text (with only spaces) and comment nodes (nodeType 8) between
                    // branch nodes are removed
                    let textNode;
                    while ((textNode = node.previousSibling) !== prevElem) {
                        if (textNode.nodeValue.trim().length && textNode.nodeType !== 8) {
                            throw new Error("text is not allowed between branching directives");
                        }
                        textNode.remove();
                    }
                }
                else {
                    throw new Error("t-elif and t-else directives must be preceded by a t-if or t-elif directive");
                }
            }
        }
        /**
         * Render a template
         *
         * @param {string} name the template should already have been added
         */
        render(name, context = {}, extra = null) {
            const template = this.templates[name];
            if (!template) {
                throw new Error(`Template ${name} does not exist`);
            }
            return template.fn.call(this, context, extra);
        }
        /**
         * Render a template to a html string.
         *
         * Note that this is more limited than the `render` method: it is not suitable
         * to render a full component tree, since this is an asynchronous operation.
         * This method can only render templates without components.
         */
        renderToString(name, context = {}, extra) {
            const vnode = this.render(name, context, extra);
            if (vnode.sel === undefined) {
                return vnode.text;
            }
            const node = document.createElement(vnode.sel);
            const elem = patch(node, vnode).elm;
            function escapeTextNodes(node) {
                if (node.nodeType === 3) {
                    node.textContent = escape(node.textContent);
                }
                for (let n of node.childNodes) {
                    escapeTextNodes(n);
                }
            }
            escapeTextNodes(elem);
            return elem.outerHTML;
        }
        /**
         * Force all widgets connected to this QWeb instance to rerender themselves.
         *
         * This method is mostly useful for external code that want to modify the
         * application in some cases.  For example, a router plugin.
         */
        forceUpdate() {
            this.isUpdating = true;
            Promise.resolve().then(() => {
                if (this.isUpdating) {
                    this.isUpdating = false;
                    this.trigger("update");
                }
            });
        }
        _compile(name, options = {}) {
            const elem = options.elem || this.templates[name].elem;
            const isDebug = elem.attributes.hasOwnProperty("t-debug");
            const ctx = new CompilationContext(name);
            if (elem.tagName !== "t") {
                ctx.shouldDefineResult = false;
            }
            if (options.hasParent) {
                ctx.variables = Object.create(null);
                ctx.parentNode = ctx.generateID();
                ctx.allowMultipleRoots = true;
                ctx.hasParentWidget = true;
                ctx.shouldDefineResult = false;
                ctx.addLine(`let c${ctx.parentNode} = extra.parentNode;`);
                if (options.defineKey) {
                    ctx.addLine(`let key0 = extra.key || "";`);
                    ctx.hasKey0 = true;
                }
            }
            this._compileNode(elem, ctx);
            if (!options.hasParent) {
                if (ctx.shouldDefineResult) {
                    ctx.addLine(`return result;`);
                }
                else {
                    if (!ctx.rootNode) {
                        throw new Error(`A template should have one root node (${ctx.templateName})`);
                    }
                    ctx.addLine(`return vn${ctx.rootNode};`);
                }
            }
            let code = ctx.generateCode();
            const templateName = ctx.templateName.replace(/`/g, "'").slice(0, 200);
            code.unshift(`    // Template name: "${templateName}"`);
            let template;
            try {
                template = new Function("context, extra", code.join("\n"));
            }
            catch (e) {
                console.groupCollapsed(`Invalid Code generated by ${templateName}`);
                console.warn(code.join("\n"));
                console.groupEnd();
                throw new Error(`Invalid generated code while compiling template '${templateName}': ${e.message}`);
            }
            if (isDebug) {
                const tpl = this.templates[name];
                if (tpl) {
                    const msg = `Template: ${tpl.elem.outerHTML}\nCompiled code:\n${template.toString()}`;
                    console.log(msg);
                }
            }
            return template;
        }
        /**
         * Generate code from an xml node
         *
         */
        _compileNode(node, ctx) {
            if (!(node instanceof Element)) {
                // this is a text node, there are no directive to apply
                let text = node.textContent;
                if (!ctx.inPreTag) {
                    if (lineBreakRE.test(text) && !text.trim()) {
                        return;
                    }
                    text = text.replace(whitespaceRE, " ");
                }
                if (this.translateFn) {
                    if (node.parentNode.getAttribute("t-translation") !== "off") {
                        const match = translationRE.exec(text);
                        text = match[1] + this.translateFn(match[2]) + match[3];
                    }
                }
                if (ctx.parentNode) {
                    if (node.nodeType === 3) {
                        ctx.addLine(`c${ctx.parentNode}.push({text: \`${text}\`});`);
                    }
                    else if (node.nodeType === 8) {
                        ctx.addLine(`c${ctx.parentNode}.push(h('!', \`${text}\`));`);
                    }
                }
                else if (ctx.parentTextNode) {
                    ctx.addLine(`vn${ctx.parentTextNode}.text += \`${text}\`;`);
                }
                else {
                    // this is an unusual situation: this text node is the result of the
                    // template rendering.
                    let nodeID = ctx.generateID();
                    ctx.addLine(`let vn${nodeID} = {text: \`${text}\`};`);
                    ctx.addLine(`result = vn${nodeID};`);
                    ctx.rootContext.rootNode = nodeID;
                    ctx.rootContext.parentTextNode = nodeID;
                }
                return;
            }
            if (node.tagName !== "t" && node.hasAttribute("t-call")) {
                const tCallNode = document.createElement("t");
                tCallNode.setAttribute("t-call", node.getAttribute("t-call"));
                node.removeAttribute("t-call");
                node.prepend(tCallNode);
            }
            const firstLetter = node.tagName[0];
            if (firstLetter === firstLetter.toUpperCase()) {
                // this is a component, we modify in place the xml document to change
                // <SomeComponent ... /> to <SomeComponent t-component="SomeComponent" ... />
                node.setAttribute("t-component", node.tagName);
            }
            else if (node.tagName !== "t" && node.hasAttribute("t-component")) {
                throw new Error(`Directive 't-component' can only be used on <t> nodes (used on a <${node.tagName}>)`);
            }
            const attributes = node.attributes;
            const validDirectives = [];
            const finalizers = [];
            // maybe this is not optimal: we iterate on all attributes here, and again
            // just after for each directive.
            for (let i = 0; i < attributes.length; i++) {
                let attrName = attributes[i].name;
                if (attrName.startsWith("t-")) {
                    let dName = attrName.slice(2).split(/-|\./)[0];
                    if (!(dName in QWeb.DIRECTIVE_NAMES)) {
                        throw new Error(`Unknown QWeb directive: '${attrName}'`);
                    }
                    if (node.tagName !== "t" && (attrName === "t-esc" || attrName === "t-raw")) {
                        const tNode = document.createElement("t");
                        tNode.setAttribute(attrName, node.getAttribute(attrName));
                        for (let child of Array.from(node.childNodes)) {
                            tNode.appendChild(child);
                        }
                        node.appendChild(tNode);
                        node.removeAttribute(attrName);
                    }
                }
            }
            const DIR_N = QWeb.DIRECTIVES.length;
            const ATTR_N = attributes.length;
            let withHandlers = false;
            for (let i = 0; i < DIR_N; i++) {
                let directive = QWeb.DIRECTIVES[i];
                let fullName;
                let value;
                for (let j = 0; j < ATTR_N; j++) {
                    const name = attributes[j].name;
                    if (name === "t-" + directive.name ||
                        name.startsWith("t-" + directive.name + "-") ||
                        name.startsWith("t-" + directive.name + ".")) {
                        fullName = name;
                        value = attributes[j].textContent;
                        validDirectives.push({ directive, value, fullName });
                        if (directive.name === "on" || directive.name === "model") {
                            withHandlers = true;
                        }
                    }
                }
            }
            for (let { directive, value, fullName } of validDirectives) {
                if (directive.finalize) {
                    finalizers.push({ directive, value, fullName });
                }
                if (directive.atNodeEncounter) {
                    const isDone = directive.atNodeEncounter({
                        node,
                        qweb: this,
                        ctx,
                        fullName,
                        value,
                    });
                    if (isDone) {
                        for (let { directive, value, fullName } of finalizers) {
                            directive.finalize({ node, qweb: this, ctx, fullName, value });
                        }
                        return;
                    }
                }
            }
            if (node.nodeName !== "t") {
                let nodeID = this._compileGenericNode(node, ctx, withHandlers);
                ctx = ctx.withParent(nodeID);
                let nodeHooks = {};
                let addNodeHook = function (hook, handler) {
                    nodeHooks[hook] = nodeHooks[hook] || [];
                    nodeHooks[hook].push(handler);
                };
                for (let { directive, value, fullName } of validDirectives) {
                    if (directive.atNodeCreation) {
                        directive.atNodeCreation({
                            node,
                            qweb: this,
                            ctx,
                            fullName,
                            value,
                            nodeID,
                            addNodeHook,
                        });
                    }
                }
                if (Object.keys(nodeHooks).length) {
                    ctx.addLine(`p${nodeID}.hook = {`);
                    for (let hook in nodeHooks) {
                        ctx.addLine(`  ${hook}: ${NODE_HOOKS_PARAMS[hook]} => {`);
                        for (let handler of nodeHooks[hook]) {
                            ctx.addLine(`    ${handler}`);
                        }
                        ctx.addLine(`  },`);
                    }
                    ctx.addLine(`};`);
                }
            }
            if (node.nodeName === "pre") {
                ctx = ctx.subContext("inPreTag", true);
            }
            this._compileChildren(node, ctx);
            // svg support
            // we hadd svg namespace if it is a svg or if it is a g, but only if it is
            // the root node.  This is the easiest way to support svg sub components:
            // they need to have a g tag as root. Otherwise, we would need a complete
            // list of allowed svg tags.
            const shouldAddNS = node.nodeName === "svg" || (node.nodeName === "g" && ctx.rootNode === ctx.parentNode);
            if (shouldAddNS) {
                ctx.rootContext.shouldDefineUtils = true;
                ctx.addLine(`utils.addNameSpace(vn${ctx.parentNode});`);
            }
            for (let { directive, value, fullName } of finalizers) {
                directive.finalize({ node, qweb: this, ctx, fullName, value });
            }
        }
        _compileGenericNode(node, ctx, withHandlers = true) {
            // nodeType 1 is generic tag
            if (node.nodeType !== 1) {
                throw new Error("unsupported node type");
            }
            const attributes = node.attributes;
            const attrs = [];
            const props = [];
            const tattrs = [];
            function handleProperties(key, val) {
                let isProp = false;
                switch (node.nodeName) {
                    case "input":
                        let type = node.getAttribute("type");
                        if (type === "checkbox" || type === "radio") {
                            if (key === "checked" || key === "indeterminate") {
                                isProp = true;
                            }
                        }
                        if (key === "value" || key === "readonly" || key === "disabled") {
                            isProp = true;
                        }
                        break;
                    case "option":
                        isProp = key === "selected" || key === "disabled";
                        break;
                    case "textarea":
                        isProp = key === "readonly" || key === "disabled";
                        break;
                    case "button":
                    case "select":
                    case "optgroup":
                        isProp = key === "disabled";
                        break;
                }
                if (isProp) {
                    props.push(`${key}: _${val}`);
                }
            }
            let classObj = "";
            for (let i = 0; i < attributes.length; i++) {
                let name = attributes[i].name;
                let value = attributes[i].textContent;
                if (this.translateFn && TRANSLATABLE_ATTRS.includes(name)) {
                    value = this.translateFn(value);
                }
                // regular attributes
                if (!name.startsWith("t-") && !node.getAttribute("t-attf-" + name)) {
                    const attID = ctx.generateID();
                    if (name === "class") {
                        if ((value = value.trim())) {
                            let classDef = value
                                .split(/\s+/)
                                .map((a) => `'${escapeQuotes(a)}':true`)
                                .join(",");
                            if (classObj) {
                                ctx.addLine(`Object.assign(${classObj}, {${classDef}})`);
                            }
                            else {
                                classObj = `_${ctx.generateID()}`;
                                ctx.addLine(`let ${classObj} = {${classDef}};`);
                            }
                        }
                    }
                    else {
                        ctx.addLine(`let _${attID} = '${escapeQuotes(value)}';`);
                        if (!name.match(/^[a-zA-Z]+$/)) {
                            // attribute contains 'non letters' => we want to quote it
                            name = '"' + name + '"';
                        }
                        attrs.push(`${name}: _${attID}`);
                        handleProperties(name, attID);
                    }
                }
                // dynamic attributes
                if (name.startsWith("t-att-")) {
                    let attName = name.slice(6);
                    const v = ctx.getValue(value);
                    let formattedValue = typeof v === "string" ? ctx.formatExpression(v) : `scope.${v.id}`;
                    if (attName === "class") {
                        ctx.rootContext.shouldDefineUtils = true;
                        formattedValue = `utils.toObj(${formattedValue})`;
                        if (classObj) {
                            ctx.addLine(`Object.assign(${classObj}, ${formattedValue})`);
                        }
                        else {
                            classObj = `_${ctx.generateID()}`;
                            ctx.addLine(`let ${classObj} = ${formattedValue};`);
                        }
                    }
                    else {
                        const attID = ctx.generateID();
                        if (!attName.match(/^[a-zA-Z]+$/)) {
                            // attribute contains 'non letters' => we want to quote it
                            attName = '"' + attName + '"';
                        }
                        // we need to combine dynamic with non dynamic attributes:
                        // class="a" t-att-class="'yop'" should be rendered as class="a yop"
                        const attValue = node.getAttribute(attName);
                        if (attValue) {
                            const attValueID = ctx.generateID();
                            ctx.addLine(`let _${attValueID} = ${formattedValue};`);
                            formattedValue = `'${attValue}' + (_${attValueID} ? ' ' + _${attValueID} : '')`;
                            const attrIndex = attrs.findIndex((att) => att.startsWith(attName + ":"));
                            attrs.splice(attrIndex, 1);
                        }
                        ctx.addLine(`let _${attID} = ${formattedValue};`);
                        attrs.push(`${attName}: _${attID}`);
                        handleProperties(attName, attID);
                    }
                }
                if (name.startsWith("t-attf-")) {
                    let attName = name.slice(7);
                    if (!attName.match(/^[a-zA-Z]+$/)) {
                        // attribute contains 'non letters' => we want to quote it
                        attName = '"' + attName + '"';
                    }
                    const formattedExpr = ctx.interpolate(value);
                    const attID = ctx.generateID();
                    let staticVal = node.getAttribute(attName);
                    if (staticVal) {
                        ctx.addLine(`let _${attID} = '${staticVal} ' + ${formattedExpr};`);
                    }
                    else {
                        ctx.addLine(`let _${attID} = ${formattedExpr};`);
                    }
                    attrs.push(`${attName}: _${attID}`);
                }
                // t-att= attributes
                if (name === "t-att") {
                    let id = ctx.generateID();
                    ctx.addLine(`let _${id} = ${ctx.formatExpression(value)};`);
                    tattrs.push(id);
                }
            }
            let nodeID = ctx.generateID();
            let key = ctx.loopNumber || ctx.hasKey0 ? `\`\${key${ctx.loopNumber}}_${nodeID}\`` : nodeID;
            const parts = [`key:${key}`];
            if (attrs.length + tattrs.length > 0) {
                parts.push(`attrs:{${attrs.join(",")}}`);
            }
            if (props.length > 0) {
                parts.push(`props:{${props.join(",")}}`);
            }
            if (classObj) {
                parts.push(`class:${classObj}`);
            }
            if (withHandlers) {
                parts.push(`on:{}`);
            }
            ctx.addLine(`let c${nodeID} = [], p${nodeID} = {${parts.join(",")}};`);
            for (let id of tattrs) {
                ctx.addIf(`_${id} instanceof Array`);
                ctx.addLine(`p${nodeID}.attrs[_${id}[0]] = _${id}[1];`);
                ctx.addElse();
                ctx.addLine(`for (let key in _${id}) {`);
                ctx.indent();
                ctx.addLine(`p${nodeID}.attrs[key] = _${id}[key];`);
                ctx.dedent();
                ctx.addLine(`}`);
                ctx.closeIf();
            }
            ctx.addLine(`let vn${nodeID} = h('${node.nodeName}', p${nodeID}, c${nodeID});`);
            if (ctx.parentNode) {
                ctx.addLine(`c${ctx.parentNode}.push(vn${nodeID});`);
            }
            else if (ctx.loopNumber || ctx.hasKey0) {
                ctx.rootContext.shouldDefineResult = true;
                ctx.addLine(`result = vn${nodeID};`);
            }
            return nodeID;
        }
        _compileChildren(node, ctx) {
            if (node.childNodes.length > 0) {
                for (let child of Array.from(node.childNodes)) {
                    this._compileNode(child, ctx);
                }
            }
        }
    }
    QWeb.utils = UTILS;
    QWeb.components = Object.create(null);
    QWeb.DIRECTIVE_NAMES = {
        name: 1,
        att: 1,
        attf: 1,
        translation: 1,
    };
    QWeb.DIRECTIVES = [];
    QWeb.TEMPLATES = {};
    QWeb.nextId = 1;
    // dev mode enables better error messages or more costly validations
    QWeb.dev = false;
    QWeb.enableTransitions = true;
    // slots contains sub templates defined with t-set inside t-component nodes, and
    // are meant to be used by the t-slot directive.
    QWeb.slots = {};
    QWeb.nextSlotId = 1;
    QWeb.subTemplates = {};

    const parser = new DOMParser();
    function htmlToVDOM(html) {
        const doc = parser.parseFromString(html, "text/html");
        const result = [];
        for (let child of doc.body.childNodes) {
            result.push(htmlToVNode(child));
        }
        return result;
    }
    function htmlToVNode(node) {
        if (!(node instanceof Element)) {
            if (node instanceof Comment) {
                return h("!", node.textContent);
            }
            return { text: node.textContent };
        }
        const attrs = {};
        for (let attr of node.attributes) {
            attrs[attr.name] = attr.textContent;
        }
        const children = [];
        for (let c of node.childNodes) {
            children.push(htmlToVNode(c));
        }
        const vnode = h(node.tagName, { attrs }, children);
        if (vnode.sel === "svg") {
            addNS(vnode.data, vnode.children, vnode.sel);
        }
        return vnode;
    }

    /**
     * Owl QWeb Directives
     *
     * This file contains the implementation of most standard QWeb directives:
     * - t-esc
     * - t-raw
     * - t-set/t-value
     * - t-if/t-elif/t-else
     * - t-call
     * - t-foreach/t-as
     * - t-debug
     * - t-log
     */
    //------------------------------------------------------------------------------
    // t-esc and t-raw
    //------------------------------------------------------------------------------
    QWeb.utils.htmlToVDOM = htmlToVDOM;
    function compileValueNode(value, node, qweb, ctx) {
        ctx.rootContext.shouldDefineScope = true;
        if (value === "0") {
            if (ctx.parentNode) {
                // the 'zero' magical symbol is where we can find the result of the rendering
                // of  the body of the t-call.
                ctx.rootContext.shouldDefineUtils = true;
                const zeroArgs = ctx.escaping
                    ? `{text: utils.vDomToString(scope[utils.zero])}`
                    : `...scope[utils.zero]`;
                ctx.addLine(`c${ctx.parentNode}.push(${zeroArgs});`);
            }
            return;
        }
        let exprID;
        if (typeof value === "string") {
            exprID = `_${ctx.generateID()}`;
            ctx.addLine(`let ${exprID} = ${ctx.formatExpression(value)};`);
        }
        else {
            exprID = `scope.${value.id}`;
        }
        ctx.addIf(`${exprID} != null`);
        if (ctx.escaping) {
            let protectID;
            if (value.hasBody) {
                ctx.rootContext.shouldDefineUtils = true;
                protectID = ctx.startProtectScope();
                ctx.addLine(`${exprID} = ${exprID} instanceof utils.VDomArray ? utils.vDomToString(${exprID}) : ${exprID};`);
            }
            if (ctx.parentTextNode) {
                ctx.addLine(`vn${ctx.parentTextNode}.text += ${exprID};`);
            }
            else if (ctx.parentNode) {
                ctx.addLine(`c${ctx.parentNode}.push({text: ${exprID}});`);
            }
            else {
                let nodeID = ctx.generateID();
                ctx.rootContext.rootNode = nodeID;
                ctx.rootContext.parentTextNode = nodeID;
                ctx.addLine(`let vn${nodeID} = {text: ${exprID}};`);
                if (ctx.rootContext.shouldDefineResult) {
                    ctx.addLine(`result = vn${nodeID}`);
                }
            }
            if (value.hasBody) {
                ctx.stopProtectScope(protectID);
            }
        }
        else {
            ctx.rootContext.shouldDefineUtils = true;
            if (value.hasBody) {
                ctx.addLine(`const vnodeArray = ${exprID} instanceof utils.VDomArray ? ${exprID} : utils.htmlToVDOM(${exprID});`);
                ctx.addLine(`c${ctx.parentNode}.push(...vnodeArray);`);
            }
            else {
                ctx.addLine(`c${ctx.parentNode}.push(...utils.htmlToVDOM(${exprID}));`);
            }
        }
        if (node.childNodes.length) {
            ctx.addElse();
            qweb._compileChildren(node, ctx);
        }
        ctx.closeIf();
    }
    QWeb.addDirective({
        name: "esc",
        priority: 70,
        atNodeEncounter({ node, qweb, ctx }) {
            let value = ctx.getValue(node.getAttribute("t-esc"));
            compileValueNode(value, node, qweb, ctx.subContext("escaping", true));
            return true;
        },
    });
    QWeb.addDirective({
        name: "raw",
        priority: 80,
        atNodeEncounter({ node, qweb, ctx }) {
            let value = ctx.getValue(node.getAttribute("t-raw"));
            compileValueNode(value, node, qweb, ctx);
            return true;
        },
    });
    //------------------------------------------------------------------------------
    // t-set
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "set",
        extraNames: ["value"],
        priority: 60,
        atNodeEncounter({ node, qweb, ctx }) {
            ctx.rootContext.shouldDefineScope = true;
            const variable = node.getAttribute("t-set");
            let value = node.getAttribute("t-value");
            ctx.variables[variable] = ctx.variables[variable] || {};
            let qwebvar = ctx.variables[variable];
            const hasBody = node.hasChildNodes();
            qwebvar.id = variable;
            qwebvar.expr = `scope.${variable}`;
            if (value) {
                const formattedValue = ctx.formatExpression(value);
                let scopeExpr = `scope`;
                if (ctx.protectedScopeNumber) {
                    ctx.rootContext.shouldDefineUtils = true;
                    scopeExpr = `utils.getScope(scope, '${variable}')`;
                }
                ctx.addLine(`${scopeExpr}.${variable} = ${formattedValue};`);
                qwebvar.value = formattedValue;
            }
            if (hasBody) {
                ctx.rootContext.shouldDefineUtils = true;
                if (value) {
                    ctx.addIf(`!(${qwebvar.expr})`);
                }
                const tempParentNodeID = ctx.generateID();
                const _parentNode = ctx.parentNode;
                ctx.parentNode = tempParentNodeID;
                ctx.addLine(`let c${tempParentNodeID} = new utils.VDomArray();`);
                const nodeCopy = node.cloneNode(true);
                for (let attr of ["t-set", "t-value", "t-if", "t-else", "t-elif"]) {
                    nodeCopy.removeAttribute(attr);
                }
                qweb._compileNode(nodeCopy, ctx);
                ctx.addLine(`${qwebvar.expr} = c${tempParentNodeID}`);
                qwebvar.value = `c${tempParentNodeID}`;
                qwebvar.hasBody = true;
                ctx.parentNode = _parentNode;
                if (value) {
                    ctx.closeIf();
                }
            }
            return true;
        },
    });
    //------------------------------------------------------------------------------
    // t-if, t-elif, t-else
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "if",
        priority: 20,
        atNodeEncounter({ node, ctx }) {
            let cond = ctx.getValue(node.getAttribute("t-if"));
            ctx.addIf(typeof cond === "string" ? ctx.formatExpression(cond) : `scope.${cond.id}`);
            return false;
        },
        finalize({ ctx }) {
            ctx.closeIf();
        },
    });
    QWeb.addDirective({
        name: "elif",
        priority: 30,
        atNodeEncounter({ node, ctx }) {
            let cond = ctx.getValue(node.getAttribute("t-elif"));
            ctx.addLine(`else if (${typeof cond === "string" ? ctx.formatExpression(cond) : `scope.${cond.id}`}) {`);
            ctx.indent();
            return false;
        },
        finalize({ ctx }) {
            ctx.closeIf();
        },
    });
    QWeb.addDirective({
        name: "else",
        priority: 40,
        atNodeEncounter({ ctx }) {
            ctx.addLine(`else {`);
            ctx.indent();
            return false;
        },
        finalize({ ctx }) {
            ctx.closeIf();
        },
    });
    //------------------------------------------------------------------------------
    // t-call
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "call",
        priority: 50,
        atNodeEncounter({ node, qweb, ctx }) {
            // Step 1: sanity checks
            // ------------------------------------------------
            ctx.rootContext.shouldDefineScope = true;
            ctx.rootContext.shouldDefineUtils = true;
            const subTemplate = node.getAttribute("t-call");
            const isDynamic = INTERP_REGEXP.test(subTemplate);
            const nodeTemplate = qweb.templates[subTemplate];
            if (!isDynamic && !nodeTemplate) {
                throw new Error(`Cannot find template "${subTemplate}" (t-call)`);
            }
            // Step 2: compile target template in sub templates
            // ------------------------------------------------
            let subIdstr;
            if (isDynamic) {
                const _id = ctx.generateID();
                ctx.addLine(`let tname${_id} = ${ctx.interpolate(subTemplate)};`);
                ctx.addLine(`let tid${_id} = this.subTemplates[tname${_id}];`);
                ctx.addIf(`!tid${_id}`);
                ctx.addLine(`tid${_id} = this.constructor.nextId++;`);
                ctx.addLine(`this.subTemplates[tname${_id}] = tid${_id};`);
                ctx.addLine(`this.constructor.subTemplates[tid${_id}] = this._compile(tname${_id}, {hasParent: true, defineKey: true});`);
                ctx.closeIf();
                subIdstr = `tid${_id}`;
            }
            else {
                let subId = qweb.subTemplates[subTemplate];
                if (!subId) {
                    subId = QWeb.nextId++;
                    qweb.subTemplates[subTemplate] = subId;
                    const subTemplateFn = qweb._compile(subTemplate, { hasParent: true, defineKey: true });
                    QWeb.subTemplates[subId] = subTemplateFn;
                }
                subIdstr = `'${subId}'`;
            }
            // Step 3: compile t-call body if necessary
            // ------------------------------------------------
            let hasBody = node.hasChildNodes();
            const protectID = ctx.startProtectScope();
            if (hasBody) {
                // we add a sub scope to protect the ambient scope
                ctx.addLine(`{`);
                ctx.indent();
                const nodeCopy = node.cloneNode(true);
                for (let attr of ["t-if", "t-else", "t-elif", "t-call"]) {
                    nodeCopy.removeAttribute(attr);
                }
                // this local scope is intended to trap c__0
                ctx.addLine(`{`);
                ctx.indent();
                ctx.addLine("let c__0 = [];");
                qweb._compileNode(nodeCopy, ctx.subContext("parentNode", "__0"));
                ctx.rootContext.shouldDefineUtils = true;
                ctx.addLine("scope[utils.zero] = c__0;");
                ctx.dedent();
                ctx.addLine(`}`);
            }
            // Step 4: add the appropriate function call to current component
            // ------------------------------------------------
            const parentComponent = `utils.getComponent(context)`;
            const key = ctx.generateTemplateKey();
            const parentNode = ctx.parentNode ? `c${ctx.parentNode}` : "result";
            const extra = `Object.assign({}, extra, {parentNode: ${parentNode}, parent: ${parentComponent}, key: ${key}})`;
            if (ctx.parentNode) {
                ctx.addLine(`this.constructor.subTemplates[${subIdstr}].call(this, scope, ${extra});`);
            }
            else {
                // this is a t-call with no parentnode, we need to extract the result
                ctx.rootContext.shouldDefineResult = true;
                ctx.addLine(`result = []`);
                ctx.addLine(`this.constructor.subTemplates[${subIdstr}].call(this, scope, ${extra});`);
                ctx.addLine(`result = result[0]`);
            }
            // Step 5: restore previous scope
            // ------------------------------------------------
            if (hasBody) {
                ctx.dedent();
                ctx.addLine(`}`);
            }
            ctx.stopProtectScope(protectID);
            return true;
        },
    });
    //------------------------------------------------------------------------------
    // t-foreach
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "foreach",
        extraNames: ["as"],
        priority: 10,
        atNodeEncounter({ node, qweb, ctx }) {
            ctx.rootContext.shouldDefineScope = true;
            ctx = ctx.subContext("loopNumber", ctx.loopNumber + 1);
            const elems = node.getAttribute("t-foreach");
            const name = node.getAttribute("t-as");
            let arrayID = ctx.generateID();
            ctx.addLine(`let _${arrayID} = ${ctx.formatExpression(elems)};`);
            ctx.addLine(`if (!_${arrayID}) { throw new Error('QWeb error: Invalid loop expression')}`);
            let keysID = ctx.generateID();
            let valuesID = ctx.generateID();
            ctx.addLine(`let _${keysID} = _${valuesID} = _${arrayID};`);
            ctx.addIf(`!(_${arrayID} instanceof Array)`);
            ctx.addLine(`_${keysID} = Object.keys(_${arrayID});`);
            ctx.addLine(`_${valuesID} = Object.values(_${arrayID});`);
            ctx.closeIf();
            ctx.addLine(`let _length${keysID} = _${keysID}.length;`);
            let varsID = ctx.startProtectScope(true);
            const loopVar = `i${ctx.loopNumber}`;
            ctx.addLine(`for (let ${loopVar} = 0; ${loopVar} < _length${keysID}; ${loopVar}++) {`);
            ctx.indent();
            ctx.addLine(`scope.${name}_first = ${loopVar} === 0`);
            ctx.addLine(`scope.${name}_last = ${loopVar} === _length${keysID} - 1`);
            ctx.addLine(`scope.${name}_index = ${loopVar}`);
            ctx.addLine(`scope.${name} = _${keysID}[${loopVar}]`);
            ctx.addLine(`scope.${name}_value = _${valuesID}[${loopVar}]`);
            const nodeCopy = node.cloneNode(true);
            let shouldWarn = !nodeCopy.hasAttribute("t-key") &&
                node.children.length === 1 &&
                node.children[0].tagName !== "t" &&
                !node.children[0].hasAttribute("t-key");
            if (shouldWarn) {
                console.warn(`Directive t-foreach should always be used with a t-key! (in template: '${ctx.templateName}')`);
            }
            if (nodeCopy.hasAttribute("t-key")) {
                const expr = ctx.formatExpression(nodeCopy.getAttribute("t-key"));
                ctx.addLine(`let key${ctx.loopNumber} = ${expr};`);
                nodeCopy.removeAttribute("t-key");
            }
            else {
                ctx.addLine(`let key${ctx.loopNumber} = i${ctx.loopNumber};`);
            }
            nodeCopy.removeAttribute("t-foreach");
            qweb._compileNode(nodeCopy, ctx);
            ctx.dedent();
            ctx.addLine("}");
            ctx.stopProtectScope(varsID);
            return true;
        },
    });
    //------------------------------------------------------------------------------
    // t-debug
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "debug",
        priority: 1,
        atNodeEncounter({ ctx }) {
            ctx.addLine("debugger;");
        },
    });
    //------------------------------------------------------------------------------
    // t-log
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "log",
        priority: 1,
        atNodeEncounter({ ctx, value }) {
            const expr = ctx.formatExpression(value);
            ctx.addLine(`console.log(${expr})`);
        },
    });

    /**
     * Owl QWeb Extensions
     *
     * This file contains the implementation of non standard QWeb directives, added
     * by Owl and that will only work on Owl projects:
     *
     * - t-on
     * - t-ref
     * - t-transition
     * - t-mounted
     * - t-slot
     * - t-model
     */
    //------------------------------------------------------------------------------
    // t-on
    //------------------------------------------------------------------------------
    // these are pieces of code that will be injected into the event handler if
    // modifiers are specified
    const MODS_CODE = {
        prevent: "e.preventDefault();",
        self: "if (e.target !== this.elm) {return}",
        stop: "e.stopPropagation();",
    };
    const FNAMEREGEXP = /^[$A-Z_][0-9A-Z_$]*$/i;
    function makeHandlerCode(ctx, fullName, value, putInCache, modcodes = MODS_CODE) {
        let [event, ...mods] = fullName.slice(5).split(".");
        if (mods.includes("capture")) {
            event = "!" + event;
        }
        if (!event) {
            throw new Error("Missing event name with t-on directive");
        }
        let code;
        // check if it is a method with no args, a method with args or an expression
        let args = "";
        const name = value.replace(/\(.*\)/, function (_args) {
            args = _args.slice(1, -1);
            return "";
        });
        const isMethodCall = name.match(FNAMEREGEXP);
        // then generate code
        if (isMethodCall) {
            ctx.rootContext.shouldDefineUtils = true;
            const comp = `utils.getComponent(context)`;
            if (args) {
                const argId = ctx.generateID();
                ctx.addLine(`let args${argId} = [${ctx.formatExpression(args)}];`);
                code = `${comp}['${name}'](...args${argId}, e);`;
                putInCache = false;
            }
            else {
                code = `${comp}['${name}'](e);`;
            }
        }
        else {
            // if we get here, then it is an expression
            // we need to capture every variable in it
            putInCache = false;
            code = ctx.captureExpression(value);
        }
        const modCode = mods.map((mod) => modcodes[mod]).join("");
        let handler = `function (e) {if (context.__owl__.status === ${5 /* DESTROYED */}){return}${modCode}${code}}`;
        if (putInCache) {
            const key = ctx.generateTemplateKey(event);
            ctx.addLine(`extra.handlers[${key}] = extra.handlers[${key}] || ${handler};`);
            handler = `extra.handlers[${key}]`;
        }
        return { event, handler };
    }
    QWeb.addDirective({
        name: "on",
        priority: 90,
        atNodeCreation({ ctx, fullName, value, nodeID }) {
            const { event, handler } = makeHandlerCode(ctx, fullName, value, true);
            ctx.addLine(`p${nodeID}.on['${event}'] = ${handler};`);
        },
    });
    //------------------------------------------------------------------------------
    // t-ref
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "ref",
        priority: 95,
        atNodeCreation({ ctx, value, addNodeHook }) {
            ctx.rootContext.shouldDefineRefs = true;
            const refKey = `ref${ctx.generateID()}`;
            ctx.addLine(`const ${refKey} = ${ctx.interpolate(value)};`);
            addNodeHook("create", `context.__owl__.refs[${refKey}] = n.elm;`);
            addNodeHook("destroy", `delete context.__owl__.refs[${refKey}];`);
        },
    });
    //------------------------------------------------------------------------------
    // t-transition
    //------------------------------------------------------------------------------
    QWeb.utils.nextFrame = function (cb) {
        requestAnimationFrame(() => requestAnimationFrame(cb));
    };
    QWeb.utils.transitionInsert = function (vn, name) {
        const elm = vn.elm;
        // remove potential duplicated vnode that is currently being removed, to
        // prevent from having twice the same node in the DOM during an animation
        const dup = elm.parentElement && elm.parentElement.querySelector(`*[data-owl-key='${vn.key}']`);
        if (dup) {
            dup.remove();
        }
        elm.classList.add(name + "-enter");
        elm.classList.add(name + "-enter-active");
        elm.classList.remove(name + "-leave-active");
        elm.classList.remove(name + "-leave-to");
        const finalize = () => {
            elm.classList.remove(name + "-enter-active");
            elm.classList.remove(name + "-enter-to");
        };
        this.nextFrame(() => {
            elm.classList.remove(name + "-enter");
            elm.classList.add(name + "-enter-to");
            whenTransitionEnd(elm, finalize);
        });
    };
    QWeb.utils.transitionRemove = function (vn, name, rm) {
        const elm = vn.elm;
        elm.setAttribute("data-owl-key", vn.key);
        elm.classList.add(name + "-leave");
        elm.classList.add(name + "-leave-active");
        const finalize = () => {
            if (!elm.classList.contains(name + "-leave-active")) {
                return;
            }
            elm.classList.remove(name + "-leave-active");
            elm.classList.remove(name + "-leave-to");
            rm();
        };
        this.nextFrame(() => {
            elm.classList.remove(name + "-leave");
            elm.classList.add(name + "-leave-to");
            whenTransitionEnd(elm, finalize);
        });
    };
    function getTimeout(delays, durations) {
        /* istanbul ignore next */
        while (delays.length < durations.length) {
            delays = delays.concat(delays);
        }
        return Math.max.apply(null, durations.map((d, i) => {
            return toMs(d) + toMs(delays[i]);
        }));
    }
    // Old versions of Chromium (below 61.0.3163.100) formats floating pointer numbers
    // in a locale-dependent way, using a comma instead of a dot.
    // If comma is not replaced with a dot, the input will be rounded down (i.e. acting
    // as a floor function) causing unexpected behaviors
    function toMs(s) {
        return Number(s.slice(0, -1).replace(",", ".")) * 1000;
    }
    function whenTransitionEnd(elm, cb) {
        if (!elm.parentNode) {
            // if we get here, this means that the element was removed for some other
            // reasons, and in that case, we don't want to work on animation since nothing
            // will be displayed anyway.
            return;
        }
        const styles = window.getComputedStyle(elm);
        const delays = (styles.transitionDelay || "").split(", ");
        const durations = (styles.transitionDuration || "").split(", ");
        const timeout = getTimeout(delays, durations);
        if (timeout > 0) {
            elm.addEventListener("transitionend", cb, { once: true });
        }
        else {
            cb();
        }
    }
    QWeb.addDirective({
        name: "transition",
        priority: 96,
        atNodeCreation({ ctx, value, addNodeHook }) {
            if (!QWeb.enableTransitions) {
                return;
            }
            ctx.rootContext.shouldDefineUtils = true;
            let name = value;
            const hooks = {
                insert: `utils.transitionInsert(vn, '${name}');`,
                remove: `utils.transitionRemove(vn, '${name}', rm);`,
            };
            for (let hookName in hooks) {
                addNodeHook(hookName, hooks[hookName]);
            }
        },
    });
    //------------------------------------------------------------------------------
    // t-slot
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "slot",
        priority: 80,
        atNodeEncounter({ ctx, value, node, qweb }) {
            const slotKey = ctx.generateID();
            const valueExpr = value.match(INTERP_REGEXP) ? ctx.interpolate(value) : `'${value}'`;
            ctx.addLine(`const slot${slotKey} = this.constructor.slots[context.__owl__.slotId + '_' + ${valueExpr}];`);
            ctx.addIf(`slot${slotKey}`);
            let parentNode = `c${ctx.parentNode}`;
            if (!ctx.parentNode) {
                ctx.rootContext.shouldDefineResult = true;
                ctx.rootContext.shouldDefineUtils = true;
                parentNode = `children${ctx.generateID()}`;
                ctx.addLine(`let ${parentNode}= []`);
                ctx.addLine(`result = {}`);
            }
            ctx.addLine(`slot${slotKey}.call(this, context.__owl__.scope, Object.assign({}, extra, {parentNode: ${parentNode}, parent: extra.parent || context}));`);
            if (!ctx.parentNode) {
                ctx.addLine(`utils.defineProxy(result, ${parentNode}[0]);`);
            }
            if (node.hasChildNodes()) {
                ctx.addElse();
                const nodeCopy = node.cloneNode(true);
                nodeCopy.removeAttribute("t-slot");
                qweb._compileNode(nodeCopy, ctx);
            }
            ctx.closeIf();
            return true;
        },
    });
    //------------------------------------------------------------------------------
    // t-model
    //------------------------------------------------------------------------------
    QWeb.utils.toNumber = function (val) {
        const n = parseFloat(val);
        return isNaN(n) ? val : n;
    };
    const hasDotAtTheEnd = /\.[\w_]+\s*$/;
    const hasBracketsAtTheEnd = /\[[^\[]+\]\s*$/;
    QWeb.addDirective({
        name: "model",
        priority: 42,
        atNodeCreation({ ctx, nodeID, value, node, fullName, addNodeHook }) {
            const type = node.getAttribute("type");
            let handler;
            let event = fullName.includes(".lazy") ? "change" : "input";
            // First step: we need to understand the structure of the expression, and
            // from it, extract a base expression (that we can capture, which is
            // important because it will be used in a handler later) and a formatted
            // expression (which uses the captured base expression)
            //
            // Also, we support 2 kinds of values: some.expr.value or some.expr[value]
            // For the first one, we have:
            // - base expression = scope[some].expr
            // - expression = exprX.value (where exprX is the var that captures the base expr)
            // and for the expression with brackets:
            // - base expression = scope[some].expr
            // - expression = exprX[keyX] (where exprX is the var that captures the base expr
            //        and keyX captures scope[value])
            let expr;
            let baseExpr;
            if (hasDotAtTheEnd.test(value)) {
                // we manage the case where the expr has a dot: some.expr.value
                const index = value.lastIndexOf(".");
                baseExpr = value.slice(0, index);
                ctx.addLine(`let expr${nodeID} = ${ctx.formatExpression(baseExpr)};`);
                expr = `expr${nodeID}${value.slice(index)}`;
            }
            else if (hasBracketsAtTheEnd.test(value)) {
                // we manage here the case where the expr ends in a bracket expression:
                //    some.expr[value]
                const index = value.lastIndexOf("[");
                baseExpr = value.slice(0, index);
                ctx.addLine(`let expr${nodeID} = ${ctx.formatExpression(baseExpr)};`);
                let exprKey = value.trimRight().slice(index + 1, -1);
                ctx.addLine(`let exprKey${nodeID} = ${ctx.formatExpression(exprKey)};`);
                expr = `expr${nodeID}[exprKey${nodeID}]`;
            }
            else {
                throw new Error(`Invalid t-model expression: "${value}" (it should be assignable)`);
            }
            const key = ctx.generateTemplateKey();
            if (node.tagName === "select") {
                ctx.addLine(`p${nodeID}.props = {value: ${expr}};`);
                addNodeHook("create", `n.elm.value=${expr};`);
                event = "change";
                handler = `(ev) => {${expr} = ev.target.value}`;
            }
            else if (type === "checkbox") {
                ctx.addLine(`p${nodeID}.props = {checked: ${expr}};`);
                handler = `(ev) => {${expr} = ev.target.checked}`;
            }
            else if (type === "radio") {
                const nodeValue = node.getAttribute("value");
                ctx.addLine(`p${nodeID}.props = {checked:${expr} === '${nodeValue}'};`);
                handler = `(ev) => {${expr} = ev.target.value}`;
                event = "click";
            }
            else {
                ctx.addLine(`p${nodeID}.props = {value: ${expr}};`);
                const trimCode = fullName.includes(".trim") ? ".trim()" : "";
                let valueCode = `ev.target.value${trimCode}`;
                if (fullName.includes(".number")) {
                    ctx.rootContext.shouldDefineUtils = true;
                    valueCode = `utils.toNumber(${valueCode})`;
                }
                handler = `(ev) => {${expr} = ${valueCode}}`;
            }
            ctx.addLine(`extra.handlers[${key}] = extra.handlers[${key}] || (${handler});`);
            ctx.addLine(`p${nodeID}.on['${event}'] = extra.handlers[${key}];`);
        },
    });
    //------------------------------------------------------------------------------
    // t-key
    //------------------------------------------------------------------------------
    QWeb.addDirective({
        name: "key",
        priority: 45,
        atNodeEncounter({ ctx, value, node }) {
            if (ctx.loopNumber === 0) {
                ctx.keyStack.push(ctx.rootContext.hasKey0);
                ctx.rootContext.hasKey0 = true;
            }
            ctx.addLine("{");
            ctx.indent();
            ctx.addLine(`let key${ctx.loopNumber} = ${ctx.formatExpression(value)};`);
        },
        finalize({ ctx }) {
            ctx.dedent();
            ctx.addLine("}");
            if (ctx.loopNumber === 0) {
                ctx.rootContext.hasKey0 = ctx.keyStack.pop();
            }
        },
    });

    const config = {};
    Object.defineProperty(config, "mode", {
        get() {
            return QWeb.dev ? "dev" : "prod";
        },
        set(mode) {
            QWeb.dev = mode === "dev";
            if (QWeb.dev) {
                const url = `https://github.com/odoo/owl/blob/master/doc/reference/config.md#mode`;
                console.warn(`Owl is running in 'dev' mode.  This is not suitable for production use. See ${url} for more information.`);
            }
            else {
                console.log(`Owl is now running in 'prod' mode.`);
            }
        },
    });
    Object.defineProperty(config, "enableTransitions", {
        get() {
            return QWeb.enableTransitions;
        },
        set(value) {
            QWeb.enableTransitions = value;
        },
    });

    /**
     * We define here OwlEvent, a subclass of CustomEvent, with an additional
     * attribute:
     *  - originalComponent: the component that triggered the event
     */
    class OwlEvent extends CustomEvent {
        constructor(component, eventType, options) {
            super(eventType, options);
            this.originalComponent = component;
        }
    }

    //------------------------------------------------------------------------------
    // t-component
    //------------------------------------------------------------------------------
    const T_COMPONENT_MODS_CODE = Object.assign({}, MODS_CODE, {
        self: "if (e.target !== vn.elm) {return}",
    });
    QWeb.utils.defineProxy = function defineProxy(target, source) {
        for (let k in source) {
            Object.defineProperty(target, k, {
                get() {
                    return source[k];
                },
                set(val) {
                    source[k] = val;
                },
            });
        }
    };
    QWeb.utils.assignHooks = function assignHooks(dataObj, hooks) {
        if ("hook" in dataObj) {
            const hookObject = dataObj.hook;
            for (let name in hooks) {
                const current = hookObject[name];
                const fn = hooks[name];
                if (current) {
                    hookObject[name] = (...args) => {
                        current(...args);
                        fn(...args);
                    };
                }
                else {
                    hookObject[name] = fn;
                }
            }
        }
        else {
            dataObj.hook = hooks;
        }
    };
    /**
     * The t-component directive is certainly a complicated and hard to maintain piece
     * of code.  To help you, fellow developer, if you have to maintain it, I offer
     * you this advice: Good luck...
     *
     * Since it is not 'direct' code, but rather code that generates other code, it
     * is not easy to understand.  To help you, here  is a detailed and commented
     * explanation of the code generated by the t-component directive for the following
     * situation:
     * ```xml
     *   <Child
     *      t-key="'somestring'"
     *      flag="state.flag"
     *      t-transition="fade"/>
     * ```
     *
     * ```js
     * // we assign utils on top of the function because it will be useful for
     * // each components
     * let utils = this.utils;
     *
     * // this is the virtual node representing the parent div
     * let c1 = [], p1 = { key: 1 };
     * var vn1 = h("div", p1, c1);
     *
     * // t-component directive: we start by evaluating the expression given by t-key:
     * let key5 = "somestring";
     *
     * // def3 is the promise that will contain later either the new component
     * // creation, or the props update...
     * let def3;
     *
     * // this is kind of tricky: we need here to find if the component was already
     * // created by a previous rendering.  This is done by checking the internal
     * // `cmap` (children map) of the parent component: it maps keys to component ids,
     * // and, then, if there is an id, we look into the children list to get the
     * // instance
     * let w4 =
     *   key5 in context.__owl__.cmap
     *   ? context.__owl__.children[context.__owl__.cmap[key5]]
     *   : false;
     *
     * // We keep the index of the position of the component in the closure.  We push
     * // null to reserve the slot, and will replace it later by the component vnode,
     * // when it will be ready (do not forget that preparing/rendering a component is
     * // asynchronous)
     * let _2_index = c1.length;
     * c1.push(null);
     *
     * // we evaluate here the props given to the component. It is done here to be
     * // able to easily reference it later, and also, it might be an expensive
     * // computation, so it is certainly better to do it only once
     * let props4 = { flag: context["state"].flag };
     *
     * // If we have a component, currently rendering, but not ready yet, we do not want
     * // to wait for it to be ready if we can avoid it
     * if (w4 && w4.__owl__.renderPromise && !w4.__owl__.vnode) {
     *   // we check if the props are the same.  In that case, we can simply reuse
     *   // the previous rendering and skip all useless work
     *   if (utils.shallowEqual(props4, w4.__owl__.renderProps)) {
     *     def3 = w4.__owl__.renderPromise;
     *   } else {
     *     // if the props are not the same, we destroy the component and starts anew.
     *     // this will be faster than waiting for its rendering, then updating it
     *     w4.destroy();
     *     w4 = false;
     *   }
     * }
     *
     * if (!w4) {
     *   // in this situation, we need to create a new component.  First step is
     *   // to get a reference to the class, then create an instance with
     *   // current context as parent, and the props.
     *   let W4 = context.component && context.components[componentKey4] || QWeb.component[componentKey4];

     *   if (!W4) {
     *     throw new Error("Cannot find the definition of component 'child'");
     *   }
     *   w4 = new W4(owner, props4);
     *
     *   // Whenever we rerender the parent component, we need to be sure that we
     *   // are able to find the component instance. To do that, we register it to
     *   // the parent cmap (children map).  Note that the 'template' key is
     *   // used here, since this is what identify the component from the template
     *   // perspective.
     *   context.__owl__.cmap[key5] = w4.__owl__.id;
     *
     *   // __prepare is called, to basically call willStart, then render the
     *   // component
     *   def3 = w4.__prepare();
     *
     *   def3 = def3.then(vnode => {
     *     // we create here a virtual node for the parent (NOT the component). This
     *     // means that the vdom of the parent will be stopped here, and from
     *     // the parent's perspective, it simply is a vnode with no children.
     *     // However, it shares the same dom element with the component root
     *     // vnode.
     *     let pvnode = h(vnode.sel, { key: key5 });
     *
     *     // we add hooks to the parent vnode so we can interact with the new
     *     // component at the proper time
     *     pvnode.data.hook = {
     *       insert(vn) {
     *         // the __mount method will patch the component vdom into the elm vn.elm,
     *         // then call the mounted hooks. However, suprisingly, the snabbdom
     *         // patch method actually replace the elm by a new elm, so we need
     *         // to synchronise the pvnode elm with the resulting elm
     *         let nvn = w4.__mount(vnode, vn.elm);
     *         pvnode.elm = nvn.elm;
     *         // what follows is only present if there are animations on the component
     *         utils.transitionInsert(vn, "fade");
     *       },
     *       remove() {
     *         // override with empty function to prevent from removing the node
     *         // directly. It will be removed when destroy is called anyway, which
     *         // delays the removal if there are animations.
     *       },
     *       destroy() {
     *         // if there are animations, we delay the call to destroy on the
     *         // component, if not, we call it directly.
     *         let finalize = () => {
     *           w4.destroy();
     *         };
     *         utils.transitionRemove(vn, "fade", finalize);
     *       }
     *     };
     *     // the pvnode is inserted at the correct position in the div's children
     *     c1[_2_index] = pvnode;
     *
     *     // we keep here a reference to the parent vnode (representing the
     *     // component, so we can reuse it later whenever we update the component
     *     w4.__owl__.pvnode = pvnode;
     *   });
     * } else {
     *   // this is the 'update' path of the directive.
     *   // the call to __updateProps is the actual component update
     *   // Note that we only update the props if we cannot reuse the previous
     *   // rendering work (in the case it was rendered with the same props)
     *   def3 = def3 || w4.__updateProps(props4, extra.forceUpdate, extra.patchQueue);
     *   def3 = def3.then(() => {
     *     // if component was destroyed in the meantime, we do nothing (so, this
     *     // means that the parent's element children list will have a null in
     *     // the component's position, which will cause the pvnode to be removed
     *     // when it is patched.
     *     if (w4.__owl__.isDestroyed) {
     *       return;
     *     }
     *     // like above, we register the pvnode to the children list, so it
     *     // will not be patched out of the dom.
     *     let pvnode = w4.__owl__.pvnode;
     *     c1[_2_index] = pvnode;
     *   });
     * }
     *
     * // we register the deferred here so the parent can coordinate its patch operation
     * // with all the children.
     * extra.promises.push(def3);
     * return vn1;
     * ```
     */
    QWeb.addDirective({
        name: "component",
        extraNames: ["props"],
        priority: 100,
        atNodeEncounter({ ctx, value, node, qweb }) {
            ctx.addLine(`// Component '${value}'`);
            ctx.rootContext.shouldDefineQWeb = true;
            ctx.rootContext.shouldDefineParent = true;
            ctx.rootContext.shouldDefineUtils = true;
            ctx.rootContext.shouldDefineScope = true;
            let hasDynamicProps = node.getAttribute("t-props") ? true : false;
            // t-on- events and t-transition
            const events = [];
            let transition = "";
            const attributes = node.attributes;
            const props = {};
            for (let i = 0; i < attributes.length; i++) {
                const name = attributes[i].name;
                const value = attributes[i].textContent;
                if (name.startsWith("t-on-")) {
                    events.push([name, value]);
                }
                else if (name === "t-transition") {
                    if (QWeb.enableTransitions) {
                        transition = value;
                    }
                }
                else if (!name.startsWith("t-")) {
                    if (name !== "class" && name !== "style") {
                        // this is a prop!
                        props[name] = ctx.formatExpression(value) || "undefined";
                    }
                }
            }
            // computing the props string representing the props object
            let propStr = Object.keys(props)
                .map((k) => k + ":" + props[k])
                .join(",");
            let componentID = ctx.generateID();
            const templateKey = ctx.generateTemplateKey();
            let ref = node.getAttribute("t-ref");
            let refExpr = "";
            let refKey = "";
            if (ref) {
                ctx.rootContext.shouldDefineRefs = true;
                refKey = `ref${ctx.generateID()}`;
                ctx.addLine(`const ${refKey} = ${ctx.interpolate(ref)};`);
                refExpr = `context.__owl__.refs[${refKey}] = w${componentID};`;
            }
            let finalizeComponentCode = `w${componentID}.destroy();`;
            if (ref) {
                finalizeComponentCode += `delete context.__owl__.refs[${refKey}];`;
            }
            if (transition) {
                finalizeComponentCode = `let finalize = () => {
          ${finalizeComponentCode}
        };
        delete w${componentID}.__owl__.transitionInserted;
        utils.transitionRemove(vn, '${transition}', finalize);`;
            }
            let createHook = "";
            let classAttr = node.getAttribute("class");
            let tattClass = node.getAttribute("t-att-class");
            let styleAttr = node.getAttribute("style");
            let tattStyle = node.getAttribute("t-att-style");
            if (tattStyle) {
                const attVar = `_${ctx.generateID()}`;
                ctx.addLine(`const ${attVar} = ${ctx.formatExpression(tattStyle)};`);
                tattStyle = attVar;
            }
            let classObj = "";
            if (classAttr || tattClass || styleAttr || tattStyle || events.length) {
                if (classAttr) {
                    let classDef = classAttr
                        .trim()
                        .split(/\s+/)
                        .map((a) => `'${a}':true`)
                        .join(",");
                    classObj = `_${ctx.generateID()}`;
                    ctx.addLine(`let ${classObj} = {${classDef}};`);
                }
                if (tattClass) {
                    let tattExpr = ctx.formatExpression(tattClass);
                    if (tattExpr[0] !== "{" || tattExpr[tattExpr.length - 1] !== "}") {
                        tattExpr = `utils.toObj(${tattExpr})`;
                    }
                    if (classAttr) {
                        ctx.addLine(`Object.assign(${classObj}, ${tattExpr})`);
                    }
                    else {
                        classObj = `_${ctx.generateID()}`;
                        ctx.addLine(`let ${classObj} = ${tattExpr};`);
                    }
                }
                let eventsCode = events
                    .map(function ([name, value]) {
                    const capture = name.match(/\.capture/);
                    name = capture ? name.replace(/\.capture/, "") : name;
                    const { event, handler } = makeHandlerCode(ctx, name, value, false, T_COMPONENT_MODS_CODE);
                    if (capture) {
                        return `vn.elm.addEventListener('${event}', ${handler}, true);`;
                    }
                    return `vn.elm.addEventListener('${event}', ${handler});`;
                })
                    .join("");
                const styleExpr = tattStyle || (styleAttr ? `'${styleAttr}'` : false);
                const styleCode = styleExpr ? `vn.elm.style = ${styleExpr};` : "";
                createHook = `utils.assignHooks(vnode.data, {create(_, vn){${styleCode}${eventsCode}}});`;
            }
            ctx.addLine(`let w${componentID} = ${templateKey} in parent.__owl__.cmap ? parent.__owl__.children[parent.__owl__.cmap[${templateKey}]] : false;`);
            let shouldProxy = !ctx.parentNode;
            if (shouldProxy) {
                let id = ctx.generateID();
                ctx.rootContext.rootNode = id;
                shouldProxy = true;
                ctx.rootContext.shouldDefineResult = true;
                ctx.addLine(`let vn${id} = {};`);
                ctx.addLine(`result = vn${id};`);
            }
            if (hasDynamicProps) {
                const dynamicProp = ctx.formatExpression(node.getAttribute("t-props"));
                ctx.addLine(`let props${componentID} = Object.assign({${propStr}}, ${dynamicProp});`);
            }
            else {
                ctx.addLine(`let props${componentID} = {${propStr}};`);
            }
            ctx.addIf(`w${componentID} && w${componentID}.__owl__.currentFiber && !w${componentID}.__owl__.vnode`);
            ctx.addLine(`w${componentID}.destroy();`);
            ctx.addLine(`w${componentID} = false;`);
            ctx.closeIf();
            let registerCode = "";
            if (shouldProxy) {
                registerCode = `utils.defineProxy(vn${ctx.rootNode}, pvnode);`;
            }
            // SLOTS
            const hasSlots = node.childNodes.length;
            let scope = hasSlots ? `Object.assign(Object.create(context), scope)` : "undefined";
            ctx.addIf(`w${componentID}`);
            // need to update component
            let styleCode = "";
            if (tattStyle) {
                styleCode = `.then(()=>{if (w${componentID}.__owl__.status === ${5 /* DESTROYED */}) {return};w${componentID}.el.style=${tattStyle};});`;
            }
            ctx.addLine(`w${componentID}.__updateProps(props${componentID}, extra.fiber, ${scope})${styleCode};`);
            ctx.addLine(`let pvnode = w${componentID}.__owl__.pvnode;`);
            if (registerCode) {
                ctx.addLine(registerCode);
            }
            if (ctx.parentNode) {
                ctx.addLine(`c${ctx.parentNode}.push(pvnode);`);
            }
            ctx.addElse();
            // new component
            const contextualValue = value.match(INTERP_REGEXP) ? "false" : ctx.formatExpression(value);
            const interpValue = ctx.interpolate(value);
            ctx.addLine(`let componentKey${componentID} = ${interpValue};`);
            ctx.addLine(`let W${componentID} = ${contextualValue} || context.constructor.components[componentKey${componentID}] || QWeb.components[componentKey${componentID}];`);
            // maybe only do this in dev mode...
            ctx.addLine(`if (!W${componentID}) {throw new Error('Cannot find the definition of component "' + componentKey${componentID} + '"')}`);
            ctx.addLine(`w${componentID} = new W${componentID}(parent, props${componentID});`);
            if (transition) {
                ctx.addLine(`const __patch${componentID} = w${componentID}.__patch;`);
                ctx.addLine(`w${componentID}.__patch = (t, vn) => {__patch${componentID}.call(w${componentID}, t, vn); if(!w${componentID}.__owl__.transitionInserted){w${componentID}.__owl__.transitionInserted = true;utils.transitionInsert(w${componentID}.__owl__.vnode, '${transition}');}};`);
            }
            ctx.addLine(`parent.__owl__.cmap[${templateKey}] = w${componentID}.__owl__.id;`);
            if (hasSlots) {
                const clone = node.cloneNode(true);
                // The next code is a fallback for compatibility reason. It accepts t-set
                // elements that are direct children with a non empty body as nodes defining
                // the content of a slot.
                //
                // This is wrong, but is necessary to prevent breaking all existing Owl
                // code using slots. This will be removed in v2.0 someday. Meanwhile,
                // please use t-set-slot everywhere you need to set the content of a
                // slot.
                for (let node of clone.children) {
                    if (node.hasAttribute("t-set") && node.hasChildNodes()) {
                        node.setAttribute("t-set-slot", node.getAttribute("t-set"));
                        node.removeAttribute("t-set");
                    }
                }
                const slotNodes = Array.from(clone.querySelectorAll("[t-set-slot]"));
                const slotNames = new Set();
                const slotId = QWeb.nextSlotId++;
                ctx.addLine(`w${componentID}.__owl__.slotId = ${slotId};`);
                if (slotNodes.length) {
                    for (let i = 0, length = slotNodes.length; i < length; i++) {
                        const slotNode = slotNodes[i];
                        // check if this is defined in a sub component (in which case it should
                        // be ignored)
                        let el = slotNode.parentElement;
                        let isInSubComponent = false;
                        while (el !== clone) {
                            if (el.hasAttribute("t-component") ||
                                el.tagName[0] === el.tagName[0].toUpperCase()) {
                                isInSubComponent = true;
                                break;
                            }
                            el = el.parentElement;
                        }
                        if (isInSubComponent) {
                            continue;
                        }
                        let key = slotNode.getAttribute("t-set-slot");
                        if (slotNames.has(key)) {
                            continue;
                        }
                        slotNames.add(key);
                        slotNode.removeAttribute("t-set-slot");
                        slotNode.parentElement.removeChild(slotNode);
                        const slotFn = qweb._compile(`slot_${key}_template`, { elem: slotNode, hasParent: true });
                        QWeb.slots[`${slotId}_${key}`] = slotFn;
                    }
                }
                if (clone.childNodes.length) {
                    const t = clone.ownerDocument.createElement("t");
                    for (let child of Object.values(clone.childNodes)) {
                        t.appendChild(child);
                    }
                    const slotFn = qweb._compile(`slot_default_template`, { elem: t, hasParent: true });
                    QWeb.slots[`${slotId}_default`] = slotFn;
                }
            }
            ctx.addLine(`let fiber = w${componentID}.__prepare(extra.fiber, ${scope}, () => { const vnode = fiber.vnode; pvnode.sel = vnode.sel; ${createHook}});`);
            // hack: specify empty remove hook to prevent the node from being removed from the DOM
            const insertHook = refExpr ? `insert(vn) {${refExpr}},` : "";
            ctx.addLine(`let pvnode = h('dummy', {key: ${templateKey}, hook: {${insertHook}remove() {},destroy(vn) {${finalizeComponentCode}}}});`);
            if (registerCode) {
                ctx.addLine(registerCode);
            }
            if (ctx.parentNode) {
                ctx.addLine(`c${ctx.parentNode}.push(pvnode);`);
            }
            ctx.addLine(`w${componentID}.__owl__.pvnode = pvnode;`);
            ctx.closeIf();
            if (classObj) {
                ctx.addLine(`w${componentID}.__owl__.classObj=${classObj};`);
            }
            ctx.addLine(`w${componentID}.__owl__.parentLastFiberId = extra.fiber.id;`);
            return true;
        },
    });

    class Scheduler {
        constructor(requestAnimationFrame) {
            this.tasks = [];
            this.isRunning = false;
            this.requestAnimationFrame = requestAnimationFrame;
        }
        start() {
            this.isRunning = true;
            this.scheduleTasks();
        }
        stop() {
            this.isRunning = false;
        }
        addFiber(fiber) {
            // if the fiber was remapped into a larger rendering fiber, it may not be a
            // root fiber.  But we only want to register root fibers
            fiber = fiber.root;
            return new Promise((resolve, reject) => {
                if (fiber.error) {
                    return reject(fiber.error);
                }
                this.tasks.push({
                    fiber,
                    callback: () => {
                        if (fiber.error) {
                            return reject(fiber.error);
                        }
                        resolve();
                    },
                });
                if (!this.isRunning) {
                    this.start();
                }
            });
        }
        rejectFiber(fiber, reason) {
            fiber = fiber.root;
            const index = this.tasks.findIndex((t) => t.fiber === fiber);
            if (index >= 0) {
                const [task] = this.tasks.splice(index, 1);
                fiber.cancel();
                fiber.error = new Error(reason);
                task.callback();
            }
        }
        /**
         * Process all current tasks. This only applies to the fibers that are ready.
         * Other tasks are left unchanged.
         */
        flush() {
            let tasks = this.tasks;
            this.tasks = [];
            tasks = tasks.filter((task) => {
                if (task.fiber.isCompleted) {
                    task.callback();
                    return false;
                }
                if (task.fiber.counter === 0) {
                    if (!task.fiber.error) {
                        try {
                            task.fiber.complete();
                        }
                        catch (e) {
                            task.fiber.handleError(e);
                        }
                    }
                    task.callback();
                    return false;
                }
                return true;
            });
            this.tasks = tasks.concat(this.tasks);
            if (this.tasks.length === 0) {
                this.stop();
            }
        }
        scheduleTasks() {
            this.requestAnimationFrame(() => {
                this.flush();
                if (this.isRunning) {
                    this.scheduleTasks();
                }
            });
        }
    }
    const scheduler = new Scheduler(browser.requestAnimationFrame);

    /**
     * Owl Fiber Class
     *
     * Fibers are small abstractions designed to contain all the internal state
     * associated with a "rendering work unit", relative to a specific component.
     *
     * A rendering will cause the creation of a fiber for each impacted components.
     *
     * Fibers capture all that necessary information, which is critical to owl
     * asynchronous rendering pipeline. Fibers can be cancelled, can be in different
     * states and in general determine the state of the rendering.
     */
    class Fiber {
        constructor(parent, component, force, target, position) {
            this.id = Fiber.nextId++;
            // isCompleted means that the rendering corresponding to this fiber's work is
            // done, either because the component has been mounted or patched, or because
            // fiber has been cancelled.
            this.isCompleted = false;
            // the fibers corresponding to component updates (updateProps) need to call
            // the willPatch and patched hooks from the corresponding component. However,
            // fibers corresponding to a new component do not need to do that. So, the
            // shouldPatch hook is the boolean that we check whenever we need to apply
            // a patch.
            this.shouldPatch = true;
            // isRendered is the last state of a fiber. If true, this means that it has
            // been rendered and is inert (so, it should not be taken into account when
            // counting the number of active fibers).
            this.isRendered = false;
            // the counter number is a critical information. It is only necessary for a
            // root fiber.  For that fiber, this number counts the number of active sub
            // fibers.  When that number reaches 0, the fiber can be applied by the
            // scheduler.
            this.counter = 0;
            this.vnode = null;
            this.child = null;
            this.sibling = null;
            this.lastChild = null;
            this.parent = null;
            this.component = component;
            this.force = force;
            this.target = target;
            this.position = position;
            const __owl__ = component.__owl__;
            this.scope = __owl__.scope;
            this.root = parent ? parent.root : this;
            this.parent = parent;
            let oldFiber = __owl__.currentFiber;
            if (oldFiber && !oldFiber.isCompleted) {
                this.force = true;
                if (oldFiber.root === oldFiber && !parent) {
                    // both oldFiber and this fiber are root fibers
                    this._reuseFiber(oldFiber);
                    return oldFiber;
                }
                else {
                    this._remapFiber(oldFiber);
                }
            }
            this.root.counter++;
            __owl__.currentFiber = this;
        }
        /**
         * When the oldFiber is not completed yet, and both oldFiber and this fiber
         * are root fibers, we want to reuse the oldFiber instead of creating a new
         * one. Doing so will guarantee that the initiator(s) of those renderings will
         * be notified (the promise will resolve) when the last rendering will be done.
         *
         * This function thus assumes that oldFiber is a root fiber.
         */
        _reuseFiber(oldFiber) {
            oldFiber.cancel(); // cancel children fibers
            oldFiber.target = this.target || oldFiber.target;
            oldFiber.position = this.position || oldFiber.position;
            oldFiber.isCompleted = false; // keep the root fiber alive
            oldFiber.isRendered = false; // the fiber has to be re-rendered
            if (oldFiber.child) {
                // remove relation to children
                oldFiber.child.parent = null;
                oldFiber.child = null;
                oldFiber.lastChild = null;
            }
            oldFiber.counter = 1; // re-initialize counter
            oldFiber.id = Fiber.nextId++;
        }
        /**
         * In some cases, a rendering initiated at some component can detect that it
         * should be part of a larger rendering initiated somewhere up the component
         * tree.  In that case, it needs to cancel the previous rendering and
         * remap itself as a part of the current parent rendering.
         */
        _remapFiber(oldFiber) {
            oldFiber.cancel();
            this.shouldPatch = oldFiber.shouldPatch;
            if (oldFiber === oldFiber.root) {
                oldFiber.counter++;
            }
            if (oldFiber.parent && !this.parent) {
                // re-map links
                this.parent = oldFiber.parent;
                this.root = this.parent.root;
                this.sibling = oldFiber.sibling;
                if (this.parent.lastChild === oldFiber) {
                    this.parent.lastChild = this;
                }
                if (this.parent.child === oldFiber) {
                    this.parent.child = this;
                }
                else {
                    let current = this.parent.child;
                    while (true) {
                        if (current.sibling === oldFiber) {
                            current.sibling = this;
                            break;
                        }
                        current = current.sibling;
                    }
                }
            }
        }
        /**
         * This function has been taken from
         * https://medium.com/react-in-depth/the-how-and-why-on-reacts-usage-of-linked-list-in-fiber-67f1014d0eb7
         */
        _walk(doWork) {
            let root = this;
            let current = this;
            while (true) {
                const child = doWork(current);
                if (child) {
                    current = child;
                    continue;
                }
                if (current === root) {
                    return;
                }
                while (!current.sibling) {
                    if (!current.parent || current.parent === root) {
                        return;
                    }
                    current = current.parent;
                }
                current = current.sibling;
            }
        }
        /**
         * Successfully complete the work of the fiber: call the mount or patch hooks
         * and patch the DOM. This function is called once the fiber and its children
         * are ready, and the scheduler decides to process it.
         */
        complete() {
            let component = this.component;
            this.isCompleted = true;
            const status = component.__owl__.status;
            if (status === 5 /* DESTROYED */) {
                return;
            }
            // build patchQueue
            const patchQueue = [];
            const doWork = function (f) {
                patchQueue.push(f);
                return f.child;
            };
            this._walk(doWork);
            const patchLen = patchQueue.length;
            // call willPatch hook on each fiber of patchQueue
            if (status === 3 /* MOUNTED */) {
                for (let i = 0; i < patchLen; i++) {
                    const fiber = patchQueue[i];
                    if (fiber.shouldPatch) {
                        component = fiber.component;
                        if (component.__owl__.willPatchCB) {
                            component.__owl__.willPatchCB();
                        }
                        component.willPatch();
                    }
                }
            }
            // call __patch on each fiber of (reversed) patchQueue
            for (let i = patchLen - 1; i >= 0; i--) {
                const fiber = patchQueue[i];
                component = fiber.component;
                if (fiber.target && i === 0) {
                    let target;
                    if (fiber.position === "self") {
                        target = fiber.target;
                        if (target.tagName.toLowerCase() !== fiber.vnode.sel) {
                            throw new Error(`Cannot attach '${component.constructor.name}' to target node (not same tag name)`);
                        }
                        // In self mode, we *know* we are to take possession of the target
                        // Hence we manually create the corresponding VNode and copy the "key" in data
                        const selfVnodeData = fiber.vnode.data ? { key: fiber.vnode.data.key } : {};
                        const selfVnode = h(fiber.vnode.sel, selfVnodeData);
                        selfVnode.elm = target;
                        target = selfVnode;
                    }
                    else {
                        target = component.__owl__.vnode || document.createElement(fiber.vnode.sel);
                    }
                    component.__patch(target, fiber.vnode);
                }
                else {
                    if (fiber.shouldPatch) {
                        component.__patch(component.__owl__.vnode, fiber.vnode);
                        // When updating a Component's props (in directive),
                        // the component has a pvnode AND should be patched.
                        // However, its pvnode.elm may have changed if it is a High Order Component
                        if (component.__owl__.pvnode) {
                            component.__owl__.pvnode.elm = component.__owl__.vnode.elm;
                        }
                    }
                    else {
                        component.__patch(document.createElement(fiber.vnode.sel), fiber.vnode);
                        component.__owl__.pvnode.elm = component.__owl__.vnode.elm;
                    }
                }
                const compOwl = component.__owl__;
                if (fiber === compOwl.currentFiber) {
                    compOwl.currentFiber = null;
                }
            }
            // insert into the DOM (mount case)
            let inDOM = false;
            if (this.target) {
                switch (this.position) {
                    case "first-child":
                        this.target.prepend(this.component.el);
                        break;
                    case "last-child":
                        this.target.appendChild(this.component.el);
                        break;
                }
                inDOM = document.body.contains(this.component.el);
                this.component.env.qweb.trigger("dom-appended");
            }
            // call patched/mounted hook on each fiber of (reversed) patchQueue
            if (status === 3 /* MOUNTED */ || inDOM) {
                for (let i = patchLen - 1; i >= 0; i--) {
                    const fiber = patchQueue[i];
                    component = fiber.component;
                    if (fiber.shouldPatch && !this.target) {
                        component.patched();
                        if (component.__owl__.patchedCB) {
                            component.__owl__.patchedCB();
                        }
                    }
                    else {
                        component.__callMounted();
                    }
                }
            }
            else {
                for (let i = patchLen - 1; i >= 0; i--) {
                    const fiber = patchQueue[i];
                    component = fiber.component;
                    component.__owl__.status = 4 /* UNMOUNTED */;
                }
            }
        }
        /**
         * Cancel a fiber and all its children.
         */
        cancel() {
            this._walk((f) => {
                if (!f.isRendered) {
                    f.root.counter--;
                }
                f.isCompleted = true;
                return f.child;
            });
        }
        /**
         * This is the global error handler for errors occurring in Owl main lifecycle
         * methods.  Caught errors are triggered on the QWeb instance, and are
         * potentially given to some parent component which implements `catchError`.
         *
         * If there are no such component, we destroy everything. This is better than
         * being in a corrupted state.
         */
        handleError(error) {
            let component = this.component;
            this.vnode = component.__owl__.vnode || h("div");
            const qweb = component.env.qweb;
            let root = component;
            let canCatch = false;
            while (component && !(canCatch = !!component.catchError)) {
                root = component;
                component = component.__owl__.parent;
            }
            qweb.trigger("error", error);
            if (canCatch) {
                component.catchError(error);
            }
            else {
                // the 3 next lines aim to mark the root fiber as being in error, and
                // to force it to end, without waiting for its children
                this.root.counter = 0;
                this.root.error = error;
                scheduler.flush();
                root.destroy();
            }
        }
    }
    Fiber.nextId = 1;

    //------------------------------------------------------------------------------
    // Prop validation helper
    //------------------------------------------------------------------------------
    /**
     * Validate the component props (or next props) against the (static) props
     * description.  This is potentially an expensive operation: it may needs to
     * visit recursively the props and all the children to check if they are valid.
     * This is why it is only done in 'dev' mode.
     */
    QWeb.utils.validateProps = function (Widget, props) {
        const propsDef = Widget.props;
        if (propsDef instanceof Array) {
            // list of strings (prop names)
            for (let i = 0, l = propsDef.length; i < l; i++) {
                const propName = propsDef[i];
                if (propName[propName.length - 1] === "?") {
                    // optional prop
                    break;
                }
                if (!(propName in props)) {
                    throw new Error(`Missing props '${propsDef[i]}' (component '${Widget.name}')`);
                }
            }
            for (let key in props) {
                if (!propsDef.includes(key) && !propsDef.includes(key + "?")) {
                    throw new Error(`Unknown prop '${key}' given to component '${Widget.name}'`);
                }
            }
        }
        else if (propsDef) {
            // propsDef is an object now
            for (let propName in propsDef) {
                if (props[propName] === undefined) {
                    if (propsDef[propName] && !propsDef[propName].optional) {
                        throw new Error(`Missing props '${propName}' (component '${Widget.name}')`);
                    }
                    else {
                        continue;
                    }
                }
                let isValid;
                try {
                    isValid = isValidProp(props[propName], propsDef[propName]);
                }
                catch (e) {
                    e.message = `Invalid prop '${propName}' in component ${Widget.name} (${e.message})`;
                    throw e;
                }
                if (!isValid) {
                    throw new Error(`Invalid Prop '${propName}' in component '${Widget.name}'`);
                }
            }
            for (let propName in props) {
                if (!(propName in propsDef)) {
                    throw new Error(`Unknown prop '${propName}' given to component '${Widget.name}'`);
                }
            }
        }
    };
    /**
     * Check if an invidual prop value matches its (static) prop definition
     */
    function isValidProp(prop, propDef) {
        if (propDef === true) {
            return true;
        }
        if (typeof propDef === "function") {
            // Check if a value is constructed by some Constructor.  Note that there is a
            // slight abuse of language: we want to consider primitive values as well.
            //
            // So, even though 1 is not an instance of Number, we want to consider that
            // it is valid.
            if (typeof prop === "object") {
                return prop instanceof propDef;
            }
            return typeof prop === propDef.name.toLowerCase();
        }
        else if (propDef instanceof Array) {
            // If this code is executed, this means that we want to check if a prop
            // matches at least one of its descriptor.
            let result = false;
            for (let i = 0, iLen = propDef.length; i < iLen; i++) {
                result = result || isValidProp(prop, propDef[i]);
            }
            return result;
        }
        // propsDef is an object
        if (propDef.optional && prop === undefined) {
            return true;
        }
        let result = propDef.type ? isValidProp(prop, propDef.type) : true;
        if (propDef.validate) {
            result = result && propDef.validate(prop);
        }
        if (propDef.type === Array && propDef.element) {
            for (let i = 0, iLen = prop.length; i < iLen; i++) {
                result = result && isValidProp(prop[i], propDef.element);
            }
        }
        if (propDef.type === Object && propDef.shape) {
            const shape = propDef.shape;
            for (let key in shape) {
                result = result && isValidProp(prop[key], shape[key]);
            }
            if (result) {
                for (let propName in prop) {
                    if (!(propName in shape)) {
                        throw new Error(`unknown prop '${propName}'`);
                    }
                }
            }
        }
        return result;
    }

    /**
     * Owl Style System
     *
     * This files contains the Owl code related to processing (extended) css strings
     * and creating/adding <style> tags to the document head.
     */
    const STYLESHEETS = {};
    function processSheet(str) {
        const tokens = str.split(/(\{|\}|;)/).map((s) => s.trim());
        const selectorStack = [];
        const parts = [];
        let rules = [];
        function generateSelector(stackIndex, parentSelector) {
            const parts = [];
            for (const selector of selectorStack[stackIndex]) {
                let part = (parentSelector && parentSelector + " " + selector) || selector;
                if (part.includes("&")) {
                    part = selector.replace(/&/g, parentSelector || "");
                }
                if (stackIndex < selectorStack.length - 1) {
                    part = generateSelector(stackIndex + 1, part);
                }
                parts.push(part);
            }
            return parts.join(", ");
        }
        function generateRules() {
            if (rules.length) {
                parts.push(generateSelector(0) + " {");
                parts.push(...rules);
                parts.push("}");
                rules = [];
            }
        }
        while (tokens.length) {
            let token = tokens.shift();
            if (token === "}") {
                generateRules();
                selectorStack.pop();
            }
            else {
                if (tokens[0] === "{") {
                    generateRules();
                    selectorStack.push(token.split(/\s*,\s*/));
                    tokens.shift();
                }
                if (tokens[0] === ";") {
                    rules.push("  " + token + ";");
                }
            }
        }
        return parts.join("\n");
    }
    function registerSheet(id, css) {
        const sheet = document.createElement("style");
        sheet.innerHTML = processSheet(css);
        STYLESHEETS[id] = sheet;
    }
    function activateSheet(id, name) {
        const sheet = STYLESHEETS[id];
        if (!sheet) {
            throw new Error(`Invalid css stylesheet for component '${name}'. Did you forget to use the 'css' tag helper?`);
        }
        sheet.setAttribute("component", name);
        document.head.appendChild(sheet);
    }

    var STATUS;
    (function (STATUS) {
        STATUS[STATUS["CREATED"] = 0] = "CREATED";
        STATUS[STATUS["WILLSTARTED"] = 1] = "WILLSTARTED";
        STATUS[STATUS["RENDERED"] = 2] = "RENDERED";
        STATUS[STATUS["MOUNTED"] = 3] = "MOUNTED";
        STATUS[STATUS["UNMOUNTED"] = 4] = "UNMOUNTED";
        STATUS[STATUS["DESTROYED"] = 5] = "DESTROYED";
    })(STATUS || (STATUS = {}));
    const portalSymbol = Symbol("portal"); // FIXME
    //------------------------------------------------------------------------------
    // Component
    //------------------------------------------------------------------------------
    let nextId = 1;
    class Component {
        //--------------------------------------------------------------------------
        // Lifecycle
        //--------------------------------------------------------------------------
        /**
         * Creates an instance of Component.
         *
         * Note that most of the time, only the root component needs to be created by
         * hand.  Other components should be created automatically by the framework (with
         * the t-component directive in a template)
         */
        constructor(parent, props) {
            Component.current = this;
            let constr = this.constructor;
            const defaultProps = constr.defaultProps;
            if (defaultProps) {
                props = props || {};
                this.__applyDefaultProps(props, defaultProps);
            }
            this.props = props;
            if (QWeb.dev) {
                QWeb.utils.validateProps(constr, this.props);
            }
            const id = nextId++;
            let depth;
            if (parent) {
                this.env = parent.env;
                const __powl__ = parent.__owl__;
                __powl__.children[id] = this;
                depth = __powl__.depth + 1;
            }
            else {
                // we are the root component
                this.env = this.constructor.env;
                if (!this.env.qweb) {
                    this.env.qweb = new QWeb();
                }
                // TODO: remove this in owl 2.0
                if (!this.env.browser) {
                    this.env.browser = browser;
                }
                this.env.qweb.on("update", this, () => {
                    switch (this.__owl__.status) {
                        case 3 /* MOUNTED */:
                            this.render(true);
                            break;
                        case 5 /* DESTROYED */:
                            // this is unlikely to happen, but if a root widget is destroyed,
                            // we want to remove our subscription.  The usual way to do that
                            // would be to perform some check in the destroy method, but since
                            // it is very performance sensitive, and since this is a rare event,
                            // we simply do it lazily
                            this.env.qweb.off("update", this);
                            break;
                    }
                });
                depth = 0;
            }
            const qweb = this.env.qweb;
            const template = constr.template || this.__getTemplate(qweb);
            this.__owl__ = {
                id: id,
                depth: depth,
                vnode: null,
                pvnode: null,
                status: 0 /* CREATED */,
                parent: parent || null,
                children: {},
                cmap: {},
                currentFiber: null,
                parentLastFiberId: 0,
                boundHandlers: {},
                mountedCB: null,
                willUnmountCB: null,
                willPatchCB: null,
                patchedCB: null,
                willStartCB: null,
                willUpdatePropsCB: null,
                observer: null,
                renderFn: qweb.render.bind(qweb, template),
                classObj: null,
                refs: null,
                scope: null,
            };
            if (constr.style) {
                this.__applyStyles(constr);
            }
            this.setup();
        }
        /**
         * The `el` is the root element of the component.  Note that it could be null:
         * this is the case if the component is not mounted yet, or is destroyed.
         */
        get el() {
            return this.__owl__.vnode ? this.__owl__.vnode.elm : null;
        }
        /**
         * setup is run just after the component is constructed. This is the standard
         * location where the component can setup its hooks. It has some advantages
         * over the constructor:
         *  - it can be patched (useful in odoo ecosystem)
         *  - it does not need to propagate the arguments to the super call
         *
         * Note: this method should not be called manually.
         */
        setup() { }
        /**
         * willStart is an asynchronous hook that can be implemented to perform some
         * action before the initial rendering of a component.
         *
         * It will be called exactly once before the initial rendering. It is useful
         * in some cases, for example, to load external assets (such as a JS library)
         * before the component is rendered.
         *
         * Note that a slow willStart method will slow down the rendering of the user
         * interface.  Therefore, some effort should be made to make this method as
         * fast as possible.
         *
         * Note: this method should not be called manually.
         */
        async willStart() { }
        /**
         * mounted is a hook that is called each time a component is attached to the
         * DOM. This is a good place to add some listeners, or to interact with the
         * DOM, if the component needs to perform some measure for example.
         *
         * Note: this method should not be called manually.
         *
         * @see willUnmount
         */
        mounted() { }
        /**
         * The willUpdateProps is an asynchronous hook, called just before new props
         * are set. This is useful if the component needs some asynchronous task
         * performed, depending on the props (for example, assuming that the props are
         * some record Id, fetching the record data).
         *
         * This hook is not called during the first render (but willStart is called
         * and performs a similar job).
         */
        async willUpdateProps(nextProps) { }
        /**
         * The willPatch hook is called just before the DOM patching process starts.
         * It is not called on the initial render.  This is useful to get some
         * information which are in the DOM.  For example, the current position of the
         * scrollbar
         */
        willPatch() { }
        /**
         * This hook is called whenever a component did actually update its props,
         * state or env.
         *
         * This method is not called on the initial render. It is useful to interact
         * with the DOM (for example, through an external library) whenever the
         * component was updated.
         *
         * Updating the component state in this hook is possible, but not encouraged.
         * One need to be careful, because updates here will cause rerender, which in
         * turn will cause other calls to updated. So, we need to be particularly
         * careful at avoiding endless cycles.
         */
        patched() { }
        /**
         * willUnmount is a hook that is called each time just before a component is
         * unmounted from the DOM. This is a good place to remove some listeners, for
         * example.
         *
         * Note: this method should not be called manually.
         *
         * @see mounted
         */
        willUnmount() { }
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Mount the component to a target element.
         *
         * This should only be done if the component was created manually. Components
         * created declaratively in templates are managed by the Owl system.
         *
         * Note that a component can be mounted an unmounted several times
         */
        async mount(target, options = {}) {
            if (!(target instanceof HTMLElement || target instanceof DocumentFragment)) {
                let message = `Component '${this.constructor.name}' cannot be mounted: the target is not a valid DOM node.`;
                message += `\nMaybe the DOM is not ready yet? (in that case, you can use owl.utils.whenReady)`;
                throw new Error(message);
            }
            const position = options.position || "last-child";
            const __owl__ = this.__owl__;
            const currentFiber = __owl__.currentFiber;
            switch (__owl__.status) {
                case 0 /* CREATED */: {
                    const fiber = new Fiber(null, this, true, target, position);
                    fiber.shouldPatch = false;
                    this.__prepareAndRender(fiber, () => { });
                    return scheduler.addFiber(fiber);
                }
                case 1 /* WILLSTARTED */:
                case 2 /* RENDERED */:
                    currentFiber.target = target;
                    currentFiber.position = position;
                    return scheduler.addFiber(currentFiber);
                case 4 /* UNMOUNTED */: {
                    const fiber = new Fiber(null, this, true, target, position);
                    fiber.shouldPatch = false;
                    this.__render(fiber);
                    return scheduler.addFiber(fiber);
                }
                case 3 /* MOUNTED */: {
                    if (position !== "self" && this.el.parentNode !== target) {
                        const fiber = new Fiber(null, this, true, target, position);
                        fiber.shouldPatch = false;
                        this.__render(fiber);
                        return scheduler.addFiber(fiber);
                    }
                    else {
                        return Promise.resolve();
                    }
                }
                case 5 /* DESTROYED */:
                    throw new Error("Cannot mount a destroyed component");
            }
        }
        /**
         * The unmount method is the opposite of the mount method.  It is useful
         * to call willUnmount calls and remove the component from the DOM.
         */
        unmount() {
            if (this.__owl__.status === 3 /* MOUNTED */) {
                this.__callWillUnmount();
                this.el.remove();
            }
        }
        /**
         * The render method is the main entry point to render a component (once it
         * is ready. This method is not initially called when the component is
         * rendered the first time).
         *
         * This method will cause all its sub components to potentially rerender
         * themselves.  Note that `render` is not called if a component is updated via
         * its props.
         */
        async render(force = false) {
            const __owl__ = this.__owl__;
            const currentFiber = __owl__.currentFiber;
            if (!__owl__.vnode && !currentFiber) {
                return;
            }
            if (currentFiber && !currentFiber.isRendered && !currentFiber.isCompleted) {
                return scheduler.addFiber(currentFiber.root);
            }
            // if we aren't mounted at this point, it implies that there is a
            // currentFiber that is already rendered (isRendered is true), so we are
            // about to be mounted
            const status = __owl__.status;
            const fiber = new Fiber(null, this, force, null, null);
            Promise.resolve().then(() => {
                if (__owl__.status === 3 /* MOUNTED */ || status !== 3 /* MOUNTED */) {
                    if (fiber.isCompleted || fiber.isRendered) {
                        return;
                    }
                    this.__render(fiber);
                }
                else {
                    // we were mounted when render was called, but we aren't anymore, so we
                    // were actually about to be unmounted ; we can thus forget about this
                    // fiber
                    fiber.isCompleted = true;
                    __owl__.currentFiber = null;
                }
            });
            return scheduler.addFiber(fiber);
        }
        /**
         * Destroy the component.  This operation is quite complex:
         *  - it recursively destroy all children
         *  - call the willUnmount hooks if necessary
         *  - remove the dom node from the dom
         *
         * This should only be called manually if you created the component.  Most
         * components will be automatically destroyed.
         */
        destroy() {
            const __owl__ = this.__owl__;
            if (__owl__.status !== 5 /* DESTROYED */) {
                const el = this.el;
                this.__destroy(__owl__.parent);
                if (el) {
                    el.remove();
                }
            }
        }
        /**
         * This method is called by the component system whenever its props are
         * updated. If it returns true, then the component will be rendered.
         * Otherwise, it will skip the rendering (also, its props will not be updated)
         */
        shouldUpdate(nextProps) {
            return true;
        }
        /**
         * Emit a custom event of type 'eventType' with the given 'payload' on the
         * component's el, if it exists. However, note that the event will only bubble
         * up to the parent DOM nodes. Thus, it must be called between mounted() and
         * willUnmount().
         */
        trigger(eventType, payload) {
            this.__trigger(this, eventType, payload);
        }
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Private helper to perform a full destroy, from the point of view of an Owl
         * component. It does not remove the el (this is done only once on the top
         * level destroyed component, for performance reasons).
         *
         * The job of this method is mostly to call willUnmount hooks, and to perform
         * all necessary internal cleanup.
         *
         * Note that it does not call the __callWillUnmount method to avoid visiting
         * all children many times.
         */
        __destroy(parent) {
            const __owl__ = this.__owl__;
            if (__owl__.status === 3 /* MOUNTED */) {
                if (__owl__.willUnmountCB) {
                    __owl__.willUnmountCB();
                }
                this.willUnmount();
                __owl__.status = 4 /* UNMOUNTED */;
            }
            const children = __owl__.children;
            for (let key in children) {
                children[key].__destroy(this);
            }
            if (parent) {
                let id = __owl__.id;
                delete parent.__owl__.children[id];
                __owl__.parent = null;
            }
            __owl__.status = 5 /* DESTROYED */;
            delete __owl__.vnode;
            if (__owl__.currentFiber) {
                __owl__.currentFiber.isCompleted = true;
            }
        }
        __callMounted() {
            const __owl__ = this.__owl__;
            __owl__.status = 3 /* MOUNTED */;
            __owl__.currentFiber = null;
            this.mounted();
            if (__owl__.mountedCB) {
                __owl__.mountedCB();
            }
        }
        __callWillUnmount() {
            const __owl__ = this.__owl__;
            if (__owl__.willUnmountCB) {
                __owl__.willUnmountCB();
            }
            this.willUnmount();
            __owl__.status = 4 /* UNMOUNTED */;
            if (__owl__.currentFiber) {
                __owl__.currentFiber.isCompleted = true;
                __owl__.currentFiber.root.counter = 0;
            }
            const children = __owl__.children;
            for (let id in children) {
                const comp = children[id];
                if (comp.__owl__.status === 3 /* MOUNTED */) {
                    comp.__callWillUnmount();
                }
            }
        }
        /**
         * Private trigger method, allows to choose the component which triggered
         * the event in the first place
         */
        __trigger(component, eventType, payload) {
            if (this.el) {
                const ev = new OwlEvent(component, eventType, {
                    bubbles: true,
                    cancelable: true,
                    detail: payload,
                });
                const triggerHook = this.env[portalSymbol];
                if (triggerHook) {
                    triggerHook(ev);
                }
                this.el.dispatchEvent(ev);
            }
        }
        /**
         * The __updateProps method is called by the t-component directive whenever
         * it updates a component (so, when the parent template is rerendered).
         */
        async __updateProps(nextProps, parentFiber, scope) {
            this.__owl__.scope = scope;
            const shouldUpdate = parentFiber.force || this.shouldUpdate(nextProps);
            if (shouldUpdate) {
                const __owl__ = this.__owl__;
                const fiber = new Fiber(parentFiber, this, parentFiber.force, null, null);
                if (!parentFiber.child) {
                    parentFiber.child = fiber;
                }
                else {
                    parentFiber.lastChild.sibling = fiber;
                }
                parentFiber.lastChild = fiber;
                const defaultProps = this.constructor.defaultProps;
                if (defaultProps) {
                    this.__applyDefaultProps(nextProps, defaultProps);
                }
                if (QWeb.dev) {
                    QWeb.utils.validateProps(this.constructor, nextProps);
                }
                await Promise.all([
                    this.willUpdateProps(nextProps),
                    __owl__.willUpdatePropsCB && __owl__.willUpdatePropsCB(nextProps),
                ]);
                if (fiber.isCompleted) {
                    return;
                }
                this.props = nextProps;
                this.__render(fiber);
            }
        }
        /**
         * Main patching method. We call the virtual dom patch method here to convert
         * a virtual dom vnode into some actual dom.
         */
        __patch(target, vnode) {
            this.__owl__.vnode = patch(target, vnode);
        }
        /**
         * The __prepare method is only called by the t-component directive, when a
         * subcomponent is created. It gets its scope, if any, from the
         * parent template.
         */
        __prepare(parentFiber, scope, cb) {
            this.__owl__.scope = scope;
            const fiber = new Fiber(parentFiber, this, parentFiber.force, null, null);
            fiber.shouldPatch = false;
            if (!parentFiber.child) {
                parentFiber.child = fiber;
            }
            else {
                parentFiber.lastChild.sibling = fiber;
            }
            parentFiber.lastChild = fiber;
            this.__prepareAndRender(fiber, cb);
            return fiber;
        }
        /**
         * Apply the stylesheets defined by the component. Note that we need to make
         * sure all inherited stylesheets are applied as well.  We then delete the
         * `style` key from the constructor to make sure we do not apply it again.
         */
        __applyStyles(constr) {
            while (constr && constr.style) {
                if (constr.hasOwnProperty("style")) {
                    activateSheet(constr.style, constr.name);
                    delete constr.style;
                }
                constr = constr.__proto__;
            }
        }
        __getTemplate(qweb) {
            let p = this.constructor;
            if (!p.hasOwnProperty("_template")) {
                // here, the component and none of its superclasses defines a static `template`
                // key. So we fall back on looking for a template matching its name (or
                // one of its subclass).
                let template = p.name;
                while (!(template in qweb.templates) && p !== Component) {
                    p = p.__proto__;
                    template = p.name;
                }
                if (p === Component) {
                    throw new Error(`Could not find template for component "${this.constructor.name}"`);
                }
                else {
                    p._template = template;
                }
            }
            return p._template;
        }
        async __prepareAndRender(fiber, cb) {
            try {
                const proms = Promise.all([
                    this.willStart(),
                    this.__owl__.willStartCB && this.__owl__.willStartCB(),
                ]);
                this.__owl__.status = 1 /* WILLSTARTED */;
                await proms;
                if (this.__owl__.status === 5 /* DESTROYED */) {
                    return Promise.resolve();
                }
            }
            catch (e) {
                fiber.handleError(e);
                return Promise.resolve();
            }
            if (!fiber.isCompleted) {
                this.__render(fiber);
                this.__owl__.status = 2 /* RENDERED */;
                cb();
            }
        }
        __render(fiber) {
            const __owl__ = this.__owl__;
            if (__owl__.observer) {
                __owl__.observer.allowMutations = false;
            }
            let error;
            try {
                let vnode = __owl__.renderFn(this, {
                    handlers: __owl__.boundHandlers,
                    fiber: fiber,
                });
                // we iterate over the children to detect those that no longer belong to the
                // current rendering: those ones, if not mounted yet, can (and have to) be
                // destroyed right now, because they are not in the DOM, and thus we won't
                // be notified later on (when patching), that they are removed from the DOM
                for (let childKey in __owl__.children) {
                    const child = __owl__.children[childKey];
                    const childOwl = child.__owl__;
                    if (childOwl.status !== 3 /* MOUNTED */ && childOwl.parentLastFiberId < fiber.id) {
                        // we only do here a "soft" destroy, meaning that we leave the child
                        // dom node alone, without removing it.  Most of the time, it does not
                        // matter, because the child component is already unmounted.  However,
                        // if some of its parent have been unmounted, the child could actually
                        // still be attached to its parent, and this may be important if we
                        // want to remount the parent, because the vdom need to match the
                        // actual DOM
                        child.__destroy(childOwl.parent);
                        if (childOwl.pvnode) {
                            // we remove the key here to make sure that the patching algorithm
                            // is able to make the difference between this pvnode and an eventual
                            // other instance of the same component
                            delete childOwl.pvnode.key;
                            // Since the component has been unmounted, we do not want to actually
                            // call a remove hook.  This is pretty important, since the t-component
                            // directive actually disabled it, so the vdom algorithm will just
                            // not remove the child elm if we don't remove the hook.
                            delete childOwl.pvnode.data.hook.remove;
                        }
                    }
                }
                if (!vnode) {
                    throw new Error(`Rendering '${this.constructor.name}' did not return anything`);
                }
                fiber.vnode = vnode;
                // we apply here the class information described on the component by the
                // template (so, something like <MyComponent class="..."/>) to the actual
                // root vnode
                if (__owl__.classObj) {
                    const data = vnode.data;
                    data.class = Object.assign(data.class || {}, __owl__.classObj);
                }
            }
            catch (e) {
                error = e;
            }
            if (__owl__.observer) {
                __owl__.observer.allowMutations = true;
            }
            fiber.root.counter--;
            fiber.isRendered = true;
            if (error) {
                fiber.handleError(error);
            }
        }
        /**
         * Apply default props (only top level).
         *
         * Note that this method does modify in place the props
         */
        __applyDefaultProps(props, defaultProps) {
            for (let propName in defaultProps) {
                if (props[propName] === undefined) {
                    props[propName] = defaultProps[propName];
                }
            }
        }
    }
    Component.template = null;
    Component._template = null;
    Component.current = null;
    Component.components = {};
    Component.env = {};
    // expose scheduler s.t. it can be mocked for testing purposes
    Component.scheduler = scheduler;
    async function mount(C, params) {
        const { env, props, target } = params;
        let origEnv = C.hasOwnProperty("env") ? C.env : null;
        if (env) {
            C.env = env;
        }
        const component = new C(null, props);
        if (origEnv) {
            C.env = origEnv;
        }
        else {
            delete C.env;
        }
        const position = params.position || "last-child";
        await component.mount(target, { position });
        return component;
    }

    /**
     * The `Context` object provides a way to share data between an arbitrary number
     * of component. Usually, data is passed from a parent to its children component,
     * but when we have to deal with some mostly global information, this can be
     * annoying, since each component will need to pass the information to each
     * children, even though some or most of them will not use the information.
     *
     * With a `Context` object, each component can subscribe (with the `useContext`
     * hook) to its state, and will be updated whenever the context state is updated.
     */
    function partitionBy(arr, fn) {
        let lastGroup = false;
        let lastValue;
        return arr.reduce((acc, cur) => {
            let curVal = fn(cur);
            if (lastGroup) {
                if (curVal === lastValue) {
                    lastGroup.push(cur);
                }
                else {
                    lastGroup = false;
                }
            }
            if (!lastGroup) {
                lastGroup = [cur];
                acc.push(lastGroup);
            }
            lastValue = curVal;
            return acc;
        }, []);
    }
    class Context extends EventBus {
        constructor(state = {}) {
            super();
            this.rev = 1;
            // mapping from component id to last observed context id
            this.mapping = {};
            this.observer = new Observer();
            this.observer.notifyCB = () => {
                // notify components in the next microtask tick to ensure that subscribers
                // are notified only once for all changes that occur in the same micro tick
                let rev = this.rev;
                return Promise.resolve().then(() => {
                    if (rev === this.rev) {
                        this.__notifyComponents();
                    }
                });
            };
            this.state = this.observer.observe(state);
            this.subscriptions.update = [];
        }
        /**
         * Instead of using trigger to emit an update event, we actually implement
         * our own function to do that.  The reason is that we need to be smarter than
         * a simple trigger function: we need to wait for parent components to be
         * done before doing children components.  More precisely, if an update
         * as an effect of destroying a children, we do not want to call any code
         * from the child, and certainly not render it.
         *
         * This method implements a simple grouping algorithm by depth. If we have
         * connected components of depths [2, 4,4,4,4, 3,8,8], the Context will notify
         * them in the following groups: [2], [4,4,4,4], [3], [8,8]. Each group will
         * be updated sequentially, but each components in a given group will be done in
         * parallel.
         *
         * This is a very simple algorithm, but it avoids checking if a given
         * component is a child of another.
         */
        async __notifyComponents() {
            const rev = ++this.rev;
            const subscriptions = this.subscriptions.update;
            const groups = partitionBy(subscriptions, (s) => (s.owner ? s.owner.__owl__.depth : -1));
            for (let group of groups) {
                const proms = group.map((sub) => sub.callback.call(sub.owner, rev));
                // at this point, each component in the current group has registered a
                // top level fiber in the scheduler. It could happen that rendering these
                // components is done (if they have no children).  This is why we manually
                // flush the scheduler.  This will force the scheduler to check
                // immediately if they are done, which will cause their rendering
                // promise to resolve earlier, which means that there is a chance of
                // processing the next group in the same frame.
                scheduler.flush();
                await Promise.all(proms);
            }
        }
    }
    /**
     * The`useContext` hook is the normal way for a component to register themselve
     * to context state changes. The `useContext` method returns the context state
     */
    function useContext(ctx) {
        const component = Component.current;
        return useContextWithCB(ctx, component, component.render.bind(component));
    }
    function useContextWithCB(ctx, component, method) {
        const __owl__ = component.__owl__;
        const id = __owl__.id;
        const mapping = ctx.mapping;
        if (id in mapping) {
            return ctx.state;
        }
        if (!__owl__.observer) {
            __owl__.observer = new Observer();
            __owl__.observer.notifyCB = component.render.bind(component);
        }
        mapping[id] = 0;
        const renderFn = __owl__.renderFn;
        __owl__.renderFn = function (comp, params) {
            mapping[id] = ctx.rev;
            return renderFn(comp, params);
        };
        ctx.on("update", component, async (contextRev) => {
            if (mapping[id] < contextRev) {
                mapping[id] = contextRev;
                await method();
            }
        });
        const __destroy = component.__destroy;
        component.__destroy = (parent) => {
            ctx.off("update", component);
            delete mapping[id];
            __destroy.call(component, parent);
        };
        return ctx.state;
    }

    /**
     * Owl Hook System
     *
     * This file introduces the concept of hooks, similar to React or Vue hooks.
     * We have currently an implementation of:
     * - useState (reactive state)
     * - onMounted
     * - onWillUnmount
     * - useRef
     */
    // -----------------------------------------------------------------------------
    // useState
    // -----------------------------------------------------------------------------
    /**
     * This is the main way a component can be made reactive.  The useState hook
     * will return an observed object (or array).  Changes to that value will then
     * trigger a rerendering of the current component.
     */
    function useState(state) {
        const component = Component.current;
        const __owl__ = component.__owl__;
        if (!__owl__.observer) {
            __owl__.observer = new Observer();
            __owl__.observer.notifyCB = component.render.bind(component);
        }
        return __owl__.observer.observe(state);
    }
    // -----------------------------------------------------------------------------
    // Life cycle hooks
    // -----------------------------------------------------------------------------
    function makeLifecycleHook(method, reverse = false) {
        if (reverse) {
            return function (cb) {
                const component = Component.current;
                if (component.__owl__[method]) {
                    const current = component.__owl__[method];
                    component.__owl__[method] = function () {
                        current.call(component);
                        cb.call(component);
                    };
                }
                else {
                    component.__owl__[method] = cb;
                }
            };
        }
        else {
            return function (cb) {
                const component = Component.current;
                if (component.__owl__[method]) {
                    const current = component.__owl__[method];
                    component.__owl__[method] = function () {
                        cb.call(component);
                        current.call(component);
                    };
                }
                else {
                    component.__owl__[method] = cb;
                }
            };
        }
    }
    function makeAsyncHook(method) {
        return function (cb) {
            const component = Component.current;
            if (component.__owl__[method]) {
                const current = component.__owl__[method];
                component.__owl__[method] = function (...args) {
                    return Promise.all([current.call(component, ...args), cb.call(component, ...args)]);
                };
            }
            else {
                component.__owl__[method] = cb;
            }
        };
    }
    const onMounted = makeLifecycleHook("mountedCB", true);
    const onWillUnmount = makeLifecycleHook("willUnmountCB");
    const onWillPatch = makeLifecycleHook("willPatchCB");
    const onPatched = makeLifecycleHook("patchedCB", true);
    const onWillStart = makeAsyncHook("willStartCB");
    const onWillUpdateProps = makeAsyncHook("willUpdatePropsCB");
    function useRef(name) {
        const __owl__ = Component.current.__owl__;
        return {
            get el() {
                const val = __owl__.refs && __owl__.refs[name];
                if (val instanceof HTMLElement) {
                    return val;
                }
                else if (val instanceof Component) {
                    return val.el;
                }
                return null;
            },
            get comp() {
                const val = __owl__.refs && __owl__.refs[name];
                return val instanceof Component ? val : null;
            },
        };
    }
    // -----------------------------------------------------------------------------
    // "Builder" hooks
    // -----------------------------------------------------------------------------
    /**
     * This hook is useful as a building block for some customized hooks, that may
     * need a reference to the component calling them.
     */
    function useComponent() {
        return Component.current;
    }
    /**
     * This hook is useful as a building block for some customized hooks, that may
     * need a reference to the env of the component calling them.
     */
    function useEnv() {
        return Component.current.env;
    }
    // -----------------------------------------------------------------------------
    // useSubEnv
    // -----------------------------------------------------------------------------
    /**
     * This hook is a simple way to let components use a sub environment.  Note that
     * like for all hooks, it is important that this is only called in the
     * constructor method.
     */
    function useSubEnv(nextEnv) {
        const component = Component.current;
        component.env = Object.assign(Object.create(component.env), nextEnv);
    }
    // -----------------------------------------------------------------------------
    // useExternalListener
    // -----------------------------------------------------------------------------
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
    function useExternalListener(target, eventName, handler, eventParams) {
        const boundHandler = handler.bind(Component.current);
        onMounted(() => target.addEventListener(eventName, boundHandler, eventParams));
        onWillUnmount(() => target.removeEventListener(eventName, boundHandler, eventParams));
    }

    var _hooks = /*#__PURE__*/Object.freeze({
        __proto__: null,
        useState: useState,
        onMounted: onMounted,
        onWillUnmount: onWillUnmount,
        onWillPatch: onWillPatch,
        onPatched: onPatched,
        onWillStart: onWillStart,
        onWillUpdateProps: onWillUpdateProps,
        useRef: useRef,
        useComponent: useComponent,
        useEnv: useEnv,
        useSubEnv: useSubEnv,
        useExternalListener: useExternalListener
    });

    class Store extends Context {
        constructor(config) {
            super(config.state);
            this.actions = config.actions;
            this.env = config.env;
            this.getters = {};
            this.updateFunctions = [];
            if (config.getters) {
                const firstArg = {
                    state: this.state,
                    getters: this.getters,
                };
                for (let g in config.getters) {
                    this.getters[g] = config.getters[g].bind(this, firstArg);
                }
            }
        }
        dispatch(action, ...payload) {
            if (!this.actions[action]) {
                throw new Error(`[Error] action ${action} is undefined`);
            }
            const result = this.actions[action]({
                dispatch: this.dispatch.bind(this),
                env: this.env,
                state: this.state,
                getters: this.getters,
            }, ...payload);
            return result;
        }
        __notifyComponents() {
            this.trigger("before-update");
            return super.__notifyComponents();
        }
    }
    const isStrictEqual = (a, b) => a === b;
    function useStore(selector, options = {}) {
        const component = Component.current;
        const componentId = component.__owl__.id;
        const store = options.store || component.env.store;
        if (!(store instanceof Store)) {
            throw new Error(`No store found when connecting '${component.constructor.name}'`);
        }
        let result = selector(store.state, component.props);
        const hashFn = store.observer.revNumber.bind(store.observer);
        let revNumber = hashFn(result);
        const isEqual = options.isEqual || isStrictEqual;
        if (!store.updateFunctions[componentId]) {
            store.updateFunctions[componentId] = [];
        }
        function selectCompareUpdate(state, props) {
            const oldResult = result;
            result = selector(state, props);
            const newRevNumber = hashFn(result);
            if ((newRevNumber > 0 && revNumber !== newRevNumber) || !isEqual(oldResult, result)) {
                revNumber = newRevNumber;
                return true;
            }
            return false;
        }
        if (options.onUpdate) {
            store.on("before-update", component, () => {
                const newValue = selector(store.state, component.props);
                options.onUpdate(newValue);
            });
        }
        store.updateFunctions[componentId].push(function () {
            return selectCompareUpdate(store.state, component.props);
        });
        useContextWithCB(store, component, function () {
            let shouldRender = false;
            for (let fn of store.updateFunctions[componentId]) {
                shouldRender = fn() || shouldRender;
            }
            if (shouldRender) {
                return component.render();
            }
        });
        onWillUpdateProps((props) => {
            selectCompareUpdate(store.state, props);
        });
        const __destroy = component.__destroy;
        component.__destroy = (parent) => {
            delete store.updateFunctions[componentId];
            if (options.onUpdate) {
                store.off("before-update", component);
            }
            __destroy.call(component, parent);
        };
        if (typeof result !== "object" || result === null) {
            return result;
        }
        return new Proxy(result, {
            get(target, k) {
                return result[k];
            },
            set(target, k, v) {
                throw new Error("Store state should only be modified through actions");
            },
            has(target, k) {
                return k in result;
            },
        });
    }
    function useDispatch(store) {
        store = store || Component.current.env.store;
        return store.dispatch.bind(store);
    }
    function useGetters(store) {
        store = store || Component.current.env.store;
        return store.getters;
    }

    /**
     * Owl Tags
     *
     * We have here a (very) small collection of tag functions:
     *
     * - xml
     *
     * The plan is to add a few other tags such as css, globalcss.
     */
    /**
     * XML tag helper for defining templates.  With this, one can simply define
     * an inline template with just the template xml:
     * ```js
     *   class A extends Component {
     *     static template = xml`<div>some template</div>`;
     *   }
     * ```
     */
    function xml(strings, ...args) {
        const name = `__template__${QWeb.nextId++}`;
        const value = String.raw(strings, ...args);
        QWeb.registerTemplate(name, value);
        return name;
    }
    /**
     * CSS tag helper for defining inline stylesheets.  With this, one can simply define
     * an inline stylesheet with just the following code:
     * ```js
     *   class A extends Component {
     *     static style = css`.component-a { color: red; }`;
     *   }
     * ```
     */
    function css(strings, ...args) {
        const name = `__sheet__${QWeb.nextId++}`;
        const value = String.raw(strings, ...args);
        registerSheet(name, value);
        return name;
    }

    var _tags = /*#__PURE__*/Object.freeze({
        __proto__: null,
        xml: xml,
        css: css
    });

    /**
     * AsyncRoot
     *
     * Owl is by default asynchronous, and the user interface will wait for all its
     * subcomponents to be rendered before updating the DOM. This is most of the
     * time what we want, but in some cases, it makes sense to "detach" a component
     * from this coordination.  This is the goal of the AsyncRoot component.
     */
    class AsyncRoot extends Component {
        async __updateProps(nextProps, parentFiber) {
            this.render(parentFiber.force);
        }
    }
    AsyncRoot.template = xml `<t t-slot="default"/>`;

    class Portal extends Component {
        constructor(parent, props) {
            super(parent, props);
            // boolean to indicate whether or not we must listen to 'dom-appended' event
            // to hook on the moment when the target is inserted into the DOM (because it
            // is not when the portal is rendered)
            this.doTargetLookUp = true;
            // set of encountered events that need to be redirected
            this._handledEvents = new Set();
            // function that will be the event's tunnel (needs to be an arrow function to
            // avoid having to rebind `this`)
            this._handlerTunnel = (ev) => {
                ev.stopPropagation();
                this.__trigger(ev.originalComponent, ev.type, ev.detail);
            };
            // Storing the parent's env
            this.parentEnv = null;
            // represents the element that is moved somewhere else
            this.portal = null;
            // the target where we will move `portal`
            this.target = null;
            this.parentEnv = parent ? parent.env : {};
            // put a callback in the env that is propagated to children s.t. portal can
            // register an handler to those events just before children will trigger them
            useSubEnv({
                [portalSymbol]: (ev) => {
                    if (!this._handledEvents.has(ev.type)) {
                        this.portal.elm.addEventListener(ev.type, this._handlerTunnel);
                        this._handledEvents.add(ev.type);
                    }
                },
            });
        }
        /**
         * Override to revert back to a classic Component's structure
         *
         * @override
         */
        __callWillUnmount() {
            super.__callWillUnmount();
            this.el.appendChild(this.portal.elm);
            this.doTargetLookUp = true;
        }
        /**
         * At each DOM change, we must ensure that the portal contains exactly one
         * child
         */
        __checkVNodeStructure(vnode) {
            const children = vnode.children;
            let countRealNodes = 0;
            for (let child of children) {
                if (child.sel) {
                    countRealNodes++;
                }
            }
            if (countRealNodes !== 1) {
                throw new Error(`Portal must have exactly one non-text child (has ${countRealNodes})`);
            }
        }
        /**
         * Ensure the target is still there at whichever time we render
         */
        __checkTargetPresence() {
            if (!this.target || !document.contains(this.target)) {
                throw new Error(`Could not find any match for "${this.props.target}"`);
            }
        }
        /**
         * Move the portal's element to the target
         */
        __deployPortal() {
            this.__checkTargetPresence();
            this.target.appendChild(this.portal.elm);
        }
        /**
         * Override to remove from the DOM the element we have teleported
         *
         * @override
         */
        __destroy(parent) {
            if (this.portal && this.portal.elm) {
                const displacedElm = this.portal.elm;
                const parent = displacedElm.parentNode;
                if (parent) {
                    parent.removeChild(displacedElm);
                }
            }
            super.__destroy(parent);
        }
        /**
         * Override to patch the element that has been teleported
         *
         * @override
         */
        __patch(target, vnode) {
            if (this.doTargetLookUp) {
                const target = document.querySelector(this.props.target);
                if (!target) {
                    this.env.qweb.on("dom-appended", this, () => {
                        this.doTargetLookUp = false;
                        this.env.qweb.off("dom-appended", this);
                        this.target = document.querySelector(this.props.target);
                        this.__deployPortal();
                    });
                }
                else {
                    this.doTargetLookUp = false;
                    this.target = target;
                }
            }
            this.__checkVNodeStructure(vnode);
            const shouldDeploy = (!this.portal || this.el.contains(this.portal.elm)) && !this.doTargetLookUp;
            if (!this.doTargetLookUp && !shouldDeploy) {
                // Only on pure patching, provided the
                // this.target's parent has not been unmounted
                this.__checkTargetPresence();
            }
            const portalPatch = this.portal ? this.portal : document.createElement(vnode.children[0].sel);
            this.portal = patch(portalPatch, vnode.children[0]);
            vnode.children = [];
            super.__patch(target, vnode);
            if (shouldDeploy) {
                this.__deployPortal();
            }
        }
        /**
         * Override to set the env
         */
        __trigger(component, eventType, payload) {
            const env = this.env;
            this.env = this.parentEnv;
            super.__trigger(component, eventType, payload);
            this.env = env;
        }
    }
    Portal.template = xml `<portal><t t-slot="default"/></portal>`;
    Portal.props = {
        target: {
            type: String,
        },
    };

    class Link extends Component {
        constructor() {
            super(...arguments);
            this.href = this.env.router.destToPath(this.props);
        }
        async willUpdateProps(nextProps) {
            this.href = this.env.router.destToPath(nextProps);
        }
        get isActive() {
            if (this.env.router.mode === "hash") {
                return document.location.hash === this.href;
            }
            return document.location.pathname === this.href;
        }
        navigate(ev) {
            // don't redirect with control keys
            if (ev.metaKey || ev.altKey || ev.ctrlKey || ev.shiftKey) {
                return;
            }
            // don't redirect on right click
            if (ev.button !== undefined && ev.button !== 0) {
                return;
            }
            // don't redirect if `target="_blank"`
            if (ev.currentTarget && ev.currentTarget.getAttribute) {
                const target = ev.currentTarget.getAttribute("target");
                if (/\b_blank\b/i.test(target)) {
                    return;
                }
            }
            ev.preventDefault();
            this.env.router.navigate(this.props);
        }
    }
    Link.template = xml `
    <a  t-att-class="{'router-link-active': isActive }"
        t-att-href="href"
        t-on-click="navigate">
        <t t-slot="default"/>
    </a>
  `;

    class RouteComponent extends Component {
        get routeComponent() {
            return this.env.router.currentRoute && this.env.router.currentRoute.component;
        }
    }
    RouteComponent.template = xml `
    <t>
        <t
            t-if="routeComponent"
            t-component="routeComponent"
            t-key="env.router.currentRouteName"
            t-props="env.router.currentParams" />
    </t>
  `;

    const paramRegexp = /\{\{(.*?)\}\}/;
    const globalParamRegexp = new RegExp(paramRegexp.source, "g");
    class Router {
        constructor(env, routes, options = { mode: "history" }) {
            this.currentRoute = null;
            this.currentParams = null;
            env.router = this;
            this.mode = options.mode;
            this.env = env;
            this.routes = {};
            this.routeIds = [];
            let nextId = 1;
            for (let partialRoute of routes) {
                if (!partialRoute.name) {
                    partialRoute.name = "__route__" + nextId++;
                }
                if (partialRoute.component) {
                    QWeb.registerComponent("__component__" + partialRoute.name, partialRoute.component);
                }
                if (partialRoute.redirect) {
                    this.validateDestination(partialRoute.redirect);
                }
                partialRoute.params = partialRoute.path ? findParams(partialRoute.path) : [];
                partialRoute.extractionRegExp = makeExtractionRegExp(partialRoute.path);
                this.routes[partialRoute.name] = partialRoute;
                this.routeIds.push(partialRoute.name);
            }
        }
        //--------------------------------------------------------------------------
        // Public API
        //--------------------------------------------------------------------------
        async start() {
            this._listener = (ev) => this._navigate(this.currentPath(), ev);
            window.addEventListener("popstate", this._listener);
            if (this.mode === "hash") {
                window.addEventListener("hashchange", this._listener);
            }
            const result = await this.matchAndApplyRules(this.currentPath());
            if (result.type === "match") {
                this.currentRoute = result.route;
                this.currentParams = result.params;
                const currentPath = this.routeToPath(result.route, result.params);
                if (currentPath !== this.currentPath()) {
                    this.setUrlFromPath(currentPath);
                }
            }
        }
        async navigate(to) {
            const path = this.destToPath(to);
            return this._navigate(path);
        }
        async _navigate(path, ev) {
            const initialName = this.currentRouteName;
            const initialParams = this.currentParams;
            const result = await this.matchAndApplyRules(path);
            if (result.type === "match") {
                const finalPath = this.routeToPath(result.route, result.params);
                const isPopStateEvent = ev && ev instanceof PopStateEvent;
                if (!isPopStateEvent) {
                    this.setUrlFromPath(finalPath);
                }
                this.currentRoute = result.route;
                this.currentParams = result.params;
            }
            else if (result.type === "nomatch") {
                this.currentRoute = null;
                this.currentParams = null;
            }
            const didChange = this.currentRouteName !== initialName || !shallowEqual(this.currentParams, initialParams);
            if (didChange) {
                this.env.qweb.forceUpdate();
                return true;
            }
            return false;
        }
        destToPath(dest) {
            this.validateDestination(dest);
            return dest.path || this.routeToPath(this.routes[dest.to], dest.params);
        }
        get currentRouteName() {
            return this.currentRoute && this.currentRoute.name;
        }
        //--------------------------------------------------------------------------
        // Private helpers
        //--------------------------------------------------------------------------
        setUrlFromPath(path) {
            const separator = this.mode === "hash" ? location.pathname : "";
            const url = location.origin + separator + path;
            if (url !== window.location.href) {
                window.history.pushState({}, path, url);
            }
        }
        validateDestination(dest) {
            if ((!dest.path && !dest.to) || (dest.path && dest.to)) {
                throw new Error(`Invalid destination: ${JSON.stringify(dest)}`);
            }
        }
        routeToPath(route, params) {
            const prefix = this.mode === "hash" ? "#" : "";
            return (prefix +
                route.path.replace(globalParamRegexp, (match, param) => {
                    const [key] = param.split(".");
                    return params[key];
                }));
        }
        currentPath() {
            let result = this.mode === "history" ? window.location.pathname : window.location.hash.slice(1);
            return result || "/";
        }
        match(path) {
            for (let routeId of this.routeIds) {
                let route = this.routes[routeId];
                let params = this.getRouteParams(route, path);
                if (params) {
                    return {
                        type: "match",
                        route: route,
                        params: params,
                    };
                }
            }
            return { type: "nomatch" };
        }
        async matchAndApplyRules(path) {
            const result = this.match(path);
            if (result.type === "match") {
                return this.applyRules(result);
            }
            return result;
        }
        async applyRules(matchResult) {
            const route = matchResult.route;
            if (route.redirect) {
                const path = this.destToPath(route.redirect);
                return this.matchAndApplyRules(path);
            }
            if (route.beforeRouteEnter) {
                const result = await route.beforeRouteEnter({
                    env: this.env,
                    from: this.currentRoute,
                    to: route,
                });
                if (result === false) {
                    return { type: "cancelled" };
                }
                else if (result !== true) {
                    // we want to navigate to another destination
                    const path = this.destToPath(result);
                    return this.matchAndApplyRules(path);
                }
            }
            return matchResult;
        }
        getRouteParams(route, path) {
            if (route.path === "*") {
                return {};
            }
            if (path.startsWith("#")) {
                path = path.slice(1);
            }
            const paramsMatch = path.match(route.extractionRegExp);
            if (!paramsMatch) {
                return false;
            }
            const result = {};
            route.params.forEach((param, index) => {
                const [key, suffix] = param.split(".");
                const paramValue = paramsMatch[index + 1];
                if (suffix === "number") {
                    return (result[key] = parseInt(paramValue, 10));
                }
                return (result[key] = paramValue);
            });
            return result;
        }
    }
    function findParams(str) {
        const result = [];
        let m;
        do {
            m = globalParamRegexp.exec(str);
            if (m) {
                result.push(m[1]);
            }
        } while (m);
        return result;
    }
    function escapeRegExp(str) {
        return str.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    }
    function makeExtractionRegExp(path) {
        // replace param strings with capture groups so that we can build a regex to match over the path
        const extractionString = path
            .split(paramRegexp)
            .map((part, index) => {
            return index % 2 ? "(.*)" : escapeRegExp(part);
        })
            .join("");
        // Example: /home/{{param1}}/{{param2}} => ^\/home\/(.*)\/(.*)$
        return new RegExp(`^${extractionString}$`);
    }

    /**
     * This file is the main file packaged by rollup (see rollup.config.js).  From
     * this file, we export all public owl elements.
     *
     * Note that dynamic values, such as a date or a commit hash are added by rollup
     */
    const Context$1 = Context;
    const useState$1 = useState;
    const core = { EventBus, Observer };
    const router = { Router, RouteComponent, Link };
    const Store$1 = Store;
    const utils = _utils;
    const tags = _tags;
    const misc = { AsyncRoot, Portal };
    const hooks$1 = Object.assign({}, _hooks, {
        useContext: useContext,
        useDispatch: useDispatch,
        useGetters: useGetters,
        useStore: useStore,
    });
    const __info__ = {};

    exports.Component = Component;
    exports.Context = Context$1;
    exports.QWeb = QWeb;
    exports.Store = Store$1;
    exports.__info__ = __info__;
    exports.browser = browser;
    exports.config = config;
    exports.core = core;
    exports.hooks = hooks$1;
    exports.misc = misc;
    exports.mount = mount;
    exports.router = router;
    exports.tags = tags;
    exports.useState = useState$1;
    exports.utils = utils;


    __info__.version = '1.2.6';
    __info__.date = '2021-05-19T10:28:32.429Z';
    __info__.hash = 'e838781';
    __info__.url = 'https://github.com/odoo/owl';


}(this.owl = this.owl || {}));
