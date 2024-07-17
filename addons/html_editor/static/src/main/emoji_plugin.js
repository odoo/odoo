import { Plugin } from "@html_editor/plugin";
import { Component, xml } from "@odoo/owl";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";

class EditorEmojiPicker extends Component {
    static template = xml`<div class="popover" t-on-mousedown.stop="() => {}">
            <EmojiPicker t-props="props"/>
        </div>`;
    static components = { EmojiPicker };
    static props = {
        close: Function,
        onSelect: Function,
    };
}

export class EmojiPlugin extends Plugin {
    static name = "emoji";
    static dependencies = ["overlay", "dom", "selection"];
    /** @type { (p: EmojiPlugin) => Record<string, any> } */
    static resources = (p) => ({
        powerboxCommands: [
            {
                category: "widget",
                name: _t("Emoji"),
                description: _t("Add an emoji"),
                fontawesome: "fa-smile-o",
                action() {
                    p.showEmojiPicker();
                },
            },
        ],
    });

    setup() {
        this.overlay = this.shared.createOverlay(EditorEmojiPicker, {
            position: "bottom-start",
            hasAutofocus: true,
        });
        this.addDomListener(this.document, "mousedown", () => {
            this.overlay.close();
        });
    }

    showEmojiPicker() {
        this.overlay.open({
            props: {
                close: () => {
                    this.overlay.close();
                },
                onSelect: (str) => {
                    this.shared.domInsert(str);
                    this.dispatch("ADD_STEP");
                },
            },
        });
    }
}
