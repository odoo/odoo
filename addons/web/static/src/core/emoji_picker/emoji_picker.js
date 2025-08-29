import { markEventHandled } from "@web/core/utils/misc";

import {
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillPatch,
    onWillStart,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { fuzzyLookup } from "@web/core/utils/search";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isMobileOS } from "@web/core/browser/feature_detection";

/**
 *
 * @param {import("@web/core/utils/hooks").Ref} [ref]
 * @param {Object} props
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @param {function} [props.onSelect]
 * @param {function} [props.onClose]
 */
export function useEmojiPicker(ref, props, options = {}) {
    const targets = [];
    const state = useState({ isOpen: false });
    const newOptions = {
        ...options,
        onClose: () => {
            state.isOpen = false;
            options.onClose?.();
        },
    };
    const popover = usePopover(EmojiPicker, {
        ...newOptions,
        animation: false,
        popoverClass: "border-secondary",
    });
    props.storeScroll = {
        scrollValue: 0,
        set: (value) => {
            props.storeScroll.scrollValue = value;
        },
        get: () => {
            return props.storeScroll.scrollValue;
        },
    };

    /**
     * @param {import("@web/core/utils/hooks").Ref} ref
     */
    function add(ref, onSelect, { show = false } = {}) {
        const toggler = () => toggle(ref, onSelect);
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

    function toggle(ref, onSelect = props.onSelect) {
        if (popover.isOpen) {
            popover.close();
        } else {
            state.isOpen = true;
            popover.open(ref.el, { ...props, onSelect });
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
    Object.assign(state, { add });
    return state;
}

const loadingListeners = [];

export const loader = {
    loadEmoji: () => loadBundle("web.assets_emoji"),
    /** @type {{ emojiValueToShortcode: Object<string, string> }} */
    loaded: undefined,
    onEmojiLoaded(cb) {
        loadingListeners.push(cb);
    },
};

/**
 * @returns {import("@web/core/emoji_picker/emoji_data")}
 */
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
            loader.loaded = { emojiValueToShortcode: {} };
            for (const emoji of res.emojis) {
                const value = emoji.codepoints;
                const shortcode = emoji.shortcodes[0];
                loader.loaded.emojiValueToShortcode[value] = shortcode;
                for (const listener of loadingListeners) {
                    listener();
                }
                loadingListeners.length = 0;
            }
        }
    }
}

export const EMOJI_PICKER_PROPS = ["close?", "onClose?", "onSelect", "state?", "storeScroll?"];

export class EmojiPicker extends Component {
    static props = EMOJI_PICKER_PROPS;
    static template = "web.EmojiPicker";

    categories = null;
    emojis = null;
    shouldScrollElem = null;
    lastSearchTerm;
    keyboardNavigated = false;

    setup() {
        this.gridRef = useRef("emoji-grid");
        this.navbarRef = useRef("navbar");
        this.ui = useState(useService("ui"));
        this.isMobileOS = isMobileOS();
        this.state = useState({
            activeEmojiIndex: 0,
            categoryId: null,
            recent: JSON.parse(browser.localStorage.getItem("web.emoji.frequent") || "{}"),
            searchTerm: "",
        });
        const onStorage = (ev) => {
            if (ev.key === "web.emoji.frequent") {
                this.state.recent = ev.newValue ? JSON.parse(ev.newValue) : {};
            } else if (ev.key === null) {
                this.state.recent = {};
            }
        };
        browser.addEventListener("storage", onStorage);
        onWillDestroy(() => {
            browser.removeEventListener("storage", onStorage);
        });
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
                const gridEl = this.gridRef?.el;
                const activeEl = gridEl?.querySelector(".o-Emoji.o-active");
                if (
                    gridEl &&
                    activeEl &&
                    this.keyboardNavigated &&
                    !isElementVisible(activeEl, gridEl)
                ) {
                    activeEl.scrollIntoView({ block: "center", behavior: "instant" });
                    this.keyboardNavigated = false;
                }
            },
            () => [this.state.activeEmojiIndex, this.gridRef?.el]
        );
        useEffect(
            () => {
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
        const recent = Object.entries(this.state.recent)
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
                if (colRight === this.emojiMatrix[currentRow].length) {
                    const rowBelowRight = this.emojiMatrix[currentRow + 1];
                    newIdx = rowBelowRight?.[0];
                } else {
                    newIdx = this.emojiMatrix[currentRow][colRight];
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
                    .querySelector(
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
        const resetOnSelect = !ev.shiftKey && !this.ui.isSmall;
        this.props.onSelect(codepoints, resetOnSelect);
        this.state.recent[codepoints] ??= 0;
        this.state.recent[codepoints]++;
        browser.localStorage.setItem("web.emoji.frequent", JSON.stringify(this.state.recent));
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

function isElementVisible(el, holder) {
    const offset = 20;
    holder = holder || document.body;
    const { top, bottom, height } = el.getBoundingClientRect();
    let { top: holderTop, bottom: holderBottom } = holder.getBoundingClientRect();
    holderTop += offset * 2; // section are position sticky top so emoji can be "visible" under section name. Overestimate to assume invisible.
    holderBottom -= offset;
    return top - offset <= holderTop ? holderTop - top <= height : bottom - holderBottom <= height;
}
