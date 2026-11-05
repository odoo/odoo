declare module "plugins" {
    import { suggestion_sources, MailSuggestionPlugin } from "@mail/core/common/plugin/suggestion/suggestion_plugin";
    import { MailComposerPlugin } from "@mail/core/common/plugin/mail_composer_plugin";
    import { MentionPlugin } from "@mail/core/common/plugin/mention_plugin";
    import { PersistSelectionPlugin } from "@mail/core/common/plugin/persist_selection_plugin";
    import { RecordLinkEditorPlugin } from "@mail/core/common/plugin/record_link_editor_plugin";

    interface SharedMethods {
        mail_composer: SharedOf<typeof MailComposerPlugin>;
        mention: SharedOf<typeof MentionPlugin>;
        persistSelection: SharedOf<typeof PersistSelectionPlugin>;
        recordLink: SharedOf<typeof RecordLinkEditorPlugin>;
        suggestion: SharedOf<typeof MailSuggestionPlugin>;
    }

    export interface EditorResourcesList {
        suggestion_sources: suggestion_sources;
    }
}
