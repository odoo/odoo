import { backgroundImageCssToParts, getBgImageURLFromURL } from "@html_editor/utils/image";
import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import {
    buildBackgroundImageVmlNodes,
    buildInlineShapeVmlContent,
    buildHideIfNotMsoNodes,
    wrapIfMso,
} from "./mso_vml_models";
import { DIMENSIONS } from "../core/utils";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { CommentNodeLayout, ElementLayout } from "../core/render_models";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { isAllowedContent } from "@html_editor/utils/dom_info";

export class MsoPlugin extends Plugin {
    static id = "mso";
    static dependencies = [
        "border",
        "measurementSnapshot",
        "render",
        "responsive",
        "rules",
        "spacing",
    ];
    resources = {
        element_layout_analysis_processors: [
            this.analyzeElementWithBackgroundLayout.bind(this),
            this.detectMsoInlineShapeSubtreeLayout.bind(this),
            this.analyzeMsoInlineShapeSubtree.bind(this),
        ],
        refine_layout_processors: [
            this.addVmlWrapper.bind(this),
            withSequence(DEFAULT_SPACING_SEQUENCE + 1, this.addTableWrapper.bind(this)),
            this.refineVmlShapes.bind(this),
            this.hideMobileSubtree.bind(this),
        ],
    };

    analyzeMsoInlineShapeSubtree(defaultEmailNodeArguments, { referenceNode }) {
        const { analysis, layout } = defaultEmailNodeArguments;
        if (this.getSubtreeReferenceNode(analysis, "msoInlineShapeSubtree") !== referenceNode) {
            return defaultEmailNodeArguments;
        }
        analysis.facts.isMsoInlineShapeSubtreeRoot = true;
        const variant = this.getSubtreeVariant(analysis, "msoInlineShapeSubtree");
        if (variant === "notMso") {
            this.addVmlLayouts(layout, buildHideIfNotMsoNodes());
            return defaultEmailNodeArguments;
        }
        analysis.topDownConstraints.push(() => ({
            // TODO EGGMAIL: <v:rect supposedly can not contain another <v:rect
            // meaning some configurations are impossible to render with the
            // current implementation, to investigate
            shouldPropagate: true,
            facts: { isVmlWrapperForbidden: true },
        }));
        let href;
        if (variant === "msoButton") {
            href = referenceNode.href;
        }
        analysis.vmlArguments = {
            href,
            backgroundColor: null,
            borderRadius: null,
            height: null,
            horizontalAlignment: null,
            padding: null,
        };
        // TODO EGGMAIL: working HERE
        // here, whatever the actual node is, it should be converted to a
        // span without any spacing, but we still want to keep style rules
        // that could affect what is below (font-size, ...)
        // the tree builder will handle the link/background/border/spacing parts
        return defaultEmailNodeArguments;
    }

    // TODO EGGMAIL: replace background images with VML output
    // handle image borders (as they are now allowed (radius for normal images and width for icons))
    // TODO LIST:
    // div border
    // border-radius not supported for MSO
    // border <= 8px for MSO
    // background-image
    // hybrid-fluid strategy => inline-block => wrapped in table for MSO
    // buttons
    // badges (all native inline-block elements)
    analyzeElementWithBackgroundLayout(defaultEmailNodeArguments, { referenceNode }) {
        const { analysis } = defaultEmailNodeArguments;
        if (
            !referenceNode.matches(`[style*="background-image"]`) ||
            this.getSubtreeVariant(analysis, "responsiveSubtree") === "mobile"
        ) {
            return defaultEmailNodeArguments;
        }
        const styleInfo = this.getStyleInfo(referenceNode);
        const parts = backgroundImageCssToParts(styleInfo.getPropertyValue("background-image"));
        if (!("url" in parts)) {
            return defaultEmailNodeArguments;
        }
        const src = getBgImageURLFromURL(parts.url);
        analysis.facts.vmlWrapperLayouts = this.buildBackgroundImageVmlNodes(referenceNode, src);
        analysis.topDownConstraints.push(() => ({
            // TODO EGGMAIL: <v:rect supposedly can not contain another <v:rect
            // meaning some configurations are impossible to render with the
            // current implementation, to investigate
            shouldPropagate: true,
            facts: { isVmlWrapperForbidden: true },
        }));
        return defaultEmailNodeArguments;
    }

    detectMsoInlineShapeSubtreeLayout(defaultEmailNodeArguments, { referenceNode }) {
        const { layout, analysis } = defaultEmailNodeArguments;
        const computedStyle = this.getComputedStyle(referenceNode);
        const display = computedStyle.getPropertyValue("display");
        const backgroundColor = computedStyle.getPropertyValue("background-color");
        if (
            this.getSubtreeVariant(analysis, "msoInlineShapeSubtree") ||
            !display.includes("inline") ||
            (!this.hasVisibleBorder(referenceNode) && !backgroundColor) ||
            selectElements(referenceNode, "img").length > 0 ||
            this.getSubtreeVariant(analysis, "responsiveSubtree") === "mobile"
        ) {
            return defaultEmailNodeArguments;
        }
        const variant = layout.ancestorTag === "A" ? "msoButton" : "msoBadge";
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            subtree: {
                type: "msoInlineShapeSubtree",
                variants: [variant, "notMso"],
            },
        });
        return defaultEmailNodeArguments;
    }

    hideMobileSubtree(layout, { emailNode }) {
        if (
            !emailNode.analysis.facts.isResponsiveSubtreeRoot ||
            this.getSubtreeVariant(emailNode.analysis, "responsiveSubtree") !== "mobile"
        ) {
            return layout;
        }
        this.addVmlLayouts(layout, buildHideIfNotMsoNodes());
        return layout;
    }

    refineVmlShapes(layout, { emailNode }) {
        const { analysis } = emailNode;
        const variant = this.getSubtreeVariant(analysis, "msoInlineShapeSubtree");
        if (
            !analysis.facts.isMsoInlineShapeSubtreeRoot ||
            (variant !== "msoButton" && variant !== "msoBadge")
        ) {
            return layout;
        }
        const childrenAncestorTagElements = emailNode.children.map((child) =>
            this.config.referenceDocument.createElement(child.layout.ancestorTag || "DIV")
        );
        const span = this.config.referenceDocument.createElement("SPAN");
        const wrapperTag = isAllowedContent(span, childrenAncestorTagElements) ? "SPAN" : "DIV";
        if (!analysis.facts.isVmlWrapperForbidden) {
            layout = new ElementLayout({
                refs: {
                    root: {
                        tag: wrapperTag,
                        // TODO EGGMAIL: get font size and color (and other relevant style)
                    },
                },
            });
        }
        // TODO EGGMAIL: apply required transformations for vmlArguments
        // here, so that we also have access to raw info necessary
        // to create the link/span above
        const originalRender = emailNode.render.bind(emailNode);
        emailNode.render = (context = {}) => {
            this.marginNode = undefined;
            const fragments = originalRender(context);
            for (const fragment of fragments) {
                // neutralize all comment nodes in the intermediate output
                // because the entire html will be put inside a MSO comment
                this.removeComments(fragment);
            }
            const getIfMsoContent = analysis.facts.isVmlWrapperForbidden
                ? () => fragments.map((fragment) => fragment.outerHTML).join("")
                : () => {
                      const htmlContent = fragments.map((fragment) => fragment.outerHTML).join("");
                      return buildInlineShapeVmlContent(analysis.facts.vmlArguments, htmlContent);
                  };
            const msoContent = getIfMsoContent(fragments);
            const commentNodeLayout = new CommentNodeLayout({
                content: wrapIfMso(msoContent),
            });
            return [commentNodeLayout.renderToFragment()];
        };
        return layout;
    }

    removeComments(root) {
        const treeWalker = this.config.referenceDocument.createTreeWalker(
            root,
            NodeFilter.SHOW_COMMENT
        );
        let comment = treeWalker.nextNode();
        while (comment) {
            const next = comment.nextNode();
            comment.remove();
            comment = next;
        }
    }

    addVmlLayouts(layout, vmlLayouts) {
        if (vmlLayouts.prefix) {
            layout.prefixLayouts.push(vmlLayouts.prefix);
        }
        if (vmlLayouts.suffix) {
            layout.suffixLayouts.push(vmlLayouts.suffix);
        }
    }

    addVmlWrapper(layout, { emailNode }) {
        const { analysis } = emailNode;
        if (analysis.facts.isVmlWrapperForbidden || !analysis.facts.vmlWrapperLayouts) {
            return layout;
        }
        this.addVmlLayouts(layout, analysis.facts.vmlWrapperLayouts);
        return layout;
    }

    addTableWrapper(layout, { emailNode }) {
        // check if lastReferenceNode is ElementLayout
        if (!(layout instanceof ElementLayout) || layout.tag !== "DIV") {
            return layout;
        }
        // check if styleinfo of the root has weird display value (non-block)
        const { styleInfo } = layout.getRef();
        const displayValue = styleInfo.getPropertyValue("display");
        if (displayValue !== "" && displayValue !== "block") {
            return layout;
        }
        // get border info from the ref
        // get background-color info from the ref
        const tableWrapperStyleInfo = this.getBorderStyleInfo(styleInfo, layout.tag);
        if (styleInfo.getPropertyValue("background-color") !== "") {
            tableWrapperStyleInfo.set("background-color", styleInfo.get("background-color"));
        }
        if (tableWrapperStyleInfo.size === 0) {
            return layout;
        }
        // check if div has a paddingNode, if it does not => generate
        if (!emailNode.paddingNode) {
            const { paddingNode } = this.buildPaddingNode(emailNode, {
                refs: { root: { style: { width: "100%" } } },
            });
            emailNode.paddingNode = paddingNode;
        }
        // apply border + background-color info on the TABLE element of the paddingNode
        // remove border + background-color from the original div
        // => this does not support round corners (but I don't think we will support
        // it for tables, at least for now).
        const { styleInfo: paddingCellStyleInfo } = emailNode.paddingNode.layout.getRef("cell");
        for (const [propertyName, propertyInfo] of tableWrapperStyleInfo.entries()) {
            paddingCellStyleInfo.set(propertyName, propertyInfo);
            styleInfo.removeProperty(propertyName);
        }
        return layout;
    }

    buildBackgroundImageVmlNodes(referenceNode, src) {
        // TODO EGGMAIL: evaluate if background-position from computed style
        // can not be percentages.
        const width = Math.round(
            this.getBoundingClientRect(referenceNode, DIMENSIONS.DESKTOP).width
        );
        const position = {
            x: parseFloat(this.getStylePropertyValue(referenceNode, "background-position-x")) || 0,
            y: parseFloat(this.getStylePropertyValue(referenceNode, "background-position-y")) || 0,
        };
        return buildBackgroundImageVmlNodes({ position, src, width });
    }
}

registry.category("mail-html-conversion-main-plugins").add(MsoPlugin.id, MsoPlugin);
