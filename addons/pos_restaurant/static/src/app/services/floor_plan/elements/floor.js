import { FloorTable } from "./table";
import { Decor } from "./decor";
import {
    getFloorTextureCss,
    isFloorTextureId,
} from "@pos_restaurant/app/services/floor_plan/utils/floor_texture";
import { getColorRGBA } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import { pick } from "@web/core/utils/objects";
import { removeNullishAndDefault, loadImage, applyDefaults } from "../utils/utils";

export const DEFAULT_FLOOR_COLOR_KEY = "white";
export const DEFAULT_FLOOR_COLOR_OPACITY = 0.3;

const defaults = {
    bgColor: DEFAULT_FLOOR_COLOR_KEY,
    bgColorOpacity: DEFAULT_FLOOR_COLOR_OPACITY,
};

export class Floor {
    constructor(data) {
        data = applyDefaults(data, defaults);
        Object.assign(this, data);
        this.elementsMap = new Map();
        this.tables = [];
        this.decorations = [];
        this.cachedSize = null;
        this.cachedSortedTables = null;
    }

    addTable(table) {
        this.tables.push(table);
        this.addElement(table);
        this.cachedSortedTables = null;
        return table;
    }

    addDecor(decor) {
        this.decorations.push(decor);
        this.addElement(decor);
        return decor;
    }

    get bgImage() {
        return this._bgImage;
    }

    set bgImage(value) {
        this._bgImage = value;
        if (this._bgImage?.id && !this._bgImage.url) {
            this._bgImage.url = "/web/image/" + this._bgImage?.id;
        }

        this.clearSizeCache();
    }

    async ensureBgImageLoaded() {
        // Some legacy background image may not have width/height info saved
        if (this._bgImage?.url && (!this._bgImage.width || !this._bgImage.height)) {
            const img = await loadImage(this.bgImage.url);
            if (img) {
                this._bgImage.width = img.width;
                this._bgImage.height = img.height;
                this.clearSizeCache();
                return true;
            }
        }
        return false; // No update
    }

    addElement(el) {
        el.setFloor(this);
        this.elementsMap.set(el.uuid, el);
        this.clearSizeCache();
    }

    getElementByUuid(uuid) {
        return this.elementsMap.get(uuid);
    }

    removeElement(uuid) {
        const element = this.elementsMap.get(uuid);
        if (!element) {
            return null;
        }
        this.elementsMap.delete(uuid);
        if (element instanceof FloorTable) {
            const index = this.tables.indexOf(element);
            if (index > -1) {
                this.tables.splice(index, 1);
            }
            this.cachedSortedTables = null; // Invalidate cache
        } else if (element instanceof Decor) {
            const index = this.decorations.indexOf(element);
            if (index > -1) {
                this.decorations.splice(index, 1);
            }
        }
        element.setFloor(null);
        this.clearSizeCache();
        return element;
    }

    getTables() {
        return this.tables;
    }

    getTableById(id) {
        return this.tables.find((t) => t.id === id);
    }

    getTablesSortedByNumber() {
        if (!this.cachedSortedTables) {
            this.cachedSortedTables = [...this.tables].sort(
                (a, b) => a.tableNumber - b.tableNumber
            );
        }
        return this.cachedSortedTables;
    }

    getDecorElements() {
        return this.decorations;
    }

    getAllElements() {
        return [...this.tables, ...this.decorations];
    }

    clearDecor() {
        this.decorations.forEach((decorData) => {
            decorData.setFloor(null);
            this.elementsMap.delete(decorData.uuid);
        });
        this.decorations = [];
        this.clearSizeCache();
    }

    getDecorPosition(uuid) {
        const element = this.elementsMap.get(uuid);
        if (!element || !(element instanceof Decor)) {
            return null;
        }

        const index = this.decorations.indexOf(element);
        return index === -1 ? null : index;
    }

    setDecorPosition(uuid, targetIndex) {
        const element = this.elementsMap.get(uuid);
        if (!element || !(element instanceof Decor)) {
            return false;
        }

        const currentIndex = this.decorations.indexOf(element);
        if (currentIndex === -1 || currentIndex === targetIndex) {
            return false;
        }
        this.decorations.splice(currentIndex, 1);
        this.decorations.splice(targetIndex, 0, element);
        return true;
    }

    moveDecor(uuid, direction) {
        const element = this.elementsMap.get(uuid);
        if (!element || !(element instanceof Decor)) {
            return false;
        }

        const index = this.decorations.indexOf(element);
        if (index === -1) {
            return false;
        }

        switch (direction.toLowerCase()) {
            case "up":
                if (index === this.decorations.length - 1) {
                    return false;
                }
                [this.decorations[index], this.decorations[index + 1]] = [
                    this.decorations[index + 1],
                    this.decorations[index],
                ];
                break;

            case "top":
                if (index === this.decorations.length - 1) {
                    return false;
                }
                {
                    const elementToTop = this.decorations.splice(index, 1)[0];
                    this.decorations.push(elementToTop);
                }
                break;

            case "down":
                if (index === 0) {
                    return false;
                }
                [this.decorations[index], this.decorations[index - 1]] = [
                    this.decorations[index - 1],
                    this.decorations[index],
                ];
                break;

            case "bottom":
                if (index === 0) {
                    return false;
                }
                {
                    const elementToBottom = this.decorations.splice(index, 1)[0];
                    this.decorations.unshift(elementToBottom);
                }
                break;

            default:
                return false;
        }

        return true;
    }

    getTableCount() {
        return this.tables.length;
    }

    getDecorCount() {
        return this.decorations.length;
    }

    getTotalCount() {
        return this.tables.length + this.decorations.length;
    }

    hasBgOpacity() {
        return this.bgColorOpacity != null && this.isColorHasBgOpacity(this.bgColor);
    }

    isColorHasBgOpacity(color) {
        return color !== "white" && !isFloorTextureId(color);
    }

    getMaxTableNumber() {
        let maxTableNumber = 0;

        for (const table of this.tables) {
            if (table.tableNumber > maxTableNumber) {
                maxTableNumber = table.tableNumber;
            }
        }
        return maxTableNumber;
    }

    getContainerStyle() {
        const bgColor = this.bgColor;
        let cssStyle = "";
        if (bgColor) {
            if (isFloorTextureId(bgColor)) {
                cssStyle = getFloorTextureCss(bgColor);
            } else {
                cssStyle = `background-color:${getColorRGBA(
                    bgColor || "white",
                    this.hasBgOpacity() ? this.bgColorOpacity : 1
                )};`;
            }
        }
        return cssStyle;
    }

    getBackgroundStyle() {
        const bgImage = this.bgImage;
        let cssStyle = "";
        if (bgImage) {
            cssStyle += `;background-image:url('${bgImage.url}');background-repeat: no-repeat;`;
        }
        return cssStyle;
    }

    clearSizeCache() {
        this.cachedSize = null;
    }

    getSize() {
        if (this.cachedSize) {
            return this.cachedSize;
        }

        let maxW = 0;
        let maxH = 0;
        let minLeft = Infinity;
        let minTop = Infinity;
        let firstVisibleTable = null;

        for (const floorElem of this.getAllElements()) {
            const bounds = floorElem.getBounds();
            const elementRight = Math.ceil(bounds.left + bounds.width);
            const elementBottom = Math.ceil(bounds.top + bounds.height);
            maxW = Math.max(maxW, elementRight);
            maxH = Math.max(maxH, elementBottom);

            // Track the topmost-leftmost element (first visible)
            if (
                floorElem.isTable &&
                (bounds.left < minLeft || (bounds.left === minLeft && bounds.top < minTop))
            ) {
                minLeft = bounds.left;
                minTop = bounds.top;
                firstVisibleTable = floorElem;
            }
        }

        const bgImage = this.bgImage;
        if (bgImage) {
            maxW = Math.max(maxW, bgImage.width || 0);
            maxH = Math.max(maxH, bgImage.height || 0);
        }

        this.cachedSize = {
            width: maxW,
            height: maxH,
            firstVisibleTable,
            minLeft: minLeft === Infinity ? 0 : minLeft,
            minTop: minTop === Infinity ? 0 : minTop,
        };
        return this.cachedSize;
    }

    getFirstVisibleTable() {
        const size = this.getSize();
        return size.firstVisibleTable;
    }

    get table_ids() {
        return this.record?.table_ids || [];
    }

    get raw() {
        const { bgImage } = this;
        return removeNullishAndDefault(
            {
                id: this.id,
                uuid: this.uuid,
                bgColor: this.bgColor,
                bgColorOpacity: this.bgColorOpacity,
                bgImage: bgImage && pick(bgImage, "width", "height", "url", "name", "id"),
                name: this.name,
                tables: this.tables.map((table) => table.raw),
                decorations: this.decorations.map((decor) => decor.raw),
            },
            defaults
        );
    }
}
