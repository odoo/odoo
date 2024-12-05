import { DocumentSelector } from "@html_editor/main/media/media_dialog/document_selector";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

const documentMediaDialogTab = {
    id: "DOCUMENTS",
    title: _t("Documents"),
    Component: DocumentSelector,
    sequence: 15,
};

/**
 * Fallback for the FilePlugin, when embedded components are not available.
 */
export class DocumentPlugin extends Plugin {
    static id = "document";
    resources = {
        media_dialog_tabs_providers: () =>
            this.config.disableFile ? [] : [documentMediaDialogTab],
    };
}
