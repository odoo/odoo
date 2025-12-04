import { Component } from "@odoo/owl";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

export class FloorPlanEditorNavBar extends Component {
    static template = "pos_restaurant.floor_editor.navbar";

    static props = {};
    setup() {
        this.floorPlanStore = useFloorPlanStore();
    }

    async onSave() {
        await this.floorPlanStore.save();
    }

    async onDiscardChanges() {
        await this.floorPlanStore.discardChanges();
    }
}
