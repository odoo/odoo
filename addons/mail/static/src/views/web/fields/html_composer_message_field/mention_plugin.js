import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { stateToUrl } from "@web/core/browser/router";
import { renderToElement } from "@web/core/utils/render";
import { url } from "@web/core/utils/urls";

export class MentionPlugin extends Plugin {
    static name = "mention";
    static dependencies = ["overlay", "dom", "history", "selection"];

    resources = {
        onBeforeInput: this.onBeforeInput.bind(this),
    };

    setup() {
        this.mentionList = this.shared.createOverlay(MentionList, {
            hasAutofocus: true,
            className: "popover",
        });
    }

    onSelect(ev, option) {
        const mentionBlock = renderToElement("mail.Wysiwyg.mentionLink", {
            option,
            href: url(
                stateToUrl({
                    model: option.partner ? "res.partner" : "discuss.channel",
                    resId: option.partner ? option.partner.id : option.channel.id,
                })
            ),
        });
        const nameNode = this.document.createTextNode(
            `${option.partner ? "@" : "#"}${option.label}`
        );
        mentionBlock.appendChild(nameNode);
        this.historySavePointRestore();
        this.shared.domInsert(mentionBlock);
        this.dispatch("ADD_STEP");
    }

    onBeforeInput(ev) {
        if (ev.data === "@" || ev.data === "#") {
            this.historySavePointRestore = this.shared.makeSavePoint();
            this.mentionList.open({
                props: {
                    onSelect: this.onSelect.bind(this),
                    type: ev.data === "@" ? "partner" : "channel",
                    close: () => {
                        this.mentionList.close();
                        this.shared.focusEditable();
                    },
                },
            });
        }
    }
}
