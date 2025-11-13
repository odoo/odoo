import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { applyTextHighlight } from "@website/js/highlight_utils";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(SnippetModel.prototype, {
    /**
     * @override
     */
    updateSnippetContent(snippetEl) {
        super.updateSnippetContent(...arguments);
        // Build the highlighted text content for new added snippets.
        for (const textEl of snippetEl?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    },

    /**
     * @override
     */
    getSnippetLabel(snippetEl) {
        const label = super.getSnippetLabel(snippetEl);
        // Check if any element in the snippet has the "parallax" class to show
        // the "Parallax" label. This must be done this way because a theme or
        // custom snippet may add or remove parallax elements. Note that if a
        // label is already set, we do not change it.
        if (!label) {
            const contentEl = snippetEl.children[0];
            if (contentEl.matches(".parallax") || !!contentEl.querySelector(".parallax")) {
                return _t("Parallax");
            }
        }
        return label;
    },

    /**
     * @override
     */
    async deleteCustomSnippet(snippet) {
        return new Promise((resolve) => {
            const message = _t("Are you sure you want to delete the block %s?", snippet.title);
            this.dialog.add(
                ConfirmationDialog,
                {
                    body: message,
                    confirm: async () => {
                        const isInnerContent =
                            this.snippetsByCategory.snippet_custom_content.includes(snippet);
                        const snippetCustom = isInnerContent
                            ? this.snippetsByCategory.snippet_custom_content
                            : this.snippetsByCategory.snippet_custom;
                        const index = snippetCustom.findIndex((s) => s.id === snippet.id);
                        if (index > -1) {
                            snippetCustom.splice(index, 1);
                        }
                        await this.orm.call("ir.ui.view", "delete_snippet", [], {
                            view_id: snippet.viewId,
                            template_key: this.snippetsName,
                        });
                    },
                    cancel: () => {},
                    confirmLabel: _t("Yes"),
                    cancelLabel: _t("No"),
                },
                {
                    onClose: resolve,
                }
            );
        });
    },

    /**
     * @override
     */
    async renameCustomSnippet(snippet, newName) {
        if (newName === snippet.title) {
            return;
        }
        snippet.title = newName;
        for (const snippetEl of this.snippetsDocument.body.querySelectorAll(
            `snippets#snippet_custom > [data-oe-snippet-key = ${snippet.key}]`
        )) {
            snippetEl.setAttribute("name", newName);
            snippetEl.children[0].dataset["name"] = newName;
        }
        await this.orm.call("ir.ui.view", "rename_snippet", [], {
            name: newName,
            view_id: snippet.viewId,
            template_key: this.snippetsName,
        });
    },

    /**
     * @override
     */
    saveSnippet(
        snippetEl,
        cleanForSaveHandlers,
        wrapWithSaveSnippetHandlers = (_, callback) => callback()
    ) {
        return new Promise((resolve) => {
            this.dialog.add(
                ConfirmationDialog,
                {
                    title: _t("Create a custom snippet"),
                    body: _t("Do you want to save this snippet as a custom one?"),
                    confirmLabel: _t("Save"),
                    cancel: () => resolve(false),
                    confirm: async () => {
                        const isButton = snippetEl.matches("a.btn");
                        const snippetKey = isButton ? "s_button" : snippetEl.dataset.snippet;
                        const thumbnailURL = this.getSnippetThumbnailURL(snippetKey);

                        const snippetCopyEl = await wrapWithSaveSnippetHandlers(snippetEl, () =>
                            snippetEl.cloneNode(true)
                        );

                        // "CleanForSave" the snippet copy (only its children in
                        // the case of a popup, or it will be saved as invisible
                        // and will not be visible in the "add snippet" dialog).
                        const rootEl = snippetEl.matches(".s_popup")
                            ? snippetCopyEl.firstElementChild
                            : snippetCopyEl;
                        cleanForSaveHandlers.forEach((handler) => handler({ root: rootEl }));

                        const defaultSnippetName = isButton
                            ? _t("Custom Button")
                            : _t("Custom %s", snippetEl.dataset.name);
                        snippetCopyEl.classList.add("s_custom_snippet");
                        delete snippetCopyEl.dataset.name;
                        if (isButton) {
                            snippetCopyEl.classList.remove("mb-2");
                            snippetCopyEl.classList.add(
                                "o_snippet_drop_in_only",
                                "s_custom_button"
                            );
                        }

                        const editableParentEl = snippetEl.closest(
                            "[data-oe-model][data-oe-field][data-oe-id]"
                        );
                        const context = {
                            ...this.context,
                            model: editableParentEl.dataset.oeModel,
                            field: editableParentEl.dataset.oeField,
                            resId: editableParentEl.dataset.oeId,
                        };
                        const savedName = await this.orm.call("ir.ui.view", "save_snippet", [], {
                            name: defaultSnippetName,
                            arch: snippetCopyEl.outerHTML,
                            template_key: this.snippetsName,
                            snippet_key: snippetKey,
                            thumbnail_url: thumbnailURL,
                            context,
                        });

                        // Reload the snippets so the sidebar is up to date.
                        await this.reload();
                        resolve(savedName);
                    },
                },
                { onClose: () => resolve(false) }
            );
        });
    },
});

registry
    .category("html_builder.snippetsPreprocessor")
    .add("website_snippets", (namespace, snippets) => {
        if (namespace === "website.snippets") {
            // This should be empty in master, it is used to fix snippets in stable.
        }
    });
