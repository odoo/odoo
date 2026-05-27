import { xml } from "@odoo/owl";
import { renderToFragment } from "@web/core/utils/render";
import { ObjectMap, SetMap, UniqueArray } from "../data_structures";
import { StyleInfo, StyleInfoMap } from "./style_models";
import { renderAttributes } from "./utils";

export class NodePositionManager extends Array {
    registerNodes(nodes = []) {
        const nodeIds = [];
        for (const node of nodes) {
            nodeIds.push(this.length);
            this.push(node);
        }
        return nodeIds;
    }

    setNodePositions(node) {
        for (const nodePosition of node.querySelectorAll("node-position[data-id]")) {
            const node = this[nodePosition.dataset.id];
            if (node) {
                nodePosition.before(this[nodePosition.dataset.id]);
            }
            nodePosition.remove();
        }
    }

    renderContext(context = {}) {
        let nodes = [];
        const { renderPositionedNodes } = context;
        if (renderPositionedNodes) {
            nodes = renderPositionedNodes(context);
        }
        return { ...context, nodeIds: this.registerNodes(nodes) };
    }

    get template() {
        return "mail.NodePositionManager";
    }
}

/**
 * @typedef {Object} ElementOptions
 * @property {Object<string, string>} [attributes={}]
 * @property {string|Iterable<string>} [classNames=""]
 * @property {Object<string, string>} [style={}]
 */

function assignAttributes(target, source) {
    if (source.attributes !== undefined) {
        target.attributes ??= {};
        for (const [name, value] of Object.entries(source.attributes)) {
            target.attributes[name] = value;
        }
    }
}

function assignClassNames(target, source) {
    if (source.classNames !== undefined) {
        target.classNames = source.classNames;
    }
}

function assignStyle(target, source) {
    if (source.style !== undefined) {
        target.style = StyleInfo.from(target.style ?? {});
        target.style.merge(StyleInfo.from(source.style));
    }
}

export function assignDefaultElementOptions(options = {}, defaultOptions = {}) {
    const newOptions = {};
    assignAttributes(newOptions, defaultOptions);
    assignAttributes(newOptions, options);
    assignClassNames(newOptions, defaultOptions);
    assignClassNames(newOptions, options);
    assignStyle(newOptions, defaultOptions);
    assignStyle(newOptions, options);
    return newOptions;
}

/**
 * @abstract
 */
export class LayoutModel {
    static template = xml``;
    refToAttributes = new ObjectMap();
    refToClassNames = new SetMap();
    refToStyleInfo = new StyleInfoMap();
    pluginIds = new Set();

    /**
     * @param {Object} [options={}]
     * @param {Object<string, ElementOptions>} [options.refs={}] assign ElementOptions to named template refs
     */
    constructor({ refs = {} } = {}) {
        for (const [ref, options] of Object.entries(refs)) {
            this.setAttributes(options, ref);
        }
    }

    get ancestorTag() {
        return "";
    }

    get descendantTag() {
        return "";
    }

    get template() {
        return this.constructor.template;
    }

    /**
     * @param {ElementOptions} options
     * @param {string} ref named ref (@see renderAttributes calls) in the template
     */
    setAttributes({ attributes = {}, classNames = "", style = {} } = {}, ref = "root") {
        this.refToAttributes.assign(attributes, ref);
        if ("class" in attributes) {
            this.refToClassNames.union(attributes["class"], ref);
        }
        this.refToStyleInfo.assign(style, ref);
        this.refToClassNames.union(classNames, ref);
    }

    getRefNames() {
        return new Set(this.refToAttributes.keys())
            .union(new Set(this.refToClassNames.keys()))
            .union(new Set(this.refToStyleInfo.keys()));
    }

    /**
     * Returns a ref description compatible with `setAttributes` and
     * `renderAttributes`.
     */
    getRef(ref = "root") {
        const styleInfo = this.refToStyleInfo.get(ref);
        return {
            attributes: this.refToAttributes.get(ref),
            classNames: this.refToClassNames.get(ref),
            styleInfo,
            style: styleInfo,
        };
    }

    renderAttributes(ref = "root") {
        return renderAttributes(this.getRef(ref));
    }

    renderContext(context = {}) {
        return { ...context, model: this };
    }

    renderToFragment(context = {}) {
        const nodePositionManager = new NodePositionManager();
        const fragment = renderToFragment(
            this.template,
            this.renderContext(
                Object.assign({ renderPositionedNodes: () => {} }, context, { nodePositionManager })
            )
        );
        nodePositionManager.setNodePositions(fragment);
        return fragment;
    }
}

export class ElementLayout extends LayoutModel {
    static template = "mail.ElementLayout";

    constructor({ tag = "DIV", attributes = {}, classNames = "", style = {} } = {}) {
        super({
            refs: {
                root: { attributes, classNames, style },
            },
        });
        this.tag = tag;
    }

    get ancestorTag() {
        return this.tag;
    }

    get descendantTag() {
        return this.tag;
    }

    // TODO EGGMAIL: is this used? Else remove
    getStyleInfo() {
        return this.refToStyleInfo.get("root");
    }
}

export class SpacingLayout extends LayoutModel {
    static template = "mail.SpacingLayout";

    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-spacing-wrapper",
        });
    }

    get ancestorTag() {
        return "TABLE";
    }

    get descendantTag() {
        return "TD";
    }
}

export class TextNodeLayout {
    content = "";

    constructor({ content }) {
        this.content = content;
    }

    renderToFragment() {
        const fragment = document.createDocumentFragment();
        const textNode = document.createTextNode(this.content);
        fragment.append(textNode);
        return fragment;
    }
}

export class CommentNodeLayout {
    content = "";

    constructor({ content }) {
        this.content = content;
    }

    renderToFragment() {
        const fragment = document.createDocumentFragment();
        const comment = document.createComment(this.content);
        fragment.append(comment);
        return fragment;
    }
}

/**
 * TODO EGGMAIL: simplify/flatten model and combine properties with EmailNode?
 */
export class Analysis {
    constructor(options = {}) {
        options.parsingFacts ??= {
            canMerge: false,
            canParentMerge: false,
        };
        this.facts = { ...(options.facts ?? {}) };
        this.parsingFacts = { ...(options.parsingFacts ?? {}) };
        // constraints are functions: (emailNode) => { shouldPropagate: bool, facts: {} }
        this.constraintsForAncestors = [...(options.constraintsForAncestors ?? [])];
        this.constraintsForDescendants = [...(options.constraintsForDescendants ?? [])];
    }
}

export class EmailNode {
    referenceNodes = new UniqueArray();
    children = new UniqueArray();

    constructor({ layout, referenceNode, parent, analysis = {} } = {}) {
        this.layout = layout;
        if (parent) {
            parent.appendChild(this);
        }
        if (referenceNode) {
            this.pushReferenceNode(referenceNode);
        }
        this.analysis = new Analysis(analysis);
        this.marginNode = undefined;
        this.paddingNode = undefined;
    }

    /**
     * The referenceNode that was used first to define what this EmailNode
     * represents. It is often the most relevant when considering positioning in
     * the parent.
     */
    get firstReferenceNode() {
        return this.referenceNodes.at(0);
    }

    /**
     * The referenceNode that was used last to define what this EmailNode
     * represents. It is often the most relevant when considering children
     * positioning.
     */
    get lastReferenceNode() {
        return this.referenceNodes.at(-1);
    }

    get firstChild() {
        return this.children.at(0);
    }

    get lastChild() {
        return this.children.at(-1);
    }

    spliceChildren(start, deleteCount, ...items) {
        const removedChildren = this.children.splice(start, deleteCount, ...items);
        for (const child of removedChildren) {
            if (!this.children.has(child)) {
                child.parent = undefined;
            }
        }
        for (const child of items) {
            if (child.parent && child.parent.children !== this.children) {
                child.parent.removeChild(child);
            }
            child.parent = this;
        }
        return removedChildren;
    }

    pushReferenceNode(referenceNode) {
        return this.referenceNodes.push(referenceNode);
    }

    appendChild(emailNode) {
        if (emailNode.parent && emailNode.parent !== this) {
            emailNode.parent.removeChild(emailNode);
        }
        emailNode.parent = this;
        return this.children.push(emailNode);
    }

    removeChild(emailNode) {
        if (this.children.has(emailNode)) {
            emailNode.parent = undefined;
            return this.children.delete(emailNode);
        } else {
            return false;
        }
    }

    render(context = {}) {
        const render = (layoutContainer, renderContext = {}, extraPositionContext = {}) => {
            let renderChildren;
            if (layoutContainer === this.marginNode) {
                renderChildren = [this];
            } else if (layoutContainer === this && this.paddingNode) {
                renderChildren = [this.paddingNode];
            }
            let renderPositionedNodes = (positionContext = {}) =>
                renderChildren.map((child) =>
                    render(child, renderChildren, {
                        ...extraPositionContext,
                        ...positionContext,
                    })
                );
            if (!renderChildren) {
                renderPositionedNodes = (positionContext = {}) =>
                    this.children.map((child) => child.render(positionContext));
            }
            return layoutContainer.layout.renderToFragment({
                ...renderContext,
                renderPositionedNodes,
            });
        };
        if (this.marginNode) {
            return render(this.marginNode, {}, context);
        } else if (this.paddingNode) {
            return render(this, context);
        } else {
            return render(this, context);
        }
    }
}

/**
 * Wrapper for a spacing layout, compatible with EmailNode render function.
 */
export class SpacingNode {
    constructor({ Layout = SpacingLayout, refs = {} } = {}) {
        this.layout = new Layout({ refs });
    }
}
