import { test } from "@odoo/hoot";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { setupPoSEnvForSelfOrder } from "../../utils";

definePosModels();

test.tags("desktop");
test("computeFloorSize", async () => {
    const store = await setupPoSEnvForSelfOrder();
    const floor = store.models["restaurant.floor"].get(2);
    store.currentFloor = floor;
    store.floorPlanStyle = "default";
    const screen = await mountWithCleanup(FloorScreen, {});
    screen.floorScrollBox = {
        el: {
            clientHeight: 500,
            offsetWidth: 700,
            scrollTop: 0,
            scrollLeft: 0,
        },
    };
    const table = store.models["restaurant.table"].getFirst();
    const order1 = await getFilledOrder(store, { self_ordering_table_id: table });
    await waitFor(`.tableId-${table.id}.occupied`);
    order1.state = "cancel";
    await waitForNone(`.tableId-${table.id}.occupied`);

    const order2 = await getFilledOrder(store, { table_id: table });
    await waitFor(`.tableId-${table.id}.occupied`);
    order2.state = "cancel";
    await waitForNone(`.tableId-${table.id}.occupied`);

    const order3 = await getFilledOrder(store, { self_ordering_table_id: table });
    const order4 = await getFilledOrder(store, { self_ordering_table_id: table });
    await waitFor(`.tableId-${table.id}.occupied`);
    order3.state = "cancel";
    await waitFor(`.tableId-${table.id}.occupied`);
    order4.state = "cancel";
    await waitForNone(`.tableId-${table.id}.occupied`);
});
