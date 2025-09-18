// @ts-check

/** @module @web/views/widgets/standard_widget_props - Standard OWL prop definitions shared by all view widgets (record and readonly) */

/** Standard OWL prop definitions shared by all view widgets: the current record and readonly flag. */
export const standardWidgetProps = {
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
};
