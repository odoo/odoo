import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { Component, xml } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { renderToElement } from "@web/core/utils/render";
import { url } from "@web/core/utils/urls";

class EditorMentionList extends Component {
    static template = xml`<div class="popover" t-on-pointerdown.stop="() => {}">
            <MentionList t-props="props"/>
        </div>`;
    static components = { MentionList };
    static props = {
        onSelect: Function,
        type: String,
        close: Function,
    };
}

export class MentionPlugin extends Plugin {
    static name = "mention";
    static dependencies = ["overlay", "dom", "history"];

    static resources = (p) => ({
        onBeforeInput: { handler: p.onBeforeInput.bind(p) },
    });

    setup() {
        this.mentionList = this.shared.createOverlay(EditorMentionList, {
            hasAutofocus: true,
        });
        this.addDomListener(this.document, "pointerdown", () => {
            this.mentionList.close();
        });
        this.addDomListener(this.document, "keydown", (ev) => {
            if (getActiveHotkey(ev) === "escape") {
                this.mentionList.close();
            }
        });
    }

    onSelect(ev, option) {
        this.mentionList.close();
        const mentionBlock = renderToElement("mail.Wysiwyg.mentionLink", {
            option,
            href: `${url("/web")}#model=${option.partner ? "res.partner" : "discuss.channel"}&id=${
                option.partner ? option.partner.id : option.channel.id
            }`,
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
                    close: () => this.mentionList.close(),
                },
            });
        }
    }
}
