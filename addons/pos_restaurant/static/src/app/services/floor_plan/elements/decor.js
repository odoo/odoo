import { TEXT_DEFAULT_FONT_SIZE } from "../../../screens/floor_screen/floor_plan_editor/utils/text";
import { getColorRGBA } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import {
    applyDefaults,
    removeNullishAndDefault,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { FloorElement } from "./floor_element";

const defaults = {
    allowText: true,
    allowBackground: true,
    allowBorder: true,
    borderColor: "black",
    borderStyle: "solid",
    roundedCorner: 0,
    opacity: 1,
    fontSize: TEXT_DEFAULT_FONT_SIZE,
    textAlign: "center",
    textcolor: "black",
};

export class Decor extends FloorElement {
    constructor(data) {
        super(applyDefaults(data, defaults));
        this.hiddenBorderCssStyle = "";
        if (this.visibleBorders) {
            this.hiddenBordersSet = new Set();
            ["top", "bottom", "left", "right"].forEach((side) => {
                if (this.visibleBorders.includes(side)) {
                    return;
                }
                this.hiddenBordersSet.add(side);
                this.hiddenBorderCssStyle += `border-${side}-width: 0;`;
                if (side === "top") {
                    this.hiddenBorderCssStyle += `border-top-left-radius: 0;`;
                    this.hiddenBorderCssStyle += `border-top-right-radius: 0;`;
                } else if (side === "bottom") {
                    this.hiddenBorderCssStyle += `border-bottom-left-radius: 0;`;
                    this.hiddenBorderCssStyle += `border-bottom-right-radius: 0;`;
                } else if (side === "left") {
                    this.hiddenBorderCssStyle += `border-top-left-radius: 0;`;
                    this.hiddenBorderCssStyle += `border-bottom-left-radius: 0;`;
                } else if (side === "right") {
                    this.hiddenBorderCssStyle += `border-top-right-radius: 0;`;
                    this.hiddenBorderCssStyle += `border-bottom-right-radius: 0;`;
                }
            });
        }
    }

    getCssStyle() {
        let style = super.getCssStyle();

        if (this.allowBackground) {
            if (this.color) {
                style += `background-color: ${getColorRGBA(this.color, this.opacity)};`;
            }
        }
        if (this.allowBorder && this.borderWidth) {
            if (this.borderColor) {
                const borderWidthPx = Math.min(this.height / 2, this.borderWidth);
                style += `border: ${borderWidthPx}px ${this.borderStyle || "solid"} ${getColorRGBA(
                    this.borderColor
                )};`;
            }

            if ((this.shape === "rect" || this.shape === "square") && this.roundedCorner) {
                style += `border-radius: ${this.roundedCorner}px;`;
            }
        }

        if (this.allowText) {
            if (this.textAlign) {
                style += `text-align: ${this.textAlign};`;
            }
        }

        if (this.hasTransparentArea) {
            const {
                topBorderWidth,
                topBorderOffset,
                bottomBorderWidth,
                bottomBorderOffset,
                leftBorderWidth,
                leftBorderOffset,
                rightBorderWidth,
                rightBorderOffset,
                borderRadius,
            } = this.getTransparentAreaBorderInfo();

            style += `--border-radius:${borderRadius}px;`;
            style += `--border-top-offset:${topBorderOffset}px;--border-top-width:${topBorderWidth}px;`;
            style += `--border-bottom-offset:${bottomBorderOffset}px;--border-bottom-width:${bottomBorderWidth}px;`;
            style += `--border-left-offset:${leftBorderOffset}px;--border-left-width:${leftBorderWidth}px;`;
            style += `--border-right-offset:${rightBorderOffset}px;--border-right-width:${rightBorderWidth}px;`;
        }

        if (this.hiddenBorderCssStyle) {
            style += this.hiddenBorderCssStyle;
        }
        return style;
    }

    getTextCssStyle(props) {
        const fontSize = props?.fontSize || this.fontSize;
        const fontWeight = props?.fontWeight || this.fontWeight;
        const textcolor = props?.textcolor || this.textcolor;
        const textDecoration = props?.textDecoration || this.textDecoration;
        const fontStyle = props?.fontStyle || this.fontStyle;

        let style = ``;

        if (fontSize) {
            style += `font-size: ${fontSize}px;`;
        }
        if (fontWeight) {
            style += `font-weight: ${fontWeight};`;
        }
        if (textDecoration) {
            style += `text-decoration: ${textDecoration};`;
        }
        if (fontStyle) {
            style += `font-style: ${fontStyle};`;
        }

        if (textcolor) {
            style += `color: ${getColorRGBA(textcolor)};`;
        }
        return style;
    }

    get raw() {
        const result = {
            ...super.raw,
            allowText: this.allowText,
            allowBackground: this.allowBackground,
            allowBorder: this.allowBorder,
            roundedCorner: this.roundedCorner,
            group: this.group,
        };

        if (this.allowBackground) {
            result.color = this.color;
            result.opacity = this.opacity;
        }
        if (this.allowBorder) {
            result.borderColor = this.borderColor;
            result.borderWidth = this.borderWidth;
            result.borderStyle = this.borderStyle;
            result.visibleBorders = this.visibleBorders;
        }
        if (this.allowText) {
            result.text = this.text;
            result.fontSize = this.fontSize;
            result.fontWeight = this.fontWeight;
            result.textcolor = this.textcolor;
            result.textAlign = this.textAlign;
            result.textDecoration = this.textDecoration;
            result.fontStyle = this.fontStyle;
        }

        return removeNullishAndDefault(result, defaults);
    }

    get hasTransparentArea() {
        return this.allowBorder && this.borderWidth > 1 && !this.color && !this.text;
    }

    getTransparentAreaBorderInfo() {
        const MIN_BORDER_WIDTH = 20;
        // Calculate border width and offset for each side
        const calculateSideBorder = (hasBorder) => {
            if (!hasBorder) {
                return { width: 0, offset: 0 };
            }

            let borderWidth = this.borderWidth;
            let borderOffset = -this.borderWidth;

            if (this.borderWidth <= MIN_BORDER_WIDTH) {
                borderWidth = MIN_BORDER_WIDTH;
                borderOffset = -(borderWidth - this.borderWidth) / 2 - this.borderWidth;
            }

            return { width: borderWidth, offset: borderOffset };
        };

        let topBorder;
        let bottomBorder;
        let leftBorder;
        let rightBorder;
        let borderRadius = 0;

        if (this.hiddenBordersSet) {
            topBorder = calculateSideBorder(!this.hiddenBordersSet.has("top"));
            bottomBorder = calculateSideBorder(!this.hiddenBordersSet.has("bottom"));
            leftBorder = calculateSideBorder(!this.hiddenBordersSet.has("left"));
            rightBorder = calculateSideBorder(!this.hiddenBordersSet.has("right"));
        } else {
            topBorder = bottomBorder = leftBorder = rightBorder = calculateSideBorder(true);

            // If border radius all the border are displayed

            borderRadius = this.roundedCorner || 0;
            if (this.shape === "circle") {
                borderRadius = this.width / 2;
            } else if (this.shape === "oval") {
                borderRadius = Math.min(this.width, this.height) / 2;
            }

            if (borderRadius && this.borderWidth <= MIN_BORDER_WIDTH) {
                const originalWidth = this.width;
                const newWidth = this.width + 2 * -leftBorder.offset;
                const scaleFactor = newWidth / originalWidth;
                borderRadius = Math.max(0, borderRadius * scaleFactor);
            }
        }

        return {
            topBorderWidth: topBorder.width,
            topBorderOffset: topBorder.offset,
            bottomBorderWidth: bottomBorder.width,
            bottomBorderOffset: bottomBorder.offset,
            leftBorderWidth: leftBorder.width,
            leftBorderOffset: leftBorder.offset,
            rightBorderWidth: rightBorder.width,
            rightBorderOffset: rightBorder.offset,
            borderRadius,
        };
    }

    getTransparentAreaInfo() {
        const {
            topBorderWidth,
            topBorderOffset,
            bottomBorderWidth,
            bottomBorderOffset,
            leftBorderWidth,
            leftBorderOffset,
            rightBorderWidth,
            rightBorderOffset,
            borderRadius,
        } = this.getTransparentAreaBorderInfo();

        const parentBorderWidth = this.borderWidth || 0;

        const topPos = topBorderOffset !== 0 ? parentBorderWidth + topBorderOffset : 0;
        const leftPos = leftBorderOffset !== 0 ? parentBorderWidth + leftBorderOffset : 0;

        const left = this.left + leftPos;
        const top = this.top + topPos;

        const parentLeftBorder = leftBorderOffset !== 0 ? parentBorderWidth : 0;
        const parentRightBorder = rightBorderOffset !== 0 ? parentBorderWidth : 0;
        const widthReduction = parentLeftBorder + parentRightBorder;

        const parentTopBorder = topBorderOffset !== 0 ? parentBorderWidth : 0;
        const parentBottomBorder = bottomBorderOffset !== 0 ? parentBorderWidth : 0;
        const heightReduction = parentTopBorder + parentBottomBorder;

        const width = this.width - widthReduction - leftBorderOffset - rightBorderOffset;
        const height = this.height - heightReduction - topBorderOffset - bottomBorderOffset;

        let borderWidth = topBorderWidth;
        if (this.hiddenBordersSet) {
            borderWidth = Math.max(
                borderWidth,
                bottomBorderWidth,
                leftBorderWidth,
                rightBorderWidth
            );
        }

        return { borderWidth, borderRadius, left, top, width, height };
    }

    isResizeMaintainRatio() {
        return this.shape !== "rect" && this.shape !== "square";
    }
}
