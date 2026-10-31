import { expect, test } from "@odoo/hoot";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";

/**
 * A saved custom value can point at a ptav no attribute line has selected anymore (the
 * product's combination changed since it was written). `_updatePTAVCustomValue` used to assume
 * `.find()` always matches, crashing the whole dialog on `undefined.customValue = ...`.
 */
function makeDialog(product) {
    return Object.assign(Object.create(ProductConfiguratorDialog.prototype), {
        _findProduct: () => product,
    });
}

test("_updatePTAVCustomValue ignores a custom value whose ptav isn't selected on any line", () => {
    const product = {
        attribute_lines: [
            { id: 1, selected_attribute_value_ids: [10], customValue: undefined },
        ],
    };
    const dialog = makeDialog(product);

    // ptav 99 belongs to no line's selected_attribute_value_ids.
    expect(() => dialog._updatePTAVCustomValue(5, 99, "some text")).not.toThrow();
    expect(product.attribute_lines[0].customValue).toBe(undefined);
});

test("_updatePTAVCustomValue still sets the value on the matching line", () => {
    const product = {
        attribute_lines: [
            { id: 1, selected_attribute_value_ids: [10], customValue: undefined },
        ],
    };
    const dialog = makeDialog(product);

    dialog._updatePTAVCustomValue(5, 10, "engraved text");
    expect(product.attribute_lines[0].customValue).toBe("engraved text");
});
