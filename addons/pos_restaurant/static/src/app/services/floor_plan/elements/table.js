import { getColorInfo } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import { FloorElement } from "./floor_element";
import { calculateBoundsFromTransform } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";
import { markRaw } from "@odoo/owl";
import { normDeg } from "../utils/utils";
const TABLE_FREE_OPACITY = 0.3;

export class FloorTable extends FloorElement {
    constructor(data) {
        super(data);
        if (this.roundedCorner == null && (this.shape === "rect" || this.shape === "square")) {
            const minSide = Math.max(this.width || 0, this.height || 0);
            this.roundedCorner = Math.round(Math.max(6, minSide * 0.05));
        }
        this.unwatched = markRaw({});
    }

    clearBoundsCache() {
        super.clearBoundsCache();
        if (this.unwatched) {
            this.unwatched.linkedPosition = null;
        }
    }

    get linkedPosition() {
        const model = this.record;
        const parentRestaurantTable = model && model.parent_id;

        // No parent: compute once and cache
        if (!parentRestaurantTable) {
            this.unwatched.linkedPosition = this.computeLinkedPosition();
            return this.unwatched.linkedPosition;
        }

        // Compute a key like "parent-superParent-..." so that if any parent
        // in the chain changes, we invalidate the cached position
        const parentKey = this.computeParentKey(parentRestaurantTable);

        const parentSide =
            model && model.parent_side
                ? model.parent_side
                : this.computeParentSide(this.floor.getTableById(parentRestaurantTable.id));

        // Reuse cache if it's still valid
        const cached = this.unwatched.linkedPosition;
        if (cached && cached.parentKey === parentKey && cached.side === parentSide) {
            return cached;
        }

        // Recompute and cache
        const parentTable = this.floor.getTableById(parentRestaurantTable.id);
        const linkedPosition = this.computeLinkedPosition(parentTable, parentSide);
        linkedPosition.side = parentSide;
        linkedPosition.parentKey = parentKey;
        this.unwatched.linkedPosition = linkedPosition;
        return this.unwatched.linkedPosition;
    }

    hasParent() {
        return !!this.record?.parent_id;
    }

    get parent_id() {
        return this.record?.parent_id;
    }

    computeParentKey(parentTableModel) {
        if (!parentTableModel || !parentTableModel.id) {
            return "";
        }
        const id = String(parentTableModel.id);
        if (parentTableModel.parent_id) {
            return id + "-" + this.computeParentKey(parentTableModel.parent_id);
        }
        return id;
    }

    computeParentSide(parentTable) {
        if (!parentTable) {
            return "left";
        }
        const bounds = this.getBounds();
        const parentBounds = parentTable.getBounds();
        const dx = bounds.left - parentBounds.left;
        const dy = bounds.top - parentBounds.top;
        if (Math.abs(dx) > Math.abs(dy)) {
            return dx < 0 ? "right" : "left";
        }
        return dy > 0 ? "bottom" : "top";
    }

    computeLinkedPosition(parentTable, side) {
        if (!parentTable) {
            return { left: this.left, top: this.top };
        }

        const childBounds = this.getBounds();

        // Get parent's actual position (which might be linked to its own parent)
        const parentPos = parentTable.linkedPosition || {
            left: parentTable.left,
            top: parentTable.top,
        };

        // Calculate parent bounds using its actual position
        const parentBounds = parentTable.record?.parent_id
            ? parentTable.calculateBoundsAtPosition(parentPos.left, parentPos.top)
            : parentTable.getBounds();

        const childLeft = this.left;
        const childTop = this.top;

        const offsetX = childBounds.left - childLeft;
        const offsetY = childBounds.top - childTop;

        switch (side) {
            case "left":
                return {
                    left: parentBounds.left - childBounds.width - offsetX,
                    top: parentBounds.centerY - childBounds.height / 2 - offsetY,
                };
            case "bottom":
                return {
                    left: parentBounds.centerX - childBounds.width / 2 - offsetX,
                    top: parentBounds.bottom - offsetY,
                };
            case "top":
                return {
                    left: parentBounds.centerX - childBounds.width / 2 - offsetX,
                    top: parentBounds.top - childBounds.height - offsetY,
                };
            case "right":
            default:
                return {
                    left: parentBounds.right - offsetX,
                    top: parentBounds.centerY - childBounds.height / 2 - offsetY,
                };
        }
    }

    calculateBoundsAtPosition(left, top) {
        // Calculate bounds as if the element was at this position
        const tempGeo = { ...this.getGeometry(), left, top };
        return calculateBoundsFromTransform(tempGeo);
    }

    get isTable() {
        return true;
    }

    get table_number() {
        return this.tableNumber;
    }

    set table_number(number) {
        this.tableNumber = number;
    }

    getCssColorStyle() {
        if (!this.color) {
            return "";
        }
        const colorInfo = getColorInfo(this.color, this.isOccupied() ? 1 : TABLE_FREE_OPACITY);
        const textColor = colorInfo.isDark ? ";color:#fff" : "";
        return (
            "border-color:" +
            colorInfo.rgb +
            ";background-color:" +
            colorInfo.rgba +
            textColor +
            ";"
        );
    }

    isOccupied() {
        return this.record?.getOrders().length > 0;
    }

    getTableViewCssStyle() {
        if (this.linkedPosition) {
            return this.getCssStyle(this.linkedPosition.left, this.linkedPosition.top);
        }
        return this.getCssStyle();
    }

    getCssStyle(...args) {
        let style = super.getCssStyle(...args) + this.getCssColorStyle();
        if (this.roundedCorner && (this.shape === "rect" || this.shape === "square")) {
            style += `border-radius: ${this.roundedCorner}px;`;
        }
        return style;
    }

    getTableContentStyle() {
        const normalized = normDeg(this.rotation);
        const counterRotation = normalized <= 180 ? -normalized : 360 - normalized;
        if (!counterRotation) {
            return "";
        }
        // Counter-rotate and counter-scale to keep the number upright and at normal size
        return `transform: rotate(${counterRotation}deg);`;
    }

    get raw() {
        return {
            ...super.raw,
            id: this.id,
            seats: this.seats,
            table_number: this.table_number,
            color: this.color,
            roundedCorner: this.roundedCorner,
        };
    }
}
