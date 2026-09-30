import { backgroundImageCssToParts, getBgImageURLFromURL } from "@html_editor/utils/image";
import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { buildBackgroundImageVmlNodes } from "./mso_vml_models";
import { DIMENSIONS } from "../core/utils";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { ElementLayout } from "../core/render_models";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class MsoPlugin extends Plugin {
    static id = "mso";
    static dependencies = ["border", "measurementSnapshot", "rules", "spacing"];
    resources = {
        element_layout_analysis_processors: [
            this.analyzeElementWithBackgroundLayout.bind(this),
            this.analyzeButtonLayout.bind(this),
        ],
        refine_layout_processors: [
            this.addVmlWrapper.bind(this),
            withSequence(DEFAULT_SPACING_SEQUENCE + 1, this.addTableWrapper.bind(this)),
        ],
    };

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
        if (
            referenceNode.nodeType !== Node.ELEMENT_NODE ||
            !referenceNode.matches(`[style*="background-image"]`)
        ) {
            return defaultEmailNodeArguments;
        }
        const styleInfo = this.getStyleInfo(referenceNode);
        const parts = backgroundImageCssToParts(styleInfo.getPropertyValue("background-image"));
        if (!("url" in parts)) {
            return defaultEmailNodeArguments;
        }
        const { analysis } = defaultEmailNodeArguments;
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

    analyzeButtonLayout(defaultEmailNodeArguments, { referenceNode }) {
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return defaultEmailNodeArguments;
        }
        const computedStyle = this.getComputedStyle(referenceNode);
        const display = computedStyle.getPropertyValue("display");
        const backgroundColor = computedStyle.getPropertyValue("background-color");

        if (
            !display.includes("inline") ||
            (!this.hasVisibleBorder(referenceNode) && !backgroundColor) ||
            selectElements(referenceNode, "img").length > 0
        ) {
            return defaultEmailNodeArguments;
        }
        const color = computedStyle.getPropertyValue("color");

        // inline-block or inline element, with border or background-color
        // check if alone or not on its line (if alone => rectangle with background,
        // not alone => set color as background color and remove background color)
        // detect interesting elements
        // extract relevant data for rendering, don't build yet
        // add the same topdown constraint as for background
        // at refinement time, check if vmlwrapper is not forbidden => build
        // if forbidden => set color to background-color, remove background-color
        // (alternative VML solution, not a rectangle, but the same element without background)
        return defaultEmailNodeArguments;
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
            if (analysis.facts.vmlFallbackLayouts) {
                this.addVmlLayouts(layout, analysis.facts.vmlFallbackLayouts);
            }
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
