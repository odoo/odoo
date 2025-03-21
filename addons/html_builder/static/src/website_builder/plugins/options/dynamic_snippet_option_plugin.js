import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { Cache } from "@web/core/utils/cache";
import { DynamicSnippetOption } from "./dynamic_snippet_option";

class DynamicSnippetOptionPlugin extends Plugin {
    static id = "dynamicSnippetOption";
    static shared = ["getComponentProps"];
    resources = {
        builder_options: [
            withSequence(10, {
                OptionComponent: DynamicSnippetOption,
                props: this.getComponentProps(),
                selector: ".s_dynamic_snippet",
            }),
        ],
        builder_actions: this.getActions(),
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
    getComponentProps() {
        return {
            fetchDynamicFilters: this.fetchDynamicFilters.bind(this),
            fetchDynamicFilterTemplates: this.fetchDynamicFilterTemplates.bind(this),
        };
    }
    getActions() {
        return {
            dynamicFilter: {
                isApplied: ({ editingElement: el, param }) =>
                    parseInt(el.dataset.filterId) === param.id,
                apply: ({ editingElement: el, param }) => {
                    el.dataset.filterId = param.id;
                    if (
                        !el.dataset.templateKey ||
                        !el.dataset.templateKey.includes(
                            `_${param.model_name.replaceAll(".", "_")}_`
                        )
                    ) {
                        // Only if filter's model name changed
                        this.updateTemplate(el, param.defaultTemplate);
                    }
                },
            },
            dynamicFilterTemplate: {
                isApplied: ({ editingElement: el, param }) => el.dataset.templateKey === param.key,
                apply: ({ editingElement: el, param }) => {
                    this.updateTemplate(el, param);
                },
            },
            customizeTemplate: {
                isApplied: ({ editingElement: el, param: { mainParam: customDataKey } }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    return customData[customDataKey];
                },
                apply: ({ editingElement: el, param: { mainParam: customDataKey }, value }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    customData[customDataKey] = true;
                    el.dataset.customTemplateData = JSON.stringify(customData);
                },
                clean: ({ editingElement: el, param: { mainParam: customDataKey }, value }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    customData[customDataKey] = false;
                    el.dataset.customTemplateData = JSON.stringify(customData);
                },
            },
        };
    }
    getTemplateClass(templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    }
    updateTemplate(el, template) {
        const newTemplateKey = template.key;
        const oldTemplateKey = el.dataset.templateKey;
        el.dataset.templateKey = newTemplateKey;
        if (oldTemplateKey) {
            el.classList.remove(this.getTemplateClass(oldTemplateKey));
        }
        el.classList.add(this.getTemplateClass(newTemplateKey));

        if (template.numOfEl) {
            el.dataset.numberOfElements = template.numOfEl;
        } else {
            delete el.dataset.numberOfElements;
        }
        if (template.numOfElSm) {
            el.dataset.numberOfElementsSmallDevices = template.numOfElSm;
        } else {
            delete el.dataset.numberOfElementsSmallDevices;
        }
        if (template.numOfElFetch) {
            el.dataset.numberOfRecords = template.numOfElFetch;
        }
        if (template.extraClasses) {
            el.dataset.extraClasses = template.extraClasses;
        } else {
            delete el.dataset.extraClasses;
        }
        if (template.columnClasses) {
            el.dataset.columnClasses = template.columnClasses;
        } else {
            delete el.dataset.columnClasses;
        }
    }
    async fetchDynamicFilters(params) {
        return this.dynamicFiltersCache.read(params);
    }
    async _fetchDynamicFilters(params) {
        return rpc("/website/snippet/options_filters", params);
    }
    async fetchDynamicFilterTemplates(params) {
        return this.dynamicFilterTemplatesCache.read(params);
    }
    async _fetchDynamicFilterTemplates(params) {
        return rpc("/website/snippet/filter_templates", params);
    }
}

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);
