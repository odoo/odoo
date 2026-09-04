import { SearchMedia } from "./search_media";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { getCSSVariableValue, getHtmlStyle, mapCSSRules } from "@html_editor/utils/formatting";
import { rpc } from "@web/core/network/rpc";

/**
 * Search the Material Symbols icons, matched against their name and tags in
 * the backend.
 *
 * @param {string} [needle] search term; every icon is returned when empty
 * @returns {Promise<Array.<{id: string, name: string, dataIcon: string, hasFilledVersion: boolean, source: string}>>}
 */
async function searchMsIcons(needle = "") {
    // The full list only changes with the icon font, so it is served from the
    // cache until the assets version changes. Searches always hit the server.
    const settings = needle ? {} : { cache: { type: "disk" } };
    const rows = await rpc("/html_editor/material_symbols_search", { needle }, settings);
    return rows.map(({ name, has_fill }) => ({
        id: name,
        name,
        dataIcon: name,
        hasFilledVersion: has_fill,
        source: "ms",
    }));
}

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
        this.state = proxy({
            needle: "",
            filteredIcons: [],
        });
        // Odoo UI icons are derived from CSS and searched client-side; Material
        // Symbols (name + tags) live in the backend and are fetched on demand,
        // so their large search-terms list never ships to the browser.
        this.oiIcons = IconSelector.getOiIcons();
        // The dialog is rendered outside of the edited document, so the icon
        // font selected there (e.g. sharp) has to be mirrored on the previews.
        const iconFontFamily = getCSSVariableValue(
            "icon-font-family",
            getHtmlStyle(this.props.document || document)
        )
            .replaceAll("'", "")
            .trim();
        this.iconsStyle = iconFontFamily ? `--icon-font-family: '${iconFontFamily}'` : undefined;
        onWillStart(async () => {
            this.allIcons = [...(await searchMsIcons()), ...this.oiIcons];
            this.state.filteredIcons = this.allIcons;
        });
    }

    isIconSelected(icon, filled) {
        return this.props.selectedMedia[this.props.id].some(
            (media) => media.id === icon.id && media.filled === filled
        );
    }

    async search(needle) {
        this.state.needle = needle;
        const lower = needle.toLowerCase();
        if (!lower) {
            this.state.filteredIcons = this.allIcons;
            return;
        }
        const oiIcons = this.oiIcons.filter((icon) => icon.searchTerms.includes(lower));
        this.state.filteredIcons = [...(await searchMsIcons(lower)), ...oiIcons];
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
    static createElements(selectedMedia, { document = window.document } = {}) {
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
     * Builds the list of Odoo UI custom icons from the CSS rules. These are
     * cheap to discover client-side and searched by name only.
     *
     * @returns {Array.<{id: string, name: string, dataIcon: string, searchTerms: string, source: string}>}
     */
    static getOiIcons() {
        const names = [
            ...new Set(
                mapCSSRules((rule) => {
                    const match = rule.selectorText.match(/\[data-icon=["'](oi_[^"']+)["']\]/);
                    if (match) {
                        return match[1];
                    }
                })
            ),
        ];
        return names.map((name) => ({
            id: name,
            name,
            dataIcon: name,
            searchTerms: name.slice("oi_".length).toLowerCase().replace(/-/g, " "),
            source: "oi",
        }));
    }
}
