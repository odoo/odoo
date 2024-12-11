import { Component, onMounted, onPatched, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { loadEmoji, loader, useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
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
        this.store = useService("mail.store");
        this.picker = useEmojiPicker(
            null,
            { onSelect: this.toggleReaction.bind(this), class: "overflow-hidden rounded-2" },
            {
                position: "bottom-middle",
                popoverClass: "o-mail-QuickReactionMenu-pickerPopover",
            }
        );
        this.dropdown = useState(useDropdownState());
        this.frequentEmojiService = useService("web.frequent.emoji");
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

    togglePicker() {
        if (this.picker.isOpen) {
            this.picker.close();
        } else {
            this.picker.open(this.toggle);
        }
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
        this.picker.close();
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

    get navigationOptions() {
        return {
            // Bypass nested dropdown behavior to allow initial focus.
            onEnabled: null,
            hotkeys: {
                arrowright: (navigator) => navigator.next(),
                arrowleft: (navigator) => navigator.previous(),
                // Disable up and down navigation as it does not make sense for horizontal menu.
                arrowdown: null,
                arrowup: null,
            },
        };
    }
}
