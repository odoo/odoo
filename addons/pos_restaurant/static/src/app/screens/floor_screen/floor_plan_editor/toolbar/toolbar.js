import { Component } from "@odoo/owl";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";
import { AddTablePopup } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/add_table_popup/add_table_popup";
import { AddDecorPopup } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/add_decor_popup/add_decor_popup";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class FloorEditorToolBar extends Component {
    static template = "pos_restaurant.floor_editor.toolbar";
    static components = {
        Dropdown,
        DropdownItem,
    };

    static props = {
        actionHandler: Function,
    };

    setup() {
        this.floorStore = useFloorPlanStore();
        this.dialog = useService("dialog");
    }

    selectFloor(floorUuid) {
        this.floorStore.selectFloorByUuid(floorUuid);
    }

    get floorScreenActions() {
        return this.props.actionHandler();
    }

    addTable() {
        this.dialog.add(AddTablePopup, {
            addTable: (type) => {
                this.floorScreenActions.createTable(type);
            },
        });
    }
    addDecor() {
        this.dialog.add(AddDecorPopup, {
            addDecor: (type, data) => {
                this.floorScreenActions.createShape(type, data);
            },
        });
    }

    addFloor() {
        this.floorScreenActions.addFloor();
    }
    editFloor() {
        this.floorScreenActions.editFloor();
    }
}
