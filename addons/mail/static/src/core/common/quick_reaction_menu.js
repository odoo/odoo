import { Component, onMounted, onPatched, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { EmojiPicker, loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {Object} action
 * @property {Object} [classNames]
 * @property {import("models").Message} message
 * @property {boolean} [messageActive]
 * @extends {Component<Props, Env>}
 */
export class QuickReactionMenu extends Component {
    static template = "mail.QuickReactionMenu";
    static props = {
        action: Object,
        classNames: { type: Object, optional: true },
        message: Object,
        messageActive: { type: Boolean, optional: true },
    };
    static components = { Dropdown };
    static DEFAULT_EMOJIS = ["👍", "❤️", "🤣", "😯", "😅", "🙏"];

    setup() {
        this.toggle = useRef("toggle");
        this.store = useState(useService("mail.store"));
        this.picker = usePopover(EmojiPicker, {
            position: "bottom-end",
            popoverClass: "o-mail-QuickReactionMenu-pickerPopover shadow-none",
            animation: false,
            arrow: false,
            onPositioned: (el, { direction, variant }) =>
                el.classList.add(`o-popover--${direction[0]}${variant[0]}`),
        });
        this.dropdown = useState(useDropdownState());
        this.frequentEmojiService = useState(useService("web.frequent.emoji"));
        this.state = useState({ emojiLoaded: Boolean(loader.loaded) });
        if (!loader.loaded) {
            loader.onEmojiLoaded(() => (this.state.emojiLoaded = true));
        }
        onMounted(() => {
            void this.state.emojiLoaded;
            if (!loader.loaded) {
                loadEmoji();
            }
        });
        onPatched(() => void this.state.emojiLoaded);
    }

    openPicker() {
        this.dropdown.close();
        this.picker.open(this.toggle.el, { onSelect: this.toggleReaction.bind(this) });
    }

    getEmojiShortcode(emoji) {
        return loader.loaded?.emojiValueToShortcode?.[emoji] ?? "?";
    }

    onClick() {
        this.picker.close();
        if (this.dropdown.isOpen) {
            this.dropdown.close();
        } else {
            this.dropdown.open();
        }
    }

    toggleReaction(emoji) {
        const reaction = this.props.message.reactions.find(
            (r) => r.content === emoji && this.store.self.in(r.personas)
        );
        if (reaction) {
            reaction.remove();
        } else {
            this.props.message.react(emoji);
            this.frequentEmojiService.incrementEmojiUsage(emoji);
        }
        this.dropdown.close();
    }

    get attClass() {
        const invisible = !this.props.messageActive && !this.dropdown.isOpen && !this.picker.isOpen;
        return {
            ...this.props.classNames,
            invisible,
            visible: !invisible,
        };
    }

    reactedBySelf(emoji) {
        return this.props.message.reactions.some(
            (r) => r.content === emoji && this.store.self.in(r.personas)
        );
    }

    get mostFrequentEmojis() {
        const numberOfEmojis = 6;
        const mostFrequent = this.frequentEmojiService.getMostFrequent(numberOfEmojis);
        return mostFrequent.concat(
            QuickReactionMenu.DEFAULT_EMOJIS.filter((emoji) => !mostFrequent.includes(emoji)).slice(
                0,
                Math.max(0, numberOfEmojis - mostFrequent.length)
            )
        );
    }
}
