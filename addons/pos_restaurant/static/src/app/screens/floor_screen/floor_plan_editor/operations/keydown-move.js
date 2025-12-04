import { constrainPositionToCanvas } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/operations/move";
import { debounce } from "@web/core/utils/timing";
import { calculateBoundsFromTransform } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";
import { setElementTransform } from "@pos_restaurant/app/services/floor_plan/utils/utils";

const ARROW_KEYS = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];

export class KeydownMoveHandler {
    constructor({ floorPlanStore, canvasRef, handles, actionMenu }) {
        this.floorPlanStore = floorPlanStore;
        this.canvasRef = canvasRef;
        this.handles = handles;
        this.actionMenu = actionMenu;
        this.debounceInProgress = false;
        // Bind debounced commit function to this instance
        this.commitKeyboardMove = debounce(this.commit.bind(this), 300);
    }

    isSupported(event) {
        return ARROW_KEYS.includes(event.key);
    }

    handle({ event, el, floorElement }) {
        if (!el || !floorElement) {
            return false;
        }

        let topToAdd = 0;
        let lefToAdd = 0;

        switch (event.key) {
            case "ArrowLeft":
                lefToAdd -= 1;
                break;
            case "ArrowRight":
                lefToAdd += 1;
                break;
            case "ArrowUp":
                topToAdd -= 1;
                break;
            case "ArrowDown":
                topToAdd += 1;
                break;
            default:
                return false;
        }

        if (this.debounceInProgress && this.floorElemData?.uuid !== floorElement.uuid) {
            return false;
        }

        // Initialize state for new element
        if (this.floorElemData?.uuid !== floorElement.uuid) {
            this.floorElemData = floorElement.getGeometry();
            this.floorElemData.uuid = floorElement.uuid;
        }

        if (!this.debounceInProgress) {
            this.handles.startAction("move");
            this.actionMenu.hide();
        }

        const tmpLeft = this.floorElemData.left + lefToAdd;
        const tmpTop = this.floorElemData.top + topToAdd;
        this.floorElemData.left = tmpLeft;
        this.floorElemData.top = tmpTop;

        const snappedBounds = calculateBoundsFromTransform(this.floorElemData);
        const position = constrainPositionToCanvas(
            tmpLeft,
            tmpTop,
            snappedBounds,
            this.canvasRef.el
        );

        this.setElementTransform(el, position.left, position.top);

        this.floorElemData.top = position.top;
        this.floorElemData.left = position.left;
        this.handles.follow({
            top: this.floorElemData.top,
            left: this.floorElemData.left,
        });

        this.debounceInProgress = true;
        // Only commit after user stops pressing keys
        this.commitKeyboardMove(floorElement.uuid, {
            left: this.floorElemData.left,
            top: this.floorElemData.top,
        });

        return true;
    }

    setElementTransform(el, left, top) {
        setElementTransform(el, left, top, this.floorElemData.rotation, this.floorElemData.scale);
    }

    commit(elementId, position) {
        this.floorPlanStore.updateElement(elementId, {
            left: position.left,
            top: position.top,
        });

        this.handles.endAction();
        this.actionMenu.show();
        this.debounceInProgress = false;
        this.floorElemData = null;
    }
}
