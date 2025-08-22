import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("floor_screen.js", () => {
    test("getPosTable", async () => {
        const store = await setupPosEnv();
        store.currentFloor = store.models["restaurant.floor"].getFirst();
        const screen = await mountWithCleanup(FloorScreen, {});
        const renderedComp = await screen.env.services.renderer.toHtml(FloorScreen, {});
        const table = screen.getPosTable(renderedComp.querySelector(".tableId-2"));
        expect(table.id).toBe(store.currentFloor.table_ids[0].id);
    });

    test.tags("desktop");
    test("computeFloorSize", async () => {
        const store = await setupPosEnv();
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
        screen.state.floorMapOffset = { x: 0, y: 0 };
        screen.computeFloorSize();
        expect(screen.state.floorWidth).toBe("927px");
        expect(screen.state.floorHeight).toBe("500px");
    });

    test("resetTable", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(1);
        const order = store.addNewOrder({ table_id: table });
        store.setOrder(order);
        const screen = await mountWithCleanup(FloorScreen, {});
        await screen.resetTable();
        expect(store.getOrder()).toBe(undefined);
    });

    test("pinch gesture computes scale and sets it", async () => {
        await setupPosEnv();
        const screen = await mountWithCleanup(FloorScreen, {});
        screen.getScale = () => 1;
        let scaleValue = null;
        screen.setScale = (value) => {
            scaleValue = value;
        };
        const startEvent = {
            touches: [
                { pageX: 0, pageY: 0 },
                { pageX: 0, pageY: 100 },
            ],
            currentTarget: {
                style: {
                    setProperty: () => {},
                },
            },
        };
        screen._onPinchStart(startEvent);
        const hypotStart = Math.hypot(0 - 0, 0 - 100);
        expect(screen.scalehypot).toBe(hypotStart);
        expect(screen.initalScale).toBe(1);
        const moveEvent = {
            touches: [
                { pageX: 0, pageY: 0 },
                { pageX: 0, pageY: 200 },
            ],
        };
        screen._computePinchHypo(moveEvent, screen.movePinch.bind(screen));
        expect(scaleValue).toBeCloseTo(2);
    });

    test.tags("desktop");
    test("_createTableHelper", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].get(2);
        const screen = await mountWithCleanup(FloorScreen, {});
        screen.selectFloor(floor);
        const table = await screen._createTableHelper(null);
        expect(Boolean(table)).toBe(true);
        expect(table.floor_id.id).toBe(floor.id);
        expect(table.table_number).toBe(4);
        expect(table.height).toBe(table.width);
        expect(table.position_v >= 0).toBe(true);
        expect(table.position_h >= 10).toBe(true);
    });

    test("_getNewTableNumber", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].getFirst();
        const screen = await mountWithCleanup(FloorScreen, {});
        screen.selectFloor(floor);
        const newNumber = screen._getNewTableNumber();
        expect(newNumber).toBe(4);
    });

    test("duplicateTable", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].getFirst();
        const screen = await mountWithCleanup(FloorScreen, {});
        screen.selectFloor(floor);
        screen.state.selectedTableIds = [floor.table_ids[0].id];
        await screen.duplicateTable();
        expect(screen.state.selectedTableIds.length).toBe(1);
        const newTableId = screen.state.selectedTableIds[0];
        expect(newTableId).not.toBe(floor.table_ids[0].id);
    });

    test("_isTableVisible", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].getFirst();
        const screen = await mountWithCleanup(FloorScreen, {});
        screen.selectFloor(floor);
        screen.floorScrollBox = {
            el: {
                scrollTop: 0,
                scrollLeft: 0,
                clientHeight: 500,
                clientWidth: 500,
            },
        };
        const table = store.models["restaurant.table"].get(2);
        expect(screen._isTableVisible(table)).toBe(true);
    });
});
