import { propComputed, propSignal, useHover } from "@mail/utils/common/hooks";
import { Component, props, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { emojiLoader, useLoadEmoji } from "@web/core/emoji_picker/emoji_loader";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @param {import("models").Store} store */
export const openReactionMenuType = (store) =>
    t.function([t.instanceOf(store.MessageReactions.Class)]);

export class MessageReactionList extends Component {
    static template = "mail.MessageReactionList";
    static components = { Dropdown };

    setup() {
        super.setup(...arguments);
        this.loadEmoji = useLoadEmoji();
        this.store = useService("mail.store");
        this.message = propSignal("message", t.instanceOf(this.store["mail.message"].Class));
        this.openReactionMenu = props.static("openReactionMenu", openReactionMenuType(this.store));
        this.reaction = propComputed("reaction", t.instanceOf(this.store.MessageReactions.Class));
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
            .map((persona) => this.message().getPersonaName(persona));
        const shortcode = emojiLoader.getShortCode(emoji);
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

    /**
     * @param {import("models").Message} message
     * @param {import("models").MessageReactions} reaction
     */
    hasSelfReacted(message, reaction) {
        return message.effectiveSelf.in(reaction.personas);
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} param1
     * @param {import("models").Message} param1.messageAtRender
     * @param {import("models").MessageReactions} param1.reactionAtRender
     */
    onClickReaction(ev, { messageAtRender, reactionAtRender }) {
        if (!messageAtRender.canAddReaction()) {
            return;
        }
        if (this.hasSelfReacted(messageAtRender, reactionAtRender)) {
            reactionAtRender.remove();
        } else {
            messageAtRender.react(reactionAtRender.content);
        }
    }

    onContextMenu(ev) {
        if (this.ui.isSmall) {
            ev.preventDefault();
            this.openReactionMenu();
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} param1
     * @param {import("models").MessageReactions} param1.reactionAtRender
     */
    onClickReactionList(ev, { reactionAtRender }) {
        this.preview.isOpen = false; // closes dropdown immediately as to not recover focus after dropdown closes
        this.openReactionMenu(reactionAtRender);
    }
}
