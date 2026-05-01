import { test, expect } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";

const { DateTime } = luxon;

definePosModels();

test("timer badge shows duration on floor screen table", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(4);
    const order = store.addNewOrder({ table_id: table });
    order.create_date = DateTime.now().minus({ minutes: 15 });
    await mountWithCleanup(FloorScreen);
    await waitFor(`.o_fp_table[data-table_id="${table.id}"] .table-timer-badge`);
    expect(
        queryOne(`.o_fp_table[data-table_id="${table.id}"] .table-timer-badge`).textContent.trim()
    ).toBe("15'");
});
