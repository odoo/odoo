// @ts-check

/** @module @web/fields/relational/many2x_autocomplete - Autocomplete component for many2one/many2many fields with search, quick-create, and dialog creation */

import { Component } from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete/autocomplete";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { deepEqual } from "@web/core/utils/collections/objects";
import { KeepLast } from "@web/core/utils/concurrency";
import { highlightText, odoomark } from "@web/core/utils/dom/html";
import {
    useForwardRefToParent,
    useOwnedDialogs,
    useService,
} from "@web/core/utils/hooks";

/**
 * Opens a SelectCreateDialog for linking/creating records on a many2x field.
 *
 * @param {Object} params
 * @param {string} params.resModel
 * @param {Object} params.activeActions
 * @param {Function} params.onSelected
 * @param {Function} params.onCreateEdit
 * @param {Function} [params.onUnselect]
 * @returns {Function} selectCreate
 */
export function useSelectCreate({
    resModel,
    activeActions,
    onSelected,
    onCreateEdit,
    onUnselect,
}) {
    const addDialog = useOwnedDialogs();
    const SelectCreateDialog = registry.category("dialogs").get("select_create");

    function selectCreate({ domain, context, filters, title }) {
        addDialog(SelectCreateDialog, {
            title: title || _t("Select records"),
            noCreate: !activeActions.create,
            multiSelect: "link" in activeActions ? activeActions.link : false, // LPE Fixme
            resModel,
            context,
            domain,
            onSelected,
            onCreateEdit: () => onCreateEdit({ context }),
            dynamicFilters: filters,
            onUnselect,
        });
    }
    return selectCreate;
}

export class Many2XAutocomplete extends Component {
    static template = "web.Many2XAutocomplete";
    static components = { AutoComplete };
    static props = {
        activeActions: Object,
        autoSelect: { type: Boolean, optional: true },
        autocomplete_container: { type: Function, optional: true },
        autofocus: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
        createAction: { type: Function, optional: true },
        dropdown: { type: Boolean, optional: true },
        fieldString: String,
        getDomain: Function,
        id: { type: String, optional: true },
        isToMany: { type: Boolean, optional: true },
        nameCreateField: { type: String, optional: true },
        otherSources: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
        quickCreate: { type: [Function, { value: null }], optional: true },
        resModel: String,
        searchLimit: { type: Number, optional: true },
        searchMoreLabel: { type: String, optional: true },
        searchMoreLimit: { type: Number, optional: true },
        searchThreshold: { type: Number, optional: true },
        setInputFloats: { type: Function, optional: true },
        preventMemoization: { type: Boolean, optional: true },
        slots: { optional: true },
        specification: { type: Object, optional: true },
        update: Function,
        value: { type: String, optional: true },
    };
    static defaultProps = {
        context: {},
        dropdown: true,
        nameCreateField: "name",
        otherSources: [],
        quickCreate: null,
        searchLimit: 7,
        searchThreshold: 0,
        searchMoreLimit: 320,
        setInputFloats: () => {},
        specification: {},
        value: "",
    };
    setup() {
        this.orm = useService("orm");

        this.autoCompleteContainer = useForwardRefToParent("autocomplete_container");
        const { activeActions, resModel, update, isToMany, fieldString } = this.props;

        this.keepLast = new KeepLast();

        this.openMany2X =
            this.props.createAction ??
            useOpenMany2XRecord({
                resModel,
                activeActions,
                isToMany,
                onRecordSaved: (record) =>
                    update([{ ...record.data, id: record.resId }]),
                onRecordDiscarded: () => {
                    if (!isToMany) {
                        this.props.update(false);
                    }
                },
                fieldString,
                onClose: () => {
                    const autoCompleteInput =
                        this.autoCompleteContainer.el.querySelector("input");

                    // There are two cases:
                    // 1. Value is the same as the input: it means the autocomplete has re-rendered with the right value
                    //    This is in case we saved the record, triggering all the interface to update.
                    // 2. Value is different from the input: it means the input has a manually entered value and nothing
                    //    happened, that is, we discarded the changes
                    if (
                        this.props.value !==
                        /** @type {HTMLInputElement} */ (autoCompleteInput).value
                    ) {
                        /** @type {HTMLInputElement} */ (autoCompleteInput).value = "";
                    }
                    /** @type {HTMLInputElement} */ (autoCompleteInput).focus();
                },
                component: this.createDialog,
                size: this.createDialogSize,
            });

        this.selectCreate = useSelectCreate({
            resModel,
            activeActions,
            onSelected: (resId) => {
                const resIds = Array.isArray(resId) ? resId : [resId];
                const values = resIds.map((id) => ({ id }));
                return update(values);
            },
            onCreateEdit: ({ context }) => this.openMany2X({ context }),
            onUnselect: isToMany ? undefined : () => update(),
        });
    }

    /** @returns {Object} Props forwarded to the AutoComplete sub-component */
    get autoCompleteProps() {
        return {
            autocomplete: "off",
            autoSelect: this.props.autoSelect,
            autofocus: this.props.autofocus,
            dropdown: this.props.dropdown,
            id: this.props.id,
            onCancel: this.onCancel.bind(this),
            onChange: this.onChange.bind(this),
            onInput: this.onInput.bind(this),
            placeholder: this.props.placeholder,
            resetOnSelect: this.props.value === "",
            sources: this.sources,
            slots: this.props.slots,
            value: this.props.value,
        };
    }

    /** @returns {Array<Object>} Autocomplete data sources */
    get sources() {
        return [this.optionsSource, ...this.props.otherSources];
    }

    /** @returns {{ placeholder: string, options: Function, optionSlot: string }} */
    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionSlot: "option",
        };
    }

    /** @returns {Object} */
    get activeActions() {
        return this.props.activeActions || {};
    }

    /** @returns {typeof Component} Dialog component for record creation */
    get createDialog() {
        return registry.category("dialogs").get("form_view");
    }

    /** @returns {string} */
    get createDialogSize() {
        return "lg";
    }

    /**
     * @param {string} value - User-typed text for prefilling default fields
     * @returns {Object}
     */
    getCreationContext(value) {
        return makeContext([
            this.props.context,
            value && { [`default_${this.props.nameCreateField}`]: value },
        ]);
    }
    /** @param {{ inputValue: string }} params */
    onInput({ inputValue }) {
        if (!this.props.value || this.props.value !== inputValue) {
            this.props.setInputFloats(true);
        }
    }
    /** Resets floating state when autocomplete is cancelled */
    onCancel() {
        this.props.setInputFloats(false);
    }

    /** @returns {Object} web_name_search specification including display_name */
    get searchSpecification() {
        return {
            display_name: {},
            ...this.props.specification,
        };
    }

    /**
     * @param {string} name - Search text
     * @returns {Promise<Array<Object>>} Matching records from web_name_search
     */
    async search(name) {
        const domain = this.props.getDomain();
        const context = this.props.context;
        if (
            !this.props.preventMemoization &&
            this.lastEmptySearch &&
            deepEqual(this.lastEmptySearch.domain, domain) &&
            deepEqual(this.lastEmptySearch.context, context) &&
            (name.startsWith(this.lastEmptySearch.name) ||
                name.length < this.props.searchThreshold)
        ) {
            return [];
        }
        const records = await this.orm.call(
            this.props.resModel,
            "web_name_search",
            [],
            {
                name,
                operator: "ilike",
                domain,
                limit: this.props.searchLimit + 1,
                context,
                specification: this.searchSpecification,
            },
        );
        if (!records.length) {
            this.lastEmptySearch = {
                context,
                domain,
                name,
            };
        }
        return records;
    }

    /** @param {string} request - User input to prefill the creation form */
    slowCreate(request) {
        return this.openMany2X({
            context: this.getCreationContext(request),
            nextRecordsContext: this.props.context,
        });
    }

    /**
     * @param {Error} error
     * @param {string} request - Original user input to fall back to slow create
     */
    onQuickCreateError(error, request) {
        if (
            error instanceof RPCError &&
            error.exceptionName === "odoo.exceptions.ValidationError"
        ) {
            return this.slowCreate(request);
        } else {
            throw error;
        }
    }

    /**
     * @param {string} request - Current autocomplete input value
     * @returns {Promise<Array<Object>>} Dropdown suggestions
     */
    async loadOptionsSource(request) {
        await this.keepLast.add(Promise.resolve());
        return this.suggest(request, (promise) => this.keepLast.add(promise));
    }

    /**
     * @param {string} request - Search input text
     * @param {Function} lock - KeepLast lock function
     * @returns {Promise<Array<Object>>} Ordered list of suggestion objects
     */
    async suggest(request, lock) {
        const suggestions = [];
        /** @type {Record<string, any>[] | null} */
        let records = null;

        if (request.length < this.props.searchThreshold) {
            if (this.addStartTypingSuggestion({ request, records })) {
                suggestions.push(this.buildStartTypingSuggestion());
            }
        } else {
            records = await lock(this.search(request));
            if (records.length) {
                for (const record of records) {
                    suggestions.push(this.buildRecordSuggestion(request, record));
                }
            } else if (this.addNoRecordsSuggestion({ request, records })) {
                suggestions.push(this.buildNoRecordsSuggestion());
            } else if (this.addStartTypingSuggestion({ request, records })) {
                suggestions.push(this.buildStartTypingSuggestion());
            }
        }

        for (const action of this.actionSuggestions) {
            const enabled = action.enabled ?? (() => true);
            if (enabled({ request, records })) {
                suggestions.push(action.build(request));
            }
        }

        return suggestions;
    }

    /** @returns {Array<{ enabled?: Function, build: Function }>} Action suggestion descriptors */
    get actionSuggestions() {
        return [
            {
                // create
                enabled: this.addCreateSuggestion.bind(this),
                build: this.buildCreateSuggestion.bind(this),
            },
            {
                // create and edit
                enabled: this.addCreateEditSuggestion.bind(this),
                build: this.buildCreateEditSuggestion.bind(this),
            },
            {
                // search more
                enabled: this.addSearchMoreSuggestion.bind(this),
                build: this.buildSearchMoreSuggestion.bind(this),
            },
        ];
    }

    /**
     * @param {{ request: string }} params
     * @returns {boolean}
     */
    addCreateSuggestion({ request }) {
        return !!this.props.quickCreate && request.length > 0;
    }

    /**
     * @param {{ records: Array|null, request: string }} params
     * @returns {boolean}
     */
    addCreateEditSuggestion({ records, request }) {
        return (
            (this.activeActions.createEdit ?? this.activeActions.create) &&
            (request.length > 0 || records?.length === 0)
        );
    }

    /**
     * @param {{ request: string, records: Array|null }} params
     * @returns {boolean}
     */
    addNoRecordsSuggestion({ request, records }) {
        return !this.activeActions.createEdit && !this.props.quickCreate;
    }

    /**
     * @param {{ records: Array|null, request: string }} params
     * @returns {boolean}
     */
    addSearchMoreSuggestion({ records, request }) {
        return request.length < this.props.searchThreshold || records?.length > 0;
    }

    /**
     * @param {{ request: string, records: Array|null }} params
     * @returns {boolean}
     */
    addStartTypingSuggestion({ request, records }) {
        return records !== null
            ? request.length === 0 && !this.activeActions.createEdit
            : !this.props.value;
    }

    /**
     * @param {string} request
     * @returns {Object} Dropdown option for quick-creating a record
     */
    buildCreateSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
            data: { slotName: "createItem" },
            label: _t('Create "%s"', request),
            onSelect: async () => {
                try {
                    await this.props.quickCreate(request);
                } catch (e) {
                    this.onQuickCreateError(e, request);
                }
            },
        };
    }

    /**
     * @param {string} request
     * @returns {Object} Dropdown option for creating via a form dialog
     */
    buildCreateEditSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
            data: { slotName: "createEditItem" },
            label: request.length > 0 ? _t("Create and edit...") : _t("Create..."),
            onSelect: () => this.slowCreate(request),
        };
    }

    /** @returns {Object} Dropdown placeholder when no records match */
    buildNoRecordsSuggestion() {
        return {
            cssClass: "o_m2o_no_result",
            data: { slotName: "noRecordsItem" },
            label: _t("No records"),
        };
    }

    /**
     * @param {string} request - Search text for highlighting
     * @param {Object} record - Matching record from web_name_search
     * @returns {Object} Dropdown option representing an existing record
     */
    buildRecordSuggestion(request, record) {
        const label = record.__formatted_display_name || record.display_name;
        return {
            data: { record, slotName: "autoCompleteItem" },
            label: label
                ? highlightText(request, odoomark(label), "text-primary fw-bold")
                : _t("Unnamed"),
            onSelect: () => this.props.update([record]),
        };
    }

    /**
     * @param {string} request
     * @returns {Object} Dropdown option that opens the SelectCreateDialog
     */
    buildSearchMoreSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            data: { slotName: "searchMoreItem" },
            label: this.SearchMoreButtonLabel,
            onSelect: this.onSearchMore.bind(this, request),
        };
    }

    /** @returns {Object} Dropdown hint prompting the user to start typing */
    buildStartTypingSuggestion() {
        return {
            cssClass: "o_m2o_start_typing",
            data: { slotName: "startTypingItem" },
            label:
                this.props.searchThreshold > 1
                    ? _t("Start typing %s characters", this.props.searchThreshold)
                    : _t("Start typing..."),
        };
    }

    /** @returns {string} */
    get SearchMoreButtonLabel() {
        return this.props.searchMoreLabel ?? _t("Search more...");
    }

    /** Triggers a "Search More" action using the current barcode input value */
    async onBarcodeSearch() {
        const autoCompleteInput = this.autoCompleteContainer.el.querySelector("input");
        return this.onSearchMore(
            /** @type {HTMLInputElement} */ (autoCompleteInput).value,
        );
    }

    /** @param {string} request - Search text to pre-filter the SelectCreateDialog */
    async onSearchMore(request) {
        const { resModel, getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                domain: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
        });
    }

    /** @param {{ inputValue: string }} params - Clears the value when input is emptied */
    onChange({ inputValue }) {
        if (!inputValue.length) {
            this.props.update(false);
        }
    }
}

/**
 * Hook to open a many2x record in a FormViewDialog.
 *
 * @param {Object} params
 * @param {string} params.resModel
 * @param {Function} params.onRecordSaved
 * @param {Function} params.onRecordDiscarded
 * @param {string} params.fieldString
 * @param {Object} params.activeActions
 * @param {boolean} params.isToMany
 * @param {Function} [params.onClose]
 * @param {typeof Component} [params.component]
 * @param {string} [params.size]
 * @returns {Function} openDialog
 */
export function useOpenMany2XRecord({
    resModel,
    onRecordSaved,
    onRecordDiscarded,
    fieldString,
    activeActions,
    isToMany,
    onClose = (isNew) => {},
    component = null,
    size = "lg",
}) {
    component ??= registry.category("dialogs").get("form_view");
    const addDialog = useOwnedDialogs();
    const orm = useService("orm");

    return async function openDialog(
        { resId = false, forceModel = null, title, context, nextRecordsContext },
        immediate = false,
    ) {
        const model = forceModel || resModel;
        let viewId;
        if (resId !== false) {
            viewId = await orm.call(model, "get_formview_id", [[resId]], {
                context,
            });
        }

        /** @type {(value?: any) => void} */
        let resolve = () => {};
        if (!title) {
            title = resId ? _t("Open: %s", fieldString) : _t("Create %s", fieldString);
        }

        const { create: canCreate, write: canWrite } = activeActions;
        const readonly = !(resId ? canWrite : canCreate);

        addDialog(
            component,
            {
                preventCreate: !canCreate,
                preventEdit: !canWrite,
                title,
                context,
                nextRecordsContext,
                readonly,
                resId,
                resModel: model,
                viewId,
                onRecordSaved,
                onRecordDiscarded,
                isToMany,
                size,
            },
            {
                onClose: () => {
                    resolve();
                    const isNew = !resId;
                    onClose(isNew);
                },
            },
        );

        if (!immediate) {
            return /** @type {any} */ (
                new Promise((_resolve) => {
                    resolve = _resolve;
                })
            );
        }
    };
}
