import { markEventHandled } from "@web/core/utils/misc";
import { useRef } from "@web/owl2/utils";
import {
    Component,
    computed,
    onMounted,
    onPatched,
    onWillPatch,
    onWillStart,
    onWillUnmount,
    proxy,
    useApp,
    useListener,
    signal,
    types as t,
    useEffect,
    xml,
} from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { range } from "@web/core/utils/numbers";
import { fuzzyLookup } from "@web/core/utils/search";
import { Dialog } from "../dialog/dialog";
import { emojiLoader, useLoadEmoji } from "./emoji_loader";

/**
 * @typedef {import("./emoji_loader").Emoji} Emoji
 */

export function useEmojiPicker(...args) {
    return usePicker(EmojiPicker, ...args);
}

export function useEmojiPickerStoreScroll() {
    const storeScroll = {
        scrollValue: 0,
        set: (value) => {
            storeScroll.scrollValue = value;
        },
        get: () => storeScroll.scrollValue,
    };
    return storeScroll;
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

    shouldScrollElem = null;
    lastSearchTerm;
    keyboardNavigated = false;

    emojiMatrix = computed(() => {
        if (!emojiLoader.loaded || !this.gridRef()) {
            return [];
        }
        const emojiEls = Array.from(this.gridRef().querySelectorAll(".o-Emoji"));
        const emojiRects = emojiEls.map((el) => el.getBoundingClientRect());
        const matrix = [];
        for (const [index, pos] of emojiRects.entries()) {
            const emojiIndex = emojiEls[index].dataset.index;
            if (matrix.length === 0 || pos.top > emojiRects[index - 1].top) {
                matrix.push([]);
            }
            matrix.at(-1).push(parseInt(emojiIndex));
        }
        return matrix;
    });

    searchTerm = signal(this.props.initialSearchTerm ?? "", { type: t.string() });
    categoryId = signal(null, { type: t.or([t.number(), t.literal(null)]) });
    hoveredEmoji = signal(null, { type: t.or([t.object(), t.literal(null)]) }); // Emoji | null
    activeEmojiIndex = signal(0, { type: t.number() });

    gridRef = signal(null, { type: t.ref() });
    emojiNavbarRepr = signal(null, { type: t.or([t.array(), t.literal(null)]) });

    recentEmojis = computed(() => {
        const recent = Object.entries(this.frequentEmojiService.all)
            .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
            .map(([codepoints]) => emojiLoader.map.get(codepoints));
        if (this.searchTerm() && recent.length > 0) {
            return fuzzyLookup(this.searchTerm(), recent, (emoji) =>
                [emoji.name].concat(emoji.keywords, emoji.emoticons, emoji.shortcodes)
            );
        }
        return recent.slice(0, 42);
    });

    activeEmoji = computed(() => {
        const activeCodepoints = this.gridRef()?.querySelector(
            `.o-EmojiPicker-content .o-Emoji[data-index="${this.activeEmojiIndex()}"]`
        )?.dataset.codepoints;
        return emojiLoader.map.get(activeCodepoints);
    });

    setup() {
        this.navbarRef = useRef("navbar");
        this.ui = useService("ui");
        this.isMobileOS = isMobileOS();
        this.frequentEmojiService = useService("frequent_emoji");
        const loadEmoji = useLoadEmoji();
        useAutofocus();
        onWillStart(async () => {
            await loadEmoji();
            this.recentCategory = {
                name: "Frequently used",
                displayName: _t("Frequently used"),
                title: "🕓",
                sortId: 0,
            };
            this.categoryId.set(
                this.recentEmojis().length
                    ? this.recentCategory.sortId
                    : emojiLoader.categories[0].sortId
            );
        });
        onMounted(() => {
            if (!emojiLoader.loaded) {
                return;
            }
            this.navbarResizeObserver = new ResizeObserver(() => this.adaptNavbar());
            this.navbarResizeObserver.observe(this.navbarRef.el);
            this.adaptNavbar();
            this.highlightActiveCategory();
            if (this.props.storeScroll) {
                this.gridRef().scrollTop = this.props.storeScroll.get();
            }
            this.hoveredEmoji.set(this.activeEmoji());
        });
        onPatched(() => {
            if (!emojiLoader.loaded) {
                return;
            }
            if (this.shouldScrollElem) {
                this.shouldScrollElem = false;
                const getElement = () =>
                    this.gridRef().querySelector(
                        `.o-EmojiPicker-category[data-category="${this.categoryId()}"`
                    );
                const elem = getElement();
                if (elem) {
                    elem.scrollIntoView();
                } else {
                    this.shouldScrollElem = getElement;
                }
            }
        });
        useEffect(() => {
            if (!this.gridRef()) {
                return;
            }
            const active = this.gridRef().querySelector(".o-Emoji.o-active");
            if (active && this.keyboardNavigated && !isElementVisible(active, this.gridRef())) {
                active.scrollIntoView({ block: "center", behavior: "instant" });
                this.keyboardNavigated = false;
            }
            this.hoveredEmoji.set(this.activeEmoji());
        });
        useEffect(() => {
            if (!this.gridRef()) {
                return;
            }
            if (this.searchTerm()) {
                this.gridRef().scrollTop = 0;
                this.categoryId.set(null);
            } else {
                if (this.lastSearchTerm) {
                    this.gridRef().scrollTop = 0;
                }
                this.highlightActiveCategory();
            }
            this.lastSearchTerm = this.searchTerm();
        });
        onWillUnmount(() => {
            this.navbarResizeObserver?.disconnect();
            if (!this.gridRef()) {
                return;
            }
            this.props.storeScroll?.set(this.gridRef().scrollTop);
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
        const allCategories = this.getAllCategories(this.recentEmojis());
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
                    ...range(maxAvailableNavbarItemAmountAtOnce - panel.length).map(
                        (idx) => `empty_${idx}`
                    )
                );
            }
            repr.push(panel);
        }
        this.emojiNavbarRepr.set(repr);
    }

    get emojisLoaded() {
        return emojiLoader.loaded;
    }

    get placeholder() {
        return this.hoveredEmoji()?.shortcodes.join(" ") ?? _t("Search emoji");
    }

    /**
     * @param {MouseEvent} ev
     * @param {Emoji} emoji
     */
    onMouseenterEmoji(ev, emoji) {
        this.hoveredEmoji.set(emoji);
    }

    /**
     * @param {MouseEvent} ev
     * @param {Emoji} emoji
     */
    onMouseleaveEmoji(ev, emoji) {
        this.hoveredEmoji.set(this.activeEmoji());
    }

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        markEventHandled(ev, "emoji.selectEmoji");
    }

    onClickToNextCategories() {
        const repr = this.emojiNavbarRepr();
        const panelIndex = repr.findIndex((p) => p.includes(this.categoryId()));
        this.selectCategory(repr[panelIndex + 1][1]);
    }

    onClickToPreviousCategories() {
        const repr = this.emojiNavbarRepr();
        const panelIndex = repr.findIndex((p) => p.includes(this.categoryId()));
        this.selectCategory(repr[panelIndex - 1].at(-2));
    }

    /**
     * @param {string} key
     */
    handleNavigation(key) {
        const emojiMatrix = this.emojiMatrix();
        const currentIdx = this.activeEmojiIndex();
        let currentRow = -1;
        let currentCol = -1;
        const rowIdx = emojiMatrix.findIndex((row) => row.includes(currentIdx));
        if (rowIdx !== -1) {
            currentRow = rowIdx;
            currentCol = emojiMatrix[currentRow].indexOf(currentIdx);
        }
        let newIdx;
        switch (key) {
            case "ArrowDown": {
                const rowBelow = emojiMatrix[currentRow + 1];
                const rowBelowBelow = emojiMatrix[currentRow + 2];
                if (rowBelow?.length <= currentCol && rowBelowBelow?.length >= currentCol) {
                    newIdx = rowBelowBelow?.[currentCol];
                } else {
                    newIdx = rowBelow?.[Math.min(currentCol, rowBelow.length - 1)];
                }
                break;
            }
            case "ArrowUp": {
                const rowAbove = emojiMatrix[currentRow - 1];
                const rowAboveAbove = emojiMatrix[currentRow - 2];
                if (rowAbove?.length <= currentCol && rowAboveAbove?.length >= currentCol) {
                    newIdx = rowAboveAbove?.[currentCol];
                } else {
                    newIdx = rowAbove?.[Math.min(currentCol, rowAbove.length - 1)];
                }
                break;
            }
            case "ArrowRight": {
                const colRight = currentCol + 1;
                if (colRight === emojiMatrix[currentRow]?.length) {
                    const rowBelowRight = emojiMatrix[currentRow + 1];
                    newIdx = rowBelowRight?.[0];
                } else {
                    newIdx = emojiMatrix[currentRow]?.[colRight];
                }
                break;
            }
            case "ArrowLeft": {
                const colLeft = currentCol - 1;
                if (colLeft < 0) {
                    const rowAboveLeft = emojiMatrix[currentRow - 1];
                    newIdx = rowAboveLeft?.[rowAboveLeft.length - 1] ?? this.activeEmojiIndex();
                } else {
                    newIdx = emojiMatrix[currentRow][colLeft];
                }
                break;
            }
        }
        this.activeEmojiIndex.set(newIdx ?? this.activeEmojiIndex());
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
                this.handleNavigation(ev.key);
                this.keyboardNavigated = true;
                break;
            case "Enter":
                ev.preventDefault();
                this.gridRef()
                    ?.querySelector(
                        `.o-EmojiPicker-content .o-Emoji[data-index="${this.activeEmojiIndex()}"]`
                    )
                    ?.click();
                break;
            case "Escape":
                this.props.close?.();
                this.props.onClose?.();
                ev.stopPropagation();
        }
    }

    /**
     * @param {Emoji[]} recentEmojis passed as argument as to not recompute `this.recentEmojis`
     */
    getAllCategories(recentEmojis) {
        return recentEmojis.length
            ? [this.recentCategory].concat(emojiLoader.categories)
            : emojiLoader.categories;
    }

    /**
     * @param {Emoji[]} recentEmojis passed as argument as to not recompute `this.recentEmojis`
     */
    getCurrentNavbarPanel(recentEmojis) {
        const repr = this.emojiNavbarRepr();
        if (!repr) {
            return this.getAllCategories(recentEmojis).map((c) => c.sortId);
        }
        if (this.categoryId() === null || Number.isNaN(this.categoryId())) {
            return repr[0];
        }
        return repr.find((panel) => panel.includes(this.categoryId()));
    }

    /**
     * @param {Emoji[]} recentEmojis passed as argument as to not recompute `this.recentEmojis`
     */
    getEmojis(recentEmojis) {
        let emojisToDisplay = emojiLoader.emojis;
        if (recentEmojis.length > 0 && this.searchTerm()) {
            emojisToDisplay = emojisToDisplay.filter((emoji) => !recentEmojis.includes(emoji));
        }
        if (this.searchTerm().length > 0) {
            return fuzzyLookup(this.searchTerm(), emojisToDisplay, (emoji) =>
                [emoji.name].concat(emoji.keywords, emoji.emoticons, emoji.shortcodes)
            );
        }
        return emojisToDisplay;
    }

    /**
     * @param {string} categoryId
     */
    selectCategory(categoryId) {
        this.searchTerm.set("");
        this.categoryId.set(categoryId);
        this.shouldScrollElem = true;
    }

    /**
     * @param {PointerEvent} ev
     */
    selectEmoji(ev) {
        const codepoints = ev.currentTarget.dataset.codepoints;
        let resetOnSelect = !ev.shiftKey;
        const res = this.props.onSelect(codepoints, resetOnSelect);
        if (res === false) {
            resetOnSelect = false;
        }
        this.frequentEmojiService.incrementEmojiUsage(codepoints);
        if (resetOnSelect) {
            this.gridRef().scrollTop = 0;
            this.props.close?.();
            this.props.onClose?.();
        }
    }

    highlightActiveCategory() {
        if (!this.gridRef || !this.gridRef()) {
            return;
        }
        const coords = this.gridRef().getBoundingClientRect();
        const res = document.elementFromPoint(coords.x + 10, coords.y + 10);
        if (!res) {
            return;
        }
        this.categoryId.set(parseInt(res.dataset.category));
    }
}

/**
 * @param {import("@odoo/owl").ComponentConstructor} PickerComponent
 * @param {import("@web/core/utils/hooks").Ref} [ref]
 * @param {Object} props
 * @param {() => {}} [props.onSelect] function that is invoked when an item in picker has been selected.
 *   When explicit value `false` is returned, this will keep the picker open (= it won't auto-close it)
 * @param {() => {}} [props.onClose]
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 */
export function usePicker(PickerComponent, ref, props, options = {}) {
    const app = useApp();
    const targets = [];
    const state = proxy({ isOpen: false });
    const ui = useService("ui");
    const dialog = useService("dialog");
    const loadEmoji = useLoadEmoji();
    let remove;
    const newOptions = {
        ...options,
        onClose: () => {
            state.isOpen = false;
            props.onClose?.();
        },
    };
    const popover = usePopover(PickerComponent, {
        ...newOptions,
        animation: false,
        popoverClass: options.popoverClass ?? "" + " bg-100 border border-secondary",
    });
    props.storeScroll = useEmojiPickerStoreScroll();

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
            const { promise, resolve } = Promise.withResolvers();
            const pickerMobileProps = {
                PickerComponent,
                onSelect: (...args) => {
                    const func = openProps?.onSelect ?? props?.onSelect;
                    const res = func?.(...args);
                    resolve(true);
                    return res;
                },
            };
            if (ref?.el) {
                pickerMobileProps.close = () => remove();
                const root = app.createRoot(PickerMobile, {
                    props: pickerMobileProps,
                });
                remove = () => {
                    state.isOpen = false;
                    props.onClose?.();
                    root.destroy();
                };
                root.mount(ref.el);
            } else {
                remove = dialog.add(PickerMobileInDialog, pickerMobileProps, {
                    onClose: () => {
                        state.isOpen = false;
                        props.onClose?.();
                        return resolve(false);
                    },
                });
            }
            return promise;
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
    static components = { Dialog };
    static props = [...PICKER_PROPS, "onClose?"];
    static template = xml`
        <Dialog size="'lg'" header="false" footer="false" contentClass="'o-discuss-mobileContextMenu d-flex position-absolute bottom-0 rounded-0 h-50 bg-100'" bodyClass="'p-1'">
            <div class="h-100" t-custom-ref="root">
                <t t-component="this.props.PickerComponent" t-props="this.pickerProps"/>
            </div>
        </Dialog>
    `;

    setup() {
        super.setup();
        this.root = useRef("root");
        useListener(
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
