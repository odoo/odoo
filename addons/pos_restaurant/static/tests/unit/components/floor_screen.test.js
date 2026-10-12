import { test, expect, animationFrame } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { Component, proxy, xml } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { FloorPlan } from "@pos_restaurant/app/screens/floor_screen/floor_plan/floor_plan";

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

test("floor plan unmounted before the background image is loaded", async () => {
    await setupPosEnv();
    const floor = getService("pos_floor_plan").selectedFloor;
    const bgImageLoaded = Promise.withResolvers();
    patch(floor, { ensureBgImageLoaded: () => bgImageLoaded.promise });

    class Parent extends Component {
        static components = { FloorPlan };
        static template = xml`<FloorPlan t-if="this.state.show"/>`;

        setup() {
            this.state = proxy({ show: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await waitFor(".o_fp_canvas");

    parent.state.show = false;
    await animationFrame();
    expect(".o_fp_canvas").toHaveCount(0);

    bgImageLoaded.resolve(true);
    await animationFrame();
    expect(".o_fp_canvas").toHaveCount(0);
});
