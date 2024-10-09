import { Plugin } from "@html_editor/plugin";
import { EmbedCodeOptionDialog } from "@html_builder/plugins/embed_code_option_dialog";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { cloneContentEls } from "@website/js/utils";

class EmbedCodeOptionPlugin extends Plugin {
    static id = "EmbedCodeOption";

    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.EmbedCodeOption",
                selector: ".s_embed_code",
            }),
        ],
        builder_actions: this.getActions(),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    getTemplateEl(editingElement) {
        return editingElement.querySelector("template.s_embed_code_saved");
    }

    getActions() {
        return {
            editCode: {
                load: async ({ editingElement }) => {
                    let newContent;
                    await new Promise((resolve) => {
                        this.services.dialog.add(
                            EmbedCodeOptionDialog,
                            {
                                title: _t("Edit embedded code"),
                                value: this.getTemplateEl(editingElement).innerHTML.trim(),
                                mode: "xml",
                                confirm: (newValue) => {
                                    newContent = newValue;
                                },
                            },
                            { onClose: resolve }
                        );
                    });
                    return newContent;
                },
                apply: ({ editingElement, loadResult: content }) => {
                    if (!content) {
                        return;
                    }
                    // Remove scripts tags from the DOM as we don't want them to
                    // interfere during edition, but keeps them in a
                    // `<template>` that will be saved to the database.
                    this.getTemplateEl(editingElement).content.replaceChildren(
                        cloneContentEls(content, true)
                    );
                    editingElement
                        .querySelector(".s_embed_code_embedded")
                        .replaceChildren(cloneContentEls(content));
                },
            },
        };
    }

    cleanForSave({ root }) {
        // Saving Embed Code snippets with <script> in the database, as these
        // elements are removed in edit mode.
        for (const embedCodeEl of root.querySelectorAll(".s_embed_code")) {
            const embedTemplateEl = embedCodeEl.querySelector(".s_embed_code_saved");
            if (embedTemplateEl) {
                embedCodeEl
                    .querySelector(".s_embed_code_embedded")
                    .replaceChildren(cloneContentEls(embedTemplateEl.content, true));
            }
        }
    }
}

registry.category("website-plugins").add(EmbedCodeOptionPlugin.id, EmbedCodeOptionPlugin);
