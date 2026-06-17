import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { makeMentionFromOption } from "@mail/core/common/suggestion_hook";

export class MailFullComposerSuggestionPlugin extends Plugin {
    static id = "mail_full_composer_suggestion";
    static dependencies = ["overlay", "dom", "history", "input", "selection"];

    resources = {
        on_beforeinput_handlers: this.onBeforeInput.bind(this),
        on_input_handlers: this.onInput.bind(this),
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
        this.dependencies.history.commit();
    }

    onBeforeInput(ev) {
        if (ev.data === "@" || ev.data === "#") {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
            this.mentionList.open({
                props: {
                    composerType: this.config.composerType,
                    onSelect: this.onSelect.bind(this),
                    thread: this.config.thread,
                    type: ev.data === "@" ? "Partner" : "discuss.channel",
                    close: ({ cancel = false } = {}) => {
                        this.mentionList.close();
                        if (cancel) {
                            this.dependencies.selection.focusEditable();
                            this.cursors.restore();
                        }
                    },
                },
            });
        }
    }

    onInput(ev) {
        if (ev.data === "@" || ev.data === "#") {
            // Track cursor position after insertion
            this.cursors = this.dependencies.selection.preserveSelection();
        }
    }
}
