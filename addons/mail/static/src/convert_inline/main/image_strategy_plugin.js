import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { StyleInfo } from "../core/style_models";
import { parseCssValue } from "../css_parsers";
import { ImageLayout, ImageLinkLayout } from "./image_models";
import { Rules } from "../core/rules_models";
import { isParagraphRelatedElement, isPhrasingContent } from "@html_editor/utils/dom_info";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

export class ImageStrategyPlugin extends Plugin {
    static id = "imageStrategy";
    static dependencies = [
        "measurementSnapshot",
        "responsiveBlock",
        "rules",
        "referenceNode",
        "render",
        "spacing",
        "style",
    ];
    resources = {
        element_layout_analysis_processors: [this.analyzeImageLayout.bind(this)],
        merge_email_node_overrides: this.discardImageEmailNodeInLink.bind(this),
        attribute_rules_processors: [
            [this.provideAttributeRules.bind(this), ImageStrategyPlugin.id],
        ],
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE,
            this.refineImage.bind(this)
        ),
        style_rules_processors: [[this.provideStyleRules.bind(this), ImageStrategyPlugin.id]],
    };

    setup() {
        this.imageBorderStyleRules = new Rules();
        this.provideImageBorderStyleRules();
    }

    provideImageBorderStyleRules() {
        const borderRules = this.imageBorderStyleRules.forPlugin(ImageStrategyPlugin.id);
        borderRules.allow(/^border(-.*)?$/, {
            when: ({ propertyName }) =>
                propertyName !== "border-spacing" && propertyName !== "border-collapse",
        });
    }

    // fix images padding
    // padding concern is only there for microsoft outlook => should be solved then
    // that concern is actually there for any node which is not a td
    // either keep padding on image to stay coherent with the current padding logic
    // OR remove padding everywhere and make it a MSO concern?
    // background images => vml strategy?
    // attachment thumbnails
    // media list img without height?
    // object-fit: cover?
    // image with 100% height in cell
    // remove height attribute in card images?
    // card-img-top height?
    // mx-auto in table cells?
    // img with font-family simple quote/double quote issue?
    // font icons to images

    provideAttributeRules(rules) {
        // height and width attributes are specified through applyLayoutStrategy
        rules.block("height", { when: this.isImg.bind(this) });
        rules.block("width", { when: this.isImg.bind(this) });
    }

    provideStyleRules(rules) {
        // TODO EGGMAIL: maybe fine tune and only accept some values
        rules.allow("width", { when: this.isImg.bind(this) });
        rules.allow("height", { when: this.isImg.bind(this) });
        rules.allow("max-width", { when: this.isImg.bind(this) });
        // Since width/height can be set on an img, we can't blindly allow border
        // nor padding, as the standard rendering box-sizing is "content-box"
        // meaning all calculations for width need to be made with padding
        // and border in mind.
        // border is added back manually using getBorderStyleInfo when building
        // layouts
        rules.block(/^border(-.*)?$/, { when: this.isImg.bind(this) });
        // padding is handled by refineImage
        rules.block(/^padding(-(top|right|bottom|left))?$/, { when: this.isImg.bind(this) });
    }

    refineImage(layout, { emailNode }) {
        if (!emailNode.analysis.facts.isImage && !emailNode.analysis.facts.isImageLink) {
            return layout;
        }
        const imgRef = emailNode.analysis.facts.isImage ? "root" : "img";
        // Neutralize borders in cases that never support padding.
        // All imageLinks or images that are not handled in this function AND have width 100%
        // can not have a border because of box-sizing: content-box (overlapping issue).
        const neutralizeBorder = (callback = () => {}) => {
            const styleInfo = layout.getRef(imgRef).styleInfo;
            const borderStyleInfo = this.filterStyleInfo(
                styleInfo,
                emailNode.analysis.imageNode,
                this.imageBorderStyleRules
            );
            for (const [propertyName, propertyInfo] of borderStyleInfo.entries()) {
                styleInfo.removeProperty(propertyName);
                callback(propertyName, propertyInfo);
            }
        };
        const width = layout.getRef().styleInfo.getPropertyValue("width");
        const parentRenderNode = this.config.referenceDocument.createElement(
            emailNode.parent.layout.descendantTag
        );
        if (
            !this.isBlock(parentRenderNode, { evaluateDisconnected: true }) ||
            // TODO EGGMAIL: if paragraphRelatedElement and link/image is the only
            // child, the paragraph can be replaced by a DIV (like buttonStrategy)
            isParagraphRelatedElement(parentRenderNode)
        ) {
            if (width === "100%") {
                neutralizeBorder();
            }
            return layout;
        }
        let needsFullWidthSpacing = false;
        if (width) {
            const parsedWidth = parseCssValue(width);
            needsFullWidthSpacing = parsedWidth.unit === "%";
        }
        const spacingNodeArgs = needsFullWidthSpacing
            ? { refs: { root: { style: { width: "100%" } } } }
            : {};
        const paddingNode = this.buildPaddingNode(emailNode, spacingNodeArgs);
        if (paddingNode) {
            // image padding behaves like a margin (space around the image)
            emailNode.marginNode = paddingNode;
            // recover border from the image email node and put it on the
            // spacing node
            neutralizeBorder((propertyName, propertyInfo) => {
                paddingNode.layout.getRef("cell").styleInfo.set(propertyName, propertyInfo);
            });
        }
        return layout;
    }

    isImg({ referenceNode }) {
        return referenceNode.nodeName === "IMG";
    }

    /**
     * TODO EGGMAIL: should we discard fa icons without content?
     */
    isFontIcon({ referenceNode }) {
        // TODO EGGMAIL: check new material icons PR, and if this selector needs to be
        // adapted/completed
        return referenceNode.nodeType === Node.ELEMENT_NODE && referenceNode.matches(".fa,.oi");
    }

    getFontIconContent(referenceNode) {
        return this.getFontIconPropertyValue(referenceNode, "content").trim().replace(/['"]/g, "");
    }

    getFontIconPropertyValue(referenceNode, propertyName) {
        return this.getComputedStyle(referenceNode, "::before").getPropertyValue(propertyName);
    }

    /**
     * Simplified scaling parsing
     * TODO EGGMAIL: evaluate if this needs to be completed Y scaling or more
     *
     * @param {string} transform property value
     * @returns horizontal scaling factor
     */
    getScaling(transform) {
        let scale;
        try {
            const matrix = new DOMMatrixReadOnly(transform);
            scale = matrix.a;
        } catch {
            scale = 1;
        }
        return scale;
    }

    analyzeImageLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        let { layout, analysis } = defaultEmailNodeArguments;
        let detectionResult = this.detectImageLink(referenceNode);
        if (detectionResult) {
            analysis.facts.imageNode = detectionResult.imageNode;
            analysis.facts.linkNode = detectionResult.linkNode;
            analysis.facts.isImageLink = true;
            analysis.parsingFacts.canMerge = true;
            analysis.parsingFacts.canParentMerge = false;
            layout = this.buildImageLinkLayout(detectionResult);
        } else if ((detectionResult = this.detectImage(referenceNode))) {
            if (parentEmailNode.analysis.facts.isImageLink) {
                // see discardImageEmailNodeInLink merge override
                analysis.parsingFacts.canParentMerge = true;
            } else {
                analysis.parsingFacts.canParentMerge = false;
                layout = this.buildImageLayout(detectionResult);
            }
            analysis.facts.imageNode = detectionResult.imageNode;
            analysis.facts.isImage = true;
            analysis.parsingFacts.canMerge = false;
        }
        if (detectionResult) {
            layout.pluginIds.add(ImageStrategyPlugin.id);
            return { layout, analysis };
        }
        return defaultEmailNodeArguments;
    }

    getForcedImageStyle({ shouldBeBlock }) {
        // TODO EGGMAIL: remove important, but add rule to remove the css properties
        // from the original styleInfo, (in case its values are important)
        const styleInfo = new StyleInfo();
        if (shouldBeBlock) {
            styleInfo.setProperty("display", "block", "important", Infinity);
        }
        return styleInfo;
    }

    buildImageRef({ imageNode, shouldBeBlock }) {
        const dimensions = this.extractImageDimensions(imageNode);
        if (shouldBeBlock === undefined && dimensions.style.width === "100%") {
            // 100% extracted width removes the ambiguity for display: block
            shouldBeBlock = true;
        }
        const forcedStyleInfo = this.getForcedImageStyle({ shouldBeBlock });
        const styleInfo = this.getStyleInfo(imageNode)
            .merge(StyleInfo.from(dimensions.style))
            .merge(forcedStyleInfo);
        return {
            attributes: Object.assign(this.getAttributes(imageNode), dimensions.attributes),
            style: styleInfo,
        };
    }

    convertCSSColorToPILRgba(color) {
        const obj = convertCSSColorToRgba(color);
        const bind8bitsIntToHex = (value) =>
            Math.max(0, Math.min(255, Math.round(value)))
                .toString(16)
                .padStart(2, "0");
        if (obj) {
            obj.red = bind8bitsIntToHex(obj.red);
            obj.green = bind8bitsIntToHex(obj.green);
            obj.blue = bind8bitsIntToHex(obj.blue);
            // convertCSSColorToRgba returns opacity as a float percentage,
            // but PIL library needs a 8 bits integer.
            obj.opacity = bind8bitsIntToHex((255 * obj.opacity) / 100);
            return `${obj.red}${obj.green}${obj.blue}${obj.opacity}`;
        }
        return false;
    }

    /**
     * TODO EGGMAIL: clean comments (most of it seems implemented)
     * find a way to generalize the layout building functions
     * so that it does not require direct access to referenceNode, and it can build everything
     * from facts.
     * Register everything needed into facts
     * => the EmailNode should output the image properly instead of the element with the .fa,.oi class
     */
    /**
     * can get computedStyle, ::before
     * can get dimensions directly without needing fit-content stuff
     * can get font-size directly
     * background capture required
     *
     * need to add an argument to getComputedStyle and check
     * all usages with 2 args
     * add the argument to all derived function? -> maybe
     * not necessary, as usage is pretty niche, and it's
     * always best to use getComputedStyle anyways
     *
     * all transformations should happen before constraints propagation
     * the Emailnode entity should be properly classified as an img
     * check if the resulting img should be handled as a normal
     * img or if it requires exceptions
     * include the spacing in the final image, use the combination of
     * dimensions + font-size to get the proper spacing
     */
    /**
     * <i>/<span> fa + circle should be centered properly when the icon is converted into an image
     *
     */
    // TODO EGGMAIL: implement the parsing variant to support OI icons (vs FA icons)
    buildFontIconImageRef({ imageNode: fontIcon, shouldBeBlock }) {
        // TODO EGGMAIL: rgba is an alias for rgb
        // rgb can also have an alpha channel
        // the value should be normalized for PILLOW
        // maybe it should be normalized for emails too.
        const font = fontIcon.matches(".fa") ? "fa" : "oi";
        const isCustom = fontIcon.matches("[data-icon^='oi_'");
        const content = this.getFontIconContent(fontIcon) || " ";
        const icon = font === "fa" || isCustom ? content.codePointAt(0) : content;
        const color = this.getFontIconPropertyValue(fontIcon, "color");
        const pilColor =
            this.convertCSSColorToPILRgba(color) || this.convertCSSColorToPILRgba("rgb(0,0,0)");
        let bg, isTransparent;
        let element = fontIcon;
        do {
            bg = this.getStylePropertyValue(element, "background-color").replace(/\s/g, "");
            isTransparent = bg === "transparent" || bg === "rgba(0,0,0,0)";
            element = element.parentElement;
        } while (isTransparent && element && isPhrasingContent(element));
        if (isTransparent) {
            bg = "rgba(0,0,0,0)";
        }
        const pilBg =
            this.convertCSSColorToPILRgba(bg) || this.convertCSSColorToPILRgba("rgba(0,0,0,0)");
        const fontSize = parseCssValue(this.getFontIconPropertyValue(fontIcon, "font-size"));
        const iconScale = this.getScaling(this.getFontIconPropertyValue(fontIcon, "transform"));
        const scaledFontSize = fontSize.number * iconScale;
        const computedStyle = this.getComputedStyle(fontIcon);
        const width = parseCssValue(computedStyle.getPropertyValue("width"));
        const height = parseCssValue(computedStyle.getPropertyValue("height"));
        const containerScale = this.getScaling(computedStyle.getPropertyValue("transform"));
        const scaledWidth = Math.max(width.number * containerScale, scaledFontSize);
        const scaledHeight = Math.max(height.number * containerScale, scaledFontSize);
        // render at double the resolution for sharper zoom accuracy
        const renderWidth = Math.max(1, Math.round(scaledWidth * 2));
        const renderHeight = Math.max(1, Math.round(scaledHeight * 2));
        const renderFontSize = Math.max(1, Math.round(scaledFontSize * 2));
        const src = `/mail/font_to_img/${icon}/${font}/${pilColor}/${pilBg}/${renderWidth}x${renderHeight}fs${renderFontSize}`;
        const defaultStyleInfo = StyleInfo.from({
            width: `${scaledWidth}px`,
            height: `${scaledHeight}px`,
            "vertical-align": "middle",
        });
        const forcedStyleInfo = this.getForcedImageStyle({ shouldBeBlock });
        return {
            attributes: Object.assign(this.getAttributes(fontIcon), {
                src,
                width: `${Math.round(scaledWidth)}`,
                height: `${Math.round(scaledHeight)}`,
            }),
            style: defaultStyleInfo.merge(forcedStyleInfo),
        };
    }

    getBorderStyleInfo(imageNode) {
        return this.filterStyleInfo(
            this.getRawStyleInfo(imageNode),
            imageNode,
            this.imageBorderStyleRules
        );
    }

    buildImageLayout(options) {
        let imageRef;
        if (this.isImg({ referenceNode: options.imageNode })) {
            imageRef = this.buildImageRef(options);
        } else {
            imageRef = this.buildFontIconImageRef(options);
        }
        imageRef.style = imageRef.style.merge(this.getBorderStyleInfo(options.imageNode));
        return new ImageLayout({ refs: { root: imageRef } });
    }

    buildImageLinkLayout({ imageNode, linkNode, shouldBeBlock }) {
        const forcedStyleInfo = this.getForcedImageStyle({ shouldBeBlock });
        let imageRef;
        if (this.isImg({ referenceNode: imageNode })) {
            imageRef = this.buildImageRef({ imageNode, shouldBeBlock });
        } else {
            imageRef = this.buildFontIconImageRef({ imageNode, shouldBeBlock });
        }
        imageRef.style = imageRef.style.merge(this.getBorderStyleInfo(imageNode));
        return new ImageLinkLayout({
            refs: {
                root: {
                    style: this.getStyleInfo(linkNode).merge(forcedStyleInfo),
                    attributes: this.getAttributes(linkNode),
                },
                img: imageRef,
            },
        });
    }

    discardImageEmailNodeInLink(parentEmailNode, { analysis }) {
        if (parentEmailNode.analysis.facts.isImageLink && analysis.facts.isImage) {
            // the imageLink will be handled as a whole from the link, no need to
            // keep the image node in the render tree. Only the image padding
            // needs to be kept.
            parentEmailNode.analysis.facts.desktopPaddingStyleInfo =
                analysis.facts.desktopPaddingStyleInfo;
            return true;
        }
    }

    detectImageLink(referenceNode) {
        if (referenceNode.nodeName === "A") {
            const visibleChildNodes = this.processChildNodes(
                referenceNode,
                (node) => !this.isDiscarded(node)
            );
            if (
                visibleChildNodes.length === 1 &&
                (this.isImg({ referenceNode: visibleChildNodes[0] }) ||
                    this.isFontIcon({ referenceNode: visibleChildNodes[0] }))
            ) {
                const imageNode = visibleChildNodes[0];
                return {
                    imageNode: imageNode,
                    linkNode: referenceNode,
                    shouldBeBlock: this.shouldBeBlock(referenceNode),
                };
            }
        }
    }

    detectImage(referenceNode) {
        if (this.isImg({ referenceNode }) || this.isFontIcon({ referenceNode })) {
            return {
                imageNode: referenceNode,
                shouldBeBlock: this.shouldBeBlock(referenceNode),
            };
        }
    }

    /**
     * @param {Element} referenceNode
     * @returns {Boolean | undefined} a boolean if block status can be
     * determined with certainty, undefined if block status should depend on
     * email dimensions of the image @see extractImageDimensions
     */
    shouldBeBlock(referenceNode) {
        if (this.isBlock(referenceNode)) {
            return true;
        }
        const parent = referenceNode.parentElement;
        if (!this.isBlock(parent) || isParagraphRelatedElement(parent)) {
            return false;
        }
        let prevSibling, nextSibling;
        let current = referenceNode;
        while ((current = current.previousSibling)) {
            if (!this.isDiscarded(current)) {
                prevSibling = current;
                break;
            }
        }
        current = referenceNode;
        while ((current = current.nextSibling)) {
            if (!this.isDiscarded(current)) {
                nextSibling = current;
                break;
            }
        }
        const isVisibleBlock = (node) => this.isBlock(node) && !this.isDiscarded(node);
        const isIsolatedAmongBlocks =
            (!prevSibling || isVisibleBlock(prevSibling)) &&
            (!nextSibling || isVisibleBlock(nextSibling));
        if (!isIsolatedAmongBlocks) {
            return false;
        }
    }

    extractImageDimensions(referenceNode) {
        const styleInfo = this.getStyleInfo(referenceNode);
        const attributes = {};
        const style = {};
        const width = parseCssValue(styleInfo.getPropertyValue("width"));
        const height = parseCssValue(styleInfo.getPropertyValue("height"));
        const maxWidth = parseCssValue(styleInfo.getPropertyValue("max-width"));
        width.rendered = parseCssValue(this.getStylePropertyValue(referenceNode, "width"));
        width.natural = referenceNode.naturalWidth;
        height.natural = referenceNode.naturalHeight;
        if (height.unit === "px") {
            if (width.unit !== "px") {
                if (width.natural > 0 && height.natural > 0) {
                    width.number = (height.number * width.natural) / height.natural;
                } else {
                    width.number = width.rendered.number || 0;
                }
                width.unit = "px";
            }
            attributes.width = `${Math.round(width.number)}`;
            attributes.height = `${Math.round(height.number)}`;
            Object.assign(style, { width: `${width.number}px`, height: `${height.number}px` });
        } else if (width.unit === "px") {
            attributes.width = `${Math.round(width.number)}`;
            Object.assign(style, { width: `${width.number}px`, height: "auto" });
        } else {
            style.height = "auto";
            if (width.unit === "%") {
                style.width = `${width.number}%`;
            } else {
                style.width = `100%`;
            }
            if (maxWidth.unit === "px") {
                attributes.width = `${Math.round(maxWidth.number)}`;
                style["max-width"] = `${maxWidth.number}px`;
            } else {
                attributes.width = `${Math.round(width.rendered.number)}`;
            }
        }
        return { attributes, style };
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ImageStrategyPlugin.id, ImageStrategyPlugin);
