import { BEGIN } from "@html_builder/utils/option_sequence";
import { EmbedCodeOptionDialog } from "./embed_code_option_dialog";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { cloneContentEls } from "@website/js/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class EmbedCodeOption extends BaseOptionComponent {
    static template = "website.EmbedCodeOption";
    static selector = ".s_embed_code";
}

class EmbedCodeOptionPlugin extends Plugin {
    static id = "embedCodeOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(BEGIN, EmbedCodeOption)],
        so_content_addition_selector: [".s_embed_code"],
        builder_actions: {
            EditCodeAction,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

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

export class EditCodeAction extends BuilderAction {
    static id = "editCode";
    async load({ editingElement }) {
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
    }
    apply({ editingElement, loadResult: content }) {
        if (!content) {
            return;
        }
        // Remove scripts tags from the DOM as we don't want them to
        // interfere during edition, but keeps them in a
        // `<template>` that will be saved to the database.
        this.getTemplateEl(editingElement).content.replaceChildren(cloneContentEls(content, true));
        editingElement
            .querySelector(".s_embed_code_embedded")
            .replaceChildren(cloneContentEls(content));
    }
    getTemplateEl(editingElement) {
        return editingElement.querySelector("template.s_embed_code_saved");
    }
}

registry.category("website-plugins").add(EmbedCodeOptionPlugin.id, EmbedCodeOptionPlugin);
