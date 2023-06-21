/* @odoo-module */

import { markEventHandled } from "@mail/utils/common/misc";

import {
    Component,
    onMounted,
    onPatched,
    onWillPatch,
    onWillStart,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { getBundle, loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { memoize } from "@web/core/utils/functions";
import { fuzzyLookup } from "@web/core/utils/search";

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
    const popover = usePopover(EmojiPicker, { ...options, popoverClass: "o-fast-popover" });
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
    return {
        add,
        get isOpen() {
            return popover.isOpen;
        },
    };
}

export const loader = {
    loadEmoji: memoize(() => getBundle("mail.assets_emoji").then(loadBundle)),
};

/**
 * @returns {import("@mail/core/common/emoji_data")}
 */
export async function loadEmoji() {
    try {
        await loader.loadEmoji();
        return odoo.runtimeImport("@mail/core/common/emoji_data");
    } catch {
        // Could be intentional (tour ended successfully while emoji still loading)
        return { emojis: [], categories: [] };
    }
}

export const EMOJI_PER_ROW = 9;

export class EmojiPicker extends Component {
    static props = ["onSelect", "close", "onClose?", "storeScroll?"];
    static defaultProps = { onClose: () => {} };
    static template = "mail.EmojiPicker";

    recent = [];
    categories = null;
    emojis = null;
    shouldScrollElem = null;

    setup() {
        this.inputRef = useRef("input");
        this.gridRef = useRef("emoji-grid");
        this.state = useState({
            activeEmojiIndex: 0,
            categoryId: null,
            searchStr: "",
        });
        onWillStart(async () => {
            const { categories, emojis } = await loadEmoji();
            this.categories = categories;
            this.emojis = emojis;
            this.emojiByCodepoints = Object.fromEntries(
                this.emojis.map((emoji) => [emoji.codepoints, emoji])
            );
            this.state.categoryId = this.categories[0]?.sortId;
            this.recent = JSON.parse(browser.localStorage.getItem("mail.emoji.frequent") || "{}");
            this.recentCategory = {
                name: "Frequently used",
                displayName: _t("Frequently used"),
                title: "🕓",
                sortId: 0,
            };
        });
        onMounted(() => {
            if (this.emojis.length === 0) {
                return;
            }
            this.inputRef.el.focus();
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
                        `.o-mail-EmojiPicker-category[data-category="${this.state.categoryId}"`
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
            () => {
                if (this.state.searchStr) {
                    this.state.categoryId = null;
                } else {
                    this.highlightActiveCategory();
                }
            },
            () => [this.state.searchStr]
        );
        onWillUnmount(() => {
            if (this.emojis.length === 0) {
                return;
            }
            if (this.props.storeScroll) {
                this.props.storeScroll.set(this.gridRef.el.scrollTop);
            }
        });
    }

    get itemsNumber() {
        return this.recentEmojis.length + this.getEmojis().length;
    }

    get recentEmojis() {
        return Object.entries(this.recent)
            .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
            .slice(0, 42)
            .map(([codepoints]) => this.emojiByCodepoints[codepoints]);
    }

    onClick(ev) {
        markEventHandled(ev, "emoji.selectEmoji");
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp": {
                const newIndex = this.state.activeEmojiIndex - EMOJI_PER_ROW;
                if (newIndex >= 0) {
                    this.state.activeEmojiIndex = newIndex;
                }
                break;
            }
            case "ArrowDown": {
                const newIndex = this.state.activeEmojiIndex + EMOJI_PER_ROW;
                if (newIndex < this.itemsNumber) {
                    this.state.activeEmojiIndex = newIndex;
                }
                break;
            }
            case "ArrowRight": {
                if (this.state.activeEmojiIndex + 1 === this.itemsNumber) {
                    break;
                }
                this.state.activeEmojiIndex++;
                ev.preventDefault();
                break;
            }
            case "ArrowLeft": {
                const newIndex = Math.max(this.state.activeEmojiIndex - 1, 0);
                if (newIndex !== this.state.activeEmojiIndex) {
                    this.state.activeEmojiIndex = newIndex;
                    ev.preventDefault();
                }
                break;
            }
            case "Enter":
                this.gridRef.el
                    .querySelector(
                        `.o-mail-EmojiPicker-content .o-mail-Emoji[data-index="${this.state.activeEmojiIndex}"]`
                    )
                    .click();
                break;
            case "Escape":
                this.props.close();
                this.props.onClose();
                ev.stopPropagation();
        }
    }

    getEmojis() {
        const search = this.state.searchStr;
        if (search.length > 1) {
            return fuzzyLookup(this.state.searchStr, this.emojis, (emoji) =>
                [emoji.name, ...emoji.keywords, ...emoji.emoticons, ...emoji.shortcodes].join(" ")
            );
        }
        return this.emojis;
    }

    selectCategory(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.state.searchStr = "";
        this.state.categoryId = id;
        this.shouldScrollElem = true;
    }

    selectEmoji(ev) {
        const codepoints = ev.currentTarget.dataset.codepoints;
        this.props.onSelect(codepoints);
        this.recent[codepoints] ??= 0;
        this.recent[codepoints]++;
        browser.localStorage.setItem("mail.emoji.frequent", JSON.stringify(this.recent));
        this.gridRef.el.scrollTop = 0;
        if (!ev.shiftKey) {
            this.props.close();
            this.props.onClose();
        }
    }

    highlightActiveCategory() {
        if (!this.gridRef || !this.gridRef.el) {
            return;
        }
        const coords = this.gridRef.el.getBoundingClientRect();
        const res = document.elementFromPoint(coords.x, coords.y + 1); // +1 for Firefox
        if (!res) {
            return;
        }
        this.state.categoryId = parseInt(res.dataset.category);
    }
}
