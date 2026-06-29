import { Component } from "@odoo/owl";
import { convertCSSColorToRgba, convertRgbToHsl, convertHslToRgb, convertRgbaToCSSColor } from "@web/core/utils/colors";

export class TagsList extends Component {
    static template = "web.TagsList";
    static defaultProps = {
        displayText: true,
    };
    static props = {
        displayText: { type: Boolean, optional: true },
        visibleItemsLimit: { type: Number, optional: true },
        tags: { type: Array, element: Object },
    };

    get visibleTagsCount() {
        return this.props.visibleItemsLimit - 1;
    }
    get visibleTags() {
        if (this.props.visibleItemsLimit && this.props.tags.length > this.props.visibleItemsLimit) {
            return this.props.tags.slice(0, this.visibleTagsCount);
        }
        return this.props.tags;
    }
    get otherTags() {
        if (this.props.visibleItemsLimit && this.props.tags.length > this.props.visibleItemsLimit) {
            return this.props.tags.slice(this.visibleTagsCount);
        }
        return [];
    }
    get tooltipInfo() {
        return JSON.stringify({
            tags: this.otherTags.map((tag) => ({
                text: tag.text,
                id: tag.id,
            })),
        });
    }

    getTagStyle(tag) {
        if (!tag.colorIndex || !tag.colorIndex.toString().startsWith("#")) {
            return "";
        }
        const color = tag.colorIndex;
        const rgba = convertCSSColorToRgba(color);
        if (!rgba) {
            return `background-color: ${color}; color: white;`;
        }
        const hsl = convertRgbToHsl(rgba.red, rgba.green, rgba.blue);
        let textColor;
        if (hsl.lightness < 45) {
            textColor = "white";
        } else {
            const darkRgb = convertHslToRgb(hsl.hue, hsl.saturation, Math.max(10, hsl.lightness - 50));
            textColor = convertRgbaToCSSColor(darkRgb.red, darkRgb.green, darkRgb.blue);
        }
        return `background-color: ${color}; color: ${textColor}; border: 1px solid rgba(0,0,0,0.1);`;
    }
}
