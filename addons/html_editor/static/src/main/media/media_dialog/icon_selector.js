import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { Component, onWillStart, proxy, t, useProps } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { SearchMedia } from "./search_media";

/**
 * Search icons, matched against their name and tags in the backend.
 *
 * @param {string} [needle] search term; every icon is returned when empty
 * @returns {Promise<Array.<{id: string, name: string, dataIcon: string, hasFilledVersion: boolean, source: string}>>}
 */
async function searchIcons(needle = "") {
    // The full list only changes with the icon font, so it is served from the
    // cache until the assets version changes. Searches always hit the server.
    const settings = needle ? {} : { cache: { type: "disk" } };
    const rows = await rpc("/html_editor/icons_search", { needle }, settings);
    return rows.map(({ name, has_fill }) => ({
        id: name,
        name,
        dataIcon: name,
        hasFilledVersion: has_fill,
        source: name.startsWith("oi_") ? "oi" : "ms",
    }));
}

/**
 * Formerly the Icons tab of the media dialog, which the icon picker replaced.
 *
 * TODO: remove it, with the `/html_editor/icons_search` route it relies on
 * (but not the `search_icons` helper, used elsewhere), once Studio no longer
 * uses it (task-5469997).
 */
export class IconSelector extends Component {
    static template = "html_editor.IconSelector";
    static components = {
        SearchMedia,
    };

    props = useProps({
        document: t
            .customValidator(t.object(), (p) => p.nodeType === Node.DOCUMENT_NODE)
            .optional(),
        id: t.string(),
        media: t.object().optional(),
        save: t.function(),
        selectedMedia: t.object(),
        selectMedia: t.function(),
    });

    setup() {
        this.state = proxy({
            needle: "",
            filteredIcons: [],
        });
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
            this.allIcons = await searchIcons();
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
        this.state.filteredIcons = await searchIcons(lower);
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
}
