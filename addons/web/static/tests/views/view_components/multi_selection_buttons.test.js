import { expect, test } from "@odoo/hoot";
import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";

test("preserves unloaded x2many records in multi-create values", () => {
    const loadedRecord = {
        resId: 1,
        data: { display_name: "Event Type 1" },
    };

    const values = MultiSelectionButtons.prototype.computeValues({
        data: {
            allowed_type_ids: {
                currentIds: [1, 2, 3],
                records: [loadedRecord],
                _cache: { 1: loadedRecord },
            },
        },
        fields: { allowed_type_ids: { type: "many2many" } },
    });

    expect(values.allowed_type_ids).toEqual([
        { id: 1, display_name: "Event Type 1" },
        { id: 2 },
        { id: 3 },
    ]);
});
