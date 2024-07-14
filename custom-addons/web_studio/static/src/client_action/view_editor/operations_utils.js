/** @odoo-module */

export function viewGroupByOperation(viewType, type, newValue, oldValue = undefined) {
    const operation_type = newValue ? "add" : "remove";
    const operation = {
        target: {
            view_type: viewType,
            field_names: [operation_type === "add" ? newValue : oldValue],
            operation_type,
            field_type: type,
        },
        type: "graph_pivot_groupbys_fields",
    };

    if (oldValue && newValue) {
        operation.target.operation_type = "replace";
        operation.target.old_field_names = oldValue;
    }

    return operation;
}
