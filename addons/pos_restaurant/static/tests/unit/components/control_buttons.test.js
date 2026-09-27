import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

definePosModels();

test("showAddCourse", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comp = await mountWithCleanup(ControlButtons, { props: {} });

    expect(comp.showAddCourse).toBe(true);

    store.config.module_pos_restaurant = false;
    expect(comp.showAddCourse).toBe(false);
    store.config.module_pos_restaurant = true;
    order.is_refund = true;
    expect(comp.showAddCourse).toBe(false);
    order.is_refund = false;

    store.config.use_course_allocation = true;
    expect(comp.showAddCourse).toBe(false);
    store.config.use_course_allocation = false;

    const compWithRemainingButtons = await mountWithCleanup(ControlButtons, {
        props: { showRemainingButtons: true },
    });
    expect(compWithRemainingButtons.showAddCourse).toBe(false);
});
