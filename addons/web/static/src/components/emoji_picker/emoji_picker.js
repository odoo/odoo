// @ts-check
/** @odoo-module native */

import {
    App,
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
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
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { normalize } from "@web/core/l10n/utils";
import { _t } from "@web/core/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { markEventHandled } from "@web/core/utils/dom/events";
import { escapeRegExp } from "@web/core/utils/format/strings";
import { useAutofocus, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { useThrottleForAnimation } from "@web/core/utils/timing";
/**
 * @typedef Emoji
 * @property {string} category
 * @property {string} codepoints
 * @property {string[]} emoticons
 * @property {string[]} keywords
 * @property {string} name
 * @property {string[]} shortcodes
 */
import { makeAppConfig } from "@web/env";
import { Dialog } from "@web/ui/dialog/dialog";
import { usePopover } from "@web/ui/popover/popover_hook";

const log = makeLogger("web.components.emoji_picker");

export function useEmojiPicker(
    /** @type {any} */ ref,
    /** @type {any} */ props,
    /** @type {any} */ options,
) {
    return usePicker(EmojiPicker, ref, props, options);
}

/** @type {WeakMap<Emoji, string[]>} */
const searchStringsByEmoji = new WeakMap();

/**
 * @param {Emoji} emoji
 * @returns {string[]}
 */
function getEmojiSearchStrings(emoji) {
    let strings = searchStringsByEmoji.get(emoji);
    if (!strings) {
        strings = [
            emoji.name,
            ...emoji.keywords,
            ...emoji.emoticons,
            ...emoji.shortcodes,
        ].map(normalize);
        searchStringsByEmoji.set(emoji, strings);
    }
    return strings;
}

export const loader = reactive({
    loadEmoji: () => loadBundle("web.assets_emoji"),
    /** @type {{ emojiValueToShortcodes: {[key: string]: string[]}, emojiRegex: RegExp } | undefined} */
    loaded: undefined,
    // What the first successful load returned, final until
    // resetLoadedEmojiData(). Every later loadEmoji() resolves in a microtask
    // instead of going back through loadBundle and a dynamic import, both of
    // which settle on a later task even when memoised -- and
    // generateEmojisOnHtml sits on every message post, where that one task
    // was enough to reorder the post RPC behind the store's 1 ms fetch
    // debounce and to swap a livechat window in after the visitor had closed it.
    /** @type {{ categories: any[], emojis: any[] } | undefined} */
    data: undefined,
});

/** @returns {Promise<{ categories: any[], emojis: any[] }>} */
export async function loadEmoji() {
    if (loader.data) {
        return loader.data;
    }
    /** @type {{ categories: any[], emojis: any[] }} */
    const res = { categories: [], emojis: [] };
    try {
        await loader.loadEmoji();
        const { getCategories, getEmojis } =
            await import("@web/components/emoji_picker/emoji_data");
        res.categories = getCategories();
        res.emojis = getEmojis();
        loader.data = res;
        if (!loader.loaded) {
            /** @type {{[key: string]: string[]}} */
            const emojiValueToShortcodes = {};
            for (const emoji of res.emojis) {
                emojiValueToShortcodes[emoji.codepoints] = emoji.shortcodes;
                getEmojiSearchStrings(emoji);
            }
            loader.loaded = {
                emojiValueToShortcodes,
                emojiRegex: new RegExp(
                    Object.keys(emojiValueToShortcodes).length
                        ? Object.keys(emojiValueToShortcodes)
                              .map(escapeRegExp)
                              .sort((a, b) => b.length - a.length)
                              .join("|")
                        : /(?!)/,
                    "gu",
                ),
            };
        }
        return res;
    } catch {
        return res;
    }
}

export async function resetLoadedEmojiData() {
    loader.loaded = undefined;
    loader.data = undefined;
    try {
        const emojiData = await import("@web/components/emoji_picker/emoji_data");
        emojiData.resetEmojiData?.();
    } catch {}
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

    /** @type {{el: HTMLElement | null}} */
    gridRef;
    /** @type {{el: HTMLElement | null}} */
    navbarRef;
    /** @type {{el: HTMLElement | null}} */
    searchInputRef;
    /** @type {any} */
    ui;
    /** @type {boolean} */
    isMobileOS;
    /** @type {{activeEmojiIndex: number, categoryId: number | null, searchTerm: string, emojiNavbarRepr: any[][] | undefined}} */
    state;
    /** @type {any} */
    frequentEmojiService;
    /** @type {{name: string, displayName: string, sortId: number, title?: string}[]} */
    categories;
    /** @type {Emoji[]} */
    emojis;
    /** @type {{[key: string]: Emoji}} */
    emojiByCodepoints;
    /** @type {Map<string, {name: string, displayName: string, sortId: number, title?: string}>} */
    categoryByName;
    /** @type {string | undefined} */
    _emojisCacheKey;
    /** @type {Emoji[] | undefined} */
    _emojisCache;
    /** @type {Emoji[] | undefined} */
    _recentEmojisCache;
    /** @type {string | undefined} */
    _recentEmojisCacheKey;
    /** @type {Emoji | undefined} */
    hoveredEmoji;
    /** @type {{name: string, displayName: string, title: string, sortId: number}} */
    recentCategory;
    /** @type {ResizeObserver | undefined} */
    navbarResizeObserver;
    /** @type {ResizeObserver | undefined} */
    gridResizeObserver;
    /** @type {number | undefined} */
    gridWidth;
    /** @type {boolean | (() => HTMLElement | null)} */
    shouldScrollElem = false;
    /** @type {string | undefined} */
    lastSearchTerm;
    keyboardNavigated = false;
    /** @type {number[][] | null} */
    _emojiMatrix = null;
    /** @type {string | undefined} */
    navbarReprKey;

    setup() {
        useLifecycleLog(log);
        this.gridRef = useRef("emoji-grid");
        this.navbarRef = useRef("navbar");
        this.ui = useService("ui");
        this.isMobileOS = isMobileOS();
        this.state = useState({
            activeEmojiIndex: 0,
            categoryId: null,
            searchTerm: this.props.initialSearchTerm ?? "",
            /** @type {any[][] | undefined} */
            emojiNavbarRepr: undefined,
        });
        this.frequentEmojiService = useService("web.frequent.emoji");
        this.searchInputRef = useAutofocus();
        this.onGridScroll = useThrottleForAnimation(() =>
            this.highlightActiveCategory(),
        );
        onWillStart(async () => {
            const end = log.perf("loadEmoji");
            const { categories, emojis } = await loadEmoji();
            end({ emojis: emojis.length });
            this.categories = categories;
            this.emojis = emojis;
            this.emojiByCodepoints = Object.fromEntries(
                this.emojis.map((emoji) => [emoji.codepoints, emoji]),
            );
            this.categoryByName = new Map(
                this.categories.map((category) => [category.name, category]),
            );
            this.recentCategory = {
                name: "Frequently used",
                displayName: _t("Frequently used"),
                title: "🕓",
                sortId: 0,
            };
            this.state.categoryId = this.recentEmojis.length
                ? this.recentCategory.sortId
                : (this.categories[0]?.sortId ?? null);
        });
        /** @type {{ recent?: Emoji[], emojis?: Emoji[], all?: Emoji[] }} */
        this.emojisFromSearchMemo = {};
        this.setupLayoutObservers();
        this.setupCategoryScrolling();
        this.setupKeyboardFollow();
    }

    setupLayoutObservers() {
        onMounted(() => {
            if (!this.emojis.length) {
                return;
            }
            if (this.navbarRef.el) {
                this.navbarResizeObserver = new ResizeObserver(() =>
                    this.adaptNavbar(),
                );
                this.navbarResizeObserver.observe(this.navbarRef.el);
            }
            if (this.gridRef.el) {
                this.gridWidth = this.gridRef.el.clientWidth;
                this.gridResizeObserver = new ResizeObserver(() => {
                    const gridWidth = this.gridRef.el?.clientWidth;
                    if (gridWidth !== undefined && gridWidth !== this.gridWidth) {
                        this.gridWidth = gridWidth;
                        this._emojiMatrix = null;
                    }
                });
                this.gridResizeObserver.observe(this.gridRef.el);
            }
            this.adaptNavbar();
            if (this.props.storeScroll && this.gridRef.el) {
                this.gridRef.el.scrollTop = this.props.storeScroll.get();
            }
            this.setHoveredEmoji(this.activeEmoji);
        });
        onWillUnmount(() => {
            this.navbarResizeObserver?.disconnect();
            this.gridResizeObserver?.disconnect();
            if (this.props.storeScroll && this.gridRef.el) {
                this.props.storeScroll.set(this.gridRef.el.scrollTop);
            }
        });
        useEffect(
            () => {
                this._emojiMatrix = null;
            },
            () => [this.searchTerm, this.getEmojisFromSearch()],
        );
    }

    setupCategoryScrolling() {
        onPatched(() => {
            if (!this.emojis.length || !this.shouldScrollElem) {
                return;
            }
            this.shouldScrollElem = false;
            /** @returns {HTMLElement | null} */
            const getElement = () =>
                this.gridRef.el?.querySelector(
                    `.o-EmojiPicker-category[data-category="${this.state.categoryId}"]`,
                ) ?? null;
            const elem = getElement();
            if (elem) {
                elem.scrollIntoView();
            } else {
                this.shouldScrollElem = getElement;
            }
        });
        useEffect(
            () => {
                if (this.searchTerm !== this.lastSearchTerm) {
                    this.state.activeEmojiIndex = 0;
                }
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
            () => [this.searchTerm],
        );
    }

    setupKeyboardFollow() {
        useEffect(
            () => {
                const gridEl = this.gridRef.el;
                if (!gridEl) {
                    return;
                }
                const activeEl = gridEl.querySelector(".o-Emoji.o-active");
                if (
                    activeEl &&
                    this.keyboardNavigated &&
                    !isElementVisible(activeEl, gridEl)
                ) {
                    activeEl.scrollIntoView({
                        block: "center",
                        behavior: "instant",
                    });
                    this.keyboardNavigated = false;
                }
                this.setHoveredEmoji(this.activeEmoji);
            },
            () => [this.state.activeEmojiIndex, this.gridRef.el],
        );
    }

    adaptNavbar() {
        if (!this.navbarRef.el) {
            return;
        }
        const computedStyle = getComputedStyle(this.navbarRef.el);
        const availableWidth =
            this.navbarRef.el.getBoundingClientRect().width -
            Number.parseInt(computedStyle.paddingLeft, 10) -
            Number.parseInt(computedStyle.marginLeft, 10) -
            Number.parseInt(computedStyle.paddingRight, 10) -
            Number.parseInt(computedStyle.marginRight, 10);
        const firstItem = this.navbarRef.el.querySelector(".o-Emoji");
        if (!firstItem) {
            return;
        }
        const itemWidth = firstItem.getBoundingClientRect().width;
        const gapWidth = Number.parseInt(computedStyle.gap, 10);
        const maxAvailableNavbarItemAmountAtOnce = Math.floor(
            availableWidth / (itemWidth + gapWidth),
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
        if (panel.length) {
            if (repr.length) {
                panel.push(
                    ...[
                        ...Array(maxAvailableNavbarItemAmountAtOnce - panel.length),
                    ].map((_, idx) => `empty_${idx}`),
                );
            }
            repr.push(panel);
        }
        const key = repr.map((p) => p.join(",")).join(";");
        if (key === this.navbarReprKey) {
            return;
        }
        this.navbarReprKey = key;
        this.state.emojiNavbarRepr = repr;
    }

    get currentNavbarPanel() {
        if (!this.state.emojiNavbarRepr) {
            return this.getAllCategories().map((c) => c.sortId);
        }
        if (this.state.categoryId === null) {
            return this.state.emojiNavbarRepr[0];
        }
        return this.state.emojiNavbarRepr.find((panel) =>
            panel.includes(this.state.categoryId),
        );
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

    get recentEmojis() {
        return this.computeRecentEmojis();
    }

    computeRecentEmojis() {
        const cacheKey = `${this.searchTerm}\x00${this.frequentEmojiService.revision}`;
        if (this._recentEmojisCache && this._recentEmojisCacheKey === cacheKey) {
            return this._recentEmojisCache;
        }
        const recent = this.frequentEmojiService
            .getMostFrequent()
            .map((codepoints) => this.emojiByCodepoints[codepoints])
            .filter(Boolean);
        const result =
            this.searchTerm && recent.length
                ? fuzzyLookup(this.searchTerm, recent, getEmojiSearchStrings, {
                      preNormalized: true,
                  })
                : recent.slice(0, 42);
        this._recentEmojisCacheKey = cacheKey;
        this._recentEmojisCache = result;
        return result;
    }

    get placeholder() {
        return this.hoveredEmoji?.shortcodes.join(" ") ?? _t("Search emoji");
    }

    /** @param {Emoji|undefined} emoji */
    setHoveredEmoji(emoji) {
        if (this.hoveredEmoji === emoji) {
            return;
        }
        this.hoveredEmoji = emoji;
        const { el } = this.searchInputRef;
        if (el) {
            /** @type {HTMLInputElement} */ (el).placeholder = this.placeholder;
        }
    }

    /**
     * @param {Event} ev
     * @returns {HTMLElement | null}
     */
    emojiCellOf(ev) {
        const cell = /** @type {HTMLElement | null} */ (
            /** @type {HTMLElement} */ (ev.target).closest?.(".o-Emoji")
        );
        return cell && this.gridRef.el?.contains(cell) ? cell : null;
    }

    /** @param {MouseEvent} ev */
    onGridMouseover(ev) {
        const cell = this.emojiCellOf(ev);
        if (cell && !cell.contains(/** @type {Node} */ (ev.relatedTarget))) {
            this.setHoveredEmoji(this.emojiByCodepoints[cell.dataset.codepoints ?? ""]);
        }
    }

    /** @param {MouseEvent} ev */
    onGridMouseout(ev) {
        const cell = this.emojiCellOf(ev);
        if (cell && !cell.contains(/** @type {Node} */ (ev.relatedTarget))) {
            this.setHoveredEmoji(this.activeEmoji);
        }
    }

    /** @param {MouseEvent} ev */
    onGridClick(ev) {
        const cell = this.emojiCellOf(ev);
        if (cell) {
            this.selectEmoji(cell, ev.shiftKey);
        }
    }

    onClick(ev) {
        markEventHandled(ev, "emoji.selectEmoji");
    }

    onClickToNextCategories() {
        const panels = this.state.emojiNavbarRepr ?? [];
        const panelIndex = panels.findIndex((p) => p.includes(this.state.categoryId));
        const nextPanel = panelIndex === -1 ? undefined : panels[panelIndex + 1];
        if (!nextPanel) {
            return;
        }
        this.selectCategory(nextPanel[1]);
    }

    onClickToPreviousCategories() {
        const panels = this.state.emojiNavbarRepr ?? [];
        const panelIndex = panels.findIndex((p) => p.includes(this.state.categoryId));
        if (panelIndex <= 0) {
            return;
        }
        this.selectCategory(panels[panelIndex - 1].at(-2));
    }

    /** @returns {number[][]} */
    get emojiMatrix() {
        if (!this._emojiMatrix) {
            this._emojiMatrix = this.computeEmojiMatrix();
        }
        return this._emojiMatrix;
    }

    /** @returns {number[][]} */
    computeEmojiMatrix() {
        if (!this.emojis.length || !this.gridRef.el) {
            return [];
        }
        const end = log.perf("computeEmojiMatrix");
        const emojiEls = /** @type {HTMLElement[]} */ (
            Array.from(this.gridRef.el.querySelectorAll(".o-Emoji"))
        );
        const emojiTops = emojiEls.map((el) => el.offsetTop);
        /** @type {number[][]} */
        const matrix = [];
        for (const [index, top] of emojiTops.entries()) {
            const emojiIndex = emojiEls[index].dataset.index;
            if (emojiIndex === undefined) {
                continue;
            }
            if (!matrix.length || top > emojiTops[index - 1]) {
                matrix.push([]);
            }
            /** @type {number[]} */ (matrix.at(-1)).push(
                Number.parseInt(emojiIndex, 10),
            );
        }
        end({ rows: matrix.length });
        return matrix;
    }

    /**
     * @param {number} row
     * @param {number} col
     * @param {-1 | 1} direction
     * @returns {number | undefined}
     */
    rowNeighbour(row, col, direction) {
        const adjacent = this.emojiMatrix[row + direction];
        if (!adjacent) {
            return undefined;
        }
        if (adjacent.length > col) {
            return adjacent[col];
        }
        const skipped = this.emojiMatrix[row + 2 * direction];
        return skipped?.length > col ? skipped[col] : adjacent.at(-1);
    }

    handleNavigation(key) {
        const currentRow = this.emojiMatrix.findIndex((row) =>
            row.includes(this.state.activeEmojiIndex),
        );
        if (currentRow === -1) {
            this.state.activeEmojiIndex =
                this.emojiMatrix[0]?.[0] ?? this.state.activeEmojiIndex;
            return;
        }
        const row = this.emojiMatrix[currentRow];
        const currentCol = row.indexOf(this.state.activeEmojiIndex);
        let newIdx;
        switch (key) {
            case "ArrowDown":
                newIdx = this.rowNeighbour(currentRow, currentCol, 1);
                break;
            case "ArrowUp":
                newIdx = this.rowNeighbour(currentRow, currentCol, -1);
                break;
            case "ArrowRight":
                newIdx =
                    currentCol + 1 === row.length
                        ? this.emojiMatrix[currentRow + 1]?.[0]
                        : row[currentCol + 1];
                break;
            case "ArrowLeft":
                newIdx =
                    currentCol === 0
                        ? this.emojiMatrix[currentRow - 1]?.at(-1)
                        : row[currentCol - 1];
                break;
        }
        this.state.activeEmojiIndex = newIdx ?? this.state.activeEmojiIndex;
    }

    get activeEmoji() {
        return this.getEmojisFromSearch()[this.state.activeEmojiIndex];
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
                        `.o-EmojiPicker-content .o-Emoji[data-index="${this.state.activeEmojiIndex}"]`,
                    )
                    ?.click();
                break;
            case "Escape":
                this.props.close?.();
                ev.stopPropagation();
        }
    }

    getAllCategories() {
        const res = [...this.categories];
        if (this.recentEmojis.length) {
            res.unshift(this.recentCategory);
        }
        return res;
    }

    getEmojis() {
        return this.computeEmojis();
    }

    computeEmojis(recentEmojis = this.recentEmojis) {
        const cacheKey = this.searchTerm
            ? `${this.searchTerm}\x00${recentEmojis.map((e) => e.codepoints).join(",")}`
            : "";
        if (this._emojisCache && this._emojisCacheKey === cacheKey) {
            return this._emojisCache;
        }
        let emojisToDisplay = [...this.emojis];
        if (recentEmojis.length && this.searchTerm) {
            emojisToDisplay = emojisToDisplay.filter(
                (emoji) => !recentEmojis.includes(emoji),
            );
        }
        if (this.searchTerm.length) {
            emojisToDisplay = fuzzyLookup(
                this.searchTerm,
                emojisToDisplay,
                getEmojiSearchStrings,
                { preNormalized: true },
            );
        }
        this._emojisCacheKey = cacheKey;
        this._emojisCache = emojisToDisplay;
        return emojisToDisplay;
    }

    getEmojisFromSearch() {
        const recent = this.computeRecentEmojis();
        const emojis = this.computeEmojis(recent);
        const memo = this.emojisFromSearchMemo;
        if (memo.recent !== recent || memo.emojis !== emojis) {
            Object.assign(memo, { recent, emojis, all: [...recent, ...emojis] });
        }
        return /** @type {Emoji[]} */ (memo.all);
    }

    selectCategory(categoryId) {
        this.searchTerm = "";
        this.state.categoryId = categoryId;
        this.shouldScrollElem = true;
    }

    /** @param {HTMLElement} cell */
    selectEmoji(cell, shiftKey = false) {
        const codepoints = cell.dataset.codepoints;
        log.logic("selectEmoji", () => ({ codepoints, shiftKey }));
        let resetOnSelect = !shiftKey;
        const res = this.props.onSelect(codepoints, resetOnSelect);
        if (res === false) {
            resetOnSelect = false;
        }
        this.frequentEmojiService.incrementEmojiUsage(codepoints);
        if (resetOnSelect) {
            if (this.gridRef.el) {
                this.gridRef.el.scrollTop = 0;
            }
            this.props.close?.();
        }
    }

    highlightActiveCategory() {
        if (!this.gridRef || !this.gridRef.el) {
            return;
        }
        const coords = this.gridRef.el.getBoundingClientRect();
        const res = document.elementFromPoint(coords.x + 10, coords.y + 10);
        const categoryEl = /** @type {HTMLElement | null} */ (res)?.closest(
            "[data-category]",
        );
        if (!categoryEl) {
            return;
        }
        const categoryId = Number.parseInt(
            /** @type {HTMLElement} */ (categoryEl).dataset.category ?? "",
            10,
        );
        if (!Number.isNaN(categoryId)) {
            this.state.categoryId = categoryId;
        }
    }
}

class MobilePickerHost {
    /**
     * @param {{ PickerComponent: any, component: any, addDialog: Function,
     *   state: { isOpen: boolean }, props: Record<string, any> }} deps
     */
    constructor({ PickerComponent, component, addDialog, state, props }) {
        this.PickerComponent = PickerComponent;
        this.component = component;
        this.addDialog = addDialog;
        this.state = state;
        this.props = props;
        /** @type {(() => void) | null} */
        this.remove = null;
    }

    onGone() {
        this.remove = null;
        this.state.isOpen = false;
        this.props.onClose?.();
    }

    close() {
        this.remove?.();
    }

    /**
     * @param {{ el: HTMLElement } | undefined} ref
     * @param {Record<string, any>} [openProps]
     * @returns {Deferred}
     */
    open(ref, openProps) {
        const def = new Deferred();
        const pickerProps = {
            PickerComponent: this.PickerComponent,
            onSelect: (/** @type {any[]} */ ...args) => {
                const onSelect = openProps?.onSelect ?? this.props?.onSelect;
                const res = onSelect?.(...args);
                def.resolve(true);
                return res;
            },
        };
        if (ref?.el) {
            this.mountInto(ref.el, pickerProps);
        } else {
            this.openDialog(pickerProps, def);
        }
        return def;
    }

    /**
     * @param {HTMLElement} el
     * @param {Record<string, any>} pickerProps
     */
    mountInto(el, pickerProps) {
        pickerProps.close = () => this.close();
        const app = new App(
            PickerMobile,
            /** @type {any} */ (
                makeAppConfig(this.component.env, {
                    name: "Popout",
                    props: pickerProps,
                })
            ),
        );
        app.mount(el);
        this.remove = () => {
            this.onGone();
            app.destroy();
        };
    }

    /**
     * @param {Record<string, any>} pickerProps
     * @param {Deferred} def
     */
    openDialog(pickerProps, def) {
        const closeDialog = this.addDialog(
            PickerMobileInDialog,
            pickerProps,
            /** @type {any} */ ({
                context: this.component,
                onClose: () => {
                    this.onGone();
                    return def.resolve(false);
                },
            }),
        );
        this.remove = () => closeDialog();
    }
}

/**
 * @param {import("@web/env").OdooComponentConstructor} PickerComponent
 * @param {{ el: HTMLElement | null }} ref
 * @param {Record<string, any>} props
 * @param {Record<string, any>} [options]
 */
export function usePicker(PickerComponent, ref, props, options = {}) {
    const component = useComponent();
    const state = useState({ isOpen: false });
    const ui = useService("ui");
    const addDialog = useOwnedDialogs();
    const newOptions = {
        ...options,
        onClose: () => {
            state.isOpen = false;
            props.onClose?.();
        },
    };
    const popover = usePopover(/** @type {any} */ (PickerComponent), {
        ...newOptions,
        animation: false,
        class: (options.class ?? "") + " bg-100 border border-secondary",
    });
    const storeScroll = {
        scrollValue: 0,
        set: (value) => {
            storeScroll.scrollValue = value;
        },
        get: () => storeScroll.scrollValue,
    };

    const mobile = new MobilePickerHost({
        PickerComponent,
        component,
        addDialog,
        state,
        props,
    });

    function open(ref, openProps) {
        state.isOpen = true;
        if (ui.isSmall || isMobileOS()) {
            return mobile.open(ref, openProps);
        }
        return popover.open(ref.el, { ...props, storeScroll, ...openProps });
    }

    function close() {
        mobile.close();
        popover.close?.();
    }

    function toggle(ref, onSelect = props.onSelect) {
        if (state.isOpen) {
            close();
        } else {
            open(ref, { ...props, onSelect });
        }
    }

    const toggler = () => toggle(isMobileOS() ? undefined : ref);
    useEffect(
        (el) => {
            if (!el) {
                return;
            }
            el.addEventListener("click", toggler);
            el.addEventListener("mouseenter", loadEmoji);
            return () => {
                el.removeEventListener("click", toggler);
                el.removeEventListener("mouseenter", loadEmoji);
            };
        },
        () => [ref?.el],
    );
    onWillDestroy(() => mobile.close());
    return Object.assign(state, { open, close, toggle });
}

class PickerMobile extends Component {
    static props = [...PICKER_PROPS];
    static template = xml`
        <t t-component="this.props.PickerComponent" t-props="this.pickerProps"/>
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
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    root;

    static components = { Dialog };
    static props = [...PICKER_PROPS];
    static template = xml`
        <Dialog size="'lg'" header="false" footer="false" contentClass="'o-discuss-mobileContextMenu d-flex position-absolute bottom-0 rounded-0 h-50 bg-100'" bodyClass="'p-1'">
            <div class="h-100" t-ref="root">
                <t t-component="this.props.PickerComponent" t-props="this.pickerProps"/>
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
                const root = this.root.el;
                if (
                    root &&
                    ev.target !== root &&
                    !root.contains(/** @type {Node} */ (ev.target))
                ) {
                    this.props.close?.();
                }
            },
            { capture: true },
        );
    }
}

function isElementVisible(el, holder) {
    const offset = 20;
    holder = holder || document.body;
    const { top, bottom, height } = el.getBoundingClientRect();
    let { top: holderTop, bottom: holderBottom } = holder.getBoundingClientRect();
    holderTop += offset * 2;
    holderBottom -= offset;
    return top - offset <= holderTop
        ? holderTop - top <= height
        : bottom - holderBottom <= height;
}
