/** @odoo-module */

import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";

patch(FloorScreen.prototype, {
    setup() {
        super.setup();
        const pos = usePos();
        this.pos = pos;
        const currentEmployee = pos?.cashier;
        this.allowedFloors = currentEmployee?.allowed_floor_ids || [];

        const allowedFloorIds = this.allowedFloors
            .map(floor => Number(floor?.id ?? floor?.data?.id))
            .filter(id => id);

        const currentFloorId = pos.currentFloor?.id ?? pos.currentFloor?.data?.id;

        let floorToUse = pos.currentFloor;

        if (!allowedFloorIds.includes(currentFloorId)) {
            floorToUse = this.allowedFloors[0];
            pos.currentFloor = floorToUse;
        }

        this.state = useState({
            selectedFloorId: floorToUse?.id ?? null,
            floorHeight: "100%",
            floorWidth: "100%",
            selectedTableIds: [],
            potentialLink: null,
        });


    },

    selectFloor(floor) {
        const floorId = floor?.id ?? floor?.data?.id ?? null;

        if (floorId === null) {
            console.warn("⚠️ Impossible de lire l'id du floor sélectionné");
            return;
        }

        const allowedFloorIds = this.allowedFloors
            .map(floor => Number(floor?.id ?? floor?.data?.id))
            .filter(id => id);

        if (!allowedFloorIds.includes(Number(floorId))) {
            console.warn(`⛔ Accès refusé à l'étage : ${floor?.name || "inconnu"}`);
            return;
        }

        this.pos.currentFloor = floor;
        this.state.selectedFloorId = Number(floorId);

        this.unselectTables();

    },
});
