/* @odoo-module */

import { markEventHandled } from "@mail/new/utils/misc";

import {
    Component,
    onMounted,
    onWillStart,
    useEffect,
    useRef,
    useState,
    onPatched,
    onWillPatch,
    onWillUnmount,
} from "@odoo/owl";
import { getBundle, loadBundle } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { memoize } from "@web/core/utils/functions";
import { escapeRegExp } from "@web/core/utils/strings";

/**
 *
 * @param {Object|string} [target] if string then it's a ref name, otherwise it's a ref
 * @param {Object} props
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @param {function} [props.onSelect]
 * @param {function} [props.onClose]
 */
export function useEmojiPicker(target, props, options = {}) {
    const targets = [];
    const popover = usePopover();
    let closePopover = false;
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
     * @param {string|Object} target a refName or an Object whose el is an HTMl element target
     * @param {HTMLElement|Function} [target.el]
     */
    function add(target, onSelect, { show = false } = {}) {
        const ref = typeof target === "string" ? useRef(target) : target;
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
        if (closePopover) {
            closePopover();
            closePopover = false;
        } else {
            closePopover = popover.add(
                ref.el,
                EmojiPicker,
                { ...props, onSelect },
                {
                    ...options,
                    onClose: () => (closePopover = false),
                    popoverClass: "o-fast-popover",
                }
            );
        }
    }

    if (target) {
        add(target);
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
            return Boolean(closePopover);
        },
    };
}

const _loadEmoji = memoize(() => getBundle("mail.assets_emoji").then(loadBundle));

/**
 * @returns {import("@mail/new/emoji_picker/emoji_data")}
 */
export async function loadEmoji() {
    await _loadEmoji();
    return odoo.runtimeImport("@mail/new/emoji_picker/emoji_data");
}

export class EmojiPicker extends Component {
    static props = ["onSelect", "close", "onClose?", "storeScroll?"];
    static defaultProps = { onClose: () => {} };
    static template = "mail.emoji_picker";

    setup() {
        this.categories = null;
        this.emojis = null;
        this.inputRef = useRef("input");
        this.gridRef = useRef("emoji-grid");
        this.shouldScrollElem = null;
        this.state = useState({
            categoryId: null,
            searchStr: "",
        });
        onWillStart(async () => {
            const { categories, emojis } = await loadEmoji();
            this.categories = categories;
            this.emojis = emojis;
            this.state.categoryId = this.categories[0].sortId;
        });
        onMounted(() => {
            this.inputRef.el.focus();
            this.highlightActiveCategory();
            if (this.props.storeScroll) {
                this.gridRef.el.scrollTop = this.props.storeScroll.get();
            }
        });
        onPatched(() => {
            if (this.shouldScrollElem) {
                this.shouldScrollElem = false;
                const getElement = () =>
                    this.gridRef.el.querySelector(
                        `.o-emoji-category[data-category="${this.state.categoryId}"`
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
            if (this.props.storeScroll) {
                this.props.storeScroll.set(this.gridRef.el.scrollTop);
            }
        });
    }

    onClick(ev) {
        markEventHandled(ev, "emoji.selectEmoji");
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.close();
            this.props.onClose();
            ev.stopPropagation();
        }
    }

    getEmojis() {
        const search = this.state.searchStr;
        if (search.length > 1) {
            const regexp = new RegExp(
                search
                    .split("")
                    .map((x) => escapeRegExp(x))
                    .join(".*")
            );
            return this.emojis.filter((emoji) =>
                [emoji.name, ...emoji.keywords, ...emoji.emoticons, ...emoji.shortcodes].some((x) =>
                    x.match(regexp)
                )
            );
        }
        return this.emojis;
    }

    selectCategory(ev) {
        const id = Number(ev.target.dataset.id);
        if (id) {
            this.state.searchStr = "";
            this.state.categoryId = id;
            this.shouldScrollElem = true;
        }
    }

    selectEmoji(ev) {
        const codepoints = ev.target.dataset.codepoints;
        if (codepoints) {
            this.props.onSelect(codepoints);
            this.gridRef.el.scrollTop = 0;
            this.props.close();
            this.props.onClose();
        }
    }

    highlightActiveCategory() {
        if (!this.gridRef || !this.gridRef.el) {
            return;
        }
        const coords = this.gridRef.el.getBoundingClientRect();
        const res = document.elementFromPoint(coords.x, coords.y);
        if (!res) {
            return;
        }
        this.state.categoryId = parseInt(res.dataset.category);
    }
}
