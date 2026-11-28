import { test, expect, animationFrame } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { Component, proxy, xml } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { FloorPlan } from "@pos_restaurant/app/screens/floor_screen/floor_plan/floor_plan";
import { FloorPlanEditor } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/floor_plan_editor";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

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

async function mountFloorPlan(width) {
    const store = await setupPosEnv();
    store.floorPlan.storedFloorPlanStyle = "default";
    class Parent extends Component {
        static components = { FloorPlan };
        static template = xml`<div style="width:${width}px;height:400px"><FloorPlan/></div>`;
    }
    await mountWithCleanup(Parent);
    await waitFor(".o_fp_table");
    await animationFrame();
    const container = queryOne(".o_fp_canvas");
    const { left, top } = container.getBoundingClientRect();
    const first = queryOne(`.o_fp_table[data-table_id="2"]`).getBoundingClientRect();
    const last = queryOne(`.o_fp_table[data-table_id="4"]`).getBoundingClientRect();
    return {
        container,
        marginLeft: Math.round(first.left - left),
        marginRight: Math.round(left + container.clientWidth - last.right),
        marginTop: Math.round(first.top - top),
        marginBottom: Math.round(top + container.clientHeight - last.bottom),
    };
}

test("floor plan centers its tables when they fit in the screen", async () => {
    const { container, marginLeft, marginRight, marginTop, marginBottom } = await mountFloorPlan(
        800
    );
    expect(marginLeft).toBe(150);
    expect(marginRight).toBe(150);
    expect(Math.abs(marginTop - marginBottom)).toBeLessThan(2);
    expect(container.scrollWidth).toBe(container.clientWidth);
    expect(container.scrollHeight).toBe(container.clientHeight);
});

test("floor plan starts at its first table when they do not fit in the screen", async () => {
    const { container, marginLeft } = await mountFloorPlan(300);
    expect(container.scrollLeft).toBe(0);
    expect(marginLeft).toBe(20);
    expect(container.scrollWidth).toBe(540);
});

test("floor plan editor shows the tables where the floor plan did", async () => {
    const store = await setupPosEnv();
    store.floorPlan.storedFloorPlanStyle = "default";
    class Parent extends Component {
        static components = { FloorPlan, FloorPlanEditor };
        static template = xml`
            <div style="width:800px;height:400px">
                <FloorPlanEditor t-if="this.floorPlanStore.editMode" initActionHandler="() => {}"/>
                <FloorPlan t-else=""/>
            </div>`;

        setup() {
            this.floorPlanStore = useFloorPlanStore();
        }
    }
    await mountWithCleanup(Parent);
    const table = store.floorPlan.selectedFloor.getTables().find((t) => t.id === 2);
    const getTableRect = () => queryOne(`#fpe-${table.uuid}`).getBoundingClientRect();
    await waitFor(`#fpe-${table.uuid}`);
    await animationFrame();
    const planRect = getTableRect();

    store.floorPlan.setEditMode(true);
    await waitFor(".o_fp_snap_guides");
    await animationFrame();
    const editorRect = getTableRect();
    expect(Math.round(editorRect.left)).toBe(Math.round(planRect.left));
    expect(Math.round(editorRect.top)).toBe(Math.round(planRect.top));
});
