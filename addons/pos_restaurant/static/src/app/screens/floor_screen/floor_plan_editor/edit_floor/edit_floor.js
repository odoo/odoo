import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";
import { Handles } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/handles/handles";
import { _t } from "@web/core/l10n/translation";
import { getColorRGBA, getColors } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import { selectImage } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/image";
import {
    opacityToTransparency,
    transparencyToOpacity,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import {
    FLOOR_TEXTURE,
    isFloorTextureId,
} from "@pos_restaurant/app/services/floor_plan/utils/floor_texture";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

export class EditFloorProperties extends Component {
    static template = "pos_restaurant.floor_editor.edit_floor_properties";
    static components = { Handles };
    static props = {
        floor: { optional: true },
        canvasRef: { optional: true },
        onSizeUpdated: { type: Function },
    };

    setup() {
        this.dialog = useService("dialog");
        this.floorPlanStore = useFloorPlanStore();
        this.state = useState({ resolution: "" });
        useExternalListener(window, "resize", this.handleWindowResize);

        onMounted(() => {
            this.handleWindowResize();
        });
    }

    get floor() {
        return this.props.floor;
    }

    handleWindowResize() {
        const canvasEl = this.props.canvasRef.el;
        if (canvasEl) {
            this.state.resolution = canvasEl.offsetWidth + " x " + canvasEl.offsetHeight + " px";
        } else {
            this.state.resolution = "";
        }
    }

    updateFloorName(event) {
        const target = event.target;
        const newName = target.value.trim();
        if (!newName.length) {
            return;
        }
        this.updateFloor({ name: newName });
    }

    getBackgroundColors() {
        return getColors();
    }

    getBackgroundPatterns() {
        return FLOOR_TEXTURE;
    }

    selectBackgroundColor(color) {
        this.updateFloor({ bgColor: color });
    }

    updateFloor(values) {
        this.floorPlanStore.updateFloor(this.floor.uuid, values);
    }

    canBeDelete() {
        return this.floorPlanStore.floors.length > 1;
    }

    deleteFloor() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this floor?"),
            confirmLabel: _t("Delete"),
            cancel: () => {},
            confirm: () => {
                this.floorPlanStore.removeFloor(this.floor.uuid);
            },
        });
    }

    updateBgColorOpacity(event) {
        const opacity = transparencyToOpacity(Number(event.target.value));
        this.floorPlanStore.updateFloor(
            this.floor.uuid,
            { bgColorOpacity: opacity },
            { batched: true }
        );
    }

    commitBgColorOpacity(event) {
        const opacity = transparencyToOpacity(Number(event.target.value));
        this.floorPlanStore.updateFloor(this.floor.uuid, { bgColorOpacity: opacity });
    }

    getBgColorTransparency() {
        return opacityToTransparency(this.floor.bgColorOpacity);
    }

    getColorValue(color) {
        return getColorRGBA(
            color.key,
            this.floor.isColorHasBgOpacity(color.key) ? this.floor.bgColorOpacity : 1
        );
    }

    async addBackgroundImage() {
        const imgData = await selectImage();
        if (!imgData) {
            return;
        }

        this.updateFloor({
            bgColor: isFloorTextureId(this.floor.bgColor) ? "white" : this.floor.bgColor,
            bgImage: {
                width: imgData.width,
                height: imgData.height,
                url: imgData.objectUrl,
                name: imgData.name,
                objectUrl: imgData.objectUrl,
            },
        });
        this.props.onSizeUpdated();
    }

    async removeBackgroundImage() {
        this.updateFloor({
            bgImage: null,
        });
        this.props.onSizeUpdated();
    }

    getResolutionMessage() {
        return _t(
            "For the current display, an image a resolution of %s is recommended.",
            this.state.resolution
        );
    }
}
