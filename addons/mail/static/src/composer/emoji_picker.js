/** @odoo-module */

import { Component, onMounted, onWillStart, useRef, useState, onPatched } from "@odoo/owl";
import { getBundle, loadBundle } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { memoize } from "@web/core/utils/functions";

export function useEmojiPicker(refName, onSelect) {
    const ref = useRef(refName);
    const popover = usePopover();
    let closePopover = false;
    const toggle = () => {
        if (closePopover) {
            closePopover();
            closePopover = false;
        } else {
            closePopover = popover.add(
                ref.el,
                EmojiPicker,
                { onSelect },
                {
                    onClose: () => (closePopover = false),
                    popoverClass: "o-fast-popover",
                }
            );
        }
    };
    onMounted(() => {
        ref.el.addEventListener("click", toggle);
        ref.el.addEventListener("mouseenter", loadEmojiData);
    });
}

export const loadEmojiData = memoize(() => getBundle("mail.assets_model_data").then(loadBundle));

export class EmojiPicker extends Component {
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
            await loadEmojiData();
            const { emojiCategoriesData, emojisData } = await odoo.runtimeImport(
                "@mail/composer/emoji_data"
            );
            this.categories = emojiCategoriesData;
            this.emojis = emojisData;
            this.state.categoryId = this.categories[0].sortId;
        });
        onMounted(() => this.inputRef.el.focus());
        onPatched(() => {
            if (this.shouldScrollElem) {
                this.shouldScrollElem();
                this.shouldScrollElem = null;
            }
        });
    }

    getEmojis() {
        const search = this.state.searchStr;
        if (search.length > 1) {
            const regexp = new RegExp(search.split("").join(".*"));
            return this.emojis.filter((emoji) => {
                return emoji.name.match(regexp) || emoji.keywords.some((w) => w.match(regexp));
            });
        }
        return this.emojis;
    }

    selectCategory(ev) {
        const id = Number(ev.target.dataset.id);
        if (id) {
            this.state.categoryId = id;
            this.state.searchStr = "";
            const getElement = () =>
                this.gridRef.el.querySelector(`.o-emoji-category[data-category="${id}"`);
            const elem = getElement();
            if (elem) {
                elem.scrollIntoView();
            } else {
                this.shouldScrollElem = getElement;
            }
        }
    }

    selectEmoji(ev) {
        const index = ev.target.dataset.index;
        if (index) {
            const emoji = this.emojis[index];
            this.props.onSelect(emoji.codepoints);
            this.props.close();
        }
    }
}

Object.assign(EmojiPicker, {
    props: ["onSelect", "close"],
    template: "mail.emoji_picker",
});
