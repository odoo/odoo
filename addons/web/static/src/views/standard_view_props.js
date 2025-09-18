// @ts-check

/** @module @web/views/standard_view_props - Shared OWL props validation shape for all standard view controllers */

/**
 * OWL props validation shape shared by all standard view controllers.
 *
 * Each view (list, kanban, form, etc.) uses these as the base `static props`
 * so the framework validates the same core set of props everywhere.
 */
export const standardViewProps = {
    info: {
        type: Object,
    },
    resModel: String,
    arch: { type: Element },
    className: { type: String, optional: true },
    context: { type: Object },
    createRecord: { type: Function, optional: true },
    display: { type: Object, optional: true },
    domain: { type: Array },
    fields: { type: Object },
    globalState: { type: Object, optional: true },
    groupBy: { type: Array, element: String },
    limit: { type: Number, optional: true },
    noBreadcrumbs: { type: Boolean, optional: true },
    orderBy: { type: Array, element: Object },
    relatedModels: { type: Object, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resIds: { type: Array, optional: true },
    searchMenuTypes: { type: Array, element: String },
    selectRecord: { type: Function, optional: true },
    state: { type: Object, optional: true },
    useSampleModel: { type: Boolean },
    updateActionState: { type: Function, optional: true },
};
