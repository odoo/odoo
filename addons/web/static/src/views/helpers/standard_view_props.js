/** @odoo-module **/

// TODO: add this in info props description

// breadcrumbs: { type: Array, optional: 1 },
// __getLocalState__: { type: CallbackRecorder, optional: 1 },
// __getContext__: { type: CallbackRecorder, optional: 1 },
// display: { type: Object, optional: 1 },
// displayName: { type: String, optional: 1 },
// noContentHelp: { type: String, optional: 1 },
// searchViewId: { type: [Number, false], optional: 1 },
// viewId: { type: [Number, false], optional: 1 },
// views: { type: Array, element: Array, optional: 1 },
// viewSwitcherEntries: { type: Array, optional: 1 },

export const standardViewProps = {
    info: {
        type: Object,
    },
    resModel: String,
    arch: { type: String },
    comparison: { validate: () => true }, // fix problem with validation with type: [Object, null]
    // Issue OWL: https://github.com/odoo/owl/issues/910
    context: { type: Object },
    domain: { type: Array },
    fields: { type: Object, elements: Object },
    relatedModels: { type: Object, elements: Object, optional: 1 },
    groupBy: { type: Array, elements: String },
    limit: { type: Number, optional: 1 },
    orderBy: { type: Array, elements: String },
    useSampleModel: { type: Boolean },
    state: { type: Object, optional: 1 },
    globalState: { type: Object, optional: 1 },
    resId: { type: [Number, false], optional: 1 },
    resIds: { type: Array, optional: 1 },
    bannerRoute: { type: String, optional: 1 },
    className: { type: String, optional: 1 },
    searchMenuTypes: { type: Array, elements: String },
    selectRecord: { type: Function, optional: 1 },
    createRecord: { type: Function, optional: 1 },
    noBreadcrumbs: { type: Boolean, optional: 1 },
};
