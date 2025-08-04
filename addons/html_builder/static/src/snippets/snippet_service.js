import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { Reactive } from "@web/core/utils/reactive";
import { escape } from "@web/core/utils/strings";
import { AddSnippetDialog } from "./add_snippet_dialog";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { markup, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SnippetModel extends Reactive {
    constructor(services, { snippetsName, context }) {
        super();
        this.orm = services.orm;
        this.dialog = services.dialog;
        this.snippetsName = snippetsName;
        this.context = context;
        this.loadProm = null;

        this.snippetsByCategory = {
            snippet_groups: [],
            snippet_custom: [],
            snippet_structure: [],
            snippet_content: [],
            snippet_custom_content: [],
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

    get hasCustomInnerContents() {
        return !!this.snippetsByCategory.snippet_custom_content.length;
    }

    get snippetCustomInnerContents() {
        return this.snippetsByCategory.snippet_custom_content;
    }

    isCustomInnerContent(customSnippetName) {
        return !!this.snippetsByCategory.snippet_content.find(
            (snippet) => snippet.name === customSnippetName
        );
    }

    isCustomStructure(customSnippetName) {
        return !!this.snippetsByCategory.snippet_structure.find(
            (snippet) => snippet.name === customSnippetName
        );
    }

    getSnippet(category, id) {
        return this.snippetsByCategory[category].find((snippet) => snippet.id === id);
    }

    getSnippetByName(category, name) {
        return this.snippetsByCategory[category].find((snippet) => snippet.name === name);
    }

    installSnippetModule(snippet, installSnippetModule) {
        const bodyText = _t("Do you want to install %s App?", snippet.moduleDisplayName);
        const linkText = _t("More info about this app.");
        const linkUrl =
            "/odoo/action-base.open_module_tree/" + encodeURIComponent(snippet.moduleId);

        this.dialog.add(ConfirmationDialog, {
            title: _t("Install %s", snippet.moduleDisplayName),
            body: markup`${bodyText}\n<a href="${linkUrl}" target="_blank"><i class="oi oi-arrow-right me-1"></i>${linkText}</a>`,
            confirm: async () => installSnippetModule(snippet),
            confirmLabel: _t("Save and Install"),
            cancel: () => {},
        });
    }

    /**
     * Opens the snippet dialog on the group of the given snippet object and
     * allows to specify its behaviour when selecting a snippet and when closing
     * it.
     *
     * @param {Object} snippet the snippet object
     * @param {Object} - `onSelect` called when a snippet is selected. Must return
     *     an HTMLElement.
     *                 - `onClose` called when the dialog is closed.
     * @param {Object} editor
     */
    openSnippetDialog(snippet, { onSelect, onClose }, editor) {
        this.dialog.add(
            AddSnippetDialog,
            {
                selectedSnippet: snippet,
                snippetModel: this,
                selectSnippet: (...args) => {
                    const newSnippetEl = onSelect(...args);
                    this.updateSnippetContent(newSnippetEl);
                },
                installSnippetModule: editor.config.installSnippetModule,
                editor,
            },
            { onClose }
        );
    }

    load() {
        if (!this.loadProm) {
            this.loadProm = (async () => {
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
                this.snippetsDocument = new DOMParser().parseFromString(html, "text/html");
                const processors = registry.category("html_builder.snippetsPreprocessor").getAll();
                for (const processor of Object.values(processors)) {
                    processor(this.snippetsName, this.snippetsDocument);
                }
                this.computeSnippetTemplates(this.snippetsDocument);
                this.setSnippetName(this.snippetsDocument);
            })();
        }
        return this.loadProm;
    }

    /**
     * Reloads the snippet data, optionally updating the context.
     *
     * @param {Object} context - Optional context to override or extend the
     *                           current context.
     * @returns {Promise<void>} A promise that resolves once the snippets are
     *                          reloaded.
     */
    reload(context = {}) {
        this.loadProm = null;
        this.context = {
            ...this.context,
            ...context,
        };
        return this.load();
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
                    content: snippetEl.children[0],
                    viewId: parseInt(snippetEl.dataset.oeSnippetId),
                    key: snippetEl.dataset.oeSnippetKey,
                    thumbnailSrc: escape(snippetEl.dataset.oeThumbnail),
                    imagePreviewSrc: snippetEl.dataset.oImagePreview,
                    isCustom: false,
                    label: snippetEl.dataset.oLabel,
                    isDisabled: false,
                    forbidSanitize: false,
                };
                const moduleId = snippetEl.dataset.moduleId;
                if (moduleId) {
                    Object.assign(snippet, {
                        moduleId,
                        isInstallable: !!moduleId,
                        moduleDisplayName: snippetEl.dataset.moduleDisplayName,
                    });
                }
                if (snippetEl.dataset.oeForbidSanitize) {
                    Object.assign(snippet, { forbidSanitize: snippetEl.dataset.oeForbidSanitize });
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

        // Extract the custom inner content from the custom snippets and remove
        // those whose module is not installed.
        const customInnerContent = [];
        const customSnippets = this.snippetsByCategory.snippet_custom;
        for (let i = customSnippets.length - 1; i >= 0; i--) {
            const snippet = customSnippets[i];
            const customSnippetName = snippet.name.startsWith("s_button_")
                ? "s_button"
                : snippet.name;
            if (this.isCustomInnerContent(customSnippetName)) {
                customInnerContent.unshift(snippet);
                customSnippets.splice(i, 1);
            } else if (!this.isCustomStructure(customSnippetName)) {
                // If no structure snippet could be found, it means that the
                // module is not installed (i.e. the original snippet has no
                // `data-snippet` attribute).
                customSnippets.splice(i, 1);
            }
        }
        this.snippetsByCategory["snippet_custom_content"] = customInnerContent;
    }

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
    }

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
    }

    setSnippetName(snippetsDocument) {
        // TODO: this should probably be done in py
        for (const snippetEl of snippetsDocument.body.querySelectorAll("snippets > *")) {
            snippetEl.children[0].dataset["name"] = snippetEl.getAttribute("name");
        }
    }

    /**
     * Returns the original snippet object based on the given `data-snippet`
     * attribute.
     *
     * @param {String} snippetKey the `data-snippet` attribute of the snippet.
     * @returns {Object}
     */
    getOriginalSnippet(snippetKey) {
        if (!snippetKey) {
            return;
        }
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

    /**
     * Removes the previews from the given snippet.
     *
     * @param {HTMLElement} snippetEl
     */
    updateSnippetContent(snippetEl) {
        snippetEl.querySelectorAll(".s_dialog_preview").forEach((el) => el.remove());
    }

    /**
     * Saves the given snippet as a custom one and reloads all the snippets
     * to have access to it directly.
     *
     * @param {HTMLElement} snippetEl the snippet we want to save
     * @param {Array<Function>} cleanForSaveHandlers all the hanlders of the
     *     `clean_for_save_handlers` resources
     * @param {Function} wrapWithSaveSnippetHandlers a function that processes the snippet
     * before and/or after the cloning. E.g. stopping the interactions before
     * cloning and restarting them after cloning.
     * @returns
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
    }
}

registry.category("services").add("html_builder.snippets", {
    dependencies: ["orm", "dialog"],

    start(env, { orm, dialog }) {
        const services = { orm, dialog };
        const context = {
            lang: user.context.lang, // will be overridden by each module through reload().
            user_lang: user.context.lang,
        };

        const snippetModelsMap = new Map();
        const getSnippetModel = (snippetsName) => {
            if (snippetModelsMap.has(snippetsName)) {
                return snippetModelsMap.get(snippetsName);
            }
            snippetModelsMap.set(
                snippetsName,
                new SnippetModel(services, {
                    snippetsName,
                    context,
                })
            );
            return snippetModelsMap.get(snippetsName);
        };

        return { getSnippetModel };
    },
});

export function useSnippets(snippetsName) {
    const snippetsService = useService("html_builder.snippets");
    return useState(snippetsService.getSnippetModel(snippetsName));
}
