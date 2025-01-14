import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { Reactive } from "@web/core/utils/reactive";
import { escape } from "@web/core/utils/strings";
import { AddSnippetDialog } from "@html_builder/builder/builder_sidebar/tabs/block_tab/add_snippet_dialog/add_snippet_dialog";
export class SnippetModel extends Reactive {
    constructor(services, { snippetsName, installSnippetModule, context }) {
        super();
        this.orm = services.orm;
        this.dialog = services.dialog;
        this.snippetsName = snippetsName;
        this.websiteService = services.website;
        this.installSnippetModule = installSnippetModule;
        this.context = context;

        this.snippetsByCategory = {
            snippet_groups: [],
            snippet_custom: [],
            snippet_structure: [],
            snippet_content: [],
        };
    }

    get hasCustomGroup() {
        return !!this.snippetsByCategory.snippet_custom.length;
    }

    get snippetGroups() {
        const snippetGroups = this.snippetsByCategory.snippet_groups;
        if (this.hasCustomGroup) {
            return snippetGroups;
        }
        return snippetGroups.filter((snippet) => snippet.groupName !== "custom");
    }

    get snippetStructures() {
        return [
            ...this.snippetsByCategory.snippet_structure,
            ...this.snippetsByCategory.snippet_custom,
        ];
    }

    get snippetInnerContents() {
        return this.snippetsByCategory.snippet_content;
    }

    getSnippet(category, id) {
        return this.snippetsByCategory[category].filter((snippet) => snippet.id === id)[0];
    }

    async load() {
        const context = { ...this.context, rendering_bundle: true };
        if (context.user_lang) {
            context.lang = this.context.user_lang;
            context.snippet_lang = this.context.lang;
        }
        const html = await this.orm.silent.call(
            "ir.ui.view",
            "render_public_asset",
            [this.snippetsName, {}],
            { context }
        );
        const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
        this.computeSnippetTemplates(snippetsDocument);
        this.setSnippetName(snippetsDocument);
    }

    computeSnippetTemplates(snippetsDocument) {
        const snippetsBody = snippetsDocument.body;
        this.snippetsByCategory = {};
        for (const snippetCategory of snippetsBody.querySelectorAll("snippets")) {
            const snippets = [];
            for (const snippetEl of snippetCategory.children) {
                const snippet = {
                    id: uniqueId(),
                    title: snippetEl.getAttribute("name"),
                    name: snippetEl.children[0].dataset.snippet,
                    thumbnailSrc: escape(snippetEl.dataset.oeThumbnail),
                    isCustom: false,
                    imagePreviewSrc: snippetEl.dataset.oImagePreview,
                };
                const moduleId = snippetEl.dataset.moduleId;
                if (moduleId) {
                    Object.assign(snippet, {
                        moduleId,
                    });
                } else {
                    Object.assign(snippet, {
                        content: snippetEl.children[0],
                        viewId: parseInt(snippetEl.dataset.oeSnippetId),
                    });
                }
                switch (snippetCategory.id) {
                    case "snippet_groups":
                        snippet.groupName = snippetEl.dataset.oSnippetGroup;
                        break;
                    case "snippet_structure":
                        snippet.groupName = snippetEl.dataset.oGroup;
                        snippet.keyWords = snippetEl.dataset.oeKeywords;
                        break;
                    case "snippet_custom":
                        snippet.groupName = "custom";
                        snippet.isCustom = true;
                        break;
                }
                snippets.push(snippet);
            }
            this.snippetsByCategory[snippetCategory.id] = snippets;
        }
    }

    async deleteCustomSnippet(snippet) {
        return new Promise((resolve) => {
            const message = _t("Are you sure you want to delete the block %s?", snippet.title);
            this.dialog.add(
                ConfirmationDialog,
                {
                    body: message,
                    confirm: async () => {
                        const snippetCustom = this.snippetsByCategory.snippet_custom;
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
    }

    async renameCustomSnippet(snippet, newName) {
        if (newName === snippet.title) {
            return;
        }
        snippet.title = newName;
        await this.orm.call("ir.ui.view", "rename_snippet", [], {
            name: newName,
            view_id: snippet.viewId,
            template_key: this.snippetsName,
        });
    }

    setSnippetName(snippetsDocument) {
        // TODO: this should probably be done in py
        for (const snippetEl of snippetsDocument.body.querySelectorAll("snippets > *")) {
            snippetEl.children[0].dataset["name"] = snippetEl.getAttribute("name");
        }
    }

    /**
     * Returns the original snippet based on the given `data-snippet` attribute.
     *
     * @param {String} snippetKey the `data-snippet` attribute of the snippet.
     * @returns
     */
    getOriginalSnippet(snippetKey) {
        return [...this.snippetStructures, ...this.snippetInnerContents].find(
            (snippet) => snippet.name === snippetKey
        );
    }

    /**
     * Returns the snippet thumbnail URL.
     *
     * @param {String} snippetKey the `data-snippet` attribute of the snippet.
     * @returns
     */
    getSnippetThumbnailURL(snippetKey) {
        const originalSnippet = this.getOriginalSnippet(snippetKey);
        return originalSnippet.thumbnailSrc;
    }

    async replaceSnippet(snippetToReplace) {
        // Find the original snippet to open the dialog on the same group.
        const originalSnippet = this.getOriginalSnippet(snippetToReplace.dataset.snippet);
        let newSnippet;
        await new Promise((resolve) => {
            this.dialog.add(
                AddSnippetDialog,
                {
                    selectedSnippet: originalSnippet,
                    snippetModel: this,
                    selectSnippet: (selectedSnippet) => {
                        newSnippet = selectedSnippet.content.cloneNode(true);
                        snippetToReplace.replaceWith(newSnippet);
                    },
                    installModule: this.installSnippetModule,
                },
                { onClose: () => resolve() }
            );
        });
        return newSnippet;
    }

    saveSnippet(snippetEl, cleanForSaveHandlers) {
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

                        const snippetCopyEl = snippetEl.cloneNode(true);
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
                        await this.load();
                        resolve(savedName);
                    },
                },
                { onClose: () => resolve(false) }
            );
        });
    }
}
