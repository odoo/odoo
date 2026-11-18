import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Analysis, DesktopOnlyLayout, EmailNode, MobileOnlyLayout } from "./render_models";

export class ResponsivePlugin extends Plugin {
    static id = "responsive";
    static dependencies = ["render"];
    static shared = ["getResponsiveSubtreeFacts"];
    resources = {
        element_layout_analysis_processors: this.analyzeResponsiveSubtree.bind(this),
        synthetic_email_node_processors: this.processResponsiveSyntheticEmailNodes.bind(this),
    };

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
