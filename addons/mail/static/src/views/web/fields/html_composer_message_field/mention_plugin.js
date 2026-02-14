import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { router } from "@web/core/browser/router";
import { renderToElement } from "@web/core/utils/render";
import { url } from "@web/core/utils/urls";

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["overlay", "dom", "history", "input", "selection"];

    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
    };

    setup() {
        this.mentionList = this.dependencies.overlay.createOverlay(MentionList, {
            hasAutofocus: true,
            className: "popover o-mail-MentionPlugin-overlay",
        });
    }

    onSelect(ev, option) {
        this.dependencies.selection.focusEditable();
        const mentionBlock = renderToElement("mail.Wysiwyg.mentionLink", {
            option,
            href: url(
                router.stateToUrl({
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
        this.dependencies.dom.insert(mentionBlock);
        this.dependencies.history.addStep();
    }

    onBeforeInput(ev) {
        if (ev.data === "@" || ev.data === "#") {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
            this.mentionList.open({
                props: {
                    onSelect: this.onSelect.bind(this),
                    thread: this.config.thread,
                    type: ev.data === "@" ? "partner" : "channel",
                    close: () => {
                        this.mentionList.close();
                    },
                },
            });
        }
    }
}
