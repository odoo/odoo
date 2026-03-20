import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { _t } from "@web/core/l10n/translation";
import { renderToFragment } from "@web/core/utils/render";

export class RecordSnapshotPlugin extends Plugin {
    static id = "recordSnapshot";
    static shared = ["createFragment"];

    resources = {
        builder_options: [withSequence(BEGIN, RecordSnapshotOption)],
        builder_actions: {
            SelectRecordAction,
        },
    };

    /**
     * Create a filled snippet fragment matching the passed model and ID.
     * Available fragments are determined by the contents fo the mass_mailing.record-snapshot-snippets registry.
     */
    async createFragment(model, id, fragmentKey) {
        const snippetInfo = registry
            .category("mass_mailing.record-snapshot-snippet-info")
            .get(model);
        const recordData = await this.services.orm.read(model, [id], snippetInfo.fields, {
            context: snippetInfo.context,
        });
        const additionalContext = await snippetInfo.additionalRenderingContext(
            recordData[0],
            this.services
        );
        const fragmentTemplate = snippetInfo.getSnippetName(fragmentKey);
        return renderToFragment(fragmentTemplate, {
            record: recordData[0],
            ...additionalContext,
        });
    }
}

export class RecordSnapshotOption extends BaseOptionComponent {
    static template = "mass_mailing.recordSnapshotOption";
    static selector = ".s_record_snapshot";

    getElementDataModel() {
        return this.env.getEditingElement().dataset.model;
    }

    getModelDisplayName() {
        const model = this.env.getEditingElement().dataset.model;
        const snippetInfo = registry
            .category("mass_mailing.record-snapshot-snippet-info")
            .get(model);
        return snippetInfo?.modelDisplayName || _t("Record");
    }

    getElementFragmentKey() {
        return this.env.getEditingElement().dataset.fragmentKey;
    }
}

class SelectRecordAction extends BuilderAction {
    static dependencies = ["builderOptions", "recordSnapshot"];
    static id = "selectRecordAction";

    getValue({ editingElement: el }) {
        if (el.dataset.id) {
            return JSON.stringify({
                id: parseInt(el.dataset.id),
                display_name: el.dataset.displayName,
                name: el.dataset.name,
            });
        }
        return;
    }

    async apply({ editingElement: el, value, params }) {
        value = JSON.parse(value);
        const fragment = await this.dependencies.recordSnapshot.createFragment(
            params.model,
            value.id,
            params.fragmentKey
        );
        const snapshotEl = this.document.createElement("div");
        snapshotEl.append(fragment);
        snapshotEl.dataset.model = params.model;
        snapshotEl.dataset.id = value.id;
        snapshotEl.dataset.name = value.name;
        snapshotEl.dataset.displayName = value.display_name;

        // Carry over class list, style and template name from old element
        snapshotEl.classList.add(...el.classList);
        snapshotEl.dataset.fragmentKey = params.fragmentKey;
        snapshotEl.style.cssText = el.style.cssText;

        el.before(snapshotEl);
        el.remove();

        this.dependencies.builderOptions.updateContainers(snapshotEl);
    }
}

registry.category("mass_mailing-plugins").add(RecordSnapshotPlugin.id, RecordSnapshotPlugin);
