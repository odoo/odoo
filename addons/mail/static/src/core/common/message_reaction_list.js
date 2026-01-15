import { useHover } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageReactionList extends Component {
    static template = "mail.MessageReactionList";
    static components = { Dropdown };
    static props = ["message", "openReactionMenu", "reaction"];

    setup() {
        super.setup();
        this.loadEmoji = loadEmoji;
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.preview = useDropdownState();
        this.hover = useHover(["reactionButton", "reactionList"], {
            onHover: () => (this.preview.isOpen = true),
            onAway: () => (this.preview.isOpen = false),
            stateObserver: () => [this.preview?.isOpen],
        });
    }

    /** @param {import("models").MessageReactions} reaction */
    previewText(reaction) {
        const { count, content: emoji } = reaction;
        const personNames = reaction.personas
            .slice(0, 3)
            .map((persona) => this.props.message.getPersonaName(persona));
        const shortcode =
            this.store.emojiLoader.loaded?.emojiValueToShortcodes?.[emoji]?.[0] ?? "?";
        switch (count) {
            case 1:
                return _t("%(emoji)s reacted by %(person)s", {
                    emoji: shortcode,
                    person: personNames[0],
                });
            case 2:
                return _t("%(emoji)s reacted by %(person1)s and %(person2)s", {
                    emoji: shortcode,
                    person1: personNames[0],
                    person2: personNames[1],
                });
            case 3:
                return _t("%(emoji)s reacted by %(person1)s, %(person2)s, and %(person3)s", {
                    emoji: shortcode,
                    person1: personNames[0],
                    person2: personNames[1],
                    person3: personNames[2],
                });
            case 4:
                return _t(
                    "%(emoji)s reacted by %(person1)s, %(person2)s, %(person3)s, and 1 other",
                    {
                        emoji: shortcode,
                        person1: personNames[0],
                        person2: personNames[1],
                        person3: personNames[2],
                    }
                );
            default:
                return _t(
                    "%(emoji)s reacted by %(person1)s, %(person2)s, %(person3)s, and %(count)s others",
                    {
                        count: count - 3,
                        emoji: shortcode,
                        person1: personNames[0],
                        person2: personNames[1],
                        person3: personNames[2],
                    }
                );
        }
    }

    hasSelfReacted(reaction) {
        return this.props.message.effectiveSelf.in(reaction.personas);
    }

    onClickReaction(reaction) {
        if (!this.props.message.canAddReaction()) {
            return;
        }
        if (this.hasSelfReacted(reaction)) {
            reaction.remove();
        } else {
            this.props.message.react(reaction.content);
        }
    }

    onContextMenu(ev) {
        if (this.ui.isSmall) {
            ev.preventDefault();
            this.props.openReactionMenu();
        }
    }

    onClickReactionList(reaction) {
        this.preview.isOpen = false; // closes dropdown immediately as to not recover focus after dropdown closes
        this.props.openReactionMenu(reaction);
    }
}
