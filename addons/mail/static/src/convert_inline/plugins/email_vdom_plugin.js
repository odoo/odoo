import { BasePlugin } from "@html_editor/base_plugin";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";
import { uuid } from "@web/core/utils/strings";

/**
 * @typedef { Object } NodeInfo
 * @property { Node } referenceNode node from this.config.reference
 * @property { Comment } vNode comment node to represent the referenceNode in
 *           another NodeInfo fragment (used to reference childNode position for
 *           the final rendering)
 * @property { DocumentFragment } fragment fragment containing the final
 *           representation of the reference node, and other vNode
 */

export class VDomPlugin extends BasePlugin {
    static id = "vDomPlugin";
    static shared = ["getNodeInfo", "renderEmailHtml"];
    resources = {
        render_email_html_handlers: this.renderEmailHtml.bind(this),
        template_node_created_handlers: this.emptyDesignElementFragment.bind(this),
    };

    setup() {
        this.referenceToInfo = new WeakMap();
        this.vNodeToInfo = new WeakMap();
        this.renderIdToInfo = new Map();
    }

    lazyNodeInfoProxyHandler(referenceNode) {
        return {
            set: () => false,
            deleteProperty: () => false,
            get: (target, key, receiver) => {
                if (key === "fragment" && !target.fragment) {
                    target.fragment = this.config.referenceDocument.createDocumentFragment();
                    const templateNode =
                        referenceNode === this.config.reference
                            ? this.config.referenceDocument.createDocumentFragment()
                            : referenceNode.cloneNode();
                    const childNodeList = childNodes(referenceNode);
                    for (const child of childNodeList) {
                        const nodeInfo = this.getNodeInfo(child);
                        templateNode.appendChild(nodeInfo.vNode);
                    }
                    // Ensure that during the final rendering, if no plugin
                    // ever modified the fragment associated with a reference
                    // node, it contains its clone and references to its
                    // childNodes.
                    target.fragment.appendChild(templateNode);
                    // Allow other plugins to process the template node
                    // (e.g. add inline style)
                    this.dispatchTo("template_node_created_handlers", {
                        nodeInfo: receiver,
                        templateNode,
                    });
                }
                return Reflect.get(target, key, receiver);
            },
        };
    }

    /**
     * Get nodeInfo related to a reference node or its related vNode.
     *
     * @param {Node} node referenceNode or vNode
     * @returns {NodeInfo} nodeInfo
     */
    getNodeInfo(node) {
        let nodeInfo;
        if (this.config.reference.contains(node)) {
            nodeInfo = this.referenceToInfo.get(node);
            if (!nodeInfo) {
                const vNode = this.config.referenceDocument.createComment("");
                nodeInfo = new Proxy(
                    {
                        renderId: uuid(),
                        referenceNode: node,
                        vNode,
                        fragment: undefined,
                    },
                    this.lazyNodeInfoProxyHandler(node)
                );
                this.vNodeToInfo.set(vNode, nodeInfo);
                this.referenceToInfo.set(node, nodeInfo);
            }
        } else if (this.vNodeToInfo.has(node)) {
            nodeInfo = this.vNodeToInfo.get(node);
        } else if (this.lastRenderTemplate?.contains(node)) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const renderElement = node.closest("[data-render-id]");
                nodeInfo = this.renderIdToInfo.get(renderElement.dataset.renderId);
            }
        }
        if (!nodeInfo) {
            // TODO EGGMAIL: error handling
            throw new Error(
                "The provided node can not be associated with an emailHtmlConversion nodeInfo."
            );
        }
        return nodeInfo;
    }

    cloneReferenceFragment(nodeInfo, options = {}) {
        const { withRenderId } = options;
        const fragment = nodeInfo.fragment;
        const renderFragment = fragment.cloneNode(true);
        const vWalker = fragment.ownerDocument.createTreeWalker(fragment, NodeFilter.SHOW_COMMENT);
        const renderWalker = renderFragment.ownerDocument.createTreeWalker(
            renderFragment,
            NodeFilter.SHOW_COMMENT
        );
        let vNode, renderNode;
        while ((vNode = vWalker.nextNode()) && (renderNode = renderWalker.nextNode())) {
            if (this.vNodeToInfo.has(vNode)) {
                this.vNodeToRenderNode.set(vNode, renderNode);
                if (withRenderId && renderNode.nodeType === Node.ELEMENT_NODE) {
                    renderNode.dataset.renderId = nodeInfo.renderId;
                    this.renderIdToInfo.set(nodeInfo.renderId, nodeInfo);
                }
            }
        }
        return renderFragment;
    }

    renderReferenceFragment(nodeInfo, options = {}) {
        const renderNode = this.vNodeToRenderNode.get(nodeInfo.vNode);
        if (!renderNode) {
            // TODO EGGMAIL: error management, a node in reference was not
            // planned to be rendered
            return;
        }
        const renderFragment = this.cloneReferenceFragment(nodeInfo, options);
        renderNode.replaceWith(renderFragment);
        for (const descendant of childNodes(nodeInfo.referenceNode)) {
            const descendantInfo = this.getNodeInfo(descendant);
            this.renderReferenceFragment(descendantInfo, options);
        }
    }

    renderEmailHtml(template, options = {}) {
        this.lastRenderTemplate = template;
        this.renderIdToInfo = new Map();
        this.vNodeToRenderNode = new WeakMap();
        const referenceInfo = this.getNodeInfo(this.config.reference);
        const renderNode = referenceInfo.vNode.cloneNode();
        this.vNodeToRenderNode.set(referenceInfo.vNode, renderNode);
        template.content.appendChild(renderNode);
        this.renderReferenceFragment(referenceInfo, options);
        this.vNodeToRenderNode = undefined;
    }

    /**
     The `<style id="design-element">` should not be sent by email, as all
     relevant style is inlined, and the variables it contains are not used
     in the final rendering. Its fragment is therefore emptied.
     */
    emptyDesignElementFragment({ nodeInfo, templateNode }) {
        if (
            templateNode.nodeType === Node.ELEMENT_NODE &&
            templateNode.matches("#design-element")
        ) {
            nodeInfo.fragment.replaceChildren();
        }
    }
}

registry.category("mail-html-conversion-plugins").add(VDomPlugin.id, VDomPlugin);
