import { Component } from "@odoo/owl";
import { convertCSSColorToRgba, convertRgbToHsl } from "@web/core/utils/colors";

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

    getColorIndex(tag) {
        if (!tag.colorIndex) {
            return "0";
        }
        if (!tag.colorIndex.toString().startsWith("#")) {
            return tag.colorIndex;
        }

        const color = tag.colorIndex;
        const rgba = convertCSSColorToRgba(color);
        if (!rgba) {
            return "0";
        }

        const hsl = convertRgbToHsl(rgba.red, rgba.green, rgba.blue);
        // If color is desaturated (Grey), very dark (Black), or very light (White)
        // snap to Odoo's default neutral Grey (Index 0)
        if (hsl.saturation < 15 || hsl.lightness < 15 || hsl.lightness > 90) {
            return "0";
        }

        // Odoo's official base colors ($o-colors from SCSS)
        const palette = [
            { r: 162, g: 162, b: 162 }, // 0: Grey (#a2a2a2)
            { r: 238, g: 45, b: 45 },   // 1: Red (#ee2d2d)
            { r: 220, g: 133, b: 52 },  // 2: Orange (#dc8534)
            { r: 232, g: 187, b: 29 },  // 3: Yellow (#e8bb1d)
            { r: 87, g: 148, b: 221 },  // 4: Blue (#5794dd)
            { r: 159, g: 98, b: 143 },  // 5: Purple (#9f628f)
            { r: 219, g: 136, b: 101 }, // 6: Salmon (#db8865)
            { r: 65, g: 169, b: 162 },  // 7: Teal (#41a9a2)
            { r: 48, g: 75, b: 224 },   // 8: Dark Blue (#304be0)
            { r: 238, g: 47, b: 138 },  // 9: Pink (#ee2f8a)
            { r: 97, g: 195, b: 110 },  // 10: Green (#61c36e)
            { r: 152, g: 114, b: 230 }, // 11: Lavender (#9872e6)
        ];

        let minDistance = Infinity;
        let bestIndex = 0;

        for (let i = 0; i < palette.length; i++) {
            const p = palette[i];
            const rMean = (p.r + rgba.red) / 2;
            const dr = p.r - rgba.red;
            const dg = p.g - rgba.green;
            const db = p.b - rgba.blue;
            // Weighted Euclidean distance for better perceptual matching
            const distance = Math.sqrt(
                (2 + rMean / 256) * dr * dr +
                4 * dg * dg +
                (2 + (255 - rMean) / 256) * db * db
            );

            if (distance < minDistance) {
                minDistance = distance;
                bestIndex = i;
            }
        }
        return bestIndex.toString();
    }

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
}
