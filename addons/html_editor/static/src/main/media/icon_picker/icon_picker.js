import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    Component,
    computed,
    onWillStart,
    signal,
    types as t,
    usePlugin,
    useProps,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { uniqueId } from "@web/core/utils/functions";
import { useAutofocus } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { FrequentIconPlugin } from "./frequent_icon_plugin";

/**
 * Same limit as the frequently used emojis of the emoji picker.
 */
const MAX_FREQUENT_ICONS = 42;

/**
 * @typedef {Object} PickerIcon
 * @property {string} id unique among the variants of every icon
 * @property {string} name the icon name, i.e. its `data-icon`
 * @property {boolean} filled whether it is the filled variant of the icon
 * @property {string} label the readable name of the icon variant, e.g.
 *  "local bar (filled)", for assistive technologies and tooltips
 * @property {string[]} searchTerms the name and the tags the search matches
 */

/**
 * Fetches the catalog of the icons, once per language thanks to the cache, and
 * lists each variant of each icon: the outlined one, followed by the filled
 * one when it differs.
 *
 * @returns {Promise<PickerIcon[]>}
 */
export async function loadIcons() {
    const catalog = await rpc(
        "/html_editor/icons",
        { lang: user.context.lang },
        { cache: { type: "disk" } }
    );
    return catalog.flatMap(({ name, has_fill, tags }) => {
        // e.g. "local_bar" -> "local bar", "oi_view-kanban" -> "view kanban"
        const label = name.replace(/^oi_/, "").replaceAll(/[_-]/g, " ");
        const searchTerms = [name.replaceAll("_", " "), ...tags];
        const icons = [{ id: name, name, filled: false, label, searchTerms }];
        if (has_fill) {
            icons.push({
                id: `${name}:filled`,
                name,
                filled: true,
                label: _t("%(icon)s (filled)", { icon: label }),
                searchTerms,
            });
        }
        return icons;
    });
}

export class IconPicker extends Component {
    static template = "html_editor.IconPicker";

    props = useProps({
        onSelect: t.function(),
        id: t.string().optional(),
        label: t.string().optional(),
        close: t.function().optional(),
        currentIcon: t.object({ name: t.string(), filled: t.boolean() }).optional(),
        onUploadImage: t.function().optional(),
        document: t
            .customValidator(t.object(), (p) => p.nodeType === Node.DOCUMENT_NODE)
            .optional(),
    });

    searchTerm = signal("", { type: t.string() });
    activeIndex = signal(0, { type: t.number() });
    hoveredIcon = signal(null, { type: t.or([t.object(), t.literal(null)]) });

    gridRef = signal.ref();
    inputRef = signal.ref();
    uploadInputRef = signal.ref();

    listboxId = uniqueId("o-we-icon-picker-listbox-");

    /** @type {PickerIcon[]} */
    icons = [];
    /** @type {PickerIcon[]} */
    frequentSnapshot = [];
    loadFailed = false;

    frequentIcons = computed(() => {
        if (this.searchTerm()) {
            return fuzzyLookup(this.searchTerm(), this.frequentSnapshot, (i) => i.searchTerms);
        }
        return this.frequentSnapshot.slice(0, MAX_FREQUENT_ICONS);
    });

    otherIcons = computed(() => {
        if (!this.searchTerm()) {
            return this.icons;
        }
        const frequentIcons = new Set(this.frequentIcons());
        return fuzzyLookup(
            this.searchTerm(),
            this.icons.filter((icon) => !frequentIcons.has(icon)),
            (icon) => icon.searchTerms
        );
    });

    setup() {
        this.frequentIconPlugin = usePlugin(FrequentIconPlugin);
        useAutofocus({ ref: this.inputRef });
        // The picker is rendered outside of the edited document, so the icon
        // font selected there (e.g. sharp) has to be mirrored on the previews.
        const iconFontFamily = getCSSVariableValue(
            "icon-font-family",
            getHtmlStyle(this.props.document || document)
        )
            .replaceAll("'", "")
            .trim();
        this.iconsStyle = iconFontFamily ? `--icon-font-family: '${iconFontFamily}'` : undefined;
        onWillStart(async () => {
            try {
                this.icons = await loadIcons();
            } catch {
                this.loadFailed = true;
                return;
            }
            // Taken once, so that the icons do not move while being picked.
            const iconsById = new Map(this.icons.map((icon) => [icon.id, icon]));
            this.frequentSnapshot = this.frequentIconPlugin
                .mostFrequent()
                .map((id) => iconsById.get(id))
                .filter(Boolean);
        });
    }

    get placeholder() {
        return this.hoveredIcon()?.label ?? _t("Search an icon");
    }

    /**
     * @param {number} index
     * @returns {string} the id of the option of the icon at the given index
     */
    getOptionId(index) {
        return `${this.listboxId}-${index}`;
    }

    /**
     * @returns {string | undefined} the id of the active option, if displayed
     */
    get activeDescendant() {
        const index = this.activeIndex();
        return index < this.getDisplayedIcons().length ? this.getOptionId(index) : undefined;
    }

    /**
     * @param {PickerIcon} icon
     * @returns {boolean} whether it is the icon being replaced
     */
    isCurrentIcon(icon) {
        const currentIcon = this.props.currentIcon;
        return icon.name === currentIcon?.name && icon.filled === currentIcon.filled;
    }

    /**
     * @returns {PickerIcon[]} the displayed icons, in the order of their index
     */
    getDisplayedIcons() {
        return [...this.frequentIcons(), ...this.otherIcons()];
    }

    onInput() {
        this.activeIndex.set(0);
        if (this.gridRef()) {
            this.gridRef().scrollTop = 0;
        }
    }

    clearSearch() {
        this.searchTerm.set("");
        this.onInput();
        this.inputRef().focus();
    }

    openFileSelector() {
        this.uploadInputRef().click();
    }

    /**
     * @param {Event} ev
     */
    onFileSelected(ev) {
        const [file] = ev.target.files;
        if (file) {
            this.props.onUploadImage(file);
            this.props.close?.();
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowDown":
            case "ArrowUp":
            case "ArrowRight":
            case "ArrowLeft":
                ev.preventDefault();
                this.navigate(ev.key);
                break;
            case "Enter": {
                ev.preventDefault();
                const icon = this.getDisplayedIcons()[this.activeIndex()];
                if (icon) {
                    this.selectIcon(icon);
                }
                break;
            }
            case "Escape":
                ev.stopPropagation();
                this.props.close?.();
                break;
        }
    }

    /**
     * Moves the active icon in the grid. The rows are read from the rendered
     * icons, as their length depends on the width of the picker and on the
     * sections.
     *
     * @param {"ArrowDown"|"ArrowUp"|"ArrowRight"|"ArrowLeft"} key
     */
    navigate(key) {
        const iconEls = [...this.gridRef().querySelectorAll(".o-IconPicker-icon")];
        if (!iconEls.length) {
            return;
        }
        const current = this.activeIndex();
        let next = current;
        if (key === "ArrowRight") {
            next = Math.min(current + 1, iconEls.length - 1);
        } else if (key === "ArrowLeft") {
            next = Math.max(current - 1, 0);
        } else {
            const rows = [];
            let lastTop;
            for (const iconEl of iconEls) {
                const top = iconEl.getBoundingClientRect().top;
                if (top !== lastTop) {
                    rows.push([]);
                    lastTop = top;
                }
                rows.at(-1).push(parseInt(iconEl.dataset.index));
            }
            const rowIndex = rows.findIndex((row) => row.includes(current));
            const column = rows[rowIndex].indexOf(current);
            const targetRow = rows[rowIndex + (key === "ArrowDown" ? 1 : -1)];
            if (targetRow) {
                next = targetRow[Math.min(column, targetRow.length - 1)];
            }
        }
        this.activeIndex.set(next);
        this.hoveredIcon.set(this.getDisplayedIcons()[next]);
        this.gridRef()
            .querySelector(`.o-IconPicker-icon[data-index="${next}"]`)
            ?.scrollIntoView({ block: "nearest" });
    }

    /**
     * @param {PickerIcon} icon
     */
    selectIcon(icon) {
        this.frequentIconPlugin.incrementIconUsage(icon.id);
        this.props.onSelect({ name: icon.name, filled: icon.filled });
        this.props.close?.();
    }
}
