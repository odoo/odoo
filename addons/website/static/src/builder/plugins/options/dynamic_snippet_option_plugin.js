import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { DynamicSnippetOption } from "./dynamic_snippet_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { setOptionsDefaultValues, updateTemplate } from '@website/js/dynamic_snippet_utils';

export const DYNAMIC_SNIPPET = SNIPPET_SPECIFIC_END;

class DynamicSnippetOptionPlugin extends Plugin {
    static id = "dynamicSnippetOption";
    selector = ".s_dynamic_snippet";
    modelNameFilter = "";
    resources = {
        builder_options: [
            withSequence(DYNAMIC_SNIPPET, {
                OptionComponent: DynamicSnippetOption,
                props: {
                    modelNameFilter: this.modelNameFilter,
                },
                selector: this.selector,
            }),
        ],
        builder_actions: {
            DynamicFilterAction,
            DynamicFilterTemplateAction,
            CustomizeTemplateAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.dynamicFiltersCache = new Cache(this._fetchDynamicFilters, JSON.stringify);
        this.dynamicFilterTemplatesCache = new Cache(
            this._fetchDynamicFilterTemplates,
            JSON.stringify
        );
    }
    destroy() {
        super.destroy();
        this.dynamicFiltersCache.invalidate();
        this.dynamicFilterTemplatesCache.invalidate();
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            await setOptionsDefaultValues(snippetEl, this.modelNameFilter);
        }
    }
}

export class DynamicFilterAction extends BuilderAction {
    static id = "dynamicFilter";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        return parseInt(el.dataset.filterId) === params.id;
    }
    apply({ editingElement: el, params }) {
        el.dataset.filterId = params.id;
        if (
            !el.dataset.templateKey ||
            !el.dataset.templateKey.includes(`_${params.model_name.replaceAll(".", "_")}_`)
        ) {
            // Only if filter's model name changed
            updateTemplate(el, params.defaultTemplate);
        }
    }
}
export class DynamicFilterTemplateAction extends BuilderAction {
    static id = "dynamicFilterTemplate";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        return el.dataset.templateKey === params.key;
    }
    apply({ editingElement: el, params }) {
        updateTemplate(el, params);
    }
}
export class CustomizeTemplateAction extends BuilderAction {
    static id = "customizeTemplate";
    isApplied({ editingElement: el, params: { mainParam: customDataKey } }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        return customData[customDataKey];
    }
    apply({ editingElement: el, params: { mainParam: customDataKey }, value }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        customData[customDataKey] = true;
        el.dataset.customTemplateData = JSON.stringify(customData);
    }
    clean({ editingElement: el, params: { mainParam: customDataKey }, value }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        customData[customDataKey] = false;
        el.dataset.customTemplateData = JSON.stringify(customData);
    }
}

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);
