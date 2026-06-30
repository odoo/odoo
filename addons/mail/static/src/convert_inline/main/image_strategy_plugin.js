import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { StyleInfo } from "../core/style_models";
import { parseCssValue } from "../css_parsers";
import { ImageLayout, ImageLinkLayout } from "./image_models";

export class ImageStrategyPlugin extends Plugin {
    static id = "imageStrategy";
    static dependencies = [
        "filterContent",
        "measurementSnapshot",
        "responsiveBlock",
        "rules",
        "referenceNode",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeImageLayout.bind(this),
        merge_email_node_overrides: this.discardImageEmailNodeInLink.bind(this),
        attribute_rules_processors: [
            [this.provideAttributeRules.bind(this), ImageStrategyPlugin.id],
        ],
        style_rules_processors: [[this.provideStyleRules.bind(this), ImageStrategyPlugin.id]],
    };

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
        return referenceNode.nodeType === Node.ELEMENT_NODE && referenceNode.matches(".fa");
    }

    getFontIconContent(referenceNode) {
        return this.getFontIconPropertyValue(referenceNode, "content").trim().replace(/['"]/g, "");
    }

    getFontIconPropertyValue(referenceNode, propertyName) {
        return this.getComputedStyle(referenceNode, "::before").getPropertyValue(propertyName);
    }

    analyzeImageLayout({ layout, analysis }, { referenceNode, parentEmailNode }) {
        let detectionResult = this.detectImageLink(referenceNode);
        if (detectionResult) {
            analysis.facts.isImageLink = true;
            analysis.parsingFacts.canMerge = true;
            analysis.parsingFacts.canParentMerge = false;
            layout = this.buildImageLinkLayout(detectionResult);
        } else if ((detectionResult = this.detectImage(referenceNode))) {
            if (parentEmailNode.analysis.facts.isImageLink) {
                analysis.parsingFacts.canParentMerge = true;
            } else {
                analysis.parsingFacts.canParentMerge = false;
                layout = this.buildImageLayout(detectionResult);
            }
            analysis.facts.isImage = true;
            analysis.parsingFacts.canMerge = false;
        }
        if (detectionResult) {
            layout.pluginIds.add(ImageStrategyPlugin.id);
            return { layout, analysis };
        }
    }

    getDefaultImageStyle(shouldBeBlock) {
        // TODO EGGMAIL: remove important, but add rule to remove the css properties
        // from the original styleInfo, (in case its values are important)
        // TODO EGGMAIL: no support for borders (width, radius, ...)
        return Object.assign(
            { "border-width": { value: "0", priority: "important" } },
            shouldBeBlock ? { display: { value: "block", priority: "important" } } : {}
        );
    }

    buildImageRef({ imageNode, shouldBeBlock }) {
        const style = this.getDefaultImageStyle(shouldBeBlock);
        const dimensions = this.extractImageDimensions(imageNode);
        Object.assign(style, dimensions.style);
        const styleInfo = this.getStyleInfo(imageNode).merge(StyleInfo.from(style));
        return {
            attributes: Object.assign(this.getAttributes(imageNode), dimensions.attributes),
            style: styleInfo,
        };
    }

    /**
     * TODO EGGMAIL: clean comments (most of it seems implemented)
     * find a way to generalize the layout building functions
     * so that it does not require direct access to referenceNode, and it can build everything
     * from facts.
     * Register everything needed into facts
     * => the EmailNode should output the image properly instead of the element with the .fa class
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
    buildFontIconImageRef({ imageNode: fontIcon, shouldBeBlock }) {
        const content = this.getFontIconContent(fontIcon) || " ";
        const color = this.getFontIconPropertyValue(fontIcon, "color").replace(/\s/g, "");
        let bg, isTransparent;
        let element = fontIcon;
        do {
            bg = this.getStylePropertyValue(element, "background-color").replace(/\s/g, "");
            isTransparent = bg === "transparent" || bg === "rgba(0,0,0,0)";
            element = element.parentElement;
        } while (isTransparent && element);
        if (isTransparent) {
            bg = "rgb(255,255,255)";
        }
        const computedStyle = this.getComputedStyle(fontIcon);
        const width = parseCssValue(computedStyle.getPropertyValue("width"));
        const height = parseCssValue(computedStyle.getPropertyValue("height"));
        const fontSize = parseCssValue(computedStyle.getPropertyValue("font-size"));
        // render at double the resolution for sharper zoom accuracy
        const renderWidth = Math.max(1, Math.round(width.number * 2));
        const renderHeight = Math.max(1, Math.round(height.number * 2));
        const renderFontSize = Math.max(1, Math.round(fontSize.number * 2));
        const src = `/mail/font_to_img/${content.charCodeAt(0)}/${encodeURIComponent(
            color
        )}/${encodeURIComponent(bg)}/${renderWidth}x${renderHeight}fs${renderFontSize}`;

        const style = Object.assign(this.getDefaultImageStyle(shouldBeBlock), {
            width: `${width.number}px`,
            height: `${height.number}px`,
            "vertical-align": "middle",
        });
        return {
            attributes: Object.assign(this.getAttributes(fontIcon), {
                src,
                width: `${Math.round(width.number)}`,
                height: `${Math.round(height.number)}`,
            }),
            style,
        };
    }

    buildImageLayout(options) {
        let imageRef;
        if (this.isImg({ referenceNode: options.imageNode })) {
            imageRef = this.buildImageRef(options);
        } else {
            imageRef = this.buildFontIconImageRef(options);
        }
        return new ImageLayout(imageRef);
    }

    buildImageLinkLayout({ imageNode, linkNode, shouldBeBlock }) {
        const style = this.getDefaultImageStyle(shouldBeBlock);
        let img;
        if (this.isImg({ referenceNode: imageNode })) {
            img = this.buildImageRef({ imageNode, shouldBeBlock });
        } else {
            img = this.buildFontIconImageRef({ imageNode, shouldBeBlock });
        }
        return new ImageLinkLayout({
            refs: {
                root: {
                    style: this.getStyleInfo(linkNode).merge(StyleInfo.from(style)),
                    attributes: this.getAttributes(linkNode),
                },
                img,
            },
        });
    }

    discardImageEmailNodeInLink({ parentEmailNode, analysis }) {
        if (parentEmailNode.analysis.facts.isImageLink && analysis.facts.isImage) {
            return true;
        }
    }

    detectImageLink(referenceNode) {
        if (referenceNode.nodeName === "A") {
            const visibleChildNodes = this.processChildNodes(
                referenceNode,
                (node) => !this.isInvisible(node)
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

    shouldBeBlock(referenceNode) {
        if (this.isBlock(referenceNode)) {
            return true;
        }
        const isVisibleBlock = (node) => this.isBlock(node) && !this.isInvisible(node);
        const prevSibling = referenceNode.previousSibling;
        const nextSibling = referenceNode.nextSibling;
        const parent = referenceNode.parentElement;
        return (
            this.isBlock(parent) &&
            (!prevSibling || isVisibleBlock(prevSibling)) &&
            (!nextSibling || isVisibleBlock(nextSibling))
        );
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
