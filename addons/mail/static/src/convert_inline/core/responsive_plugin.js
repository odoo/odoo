import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { DIMENSIONS } from "./utils";
import { Analysis, DesktopOnlyLayout, EmailNode, MobileOnlyLayout } from "./render_models";

const { DESKTOP, MOBILE } = DIMENSIONS;

export class ResponsivePlugin extends Plugin {
    static id = "responsive";
    static dependencies = ["render"];
    static shared = ["callWithDimensions", "getResponsiveSubtreeFacts"];
    resources = {
        on_measure_reference_content_handlers: this.responsiveParsing.bind(this),
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        element_layout_analysis_processors: this.analyzeResponsiveSubtree.bind(this),
        synthetic_email_node_processors: this.processResponsiveSyntheticEmailNodes.bind(this),
    };

    responsiveParsing() {
        this.parseWithDimensions(DESKTOP);
        this.parseWithDimensions(MOBILE);
    }

    callWithDimensions(callback, dimensions) {
        const originalDimensions = this.layoutDimensions;
        if (this.layoutDimensions !== dimensions) {
            this.config.updateLayoutDimensions(dimensions);
        }
        callback(dimensions);
        if (this.layoutDimensions !== originalDimensions) {
            this.config.updateLayoutDimensions(originalDimensions);
        }
    }

    analyzeResponsiveSubtree(defaultEmailNodeArguments, { referenceNode }) {
        const { analysis } = defaultEmailNodeArguments;
        if (this.getSubtreeReferenceNode(analysis, "responsiveSubtree") !== referenceNode) {
            return defaultEmailNodeArguments;
        }
        analysis.parsingFacts.needSyntheticEmailNode = true;
        analysis.facts.needResponsiveSubtreeRoot = true;
        return defaultEmailNodeArguments;
    }

    getResponsiveSubtreeFacts() {
        return {
            canMerge: false,
            subtree: { type: "responsiveSubtree", variants: ["desktop", "mobile"] },
        };
    }

    parseWithDimensions(dimensions) {
        this.callWithDimensions(() => {
            // TODO EGGMAIL: should we loop over every node and trigger an event
            // on a node level, or should we allow plugins to parse the reference
            // independently (which prevents parallelization of measurements on the same element),
            // but require more complex logic to determine if a measurement has to be done in
            // the first place? Currently letting every plugin loop over the reference as they see
            // fit, to refactor if needed.
            this.trigger("on_parse_layout_with_dimensions_handlers", { dimensions });
        }, dimensions);
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }

    processResponsiveSyntheticEmailNodes(emailNode) {
        if (!emailNode.analysis.facts.needResponsiveSubtreeRoot) {
            return emailNode;
        }
        const processedNode = this.buildResponsiveOnlyEmailNode(
            this.getSubtreeVariant(emailNode.analysis, "responsiveSubtree") === "mobile"
                ? MobileOnlyLayout
                : DesktopOnlyLayout,
            emailNode.analysis.parsingFacts.subtreeContext
        );
        if (emailNode.parent) {
            const index = emailNode.parent?.children.indexOf(emailNode);
            emailNode.parent.spliceChildren(index, 1, processedNode);
        }
        processedNode.appendChild(emailNode);
        return emailNode;
    }

    buildResponsiveOnlyEmailNode(ResponsiveLayout, subtreeContext = {}) {
        return new EmailNode({
            layout: new ResponsiveLayout(),
            analysis: new Analysis({
                facts: { isResponsiveSubtreeRoot: true },
                parsingFacts: { canMerge: false, canParentMerge: false, subtreeContext },
            }),
        });
    }
}

registry.category("mail-html-conversion-core-plugins").add(ResponsivePlugin.id, ResponsivePlugin);
