import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { Reactive } from "@web/core/utils/reactive";
import { escape } from "@web/core/utils/strings";

const cacheSnippetTemplate = {};

export class SnippetModel extends Reactive {
    constructor(services, { websiteId, snippetsName }) {
        super();
        this.websiteId = websiteId;
        this.orm = services.orm;
        this.dialog = services.dialog;
        this.snippetsName = snippetsName;

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
        if (!cacheSnippetTemplate[this.snippetsName]) {
            cacheSnippetTemplate[this.snippetsName] = this.orm.silent.call(
                "ir.ui.view",
                "render_public_asset",
                [this.snippetsName, {}],
                { context: { rendering_bundle: true, website_id: this.websiteId } }
            );
        }
        const html = await cacheSnippetTemplate[this.snippetsName];
        const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
        this.computeSnippetTemplates(snippetsDocument);
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
}
