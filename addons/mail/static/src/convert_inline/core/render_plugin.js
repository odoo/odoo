import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { Analysis, ElementLayout, EmailNode, TextNodeLayout } from "./render_models";

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
    static dependencies = ["measurementSnapshot", "referenceNode", "rules"];
    resources = {
        on_build_render_tree_handlers: this.buildRenderTree.bind(this),
        on_render_email_template_handlers: this.renderEmailHtml.bind(this),
    };

    setup() {
        this.discardedNodes = new WeakSet();
        this.syntheticEmailNodeContainers = new Set();
    }

    buildRenderTree() {
        this.discardIrrelevantNodes();
        const reference = this.config.reference;
        if (!this.isAllowedReferenceNode(reference) || this.discardedNodes.has(reference)) {
            return;
        }
        this.renderTree = this.createEmailNode(reference);
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
        const rejectedChildren = new WeakSet();
        const treeWalker = this.createReferenceTreeWalker((node) => {
            if (rejectedChildren.has(node)) {
                return NodeFilter.FILTER_REJECT;
            }
            return NodeFilter.FILTER_ACCEPT;
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

    // -- multiple objectives:
    // -- -- deny absorption by parent (if parent allows it)
    // -- -- deny future children absorption (without considering children identities)
    // -- -- provide useful layout info (styleInfo selection, attributes, etc)
    createEmailNode(referenceNode, parentEmailNode) {
        let childNodes, emailNode;
        if (referenceNode.nodeType === Node.TEXT_NODE) {
            const layout = new TextNodeLayout({ content: referenceNode.nodeValue });
            emailNode = new EmailNode({
                layout,
                referenceNode: referenceNode,
                parent: parentEmailNode,
            });
        } else {
            const { layout, analysis } = this.getEmailNodeArguments(referenceNode, parentEmailNode);
            const parentParsingFacts = parentEmailNode?.analysis.parsingFacts;
            if (parentEmailNode && !analysis.parsingFacts.canParentMerge) {
                parentParsingFacts.canMerge = false;
            }
            emailNode = parentEmailNode;
            if (parentEmailNode && parentParsingFacts.canMerge) {
                if (
                    !this.delegateTo("merge_email_node_overrides", {
                        parentEmailNode,
                        layout,
                        analysis,
                    })
                ) {
                    this.mergeElementLayout({ parentEmailNode, layout, analysis });
                    this.mergeElementAnalysis({ parentEmailNode, layout, analysis });
                }
                parentEmailNode.pushReferenceNode(referenceNode);
            } else {
                emailNode = new EmailNode({
                    layout,
                    referenceNode: referenceNode,
                    parent: parentEmailNode,
                    analysis,
                });
            }
            childNodes = this.processChildNodes(
                referenceNode,
                (node) => !this.discardedNodes.has(node)
            );
            if (childNodes.length !== 1) {
                emailNode.analysis.parsingFacts.canMerge = false;
            }
        }
        if (emailNode.analysis.parsingFacts.needSyntheticEmailNode) {
            this.syntheticEmailNodeContainers.add(emailNode);
        }
        for (const childNode of childNodes ?? []) {
            this.createEmailNode(childNode, emailNode);
        }
        return emailNode;
    }

    /**
     * Default merge logic for layouts, childLayout overrides parentLayout
     * values
     */
    mergeElementLayout({ parentEmailNode, layout, analysis }) {
        if (this.delegateTo("merge_layout_overrides", { parentEmailNode, layout, analysis })) {
            return;
        }
        // TODO EGGMAIL: review default merge behavior
        const parentLayout = parentEmailNode.layout;
        const mergedLayout = new ElementLayout({
            tag: layout.ancestorTag || parentLayout.ancestorTag || "DIV",
        });
        mergedLayout.setAttributes(parentLayout.getRef());
        mergedLayout.setAttributes(layout.getRef());
        parentEmailNode.layout = mergedLayout;
    }

    /**
     * Default merge logic for analysis, childAnalysis overrides parentAnalysis
     * values, and constraints are concatenated
     */
    mergeElementAnalysis({ parentEmailNode, layout, analysis }) {
        //parentAnalysis, childAnalysis) {
        if (this.delegateTo("merge_analysis_overrides", { parentEmailNode, layout, analysis })) {
            return;
        }
        // TODO EGGMAIL: review default merge behavior
        const parentAnalysis = parentEmailNode.analysis;
        const mergedAnalysis = new Analysis(parentAnalysis);
        parentEmailNode.analysis = mergedAnalysis;
        this.mergeFacts(parentEmailNode, analysis.parsingFacts, "parsingFacts");
        this.mergeFacts(parentEmailNode, analysis.facts);
        mergedAnalysis.constraintsForAncestors = mergedAnalysis.constraintsForAncestors.concat(
            analysis.constraintsForAncestors
        );
        mergedAnalysis.constraintsForDescendants = mergedAnalysis.constraintsForAncestors.concat(
            analysis.constraintsForDescendants
        );
    }

    /**
     * some emailNode children need to be grouped into synthetic
     * containers (eg children of a hybrid fluid row, if a cluster of inline nodes
     * is next to a "block", they all should be wrapped in a "block")
     * This process is done separately because it does not follow the
     * natural treeWalking order
     */
    addSyntheticEmailNodes() {
        for (const emailNode of [...this.syntheticEmailNodeContainers]) {
            this.syntheticEmailNodeContainers.delete(emailNode);
            // IMPORTANT: if emailNode is replaced/removed, all of its children
            // should be given a new parent, this is not a phase where nodes
            // can be discarded.
            this.processThrough("synthetic_email_node_processors", emailNode);
        }
    }

    // TODO EGGMAIL: search and replace all usages of:
    // apply_layout_strategy_overrides
    getEmailNodeArguments(referenceNode, parentEmailNode) {
        const { layout, analysis } = this.processThrough(
            "element_layout_analysis_processors",
            this.getDefaultEmailNodeArguments(referenceNode),
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

    getDefaultEmailNodeArguments(referenceNode) {
        const layout = new ElementLayout({
            tag: this.getTagName(referenceNode),
            attributes: this.getAttributes(referenceNode),
            style: this.getStyleInfo(referenceNode),
        });
        const analysis = new Analysis({
            facts: this.getReferenceNodeFacts(referenceNode),
            parsingFacts: { canParentMerge: true, canMerge: true },
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

    mergeFacts(emailNode, facts = {}, factType = "facts") {
        for (const [fact, value] of Object.entries(facts)) {
            if (!this.delegateTo("merge_fact_overrides", { emailNode, fact, value, factType })) {
                // TODO EGGMAIL: not sure if delegate is the best action here
                // (only one plugin can interfere with a fact)
                // TODO EGGMAIL: maybe we need another argument (exception, ...)?
                // TODO EGGMAIL: maybe we can use the Rules structure for facts?
                // TODO EGGMAIL: better default action for merging current fact with a new value
                // should we save descendantFacts separately from localFacts?
                // TODO EGGMAIL: here a fact from a descendant is directly applied to the current
                // emailNode, maybe it makes sense to aggregate all descendant facts, then apply
                // the final result on the current emailNode?
                emailNode.analysis[factType][fact] = value;
            }
        }
    }

    /**
     * Allow descendants to propagate facts to their ancestors through constraints
     * callbacks (reverse DFS propagation)
     */
    addBottomUpConstraints(emailNode) {
        const childConstraints = [];
        for (const child of emailNode.children) {
            childConstraints.concat(this.addBottomUpConstraints(child));
        }
        const propagatedConstraints = [];
        for (const constraint of childConstraints) {
            // `constraint` API => return object with "shouldPropagate"+ "facts" + "constraint" function
            const annotations = constraint(emailNode);
            if (annotations.shouldPropagate) {
                const newConstraint = annotations.constraint ?? constraint;
                propagatedConstraints.push(newConstraint);
            }
            this.mergeFacts(emailNode, annotations.facts ?? {});
        }
        return emailNode.analysis.constraintsForAncestors.concat(propagatedConstraints);
    }

    /**
     * Allow ancestors to propagate facts to their descendants through constraints
     * callbacks (DFS propagation)
     */
    addTopDownConstraints(emailNode, constraints = []) {
        const propagatedConstraints = [];
        for (const constraint of constraints) {
            const annotations = constraint(emailNode);
            if (annotations.shouldPropagate) {
                const newConstraint = annotations.constraint ?? constraint;
                propagatedConstraints.push(newConstraint);
            }
            this.mergeFacts(emailNode, annotations.facts ?? {});
        }
        for (const child of emailNode.children) {
            this.addTopDownConstraints(
                child,
                emailNode.analysis.constraintsForDescendants.concat(propagatedConstraints)
            );
        }
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
        emailNode.layout = this.processThrough("refine_layout_processors", emailNode.layout, {
            emailNode,
        });
        for (const childEmailNode of emailNode.children) {
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
    }
}

registry.category("mail-html-conversion-core-plugins").add(RenderPlugin.id, RenderPlugin);
