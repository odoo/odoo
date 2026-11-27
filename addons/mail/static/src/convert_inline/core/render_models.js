import { xml } from "@odoo/owl";
import { renderToFragment } from "@web/core/utils/render";
import { ObjectMap, SetMap, UniqueArray } from "@mail/convert_inline/data_structures";
import { StyleInfo, StyleInfoMap } from "@mail/convert_inline/core/style_models";
import { renderAttributes } from "@mail/convert_inline/core/utils";

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

    /**
     * @param {Object} context { renderPositionedNodes }
     * @returns {Object} context { nodeIds }
     */
    renderContext(context = {}) {
        let nodes = [];
        const { renderPositionedNodes } = context;
        if (renderPositionedNodes) {
            nodes = renderPositionedNodes(context);
        }
        return { ...context, nodeIds: this.registerNodes(nodes) };
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
    const newOptions = { ...options };
    delete newOptions.attributes;
    delete newOptions.classNames;
    delete newOptions.style;
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
export class TemplateLayout {
    static template = xml``;
    refToAttributes = new ObjectMap();
    refToClassNames = new SetMap();
    refToStyleInfo = new StyleInfoMap();

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

    replaceStyleInfo(styleInfo, ref = "root") {
        this.refToStyleInfo.set(ref, styleInfo);
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
            styleInfo, // mutable source
            style: StyleInfo.from(styleInfo), // copy
        };
    }

    getRefs() {
        const refs = {};
        for (const refName of this.getRefNames()) {
            refs[refName] = this.getRef(refName);
        }
        return refs;
    }

    renderAttributes(ref = "root") {
        return renderAttributes(this.getRef(ref));
    }

    /**
     * @param {Object} context { renderPositionedNodes }
     * @returns {Object} context { renderPositionedNodes, model }
     */
    renderContext(context = {}) {
        return { ...context, model: this };
    }

    /**
     * @param {Object} context { renderPositionedNodes }
     */
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

    isNeutral() {
        return false;
    }
}

export class ElementLayout extends TemplateLayout {
    static template = "mail.ElementLayout";

    constructor(options = {}) {
        super(options);
        this.tag = options.refs?.root?.tag ?? "DIV";
    }

    get ancestorTag() {
        return this.tag;
    }

    get descendantTag() {
        return this.tag;
    }

    /**
     * A DIV with no style instruction does not need to be rendered if
     * it has a margin or padding node @see EmailNode.render
     */
    isNeutral() {
        return (
            this.tag === "DIV" &&
            [...this.getRefNames()].every(
                (ref) => Object.entries(this.renderAttributes(ref)).length === 0
            )
        );
    }
}

export class DesktopOnlyLayout extends ElementLayout {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-desktop-only",
        });
    }
}

export class MobileOnlyLayout extends ElementLayout {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-mobile-only",
            style: {
                display: "none",
            },
        });
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

    isNeutral() {
        return false;
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

    isNeutral() {
        return false;
    }
}

/**
 * Layout to wrap the content rendered by the next levels of the EmailNode
 * render stack @see EmailNode.addWrapper
 * Override renderToFragment to define what the wrapping does.
 * @abstract
 */
export class WrapperLayout {
    /**
     * @param {Object} context { renderPositionedNodes }
     * @returns {DocumentFragment[]} wrapped content
     */
    renderContent(context = {}) {
        return context.renderPositionedNodes?.(context) ?? [];
    }

    /**
     * @param {Object} context { renderPositionedNodes }
     */
    renderToFragment(context = {}) {
        const fragment = document.createDocumentFragment();
        fragment.append(...this.renderContent(context));
        return fragment;
    }

    isNeutral() {
        return false;
    }
}

/**
 * Surround the wrapped content with a prefix comment and a suffix comment.
 */
export class CommentPairLayout extends WrapperLayout {
    constructor({ prefix, suffix }) {
        super();
        this.prefix = new CommentNodeLayout({ content: prefix });
        this.suffix = new CommentNodeLayout({ content: suffix });
    }

    renderToFragment(context = {}) {
        const fragment = document.createDocumentFragment();
        fragment.append(
            this.prefix.renderToFragment(),
            ...this.renderContent(context),
            this.suffix.renderToFragment()
        );
        return fragment;
    }
}

/**
 * @typedef {Object} BuildDirectives
 * Instructions given to the RenderPlugin to build the EmailTree. This is a
 * closed set owned by the RenderPlugin.
 * @property {boolean} [canMerge] authorization to attempt merging the layout
 *           and analysis of a descendant onto oneself
 * @property {boolean} [canParentMerge] authorization for a parent to attempt
 *           merging the layout and analysis of oneself onto them
 * @property {Object} [subtreeContext] variant and referenceNode of each
 *           subtree type the node is part of, by subtree type
 * @property {{ type: string, variants: string[] }} [subtree] request to build
 *           one subtree per variant from this node
 * @property {boolean} [needSyntheticEmailNode] request to be processed by
 *           `synthetic_email_node_processors`
 * @property {boolean} [isSkippingContainer] request to only parse the
 *           descendants returned by `skippingContainerDescendantProviders`
 * @property {Function[]} [skippingContainerDescendantProviders]
 */

export class Analysis {
    constructor(options = {}) {
        this.facts = { ...options.facts };
        /** @type {BuildDirectives} */
        this.buildDirectives = {
            ...(options.buildDirectives ?? { canMerge: false, canParentMerge: false }),
        };
        // constraints are functions: (emailNode) => ({ shouldPropagate: bool, facts: {}, constraint: (emailNode) => (...) })
        this.bottomUpConstraints = [...(options.bottomUpConstraints ?? [])];
        this.topDownConstraints = [...(options.topDownConstraints ?? [])];
    }
}

export class EmailTree {
    roots = new UniqueArray();

    constructor({ roots = [] } = {}) {
        this.roots.push(...roots);
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
            this.pushReferenceNodes(referenceNode);
        }
        this.analysis = new Analysis(analysis);
        this.marginNode = undefined;
        this.paddingNode = undefined;
        // wrappers around the margin, the layout and the padding
        this.marginWrappers = [];
        // wrappers between the margin and the layout
        this.layoutWrappers = [];
    }

    /**
     * Wrap a part of the render stack of this EmailNode with a wrapper layout:
     *
     * [marginWrappers] > marginNode > [layoutWrappers] > layout > paddingNode > children
     *
     * In each group, wrappers are ordered from the outermost to the innermost,
     * meaning that a wrapper added later is nested inside the previous ones.
     *
     * @param {WrapperLayout} layout
     * @param {Object} [options]
     * @param {"margin"|"layout"} [options.around="layout"]
     *        - "margin": the wrapper is around the marginNode.
     *        - "layout": the wrapper is inside the marginNode, around the
     *          main layout.
     */
    addWrapper(layout, { around = "layout" } = {}) {
        if (around === "margin") {
            this.marginWrappers.push(layout);
        } else if (around === "layout") {
            this.layoutWrappers.push(layout);
        } else {
            throw new Error(`Unknown wrapper position: ${around}`);
        }
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

    get nextSibling() {
        if (!this.parent) {
            return undefined;
        }
        const index = this.parent.children.indexOf(this);
        return this.parent.children.at(index + 1);
    }

    get previousSibling() {
        if (!this.parent) {
            return undefined;
        }
        const index = this.parent.children.indexOf(this);
        if (index === 0) {
            return undefined;
        }
        return this.parent.children.at(index - 1);
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

    pushReferenceNodes(...referenceNodes) {
        return this.referenceNodes.push(...referenceNodes);
    }

    appendChild(emailNode) {
        if (emailNode.parent && emailNode.parent !== this) {
            emailNode.parent.removeChild(emailNode);
        }
        emailNode.parent = this;
        return this.children.push(emailNode);
    }

    appendSubtree(emailTree) {
        for (const emailNode of emailTree.roots) {
            this.appendChild(emailNode);
        }
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
        const isNeutral = this.layout.isNeutral();
        const stack = [
            ...this.marginWrappers.map((layout) => ({ layout, shouldRender: () => true })),
            { layout: this.marginNode?.layout, shouldRender: () => this.marginNode },
            ...this.layoutWrappers.map((layout) => ({ layout, shouldRender: () => true })),
            {
                layout: this.layout,
                shouldRender: () => !isNeutral || (!this.marginNode && !this.paddingNode),
            },
            { layout: this.paddingNode?.layout, shouldRender: () => this.paddingNode },
        ];
        const render = (index, renderContext) => {
            if (index === stack.length) {
                return this.children.flatMap((child) => child.render(renderContext));
            }
            const { layout, shouldRender } = stack.at(index);
            if (!shouldRender()) {
                return render(index + 1, renderContext);
            }
            return [
                layout.renderToFragment({
                    ...renderContext,
                    renderPositionedNodes: (nodesContext) => render(index + 1, nodesContext),
                }),
            ];
        };
        return render(0, context);
    }
}
