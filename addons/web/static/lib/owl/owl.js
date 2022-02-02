(function (exports) {
    'use strict';

    function filterOutModifiersFromData(dataList) {
        dataList = dataList.slice();
        const modifiers = [];
        let elm;
        while ((elm = dataList[0]) && typeof elm === "string") {
            modifiers.push(dataList.shift());
        }
        return { modifiers, data: dataList };
    }
    const config = {
        // whether or not blockdom should normalize DOM whenever a block is created.
        // Normalizing dom mean removing empty text nodes (or containing only spaces)
        shouldNormalizeDom: true,
        // this is the main event handler. Every event handler registered with blockdom
        // will go through this function, giving it the data registered in the block
        // and the event
        mainEventHandler: (data, ev, currentTarget) => {
            if (typeof data === "function") {
                data(ev);
            }
            else if (Array.isArray(data)) {
                data = filterOutModifiersFromData(data).data;
                data[0](data[1], ev);
            }
            return false;
        },
    };

    // -----------------------------------------------------------------------------
    // Toggler node
    // -----------------------------------------------------------------------------
    class VToggler {
        constructor(key, child) {
            this.key = key;
            this.child = child;
        }
        mount(parent, afterNode) {
            this.parentEl = parent;
            this.child.mount(parent, afterNode);
        }
        moveBefore(other, afterNode) {
            this.child.moveBefore(other ? other.child : null, afterNode);
        }
        patch(other, withBeforeRemove) {
            if (this === other) {
                return;
            }
            let child1 = this.child;
            let child2 = other.child;
            if (this.key === other.key) {
                child1.patch(child2, withBeforeRemove);
            }
            else {
                child2.mount(this.parentEl, child1.firstNode());
                if (withBeforeRemove) {
                    child1.beforeRemove();
                }
                child1.remove();
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
    }
    function toggler(key, child) {
        return new VToggler(key, child);
    }

    const { setAttribute: elemSetAttribute, removeAttribute } = Element.prototype;
    const tokenList = DOMTokenList.prototype;
    const tokenListAdd = tokenList.add;
    const tokenListRemove = tokenList.remove;
    const isArray = Array.isArray;
    const { split, trim } = String.prototype;
    const wordRegexp = /\s+/;
    /**
     * We regroup here all code related to updating attributes in a very loose sense:
     * attributes, properties and classs are all managed by the functions in this
     * file.
     */
    function setAttribute(key, value) {
        switch (value) {
            case false:
            case undefined:
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
        return function (value) {
            setAttribute.call(this, attr, value);
        };
    }
    function attrsSetter(attrs) {
        if (isArray(attrs)) {
            setAttribute.call(this, attrs[0], attrs[1]);
        }
        else {
            for (let k in attrs) {
                setAttribute.call(this, k, attrs[k]);
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
                setAttribute.call(this, name, val);
            }
            else {
                removeAttribute.call(this, oldAttrs[0]);
                setAttribute.call(this, name, val);
            }
        }
        else {
            for (let k in oldAttrs) {
                if (!(k in attrs)) {
                    removeAttribute.call(this, k);
                }
            }
            for (let k in attrs) {
                const val = attrs[k];
                if (val !== oldAttrs[k]) {
                    setAttribute.call(this, k, val);
                }
            }
        }
    }
    function toClassObj(expr) {
        const result = {};
        switch (typeof expr) {
            case "string":
                // we transform here a list of classes into an object:
                //  'hey you' becomes {hey: true, you: true}
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
                // this is already an object but we may need to split keys:
                // {'a': true, 'b c': true} should become {a: true, b: true, c: true}
                for (let key in expr) {
                    const value = expr[key];
                    if (value) {
                        const words = split.call(key, wordRegexp);
                        for (let word of words) {
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
    function setClass(val) {
        val = val === "" ? {} : toClassObj(val);
        // add classes
        const cl = this.classList;
        for (let c in val) {
            tokenListAdd.call(cl, c);
        }
    }
    function updateClass(val, oldVal) {
        oldVal = oldVal === "" ? {} : toClassObj(oldVal);
        val = val === "" ? {} : toClassObj(val);
        const cl = this.classList;
        // remove classes
        for (let c in oldVal) {
            if (!(c in val)) {
                tokenListRemove.call(cl, c);
            }
        }
        // add classes
        for (let c in val) {
            if (!(c in oldVal)) {
                tokenListAdd.call(cl, c);
            }
        }
    }
    function makePropSetter(name) {
        return function setProp(value) {
            this[name] = value;
        };
    }
    function isProp(tag, key) {
        switch (tag) {
            case "input":
                return (key === "checked" ||
                    key === "indeterminate" ||
                    key === "value" ||
                    key === "readonly" ||
                    key === "disabled");
            case "option":
                return key === "selected" || key === "disabled";
            case "textarea":
                return key === "value" || key === "readonly" || key === "disabled";
            case "select":
                return key === "value" || key === "disabled";
            case "button":
            case "optgroup":
                return key === "disabled";
        }
        return false;
    }

    function createEventHandler(rawEvent) {
        const eventName = rawEvent.split(".")[0];
        const capture = rawEvent.includes(".capture");
        if (rawEvent.includes(".synthetic")) {
            return createSyntheticHandler(eventName, capture);
        }
        else {
            return createElementHandler(eventName, capture);
        }
    }
    // Native listener
    let nextNativeEventId = 1;
    function createElementHandler(evName, capture = false) {
        let eventKey = `__event__${evName}_${nextNativeEventId++}`;
        if (capture) {
            eventKey = `${eventKey}_capture`;
        }
        function listener(ev) {
            const currentTarget = ev.currentTarget;
            if (!currentTarget || !document.contains(currentTarget))
                return;
            const data = currentTarget[eventKey];
            if (!data)
                return;
            config.mainEventHandler(data, ev, currentTarget);
        }
        function setup(data) {
            this[eventKey] = data;
            this.addEventListener(evName, listener, { capture });
        }
        function update(data) {
            this[eventKey] = data;
        }
        return { setup, update };
    }
    // Synthetic handler: a form of event delegation that allows placing only one
    // listener per event type.
    let nextSyntheticEventId = 1;
    function createSyntheticHandler(evName, capture = false) {
        let eventKey = `__event__synthetic_${evName}`;
        if (capture) {
            eventKey = `${eventKey}_capture`;
        }
        setupSyntheticEvent(evName, eventKey, capture);
        const currentId = nextSyntheticEventId++;
        function setup(data) {
            const _data = this[eventKey] || {};
            _data[currentId] = data;
            this[eventKey] = _data;
        }
        return { setup, update: setup };
    }
    function nativeToSyntheticEvent(eventKey, event) {
        let dom = event.target;
        while (dom !== null) {
            const _data = dom[eventKey];
            if (_data) {
                for (const data of Object.values(_data)) {
                    const stopped = config.mainEventHandler(data, event, dom);
                    if (stopped)
                        return;
                }
            }
            dom = dom.parentNode;
        }
    }
    const CONFIGURED_SYNTHETIC_EVENTS = {};
    function setupSyntheticEvent(evName, eventKey, capture = false) {
        if (CONFIGURED_SYNTHETIC_EVENTS[eventKey]) {
            return;
        }
        document.addEventListener(evName, (event) => nativeToSyntheticEvent(eventKey, event), {
            capture,
        });
        CONFIGURED_SYNTHETIC_EVENTS[eventKey] = true;
    }

    const getDescriptor$3 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
    const nodeProto$4 = Node.prototype;
    const nodeInsertBefore$3 = nodeProto$4.insertBefore;
    const nodeSetTextContent$1 = getDescriptor$3(nodeProto$4, "textContent").set;
    const nodeRemoveChild$3 = nodeProto$4.removeChild;
    // -----------------------------------------------------------------------------
    // Multi NODE
    // -----------------------------------------------------------------------------
    class VMulti {
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
                }
                else {
                    const childAnchor = document.createTextNode("");
                    anchors[i] = childAnchor;
                    nodeInsertBefore$3.call(parent, childAnchor, afterNode);
                }
            }
            this.anchors = anchors;
            this.parentEl = parent;
        }
        moveBefore(other, afterNode) {
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
                    child.moveBefore(null, afterNode);
                }
                else {
                    const anchor = anchors[i];
                    nodeInsertBefore$3.call(parent, anchor, afterNode);
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
                    }
                    else {
                        const afterNode = vn1.firstNode();
                        const anchor = document.createTextNode("");
                        anchors[i] = anchor;
                        nodeInsertBefore$3.call(parentEl, anchor, afterNode);
                        if (withBeforeRemove) {
                            vn1.beforeRemove();
                        }
                        vn1.remove();
                        children1[i] = undefined;
                    }
                }
                else if (vn2) {
                    children1[i] = vn2;
                    const anchor = anchors[i];
                    vn2.mount(parentEl, anchor);
                    nodeRemoveChild$3.call(parentEl, anchor);
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
                nodeSetTextContent$1.call(parentEl, "");
            }
            else {
                const children = this.children;
                const anchors = this.anchors;
                for (let i = 0, l = children.length; i < l; i++) {
                    const child = children[i];
                    if (child) {
                        child.remove();
                    }
                    else {
                        nodeRemoveChild$3.call(parentEl, anchors[i]);
                    }
                }
            }
        }
        firstNode() {
            const child = this.children[0];
            return child ? child.firstNode() : this.anchors[0];
        }
        toString() {
            return this.children.map((c) => (c ? c.toString() : "")).join("");
        }
    }
    function multi(children) {
        return new VMulti(children);
    }

    const getDescriptor$2 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
    const nodeProto$3 = Node.prototype;
    const characterDataProto$1 = CharacterData.prototype;
    const nodeInsertBefore$2 = nodeProto$3.insertBefore;
    const characterDataSetData$1 = getDescriptor$2(characterDataProto$1, "data").set;
    const nodeRemoveChild$2 = nodeProto$3.removeChild;
    class VSimpleNode {
        constructor(text) {
            this.text = text;
        }
        mountNode(node, parent, afterNode) {
            this.parentEl = parent;
            nodeInsertBefore$2.call(parent, node, afterNode);
            this.el = node;
        }
        moveBefore(other, afterNode) {
            const target = other ? other.el : afterNode;
            nodeInsertBefore$2.call(this.parentEl, this.el, target);
        }
        beforeRemove() { }
        remove() {
            nodeRemoveChild$2.call(this.parentEl, this.el);
        }
        firstNode() {
            return this.el;
        }
        toString() {
            return this.text;
        }
    }
    class VText$1 extends VSimpleNode {
        mount(parent, afterNode) {
            this.mountNode(document.createTextNode(toText(this.text)), parent, afterNode);
        }
        patch(other) {
            const text2 = other.text;
            if (this.text !== text2) {
                characterDataSetData$1.call(this.el, toText(text2));
                this.text = text2;
            }
        }
    }
    class VComment extends VSimpleNode {
        mount(parent, afterNode) {
            this.mountNode(document.createComment(toText(this.text)), parent, afterNode);
        }
        patch() { }
    }
    function text(str) {
        return new VText$1(str);
    }
    function comment(str) {
        return new VComment(str);
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

    const getDescriptor$1 = (o, p) => Object.getOwnPropertyDescriptor(o, p);
    const nodeProto$2 = Node.prototype;
    const elementProto = Element.prototype;
    const characterDataProto = CharacterData.prototype;
    const characterDataSetData = getDescriptor$1(characterDataProto, "data").set;
    const nodeGetFirstChild = getDescriptor$1(nodeProto$2, "firstChild").get;
    const nodeGetNextSibling = getDescriptor$1(nodeProto$2, "nextSibling").get;
    const NO_OP$1 = () => { };
    const cache$1 = {};
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
    function createBlock(str) {
        if (str in cache$1) {
            return cache$1[str];
        }
        // step 0: prepare html base element
        const doc = new DOMParser().parseFromString(`<t>${str}</t>`, "text/xml");
        const node = doc.firstChild.firstChild;
        if (config.shouldNormalizeDom) {
            normalizeNode(node);
        }
        // step 1: prepare intermediate tree
        const tree = buildTree(node);
        // step 2: prepare block context
        const context = buildContext(tree);
        // step 3: build the final block class
        const template = tree.el;
        const Block = buildBlock(template, context);
        cache$1[str] = Block;
        return Block;
    }
    // -----------------------------------------------------------------------------
    // Helper
    // -----------------------------------------------------------------------------
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
                // HTMLElement
                let currentNS = domParentTree && domParentTree.currentNS;
                const tagName = node.tagName;
                let el = undefined;
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
                const attrs = node.attributes;
                const ns = attrs.getNamedItem("block-ns");
                if (ns) {
                    attrs.removeNamedItem("block-ns");
                    currentNS = ns.value;
                }
                if (!el) {
                    el = currentNS
                        ? document.createElementNS(currentNS, tagName)
                        : document.createElement(tagName);
                }
                if (el instanceof Element) {
                    for (let i = 0; i < attrs.length; i++) {
                        const attrName = attrs[i].name;
                        const attrValue = attrs[i].value;
                        if (attrName.startsWith("block-handler-")) {
                            const idx = parseInt(attrName.slice(14), 10);
                            info.push({
                                type: "handler",
                                idx,
                                event: attrValue,
                            });
                        }
                        else if (attrName.startsWith("block-attribute-")) {
                            const idx = parseInt(attrName.slice(16), 10);
                            info.push({
                                type: "attribute",
                                idx,
                                name: attrValue,
                                tag: tagName,
                            });
                        }
                        else if (attrName === "block-attributes") {
                            info.push({
                                type: "attributes",
                                idx: parseInt(attrValue, 10),
                            });
                        }
                        else if (attrName === "block-ref") {
                            info.push({
                                type: "ref",
                                idx: parseInt(attrValue, 10),
                            });
                        }
                        else {
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
                    currentNS,
                };
                if (node.firstChild) {
                    const childNode = node.childNodes[0];
                    if (node.childNodes.length === 1 &&
                        childNode.nodeType === Node.ELEMENT_NODE &&
                        childNode.tagName.startsWith("block-child-")) {
                        const tagName = childNode.tagName;
                        const index = parseInt(tagName.slice(12), 10);
                        info.push({ idx: index, type: "child", isOnlyChild: true });
                    }
                    else {
                        tree.firstChild = buildTree(node.firstChild, tree, tree);
                        el.appendChild(tree.firstChild.el);
                        let curNode = node.firstChild;
                        let curTree = tree.firstChild;
                        while ((curNode = curNode.nextSibling)) {
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
            case Node.TEXT_NODE:
            case Node.COMMENT_NODE: {
                // text node or comment node
                const el = node.nodeType === Node.TEXT_NODE
                    ? document.createTextNode(node.textContent)
                    : document.createComment(node.textContent);
                return {
                    parent: parent,
                    firstChild: null,
                    nextSibling: null,
                    el,
                    info: [],
                    refN: 0,
                    currentNS: null,
                };
            }
        }
        throw new Error("boom");
    }
    function addRef(tree) {
        tree.isRef = true;
        do {
            tree.refN++;
        } while ((tree = tree.parent));
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
            //node
            if (isRef) {
                for (let info of tree.info) {
                    info.refIdx = initialIdx;
                }
                tree.refIdx = initialIdx;
                updateCtx(ctx, tree);
                fromIdx++;
            }
            // right
            if (nextSibling) {
                const idx = fromIdx + firstChild;
                ctx.collectors.push({ idx, prevIdx: initialIdx, getVal: nodeGetNextSibling });
                buildContext(tree.nextSibling, ctx, idx);
            }
            // left
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
                        updateData: setText,
                    });
                    break;
                case "child":
                    if (info.isOnlyChild) {
                        // tree is the parentnode here
                        ctx.children[info.idx] = {
                            parentRefIdx: info.refIdx,
                            isOnlyChild: true,
                        };
                    }
                    else {
                        // tree is the anchor text node
                        ctx.children[info.idx] = {
                            parentRefIdx: parentTree(tree).refIdx,
                            afterRefIdx: info.refIdx,
                        };
                    }
                    break;
                case "attribute": {
                    const refIdx = info.refIdx;
                    let updater;
                    let setter;
                    if (isProp(info.tag, info.name)) {
                        const setProp = makePropSetter(info.name);
                        setter = setProp;
                        updater = setProp;
                    }
                    else if (info.name === "class") {
                        setter = setClass;
                        updater = updateClass;
                    }
                    else {
                        setter = createAttrUpdater(info.name);
                        updater = setter;
                    }
                    ctx.locations.push({
                        idx: info.idx,
                        refIdx,
                        setData: setter,
                        updateData: updater,
                    });
                    break;
                }
                case "attributes":
                    ctx.locations.push({
                        idx: info.idx,
                        refIdx: info.refIdx,
                        setData: attrsSetter,
                        updateData: attrsUpdater,
                    });
                    break;
                case "handler": {
                    const { setup, update } = createEventHandler(info.event);
                    ctx.locations.push({
                        idx: info.idx,
                        refIdx: info.refIdx,
                        setData: setup,
                        updateData: update,
                    });
                    break;
                }
                case "ref":
                    ctx.cbRefs.push(info.idx);
                    ctx.locations.push({
                        idx: info.idx,
                        refIdx: info.refIdx,
                        setData: setRef,
                        updateData: NO_OP$1,
                    });
            }
        }
    }
    // -----------------------------------------------------------------------------
    // building the concrete block class
    // -----------------------------------------------------------------------------
    function buildBlock(template, ctx) {
        let B = createBlockClass(template, ctx);
        if (ctx.cbRefs.length) {
            const refs = ctx.cbRefs;
            B = class extends B {
                remove() {
                    super.remove();
                    for (let ref of refs) {
                        let fn = this.data[ref];
                        fn(null);
                    }
                }
            };
        }
        if (ctx.children.length) {
            B = class extends B {
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
        const { refN, collectors, children } = ctx;
        const colN = collectors.length;
        ctx.locations.sort((a, b) => a.idx - b.idx);
        const locations = ctx.locations.map((loc) => ({
            refIdx: loc.refIdx,
            setData: loc.setData,
            updateData: loc.updateData,
        }));
        const locN = locations.length;
        const childN = children.length;
        const childrenLocs = children;
        const isDynamic = refN > 0;
        // these values are defined here to make them faster to lookup in the class
        // block scope
        const nodeCloneNode = nodeProto$2.cloneNode;
        const nodeInsertBefore = nodeProto$2.insertBefore;
        const elementRemove = elementProto.remove;
        return class Block {
            constructor(data) {
                this.data = data;
            }
            beforeRemove() { }
            remove() {
                elementRemove.call(this.el);
            }
            firstNode() {
                return this.el;
            }
            moveBefore(other, afterNode) {
                const target = other ? other.el : afterNode;
                nodeInsertBefore.call(this.parentEl, this.el, target);
            }
            mount(parent, afterNode) {
                const el = nodeCloneNode.call(template, true);
                nodeInsertBefore.call(parent, el, afterNode);
                if (isDynamic) {
                    // collecting references
                    const refs = new Array(refN);
                    this.refs = refs;
                    refs[0] = el;
                    for (let i = 0; i < colN; i++) {
                        const w = collectors[i];
                        refs[w.idx] = w.getVal.call(refs[w.prevIdx]);
                    }
                    // applying data to all update points
                    if (locN) {
                        const data = this.data;
                        for (let i = 0; i < locN; i++) {
                            const loc = locations[i];
                            loc.setData.call(refs[loc.refIdx], data[i]);
                        }
                    }
                    // preparing all children
                    if (childN) {
                        const children = this.children;
                        for (let i = 0; i < childN; i++) {
                            const child = children[i];
                            if (child) {
                                const loc = childrenLocs[i];
                                const afterNode = loc.afterRefIdx ? refs[loc.afterRefIdx] : null;
                                child.isOnlyChild = loc.isOnlyChild;
                                child.mount(refs[loc.parentRefIdx], afterNode);
                            }
                        }
                    }
                }
                this.el = el;
                this.parentEl = parent;
            }
            patch(other, withBeforeRemove) {
                if (this === other) {
                    return;
                }
                const refs = this.refs;
                // update texts/attributes/
                if (locN) {
                    const data1 = this.data;
                    const data2 = other.data;
                    for (let i = 0; i < locN; i++) {
                        const val1 = data1[i];
                        const val2 = data2[i];
                        if (val1 !== val2) {
                            const loc = locations[i];
                            loc.updateData.call(refs[loc.refIdx], val2, val1);
                        }
                    }
                    this.data = data2;
                }
                // update children
                if (childN) {
                    let children1 = this.children;
                    const children2 = other.children;
                    for (let i = 0; i < childN; i++) {
                        const child1 = children1[i];
                        const child2 = children2[i];
                        if (child1) {
                            if (child2) {
                                child1.patch(child2, withBeforeRemove);
                            }
                            else {
                                if (withBeforeRemove) {
                                    child1.beforeRemove();
                                }
                                child1.remove();
                                children1[i] = undefined;
                            }
                        }
                        else if (child2) {
                            const loc = childrenLocs[i];
                            const afterNode = loc.afterRefIdx ? refs[loc.afterRefIdx] : null;
                            child2.mount(refs[loc.parentRefIdx], afterNode);
                            children1[i] = child2;
                        }
                    }
                }
            }
            toString() {
                const div = document.createElement("div");
                this.mount(div, null);
                return div.innerHTML;
            }
        };
    }
    function setText(value) {
        characterDataSetData.call(this, toText(value));
    }
    function setRef(fn) {
        fn(this);
    }

    const getDescriptor = (o, p) => Object.getOwnPropertyDescriptor(o, p);
    const nodeProto$1 = Node.prototype;
    const nodeInsertBefore$1 = nodeProto$1.insertBefore;
    const nodeAppendChild = nodeProto$1.appendChild;
    const nodeRemoveChild$1 = nodeProto$1.removeChild;
    const nodeSetTextContent = getDescriptor(nodeProto$1, "textContent").set;
    // -----------------------------------------------------------------------------
    // List Node
    // -----------------------------------------------------------------------------
    class VList {
        constructor(children) {
            this.children = children;
        }
        mount(parent, afterNode) {
            const children = this.children;
            const _anchor = document.createTextNode("");
            this.anchor = _anchor;
            nodeInsertBefore$1.call(parent, _anchor, afterNode);
            const l = children.length;
            if (l) {
                const mount = children[0].mount;
                for (let i = 0; i < l; i++) {
                    mount.call(children[i], parent, _anchor);
                }
            }
            this.parentEl = parent;
        }
        moveBefore(other, afterNode) {
            if (other) {
                const next = other.children[0];
                afterNode = (next ? next.firstNode() : other.anchor) || null;
            }
            const children = this.children;
            for (let i = 0, l = children.length; i < l; i++) {
                children[i].moveBefore(null, afterNode);
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
            const { mount: cMount, patch: cPatch, remove: cRemove, beforeRemove, moveBefore: cMoveBefore, firstNode: cFirstNode, } = proto;
            const _anchor = this.anchor;
            const isOnlyChild = this.isOnlyChild;
            const parent = this.parentEl;
            // fast path: no new child => only remove
            if (ch2.length === 0 && isOnlyChild) {
                if (withBeforeRemove) {
                    for (let i = 0, l = ch1.length; i < l; i++) {
                        beforeRemove.call(ch1[i]);
                    }
                }
                nodeSetTextContent.call(parent, "");
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
            let mapping = undefined;
            while (startIdx1 <= endIdx1 && startIdx2 <= endIdx2) {
                // -------------------------------------------------------------------
                if (startVn1 === null) {
                    startVn1 = ch1[++startIdx1];
                    continue;
                }
                // -------------------------------------------------------------------
                if (endVn1 === null) {
                    endVn1 = ch1[--endIdx1];
                    continue;
                }
                // -------------------------------------------------------------------
                let startKey1 = startVn1.key;
                let startKey2 = startVn2.key;
                if (startKey1 === startKey2) {
                    cPatch.call(startVn1, startVn2, withBeforeRemove);
                    ch2[startIdx2] = startVn1;
                    startVn1 = ch1[++startIdx1];
                    startVn2 = ch2[++startIdx2];
                    continue;
                }
                // -------------------------------------------------------------------
                let endKey1 = endVn1.key;
                let endKey2 = endVn2.key;
                if (endKey1 === endKey2) {
                    cPatch.call(endVn1, endVn2, withBeforeRemove);
                    ch2[endIdx2] = endVn1;
                    endVn1 = ch1[--endIdx1];
                    endVn2 = ch2[--endIdx2];
                    continue;
                }
                // -------------------------------------------------------------------
                if (startKey1 === endKey2) {
                    // bnode moved right
                    cPatch.call(startVn1, endVn2, withBeforeRemove);
                    ch2[endIdx2] = startVn1;
                    const nextChild = ch2[endIdx2 + 1];
                    cMoveBefore.call(startVn1, nextChild, _anchor);
                    startVn1 = ch1[++startIdx1];
                    endVn2 = ch2[--endIdx2];
                    continue;
                }
                // -------------------------------------------------------------------
                if (endKey1 === startKey2) {
                    // bnode moved left
                    cPatch.call(endVn1, startVn2, withBeforeRemove);
                    ch2[startIdx2] = endVn1;
                    const nextChild = ch1[startIdx1];
                    cMoveBefore.call(endVn1, nextChild, _anchor);
                    endVn1 = ch1[--endIdx1];
                    startVn2 = ch2[++startIdx2];
                    continue;
                }
                // -------------------------------------------------------------------
                mapping = mapping || createMapping(ch1, startIdx1, endIdx1);
                let idxInOld = mapping[startKey2];
                if (idxInOld === undefined) {
                    cMount.call(startVn2, parent, cFirstNode.call(startVn1) || null);
                }
                else {
                    const elmToMove = ch1[idxInOld];
                    cMoveBefore.call(elmToMove, startVn1, null);
                    cPatch.call(elmToMove, startVn2, withBeforeRemove);
                    ch2[startIdx2] = elmToMove;
                    ch1[idxInOld] = null;
                }
                startVn2 = ch2[++startIdx2];
            }
            // ---------------------------------------------------------------------
            if (startIdx1 <= endIdx1 || startIdx2 <= endIdx2) {
                if (startIdx1 > endIdx1) {
                    const nextChild = ch2[endIdx2 + 1];
                    const anchor = nextChild ? cFirstNode.call(nextChild) || null : _anchor;
                    for (let i = startIdx2; i <= endIdx2; i++) {
                        cMount.call(ch2[i], parent, anchor);
                    }
                }
                else {
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
                nodeSetTextContent.call(parentEl, "");
            }
            else {
                const children = this.children;
                const l = children.length;
                if (l) {
                    const remove = children[0].remove;
                    for (let i = 0; i < l; i++) {
                        remove.call(children[i]);
                    }
                }
                nodeRemoveChild$1.call(parentEl, anchor);
            }
        }
        firstNode() {
            const child = this.children[0];
            return child ? child.firstNode() : undefined;
        }
        toString() {
            return this.children.map((c) => c.toString()).join("");
        }
    }
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

    const nodeProto = Node.prototype;
    const nodeInsertBefore = nodeProto.insertBefore;
    const nodeRemoveChild = nodeProto.removeChild;
    class VHtml {
        constructor(html) {
            this.content = [];
            this.html = html;
        }
        mount(parent, afterNode) {
            this.parentEl = parent;
            const template = document.createElement("template");
            template.innerHTML = this.html;
            this.content = [...template.content.childNodes];
            for (let elem of this.content) {
                nodeInsertBefore.call(parent, elem, afterNode);
            }
            if (!this.content.length) {
                const textNode = document.createTextNode("");
                this.content.push(textNode);
                nodeInsertBefore.call(parent, textNode, afterNode);
            }
        }
        moveBefore(other, afterNode) {
            const target = other ? other.content[0] : afterNode;
            const parent = this.parentEl;
            for (let elem of this.content) {
                nodeInsertBefore.call(parent, elem, target);
            }
        }
        patch(other) {
            if (this === other) {
                return;
            }
            const html2 = other.html;
            if (this.html !== html2) {
                const parent = this.parentEl;
                // insert new html in front of current
                const afterNode = this.content[0];
                const template = document.createElement("template");
                template.innerHTML = html2;
                const content = [...template.content.childNodes];
                for (let elem of content) {
                    nodeInsertBefore.call(parent, elem, afterNode);
                }
                if (!content.length) {
                    const textNode = document.createTextNode("");
                    content.push(textNode);
                    nodeInsertBefore.call(parent, textNode, afterNode);
                }
                // remove current content
                this.remove();
                this.content = content;
                this.html = other.html;
            }
        }
        beforeRemove() { }
        remove() {
            const parent = this.parentEl;
            for (let elem of this.content) {
                nodeRemoveChild.call(parent, elem);
            }
        }
        firstNode() {
            return this.content[0];
        }
        toString() {
            return this.html;
        }
    }
    function html(str) {
        return new VHtml(str);
    }

    function mount$1(vnode, fixture, afterNode = null) {
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

    /**
     * Apply default props (only top level).
     *
     * Note that this method does modify in place the props
     */
    function applyDefaultProps(props, ComponentClass) {
        const defaultProps = ComponentClass.defaultProps;
        if (defaultProps) {
            for (let propName in defaultProps) {
                if (props[propName] === undefined) {
                    props[propName] = defaultProps[propName];
                }
            }
        }
    }
    //------------------------------------------------------------------------------
    // Prop validation helper
    //------------------------------------------------------------------------------
    function getPropDescription(staticProps) {
        if (staticProps instanceof Array) {
            return Object.fromEntries(staticProps.map((p) => (p.endsWith("?") ? [p.slice(0, -1), false] : [p, true])));
        }
        return staticProps || { "*": true };
    }
    /**
     * Validate the component props (or next props) against the (static) props
     * description.  This is potentially an expensive operation: it may needs to
     * visit recursively the props and all the children to check if they are valid.
     * This is why it is only done in 'dev' mode.
     */
    function validateProps(name, props, parent) {
        const ComponentClass = typeof name !== "string"
            ? name
            : parent.constructor.components[name];
        if (!ComponentClass) {
            // this is an error, wrong component. We silently return here instead so the
            // error is triggered by the usual path ('component' function)
            return;
        }
        applyDefaultProps(props, ComponentClass);
        let propsDef = getPropDescription(ComponentClass.props);
        const allowAdditionalProps = "*" in propsDef;
        for (let propName in propsDef) {
            if (propName === "*") {
                continue;
            }
            if (props[propName] === undefined) {
                if (propsDef[propName] && !propsDef[propName].optional) {
                    throw new Error(`Missing props '${propName}' (component '${ComponentClass.name}')`);
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
                e.message = `Invalid prop '${propName}' in component ${ComponentClass.name} (${e.message})`;
                throw e;
            }
            if (!isValid) {
                throw new Error(`Invalid Prop '${propName}' in component '${ComponentClass.name}'`);
            }
        }
        if (!allowAdditionalProps) {
            for (let propName in props) {
                if (!(propName in propsDef)) {
                    throw new Error(`Unknown prop '${propName}' given to component '${ComponentClass.name}'`);
                }
            }
        }
    }
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
     * Creates a batched version of a callback so that all calls to it in the same
     * microtick will only call the original callback once.
     *
     * @param callback the callback to batch
     * @returns a batched version of the original callback
     */
    function batched(callback) {
        let called = false;
        return async () => {
            // This await blocks all calls to the callback here, then releases them sequentially
            // in the next microtick. This line decides the granularity of the batch.
            await Promise.resolve();
            if (!called) {
                called = true;
                callback();
                // wait for all calls in this microtick to fall through before resetting "called"
                // so that only the first call to the batched function calls the original callback
                await Promise.resolve();
                called = false;
            }
        };
    }
    function validateTarget(target) {
        if (!(target instanceof HTMLElement)) {
            throw new Error("Cannot mount component: the target is not a valid DOM element");
        }
        if (!document.body.contains(target)) {
            throw new Error("Cannot mount a component on a detached dom node");
        }
    }
    class EventBus extends EventTarget {
        trigger(name, payload) {
            this.dispatchEvent(new CustomEvent(name, { detail: payload }));
        }
    }
    function whenReady(fn) {
        return new Promise(function (resolve) {
            if (document.readyState !== "loading") {
                resolve(true);
            }
            else {
                document.addEventListener("DOMContentLoaded", resolve, false);
            }
        }).then(fn || function () { });
    }
    async function loadFile(url) {
        const result = await fetch(url);
        if (!result.ok) {
            throw new Error("Error while fetching xml templates");
        }
        return await result.text();
    }
    /*
     * This class just transports the fact that a string is safe
     * to be injected as HTML. Overriding a JS primitive is quite painful though
     * so we need to redfine toString and valueOf.
     */
    class Markup extends String {
    }
    /*
     * Marks a value as safe, that is, a value that can be injected as HTML directly.
     * It should be used to wrap the value passed to a t-out directive to allow a raw rendering.
     */
    function markup(value) {
        return new Markup(value);
    }

    /**
     * This file contains utility functions that will be injected in each template,
     * to perform various useful tasks in the compiled code.
     */
    function withDefault(value, defaultValue) {
        return value === undefined || value === null || value === false ? defaultValue : value;
    }
    function callSlot(ctx, parent, key, name, dynamic, extra, defaultContent) {
        key = key + "__slot_" + name;
        const slots = (ctx.props && ctx.props.slots) || {};
        const { __render, __ctx, __scope } = slots[name] || {};
        const slotScope = Object.create(__ctx || {});
        if (__scope) {
            slotScope[__scope] = extra || {};
        }
        const slotBDom = __render ? __render.call(__ctx.__owl__.component, slotScope, parent, key) : null;
        if (defaultContent) {
            let child1 = undefined;
            let child2 = undefined;
            if (slotBDom) {
                child1 = dynamic ? toggler(name, slotBDom) : slotBDom;
            }
            else {
                child2 = defaultContent.call(ctx.__owl__.component, ctx, parent, key);
            }
            return multi([child1, child2]);
        }
        return slotBDom || text("");
    }
    function capture(ctx) {
        const component = ctx.__owl__.component;
        const result = Object.create(component);
        for (let k in ctx) {
            result[k] = ctx[k];
        }
        return result;
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
        }
        else if (collection) {
            values = Object.keys(collection);
            keys = Object.values(collection);
        }
        else {
            throw new Error("Invalid loop expression");
        }
        const n = values.length;
        return [keys, values, n, new Array(n)];
    }
    const isBoundary = Symbol("isBoundary");
    function setContextValue(ctx, key, value) {
        const ctx0 = ctx;
        while (!ctx.hasOwnProperty(key) && !ctx.hasOwnProperty(isBoundary)) {
            const newCtx = ctx.__proto__;
            if (!newCtx) {
                ctx = ctx0;
                break;
            }
            ctx = newCtx;
        }
        ctx[key] = value;
    }
    function toNumber(val) {
        const n = parseFloat(val);
        return isNaN(n) ? val : n;
    }
    function shallowEqual$1(l1, l2) {
        for (let i = 0, l = l1.length; i < l; i++) {
            if (l1[i] !== l2[i]) {
                return false;
            }
        }
        return true;
    }
    class LazyValue {
        constructor(fn, ctx, node) {
            this.fn = fn;
            this.ctx = capture(ctx);
            this.node = node;
        }
        evaluate() {
            return this.fn(this.ctx, this.node);
        }
        toString() {
            return this.evaluate().toString();
        }
    }
    /*
     * Safely outputs `value` as a block depending on the nature of `value`
     */
    function safeOutput(value) {
        if (!value) {
            return value;
        }
        let safeKey;
        let block;
        if (value instanceof Markup) {
            safeKey = `string_safe`;
            block = html(value);
        }
        else if (value instanceof LazyValue) {
            safeKey = `lazy_value`;
            block = value.evaluate();
        }
        else if (typeof value === "string") {
            safeKey = "string_unsafe";
            block = text(value);
        }
        else {
            // Assuming it is a block
            safeKey = "block_safe";
            block = value;
        }
        return toggler(safeKey, block);
    }
    let boundFunctions = new WeakMap();
    function bind(ctx, fn) {
        let component = ctx.__owl__.component;
        let boundFnMap = boundFunctions.get(component);
        if (!boundFnMap) {
            boundFnMap = new WeakMap();
            boundFunctions.set(component, boundFnMap);
        }
        let boundFn = boundFnMap.get(fn);
        if (!boundFn) {
            boundFn = fn.bind(component);
            boundFnMap.set(fn, boundFn);
        }
        return boundFn;
    }
    function multiRefSetter(refs, name) {
        let count = 0;
        return (el) => {
            if (el) {
                count++;
                if (count > 1) {
                    throw new Error("Cannot have 2 elements with same ref name at the same time");
                }
            }
            if (count === 0 || el) {
                refs[name] = el;
            }
        };
    }
    const UTILS = {
        withDefault,
        zero: Symbol("zero"),
        isBoundary,
        callSlot,
        capture,
        withKey,
        prepareList,
        setContextValue,
        multiRefSetter,
        shallowEqual: shallowEqual$1,
        toNumber,
        validateProps,
        LazyValue,
        safeOutput,
        bind,
    };

    const mainEventHandler = (data, ev, currentTarget) => {
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
                        }
                        else {
                            return stopped;
                        }
                    case "prevent":
                        if ((selfMode && isSelf) || !selfMode)
                            ev.preventDefault();
                        continue;
                    case "stop":
                        if ((selfMode && isSelf) || !selfMode)
                            ev.stopPropagation();
                        stopped = true;
                        continue;
                }
            }
        }
        // If handler is empty, the array slot 0 will also be empty, and data will not have the property 0
        // We check this rather than data[0] being truthy (or typeof function) so that it crashes
        // as expected when there is a handler expression that evaluates to a falsy value
        if (Object.hasOwnProperty.call(data, 0)) {
            const handler = data[0];
            if (typeof handler !== "function") {
                throw new Error(`Invalid handler (expected a function, received: '${handler}')`);
            }
            let node = data[1] ? data[1].__owl__ : null;
            if (node ? node.status === 1 /* MOUNTED */ : true) {
                handler.call(node ? node.component : null, ev);
            }
        }
        return stopped;
    };

    // Maps fibers to thrown errors
    const fibersInError = new WeakMap();
    const nodeErrorHandlers = new WeakMap();
    function _handleError(node, error, isFirstRound = false) {
        if (!node) {
            return false;
        }
        const fiber = node.fiber;
        if (fiber) {
            fibersInError.set(fiber, error);
        }
        const errorHandlers = nodeErrorHandlers.get(node);
        if (errorHandlers) {
            let stopped = false;
            // execute in the opposite order
            for (let i = errorHandlers.length - 1; i >= 0; i--) {
                try {
                    errorHandlers[i](error);
                    stopped = true;
                    break;
                }
                catch (e) {
                    error = e;
                }
            }
            if (stopped) {
                if (isFirstRound && fiber && fiber.node.fiber) {
                    fiber.root.counter--;
                }
                return true;
            }
        }
        return _handleError(node.parent, error);
    }
    function handleError(params) {
        const error = params.error;
        const node = "node" in params ? params.node : params.fiber.node;
        const fiber = "fiber" in params ? params.fiber : node.fiber;
        // resets the fibers on components if possible. This is important so that
        // new renderings can be properly included in the initial one, if any.
        let current = fiber;
        do {
            current.node.fiber = current;
            current = current.parent;
        } while (current);
        fibersInError.set(fiber.root, error);
        const handled = _handleError(node, error, true);
        if (!handled) {
            console.warn(`[Owl] Unhandled error. Destroying the root component`);
            try {
                node.app.destroy();
            }
            catch (e) {
                console.error(e);
            }
        }
    }

    function makeChildFiber(node, parent) {
        let current = node.fiber;
        if (current) {
            let root = parent.root;
            cancelFibers(root, current.children);
            current.root = null;
        }
        return new Fiber(node, parent);
    }
    function makeRootFiber(node) {
        let current = node.fiber;
        if (current) {
            let root = current.root;
            root.counter -= cancelFibers(root, current.children);
            current.children = [];
            root.counter++;
            current.bdom = null;
            if (fibersInError.has(current)) {
                fibersInError.delete(current);
                fibersInError.delete(root);
                current.appliedToDom = false;
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
    /**
     * @returns number of not-yet rendered fibers cancelled
     */
    function cancelFibers(root, fibers) {
        let result = 0;
        for (let fiber of fibers) {
            fiber.node.fiber = null;
            fiber.root = root;
            if (!fiber.bdom) {
                result++;
            }
            result += cancelFibers(root, fiber.children);
        }
        return result;
    }
    class Fiber {
        constructor(node, parent) {
            this.bdom = null;
            this.children = [];
            this.appliedToDom = false;
            this.node = node;
            this.parent = parent;
            if (parent) {
                const root = parent.root;
                root.counter++;
                this.root = root;
                parent.children.push(this);
            }
            else {
                this.root = this;
            }
        }
    }
    class RootFiber extends Fiber {
        constructor() {
            super(...arguments);
            this.counter = 1;
            // only add stuff in this if they have registered some hooks
            this.willPatch = [];
            this.patched = [];
            this.mounted = [];
            // A fiber is typically locked when it is completing and the patch has not, or is being applied.
            // i.e.: render triggered in onWillUnmount or in willPatch will be delayed
            this.locked = false;
        }
        complete() {
            const node = this.node;
            this.locked = true;
            let current = undefined;
            try {
                // Step 1: calling all willPatch lifecycle hooks
                for (current of this.willPatch) {
                    // because of the asynchronous nature of the rendering, some parts of the
                    // UI may have been rendered, then deleted in a followup rendering, and we
                    // do not want to call onWillPatch in that case.
                    let node = current.node;
                    if (node.fiber === current) {
                        const component = node.component;
                        for (let cb of node.willPatch) {
                            cb.call(component);
                        }
                    }
                }
                current = undefined;
                // Step 2: patching the dom
                node.patch();
                this.locked = false;
                // Step 4: calling all mounted lifecycle hooks
                let mountedFibers = this.mounted;
                while ((current = mountedFibers.pop())) {
                    current = current;
                    if (current.appliedToDom) {
                        for (let cb of current.node.mounted) {
                            cb();
                        }
                    }
                }
                // Step 5: calling all patched hooks
                let patchedFibers = this.patched;
                while ((current = patchedFibers.pop())) {
                    current = current;
                    if (current.appliedToDom) {
                        for (let cb of current.node.patched) {
                            cb();
                        }
                    }
                }
            }
            catch (e) {
                this.locked = false;
                handleError({ fiber: current || this, error: e });
            }
        }
    }
    class MountFiber extends RootFiber {
        constructor(node, target, options = {}) {
            super(node, null);
            this.target = target;
            this.position = options.position || "last-child";
        }
        complete() {
            let current = this;
            try {
                // validateTarget(this.target); NXOWL
                const node = this.node;
                if (node.bdom) {
                    // this is a complicated situation: if we mount a fiber with an existing
                    // bdom, this means that this same fiber was already completed, mounted,
                    // but a crash occurred in some mounted hook. Then, it was handled and
                    // the new rendering is being applied.
                    node.updateDom();
                }
                else {
                    node.bdom = this.bdom;
                    if (this.position === "last-child" || this.target.childNodes.length === 0) {
                        mount$1(node.bdom, this.target);
                    }
                    else {
                        const firstChild = this.target.childNodes[0];
                        mount$1(node.bdom, this.target, firstChild);
                    }
                }
                // unregistering the fiber before mounted since it can do another render
                // and that the current rendering is obviously completed
                node.fiber = null;
                node.status = 1 /* MOUNTED */;
                this.appliedToDom = true;
                let mountedFibers = this.mounted;
                while ((current = mountedFibers.pop())) {
                    if (current.appliedToDom) {
                        for (let cb of current.node.mounted) {
                            cb();
                        }
                    }
                }
            }
            catch (e) {
                handleError({ fiber: current, error: e });
            }
        }
    }

    let currentNode = null;
    function getCurrent() {
        if (!currentNode) {
            throw new Error("No active component (a hook function should only be called in 'setup')");
        }
        return currentNode;
    }
    function useComponent() {
        return currentNode.component;
    }
    function component(name, props, key, ctx, parent) {
        let node = ctx.children[key];
        let isDynamic = typeof name !== "string";
        if (node) {
            if (node.status < 1 /* MOUNTED */) {
                node.destroy();
                node = undefined;
            }
            else if (node.status === 2 /* DESTROYED */) {
                node = undefined;
            }
        }
        if (isDynamic && node && node.component.constructor !== name) {
            node = undefined;
        }
        const parentFiber = ctx.fiber;
        if (node) {
            node.updateAndRender(props, parentFiber);
        }
        else {
            // new component
            let C;
            if (isDynamic) {
                C = name;
            }
            else {
                C = parent.constructor.components[name];
                if (!C) {
                    throw new Error(`Cannot find the definition of component "${name}"`);
                }
            }
            node = new ComponentNode(C, props, ctx.app, ctx);
            ctx.children[key] = node;
            const fiber = makeChildFiber(node, parentFiber);
            node.initiateRender(fiber);
        }
        return node;
    }
    class ComponentNode {
        constructor(C, props, app, parent) {
            this.fiber = null;
            this.bdom = null;
            this.status = 0 /* NEW */;
            this.children = Object.create(null);
            this.refs = {};
            this.willStart = [];
            this.willUpdateProps = [];
            this.willUnmount = [];
            this.mounted = [];
            this.willPatch = [];
            this.patched = [];
            this.willDestroy = [];
            currentNode = this;
            this.app = app;
            this.parent = parent || null;
            this.level = parent ? parent.level + 1 : 0;
            applyDefaultProps(props, C);
            const env = (parent && parent.childEnv) || app.env;
            this.childEnv = env;
            this.component = new C(props, env, this);
            this.renderFn = app.getTemplate(C.template).bind(this.component, this.component, this);
            this.component.setup();
            currentNode = null;
        }
        mountComponent(target, options) {
            const fiber = new MountFiber(this, target, options);
            this.app.scheduler.addFiber(fiber);
            this.initiateRender(fiber);
        }
        async initiateRender(fiber) {
            this.fiber = fiber;
            if (this.mounted.length) {
                fiber.root.mounted.push(fiber);
            }
            const component = this.component;
            try {
                await Promise.all(this.willStart.map((f) => f.call(component)));
            }
            catch (e) {
                handleError({ node: this, error: e });
                return;
            }
            if (this.status === 0 /* NEW */ && this.fiber === fiber) {
                this._render(fiber);
            }
        }
        async render() {
            let current = this.fiber;
            if (current && current.root.locked) {
                await Promise.resolve();
                // situation may have changed after the microtask tick
                current = this.fiber;
            }
            if (current && !current.bdom && !fibersInError.has(current)) {
                return;
            }
            if (!this.bdom && !current) {
                return;
            }
            const fiber = makeRootFiber(this);
            this.fiber = fiber;
            this.app.scheduler.addFiber(fiber);
            await Promise.resolve();
            if (this.status === 2 /* DESTROYED */) {
                return;
            }
            // We only want to actually render the component if the following two
            // conditions are true:
            // * this.fiber: it could be null, in which case the render has been cancelled
            // * (current || !fiber.parent): if current is not null, this means that the
            //   render function was called when a render was already occurring. In this
            //   case, the pending rendering was cancelled, and the fiber needs to be
            //   rendered to complete the work.  If current is null, we check that the
            //   fiber has no parent.  If that is the case, the fiber was downgraded from
            //   a root fiber to a child fiber in the previous microtick, because it was
            //   embedded in a rendering coming from above, so the fiber will be rendered
            //   in the next microtick anyway, so we should not render it again.
            if (this.fiber === fiber && (current || !fiber.parent)) {
                this._render(fiber);
            }
        }
        _render(fiber) {
            try {
                fiber.bdom = this.renderFn();
                fiber.root.counter--;
            }
            catch (e) {
                handleError({ node: this, error: e });
            }
        }
        destroy() {
            let shouldRemove = this.status === 1 /* MOUNTED */;
            this._destroy();
            if (shouldRemove) {
                this.bdom.remove();
            }
        }
        _destroy() {
            const component = this.component;
            if (this.status === 1 /* MOUNTED */) {
                for (let cb of this.willUnmount) {
                    cb.call(component);
                }
            }
            for (let child of Object.values(this.children)) {
                child._destroy();
            }
            for (let cb of this.willDestroy) {
                cb.call(component);
            }
            this.status = 2 /* DESTROYED */;
        }
        async updateAndRender(props, parentFiber) {
            // update
            const fiber = makeChildFiber(this, parentFiber);
            this.fiber = fiber;
            const component = this.component;
            applyDefaultProps(props, component.constructor);
            const prom = Promise.all(this.willUpdateProps.map((f) => f.call(component, props)));
            await prom;
            if (fiber !== this.fiber) {
                return;
            }
            component.props = props;
            this._render(fiber);
            const parentRoot = parentFiber.root;
            if (this.willPatch.length) {
                parentRoot.willPatch.push(fiber);
            }
            if (this.patched.length) {
                parentRoot.patched.push(fiber);
            }
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
                // If the error was handled by some child component, we need to find it to
                // apply its change
                for (let k in this.children) {
                    const child = this.children[k];
                    child.updateDom();
                }
            }
            else {
                // if we get here, this is the component that handled the error and rerendered
                // itself, so we can simply patch the dom
                this.bdom.patch(this.fiber.bdom, false);
                this.fiber.appliedToDom = true;
                this.fiber = null;
            }
        }
        // ---------------------------------------------------------------------------
        // Block DOM methods
        // ---------------------------------------------------------------------------
        firstNode() {
            const bdom = this.bdom;
            return bdom ? bdom.firstNode() : undefined;
        }
        mount(parent, anchor) {
            const bdom = this.fiber.bdom;
            this.bdom = bdom;
            bdom.mount(parent, anchor);
            this.status = 1 /* MOUNTED */;
            this.fiber.appliedToDom = true;
            this.fiber = null;
        }
        moveBefore(other, afterNode) {
            this.bdom.moveBefore(other ? other.bdom : null, afterNode);
        }
        patch() {
            const hasChildren = Object.keys(this.children).length > 0;
            this.bdom.patch(this.fiber.bdom, hasChildren);
            if (hasChildren) {
                this.cleanOutdatedChildren();
            }
            this.fiber.appliedToDom = true;
            this.fiber = null;
        }
        beforeRemove() {
            this._destroy();
        }
        remove() {
            this.bdom.remove();
        }
        cleanOutdatedChildren() {
            const children = this.children;
            for (const key in children) {
                const node = children[key];
                const status = node.status;
                if (status !== 1 /* MOUNTED */) {
                    delete children[key];
                    if (status !== 2 /* DESTROYED */) {
                        node.destroy();
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------------
    //  hooks
    // -----------------------------------------------------------------------------
    function onWillStart(fn) {
        const node = getCurrent();
        node.willStart.push(fn.bind(node.component));
    }
    function onWillUpdateProps(fn) {
        const node = getCurrent();
        node.willUpdateProps.push(fn.bind(node.component));
    }
    function onMounted(fn) {
        const node = getCurrent();
        node.mounted.push(fn.bind(node.component));
    }
    function onWillPatch(fn) {
        const node = getCurrent();
        node.willPatch.unshift(fn.bind(node.component));
    }
    function onPatched(fn) {
        const node = getCurrent();
        node.patched.push(fn.bind(node.component));
    }
    function onWillUnmount(fn) {
        const node = getCurrent();
        node.willUnmount.unshift(fn.bind(node.component));
    }
    function onWillDestroy(fn) {
        const node = getCurrent();
        node.willDestroy.push(fn.bind(node.component));
    }
    function onWillRender(fn) {
        const node = getCurrent();
        const renderFn = node.renderFn;
        node.renderFn = () => {
            fn.call(node.component);
            return renderFn();
        };
    }
    function onRendered(fn) {
        const node = getCurrent();
        const renderFn = node.renderFn;
        node.renderFn = () => {
            const result = renderFn();
            fn.call(node.component);
            return result;
        };
    }
    function onError(callback) {
        const node = getCurrent();
        let handlers = nodeErrorHandlers.get(node);
        if (!handlers) {
            handlers = [];
            nodeErrorHandlers.set(node, handlers);
        }
        handlers.push(callback.bind(node.component));
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
        if (start === "`") {
            return {
                type: "TEMPLATE_STRING",
                value: s,
                replace(replacer) {
                    return s.replace(/\$\{(.*?)\}/g, (match, group) => {
                        return "${" + replacer(group) + "}";
                    });
                },
            };
        }
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
    const isLeftSeparator = (token) => token && (token.type === "LEFT_BRACE" || token.type === "COMMA");
    const isRightSeparator = (token) => token && (token.type === "RIGHT_BRACE" || token.type === "COMMA");
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
    function compileExprToArray(expr) {
        const localVars = new Set();
        const tokens = tokenize(expr);
        let i = 0;
        let stack = []; // to track last opening [ or {
        while (i < tokens.length) {
            let token = tokens[i];
            let prevToken = tokens[i - 1];
            let nextToken = tokens[i + 1];
            let groupType = stack[stack.length - 1];
            switch (token.type) {
                case "LEFT_BRACE":
                case "LEFT_BRACKET":
                    stack.push(token.type);
                    break;
                case "RIGHT_BRACE":
                case "RIGHT_BRACKET":
                    stack.pop();
            }
            let isVar = token.type === "SYMBOL" && !RESERVED_WORDS.includes(token.value);
            if (token.type === "SYMBOL" && !RESERVED_WORDS.includes(token.value)) {
                if (prevToken) {
                    // normalize missing tokens: {a} should be equivalent to {a:a}
                    if (groupType === "LEFT_BRACE" &&
                        isLeftSeparator(prevToken) &&
                        isRightSeparator(nextToken)) {
                        tokens.splice(i + 1, 0, { type: "COLON", value: ":" }, { ...token });
                        nextToken = tokens[i + 1];
                    }
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
            if (token.type === "TEMPLATE_STRING") {
                token.value = token.replace((expr) => compileExpr(expr));
            }
            if (nextToken && nextToken.type === "OPERATOR" && nextToken.value === "=>") {
                if (token.type === "RIGHT_PAREN") {
                    let j = i - 1;
                    while (j > 0 && tokens[j].type !== "LEFT_PAREN") {
                        if (tokens[j].type === "SYMBOL" && tokens[j].originalValue) {
                            tokens[j].value = tokens[j].originalValue;
                            localVars.add(tokens[j].value); //] = { id: tokens[j].value, expr: tokens[j].value };
                        }
                        j--;
                    }
                }
                else {
                    localVars.add(token.value); //] = { id: token.value, expr: token.value };
                }
            }
            if (isVar) {
                token.varName = token.value;
                if (!localVars.has(token.value)) {
                    token.originalValue = token.value;
                    token.value = `ctx['${token.value}']`;
                }
            }
            i++;
        }
        // Mark all variables that have been used locally.
        // This assumes the expression has only one scope (incorrect but "good enough for now")
        for (const token of tokens) {
            if (token.type === "SYMBOL" && token.varName && localVars.has(token.value)) {
                token.originalValue = token.value;
                token.value = `_${token.value}`;
                token.isLocal = true;
            }
        }
        return tokens;
    }
    function compileExpr(expr) {
        return compileExprToArray(expr)
            .map((t) => t.value)
            .join("");
    }
    const INTERP_REGEXP = /\{\{.*?\}\}/g;
    const INTERP_GROUP_REGEXP = /\{\{.*?\}\}/g;
    function interpolate(s) {
        let matches = s.match(INTERP_REGEXP);
        if (matches && matches[0].length === s.length) {
            return `(${compileExpr(s.slice(2, -2))})`;
        }
        let r = s.replace(INTERP_GROUP_REGEXP, (s) => "${" + compileExpr(s.slice(2, -2)) + "}");
        return "`" + r + "`";
    }

    // using a non-html document so that <inner/outer>HTML serializes as XML instead
    // of HTML (as we will parse it as xml later)
    const xmlDoc = document.implementation.createDocument(null, null, null);
    const MODS = new Set(["stop", "capture", "prevent", "self", "synthetic"]);
    // -----------------------------------------------------------------------------
    // BlockDescription
    // -----------------------------------------------------------------------------
    class BlockDescription {
        constructor(target, type) {
            this.dynamicTagName = null;
            this.isRoot = false;
            this.hasDynamicChildren = false;
            this.children = [];
            this.data = [];
            this.childNumber = 0;
            this.parentVar = "";
            this.id = BlockDescription.nextBlockId++;
            this.varName = "b" + this.id;
            this.blockName = "block" + this.id;
            this.target = target;
            this.type = type;
        }
        static generateId(prefix) {
            this.nextDataIds[prefix] = (this.nextDataIds[prefix] || 0) + 1;
            return prefix + this.nextDataIds[prefix];
        }
        insertData(str, prefix = "d") {
            const id = BlockDescription.generateId(prefix);
            this.target.addLine(`let ${id} = ${str};`);
            return this.data.push(id) - 1;
        }
        insert(dom) {
            if (this.currentDom) {
                this.currentDom.appendChild(dom);
            }
            else {
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
            }
            else if (this.type === "list") {
                return `list(c_block${this.id})`;
            }
            return expr;
        }
        asXmlString() {
            // Can't use outerHTML on text/comment nodes
            // append dom to any element and use innerHTML instead
            const t = xmlDoc.createElement("t");
            t.appendChild(this.dom);
            return t.innerHTML;
        }
    }
    BlockDescription.nextBlockId = 1;
    BlockDescription.nextDataIds = {};
    function createContext(parentCtx, params) {
        return Object.assign({
            block: null,
            index: 0,
            forceNewBlock: true,
            translate: parentCtx.translate,
            tKeyExpr: null,
            nameSpace: parentCtx.nameSpace,
            tModelSelectedExpr: parentCtx.tModelSelectedExpr,
        }, params);
    }
    class CodeTarget {
        constructor(name) {
            this.indentLevel = 0;
            this.loopLevel = 0;
            this.code = [];
            this.hasRoot = false;
            this.hasCache = false;
            this.hasRef = false;
            // maps ref name to [id, expr]
            this.refInfo = {};
            this.shouldProtectScope = false;
            this.name = name;
        }
        addLine(line, idx) {
            const prefix = new Array(this.indentLevel + 2).join("  ");
            if (idx === undefined) {
                this.code.push(prefix + line);
            }
            else {
                this.code.splice(idx, 0, prefix + line);
            }
        }
        generateCode() {
            let result = [];
            result.push(`function ${this.name}(ctx, node, key = "") {`);
            if (this.hasRef) {
                result.push(`  const refs = ctx.__owl__.refs;`);
                for (let name in this.refInfo) {
                    const [id, expr] = this.refInfo[name];
                    result.push(`  const ${id} = ${expr};`);
                }
            }
            if (this.shouldProtectScope) {
                result.push(`  ctx = Object.create(ctx);`);
                result.push(`  ctx[isBoundary] = 1`);
            }
            if (this.hasCache) {
                result.push(`  let cache = ctx.cache || {};`);
                result.push(`  let nextCache = ctx.cache = {};`);
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
    }
    const TRANSLATABLE_ATTRS = ["label", "title", "placeholder", "alt"];
    const translationRE = /^(\s*)([\s\S]+?)(\s*)$/;
    class CodeGenerator {
        constructor(ast, options) {
            this.blocks = [];
            this.ids = {};
            this.nextBlockId = 1;
            this.isDebug = false;
            this.targets = [];
            this.target = new CodeTarget("template");
            this.staticCalls = [];
            this.helpers = new Set();
            this.translateFn = options.translateFn || ((s) => s);
            this.translatableAttributes = options.translatableAttributes || TRANSLATABLE_ATTRS;
            this.hasSafeContext = options.hasSafeContext || false;
            this.dev = options.dev || false;
            this.ast = ast;
            this.templateName = options.name;
        }
        generateCode() {
            const ast = this.ast;
            this.isDebug = ast.type === 12 /* TDebug */;
            BlockDescription.nextBlockId = 1;
            BlockDescription.nextDataIds = {};
            this.compileAST(ast, {
                block: null,
                index: 0,
                forceNewBlock: false,
                isLast: true,
                translate: true,
                tKeyExpr: null,
            });
            // define blocks and utility functions
            let mainCode = [
                `  let { text, createBlock, list, multi, html, toggler, component, comment } = bdom;`,
            ];
            if (this.helpers.size) {
                mainCode.push(`let { ${[...this.helpers].join(", ")} } = helpers;`);
            }
            if (this.templateName) {
                mainCode.push(`// Template name: "${this.templateName}"`);
            }
            for (let { id, template } of this.staticCalls) {
                mainCode.push(`const ${id} = getTemplate(${template});`);
            }
            // define all blocks
            if (this.blocks.length) {
                mainCode.push(``);
                for (let block of this.blocks) {
                    if (block.dom) {
                        let xmlString = block.asXmlString();
                        if (block.dynamicTagName) {
                            xmlString = xmlString.replace(/^<\w+/, `<\${tag || '${block.dom.nodeName}'}`);
                            xmlString = xmlString.replace(/\w+>$/, `\${tag || '${block.dom.nodeName}'}>`);
                            mainCode.push(`let ${block.blockName} = tag => createBlock(\`${xmlString}\`);`);
                        }
                        else {
                            mainCode.push(`let ${block.blockName} = createBlock(\`${xmlString}\`);`);
                        }
                    }
                }
            }
            // define all slots/defaultcontent function
            if (this.targets.length) {
                for (let fn of this.targets) {
                    mainCode.push("");
                    mainCode = mainCode.concat(fn.generateCode());
                }
            }
            // generate main code
            mainCode.push("");
            mainCode = mainCode.concat("return " + this.target.generateCode());
            const code = mainCode.join("\n  ");
            if (this.isDebug) {
                const msg = `[Owl Debug]\n${code}`;
                console.log(msg);
            }
            return code;
        }
        compileInNewTarget(prefix, ast, ctx) {
            const name = this.generateId(prefix);
            const initialTarget = this.target;
            const target = new CodeTarget(name);
            this.targets.push(target);
            this.target = target;
            const subCtx = createContext(ctx);
            this.compileAST(ast, subCtx);
            this.target = initialTarget;
            return name;
        }
        addLine(line) {
            this.target.addLine(line);
        }
        generateId(prefix = "") {
            this.ids[prefix] = (this.ids[prefix] || 0) + 1;
            return prefix + this.ids[prefix];
        }
        insertAnchor(block) {
            const tag = `block-child-${block.children.length}`;
            const anchor = xmlDoc.createElement(tag);
            block.insert(anchor);
        }
        createBlock(parentBlock, type, ctx) {
            const hasRoot = this.target.hasRoot;
            const block = new BlockDescription(this.target, type);
            if (!hasRoot && !ctx.preventRoot) {
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
            const tKeyExpr = ctx.tKeyExpr;
            if (block.parentVar) {
                let keyArg = `key${this.target.loopLevel}`;
                if (tKeyExpr) {
                    keyArg = `${tKeyExpr} + ${keyArg}`;
                }
                this.helpers.add("withKey");
                this.addLine(`${block.parentVar}[${ctx.index}] = withKey(${blockExpr}, ${keyArg});`);
                return;
            }
            if (tKeyExpr) {
                blockExpr = `toggler(${tKeyExpr}, ${blockExpr})`;
            }
            if (block.isRoot && !ctx.preventRoot) {
                this.addLine(`return ${blockExpr};`);
            }
            else {
                this.addLine(`let ${block.varName} = ${blockExpr};`);
            }
        }
        /**
         * Captures variables that are used inside of an expression. This is useful
         * because in compiled code, almost all variables are accessed through the ctx
         * object. In the case of functions, that lookup in the context can be delayed
         * which can cause issues if the value has changed since the function was
         * defined.
         *
         * @param expr the expression to capture
         * @param forceCapture whether the expression should capture its scope even if
         *  it doesn't contain a function. Useful when the expression will be used as
         *  a function body.
         * @returns a new expression that uses the captured values
         */
        captureExpression(expr, forceCapture = false) {
            if (!forceCapture && !expr.includes("=>")) {
                return compileExpr(expr);
            }
            const tokens = compileExprToArray(expr);
            const mapping = new Map();
            return tokens
                .map((tok) => {
                if (tok.varName && !tok.isLocal) {
                    if (!mapping.has(tok.varName)) {
                        const varId = this.generateId("v");
                        mapping.set(tok.varName, varId);
                        this.addLine(`const ${varId} = ${tok.value};`);
                    }
                    tok.value = mapping.get(tok.varName);
                }
                return tok.value;
            })
                .join("");
        }
        compileAST(ast, ctx) {
            switch (ast.type) {
                case 1 /* Comment */:
                    this.compileComment(ast, ctx);
                    break;
                case 0 /* Text */:
                    this.compileText(ast, ctx);
                    break;
                case 2 /* DomNode */:
                    this.compileTDomNode(ast, ctx);
                    break;
                case 4 /* TEsc */:
                    this.compileTEsc(ast, ctx);
                    break;
                case 8 /* TOut */:
                    this.compileTOut(ast, ctx);
                    break;
                case 5 /* TIf */:
                    this.compileTIf(ast, ctx);
                    break;
                case 9 /* TForEach */:
                    this.compileTForeach(ast, ctx);
                    break;
                case 10 /* TKey */:
                    this.compileTKey(ast, ctx);
                    break;
                case 3 /* Multi */:
                    this.compileMulti(ast, ctx);
                    break;
                case 7 /* TCall */:
                    this.compileTCall(ast, ctx);
                    break;
                case 15 /* TCallBlock */:
                    this.compileTCallBlock(ast, ctx);
                    break;
                case 6 /* TSet */:
                    this.compileTSet(ast, ctx);
                    break;
                case 11 /* TComponent */:
                    this.compileComponent(ast, ctx);
                    break;
                case 12 /* TDebug */:
                    this.compileDebug(ast, ctx);
                    break;
                case 13 /* TLog */:
                    this.compileLog(ast, ctx);
                    break;
                case 14 /* TSlot */:
                    this.compileTSlot(ast, ctx);
                    break;
                case 16 /* TTranslation */:
                    this.compileTTranslation(ast, ctx);
                    break;
                case 17 /* TPortal */:
                    this.compileTPortal(ast, ctx);
            }
        }
        compileDebug(ast, ctx) {
            this.addLine(`debugger;`);
            if (ast.content) {
                this.compileAST(ast.content, ctx);
            }
        }
        compileLog(ast, ctx) {
            this.addLine(`console.log(${compileExpr(ast.expr)});`);
            if (ast.content) {
                this.compileAST(ast.content, ctx);
            }
        }
        compileComment(ast, ctx) {
            let { block, forceNewBlock } = ctx;
            const isNewBlock = !block || forceNewBlock;
            if (isNewBlock) {
                block = this.createBlock(block, "comment", ctx);
                this.insertBlock(`comment(\`${ast.value}\`)`, block, {
                    ...ctx,
                    forceNewBlock: forceNewBlock && !block,
                });
            }
            else {
                const text = xmlDoc.createComment(ast.value);
                block.insert(text);
            }
        }
        compileText(ast, ctx) {
            let { block, forceNewBlock } = ctx;
            let value = ast.value;
            if (value && ctx.translate !== false) {
                const match = translationRE.exec(value);
                value = match[1] + this.translateFn(match[2]) + match[3];
            }
            if (!block || forceNewBlock) {
                block = this.createBlock(block, "text", ctx);
                this.insertBlock(`text(\`${value}\`)`, block, {
                    ...ctx,
                    forceNewBlock: forceNewBlock && !block,
                });
            }
            else {
                const createFn = ast.type === 0 /* Text */ ? xmlDoc.createTextNode : xmlDoc.createComment;
                block.insert(createFn.call(xmlDoc, value));
            }
        }
        generateHandlerCode(rawEvent, handler) {
            const modifiers = rawEvent
                .split(".")
                .slice(1)
                .map((m) => {
                if (!MODS.has(m)) {
                    throw new Error(`Unknown event modifier: '${m}'`);
                }
                return `"${m}"`;
            });
            let modifiersCode = "";
            if (modifiers.length) {
                modifiersCode = `${modifiers.join(",")}, `;
            }
            return `[${modifiersCode}${this.captureExpression(handler)}, ctx]`;
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
                    const tagExpr = this.generateId("tag");
                    this.addLine(`let ${tagExpr} = ${compileExpr(ast.dynamicTag)};`);
                    block.dynamicTagName = tagExpr;
                }
            }
            // attributes
            const attrs = {};
            const nameSpace = ast.ns || ctx.nameSpace;
            if (nameSpace && isNewBlock) {
                // specific namespace uri
                attrs["block-ns"] = nameSpace;
            }
            for (let key in ast.attrs) {
                let expr, attrName;
                if (key.startsWith("t-attf")) {
                    expr = interpolate(ast.attrs[key]);
                    const idx = block.insertData(expr, "attr");
                    attrName = key.slice(7);
                    attrs["block-attribute-" + idx] = attrName;
                }
                else if (key.startsWith("t-att")) {
                    expr = compileExpr(ast.attrs[key]);
                    const idx = block.insertData(expr, "attr");
                    if (key === "t-att") {
                        attrs[`block-attributes`] = String(idx);
                    }
                    else {
                        attrName = key.slice(6);
                        attrs[`block-attribute-${idx}`] = attrName;
                    }
                }
                else if (this.translatableAttributes.includes(key)) {
                    attrs[key] = this.translateFn(ast.attrs[key]);
                }
                else {
                    expr = `"${ast.attrs[key]}"`;
                    attrName = key;
                    attrs[key] = ast.attrs[key];
                }
                if (attrName === "value" && ctx.tModelSelectedExpr) {
                    let selectedId = block.insertData(`${ctx.tModelSelectedExpr} === ${expr}`, "attr");
                    attrs[`block-attribute-${selectedId}`] = "selected";
                }
            }
            // event handlers
            for (let ev in ast.on) {
                const name = this.generateHandlerCode(ev, ast.on[ev]);
                const idx = block.insertData(name, "hdlr");
                attrs[`block-handler-${idx}`] = ev;
            }
            // t-ref
            if (ast.ref) {
                this.target.hasRef = true;
                const isDynamic = INTERP_REGEXP.test(ast.ref);
                if (isDynamic) {
                    const str = ast.ref.replace(INTERP_REGEXP, (expr) => "${" + this.captureExpression(expr.slice(2, -2), true) + "}");
                    const idx = block.insertData(`(el) => refs[\`${str}\`] = el`, "ref");
                    attrs["block-ref"] = String(idx);
                }
                else {
                    let name = ast.ref;
                    if (name in this.target.refInfo) {
                        // ref has already been defined
                        this.helpers.add("multiRefSetter");
                        const info = this.target.refInfo[name];
                        const index = block.data.push(info[0]) - 1;
                        attrs["block-ref"] = String(index);
                        info[1] = `multiRefSetter(refs, \`${name}\`)`;
                    }
                    else {
                        let id = this.generateId("ref");
                        this.target.refInfo[name] = [id, `(el) => refs[\`${name}\`] = el`];
                        const index = block.data.push(id) - 1;
                        attrs["block-ref"] = String(index);
                    }
                }
            }
            // t-model
            let tModelSelectedExpr;
            if (ast.model) {
                const { hasDynamicChildren, baseExpr, expr, eventType, shouldNumberize, shouldTrim, targetAttr, specialInitTargetAttr, } = ast.model;
                const baseExpression = compileExpr(baseExpr);
                const bExprId = this.generateId("bExpr");
                this.addLine(`const ${bExprId} = ${baseExpression};`);
                const expression = compileExpr(expr);
                const exprId = this.generateId("expr");
                this.addLine(`const ${exprId} = ${expression};`);
                const fullExpression = `${bExprId}[${exprId}]`;
                let idx;
                if (specialInitTargetAttr) {
                    idx = block.insertData(`${fullExpression} === '${attrs[targetAttr]}'`, "attr");
                    attrs[`block-attribute-${idx}`] = specialInitTargetAttr;
                }
                else if (hasDynamicChildren) {
                    const bValueId = this.generateId("bValue");
                    tModelSelectedExpr = `${bValueId}`;
                    this.addLine(`let ${tModelSelectedExpr} = ${fullExpression}`);
                }
                else {
                    idx = block.insertData(`${fullExpression}`, "attr");
                    attrs[`block-attribute-${idx}`] = targetAttr;
                }
                this.helpers.add("toNumber");
                let valueCode = `ev.target.${targetAttr}`;
                valueCode = shouldTrim ? `${valueCode}.trim()` : valueCode;
                valueCode = shouldNumberize ? `toNumber(${valueCode})` : valueCode;
                const handler = `[(ev) => { ${fullExpression} = ${valueCode}; }]`;
                idx = block.insertData(handler, "hdlr");
                attrs[`block-handler-${idx}`] = eventType;
            }
            const dom = xmlDoc.createElement(ast.tag);
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
                    const subCtx = createContext(ctx, {
                        block,
                        index: block.childNumber,
                        forceNewBlock: false,
                        isLast: ctx.isLast && i === children.length - 1,
                        tKeyExpr: ctx.tKeyExpr,
                        nameSpace,
                        tModelSelectedExpr,
                    });
                    this.compileAST(child, subCtx);
                }
                block.currentDom = initialDom;
            }
            if (isNewBlock) {
                this.insertBlock(`${block.blockName}(ddd)`, block, ctx);
                // may need to rewrite code!
                if (block.children.length && block.hasDynamicChildren) {
                    const code = this.target.code;
                    const children = block.children.slice();
                    let current = children.shift();
                    for (let i = codeIdx; i < code.length; i++) {
                        if (code[i].trimStart().startsWith(`let ${current.varName} `)) {
                            code[i] = code[i].replace(`let ${current.varName}`, current.varName);
                            current = children.shift();
                            if (!current)
                                break;
                        }
                    }
                    this.target.addLine(`let ${block.children.map((c) => c.varName)};`, codeIdx);
                }
            }
        }
        compileTEsc(ast, ctx) {
            let { block, forceNewBlock } = ctx;
            let expr;
            if (ast.expr === "0") {
                this.helpers.add("zero");
                expr = `ctx[zero]`;
            }
            else {
                expr = compileExpr(ast.expr);
                if (ast.defaultValue) {
                    this.helpers.add("withDefault");
                    expr = `withDefault(${expr}, \`${ast.defaultValue}\`)`;
                }
            }
            if (!block || forceNewBlock) {
                block = this.createBlock(block, "text", ctx);
                this.insertBlock(`text(${expr})`, block, { ...ctx, forceNewBlock: forceNewBlock && !block });
            }
            else {
                const idx = block.insertData(expr, "txt");
                const text = xmlDoc.createElement(`block-text-${idx}`);
                block.insert(text);
            }
        }
        compileTOut(ast, ctx) {
            let { block } = ctx;
            if (block) {
                this.insertAnchor(block);
            }
            block = this.createBlock(block, "html", ctx);
            this.helpers.add(ast.expr === "0" ? "zero" : "safeOutput");
            let expr = ast.expr === "0" ? "ctx[zero]" : `safeOutput(${compileExpr(ast.expr)})`;
            if (ast.body) {
                const nextId = BlockDescription.nextBlockId;
                const subCtx = createContext(ctx);
                this.compileAST({ type: 3 /* Multi */, content: ast.body }, subCtx);
                this.helpers.add("withDefault");
                expr = `withDefault(${expr}, b${nextId})`;
            }
            this.insertBlock(`${expr}`, block, ctx);
        }
        compileTIf(ast, ctx, nextNode) {
            let { block, forceNewBlock, index } = ctx;
            let currentIndex = index;
            const codeIdx = this.target.code.length;
            const isNewBlock = !block || (block.type !== "multi" && forceNewBlock);
            if (block) {
                block.hasDynamicChildren = true;
            }
            if (!block || (block.type !== "multi" && forceNewBlock)) {
                block = this.createBlock(block, "multi", ctx);
            }
            this.addLine(`if (${compileExpr(ast.condition)}) {`);
            this.target.indentLevel++;
            this.insertAnchor(block);
            const subCtx = createContext(ctx, { block, index: currentIndex });
            this.compileAST(ast.content, subCtx);
            this.target.indentLevel--;
            if (ast.tElif) {
                for (let clause of ast.tElif) {
                    this.addLine(`} else if (${compileExpr(clause.condition)}) {`);
                    this.target.indentLevel++;
                    this.insertAnchor(block);
                    const subCtx = createContext(ctx, { block, index: currentIndex });
                    this.compileAST(clause.content, subCtx);
                    this.target.indentLevel--;
                }
            }
            if (ast.tElse) {
                this.addLine(`} else {`);
                this.target.indentLevel++;
                this.insertAnchor(block);
                const subCtx = createContext(ctx, { block, index: currentIndex });
                this.compileAST(ast.tElse, subCtx);
                this.target.indentLevel--;
            }
            this.addLine("}");
            if (isNewBlock) {
                // note: this part is duplicated from end of compiledomnode:
                if (block.children.length) {
                    const code = this.target.code;
                    const children = block.children.slice();
                    let current = children.shift();
                    for (let i = codeIdx; i < code.length; i++) {
                        if (code[i].trimStart().startsWith(`let ${current.varName} `)) {
                            code[i] = code[i].replace(`let ${current.varName}`, current.varName);
                            current = children.shift();
                            if (!current)
                                break;
                        }
                    }
                    this.target.addLine(`let ${block.children.map((c) => c.varName)};`, codeIdx);
                }
                // note: this part is duplicated from end of compilemulti:
                const args = block.children.map((c) => c.varName).join(", ");
                this.insertBlock(`multi([${args}])`, block, ctx);
            }
        }
        compileTForeach(ast, ctx) {
            let { block } = ctx;
            if (block) {
                this.insertAnchor(block);
            }
            block = this.createBlock(block, "list", ctx);
            this.target.loopLevel++;
            const loopVar = `i${this.target.loopLevel}`;
            this.addLine(`ctx = Object.create(ctx);`);
            const vals = `v_block${block.id}`;
            const keys = `k_block${block.id}`;
            const l = `l_block${block.id}`;
            const c = `c_block${block.id}`;
            this.helpers.add("prepareList");
            this.addLine(`const [${keys}, ${vals}, ${l}, ${c}] = prepareList(${compileExpr(ast.collection)});`);
            // Throw errors on duplicate keys in dev mode
            if (this.dev) {
                this.addLine(`const keys${block.id} = new Set();`);
            }
            this.addLine(`for (let ${loopVar} = 0; ${loopVar} < ${l}; ${loopVar}++) {`);
            this.target.indentLevel++;
            this.addLine(`ctx[\`${ast.elem}\`] = ${vals}[${loopVar}];`);
            if (!ast.hasNoFirst) {
                this.addLine(`ctx[\`${ast.elem}_first\`] = ${loopVar} === 0;`);
            }
            if (!ast.hasNoLast) {
                this.addLine(`ctx[\`${ast.elem}_last\`] = ${loopVar} === ${vals}.length - 1;`);
            }
            if (!ast.hasNoIndex) {
                this.addLine(`ctx[\`${ast.elem}_index\`] = ${loopVar};`);
            }
            if (!ast.hasNoValue) {
                this.addLine(`ctx[\`${ast.elem}_value\`] = ${keys}[${loopVar}];`);
            }
            this.addLine(`let key${this.target.loopLevel} = ${ast.key ? compileExpr(ast.key) : loopVar};`);
            if (this.dev) {
                // Throw error on duplicate keys in dev mode
                this.addLine(`if (keys${block.id}.has(key${this.target.loopLevel})) { throw new Error(\`Got duplicate key in t-foreach: \${key${this.target.loopLevel}}\`)}`);
                this.addLine(`keys${block.id}.add(key${this.target.loopLevel});`);
            }
            let id;
            if (ast.memo) {
                this.target.hasCache = true;
                id = this.generateId();
                this.addLine(`let memo${id} = ${compileExpr(ast.memo)}`);
                this.addLine(`let vnode${id} = cache[key${this.target.loopLevel}];`);
                this.addLine(`if (vnode${id}) {`);
                this.target.indentLevel++;
                this.addLine(`if (shallowEqual(vnode${id}.memo, memo${id})) {`);
                this.target.indentLevel++;
                this.addLine(`${c}[${loopVar}] = vnode${id};`);
                this.addLine(`nextCache[key${this.target.loopLevel}] = vnode${id};`);
                this.addLine(`continue;`);
                this.target.indentLevel--;
                this.addLine("}");
                this.target.indentLevel--;
                this.addLine("}");
            }
            const subCtx = createContext(ctx, { block, index: loopVar });
            this.compileAST(ast.body, subCtx);
            if (ast.memo) {
                this.addLine(`nextCache[key${this.target.loopLevel}] = Object.assign(${c}[${loopVar}], {memo: memo${id}});`);
            }
            this.target.indentLevel--;
            this.target.loopLevel--;
            this.addLine(`}`);
            if (!ctx.isLast) {
                this.addLine(`ctx = ctx.__proto__;`);
            }
            this.insertBlock("l", block, ctx);
        }
        compileTKey(ast, ctx) {
            const tKeyExpr = this.generateId("tKey_");
            this.addLine(`const ${tKeyExpr} = ${compileExpr(ast.expr)};`);
            ctx = createContext(ctx, {
                tKeyExpr,
                block: ctx.block,
                index: ctx.index,
            });
            this.compileAST(ast.content, ctx);
        }
        compileMulti(ast, ctx) {
            let { block, forceNewBlock } = ctx;
            const isNewBlock = !block || forceNewBlock;
            let codeIdx = this.target.code.length;
            if (isNewBlock) {
                const n = ast.content.filter((c) => c.type !== 6 /* TSet */).length;
                if (n <= 1) {
                    for (let child of ast.content) {
                        this.compileAST(child, ctx);
                    }
                    return;
                }
                block = this.createBlock(block, "multi", ctx);
            }
            let index = 0;
            for (let i = 0, l = ast.content.length; i < l; i++) {
                const child = ast.content[i];
                const isTSet = child.type === 6 /* TSet */;
                const subCtx = createContext(ctx, {
                    block,
                    index,
                    forceNewBlock: !isTSet,
                    preventRoot: ctx.preventRoot,
                    isLast: ctx.isLast && i === l - 1,
                });
                this.compileAST(child, subCtx);
                if (!isTSet) {
                    index++;
                }
            }
            if (isNewBlock) {
                if (block.hasDynamicChildren) {
                    if (block.children.length) {
                        const code = this.target.code;
                        const children = block.children.slice();
                        let current = children.shift();
                        for (let i = codeIdx; i < code.length; i++) {
                            if (code[i].trimStart().startsWith(`let ${current.varName} `)) {
                                code[i] = code[i].replace(`let ${current.varName}`, current.varName);
                                current = children.shift();
                                if (!current)
                                    break;
                            }
                        }
                        this.target.addLine(`let ${block.children.map((c) => c.varName)};`, codeIdx);
                    }
                }
                const args = block.children.map((c) => c.varName).join(", ");
                this.insertBlock(`multi([${args}])`, block, ctx);
            }
        }
        compileTCall(ast, ctx) {
            let { block, forceNewBlock } = ctx;
            if (ast.body) {
                this.addLine(`ctx = Object.create(ctx);`);
                this.addLine(`ctx[isBoundary] = 1;`);
                this.helpers.add("isBoundary");
                const nextId = BlockDescription.nextBlockId;
                const subCtx = createContext(ctx, { preventRoot: true });
                this.compileAST({ type: 3 /* Multi */, content: ast.body }, subCtx);
                if (nextId !== BlockDescription.nextBlockId) {
                    this.helpers.add("zero");
                    this.addLine(`ctx[zero] = b${nextId};`);
                }
            }
            const isDynamic = INTERP_REGEXP.test(ast.name);
            const subTemplate = isDynamic ? interpolate(ast.name) : "`" + ast.name + "`";
            if (block) {
                if (!forceNewBlock) {
                    this.insertAnchor(block);
                }
            }
            const key = `key + \`${this.generateComponentKey()}\``;
            if (isDynamic) {
                const templateVar = this.generateId("template");
                this.addLine(`const ${templateVar} = ${subTemplate};`);
                block = this.createBlock(block, "multi", ctx);
                this.helpers.add("call");
                this.insertBlock(`call(this, ${templateVar}, ctx, node, ${key})`, block, {
                    ...ctx,
                    forceNewBlock: !block,
                });
            }
            else {
                const id = this.generateId(`callTemplate_`);
                this.helpers.add("getTemplate");
                this.staticCalls.push({ id, template: subTemplate });
                block = this.createBlock(block, "multi", ctx);
                this.insertBlock(`${id}.call(this, ctx, node, ${key})`, block, {
                    ...ctx,
                    forceNewBlock: !block,
                });
            }
            if (ast.body && !ctx.isLast) {
                this.addLine(`ctx = ctx.__proto__;`);
            }
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
        }
        compileTSet(ast, ctx) {
            this.target.shouldProtectScope = true;
            this.helpers.add("isBoundary").add("withDefault");
            const expr = ast.value ? compileExpr(ast.value || "") : "null";
            if (ast.body) {
                this.helpers.add("LazyValue");
                const bodyAst = { type: 3 /* Multi */, content: ast.body };
                const name = this.compileInNewTarget("value", bodyAst, ctx);
                let value = `new LazyValue(${name}, ctx, node)`;
                value = ast.value ? (value ? `withDefault(${expr}, ${value})` : expr) : value;
                this.addLine(`ctx[\`${ast.name}\`] = ${value};`);
            }
            else {
                let value;
                if (ast.defaultValue) {
                    if (ast.value) {
                        value = `withDefault(${expr}, \`${ast.defaultValue}\`)`;
                    }
                    else {
                        value = `\`${ast.defaultValue}\``;
                    }
                }
                else {
                    value = expr;
                }
                this.helpers.add("setContextValue");
                this.addLine(`setContextValue(ctx, "${ast.name}", ${value});`);
            }
        }
        generateComponentKey() {
            const parts = [this.generateId("__")];
            for (let i = 0; i < this.target.loopLevel; i++) {
                parts.push(`\${key${i + 1}}`);
            }
            return parts.join("__");
        }
        compileComponent(ast, ctx) {
            let { block } = ctx;
            // props
            const props = [];
            let hasSlotsProp = false;
            for (let propName in ast.props) {
                let propValue = this.captureExpression(ast.props[propName]) || undefined;
                if (propName.includes(".")) {
                    let [name, suffix] = propName.split(".");
                    if (suffix === "bind") {
                        this.helpers.add("bind");
                        propName = name;
                        propValue = `bind(ctx, ${propValue})`;
                    }
                    else {
                        throw new Error("Invalid prop suffix");
                    }
                }
                propName = /^[a-z_]+$/i.test(propName) ? propName : `'${propName}'`;
                props.push(`${propName}: ${propValue}`);
                if (propName === "slots") {
                    hasSlotsProp = true;
                }
            }
            // slots
            const hasSlot = !!Object.keys(ast.slots).length;
            let slotDef = "";
            if (hasSlot) {
                let ctxStr = "ctx";
                if (this.target.loopLevel || !this.hasSafeContext) {
                    ctxStr = this.generateId("ctx");
                    this.helpers.add("capture");
                    this.addLine(`const ${ctxStr} = capture(ctx);`);
                }
                let slotStr = [];
                for (let slotName in ast.slots) {
                    const slotAst = ast.slots[slotName].content;
                    const name = this.compileInNewTarget("slot", slotAst, ctx);
                    const params = [`__render: ${name}, __ctx: ${ctxStr}`];
                    const scope = ast.slots[slotName].scope;
                    if (scope) {
                        params.push(`__scope: "${scope}"`);
                    }
                    if (ast.slots[slotName].attrs) {
                        for (const [n, v] of Object.entries(ast.slots[slotName].attrs)) {
                            params.push(`${n}: ${compileExpr(v) || undefined}`);
                        }
                    }
                    const slotInfo = `{${params.join(", ")}}`;
                    slotStr.push(`'${slotName}': ${slotInfo}`);
                }
                slotDef = `{${slotStr.join(", ")}}`;
            }
            if (slotDef && !(ast.dynamicProps || hasSlotsProp)) {
                props.push(`slots: ${slotDef}`);
            }
            const propStr = `{${props.join(",")}}`;
            let propString = propStr;
            if (ast.dynamicProps) {
                if (!props.length) {
                    propString = `Object.assign({}, ${compileExpr(ast.dynamicProps)})`;
                }
                else {
                    propString = `Object.assign({}, ${compileExpr(ast.dynamicProps)}, ${propStr})`;
                }
            }
            let propVar;
            if ((slotDef && (ast.dynamicProps || hasSlotsProp)) || this.dev) {
                propVar = this.generateId("props");
                this.addLine(`const ${propVar} = ${propString};`);
                propString = propVar;
            }
            if (slotDef && (ast.dynamicProps || hasSlotsProp)) {
                this.addLine(`${propVar}.slots = Object.assign(${slotDef}, ${propVar}.slots)`);
            }
            // cmap key
            const key = this.generateComponentKey();
            let expr;
            if (ast.isDynamic) {
                expr = this.generateId("Comp");
                this.addLine(`let ${expr} = ${compileExpr(ast.name)};`);
            }
            else {
                expr = `\`${ast.name}\``;
            }
            if (this.dev) {
                this.addLine(`helpers.validateProps(${expr}, ${propVar}, ctx);`);
            }
            if (block && (ctx.forceNewBlock === false || ctx.tKeyExpr)) {
                // todo: check the forcenewblock condition
                this.insertAnchor(block);
            }
            let keyArg = `key + \`${key}\``;
            if (ctx.tKeyExpr) {
                keyArg = `${ctx.tKeyExpr} + ${keyArg}`;
            }
            const blockArgs = `${expr}, ${propString}, ${keyArg}, node, ctx`;
            let blockExpr = `component(${blockArgs})`;
            if (ast.isDynamic) {
                blockExpr = `toggler(${expr}, ${blockExpr})`;
            }
            block = this.createBlock(block, "multi", ctx);
            this.insertBlock(blockExpr, block, ctx);
        }
        compileTSlot(ast, ctx) {
            this.helpers.add("callSlot");
            let { block } = ctx;
            let blockString;
            let slotName;
            let dynamic = false;
            if (ast.name.match(INTERP_REGEXP)) {
                dynamic = true;
                slotName = interpolate(ast.name);
            }
            else {
                slotName = "'" + ast.name + "'";
            }
            let scope = null;
            if (ast.attrs) {
                const params = [];
                for (const [n, v] of Object.entries(ast.attrs)) {
                    params.push(`${n}: ${compileExpr(v) || undefined}`);
                }
                scope = `{${params.join(", ")}}`;
            }
            if (ast.defaultContent) {
                const name = this.compileInNewTarget("defaultContent", ast.defaultContent, ctx);
                blockString = `callSlot(ctx, node, key, ${slotName}, ${dynamic}, ${scope}, ${name})`;
            }
            else {
                if (dynamic) {
                    let name = this.generateId("slot");
                    this.addLine(`const ${name} = ${slotName};`);
                    blockString = `toggler(${name}, callSlot(ctx, node, key, ${name}), ${dynamic}, ${scope})`;
                }
                else {
                    blockString = `callSlot(ctx, node, key, ${slotName}, ${dynamic}, ${scope})`;
                }
            }
            if (block) {
                this.insertAnchor(block);
            }
            block = this.createBlock(block, "multi", ctx);
            this.insertBlock(blockString, block, { ...ctx, forceNewBlock: false });
        }
        compileTTranslation(ast, ctx) {
            if (ast.content) {
                this.compileAST(ast.content, Object.assign({}, ctx, { translate: false }));
            }
        }
        compileTPortal(ast, ctx) {
            this.helpers.add("Portal");
            let { block } = ctx;
            const name = this.compileInNewTarget("slot", ast.content, ctx);
            const key = this.generateComponentKey();
            let ctxStr = "ctx";
            if (this.target.loopLevel || !this.hasSafeContext) {
                ctxStr = this.generateId("ctx");
                this.helpers.add("capture");
                this.addLine(`const ${ctxStr} = capture(ctx);`);
            }
            const blockString = `component(Portal, {target: ${ast.target},slots: {'default': {__render: ${name}, __ctx: ${ctxStr}}}}, key + \`${key}\`, node, ctx)`;
            if (block) {
                this.insertAnchor(block);
            }
            block = this.createBlock(block, "multi", ctx);
            this.insertBlock(blockString, block, { ...ctx, forceNewBlock: false });
        }
    }

    // -----------------------------------------------------------------------------
    // AST Type definition
    // -----------------------------------------------------------------------------
    // -----------------------------------------------------------------------------
    // Parser
    // -----------------------------------------------------------------------------
    const cache = new WeakMap();
    function parse(xml) {
        if (typeof xml === "string") {
            const elem = parseXML$1(`<t>${xml}</t>`).firstChild;
            return _parse(elem);
        }
        let ast = cache.get(xml);
        if (!ast) {
            // we clone here the xml to prevent modifying it in place
            ast = _parse(xml.cloneNode(true));
            cache.set(xml, ast);
        }
        return ast;
    }
    function _parse(xml) {
        normalizeXML(xml);
        const ctx = { inPreTag: false, inSVG: false };
        return parseNode(xml, ctx) || { type: 0 /* Text */, value: "" };
    }
    function parseNode(node, ctx) {
        if (!(node instanceof Element)) {
            return parseTextCommentNode(node, ctx);
        }
        return (parseTDebugLog(node, ctx) ||
            parseTForEach(node, ctx) ||
            parseTIf(node, ctx) ||
            parseTPortal(node, ctx) ||
            parseTCall(node, ctx) ||
            parseTCallBlock(node) ||
            parseTEscNode(node, ctx) ||
            parseTKey(node, ctx) ||
            parseTTranslation(node, ctx) ||
            parseTSlot(node, ctx) ||
            parseTOutNode(node, ctx) ||
            parseComponent(node, ctx) ||
            parseDOMNode(node, ctx) ||
            parseTSetNode(node, ctx) ||
            parseTNode(node, ctx));
    }
    // -----------------------------------------------------------------------------
    // <t /> tag
    // -----------------------------------------------------------------------------
    function parseTNode(node, ctx) {
        if (node.tagName !== "t") {
            return null;
        }
        return parseChildNodes(node, ctx);
    }
    // -----------------------------------------------------------------------------
    // Text and Comment Nodes
    // -----------------------------------------------------------------------------
    const lineBreakRE = /[\r\n]/;
    const whitespaceRE = /\s+/g;
    function parseTextCommentNode(node, ctx) {
        if (node.nodeType === Node.TEXT_NODE) {
            let value = node.textContent || "";
            if (!ctx.inPreTag) {
                if (lineBreakRE.test(value) && !value.trim()) {
                    return null;
                }
                value = value.replace(whitespaceRE, " ");
            }
            return { type: 0 /* Text */, value };
        }
        else if (node.nodeType === Node.COMMENT_NODE) {
            return { type: 1 /* Comment */, value: node.textContent || "" };
        }
        return null;
    }
    // -----------------------------------------------------------------------------
    // debugging
    // -----------------------------------------------------------------------------
    function parseTDebugLog(node, ctx) {
        if (node.hasAttribute("t-debug")) {
            node.removeAttribute("t-debug");
            return {
                type: 12 /* TDebug */,
                content: parseNode(node, ctx),
            };
        }
        if (node.hasAttribute("t-log")) {
            const expr = node.getAttribute("t-log");
            node.removeAttribute("t-log");
            return {
                type: 13 /* TLog */,
                expr,
                content: parseNode(node, ctx),
            };
        }
        return null;
    }
    // -----------------------------------------------------------------------------
    // Regular dom node
    // -----------------------------------------------------------------------------
    const hasDotAtTheEnd = /\.[\w_]+\s*$/;
    const hasBracketsAtTheEnd = /\[[^\[]+\]\s*$/;
    const ROOT_SVG_TAGS = new Set(["svg", "g", "path"]);
    function parseDOMNode(node, ctx) {
        const { tagName } = node;
        const dynamicTag = node.getAttribute("t-tag");
        node.removeAttribute("t-tag");
        if (tagName === "t" && !dynamicTag) {
            return null;
        }
        ctx = Object.assign({}, ctx);
        if (tagName === "pre") {
            ctx.inPreTag = true;
        }
        const shouldAddSVGNS = ROOT_SVG_TAGS.has(tagName) && !ctx.inSVG;
        ctx.inSVG = ctx.inSVG || shouldAddSVGNS;
        const ns = shouldAddSVGNS ? "http://www.w3.org/2000/svg" : null;
        const ref = node.getAttribute("t-ref");
        node.removeAttribute("t-ref");
        const nodeAttrsNames = node.getAttributeNames();
        const attrs = {};
        const on = {};
        let model = null;
        for (let attr of nodeAttrsNames) {
            const value = node.getAttribute(attr);
            if (attr.startsWith("t-on")) {
                if (attr === "t-on") {
                    throw new Error("Missing event name with t-on directive");
                }
                on[attr.slice(5)] = value;
            }
            else if (attr.startsWith("t-model")) {
                if (!["input", "select", "textarea"].includes(tagName)) {
                    throw new Error("The t-model directive only works with <input>, <textarea> and <select>");
                }
                let baseExpr, expr;
                if (hasDotAtTheEnd.test(value)) {
                    const index = value.lastIndexOf(".");
                    baseExpr = value.slice(0, index);
                    expr = `'${value.slice(index + 1)}'`;
                }
                else if (hasBracketsAtTheEnd.test(value)) {
                    const index = value.lastIndexOf("[");
                    baseExpr = value.slice(0, index);
                    expr = value.slice(index + 1, -1);
                }
                else {
                    throw new Error(`Invalid t-model expression: "${value}" (it should be assignable)`);
                }
                const typeAttr = node.getAttribute("type");
                const isInput = tagName === "input";
                const isSelect = tagName === "select";
                const isTextarea = tagName === "textarea";
                const isCheckboxInput = isInput && typeAttr === "checkbox";
                const isRadioInput = isInput && typeAttr === "radio";
                const isOtherInput = isInput && !isCheckboxInput && !isRadioInput;
                const hasLazyMod = attr.includes(".lazy");
                const hasNumberMod = attr.includes(".number");
                const hasTrimMod = attr.includes(".trim");
                const eventType = isRadioInput ? "click" : isSelect || hasLazyMod ? "change" : "input";
                model = {
                    baseExpr,
                    expr,
                    targetAttr: isCheckboxInput ? "checked" : "value",
                    specialInitTargetAttr: isRadioInput ? "checked" : null,
                    eventType,
                    shouldTrim: hasTrimMod && (isOtherInput || isTextarea),
                    shouldNumberize: hasNumberMod && (isOtherInput || isTextarea),
                };
                if (isSelect) {
                    // don't pollute the original ctx
                    ctx = Object.assign({}, ctx);
                    ctx.tModelInfo = model;
                }
            }
            else if (attr !== "t-name") {
                if (attr.startsWith("t-") && !attr.startsWith("t-att")) {
                    throw new Error(`Unknown QWeb directive: '${attr}'`);
                }
                const tModel = ctx.tModelInfo;
                if (tModel && ["t-att-value", "t-attf-value"].includes(attr)) {
                    tModel.hasDynamicChildren = true;
                }
                attrs[attr] = value;
            }
        }
        const children = parseChildren(node, ctx);
        return {
            type: 2 /* DomNode */,
            tag: tagName,
            dynamicTag,
            attrs,
            on,
            ref,
            content: children,
            model,
            ns,
        };
    }
    // -----------------------------------------------------------------------------
    // t-esc
    // -----------------------------------------------------------------------------
    function parseTEscNode(node, ctx) {
        if (!node.hasAttribute("t-esc")) {
            return null;
        }
        const escValue = node.getAttribute("t-esc");
        node.removeAttribute("t-esc");
        const tesc = {
            type: 4 /* TEsc */,
            expr: escValue,
            defaultValue: node.textContent || "",
        };
        let ref = node.getAttribute("t-ref");
        node.removeAttribute("t-ref");
        const ast = parseNode(node, ctx);
        if (!ast) {
            return tesc;
        }
        if (ast.type === 2 /* DomNode */) {
            return {
                ...ast,
                ref,
                content: [tesc],
            };
        }
        if (ast.type === 11 /* TComponent */) {
            throw new Error("t-esc is not supported on Component nodes");
        }
        return tesc;
    }
    // -----------------------------------------------------------------------------
    // t-out
    // -----------------------------------------------------------------------------
    function parseTOutNode(node, ctx) {
        if (!node.hasAttribute("t-out") && !node.hasAttribute("t-raw")) {
            return null;
        }
        if (node.hasAttribute("t-raw")) {
            console.warn(`t-raw has been deprecated in favor of t-out. If the value to render is not wrapped by the "markup" function, it will be escaped`);
        }
        const expr = (node.getAttribute("t-out") || node.getAttribute("t-raw"));
        node.removeAttribute("t-out");
        node.removeAttribute("t-raw");
        const tOut = { type: 8 /* TOut */, expr, body: null };
        const ref = node.getAttribute("t-ref");
        node.removeAttribute("t-ref");
        const ast = parseNode(node, ctx);
        if (!ast) {
            return tOut;
        }
        if (ast.type === 2 /* DomNode */) {
            tOut.body = ast.content.length ? ast.content : null;
            return {
                ...ast,
                ref,
                content: [tOut],
            };
        }
        return tOut;
    }
    // -----------------------------------------------------------------------------
    // t-foreach and t-key
    // -----------------------------------------------------------------------------
    function parseTForEach(node, ctx) {
        if (!node.hasAttribute("t-foreach")) {
            return null;
        }
        const html = node.outerHTML;
        const collection = node.getAttribute("t-foreach");
        node.removeAttribute("t-foreach");
        const elem = node.getAttribute("t-as") || "";
        node.removeAttribute("t-as");
        const key = node.getAttribute("t-key");
        if (!key) {
            throw new Error(`"Directive t-foreach should always be used with a t-key!" (expression: t-foreach="${collection}" t-as="${elem}")`);
        }
        node.removeAttribute("t-key");
        const memo = node.getAttribute("t-memo") || "";
        node.removeAttribute("t-memo");
        const body = parseNode(node, ctx);
        if (!body) {
            return null;
        }
        const hasNoTCall = !html.includes("t-call");
        const hasNoFirst = hasNoTCall && !html.includes(`${elem}_first`);
        const hasNoLast = hasNoTCall && !html.includes(`${elem}_last`);
        const hasNoIndex = hasNoTCall && !html.includes(`${elem}_index`);
        const hasNoValue = hasNoTCall && !html.includes(`${elem}_value`);
        return {
            type: 9 /* TForEach */,
            collection,
            elem,
            body,
            memo,
            key,
            hasNoFirst,
            hasNoLast,
            hasNoIndex,
            hasNoValue,
        };
    }
    function parseTKey(node, ctx) {
        if (!node.hasAttribute("t-key")) {
            return null;
        }
        const key = node.getAttribute("t-key");
        node.removeAttribute("t-key");
        const body = parseNode(node, ctx);
        if (!body) {
            return null;
        }
        return { type: 10 /* TKey */, expr: key, content: body };
    }
    // -----------------------------------------------------------------------------
    // t-call
    // -----------------------------------------------------------------------------
    function parseTCall(node, ctx) {
        if (!node.hasAttribute("t-call")) {
            return null;
        }
        const subTemplate = node.getAttribute("t-call");
        node.removeAttribute("t-call");
        if (node.tagName !== "t") {
            const ast = parseNode(node, ctx);
            const tcall = { type: 7 /* TCall */, name: subTemplate, body: null };
            if (ast && ast.type === 2 /* DomNode */) {
                ast.content = [tcall];
                return ast;
            }
            if (ast && ast.type === 11 /* TComponent */) {
                return {
                    ...ast,
                    slots: { default: { content: tcall } },
                };
            }
        }
        const body = parseChildren(node, ctx);
        return {
            type: 7 /* TCall */,
            name: subTemplate,
            body: body.length ? body : null,
        };
    }
    // -----------------------------------------------------------------------------
    // t-call-block
    // -----------------------------------------------------------------------------
    function parseTCallBlock(node, ctx) {
        if (!node.hasAttribute("t-call-block")) {
            return null;
        }
        const name = node.getAttribute("t-call-block");
        return {
            type: 15 /* TCallBlock */,
            name,
        };
    }
    // -----------------------------------------------------------------------------
    // t-if
    // -----------------------------------------------------------------------------
    function parseTIf(node, ctx) {
        if (!node.hasAttribute("t-if")) {
            return null;
        }
        const condition = node.getAttribute("t-if");
        node.removeAttribute("t-if");
        const content = parseNode(node, ctx) || { type: 0 /* Text */, value: "" };
        let nextElement = node.nextElementSibling;
        // t-elifs
        const tElifs = [];
        while (nextElement && nextElement.hasAttribute("t-elif")) {
            const condition = nextElement.getAttribute("t-elif");
            nextElement.removeAttribute("t-elif");
            const tElif = parseNode(nextElement, ctx);
            const next = nextElement.nextElementSibling;
            nextElement.remove();
            nextElement = next;
            if (tElif) {
                tElifs.push({ condition, content: tElif });
            }
        }
        // t-else
        let tElse = null;
        if (nextElement && nextElement.hasAttribute("t-else")) {
            nextElement.removeAttribute("t-else");
            tElse = parseNode(nextElement, ctx);
            nextElement.remove();
        }
        return {
            type: 5 /* TIf */,
            condition,
            content,
            tElif: tElifs.length ? tElifs : null,
            tElse,
        };
    }
    // -----------------------------------------------------------------------------
    // t-set directive
    // -----------------------------------------------------------------------------
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
        return { type: 6 /* TSet */, name, value, defaultValue, body };
    }
    // -----------------------------------------------------------------------------
    // Components
    // -----------------------------------------------------------------------------
    // Error messages when trying to use an unsupported directive on a component
    const directiveErrorMap = new Map([
        ["t-on", "t-on is no longer supported on components. Consider passing a callback in props."],
        [
            "t-ref",
            "t-ref is no longer supported on components. Consider exposing only the public part of the component's API through a callback prop.",
        ],
        ["t-att", "t-att makes no sense on component: props are already treated as expressions"],
        [
            "t-attf",
            "t-attf is not supported on components: use template strings for string interpolation in props",
        ],
    ]);
    function parseComponent(node, ctx) {
        let name = node.tagName;
        const firstLetter = name[0];
        let isDynamic = node.hasAttribute("t-component");
        if (isDynamic && name !== "t") {
            throw new Error(`Directive 't-component' can only be used on <t> nodes (used on a <${name}>)`);
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
        const props = {};
        for (let name of node.getAttributeNames()) {
            const value = node.getAttribute(name);
            if (name.startsWith("t-")) {
                const message = directiveErrorMap.get(name.split("-").slice(0, 2).join("-"));
                throw new Error(message || `unsupported directive on Component: ${name}`);
            }
            else {
                props[name] = value;
            }
        }
        const slots = {};
        if (node.hasChildNodes()) {
            const clone = node.cloneNode(true);
            // named slots
            const slotNodes = Array.from(clone.querySelectorAll("[t-set-slot]"));
            for (let slotNode of slotNodes) {
                if (slotNode.tagName !== "t") {
                    throw new Error(`Directive 't-set-slot' can only be used on <t> nodes (used on a <${slotNode.tagName}>)`);
                }
                const name = slotNode.getAttribute("t-set-slot");
                // check if this is defined in a sub component (in which case it should
                // be ignored)
                let el = slotNode.parentElement;
                let isInSubComponent = false;
                while (el !== clone) {
                    if (el.hasAttribute("t-component") || el.tagName[0] === el.tagName[0].toUpperCase()) {
                        isInSubComponent = true;
                        break;
                    }
                    el = el.parentElement;
                }
                if (isInSubComponent) {
                    continue;
                }
                slotNode.removeAttribute("t-set-slot");
                slotNode.remove();
                const slotAst = parseNode(slotNode, ctx);
                if (slotAst) {
                    const slotInfo = { content: slotAst };
                    const attrs = {};
                    for (let attributeName of slotNode.getAttributeNames()) {
                        const value = slotNode.getAttribute(attributeName);
                        if (attributeName === "t-slot-scope") {
                            slotInfo.scope = value;
                            continue;
                        }
                        attrs[attributeName] = value;
                    }
                    if (Object.keys(attrs).length) {
                        slotInfo.attrs = attrs;
                    }
                    slots[name] = slotInfo;
                }
            }
            // default slot
            const defaultContent = parseChildNodes(clone, ctx);
            if (defaultContent) {
                slots.default = { content: defaultContent };
            }
        }
        return { type: 11 /* TComponent */, name, isDynamic, dynamicProps, props, slots };
    }
    // -----------------------------------------------------------------------------
    // Slots
    // -----------------------------------------------------------------------------
    function parseTSlot(node, ctx) {
        if (!node.hasAttribute("t-slot")) {
            return null;
        }
        const name = node.getAttribute("t-slot");
        node.removeAttribute("t-slot");
        const attrs = {};
        for (let attributeName of node.getAttributeNames()) {
            const value = node.getAttribute(attributeName);
            attrs[attributeName] = value;
        }
        return {
            type: 14 /* TSlot */,
            name,
            attrs,
            defaultContent: parseChildNodes(node, ctx),
        };
    }
    function parseTTranslation(node, ctx) {
        if (node.getAttribute("t-translation") !== "off") {
            return null;
        }
        node.removeAttribute("t-translation");
        return {
            type: 16 /* TTranslation */,
            content: parseNode(node, ctx),
        };
    }
    // -----------------------------------------------------------------------------
    // Portal
    // -----------------------------------------------------------------------------
    function parseTPortal(node, ctx) {
        if (!node.hasAttribute("t-portal")) {
            return null;
        }
        const target = node.getAttribute("t-portal");
        node.removeAttribute("t-portal");
        const content = parseNode(node, ctx);
        if (!content) {
            return {
                type: 0 /* Text */,
                value: "",
            };
        }
        return {
            type: 17 /* TPortal */,
            target,
            content,
        };
    }
    // -----------------------------------------------------------------------------
    // helpers
    // -----------------------------------------------------------------------------
    /**
     * Parse all the child nodes of a given node and return a list of ast elements
     */
    function parseChildren(node, ctx) {
        const children = [];
        for (let child of node.childNodes) {
            const childAst = parseNode(child, ctx);
            if (childAst) {
                if (childAst.type === 3 /* Multi */) {
                    children.push(...childAst.content);
                }
                else {
                    children.push(childAst);
                }
            }
        }
        return children;
    }
    /**
     * Parse all the child nodes of a given node and return an ast if possible.
     * In the case there are multiple children, they are wrapped in a astmulti.
     */
    function parseChildNodes(node, ctx) {
        const children = parseChildren(node, ctx);
        switch (children.length) {
            case 0:
                return null;
            case 1:
                return children[0];
            default:
                return { type: 3 /* Multi */, content: children };
        }
    }
    /**
     * Normalizes the content of an Element so that t-if/t-elif/t-else directives
     * immediately follow one another (by removing empty text nodes or comments).
     * Throws an error when a conditional branching statement is malformed. This
     * function modifies the Element in place.
     *
     * @param el the element containing the tree that should be normalized
     */
    function normalizeTIf(el) {
        let tbranch = el.querySelectorAll("[t-elif], [t-else]");
        for (let i = 0, ilen = tbranch.length; i < ilen; i++) {
            let node = tbranch[i];
            let prevElem = node.previousElementSibling;
            let pattr = (name) => prevElem.getAttribute(name);
            let nattr = (name) => +!!node.getAttribute(name);
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
     * Normalizes the content of an Element so that t-esc directives on components
     * are removed and instead places a <t t-esc=""> as the default slot of the
     * component. Also throws if the component already has content. This function
     * modifies the Element in place.
     *
     * @param el the element containing the tree that should be normalized
     */
    function normalizeTEsc(el) {
        const elements = [...el.querySelectorAll("[t-esc]")].filter((el) => el.tagName[0] === el.tagName[0].toUpperCase() || el.hasAttribute("t-component"));
        for (const el of elements) {
            if (el.childNodes.length) {
                throw new Error("Cannot have t-esc on a component that already has content");
            }
            const value = el.getAttribute("t-esc");
            el.removeAttribute("t-esc");
            const t = el.ownerDocument.createElement("t");
            if (value != null) {
                t.setAttribute("t-esc", value);
            }
            el.appendChild(t);
        }
    }
    /**
     * Normalizes the tree inside a given element and do some preliminary validation
     * on it. This function modifies the Element in place.
     *
     * @param el the element containing the tree that should be normalized
     */
    function normalizeXML(el) {
        normalizeTIf(el);
        normalizeTEsc(el);
    }
    /**
     * Parses an XML string into an XML document, throwing errors on parser errors
     * instead of returning an XML document containing the parseerror.
     *
     * @param xml the string to parse
     * @returns an XML document corresponding to the content of the string
     */
    function parseXML$1(xml) {
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

    function compile(template, options = {}) {
        // parsing
        const ast = parse(template);
        // some work
        const hasSafeContext = template instanceof Node
            ? !(template instanceof Element) || template.querySelector("[t-set], [t-call]") === null
            : !template.includes("t-set") && !template.includes("t-call");
        // code generation
        const codeGenerator = new CodeGenerator(ast, { ...options, hasSafeContext });
        const code = codeGenerator.generateCode();
        // template function
        return new Function("bdom, helpers", code);
    }

    const bdom = { text, createBlock, list, multi, html, toggler, component, comment };
    const globalTemplates = {};
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
    class TemplateSet {
        constructor(config = {}) {
            this.rawTemplates = Object.create(globalTemplates);
            this.templates = {};
            this.utils = Object.assign({}, UTILS, {
                call: (owner, subTemplate, ctx, parent, key) => {
                    const template = this.getTemplate(subTemplate);
                    return toggler(subTemplate, template.call(owner, ctx, parent, key));
                },
                getTemplate: (name) => this.getTemplate(name),
            });
            this.dev = config.dev || false;
            this.translateFn = config.translateFn;
            this.translatableAttributes = config.translatableAttributes;
            if (config.templates) {
                this.addTemplates(config.templates);
            }
        }
        addTemplate(name, template, options = {}) {
            if (name in this.rawTemplates && !options.allowDuplicate) {
                throw new Error(`Template ${name} already defined`);
            }
            this.rawTemplates[name] = template;
        }
        addTemplates(xml, options = {}) {
            if (!xml) {
                // empty string
                return;
            }
            xml = xml instanceof Document ? xml : parseXML(xml);
            for (const template of xml.querySelectorAll("[t-name]")) {
                const name = template.getAttribute("t-name");
                this.addTemplate(name, template, options);
            }
        }
        getTemplate(name) {
            if (!(name in this.templates)) {
                const rawTemplate = this.rawTemplates[name];
                if (rawTemplate === undefined) {
                    throw new Error(`Missing template: "${name}"`);
                }
                const templateFn = this._compileTemplate(name, rawTemplate);
                // first add a function to lazily get the template, in case there is a
                // recursive call to the template name
                const templates = this.templates;
                this.templates[name] = function (context, parent) {
                    return templates[name].call(this, context, parent);
                };
                const template = templateFn(bdom, this.utils);
                this.templates[name] = template;
            }
            return this.templates[name];
        }
        _compileTemplate(name, template) {
            return compile(template, {
                name,
                dev: this.dev,
                translateFn: this.translateFn,
                translatableAttributes: this.translatableAttributes,
            });
        }
    }
    // -----------------------------------------------------------------------------
    //  xml tag helper
    // -----------------------------------------------------------------------------
    function xml(...args) {
        const name = `__template__${xml.nextId++}`;
        const value = String.raw(...args);
        globalTemplates[name] = value;
        return name;
    }
    xml.nextId = 1;

    class Component {
        constructor(props, env, node) {
            this.props = props;
            this.env = env;
            this.__owl__ = node;
        }
        setup() { }
        render() {
            this.__owl__.render();
        }
    }
    Component.template = "";

    const VText = text("").constructor;
    class VPortal extends VText {
        constructor(selector, realBDom) {
            super("");
            this.target = null;
            this.selector = selector;
            this.realBDom = realBDom;
        }
        mount(parent, anchor) {
            super.mount(parent, anchor);
            this.target = document.querySelector(this.selector);
            if (!this.target) {
                let el = this.el;
                while (el && el.parentElement instanceof HTMLElement) {
                    el = el.parentElement;
                }
                this.target = el && el.querySelector(this.selector);
                if (!this.target) {
                    throw new Error("invalid portal target");
                }
            }
            this.realBDom.mount(this.target, null);
        }
        beforeRemove() {
            this.realBDom.beforeRemove();
        }
        remove() {
            if (this.realBDom) {
                super.remove();
                this.realBDom.remove();
                this.realBDom = null;
            }
        }
        patch(other) {
            super.patch(other);
            if (this.realBDom) {
                this.realBDom.patch(other.realBDom, true);
            }
            else {
                this.realBDom = other.realBDom;
                this.realBDom.mount(this.target, null);
            }
        }
    }
    class Portal extends Component {
        setup() {
            const node = this.__owl__;
            const renderFn = node.renderFn;
            node.renderFn = () => new VPortal(this.props.target, renderFn());
            onWillUnmount(() => {
                if (node.bdom) {
                    node.bdom.remove();
                }
            });
        }
    }
    Portal.template = xml `<t t-slot="default"/>`;
    Portal.props = {
        target: {
            type: String,
        },
        slots: true,
    };

    // -----------------------------------------------------------------------------
    //  Scheduler
    // -----------------------------------------------------------------------------
    class Scheduler {
        constructor() {
            this.tasks = new Set();
            this.isRunning = false;
            this.requestAnimationFrame = Scheduler.requestAnimationFrame;
        }
        start() {
            this.isRunning = true;
            this.scheduleTasks();
        }
        stop() {
            this.isRunning = false;
        }
        addFiber(fiber) {
            this.tasks.add(fiber.root);
            if (!this.isRunning) {
                this.start();
            }
        }
        /**
         * Process all current tasks. This only applies to the fibers that are ready.
         * Other tasks are left unchanged.
         */
        flush() {
            this.tasks.forEach((fiber) => {
                if (fiber.root !== fiber) {
                    this.tasks.delete(fiber);
                    return;
                }
                const hasError = fibersInError.has(fiber);
                if (hasError && fiber.counter !== 0) {
                    this.tasks.delete(fiber);
                    return;
                }
                if (fiber.node.status === 2 /* DESTROYED */) {
                    this.tasks.delete(fiber);
                    return;
                }
                if (fiber.counter === 0) {
                    if (!hasError) {
                        fiber.complete();
                    }
                    this.tasks.delete(fiber);
                }
            });
            if (this.tasks.size === 0) {
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
    // capture the value of requestAnimationFrame as soon as possible, to avoid
    // interactions with other code, such as test frameworks that override them
    Scheduler.requestAnimationFrame = window.requestAnimationFrame.bind(window);

    const DEV_MSG = `Owl is running in 'dev' mode.

This is not suitable for production use.
See https://github.com/odoo/owl/blob/master/doc/reference/config.md#mode for more information.`;
    class App extends TemplateSet {
        constructor(Root, config = {}) {
            super(config);
            this.scheduler = new Scheduler();
            this.root = null;
            this.Root = Root;
            if (config.test) {
                this.dev = true;
            }
            if (this.dev && !config.test) {
                console.info(DEV_MSG);
            }
            const descrs = Object.getOwnPropertyDescriptors(config.env || {});
            this.env = Object.freeze(Object.defineProperties({}, descrs));
            this.props = config.props || {};
        }
        mount(target, options) {
            validateTarget(target);
            const node = this.makeNode(this.Root, this.props);
            const prom = this.mountNode(node, target, options);
            this.root = node;
            return prom;
        }
        makeNode(Component, props) {
            return new ComponentNode(Component, props, this);
        }
        mountNode(node, target, options) {
            const promise = new Promise((resolve, reject) => {
                let isResolved = false;
                // manually set a onMounted callback.
                // that way, we are independant from the current node.
                node.mounted.push(() => {
                    resolve(node.component);
                    isResolved = true;
                });
                // Manually add the last resort error handler on the node
                let handlers = nodeErrorHandlers.get(node);
                if (!handlers) {
                    handlers = [];
                    nodeErrorHandlers.set(node, handlers);
                }
                handlers.unshift((e) => {
                    if (isResolved) {
                        console.error(e);
                    }
                    else {
                        reject(e);
                    }
                    throw e;
                });
            });
            node.mountComponent(target, options);
            return promise;
        }
        destroy() {
            if (this.root) {
                this.root.destroy();
            }
        }
    }
    async function mount(C, target, config = {}) {
        return new App(C, config).mount(target, config);
    }

    function status(component) {
        switch (component.__owl__.status) {
            case 0 /* NEW */:
                return "new";
            case 1 /* MOUNTED */:
                return "mounted";
            case 2 /* DESTROYED */:
                return "destroyed";
        }
    }

    class Memo extends Component {
        constructor(props, env, node) {
            super(props, env, node);
            // prevent patching process conditionally
            let applyPatch = false;
            const patchFn = node.patch;
            node.patch = () => {
                if (applyPatch) {
                    patchFn.call(node);
                    applyPatch = false;
                }
            };
            // check props change, and render/apply patch if it changed
            let prevProps = props;
            const updateAndRender = node.updateAndRender;
            node.updateAndRender = function (props, parentFiber) {
                const shouldUpdate = !shallowEqual(prevProps, props);
                if (shouldUpdate) {
                    prevProps = props;
                    updateAndRender.call(node, props, parentFiber);
                    applyPatch = true;
                }
                return Promise.resolve();
            };
        }
    }
    Memo.template = xml `<t t-slot="default"/>`;
    /**
     * we assume that each object have the same set of keys
     */
    function shallowEqual(p1, p2) {
        for (let k in p1) {
            if (k !== "slots" && p1[k] !== p2[k]) {
                return false;
            }
        }
        return true;
    }

    // Allows to get the target of a Reactive (used for making a new Reactive from the underlying object)
    const TARGET = Symbol("Target");
    // Escape hatch to prevent reactivity system to turn something into a reactive
    const SKIP = Symbol("Skip");
    // Special key to subscribe to, to be notified of key creation/deletion
    const KEYCHANGES = Symbol("Key changes");
    const objectToString = Object.prototype.toString;
    /**
     * Checks whether a given value can be made into a reactive object.
     *
     * @param value the value to check
     * @returns whether the value can be made reactive
     */
    function canBeMadeReactive(value) {
        if (typeof value !== "object") {
            return false;
        }
        // extract "RawType" from strings like "[object RawType]" => this lets us
        // ignore many native objects such as Promise (whose toString is [object Promise])
        // or Date ([object Date]).
        const rawType = objectToString.call(value).slice(8, -1);
        return rawType === "Object" || rawType === "Array";
    }
    /**
     * Mark an object or array so that it is ignored by the reactivity system
     *
     * @param value the value to mark
     * @returns the object itself
     */
    function markRaw(value) {
        value[SKIP] = true;
        return value;
    }
    /**
     * Given a reactive objet, return the raw (non reactive) underlying object
     *
     * @param value a reactive value
     * @returns the underlying value
     */
    function toRaw(value) {
        return value[TARGET];
    }
    const targetToKeysToCallbacks = new WeakMap();
    /**
     * Observes a given key on a target with an callback. The callback will be
     * called when the given key changes on the target.
     *
     * @param target the target whose key should be observed
     * @param key the key to observe (or Symbol(KEYCHANGES) for key creation
     *  or deletion)
     * @param callback the function to call when the key changes
     */
    function observeTargetKey(target, key, callback) {
        if (!targetToKeysToCallbacks.get(target)) {
            targetToKeysToCallbacks.set(target, new Map());
        }
        const keyToCallbacks = targetToKeysToCallbacks.get(target);
        if (!keyToCallbacks.get(key)) {
            keyToCallbacks.set(key, new Set());
        }
        keyToCallbacks.get(key).add(callback);
        if (!callbacksToTargets.has(callback)) {
            callbacksToTargets.set(callback, new Set());
        }
        callbacksToTargets.get(callback).add(target);
    }
    /**
     * Notify Reactives that are observing a given target that a key has changed on
     * the target.
     *
     * @param target target whose Reactives should be notified that the target was
     *  changed.
     * @param key the key that changed (or Symbol `KEYCHANGES` if a key was created
     *   or deleted)
     */
    function notifyReactives(target, key) {
        const keyToCallbacks = targetToKeysToCallbacks.get(target);
        if (!keyToCallbacks) {
            return;
        }
        const callbacks = keyToCallbacks.get(key);
        if (!callbacks) {
            return;
        }
        // Loop on copy because clearReactivesForCallback will modify the set in place
        for (const callback of [...callbacks]) {
            clearReactivesForCallback(callback);
            callback();
        }
    }
    const callbacksToTargets = new WeakMap();
    /**
     * Clears all subscriptions of the Reactives associated with a given callback.
     *
     * @param callback the callback for which the reactives need to be cleared
     */
    function clearReactivesForCallback(callback) {
        const targetsToClear = callbacksToTargets.get(callback);
        if (!targetsToClear) {
            return;
        }
        for (const target of targetsToClear) {
            const observedKeys = targetToKeysToCallbacks.get(target);
            if (!observedKeys) {
                continue;
            }
            for (const callbacks of observedKeys.values()) {
                callbacks.delete(callback);
            }
        }
        targetsToClear.clear();
    }
    const reactiveCache = new WeakMap();
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
     * + Accessing an object keys (eg with Object.keys or with `for..in`) will
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
    function reactive(target, callback = () => { }) {
        if (!canBeMadeReactive(target)) {
            throw new Error(`Cannot make the given value reactive`);
        }
        if (SKIP in target) {
            return target;
        }
        const originalTarget = target[TARGET];
        if (originalTarget) {
            return reactive(originalTarget, callback);
        }
        if (!reactiveCache.has(target)) {
            reactiveCache.set(target, new Map());
        }
        const reactivesForTarget = reactiveCache.get(target);
        if (!reactivesForTarget.has(callback)) {
            const proxy = new Proxy(target, {
                get(target, key, proxy) {
                    if (key === TARGET) {
                        return target;
                    }
                    observeTargetKey(target, key, callback);
                    const value = Reflect.get(target, key, proxy);
                    if (!canBeMadeReactive(value)) {
                        return value;
                    }
                    return reactive(value, callback);
                },
                set(target, key, value, proxy) {
                    const isNewKey = !Object.hasOwnProperty.call(target, key);
                    const originalValue = Reflect.get(target, key, proxy);
                    const ret = Reflect.set(target, key, value, proxy);
                    if (isNewKey) {
                        notifyReactives(target, KEYCHANGES);
                    }
                    // While Array length may trigger the set trap, it's not actually set by this
                    // method but is updated behind the scenes, and the trap is not called with the
                    // new value. We disable the "same-value-optimization" for it because of that.
                    if (originalValue !== value || (Array.isArray(target) && key === "length")) {
                        notifyReactives(target, key);
                    }
                    return ret;
                },
                deleteProperty(target, key) {
                    const ret = Reflect.deleteProperty(target, key);
                    notifyReactives(target, KEYCHANGES);
                    notifyReactives(target, key);
                    return ret;
                },
                ownKeys(target) {
                    observeTargetKey(target, KEYCHANGES, callback);
                    return Reflect.ownKeys(target);
                },
                has(target, key) {
                    // TODO: this observes all key changes instead of only the presence of the argument key
                    observeTargetKey(target, KEYCHANGES, callback);
                    return Reflect.has(target, key);
                },
            });
            reactivesForTarget.set(callback, proxy);
        }
        return reactivesForTarget.get(callback);
    }
    const batchedRenderFunctions = new WeakMap();
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
    function useState(state) {
        const node = getCurrent();
        if (!batchedRenderFunctions.has(node)) {
            batchedRenderFunctions.set(node, batched(() => node.render()));
            onWillDestroy(() => clearReactivesForCallback(render));
        }
        const render = batchedRenderFunctions.get(node);
        const reactiveState = reactive(state, render);
        return reactiveState;
    }

    // -----------------------------------------------------------------------------
    // useRef
    // -----------------------------------------------------------------------------
    /**
     * The purpose of this hook is to allow components to get a reference to a sub
     * html node or component.
     */
    function useRef(name) {
        const node = getCurrent();
        const refs = node.refs;
        return {
            get el() {
                return refs[name] || null;
            },
        };
    }
    // -----------------------------------------------------------------------------
    // useEnv and useSubEnv
    // -----------------------------------------------------------------------------
    /**
     * This hook is useful as a building block for some customized hooks, that may
     * need a reference to the env of the component calling them.
     */
    function useEnv() {
        return getCurrent().component.env;
    }
    function extendEnv(currentEnv, extension) {
        const env = Object.create(currentEnv);
        const descrs = Object.getOwnPropertyDescriptors(extension);
        return Object.freeze(Object.defineProperties(env, descrs));
    }
    /**
     * This hook is a simple way to let components use a sub environment.  Note that
     * like for all hooks, it is important that this is only called in the
     * constructor method.
     */
    function useSubEnv(envExtension) {
        const node = getCurrent();
        node.component.env = extendEnv(node.component.env, envExtension);
        useChildSubEnv(envExtension);
    }
    function useChildSubEnv(envExtension) {
        const node = getCurrent();
        node.childEnv = extendEnv(node.childEnv, envExtension);
    }
    // -----------------------------------------------------------------------------
    // useEffect
    // -----------------------------------------------------------------------------
    const NO_OP = () => { };
    /**
     * This hook will run a callback when a component is mounted and patched, and
     * will run a cleanup function before patching and before unmounting the
     * the component.
     *
     * @param {Effect} effect the effect to run on component mount and/or patch
     * @param {()=>any[]} [computeDependencies=()=>[NaN]] a callback to compute
     *      dependencies that will decide if the effect needs to be cleaned up and
     *      run again. If the dependencies did not change, the effect will not run
     *      again. The default value returns an array containing only NaN because
     *      NaN !== NaN, which will cause the effect to rerun on every patch.
     */
    function useEffect(effect, computeDependencies = () => [NaN]) {
        let cleanup;
        let dependencies;
        onMounted(() => {
            dependencies = computeDependencies();
            cleanup = effect(...dependencies) || NO_OP;
        });
        onPatched(() => {
            const newDeps = computeDependencies();
            const shouldReapply = newDeps.some((val, i) => val !== dependencies[i]);
            if (shouldReapply) {
                dependencies = newDeps;
                cleanup();
                cleanup = effect(...dependencies) || NO_OP;
            }
        });
        onWillUnmount(() => cleanup());
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
        const node = getCurrent();
        const boundHandler = handler.bind(node.component);
        onMounted(() => target.addEventListener(eventName, boundHandler, eventParams));
        onWillUnmount(() => target.removeEventListener(eventName, boundHandler, eventParams));
    }

    config.shouldNormalizeDom = false;
    config.mainEventHandler = mainEventHandler;
    UTILS.Portal = Portal;
    const blockDom = {
        config,
        // bdom entry points
        mount: mount$1,
        patch,
        remove,
        // bdom block types
        list,
        multi,
        text,
        toggler,
        createBlock,
        html,
        comment,
    };
    const __info__ = {};

    exports.App = App;
    exports.Component = Component;
    exports.EventBus = EventBus;
    exports.Memo = Memo;
    exports.__info__ = __info__;
    exports.blockDom = blockDom;
    exports.loadFile = loadFile;
    exports.markRaw = markRaw;
    exports.markup = markup;
    exports.mount = mount;
    exports.onError = onError;
    exports.onMounted = onMounted;
    exports.onPatched = onPatched;
    exports.onRendered = onRendered;
    exports.onWillDestroy = onWillDestroy;
    exports.onWillPatch = onWillPatch;
    exports.onWillRender = onWillRender;
    exports.onWillStart = onWillStart;
    exports.onWillUnmount = onWillUnmount;
    exports.onWillUpdateProps = onWillUpdateProps;
    exports.reactive = reactive;
    exports.status = status;
    exports.toRaw = toRaw;
    exports.useChildSubEnv = useChildSubEnv;
    exports.useComponent = useComponent;
    exports.useEffect = useEffect;
    exports.useEnv = useEnv;
    exports.useExternalListener = useExternalListener;
    exports.useRef = useRef;
    exports.useState = useState;
    exports.useSubEnv = useSubEnv;
    exports.whenReady = whenReady;
    exports.xml = xml;
    exports.batched = batched;

    Object.defineProperty(exports, '__esModule', { value: true });


    __info__.version = '2.0.0-alpha1';
    __info__.date = '2022-01-31T16:02:34.789Z';
    __info__.hash = 'fa7a393';
    __info__.url = 'https://github.com/odoo/owl';


})(this.owl = this.owl || {});
