import { markEventHandled } from "@web/core/utils/misc";

import {
    App,
    Component,
    onMounted,
    onPatched,
    onWillPatch,
    onWillStart,
    onWillUnmount,
    reactive,
    useComponent,
    useEffect,
    useExternalListener,
    useRef,
    useState,
    xml,
} from "@odoo/owl";

import { loadBundle } from "@web/core/assets";
import { _t, appTranslateFn } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { fuzzyLookup } from "@web/core/utils/search";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Deferred } from "../utils/concurrency";
import { Dialog } from "../dialog/dialog";
import { getTemplate } from "@web/core/templates";

/**
 * @typedef Emoji
 * @property {string} category
 * @property {string} codepoints the emoji itself to be displayed
 * @property {string[]} emoticons string substitution (eg: ":p")
 * @property {string[]} keywords
 * @property {string} name
 * @property {string[]} shortcodes
 */

export function useEmojiPicker(...args) {
    return usePicker(EmojiPicker, ...args);
}

export const loader = reactive({
    loadEmoji: () => loadBundle("web.assets_emoji"),
    /** @type {{ emojiValueToShortcodes: Object<string, string[]>, emojiRegex: RegExp} }} */
    loaded: undefined,
});

/** @returns {Promise<{ categories: Object[], emojis: Emoji[] }>")} */
export async function loadEmoji() {
    const res = { categories: [], emojis: [] };
    try {
        await loader.loadEmoji();
        const { getCategories, getEmojis } = odoo.loader.modules.get(
            "@web/core/emoji_picker/emoji_data"
        );
        res.categories = getCategories();
        res.emojis = getEmojis();
        return res;
    } catch {
        // Could be intentional (tour ended successfully while emoji still loading)
        return res;
    } finally {
        if (!loader.loaded) {
            const emojiValueToShortcodes = {};
            for (const emoji of res.emojis) {
                emojiValueToShortcodes[emoji.codepoints] = emoji.shortcodes;
            }
            loader.loaded = {
                emojiValueToShortcodes,
                emojiRegex: new RegExp(
                    Object.keys(emojiValueToShortcodes).length
                        ? Object.keys(emojiValueToShortcodes)
                              .map((c) => c.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"))
                              .sort((a, b) => b.length - a.length) // Sort to get composed emojis first
                              .join("|")
                        : /(?!)/,
                    "gu"
                ),
            };
        }
    }
}

export const PICKER_PROPS = [
    "PickerComponent?",
    "close?",
    "onClose?",
    "onSelect",
    "state?",
    "storeScroll?",
    "mobile?",
];

export class EmojiPicker extends Component {
    static props = [...PICKER_PROPS, "class?", "initialSearchTerm?"];
    static template = "web.EmojiPicker";

    categories = null;
    /** @type {Emoji[]|null} */
    emojis = null;
    shouldScrollElem = null;
    lastSearchTerm;
    keyboardNavigated = false;

    setup() {
        this.gridRef = useRef("emoji-grid");
        this.navbarRef = useRef("navbar");
        this.ui = useService("ui");
        this.isMobileOS = isMobileOS();
        this.state = useState({
            activeEmojiIndex: 0,
            categoryId: null,
            searchTerm: this.props.initialSearchTerm ?? "",
            /** @type {Emoji|undefined} */
            hoveredEmoji: undefined,
        });
        this.frequentEmojiService = useService("web.frequent.emoji");
        useAutofocus();
        onWillStart(async () => {
            const { categories, emojis } = await loadEmoji();
            this.categories = categories;
            this.emojis = emojis;
            this.emojiByCodepoints = Object.fromEntries(
                this.emojis.map((emoji) => [emoji.codepoints, emoji])
            );
            this.recentCategory = {
                name: "Frequently used",
                displayName: _t("Frequently used"),
                title: "🕓",
                sortId: 0,
            };
            this.state.categoryId = this.recentEmojis.length
                ? this.recentCategory.sortId
                : this.categories[0].sortId;
        });
        onMounted(() => {
            if (this.emojis.length === 0) {
                return;
            }
            this.navbarResizeObserver = new ResizeObserver(() => this.adaptNavbar());
            this.navbarResizeObserver.observe(this.navbarRef.el);
            this.adaptNavbar();
            this.highlightActiveCategory();
            if (this.props.storeScroll) {
                this.gridRef.el.scrollTop = this.props.storeScroll.get();
            }
            this.state.hoveredEmoji = this.activeEmoji;
        });
        onPatched(() => {
            if (this.emojis.length === 0) {
                return;
            }
            if (this.shouldScrollElem) {
                this.shouldScrollElem = false;
                const getElement = () =>
                    this.gridRef.el.querySelector(
                        `.o-EmojiPicker-category[data-category="${this.state.categoryId}"`
                    );
                const elem = getElement();
                if (elem) {
                    elem.scrollIntoView();
                } else {
                    this.shouldScrollElem = getElement;
                }
            }
        });
        useEffect(
            () => this.updateEmojiPickerRepr(),
            () => [this.state.categoryId, this.state.searchTerm]
        );
        useEffect(
            (el) => {
                const gridEl = this.gridRef.el;
                const activeEl = gridEl?.querySelector(".o-Emoji.o-active");
                if (!gridEl) {
                    return;
                }
                if (activeEl && this.keyboardNavigated && !isElementVisible(activeEl, gridEl)) {
                    activeEl.scrollIntoView({ block: "center", behavior: "instant" });
                    this.keyboardNavigated = false;
                }
                this.state.hoveredEmoji = this.activeEmoji;
            },
            () => [this.state.activeEmojiIndex, this.gridRef.el]
        );
        useEffect(
            () => {
                if (!this.gridRef.el) {
                    return;
                }
                if (this.searchTerm) {
                    this.gridRef.el.scrollTop = 0;
                    this.state.categoryId = null;
                } else {
                    if (this.lastSearchTerm) {
                        this.gridRef.el.scrollTop = 0;
                    }
                    this.highlightActiveCategory();
                }
                this.lastSearchTerm = this.searchTerm;
            },
            () => [this.searchTerm]
        );
        onWillUnmount(() => {
            this.navbarResizeObserver?.disconnect();
            if (!this.gridRef.el) {
                return;
            }
            if (this.props.storeScroll) {
                this.props.storeScroll.set(this.gridRef.el.scrollTop);
            }
        });
    }

    adaptNavbar() {
        if (!this.navbarRef.el) {
            return;
        }
        const computedStyle = getComputedStyle(this.navbarRef.el);
        const availableWidth =
            this.navbarRef.el.getBoundingClientRect().width -
            parseInt(computedStyle.paddingLeft) -
            parseInt(computedStyle.marginLeft) -
            parseInt(computedStyle.paddingLeft) -
            parseInt(computedStyle.marginLeft);
        const itemWidth = this.navbarRef.el.querySelector(".o-Emoji").getBoundingClientRect().width;
        const gapWidth = parseInt(computedStyle.gap);
        const maxAvailableNavbarItemAmountAtOnce = Math.floor(
            availableWidth / (itemWidth + gapWidth)
        );
        const repr = [];
        let panel = [];
        const allCategories = this.getAllCategories();
        for (const category of allCategories) {
            if (
                panel.length === maxAvailableNavbarItemAmountAtOnce - 1 &&
                category !== allCategories.at(-1)
            ) {
                panel.push("next");
                repr.push(panel);
                panel = [];
                panel.push("previous");
            }
            panel.push(category.sortId);
        }
        if (panel.length > 0) {
            if (repr.length > 0) {
                panel.push(
                    ...[...Array(maxAvailableNavbarItemAmountAtOnce - panel.length)].map(
                        (_, idx) => "empty_" + idx
                    )
                );
            }
            repr.push(panel);
        }
        this.state.emojiNavbarRepr = repr;
    }

    get currentNavbarPanel() {
        if (!this.state.emojiNavbarRepr) {
            return this.getAllCategories().map((c) => c.sortId);
        }
        if (this.state.categoryId === null || Number.isNaN(this.state.categoryId)) {
            return this.state.emojiNavbarRepr[0];
        }
        return this.state.emojiNavbarRepr.find((panel) => panel.includes(this.state.categoryId));
    }

    get searchTerm() {
        return this.props.state ? this.props.state.searchTerm : this.state.searchTerm;
    }

    set searchTerm(value) {
        if (this.props.state) {
            this.props.state.searchTerm = value;
        } else {
            this.state.searchTerm = value;
        }
    }

    get itemsNumber() {
        return this.recentEmojis.length + this.getEmojis().length;
    }

    get recentEmojis() {
        const recent = Object.entries(this.frequentEmojiService.all)
            .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
            .map(([codepoints]) => this.emojiByCodepoints[codepoints]);
        if (this.searchTerm && recent.length > 0) {
            return fuzzyLookup(this.searchTerm, recent, (emoji) => [
                emoji.name,
                ...emoji.keywords,
                ...emoji.emoticons,
                ...emoji.shortcodes,
            ]);
        }
        return recent.slice(0, 42);
    }

    get placeholder() {
        return this.state.hoveredEmoji?.shortcodes.join(" ") ?? _t("Search emoji");
    }

    onMouseenterEmoji(ev, emoji) {
        this.state.hoveredEmoji = emoji;
    }

    onMouseleaveEmoji(ev, emoji) {
        this.state.hoveredEmoji = this.activeEmoji;
    }

    onClick(ev) {
        markEventHandled(ev, "emoji.selectEmoji");
    }

    onClickToNextCategories() {
        const panelIndex = this.state.emojiNavbarRepr.findIndex((p) =>
            p.includes(this.state.categoryId)
        );
        this.selectCategory(this.state.emojiNavbarRepr[panelIndex + 1][1]);
    }

    onClickToPreviousCategories() {
        const panelIndex = this.state.emojiNavbarRepr.findIndex((p) =>
            p.includes(this.state.categoryId)
        );
        this.selectCategory(this.state.emojiNavbarRepr[panelIndex - 1].at(-2));
    }

    /**
     * Builds the representation of the emoji picker (a 2D matrix of emojis)
     * from the current DOM state. This is necessary to handle keyboard
     * navigation of the emoji picker.
     */
    updateEmojiPickerRepr() {
        if (this.emojis.length === 0) {
            return;
        }
        const emojiEls = Array.from(this.gridRef.el.querySelectorAll(".o-Emoji"));
        const emojiRects = emojiEls.map((el) => el.getBoundingClientRect());
        this.emojiMatrix = [];
        for (const [index, pos] of emojiRects.entries()) {
            const emojiIndex = emojiEls[index].dataset.index;
            if (this.emojiMatrix.length === 0 || pos.top > emojiRects[index - 1].top) {
                this.emojiMatrix.push([]);
            }
            this.emojiMatrix.at(-1).push(parseInt(emojiIndex));
        }
    }

    handleNavigation(key) {
        const currentIdx = this.state.activeEmojiIndex;
        let currentRow = -1;
        let currentCol = -1;
        const rowIdx = this.emojiMatrix.findIndex((row) => row.includes(currentIdx));
        if (rowIdx !== -1) {
            currentRow = rowIdx;
            currentCol = this.emojiMatrix[currentRow].indexOf(currentIdx);
        }
        let newIdx;
        switch (key) {
            case "ArrowDown": {
                const rowBelow = this.emojiMatrix[currentRow + 1];
                const rowBelowBelow = this.emojiMatrix[currentRow + 2];
                if (rowBelow?.length <= currentCol && rowBelowBelow?.length >= currentCol) {
                    newIdx = rowBelowBelow?.[currentCol];
                } else {
                    newIdx = rowBelow?.[Math.min(currentCol, rowBelow.length - 1)];
                }
                break;
            }
            case "ArrowUp": {
                const rowAbove = this.emojiMatrix[currentRow - 1];
                const rowAboveAbove = this.emojiMatrix[currentRow - 2];
                if (rowAbove?.length <= currentCol && rowAboveAbove?.length >= currentCol) {
                    newIdx = rowAboveAbove?.[currentCol];
                } else {
                    newIdx = rowAbove?.[Math.min(currentCol, rowAbove.length - 1)];
                }
                break;
            }
            case "ArrowRight": {
                const colRight = currentCol + 1;
                if (colRight === this.emojiMatrix[currentRow]?.length) {
                    const rowBelowRight = this.emojiMatrix[currentRow + 1];
                    newIdx = rowBelowRight?.[0];
                } else {
                    newIdx = this.emojiMatrix[currentRow]?.[colRight];
                }
                break;
            }
            case "ArrowLeft": {
                const colLeft = currentCol - 1;
                if (colLeft < 0) {
                    const rowAboveLeft = this.emojiMatrix[currentRow - 1];
                    newIdx = rowAboveLeft?.[rowAboveLeft.length - 1] ?? this.state.activeEmojiIndex;
                } else {
                    newIdx = this.emojiMatrix[currentRow][colLeft];
                }
                break;
            }
        }
        this.state.activeEmojiIndex = newIdx ?? this.state.activeEmojiIndex;
    }

    get activeEmoji() {
        const activeCodepoints = this.gridRef.el.querySelector(
            `.o-EmojiPicker-content .o-Emoji[data-index="${this.state.activeEmojiIndex}"]`
        )?.dataset.codepoints;
        return activeCodepoints ? this.emojiByCodepoints[activeCodepoints] : undefined;
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowDown":
            case "ArrowUp":
            case "ArrowRight":
            case "ArrowLeft":
                this.handleNavigation(ev.key);
                this.keyboardNavigated = true;
                break;
            case "Enter":
                ev.preventDefault();
                this.gridRef.el
                    ?.querySelector(
                        `.o-EmojiPicker-content .o-Emoji[data-index="${this.state.activeEmojiIndex}"]`
                    )
                    ?.click();
                break;
            case "Escape":
                this.props.close?.();
                this.props.onClose?.();
                ev.stopPropagation();
        }
    }

    getAllCategories() {
        const res = [...this.categories];
        if (this.recentEmojis.length > 0) {
            res.unshift(this.recentCategory);
        }
        return res;
    }

    getEmojis() {
        let emojisToDisplay = [...this.emojis];
        const recentEmojis = this.recentEmojis;
        if (recentEmojis.length > 0 && this.searchTerm) {
            emojisToDisplay = emojisToDisplay.filter((emoji) => !recentEmojis.includes(emoji));
        }
        if (this.searchTerm.length > 0) {
            return fuzzyLookup(this.searchTerm, emojisToDisplay, (emoji) => [
                emoji.name,
                ...emoji.keywords,
                ...emoji.emoticons,
                ...emoji.shortcodes,
            ]);
        }
        return emojisToDisplay;
    }

    getEmojisFromSearch() {
        return [...this.recentEmojis, ...this.getEmojis()];
    }

    selectCategory(categoryId) {
        this.searchTerm = "";
        this.state.categoryId = categoryId;
        this.shouldScrollElem = true;
    }

    selectEmoji(ev) {
        const codepoints = ev.currentTarget.dataset.codepoints;
        let resetOnSelect = !ev.shiftKey;
        const res = this.props.onSelect(codepoints, resetOnSelect);
        if (res === false) {
            resetOnSelect = false;
        }
        this.frequentEmojiService.incrementEmojiUsage(codepoints);
        if (resetOnSelect) {
            this.gridRef.el.scrollTop = 0;
            this.props.close?.();
            this.props.onClose?.();
        }
    }

    highlightActiveCategory() {
        if (!this.gridRef || !this.gridRef.el) {
            return;
        }
        const coords = this.gridRef.el.getBoundingClientRect();
        const res = document.elementFromPoint(coords.x + 10, coords.y + 10);
        if (!res) {
            return;
        }
        this.state.categoryId = parseInt(res.dataset.category);
    }
}

/**
 * @param {() => {}} PickerComponent
 * @param {import("@web/core/utils/hooks").Ref} [ref]
 * @param {Object} props
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @param {function} [props.onSelect] function that is invoked when an item in picker has been selected.
 *   When explicit value `false` is returned, this will keep the picker open (= it won't auto-close it)
 * @param {function} [props.onClose]
 */
export function usePicker(PickerComponent, ref, props, options = {}) {
    const component = useComponent();
    const targets = [];
    const state = useState({ isOpen: false });
    const ui = useService("ui");
    const dialog = useService("dialog");
    let remove;
    const newOptions = {
        ...options,
        onClose: () => {
            state.isOpen = false;
            options.onClose?.();
        },
    };
    const popover = usePopover(PickerComponent, {
        ...newOptions,
        animation: false,
        popoverClass: options.popoverClass ?? "" + " bg-100 border border-secondary",
    });
    props.storeScroll = {
        scrollValue: 0,
        set: (value) => {
            props.storeScroll.scrollValue = value;
        },
        get: () => props.storeScroll.scrollValue,
    };

    /**
     * @param {import("@web/core/utils/hooks").Ref} ref
     */
    function add(ref, onSelect, { show = false } = {}) {
        const toggler = () => toggle(isMobileOS() ? undefined : ref, onSelect);
        targets.push([ref, toggler]);
        if (!ref.el) {
            return;
        }
        ref.el.addEventListener("click", toggler);
        ref.el.addEventListener("mouseenter", loadEmoji);
        if (show) {
            ref.el.click();
        }
    }

    function open(ref, openProps) {
        state.isOpen = true;
        if (ui.isSmall || isMobileOS()) {
            const def = new Deferred();
            const pickerMobileProps = {
                PickerComponent,
                onSelect: (...args) => {
                    const func = openProps?.onSelect ?? props?.onSelect;
                    const res = func?.(...args);
                    def.resolve(true);
                    return res;
                },
            };
            if (ref?.el) {
                pickerMobileProps.close = () => remove();
                const app = new App(PickerMobile, {
                    name: "Popout",
                    env: component.env,
                    props: pickerMobileProps,
                    getTemplate,
                    translatableAttributes: ["data-tooltip"],
                    translateFn: appTranslateFn,
                });
                app.mount(ref.el);
                remove = () => {
                    state.isOpen = false;
                    props.onClose?.();
                    app.destroy();
                };
            } else {
                remove = dialog.add(PickerMobileInDialog, pickerMobileProps, {
                    context: component,
                    onClose: () => {
                        state.isOpen = false;
                        return def.resolve(false);
                    },
                });
            }
            return def;
        }
        return popover.open(ref.el, { ...props, ...openProps });
    }

    function close() {
        remove?.();
        popover.close?.();
    }

    function toggle(ref, onSelect = props.onSelect) {
        if (state.isOpen) {
            close();
        } else {
            open(ref, { ...props, onSelect });
        }
    }

    if (ref) {
        add(ref);
    }
    onMounted(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.addEventListener("click", toggle);
            ref.el.addEventListener("mouseenter", loadEmoji);
        }
    });
    onWillPatch(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.removeEventListener("click", toggle);
            ref.el.removeEventListener("mouseenter", loadEmoji);
        }
    });
    onPatched(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.addEventListener("click", toggle);
            ref.el.addEventListener("mouseenter", loadEmoji);
        }
    });
    Object.assign(state, { open, close, toggle });
    return state;
}

class PickerMobile extends Component {
    static props = [...PICKER_PROPS, "onClose?"];
    static template = xml`
        <t t-component="props.PickerComponent" t-props="pickerProps"/>
    `;

    get pickerProps() {
        return {
            ...this.props,
            onSelect: (...args) => this.props.onSelect(...args),
            mobile: true,
        };
    }
}

class PickerMobileInDialog extends PickerMobile {
    static components = { Dialog };
    static props = [...PICKER_PROPS, "onClose?"];
    static template = xml`
        <Dialog size="'lg'" header="false" footer="false" contentClass="'o-discuss-mobileContextMenu d-flex position-absolute bottom-0 rounded-0 h-50 bg-100'" bodyClass="'p-1'">
            <div class="h-100" t-ref="root">
                <t t-component="props.PickerComponent" t-props="pickerProps"/>
            </div>
        </Dialog>
    `;

    setup() {
        super.setup();
        this.root = useRef("root");
        useExternalListener(
            window,
            "click",
            (ev) => {
                if (ev.target !== this.root.el && !this.root.el.contains(ev.target)) {
                    this.props.close?.();
                }
            },
            { capture: true }
        );
    }
}

function isElementVisible(el, holder) {
    const offset = 20;
    holder = holder || document.body;
    const { top, bottom, height } = el.getBoundingClientRect();
    let { top: holderTop, bottom: holderBottom } = holder.getBoundingClientRect();
    holderTop += offset * 2; // section are position sticky top so emoji can be "visible" under section name. Overestimate to assume invisible.
    holderBottom -= offset;
    return top - offset <= holderTop ? holderTop - top <= height : bottom - holderBottom <= height;
}
