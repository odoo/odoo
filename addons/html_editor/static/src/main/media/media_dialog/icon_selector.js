import { SearchMedia } from "./search_media";
import { Component, proxy } from "@odoo/owl";
import MS_ICONS from "./data/ms_icons";
import OI_ICONS from "./data/oi_icons";

export class IconSelector extends Component {
    static mediaSpecificClasses = ["oi"];
    static mediaSpecificStyles = ["color", "background-color"];
    static mediaExtraClasses = [/^text-\S+$/, /^bg-\S+$/, /^fa-\S+$/];
    static tagNames = ["SPAN", "I"];
    static template = "html_editor.IconSelector";
    static components = {
        SearchMedia,
    };
    static props = ["*"];

    setup() {
        // Pre-populate filled state when editing an existing filled icon
        this.state = proxy({
            needle: "",
            filteredIcons: this.props.icons,
        });
    }

    isIconSelected(icon, filled) {
        return this.props.selectedMedia[this.props.id].some(
            (media) => media.id === icon.id && media.filled === filled
        );
    }

    search(needle) {
        this.state.needle = needle;
        const lower = this.state.needle.toLowerCase();
        if (!lower) {
            this.state.filteredIcons = this.props.icons;
            return;
        }
        this.state.filteredIcons = this.props.icons.filter((icon) =>
            icon.searchTerms.includes(lower)
        );
    }

    /**
     * Determines whether the icon being selected differs from the current media element.
     * For MS/OI icons this compares the data-icon attribute and filled state;
     * for FA icons it compares class names.
     *
     * @param {Object} icon
     * @returns {boolean}
     */
    iconHasChanged(icon, filled) {
        if (!this.props.media) {
            return false;
        }
        // Material Symbols and Odoo UI icons: compare data-icon and filled state
        const dataIconChanged = this.props.media.dataset.icon !== icon.dataIcon;
        const filledChanged = this.props.media.classList.contains("oi-filled") !== filled;
        return dataIconChanged || filledChanged;
    }

    async onClickIcon(icon, filled) {
        this.props.selectMedia({
            ...icon,
            filled,
            initialIconChanged: this.iconHasChanged(icon, filled),
        });
        await this.props.save();
    }

    /**
     * Utility methods, used by the MediaDialog component.
     */
    static createElements(selectedMedia) {
        return selectedMedia.map((icon) => {
            const iconEl = document.createElement("span");
            // Material Symbols and Odoo UI icons: icon is identified by data-icon attribute
            iconEl.classList.add("oi");
            if (icon.filled) {
                iconEl.classList.add("oi-filled");
            }
            iconEl.dataset.icon = icon.dataIcon;
            return iconEl;
        });
    }

    /**
     * Builds the full list of icons for the picker, merging:
     *   1. Material Symbols
     *   2. Odoo UI custom icons
     *
     * @returns {Array.<{id: string, label: string, source: string, base: string, icons: Array}>}
     */
    static initFonts() {
        return [
            ...Object.entries(MS_ICONS).map(([name, icon]) => ({
                id: `ms_${name}`,
                name,
                dataIcon: name,
                hasFilledVersion: icon.has_fill,
                searchTerms: `${name} ${icon.tags}`.toLowerCase(),
                source: "ms",
            })),
            ...OI_ICONS.map((name) => ({
                id: `oi_${name}`,
                name,
                dataIcon: `oi_${name}`,
                searchTerms: name.toLowerCase().replace(/-/g, " "),
                source: "oi",
            })),
        ];
    }
}
