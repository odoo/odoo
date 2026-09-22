import { backgroundImageCssToParts, getBgImageURLFromURL } from "@html_editor/utils/image";
import { Plugin } from "@mail/convert_inline/plugin";
import { registry } from "@web/core/registry";
import {
    buildBackgroundImageVmlLayout,
    buildHideFromMsoLayout,
    cssBackgroundPositionToVml,
    cssBorderRadiusToVml,
    MsoOnlyLayout,
    VmlRoundRectLayout,
} from "@mail/convert_inline/main/mso_vml_models";
import {
    computeCompositeColor,
    DIMENSIONS,
    DIRECTION_VARIANTS,
    isCSSColorTransparent,
    VERTICAL_DIRECTION_VARIANTS,
} from "@mail/convert_inline/core/utils";
import { withSequence } from "@html_editor/utils/resource";
import { DEFAULT_SPACING_SEQUENCE } from "@mail/convert_inline/main/spacing_plugin";
import { ElementLayout, TextNodeLayout } from "@mail/convert_inline/core/render_models";
import { selectElements } from "@html_editor/utils/dom_traversal";
import {
    isParagraphRelatedElement,
    isPhrasingContent,
    paragraphRelatedElements,
} from "@html_editor/utils/dom_info";
import { convertRgbaToCSSColor, rgbaToHex } from "@web/core/utils/colors";
import { parseCssValue } from "@mail/convert_inline/css_parsers";
import { Rules } from "@mail/convert_inline/core/rules_models";

export class MsoPlugin extends Plugin {
    static id = "mso";
    static dependencies = [
        "border",
        "measurementSnapshot",
        "filterContent",
        "referenceNode",
        "render",
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
            this.addBackgroundImageVmlWrapper.bind(this),
            withSequence(DEFAULT_SPACING_SEQUENCE - 1, this.refineVmlShapes.bind(this)),
            // after spacing_plugin, to override its spacing nodes
            withSequence(DEFAULT_SPACING_SEQUENCE + 1, this.refineVmlShapeSpacing.bind(this)),
            withSequence(DEFAULT_SPACING_SEQUENCE + 1, this.addTableWrapper.bind(this)),
            this.hideMobileSubtree.bind(this),
        ],
        mso_background_extraction_style_rules_processors:
            this.provideBackgroundExtractionStyleRules.bind(this),
        mso_vml_inner_wrapper_style_rules_processors: [
            this.provideTextAndFontStyleRules,
            this.provideVmlInnerWrapperStyleRules.bind(this),
        ],
    };

    setup() {
        this.backgroundExtractionRules = this.processRules(
            "mso_background_extraction_style_rules_processors",
            new Rules()
        );
        this.vmlInnerWrapperStyleRules = this.processRules(
            "mso_vml_inner_wrapper_style_rules_processors",
            new Rules()
        );
    }

    provideVmlInnerWrapperStyleRules(rules) {
        rules.allow("direction");
    }

    provideBackgroundExtractionStyleRules(rules) {
        // extract the combined result (background-color and background image)
        // see rules in image_strategy_plugin and filter_content_plugin
        rules.allow("background-color");
        rules.allow("background");
        rules.allow("background-position");
        rules.allow("background-image");
        rules.allow("background-size");
    }

    getVmlStyleInfo(styleInfo, referenceNode) {
        return this.filterStyleInfo(styleInfo, referenceNode, this.vmlInnerWrapperStyleRules);
    }

    analyzeMsoInlineShapeSubtree(defaultEmailNodeArguments, { referenceNode }) {
        const { analysis, layout } = defaultEmailNodeArguments;
        if (this.getSubtreeReferenceNode(analysis, "msoInlineShapeSubtree") !== referenceNode) {
            return defaultEmailNodeArguments;
        }
        analysis.facts.isMsoInlineShapeSubtreeRoot = true;
        const variant = this.getSubtreeVariant(analysis, "msoInlineShapeSubtree");
        if (variant === "notMso") {
            return defaultEmailNodeArguments;
        }
        analysis.topDownConstraints.push(() => ({
            // TODO EGGMAIL: <v:rect supposedly can not contain another <v:rect
            // meaning some configurations are impossible to render with the
            // current implementation, to investigate
            shouldPropagate: true,
            facts: { isVmlWrapperForbidden: true },
        }));
        analysis.facts.vmlArguments = this.extractInlineShapeVmlProps(referenceNode);
        const styleInfo = layout.getRef().styleInfo;
        // specific style that should be inherited by html inside the VML
        analysis.facts.vmlContextStyleInfo = this.getVmlStyleInfo(styleInfo, referenceNode);
        // TODO EGGMAIL: find an alternative strategy that does not use VML, eg
        // discard the button shape and display it as a link, or prevent such
        // configurations in the editor
        this.analyzeMsoInlineShapeMargin(analysis, referenceNode);
        return defaultEmailNodeArguments;
    }

    /**
     * The margin of an inline shape can only be rendered for MSO (as a spacing
     * table) if the shape is the only child of a block. A paragraph related
     * parent is converted to a DIV, since a table can not be inside it.
     * TODO EGGMAIL: there is no reliable approximation of the margin of an
     * inline shape surrounded by other content, it is dropped for MSO.
     */
    analyzeMsoInlineShapeMargin(analysis, referenceNode) {
        const parent = referenceNode.parentElement;
        if (
            !parent ||
            !this.isBlock(parent) ||
            this.processChildNodes(parent, (node) => !this.isDiscarded(node)).length !== 1
        ) {
            return;
        }
        analysis.facts.isMsoInlineShapeMarginAllowed = true;
        analysis.bottomUpConstraints.push((emailNode) => {
            // Same strategy as for buttons with width 100% (@see button_strategy_plugin)
            if (
                emailNode.lastReferenceNode !== parent ||
                !isParagraphRelatedElement(parent) ||
                !(emailNode.layout instanceof ElementLayout)
            ) {
                return;
            }
            emailNode.layout.tag = "DIV";
            // Neutralize the margin of the paragraph related element, it will
            // be applied through a spacing wrapper (as for all div).
            emailNode.layout.replaceStyleInfo(
                this.filterStyleInfo(
                    emailNode.layout.getRef().styleInfo,
                    emailNode.layout.descendantTag
                )
            );
        });
    }

    extractInlineShapeVmlProps(referenceNode) {
        return {
            fill: this.extractVmlFill(referenceNode),
            stroke: this.extractVmlStroke(referenceNode),
            arcSize: this.extractVmlArcSize(referenceNode),
            padding: this.extractVmlPadding(referenceNode),
            href: this.extractVmlHref(referenceNode),
        };
    }

    extractVmlFill(referenceNode) {
        const color = this.getStylePropertyValue(referenceNode, "background-color");
        if (isCSSColorTransparent(color)) {
            return null;
        }
        // TODO EGGMAIL: handle more ancestors for transparency composition?
        const { red, green, blue, opacity } = computeCompositeColor([color, "rgb(255, 255, 255)"]);
        return {
            color: convertRgbaToCSSColor(red, green, blue, opacity).substring(0, 7),
        };
    }

    extractVmlStroke(referenceNode) {
        if (!this.hasVisibleBorder(referenceNode)) {
            return null;
        }
        // TODO EGGMAIL: investigate if this very simplified extraction is adequate
        const computedStyle = this.getComputedStyle(referenceNode);
        let width, color;
        for (const side of DIRECTION_VARIANTS) {
            width = parseFloat(computedStyle.getPropertyValue(`border-${side}-width`));
            if (width > 0) {
                color = computedStyle.getPropertyValue(`border-${side}-color`);
                break;
            }
        }
        color = rgbaToHex(color).substring(0, 7);
        return {
            width,
            color,
        };
    }

    extractVmlArcSize(referenceNode) {
        const [horizontal, vertical = horizontal] = this.getStylePropertyValue(
            referenceNode,
            "border-top-left-radius"
        ).split(/\s+/);
        const resolveRadius = (value, dimension) => {
            value = parseCssValue(value);
            if (value.unit === "px") {
                return value.number;
            } else if (value.unit === "%") {
                return (value.number * dimension) / 100;
            } else {
                return 0;
            }
        };
        const { height, width } = this.getBoundingClientRect(referenceNode);
        const radius = Math.min(resolveRadius(horizontal, width), resolveRadius(vertical, height));
        return cssBorderRadiusToVml({ radius, height, width });
    }

    extractVmlPadding(referenceNode) {
        const computedStyle = this.getComputedStyle(referenceNode);
        const getPadding = (side) => {
            const value = parseCssValue(computedStyle.getPropertyValue(`padding-${side}`));
            if (value.unit !== "px") {
                // default spacing values for button/badge
                return VERTICAL_DIRECTION_VARIANTS.includes(side) ? 5 : 10;
            }
            return value.number;
        };
        return {
            top: getPadding("top"),
            right: getPadding("right"),
            bottom: getPadding("bottom"),
            left: getPadding("left"),
        };
    }

    extractVmlHref(referenceNode) {
        return referenceNode.getAttribute("href");
    }

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
        analysis.facts.backgroundImageVmlLayout = this.buildBackgroundImageVmlLayout(
            referenceNode,
            src
        );
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
            !referenceNode.matches(".badge, a.btn") ||
            (!this.hasVisibleBorder(referenceNode) && isCSSColorTransparent(backgroundColor)) ||
            selectElements(referenceNode, "img").length > 0 ||
            this.getSubtreeVariant(analysis, "responsiveSubtree") === "mobile"
        ) {
            return defaultEmailNodeArguments;
        }
        const variant = layout.ancestorTag === "A" ? "msoButton" : "msoBadge";
        Object.assign(analysis.buildDirectives, {
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
        emailNode.addWrapper(buildHideFromMsoLayout(), { around: "margin" });
        return layout;
    }

    isMsoInlineShapeRoot(emailNode) {
        const { analysis } = emailNode;
        return (
            analysis.facts.isMsoInlineShapeSubtreeRoot &&
            this.getSubtreeVariant(analysis, "msoInlineShapeSubtree") !== "notMso"
        );
    }

    refineVmlShapes(layout, { emailNode }) {
        const { analysis } = emailNode;
        if (!analysis.facts.isMsoInlineShapeSubtreeRoot) {
            return layout;
        }
        if (!this.isMsoInlineShapeRoot(emailNode)) {
            // notMso variant
            emailNode.addWrapper(buildHideFromMsoLayout(), { around: "margin" });
            return layout;
        }
        emailNode.addWrapper(new MsoOnlyLayout(), { around: "margin" });
        if (analysis.facts.isVmlWrapperForbidden) {
            return layout;
        }
        emailNode.addWrapper(new VmlRoundRectLayout(analysis.facts.vmlArguments), {
            around: "layout",
        });
        const isWrapperPhrasingContent = emailNode.children.every((child) => {
            if (child.layout instanceof TextNodeLayout) {
                return true;
            }
            return isPhrasingContent(
                this.config.referenceDocument.createElement(child.layout.ancestorTag || "DIV")
            );
        });
        return new ElementLayout({
            refs: {
                root: {
                    tag: isWrapperPhrasingContent ? "SPAN" : "DIV",
                    style: analysis.facts.vmlContextStyleInfo,
                },
            },
        });
    }

    /**
     * The VML shape replaces the padding, and the margin is rendered as a
     * spacing table around it when possible (inside the MSO only branch).
     */
    refineVmlShapeSpacing(layout, { emailNode }) {
        const { analysis } = emailNode;
        if (!this.isMsoInlineShapeRoot(emailNode) || analysis.facts.isVmlWrapperForbidden) {
            return layout;
        }
        // Padding is already included in the VML shape
        emailNode.paddingNode = undefined;
        emailNode.marginNode = undefined;
        if (
            !analysis.facts.isMsoInlineShapeMarginAllowed ||
            // A table can not be inside a paragraph related element
            paragraphRelatedElements.includes(emailNode.parent?.layout.descendantTag)
        ) {
            return layout;
        }
        const { marginNode, isRelevant } = this.buildMarginNode(emailNode, {
            refs: { root: { style: { width: "100%" } } },
        });
        if (!isRelevant) {
            return layout;
        }
        const align = this.getHorizontalAlignment(emailNode.firstReferenceNode.parentElement);
        if (align) {
            marginNode.layout.setAttributes({ attributes: { align } });
            marginNode.layout.setAttributes({ attributes: { align } }, "cell");
        }
        emailNode.marginNode = marginNode;
        return layout;
    }

    /**
     * @param {HTMLElement} element
     * @returns {"left"|"center"|"right"|undefined} alignment of the inline
     *          content of element
     */
    getHorizontalAlignment(element) {
        const computedStyle = this.getComputedStyle(element);
        const textAlign = computedStyle.getPropertyValue("text-align");
        const isRtl = computedStyle.getPropertyValue("direction") === "rtl";
        switch (textAlign) {
            case "left":
            case "center":
            case "right":
                return textAlign;
            case "start":
                return isRtl ? "right" : "left";
            case "end":
                return isRtl ? "left" : "right";
        }
    }

    addBackgroundImageVmlWrapper(layout, { emailNode }) {
        const { analysis } = emailNode;
        if (analysis.facts.isVmlWrapperForbidden || !analysis.facts.backgroundImageVmlLayout) {
            return layout;
        }
        emailNode.addWrapper(analysis.facts.backgroundImageVmlLayout, { around: "layout" });
        return layout;
    }

    addTableWrapper(layout, { emailNode }) {
        if (!(layout instanceof ElementLayout) || layout.tag !== "DIV") {
            return layout;
        }
        const { styleInfo } = layout.getRef();
        const displayValue = styleInfo.getPropertyValue("display");
        if (displayValue !== "" && displayValue !== "block") {
            return layout;
        }
        const tableWrapperStyleInfo = this.getBorderStyleInfo(styleInfo, layout.tag);
        tableWrapperStyleInfo.merge(
            this.filterStyleInfo(styleInfo, "DIV", this.backgroundExtractionRules)
        );
        if (tableWrapperStyleInfo.size === 0) {
            return layout;
        }
        if (!emailNode.paddingNode) {
            const { paddingNode } = this.buildPaddingNode(emailNode, {
                refs: { root: { style: { width: "100%" } } },
            });
            emailNode.paddingNode = paddingNode;
        }
        const { styleInfo: paddingCellStyleInfo } = emailNode.paddingNode.layout.getRef("cell");
        for (const [propertyName, propertyInfo] of tableWrapperStyleInfo.entries()) {
            paddingCellStyleInfo.set(propertyName, propertyInfo);
            styleInfo.removeProperty(propertyName);
        }
        return layout;
    }

    buildBackgroundImageVmlLayout(referenceNode, src) {
        // TODO EGGMAIL: evaluate if background-position from computed style
        // can not be percentages.
        const width = Math.round(
            this.getBoundingClientRect(referenceNode, DIMENSIONS.DESKTOP).width
        );
        const position = {
            x: cssBackgroundPositionToVml(
                parseFloat(this.getStylePropertyValue(referenceNode, "background-position-x")) || 0
            ),
            y: cssBackgroundPositionToVml(
                parseFloat(this.getStylePropertyValue(referenceNode, "background-position-y")) || 0
            ),
        };
        return buildBackgroundImageVmlLayout({ position, src, width });
    }
}

registry.category("mail-html-conversion-main-plugins").add(MsoPlugin.id, MsoPlugin);
