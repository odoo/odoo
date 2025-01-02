import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_models";
import { ProjectMilestone } from "./project_task_model"

describe.current.tags("desktop");
defineProjectModels();

beforeEach(() => {
    ProjectMilestone._records = [
        { id: 1, product_uom_qty: -1, quantity_percentage: -25 },
        { id: 2, product_uom_qty: 5, quantity_percentage: 125 },
        { id: 3, product_uom_qty: 2, quantity_percentage: 0.02 },
    ];
});

const mountViewParams = {
    resModel: "project.milestone",
    type: "form",
    arch: `
        <form>
            <field name="product_uom_qty" decoration-danger="quantity_percentage &lt; 0 or 1 &lt; quantity_percentage"/>
            <field name="quantity_percentage" decoration-danger="quantity_percentage &lt; 0 or 1 &lt; quantity_percentage"/>
        </form>
    `,
};

/**
 * Helper function to mount the view and test if an element has the `text-danger` class.
 * @param {number} resId.
 * @param {boolean} shouldHaveClass.
 */
async function _testElementClass(resId, shouldHaveClass) {
    mountViewParams.resId = resId;
    await mountView(mountViewParams);

    const quantityElement = queryFirst('#quantity_percentage_0').parentElement;
    const productUomQtyElement = queryFirst('#product_uom_qty_0').parentElement;

    if (shouldHaveClass) {
        expect(quantityElement).toHaveClass("text-danger");
        expect(productUomQtyElement).toHaveClass("text-danger");
    } else {
        expect(quantityElement).not.toHaveClass("text-danger");
        expect(productUomQtyElement).not.toHaveClass("text-danger");
    }
}

test("Quantities have text-danger if quantity < 0", async () => {
    await _testElementClass(1, true);
});

test("Quantities have text-danger if quantity > 100", async () => {
    await _testElementClass(2, true);
});

test("Quantities don't have text-danger if quantity >= 0", async () => {
    await _testElementClass(3, false);
});
