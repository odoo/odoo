import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

export const applyDiscount = async (percent) => {
    const comp = await mountWithCleanup(ControlButtons, {});
    await comp.applyDiscount(percent);
};
