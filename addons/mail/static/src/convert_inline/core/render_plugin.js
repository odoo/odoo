import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { Analysis, ElementLayout, EmailNode, LayoutModel, TextNodeLayout } from "./render_models";
import { isSelfClosingElement } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

/**
 * This plugin handles 4 conversion phases, leading to the ability to render the email html:
 * 1) identify semantic grouping boundaries
 * // a) discard pass to remove irrelevant nodes
 * // b) absorption pass to eliminate containers overlapping their content (no visual value)
 * // c) add synthetic nodes pass to group some content inside a container that is implied by css only
 * 2) propagate constraints from these groupings to annotate them:
 * // a) bottom up analysis (descendants propagate constraints and information to their ancestors)
 * // b) top down analysis (ancestors propagate constraints and information to their descendants)
 * 3) refine the layout of semantic nodes from the analysis plugin
 * // a) alter/replace node identities to fulfill constraints for every node
 * 4) render the final email html tree
 * // a) render each layout to create the final html tree
 */
export class RenderPlugin extends Plugin {
    static id = "render";
    static dependencies = ["math", "measurementSnapshot", "referenceNode", "rules"];
    static shared = ["attemptMerge", "isDiscarded"];
    resources = {
        build_render_tree_processors: withSequence(1, this.buildRenderTree.bind(this)),
        render_email_template_processors: this.renderEmailHtml.bind(this),
    };

    setup() {
        this.discardedNodes = new WeakSet();
        this.syntheticEmailNodeContainers = new Set();
        this.syntheticEmailNodeContainersPile = [];
    }

    isDiscarded(referenceNode) {
        return (
            !referenceNode ||
            (this.config.reference.contains(referenceNode) &&
                this.discardedNodes.has(referenceNode))
        );
    }

    buildRenderTree() {
        this.discardIrrelevantNodes();
        const reference = this.config.reference;
        if (!this.isAllowedReferenceNode(reference) || this.isDiscarded(reference)) {
            return;
        }
        this.renderTree = this.createEmailNodes();
        this.addSyntheticEmailNodes();
        this.addBottomUpConstraints(this.renderTree);
        this.addTopDownConstraints(this.renderTree);
        this.enforceConstraints(this.renderTree);
    }

    /**
     * TODO EGGMAIL: if a parent node has an irrelevant node, it may itself
     * be irrelevant, but this function does not handle that currently.
     */
    discardIrrelevantNodes() {
        const rejectedChildren = new Set();
        const treeWalker = this.createReferenceTreeWalker({
            filter: (node) => {
                if (rejectedChildren.has(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        let node = treeWalker.root;
        do {
            if (!this.checkPredicates("should_discard_reference_node_predicates", node)) {
                continue;
            }
            this.discardedNodes.add(node);
            this.processChildNodes(node, (child) => {
                rejectedChildren.add(child);
            });
            console.log("discarded", node);
        } while ((node = treeWalker.nextNode()));
    }

    createEmailNodes(rootReferenceNode = this.config.reference, config = {}) {
        const nodeToEmailNode = new Map();
        const contexts = [];
        const createContext = (container, targetsProviders = []) => {
            const targets = new Set();
            for (const provider of targetsProviders) {
                for (const target of provider() || []) {
                    if (container.contains(target)) {
                        targets.add(target);
                    }
                }
            }
            const paths = new Set();
            for (const target of targets) {
                for (
                    let node = target.parentNode;
                    node && node !== container;
                    node = node.parentNode
                ) {
                    paths.add(node);
                }
            }
            return {
                container,
                targets,
                paths,
                activeTarget: null,
            };
        };
        const filter = (node) => {
            while (contexts.length && !contexts.at(-1).container.contains(node)) {
                contexts.pop();
            }
            if (this.discardedNodes.has(node)) {
                return NodeFilter.FILTER_REJECT;
            }
            const context = contexts.at(-1);
            if (context) {
                if (context.activeTarget && !context.activeTarget.contains(node)) {
                    context.activeTarget = null;
                }
                if (!context.activeTarget) {
                    if (context.targets.has(node)) {
                        context.activeTarget = node;
                    } else if (context.paths.has(node)) {
                        return NodeFilter.FILTER_SKIP;
                    } else {
                        return NodeFilter.FILTER_REJECT;
                    }
                }
            }
            return NodeFilter.FILTER_ACCEPT;
        };
        const treeWalker = this.createReferenceTreeWalker({ filter, root: rootReferenceNode });
        let node = treeWalker.root;
        do {
            let parentNode, parentEmailNode, isOnlyChild;
            if (node !== treeWalker.root) {
                const parentPath = new Set();
                for (
                    parentNode = node.parentNode;
                    parentNode && !parentEmailNode;
                    parentNode = parentNode.parentNode
                ) {
                    parentEmailNode = nodeToEmailNode.get(parentNode);
                    if (!parentEmailNode) {
                        parentPath.add(parentNode);
                    }
                }
                // set emailNode of the first non-skipped node for skipped nodes
                for (const pathNode of parentPath) {
                    nodeToEmailNode.set(pathNode, parentEmailNode);
                }
            }
            if (
                parentNode &&
                parentEmailNode &&
                !parentEmailNode.analysis.parsingFacts.isSkippingContainer
            ) {
                isOnlyChild =
                    this.processChildNodes(parentNode, (node) => !this.discardedNodes.has(node))
                        .length === 1;
            }
            const emailNode = this.createEmailNode(
                {
                    referenceNode: node,
                    parentEmailNode,
                    isOnlyChild,
                },
                config
            );
            nodeToEmailNode.set(node, emailNode);
            if (emailNode.analysis.parsingFacts.isSkippingContainer) {
                const providers =
                    emailNode.analysis.parsingFacts.skippingContainerDescendantProviders;
                contexts.push(createContext(node, providers));
            }
            if (emailNode.analysis.parsingFacts.hasMobileSubtree) {
                emailNode.analysis.parsingFacts.mobileSubTree = this.createEmailNodes(node, {
                    parsingFacts: { isMobileSubtree: true },
                });
            }
        } while ((node = treeWalker.nextNode()));
        return nodeToEmailNode.get(rootReferenceNode);
    }

    // -- multiple objectives:
    // -- -- deny absorption by parent (if parent allows it)
    // -- -- deny future children absorption (without considering children identities)
    // -- -- provide useful layout info (styleInfo selection, attributes, etc)
    createEmailNode({ referenceNode, parentEmailNode, isOnlyChild }, config = {}) {
        let emailNode;
        if (referenceNode.nodeType === Node.TEXT_NODE) {
            const layout = new TextNodeLayout({ content: referenceNode.nodeValue });
            emailNode = new EmailNode({
                layout,
                referenceNode,
                parent: parentEmailNode,
            });
        } else {
            const { layout, analysis } = this.getEmailNodeArguments(
                { referenceNode, parentEmailNode },
                config
            );
            emailNode = new EmailNode({
                layout,
                referenceNode: referenceNode,
                parent: parentEmailNode,
                analysis,
            });
            if (parentEmailNode && isOnlyChild && this.attemptMerge(parentEmailNode, emailNode)) {
                emailNode = parentEmailNode;
            }
        }
        if (emailNode.analysis.parsingFacts.needSyntheticEmailNode) {
            this.syntheticEmailNodeContainers.add(emailNode);
        }
        return emailNode;
    }

    /**
     * TODO EGGMAIL: if attemptMerge is done during addSyntheticEmailNode
     * we could potentially remove a node that has not yet been handled
     * in this case, we need to add the new parent to the list and remove
     * the previous one
     */
    attemptMerge(parentEmailNode, emailNode) {
        if (!parentEmailNode.children.has(emailNode)) {
            return false;
        }
        if (
            !parentEmailNode.analysis.parsingFacts.canMerge ||
            !emailNode.analysis.parsingFacts.canParentMerge
        ) {
            return false;
        }
        let mergeSuccess = false;
        const parentLayout = parentEmailNode.layout;
        // merge_email_node_overrides callbacks must only modify layout and
        // analysis, other concerns are handled in case of mergeSuccess.
        if (this.delegateTo("merge_email_node_overrides", parentEmailNode, emailNode)) {
            mergeSuccess = true;
        } else if (
            // TODO EGGMAIL: investigate if more automatic merge cases
            // can be allowed // => neutral div into a strategy table could be
            // correct (need investigation if table can accept div properties)
            parentLayout instanceof ElementLayout &&
            parentLayout.descendantTag === "DIV" &&
            emailNode.lastReferenceNode &&
            this.isBlock(emailNode.lastReferenceNode) &&
            parentEmailNode.lastReferenceNode &&
            this.isBlock(parentEmailNode.lastReferenceNode) &&
            this.areRectEqual(
                this.getBoundingClientRect(parentEmailNode.lastReferenceNode),
                this.getBoundingClientRect(emailNode.lastReferenceNode)
            )
        ) {
            mergeSuccess = true;
            this.mergeElementLayout(parentEmailNode, emailNode);
            this.mergeAnalysis(parentEmailNode, emailNode);
        } else if (this.delegateTo("merge_layout_overrides", parentEmailNode, emailNode)) {
            mergeSuccess = true;
            this.mergeAnalysis(parentEmailNode, emailNode);
        }
        if (mergeSuccess) {
            if (
                this.syntheticEmailNodeContainers.has(emailNode) &&
                this.syntheticEmailNodeContainersPile.length !== 0
            ) {
                // if a node needing synthetic handling is merged into its parent
                // during synthetic handling, replace it by its parent in the queue
                const index = this.syntheticEmailNodeContainersPile.indexOf(emailNode);
                this.syntheticEmailNodeContainersPile[index] = parentEmailNode;
            }
            parentEmailNode.pushReferenceNodes(...emailNode.referenceNodes);
            parentEmailNode.removeChild(emailNode);
            for (const child of emailNode.children) {
                parentEmailNode.appendChild(child);
            }
        }
        return mergeSuccess;
    }

    /**
     * Default merge logic for layouts, childLayout overrides parentLayout
     * values
     */
    mergeElementLayout(parentEmailNode, emailNode) {
        if (this.delegateTo("merge_layout_overrides", parentEmailNode, emailNode)) {
            return;
        }
        const { layout } = emailNode;
        // Build a dummy to aggregate the child layout properties onto the
        // parent layout properties
        const dummyLayout = new LayoutModel({ refs: parentEmailNode.layout.getRefs() });
        const styleInfo = dummyLayout.getRef().styleInfo;
        // TODO EGGMAIL: handle the following properly with rules, evaluate
        // what other properties should be removed
        // Only the resulting layout (from emailNode) can determine the display
        // mode.
        styleInfo.removeProperty("display");
        for (const refName of layout.getRefNames()) {
            dummyLayout.setAttributes(layout.getRef(refName), refName);
        }
        const refs = dummyLayout.getRefs();
        refs.root.tag = layout.ancestorTag;
        parentEmailNode.layout = new layout.constructor({ refs });
    }

    /**
     * Default merge logic for analysis, childAnalysis overrides parentAnalysis
     * values, and constraints are evaluated
     */
    mergeAnalysis(parentEmailNode, emailNode) {
        if (this.delegateTo("merge_analysis_overrides", parentEmailNode, emailNode)) {
            return;
        }
        const { analysis } = emailNode;
        const parentAnalysis = parentEmailNode.analysis;
        // Apply BottomUp constraints from the child and concat propagated ones
        parentAnalysis.bottomUpConstraints = parentAnalysis.bottomUpConstraints.concat(
            this.applyBottomUpConstraints(parentEmailNode, analysis.bottomUpConstraints)
        );
        // Discard TopDown propagated constraints as emailNode will be removed
        this.applyTopDownConstraints(emailNode, parentAnalysis.topDownConstraints);
        this.mergeFacts(parentEmailNode, {
            facts: analysis.parsingFacts,
            factType: "parsingFacts",
        });
        this.mergeFacts(parentEmailNode, { facts: analysis.facts });
    }

    /**
     * some emailNode children need to be grouped into synthetic
     * containers (eg children of a hybrid fluid row, if a cluster of inline nodes
     * is next to a "block", they all should be wrapped in a "block")
     * This process is done separately because it does not follow the
     * natural treeWalking order
     */
    addSyntheticEmailNodes() {
        this.syntheticEmailNodeContainersPile = [...this.syntheticEmailNodeContainers].reverse();
        let emailNode;
        while ((emailNode = this.syntheticEmailNodeContainersPile.pop())) {
            this.syntheticEmailNodeContainers.delete(emailNode);
            // IMPORTANT: if emailNode is replaced/removed, all of its children
            // should be given a new parent, this is not a phase where nodes
            // can be discarded lightly.
            this.processThrough("synthetic_email_node_processors", emailNode);
        }
    }

    getEmailNodeArguments({ referenceNode, parentEmailNode }, { parsingFacts } = {}) {
        const { layout, analysis } = this.processThrough(
            "element_layout_analysis_processors",
            this.getDefaultEmailNodeArguments(referenceNode, { parsingFacts }),
            { referenceNode, parentEmailNode }
        );
        // TODO EGGMAIL: all layouts don't provide pluginIds
        // The API is not friendly
        // we should get constructor wrappers which, in a plugin, automatically
        // add the pluginId, or scrap the whole concept
        if (layout.pluginIds.size === 0) {
            layout.pluginIds.add(RenderPlugin.id);
        }
        console.log(Array.from(layout.pluginIds).join(", "), referenceNode);
        return { layout, analysis };
    }

    getDefaultEmailNodeArguments(referenceNode, { parsingFacts = {} } = {}) {
        const layout = new ElementLayout({
            refs: {
                root: {
                    tag: this.getTagName(referenceNode),
                    attributes: this.getAttributes(referenceNode),
                    style: this.getStyleInfo(referenceNode),
                },
            },
        });
        const analysis = new Analysis({
            facts: this.getReferenceNodeFacts(referenceNode),
            parsingFacts: { canParentMerge: true, canMerge: true, ...parsingFacts },
        });
        return { layout, analysis };
    }

    getReferenceNodeFacts(referenceNode) {
        return this.processThrough("reference_node_facts_processors", {}, { referenceNode });
    }

    getTagName(referenceNode) {
        return this.processThrough("reference_node_tag_name_processors", referenceNode.tagName, {
            referenceNode,
        });
    }

    mergeFacts(
        emailNode,
        { facts = {}, factType = "facts", isConstraint = false, direction = "down" } = {}
    ) {
        for (const [fact, value] of Object.entries(facts)) {
            if (
                !this.delegateTo("merge_fact_overrides", {
                    emailNode,
                    fact,
                    value,
                    factType,
                    isConstraint,
                    direction,
                })
            ) {
                // TODO EGGMAIL: not sure if delegate is the best action here
                // (only one plugin can interfere with a fact)
                // TODO EGGMAIL: maybe we need another argument (exception, ...)?
                // TODO EGGMAIL: maybe we can use the Rules structure for facts?
                // TODO EGGMAIL: better default action for merging current fact with a new value
                // should we save descendantFacts separately from localFacts?
                // TODO EGGMAIL: here a fact from a descendant is directly applied to the current
                // emailNode, maybe it makes sense to aggregate all descendant facts, then apply
                // the final result on the current emailNode?
                // TODO EGGMAIL: re-evaluate every fact, and decide if they need a custom
                // merge handling
                emailNode.analysis[factType][fact] = value;
            }
        }
    }

    /**
     * Allow descendants to propagate facts to their ancestors through constraints
     * callbacks (reverse DFS propagation)
     */
    addBottomUpConstraints(emailNode) {
        let childConstraints = [];
        for (const child of emailNode.children) {
            childConstraints = childConstraints.concat(this.addBottomUpConstraints(child));
        }
        const propagatedConstraints = this.applyBottomUpConstraints(emailNode, childConstraints);
        return emailNode.analysis.bottomUpConstraints.concat(propagatedConstraints);
    }

    applyBottomUpConstraints(emailNode, constraints) {
        const propagatedConstraints = [];
        for (const constraint of constraints) {
            // `constraint` API => return object with "shouldPropagate"+ "facts" + "constraint" function
            const annotations = constraint(emailNode);
            if (!annotations) {
                continue;
            }
            if (annotations.shouldPropagate) {
                const newConstraint = annotations.constraint ?? constraint;
                propagatedConstraints.push(newConstraint);
            }
            if (annotations.topDownConstraints) {
                emailNode.analysis.topDownConstraints.push(...annotations.topDownConstraints);
            }
            this.mergeFacts(emailNode, {
                facts: annotations.facts ?? {},
                isConstraint: true,
                direction: "up",
            });
        }
        return propagatedConstraints;
    }

    /**
     * Allow ancestors to propagate facts to their descendants through constraints
     * callbacks (DFS propagation)
     */
    addTopDownConstraints(emailNode, constraints = []) {
        const propagatedConstraints = this.applyTopDownConstraints(emailNode, constraints);
        for (const child of emailNode.children) {
            this.addTopDownConstraints(
                child,
                emailNode.analysis.topDownConstraints.concat(propagatedConstraints)
            );
        }
    }

    applyTopDownConstraints(emailNode, constraints) {
        const propagatedConstraints = [];
        for (const constraint of constraints) {
            const annotations = constraint(emailNode);
            if (!annotations) {
                continue;
            }
            if (annotations.shouldPropagate) {
                const newConstraint = annotations.constraint ?? constraint;
                propagatedConstraints.push(newConstraint);
            }
            this.mergeFacts(emailNode, {
                facts: annotations.facts ?? {},
                isConstraint: true,
            });
        }
        return propagatedConstraints;
    }

    // My idea right now:
    // layout starts as the simple element transcription
    // analysis accumulates facts during various kind of passes
    // after every node has its facts updated, the render_plugin goes through the tree
    // and fulfill all facts
    // // -> all facts are "requests" to be fulfilled by the layout, if the layout changes, it should ensure
    // // all facts are fulfilled.
    // TODO:
    // cleanup comments to extract useful ideas and remove other stuff
    // decide on layout general API
    // merge LayoutModel and Layout models, makes no sense to have both
    // an layout can contain others => we are really into the LayoutModel territory here
    // an layout can also have multiple slots instead of sub-identities (do I keep such flexibility?)
    // the "render" method of an Layout should take care of handling its subtree
    // the Layout subtree relates to only one EmailNode, which was one render intention
    enforceConstraints(emailNode) {
        // keep original layout (inside emailNode) untouched during the
        // whole process, but the current layout can be used
        // don't replace existing siblings emailNodes during refinement
        emailNode.layout = this.processThrough("refine_layout_processors", emailNode.layout, {
            emailNode,
        });
        // TODO EGGMAIL: if enforcing constraints adds siblings or ancestors,
        // they won't go through the "refine_layout_processors" hook.
        // (known limitation, update this code if a change is necessary)
        for (const childEmailNode of [...emailNode.children]) {
            this.enforceConstraints(childEmailNode);
        }
    }

    /**
     * TODO EGGMAIL: reconsider what's better:
     * always ensure that at least an empty paragraph is returned, or return
     * nothing and let the caller decide what to do when convert_inline
     * outputs nothing?
     * Probably best to return an empty string, but then edge cases have
     * to be handled in the html_field, consider edge cases where there is
     * content in the reference, but it is discarded, vs cases where there
     * is no content in the reference.
     */
    ensureTemplateContent(template) {
        if (!template.content.firstChild) {
            const paragraph = this.config.referenceDocument.createElement("P");
            const br = this.config.referenceDocument.createElement("BR");
            paragraph.append(br);
            template.content.appendChild(paragraph);
        }
        if (this.config.debug) {
            for (const el of template.content.querySelectorAll(":empty")) {
                const comments = childNodes(el).filter(
                    (node) => node.nodeType === Node.COMMENT_NODE
                );
                if (comments.length === 0 && !isSelfClosingElement(el) && el.nodeName !== "T") {
                    // Warning when an element is eligible to become an illegal
                    // self-closing node due to backend parsing
                    console.warn(
                        "A comment childNode is expected for the following element to avoid backend XML parsing issues:",
                        el
                    );
                }
            }
        }
    }

    renderEmailHtml(template) {
        let fragment;
        if (this.renderTree) {
            fragment = this.renderTree.render();
        }
        if (fragment) {
            template.content.appendChild(fragment);
        }
        this.ensureTemplateContent(template);
        return template;
    }
}

registry.category("mail-html-conversion-core-plugins").add(RenderPlugin.id, RenderPlugin);
