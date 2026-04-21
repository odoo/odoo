import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { makeMentionFromOption } from "@mail/core/common/suggestion_hook";

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
        const mentionBlock = makeMentionFromOption(option, { thread: this.config.thread });
        if (!mentionBlock) {
            return;
        }
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
                    type: ev.data === "@" ? "Partner" : "Thread",
                    close: () => {
                        this.mentionList.close();
                    },
                },
            });
        }
    }
}
