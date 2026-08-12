import { SearchMedia } from "./search_media";
import { Component, onWillStart, proxy, useOnChange } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { KeepLast } from "@web/core/utils/concurrency";
import { mapCSSRules } from "@html_editor/utils/formatting";
import { rpc } from "@web/core/network/rpc";

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
        const preselected = this.props.selectedMedia[this.props.id];
        this.state = proxy({
            needle: "",
            variant: preselected[0]?.variant || "outline",
            filteredIcons: [],
            focusedIconIndex: 0,
        });
        this.keepLast = new KeepLast();
        this.oiIcons = IconSelector.getOiIcons();
        onWillStart(async () => {
            this.state.filteredIcons = await this.searchIcons(
                this.state.needle,
                this.state.variant
            );
        });
        useOnChange(
            () => [this.state.needle, this.state.variant],
            async (needle, variant) => {
                this.state.filteredIcons = await this.searchIcons(needle, variant);
                this.state.focusedIconIndex = 0;
            }
        );
    }

    isIconSelected(icon) {
        return this.props.selectedMedia[this.props.id].some(
            (media) => media.id === icon.id && media.variant === icon.variant
        );
    }

    onNeedleChange(needle) {
        this.state.needle = needle;
    }

    /**
     * Keyboard navigation for the icon grid. Arrow keys move focus between
     * icons. Enter and Space select the focused icon. any other single-character
     * key redirects to the search input.
     *
     * @param {KeyboardEvent} ev
     */
    onIconKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (!hotkey || !ev.target.classList.contains("font-icons-icon")) {
            return;
        }

        if (hotkey === "enter" || hotkey === "space") {
            ev.preventDefault();
            ev.target.click();
            return;
        }

        if (
            hotkey === "arrowright" ||
            hotkey === "arrowleft" ||
            hotkey === "arrowdown" ||
            hotkey === "arrowup"
        ) {
            this._navigateArrow(ev, hotkey);
            return;
        }

        if (hotkey.length === 1) {
            ev.target.closest(".o_select_media_dialog")?.querySelector(".o_we_search")?.focus();
        }
    }

    /**
     * Move focus to the next icon in the given arrow direction.
     *
     * @param {KeyboardEvent} ev
     * @param {string} hotkey
     */
    _navigateArrow(ev, hotkey) {
        const icons = [...ev.target.parentElement.querySelectorAll(".font-icons-icon")];
        const currentIndex = icons.indexOf(ev.target);
        if (currentIndex === -1) {
            return;
        }
        const nextIndex = this._computeArrowIndex(icons, currentIndex, hotkey);
        if (icons[nextIndex]) {
            ev.preventDefault();
            this.state.focusedIconIndex = nextIndex;
            // Update tabindex on the DOM directly so focus can move
            ev.target.tabIndex = -1;
            icons[nextIndex].tabIndex = 0;
            icons[nextIndex].focus();
        }
    }

    /**
     * Group icon elements into rows by their vertical offset.
     * @param {HTMLElement[]} icons
     * @returns {HTMLElement[][]}
     */
    _getIconRows(icons) {
        const rows = [];
        let row = [];
        let rowTop = null;
        for (const icon of icons) {
            const top = icon.offsetTop;
            if (top !== rowTop) {
                if (row.length) {
                    rows.push(row);
                }
                row = [icon];
                rowTop = top;
            } else {
                row.push(icon);
            }
        }
        if (row.length) {
            rows.push(row);
        }
        return rows;
    }

    /**
     * Compute the next icon index when navigating with arrow keys.
     * Returns undefined if the move is not possible (e.g. at the grid edge).
     *
     * @param {HTMLElement[]} icons
     * @param {number} currentIndex
     * @param {string} hotkey - one of "arrowright", "arrowleft", "arrowdown", "arrowup"
     * @returns {number|undefined}
     */
    _computeArrowIndex(icons, currentIndex, hotkey) {
        if (hotkey === "arrowright") {
            return currentIndex + 1;
        }
        if (hotkey === "arrowleft") {
            return currentIndex - 1;
        }
        if (hotkey === "arrowdown" || hotkey === "arrowup") {
            const rows = this._getIconRows(icons);
            // Find the current position in the row/col grid.
            let rowIndex = -1;
            let colIndex = -1;
            for (let r = 0; r < rows.length; r++) {
                const col = rows[r].indexOf(icons[currentIndex]);
                if (col !== -1) {
                    rowIndex = r;
                    colIndex = col;
                    break;
                }
            }
            const targetRowIndex = rowIndex + (hotkey === "arrowdown" ? 1 : -1);
            if (rows[targetRowIndex]) {
                const clampedCol = Math.min(colIndex, rows[targetRowIndex].length - 1);
                return icons.indexOf(rows[targetRowIndex][clampedCol]);
            }
        }
        return undefined;
    }

    /**
     * Determines whether the icon being selected differs from the current
     * media element. Compares data-icon and variant (filled state).
     *
     * @param {Object} icon
     * @returns {boolean}
     */
    iconHasChanged(icon) {
        if (!this.props.media) {
            return false;
        }
        const dataIconChanged = this.props.media.dataset.icon !== icon.dataIcon;
        const filledChanged =
            this.props.media.classList.contains("oi-filled") !== (icon.variant === "filled");
        return dataIconChanged || filledChanged;
    }

    async onClickIcon(icon) {
        this.props.selectMedia({
            ...icon,
            initialIconChanged: this.iconHasChanged(icon),
        });
        await this.props.save();
    }

    /**
     * Utility methods, used by the MediaDialog component.
     */
    static createElements(selectedMedia, { document = window.document } = {}) {
        return selectedMedia.map((icon) => {
            const iconEl = document.createElement("span");
            iconEl.classList.add("oi");
            if (icon.variant === "filled") {
                iconEl.classList.add("oi-filled");
            }
            iconEl.dataset.icon = icon.dataIcon;
            return iconEl;
        });
    }

    /**
     * Fetch the Material Symbols icons that match the given needle and variant.
     *
     * @param {string} needle
     * @param {"outline" | "filled" } variant
     * @returns {Promise<Array<{id: string, name: string, dataIcon: string, variant: string, source: string}>>}
     */
    async searchIcons(needle, variant) {
        const result = await this.keepLast.add(
            Promise.all([this.searchMsIcons(needle, variant), this.searchOiIcons(needle)])
        );

        // result is undefined when a newer search superseded this one
        if (!result) {
            return;
        }

        return result.flat();
    }

    /**
     * Fetch the Material Symbols icons that match the given needle and variant.
     *
     * @param {string} needle
     * @param {"outline" | "filled" } variant
     * @returns {Promise<Array<{id: string, name: string, dataIcon: string, variant: string, source: string}>>}
     */
    async searchMsIcons(needle, variant) {
        const result = await rpc(
            "/web/material_symbols/search",
            {
                needle: needle.toLowerCase(),
                variant: variant,
            },
            { cache: true }
        );
        return result.map(({ name, variant }) => ({
            id: `ms_${name}_${variant}`,
            name,
            dataIcon: name,
            variant,
            source: "ms",
        }));
    }

    /**
     * Filter the Odoo UI icons that match the given needle.
     *
     * @param {string} needle
     * @returns {Array.<{id: string, name: string, dataIcon: string, searchTerms: string, variant: string, source: string}>}
     */
    searchOiIcons(needle) {
        if (!needle) {
            return this.oiIcons;
        }
        return this.oiIcons.filter((icon) => icon.searchTerms.includes(needle.toLowerCase()));
    }

    /**
     * Builds the list of Odoo UI custom icons from the CSS rules. These are
     * cheap to discover client-side and searched by name only.
     *
     * @returns {Array.<{id: string, name: string, dataIcon: string, searchTerms: string, variant: string, source: string}>}
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
            variant: "outline",
            searchTerms: name.slice("oi_".length).toLowerCase().replace(/-/g, " "),
            source: "oi",
        }));
    }
}
