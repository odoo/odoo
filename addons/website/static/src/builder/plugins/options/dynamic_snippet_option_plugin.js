import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { BuilderAction } from "@html_builder/core/builder_action";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { generateHTMLId } from "@web/core/utils/strings";

/**
 * @typedef {object} Template
 * @property {number} id
 * @property {string} name
 * @property {string} columnClasses
 * @property {string} containerClasses
 * @property {string} contentClasses
 * @property {string} extraClasses
 * @property {string} extraSnippetClasses
 * @property {string} key
 * @property {string} numberOfElements
 * @property {string} numberOfElementsSmallDevices
 * @property {string} limit
 * @property {string} rowPerSlide
 * @property {string} thumb
 */

/**
 * @typedef { Object } DynamicSnippetOptionShared
 * @property { DynamicSnippetOptionPlugin['fetchDynamicFilters'] } fetchDynamicFilters
 * @property { DynamicSnippetOptionPlugin['fetchDynamicSnippetTemplates'] } fetchDynamicSnippetTemplates
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetFilterId'] } getDefaultSnippetFilterId
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetRecordId'] } getDefaultSnippetRecordId
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetTemplate'] } getDefaultSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['getSnippetModelName'] } getSnippetModelName
 * @property { DynamicSnippetOptionPlugin['getSnippetTitleClasses'] } getSnippetTitleClasses
 * @property { DynamicSnippetOptionPlugin['getTemplateByKey'] } getTemplateByKey
 * @property { DynamicSnippetOptionPlugin['isModelSnippetTemplate'] } isModelSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['isSingleModeSnippet'] } isSingleModeSnippet
 * @property { DynamicSnippetOptionPlugin['isSingleModeSnippetTemplate'] } isSingleModeSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['updateTemplate'] } updateTemplate
 * @property { DynamicSnippetOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

/**
 * @typedef {((domain: import("@web/core/domain").DomainListRepr, args: { snippetEl: HTMLElement }) => domain)[]} dynamic_filter_contextual_domain_processors
 * @typedef {((domain: import("@web/core/domain").DomainListRepr, domainInfo: Object) => domain)[]} dynamic_filter_search_domain_processors
 * @typedef {((snippetEl: HTMLElement) => string?)[]} model_name_filter_overrides
 */

export const CONTAINER_CLASSES = ["container", "container-fluid", "o_container_small"];

export function getSharedSnippetArg(el, name) {
    return el.hasAttribute("data-arg-" + name)
        ? JSON.parse(el.getAttribute("data-arg-" + name))
        : undefined;
}
export function setSharedSnippetArg(el, name, value) {
    if (value === undefined) {
        el.removeAttribute("data-arg-" + name);
    } else {
        el.setAttribute("data-arg-" + name, JSON.stringify(value));
    }
}
export function setSharedSnippetInnerArg(el, name, key, value) {
    const currentArg = getSharedSnippetArg(el, name) ?? {};
    if (value === undefined) {
        if (!(key in currentArg)) {
            return;
        }
        delete currentArg[key];
    } else {
        currentArg[key] = value;
    }
    setSharedSnippetArg(el, name, currentArg);
}
export function setSharedSnippetArgIfUndefined(el, name, value) {
    if (!el.hasAttribute("data-arg-" + name)) {
        setSharedSnippetArg(el, name, value);
    }
}

export function dynamicContentOfDynamicSnippet(el) {
    return el.querySelector(
        '[data-oe-shared-snippet="website.shared_snippet_template_dynamic_snippet_content"]'
    );
}

export class DynamicSnippetOptionPlugin extends Plugin {
    static id = "dynamicSnippetOption";
    static shared = [
        "fetchDynamicFilters",
        "fetchDynamicSnippetTemplates",
        "getDefaultSnippetFilterId",
        "getDefaultSnippetRecordId",
        "getDefaultSnippetTemplate",
        "getSnippetModelName",
        "getSnippetTitleClasses",
        "getTemplateByKey",
        "isModelSnippetTemplate",
        "isSingleModeSnippet",
        "isSingleModeSnippetTemplate",
        "updateTemplate",
        "getModelNameFilter",
    ];
    fetchedDynamicFilters = [];
    fetchedDynamicFilterTemplates = [];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            DynamicFilterAction,
            DynamicSnippetTemplateAction,
            DynamicModelAction,
            DynamicRecordAction,
            CustomizeTemplateAction,
            NumberOfRecordsAction,
            DynamicSnippetInnerArgAction,
            DynamicSearchDomainJsonAction,
            DynamicSearchDomainAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_cloned_handlers: ({ cloneEl }) => this.assignUniqueID(cloneEl),
        is_unremovable_selectors: ".s_dynamic_snippet_title",
        dynamic_snippet_wrapper_templates_with_single_mode:
            "website.s_dynamic_snippet_wrapper_grid",
    };
    setup() {
        this.dynamicFiltersCache = new Cache(this._fetchDynamicFilters, JSON.stringify);
        this.dynamicFilterTemplatesCache = new Cache(
            this._fetchDynamicSnippetTemplates,
            JSON.stringify
        );
    }
    destroy() {
        super.destroy();
        this.dynamicFiltersCache.invalidate();
        this.dynamicFilterTemplatesCache.invalidate();
    }
    getModelNameFilter(snippetEl) {
        for (const override of this.getResource("model_name_filter_overrides")) {
            const name = override(snippetEl);
            if (name) {
                return name;
            }
        }
        return "";
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic")) {
            await this.setOptionsDefaultValues(snippetEl);
        }
        this.assignUniqueID(snippetEl);
    }
    assignUniqueID(snippetEl) {
        const dynamicEl = dynamicContentOfDynamicSnippet(snippetEl);
        if (!dynamicEl) {
            return;
        }
        const uniqueId = generateHTMLId("sDynamicSnippet");
        setSharedSnippetInnerArg(dynamicEl, "wrapper_data", "unique_id", uniqueId);
    }
    async setOptionsDefaultValues(snippetEl) {
        const modelNameFilter = this.getModelNameFilter(snippetEl);
        await this.fetchDynamicFilters({
            model_name: modelNameFilter,
            search_domain: this.processThrough("dynamic_filter_contextual_domain_processors", [], {
                snippetEl,
            }),
        });
        await this.fetchDynamicSnippetTemplates(modelNameFilter);

        const dynamicFilters = {};
        for (const dynamicFilter of this.fetchedDynamicFilters) {
            dynamicFilters[dynamicFilter.id] = dynamicFilter;
        }
        const dynamicFilterTemplates = {};
        for (const dynamicFilterTemplate of this.fetchedDynamicFilterTemplates) {
            dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
        }
        const dynamicEl = dynamicContentOfDynamicSnippet(snippetEl);
        const defaultModelName = modelNameFilter || this.fetchedDynamicFilters[0]?.model_name;
        const isSingleMode = this.isSingleModeSnippet({
            dynamicEl,
            model: defaultModelName,
        });
        // The snippet simply gets its template from a "template class"
        // when provided. Otherwise, it will use a default template.
        let defaultTemplate = this.fetchedDynamicFilterTemplates.find((template) =>
            snippetEl.classList.contains(this.getTemplateClass(template.key))
        );
        if (!defaultTemplate) {
            defaultTemplate = this.getDefaultSnippetTemplate(defaultModelName, isSingleMode);
        }
        if (isSingleMode) {
            if (defaultModelName) {
                setSharedSnippetArgIfUndefined(dynamicEl, "res_model", defaultModelName);
            }
            const defaultSnippetRecordId = await this.getDefaultSnippetRecordId(defaultModelName);
            if (defaultSnippetRecordId) {
                setSharedSnippetArgIfUndefined(dynamicEl, "res_id", defaultSnippetRecordId);
            }
            setSharedSnippetArgIfUndefined(dynamicEl, "content_template", defaultTemplate.key);
            this.updateTemplate(snippetEl, dynamicEl, defaultTemplate);
        } else {
            let selectedFilterId = getSharedSnippetArg(dynamicEl, "filter_id");
            if (Object.keys(dynamicFilters).length > 0) {
                setSharedSnippetArgIfUndefined(
                    dynamicEl,
                    "limit",
                    this.fetchedDynamicFilters[0].limit
                );
                const defaultFilterId = this.fetchedDynamicFilters[0].id;
                if (!dynamicFilters[selectedFilterId]) {
                    setSharedSnippetArg(dynamicEl, "filter_id", defaultFilterId);
                    selectedFilterId = defaultFilterId;
                }
            }
            if (
                dynamicFilters[selectedFilterId] &&
                !dynamicFilterTemplates[getSharedSnippetArg(dynamicEl, "content_template")]
            ) {
                setSharedSnippetArg(dynamicEl, "content_template", defaultTemplate.key);
                this.updateTemplate(snippetEl, dynamicEl, defaultTemplate);
            }
        }
    }
    getTemplateByKey(templateKey) {
        return (
            templateKey && this.fetchedDynamicFilterTemplates.find(({ key }) => key === templateKey)
        );
    }
    getTemplateClass(templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    }
    updateTemplate(snippetEl, dynamicEl, template) {
        const newTemplateKey = template.key;
        const oldTemplateKey = getSharedSnippetArg(dynamicEl, "content_template");
        const oldTemplate = this.getTemplateByKey(oldTemplateKey);
        setSharedSnippetArg(dynamicEl, "content_template", newTemplateKey);
        if (oldTemplateKey) {
            snippetEl.classList.remove(this.getTemplateClass(oldTemplateKey));
        }
        snippetEl.classList.add(this.getTemplateClass(newTemplateKey));

        const wrapperData = getSharedSnippetArg(dynamicEl, "wrapper_data") ?? {};
        for (const [keyInTemplate, keyInData] of [
            ["numberOfElements", "number_of_elements"],
            ["numberOfElementsSmallDevices", "number_of_elements_small_devices"],
            ["extraClasses", "extra_classes"],
            ["columnClasses", "column_classes"],
            ["rowPerSlide", "row_per_slide"],
        ]) {
            if (template[keyInTemplate]) {
                wrapperData[keyInData] = template[keyInTemplate];
            } else {
                delete wrapperData[keyInData];
            }
        }
        setSharedSnippetArg(dynamicEl, "wrapper_data", wrapperData);
        if (template.limit) {
            setSharedSnippetArg(dynamicEl, "limit", template.limit);
        }
        if (oldTemplate) {
            const snippetContainerEl = snippetEl.querySelector(".s_dynamic_snippet_container");
            snippetContainerEl.classList.remove(...CONTAINER_CLASSES);
            snippetContainerEl.classList.add(
                ...(template.containerClasses || "container").split(" ")
            );

            dynamicEl.classList.remove(...(oldTemplate.contentClasses?.split(" ") || []));
            dynamicEl.classList.add(...(template.contentClasses?.split(" ") || []));

            snippetEl.classList.remove(...(oldTemplate.extraSnippetClasses?.split(" ") || []));
            snippetEl.classList.add(...(template.extraSnippetClasses?.split(" ") || []));
        }
    }
    async fetchDynamicFilters(params) {
        this.fetchedDynamicFilters = await this.dynamicFiltersCache.read(params);
        return this.fetchedDynamicFilters;
    }
    async _fetchDynamicFilters(params) {
        return rpc("/website/snippet/options_filters", params);
    }
    async fetchDynamicSnippetTemplates(modelName) {
        this.fetchedDynamicFilterTemplates = await this.dynamicFilterTemplatesCache.read({
            filter_name: modelName.replaceAll(".", "_"),
        });
        return this.fetchedDynamicFilterTemplates;
    }
    async _fetchDynamicSnippetTemplates(params) {
        return rpc("/website/snippet/filter_templates", params);
    }
    isSingleModeSnippet({ dynamicEl, model }) {
        // TODO: Currently, we need to verify that at least one template is
        // available for single record mode to be enabled. This check should be
        // removed once all single record templates have been added.
        return !!(
            getSharedSnippetArg(dynamicEl, "limit") === 1 &&
            this.getDefaultSnippetTemplate(model || this.getSnippetModelName(dynamicEl), true) &&
            this.getResource("dynamic_snippet_wrapper_templates_with_single_mode").includes(
                getSharedSnippetArg(dynamicEl, "wrapper_template")
            )
        );
    }
    isSingleModeSnippetTemplate(key) {
        return key.includes("_single_");
    }
    isModelSnippetTemplate(key, modelName) {
        return modelName && key.includes(`_${modelName.replaceAll(".", "_")}_`);
    }
    getDefaultSnippetTemplate(modelName, singleMode) {
        if (modelName) {
            // Return the default snippet template associated with the current
            // model for either single or multi-record modes.
            return this.fetchedDynamicFilterTemplates.find((template) => {
                const isSingleTemplate = this.isSingleModeSnippetTemplate(template.key);
                return (
                    this.isModelSnippetTemplate(template.key, modelName) &&
                    (singleMode ? isSingleTemplate : !isSingleTemplate)
                );
            });
        }
    }
    async getDefaultSnippetRecordId(modelName) {
        const defaultRecrod = await this.services.orm.searchRead(
            modelName,
            [["is_published", "=", true]],
            ["id"],
            { limit: 1 }
        );
        return defaultRecrod[0]?.id || "";
    }
    getDefaultSnippetFilterId(modelName) {
        return this.fetchedDynamicFilters.find(({ model_name }) => model_name === modelName).id;
    }
    getSnippetModelName(dynamicEl) {
        return (
            getSharedSnippetArg(dynamicEl, "res_model") ||
            this.fetchedDynamicFilters.find(
                ({ id }) => id === getSharedSnippetArg(dynamicEl, "filter_id")
            )?.model_name
        );
    }
    getSnippetTitleClasses(position) {
        const classes = {
            left: "d-flex justify-content-between s_dynamic_snippet_title_aside col-lg-3 flex-lg-column justify-content-lg-start",
            top: "d-flex justify-content-between",
            none: "d-none",
        };
        return position ? classes[position] : classes;
    }
}

export class DynamicFilterAction extends BuilderAction {
    static id = "dynamicFilter";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        return getSharedSnippetArg(dynamicContentOfDynamicSnippet(el), "filter_id") === params.id;
    }
    async apply({ editingElement: el, params }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        const utils = this.dependencies.dynamicSnippetOption;
        let defaultTemplate = params.defaultTemplate;
        setSharedSnippetArg(dynamicEl, "filter_id", params.id);
        // Only if filter's model name changed
        const templateKey = getSharedSnippetArg(dynamicEl, "content_template");
        if (!templateKey || !utils.isModelSnippetTemplate(templateKey, params.model_name)) {
            if (utils.isSingleModeSnippet({ dynamicEl })) {
                setSharedSnippetArg(dynamicEl, "res_model", params.model_name);
                setSharedSnippetArg(dynamicEl, "filter_id", undefined);
                defaultTemplate = utils.getDefaultSnippetTemplate(params.model_name, true);
                const defaultResId = await utils.getDefaultSnippetRecordId(params.model_name);
                setSharedSnippetArg(dynamicEl, "res_id", defaultResId);
            }
            utils.updateTemplate(el, dynamicEl, defaultTemplate);
        }
    }
}
export class DynamicSnippetTemplateAction extends BuilderAction {
    static id = "dynamicSnippetTemplate";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        return getSharedSnippetArg(dynamicEl, "content_template") === params.key;
    }
    apply({ editingElement: el, params }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        this.dependencies.dynamicSnippetOption.updateTemplate(el, dynamicEl, params);
    }
}
export class CustomizeTemplateAction extends BuilderAction {
    static id = "customizeTemplate";
    isApplied({ editingElement, params: { mainParam: customDataKey } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        return getSharedSnippetArg(dynamicEl, "content_data")[customDataKey];
    }
    apply({ editingElement, params: { mainParam: customDataKey } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        setSharedSnippetInnerArg(dynamicEl, "content_data", customDataKey, true);
    }
    clean({ editingElement, params: { mainParam: customDataKey } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        setSharedSnippetInnerArg(dynamicEl, "content_data", customDataKey, false);
    }
}
export class DynamicModelAction extends BuilderAction {
    static id = "dynamicModel";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params: { mainParam: modelName } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        return getSharedSnippetArg(dynamicEl, "res_model") === modelName;
    }
    async apply({ editingElement: el, params: { mainParam: modelName } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        const utils = this.dependencies.dynamicSnippetOption;
        // Update the snippet data attributes (only available in the
        // "single record" mode).
        if (getSharedSnippetArg(dynamicEl, "res_model") !== modelName) {
            setSharedSnippetArg(dynamicEl, "res_model", modelName);
            const newResId = parseInt(await utils.getDefaultSnippetRecordId(modelName));
            setSharedSnippetArg(dynamicEl, "res_id", newResId);
            utils.updateTemplate(el, dynamicEl, utils.getDefaultSnippetTemplate(modelName, true));
        }
    }
}

export class DynamicRecordAction extends BuilderAction {
    static id = "dynamicRecord";
    getValue({ editingElement }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const resId = getSharedSnippetArg(dynamicEl, "res_id");
        return resId && JSON.stringify({ id: resId });
    }
    apply({ editingElement, value }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const { id } = JSON.parse(value);
        setSharedSnippetArg(dynamicEl, "res_id", id);
    }
}
export class NumberOfRecordsAction extends BuilderAction {
    static id = "numberOfRecords";
    static dependencies = ["dynamicSnippetOption", "builderActions"];

    setup() {
        this.previousTemplate = false;
        this.utils = this.dependencies.dynamicSnippetOption;
    }
    async load({ editingElement }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const modelName = this.utils.getSnippetModelName(dynamicEl);
        return {
            modelName,
            defaultRecordId: await this.utils.getDefaultSnippetRecordId(modelName),
        };
    }
    isApplied({ editingElement: el, params }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        return getSharedSnippetArg(dynamicEl, "limit") === params.mainParam;
    }
    apply({ editingElement: el, params, loadResult }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(el);
        const isSingleModeBefore = this.utils.isSingleModeSnippet({ dynamicEl });
        setSharedSnippetArg(dynamicEl, "limit", params.mainParam);
        // Changing the number of records should automatically switch to a
        // "single record" filter mode if only one record is selected, and
        // conversely, revert to the default filter mode when more than one
        // record is selected.
        const isSingleModeAfter = this.utils.isSingleModeSnippet({ dynamicEl });
        const switchMode = isSingleModeBefore !== isSingleModeAfter;
        if (switchMode) {
            const canUsePreviousTemplate =
                !!this.previousTemplate &&
                this.utils.isModelSnippetTemplate(
                    this.previousTemplate.key,
                    loadResult.modelName
                ) &&
                !!this.utils.isSingleModeSnippetTemplate(this.previousTemplate.key) ===
                    isSingleModeAfter;
            const newModeDefaultTemplate = !canUsePreviousTemplate
                ? this.utils.getDefaultSnippetTemplate(loadResult.modelName, isSingleModeAfter)
                : this.previousTemplate;
            this.previousTemplate = this.utils.getTemplateByKey(
                getSharedSnippetArg(dynamicEl, "content_template")
            );
            if (isSingleModeAfter) {
                // Remove useless data on the target and set the single
                // record default values.
                setSharedSnippetArg(dynamicEl, "filter_id", undefined);
                setSharedSnippetArg(dynamicEl, "res_model", loadResult.modelName);
                setSharedSnippetArg(dynamicEl, "res_id", loadResult.defaultRecordId);
            } else {
                setSharedSnippetArg(
                    dynamicEl,
                    "filter_id",
                    this.utils.getDefaultSnippetFilterId(loadResult.modelName)
                );
                setSharedSnippetArg(dynamicEl, "res_model", undefined);
                setSharedSnippetArg(dynamicEl, "res_id", undefined);
            }
            // Update the snippet title section.
            const titleEl = el.querySelector(".s_dynamic_snippet_title");
            const classAction = this.dependencies.builderActions.getAction("classAction");
            const titleClasses = Object.values(this.utils.getSnippetTitleClasses()).find(
                (classes) =>
                    titleEl.matches(
                        classes
                            .split(" ")
                            .map((c) => "." + c)
                            .join("")
                    )
            );
            classAction.clean({
                editingElement: titleEl,
                params: { mainParam: titleClasses },
            });
            classAction.apply({
                editingElement: titleEl,
                params: {
                    mainParam: this.utils.getSnippetTitleClasses(
                        isSingleModeAfter ? "none" : "top"
                    ),
                },
            });
            this.utils.updateTemplate(el, dynamicEl, newModeDefaultTemplate);
        }
    }
}

export class DynamicSnippetInnerArgAction extends BuilderAction {
    static id = "dynamicSnippetInnerArg";
    isApplied({ editingElement, params: { arg, key }, value }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        return getSharedSnippetArg(dynamicEl, arg)?.[key] === value;
    }
    getValue({ editingElement, params: { arg, key } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        return getSharedSnippetArg(dynamicEl, arg)?.[key];
    }
    apply({ editingElement, params: { arg, key }, value }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        setSharedSnippetInnerArg(dynamicEl, arg, key, value);
    }
    clean({ editingElement, params: { arg, key } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        setSharedSnippetInnerArg(dynamicEl, arg, key, undefined);
    }
}

export class DynamicSearchDomainAction extends BuilderAction {
    static id = "dynamicSearchDomain";
    getValue({ editingElement, params: { mainParam: key } }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        if (dynamicEl.dataset.searchDomainInfo) {
            return JSON.parse(dynamicEl.dataset.searchDomainInfo)?.[key];
        }
    }
    isApplied(args) {
        return this.getValue(args) === args.value;
    }
    apply(args) {
        this.writeValue(args);
    }
    clean(args) {
        this.writeValue({ ...args, value: undefined });
    }
    writeValue({ editingElement, params: { mainParam: key }, value }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const searchDomainInfo = dynamicEl.dataset.searchDomainInfo
            ? JSON.parse(dynamicEl.dataset.searchDomainInfo)
            : {};
        if (value === undefined) {
            delete searchDomainInfo[key];
        } else {
            searchDomainInfo[key] = value;
        }
        dynamicEl.dataset.searchDomainInfo = JSON.stringify(searchDomainInfo);
        setSharedSnippetArg(
            dynamicEl,
            "search_domain",
            this.processThrough("dynamic_filter_search_domain_processors", [], searchDomainInfo)
        );
    }
}

export class DynamicSearchDomainJsonAction extends DynamicSearchDomainAction {
    static id = "dynamicSearchDomainJson";
    getValue(args) {
        const searchDomainInfoValue = super.getValue(args);
        return searchDomainInfoValue && JSON.stringify(searchDomainInfoValue);
    }
    apply(args) {
        super.apply({ ...args, value: JSON.parse(args.value) });
    }
}

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);

class SharedSnippetPlugin extends Plugin {
    static id = "sharedSnippet";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        clean_for_save_processors: (root) => {
            for (const el of selectElements(root, "[data-oe-shared-snippet]")) {
                // This mirrors the handling of `t-shared-snippet` during qweb
                // rendering server side. The information stored in the
                // directive were stored in `data-oe-shared-snippet` for the
                // browser side to use. This code re-creates the directive
                // (and remove the content)
                el.replaceChildren();
                const key = el.getAttribute("data-oe-shared-snippet");
                el.removeAttribute("data-oe-shared-snippet");
                el.setAttribute("t-shared-snippet", key);
            }
            return root;
        },
    };
}

registry.category("website-plugins").add(SharedSnippetPlugin.id, SharedSnippetPlugin);
