import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

export class PingMentionPlugin extends Plugin {
    static id = "ping_mention";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        link_click_overrides: (ev, linkEl) => {
            if (linkEl.matches(".o_mail_redirect")) {
                this.services.popover.add(ev.target, AvatarCard, {
                    id: linkEl.dataset.oeId,
                    model: linkEl.dataset.oeModel,
                });
                return true;
            }
        },
        on_editor_started_handlers: this.onEditorStarted.bind(this),
        clean_for_save_processors: this.cleanForSave.bind(this),
    };

    setup() {
        super.setup();
        /** @type {import("models").Store} */
        this.store = this.services["mail.store"];
    }

    markAllMentionsAsPinged() {
        for (const mentionEl of this.editable.querySelectorAll(
            "a.o_mail_redirect:not([data-mail-pinged])"
        )) {
            mentionEl.dataset.mailPinged = "1";
        }
    }

    onEditorStarted() {
        this.markAllMentionsAsPinged();
    }

    cleanForSave(root) {
        this.markAllMentionsAsPinged();
        const { resId, resModel } = this.config.getRecordInfo();
        for (const mentionEl of root.querySelectorAll(
            "a.o_mail_redirect:not([data-mail-pinged])"
        )) {
            delete mentionEl.dataset.mailPinged;
            const { oeId, oeModel } = mentionEl.dataset;
            if (oeModel !== "res.partner") {
                continue;
            }
            const truncateUnicode = (str, max = 100) =>
                [...str].length > max ? [...str].slice(0, max - 1).join("") + "…" : str;
            const content = truncateUnicode(
                closestBlock(mentionEl)
                    .innerText.replace(mentionEl.innerText, ` ${mentionEl.innerText} `)
                    .trim()
            );
            // Do not await result
            this.services.orm.call("mail.thread", "message_notify", [0], {
                partner_ids: [parseInt(oeId)],
                body: _t("You have been mentioned: %(content)s", { content }),
                model: resModel,
                res_id: resId,
            });
        }
    }
}
