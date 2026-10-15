import { describe, expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

describe("restaurant floor_plan_service.js", () => {
    test("duplicateElement keeps the seats of the original table", async () => {
        const store = await setupPosEnv();
        const floorPlan = store.floorPlan;
        floorPlan.setEditMode(true);
        const table = floorPlan.selectedFloor.getTables().find((t) => t.id === 2);
        expect(table.seats).toBe(4);

        const duplicate = floorPlan.duplicateElement(table.uuid);
        expect(duplicate.id).toBe(null);
        expect(duplicate.seats).toBe(4);

        floorPlan.updateElement(table.uuid, { seats: 7 });
        expect(floorPlan.duplicateElement(table.uuid).seats).toBe(7);
    });
});
