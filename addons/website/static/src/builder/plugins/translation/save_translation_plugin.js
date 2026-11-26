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

        const attrTranslation = this.dependencies.translation
            .getDirtyAttributeTranslationsInfo()
            .map((data) => ({
                group: getGroup(data),
                content: { [data.oeTranslationSourceSha]: data.translation },
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
