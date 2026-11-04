import { Plugin } from "@html_editor/plugin";

import { PARTNER_MENTION_SELECTOR } from "@mail/utils/common/format";

/** @param {HTMLElement} mentionEl */
function unrenderPartnerMention(mentionEl) {
    mentionEl.classList.remove(
        "o-mail-partnerMention",
        "o-mail-partnerMention-failed",
        "o-mail-partnerMention-sent"
    );
    mentionEl.replaceChildren(mentionEl.textContent);
}

/**
 * Renders the partner mentions like in the message body. Only shown: the saved content keeps the
 * mention text.
 */
export class PartnerMentionPlugin extends Plugin {
    static id = "partnerMention";
    static dependencies = ["domObserver"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        clean_for_save_processors: (root) => {
            for (const mentionEl of root.querySelectorAll(".o-mail-partnerMention")) {
                unrenderPartnerMention(mentionEl);
            }
            return root;
        },
        // e.g. copied from a message where it is rendered: rendered again once inserted
        fragment_to_insert_processors: (fragment) => {
            for (const mentionEl of fragment.querySelectorAll(PARTNER_MENTION_SELECTOR)) {
                unrenderPartnerMention(mentionEl);
            }
            return fragment;
        },
        on_content_updated_handlers: () => this.renderPartnerMentions(),
        on_editor_started_handlers: () => this.renderPartnerMentions(),
    };

    /** Not recorded in the history, so that undo never comes back to an unrendered mention. */
    renderPartnerMentions() {
        this.dependencies.domObserver.ignore(() =>
            this.services["mail.store"].renderPartnerMentions(this.editable)
        );
    }
}
