import { Plugin } from "@html_editor/plugin";
import { MentionList } from "@mail/core/web/mention_list";
import { makeMentionFromOption, SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";

export class MailFullComposerSuggestionPlugin extends Plugin {
    static id = "mail_full_composer_suggestion";
    static dependencies = ["overlay", "dom", "history", "input", "selection"];

    resources = {
        on_beforeinput_handlers: this.onBeforeInput.bind(this),
        selectors_for_feff_providers: () =>
            "a.o_mail_redirect, a.o_channel_redirect, a.o-discuss-mention",
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
        if (ev.data === SUGGESTION_DELIMITERS.PARTNER) {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
            this.mentionList.open({
                props: {
                    composerType: this.config.composerType,
                    onSelect: this.onSelect.bind(this),
                    thread: this.config.thread,
                    type: "Partner",
                    close: () => {
                        this.mentionList.close();
                    },
                },
            });
        }
    }
}
