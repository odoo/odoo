import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";

export class SaveTranslationPlugin extends Plugin {
    static id = "saveTranslation";
    static dependencies = ["translation"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        save_element_context_processors: (context) => omit(context, "delay_translations"),
        on_ready_to_save_document_handlers: this.saveTranslations.bind(this),
    };

    async saveTranslations() {
        const getGroup = (dataset) => [dataset.oeModel, dataset.oeId, dataset.oeField];

        const delayedTranslation = [...this.editable.querySelectorAll(".o_delay_translation")].map(
            (el) => ({ group: getGroup(el.dataset), content: {} })
        );

        const dirtyEls = this.editable.querySelectorAll(".o_dirty[data-oe-translation-source-sha]");
        const elTranslation = [...dirtyEls].map((el) => {
            const cleanedEl = this.processThrough("clean_for_save_processors", el.cloneNode(true));
            const sourceSha = el.dataset.oeTranslationSourceSha;
            return { group: getGroup(el.dataset), content: { [sourceSha]: cleanedEl.innerHTML } };
        });

        // This is not a good way to handle characters that needs escaping, as
        // attribute's text ends up escaped several times after save. But this
        // keeps the previous behavior: the `EscapeTextNodesPlugin` takes care
        // of escaping the content of text nodes (as the content of the
        // translation may come from xml nodes of a qweb view).
        // TODO: find a good solution to handle translation's escaping
        // (attributes's text vs xml nodes)
        const escapeTextNodesInHTML = (html) => {
            const spanEl = document.createElement("span");
            spanEl.innerHTML = html;
            return this.processThrough("clean_for_save_processors", spanEl).innerHTML;
        };

        const attrTranslation = this.dependencies.translation
            .getDirtyAttributeTranslationsInfo()
            .map((data) => ({
                group: getGroup(data),
                content: { [data.oeTranslationSourceSha]: escapeTextNodesInHTML(data.translation) },
            }));

        const lang = this.services.website.currentWebsite.metadata.lang;
        const allTranslations = [...elTranslation, ...attrTranslation, ...delayedTranslation];
        await Promise.all(
            Object.entries(Object.groupBy(allTranslations, (e) => JSON.stringify(e.group))).map(
                ([group, toSave]) => {
                    const [oeModel, oeId, oeField] = JSON.parse(group);
                    const contents = toSave.map((t) => t.content);
                    return rpc("/website/field/translation/update", {
                        model: oeModel,
                        record_id: [Number(oeId)],
                        field_name: oeField,
                        translations: { [lang]: Object.assign({}, ...contents) },
                    });
                }
            )
        );
    }
}

registry.category("translation-plugins").add(SaveTranslationPlugin.id, SaveTranslationPlugin);
