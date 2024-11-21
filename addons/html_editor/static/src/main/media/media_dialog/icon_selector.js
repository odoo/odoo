import { SearchMedia } from "./search_media";
import { fonts } from "@html_editor/utils/fonts";

import { Component, useState } from "@odoo/owl";

export class IconSelector extends Component {
    static mediaSpecificClasses = ["fa"];
    static mediaSpecificStyles = ["color", "background-color"];
    static mediaExtraClasses = [
        "rounded-circle",
        "rounded",
        "img-thumbnail",
        "shadow",
        /^text-\S+$/,
        /^bg-\S+$/,
        /^fa-\S+$/,
    ];
    static tagNames = ["SPAN", "I"];
    static template = "html_editor.IconSelector";
    static components = {
        SearchMedia,
    };
    static props = ["*"];

    setup() {
        this.state = useState({
            fonts: this.props.fonts,
            needle: "",
        });
    }

    get selectedMediaIds() {
        return this.props.selectedMedia[this.props.id].map(({ id }) => id);
    }

    search(needle) {
        this.state.needle = needle;
        if (!this.state.needle) {
            this.state.fonts = this.props.fonts;
        } else {
            this.state.fonts = this.props.fonts.map((font) => {
                const icons = font.icons.filter(
                    (icon) => icon.alias.indexOf(this.state.needle) >= 0
                );
                return { ...font, icons };
            });
        }
    }

    async onClickIcon(font, icon) {
        this.props.selectMedia({
            ...icon,
            fontBase: font.base,
            // To check if the icon has changed, we only need to compare
            // an alias of the icon with the class from the old media (some
            // icons can have multiple classes e.g. "fa-gears" ~ "fa-cogs")
            initialIconChanged:
                this.props.media &&
                !icon.names.some((name) => this.props.media.classList.contains(name)),
        });
        await this.props.save();
    }

    /**
     * Utility methods, used by the MediaDialog component.
     */
    static createElements(selectedMedia) {
        return selectedMedia.map((icon) => {
            const iconEl = document.createElement("span");
            iconEl.classList.add(icon.fontBase, icon.names[0]);
            return iconEl;
        });
    }
    static initFonts() {
        fonts.computeFonts();
        const allFonts = fonts.fontIcons.map(({ cssData, base }) => {
            const uniqueIcons = Array.from(
                new Map(
                    cssData.map((icon) => {
                        const alias = icon.names.join(",");
                        const id = `${base}_${alias}`;
                        return [id, { ...icon, alias, id }];
                    })
                ).values()
            );
            return { base, icons: uniqueIcons };
        });
        return allFonts;
    }
}
