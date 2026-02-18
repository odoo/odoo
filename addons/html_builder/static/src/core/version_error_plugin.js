import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class VersionErrorPlugin extends Plugin {
    static id = "versionError";
    static shared = ["checkNotifyOutdatedSnippet"];
    static dependencies = [];

    resources = {};

    /**
     * Checks if a snippet is up to date by comparing its versions (vcss, vxml, vjs)
     * with those of the original snippet in the model.
     *
     * @param {HTMLElement} el - The element to check (will look for parent with data-snippet if needed)
     * @returns {boolean} - true if the snippet is up to date, or if the element is not a snippet
     */
    isSnippetUpToDate(el) {
        const snippetEl = el?.closest?.("[data-snippet]");
        if (!snippetEl) {
            return true;
        }
        const snippetKey = snippetEl.dataset.snippet;
        const snippet = this.config.snippetModel.getOriginalSnippet(snippetKey);
        if (!snippet) {
            return true;
        }
        const {
            vcss: originalVcss,
            vxml: originalVxml,
            vjs: originalVjs,
        } = snippet.content.dataset;
        const { vcss: elVcss, vxml: elVxml, vjs: elVjs } = snippetEl.dataset;
        return originalVcss === elVcss && originalVxml === elVxml && originalVjs === elVjs;
    }

    /**
     * Checks if snippet is outdated. If yes, displays an appropriate
     * notification and returns true, otherwise return false.
     *
     * @param {HTMLElement} editingElement - The element being checked
     * @return {Boolean} - True if the snippet is outdated
     */
    checkNotifyOutdatedSnippet(editingElement) {
        if (!this.isSnippetUpToDate(editingElement)) {
            const notificationTitle = _t("This snippet is outdated");
            const existingNotifications = Array.from(
                document.querySelectorAll(".o_notification .o_notification_content")
            );
            const hasExistingNotification = existingNotifications.some((el) =>
                el.textContent.startsWith(notificationTitle)
            );
            if (!hasExistingNotification) {
                this.services.notification.add(
                    _t(
                        "It might have caused problem during the editing. Please drag the new version from the snippet panel to update it."
                    ),
                    {
                        type: "warning",
                        title: notificationTitle,
                        sticky: true,
                    }
                );
            }
            return true;
        }
        return false;
    }
}
