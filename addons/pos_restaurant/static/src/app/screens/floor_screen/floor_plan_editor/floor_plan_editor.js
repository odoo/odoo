import { onMounted, onWillUnmount, useEffect, useRef, useExternalListener } from "@odoo/owl";
import { EditDecorProperties } from "./edit_decor/edit_decor";
import { EditTableProperties } from "./edit_table/edit_table";
import { EditFloorProperties } from "./edit_floor/edit_floor";

import { Handles } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/handles/handles";
import {
    MoveOperation,
    ResizeOperation,
    RotationOperation,
    LineResizeOperation,
} from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/operations";

import { KeydownMoveHandler } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/operations/keydown-move";
import { TextEditHandler } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/operations/text_edit";
import { useActionMenu } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/action_menu_hook";
import { isClickOnBorder } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/border_detection";
import { selectImage } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/image";
import { Snapping } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/snapping";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { FloorPlanBase } from "@pos_restaurant/app/screens/floor_screen/floor_plan_base";
import { useDebounced } from "@web/core/utils/timing";
import {
    loadImage,
    STATIC_IMG_BASE_URL,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { SIZES } from "@web/core/ui/ui_service";

const SETTING_MENU_SPACE = 320;
const TABLE_SPACING = 20;
const TABLE_START_X = 50;
const TABLE_START_Y = 50;
const IMG_SQUARE_SIZE = 150;
const IMG_SIZE = 220;

export class FloorPlanEditor extends FloorPlanBase {
    static template = "pos_restaurant.floor_plan_editor";
    static components = { Handles, EditTableProperties, EditDecorProperties, EditFloorProperties };
    static props = {
        initActionHandler: Function,
    };

    setup() {
        super.setup();
        this.snapGuidesRef = useRef("snapGuides");
        this.dialog = useService("dialog");
        this.ui = useService("ui");

        this.state.actionMenuPosition = null;
        this.state.canvasTranslateX = 0;
        this.selectedDOMElement = null;
        this.cancelCanvasClick = false;

        this.startResize = this.startResize.bind(this);
        this.startDrag = this.startDrag.bind(this);
        this.startRotate = this.startRotate.bind(this);
        this.handleMove = this.handleMove.bind(this);
        this.handleEnd = this.handleEnd.bind(this);
        this.handleWindowResize = this.handleWindowResize.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handlesActions = this.handlesActions.bind(this);
        this.handleBeforeUnload = this.handleBeforeUnload.bind(this);
        this.updateElement = this.updateElement.bind(this);
        this.moveLayer = this.moveLayer.bind(this);

        onMounted(() => {
            this.snapping = new Snapping(
                this.snapGuidesRef.el,
                this.floorPlanStore,
                this.containerRef.el
            );
            this.textEditHandler = new TextEditHandler({
                canvasRef: this.canvasRef,
                handles: this.handles,
                floorPlanStore: this.floorPlanStore,
            });

            if (this.props.initActionHandler) {
                this.props.initActionHandler({
                    createTable: (type) => this.addFloorElement(type, true),
                    createShape: (type, data) => this.addFloorElement(type, false, data),
                    addFloor: () => this.addFloor(),
                    editFloor: () => this.startEditFloor(),
                });
            }
        });

        onWillUnmount(() => {
            if (this.props.initActionHandler) {
                this.props.initActionHandler(null);
            }
        });

        useEffect(
            (selectedFloor) => {
                this.selectedDOMElement = null;
                this.updateActionMenu();
                this.ensureBoardFits(false);

                selectedFloor?.ensureBgImageLoaded().then((hasChanged) => {
                    if (hasChanged) {
                        this.ensureBoardFits(false);
                    }
                });
            },
            () => [this.floorPlanStore.selectedFloor]
        );

        useEffect(
            (selectedFloorEl) => {
                this.textEditHandler?.endEdit();
                this.selectedDOMElement = this.getDOMFloorElement(selectedFloorEl?.uuid);
                this.updateActionMenu();
                this.startEditText();
            },
            () => [this.floorPlanStore.getSelectedElement()]
        ); //This use effect need to be declared before the action menu setup, so that selectedDOMElement is set before action menu uses it

        useEffect(
            (isEditMode) => {
                this.updatedCanvasTranslateX();
                if (isEditMode) {
                    this.startEditText();
                }
            },
            () => [this.floorPlanStore.elementEditMode]
        );

        this.actionMenu = useActionMenu(
            "actionMenu",
            this.containerRef,
            () => ({ domElement: this.selectedDOMElement, floorElement: this.selectedElement }),
            (direction) => {
                this.state.actionMenuPosition = direction;
            }
        );
        this.state.actionMenuPosition = this.actionMenu.position;

        useExternalListener(document, "mousemove", this.handleMove);
        useExternalListener(document, "touchmove", this.handleMove, { passive: false });
        useExternalListener(document, "mouseup", this.handleEnd);
        useExternalListener(document, "touchend", this.handleEnd, { passive: false });
        useExternalListener(document, "keydown", this.handleKeyDown);
        useExternalListener(window, "resize", useDebounced(this.handleWindowResize, 100));
        useExternalListener(window, "beforeunload", this.handleBeforeUnload);

        onWillUnmount(() => {
            this.operation?.stop();
        });
    }

    startEditText() {
        if (this.floorPlanStore.elementEditMode && this.selectedElement?.isText) {
            this.textEditHandler.startEdit(this.selectedElement, this.selectedDOMElement);
        }
    }
    closeElementEdition() {
        this.floorPlanStore.selectElementByUuid(null);
    }

    handlesActions(handles) {
        this.handles = handles;
    }

    onCanvasClick(e) {
        if (this.operation || this.cancelCanvasClick) {
            return;
        }

        // Don't deselect if a text selection is in progress
        if (this.textSelectionInProgress) {
            return;
        }

        if (
            e.target === this.canvasRef.el ||
            e.target === this.snapGuidesRef.el ||
            e.target === this.containerRef.el
        ) {
            this.floorPlanStore.selectElementByUuid(null);
            this.endEditFloor();
        }
    }

    handleKeyDown(e) {
        // Prevent keyboard shortcuts when a dialog is open
        if (document.body.classList.contains("modal-open")) {
            return;
        }

        const ctrlOrCmd = e.ctrlKey || e.metaKey;
        const key = e.key.toLowerCase();

        if (ctrlOrCmd && key === "z" && !e.shiftKey) {
            e.preventDefault();
            this.floorPlanStore.undo();
            return;
        }

        if (ctrlOrCmd && (key === "y" || (key === "z" && e.shiftKey))) {
            e.preventDefault();
            this.floorPlanStore.redo();
            return;
        }

        if (e.target.matches("input, textarea") || e.target.isContentEditable) {
            return;
        }

        const selectedElement = this.floorPlanStore.getSelectedElement();
        if (selectedElement?.textEditing) {
            return;
        }

        if (ctrlOrCmd && e.key.toLowerCase() === "v") {
            if (this.copiedShapeId) {
                this.duplicateShape(this.copiedShapeId);
            }
            return;
        }

        if (selectedElement) {
            e.preventDefault();
            if (ctrlOrCmd && e.key.toLowerCase() === "c") {
                this.copiedShapeId = selectedElement.uuid;
                return;
            }

            if (e.key === "Delete" || e.key === "Backspace") {
                e.preventDefault();
                this.deleteSelected();
                return;
            }

            if (!this.keydownMoveHandler) {
                this.keydownMoveHandler = new KeydownMoveHandler({
                    floorPlanStore: this.floorPlanStore,
                    canvasRef: this.canvasRef,
                    handles: this.handles,
                    actionMenu: this.actionMenu,
                });
            }
            if (this.keydownMoveHandler.isSupported(e)) {
                this.keydownMoveHandler.handle(this.getActionContext(e));
                return;
            }
        }
    }

    handleWindowResize() {
        this.ensureBoardFits(false);
    }

    async addFloorElement(type, isTable = false, shapeData = {}) {
        let data;
        if (isTable) {
            data = this.floorPlanStore.addTable(type, {}, (table) =>
                this.findBestPlacement(table.width, table.height)
            );
        } else {
            if (type === "image") {
                shapeData = await this.createImageShapeData(shapeData);
            } else if (shapeData.group) {
                const defaultValues = this.floorPlanStore.getDefaultValuesForGroup(shapeData.group);
                shapeData = { ...shapeData, ...defaultValues }; // The default group values override the given values
            }

            data = this.floorPlanStore.addDecor(type, shapeData, (decor) =>
                this.getCenterPosition(decor.width, decor.height)
            );
        }
        this.ensureBoardFits();
        setTimeout(() => {
            //wait for DOM update
            this.scrollToElement(data.uuid);
        });
    }

    async createImageShapeData(data) {
        let { url, name } = data || {};
        if (!url && name) {
            url = `${STATIC_IMG_BASE_URL}/${name}`;
        }
        let imgData;
        if (url) {
            imgData = await loadImage(url);
        } else {
            imgData = await selectImage();
            name = imgData.name;
        }
        const aspectRatio = imgData.width / imgData.height;
        let width, height;

        if (aspectRatio === 1) {
            // Square image
            width = IMG_SQUARE_SIZE;
            height = IMG_SQUARE_SIZE;
        } else if (aspectRatio > 1) {
            // Landscape
            width = IMG_SIZE;
            height = Math.round(IMG_SIZE / aspectRatio);
        } else {
            // Portrait
            height = IMG_SIZE;
            width = Math.round(IMG_SIZE * aspectRatio);
        }

        return {
            shape: "image",
            url: imgData.url || url,
            objectUrl: imgData.objectUrl,
            name,
            width: width,
            height: height,
        };
    }

    getCenterPosition(width, height) {
        const containerRect = this.containerRef.el.getBoundingClientRect();
        const scrollLeft = this.containerRef.el.scrollLeft;
        const scrollTop = this.containerRef.el.scrollTop;

        // Calculate the center point of the viewport
        const viewportCenterX = scrollLeft + containerRect.width / 2;
        const viewportCenterY = scrollTop + containerRect.height / 2;

        return {
            left: viewportCenterX - width / 2,
            top: viewportCenterY - height / 2,
        };
    }

    findBestPlacement(width, height) {
        const tables = this.floorPlanStore.getFloorTables();
        if (tables.length === 0) {
            return { left: TABLE_START_X, top: TABLE_START_Y };
        }
        const canvasWidth = this.canvasRef.el.clientWidth;
        const maxRight = canvasWidth - TABLE_SPACING;
        let currentRow = 0;
        while (currentRow < 100) {
            const rowTop = TABLE_START_Y + currentRow * (height + TABLE_SPACING);
            let currentLeft = TABLE_START_X;
            while (currentLeft + width <= maxRight) {
                if (
                    this.isPositionAvailableForTable(
                        currentLeft,
                        rowTop,
                        width,
                        height,
                        TABLE_SPACING
                    )
                ) {
                    return { left: currentLeft, top: rowTop };
                }
                currentLeft += width + TABLE_SPACING;
            }
            currentRow++;
        }

        // Fallback to center if grid is somehow full
        return this.getCenterPosition(width, height);
    }

    isPositionAvailableForTable(left, top, width, height, spacing) {
        const tables = this.floorPlanStore.getFloorTables();

        for (const table of tables) {
            const bounds = table.getBounds();
            const noOverlap =
                left + width + spacing <= bounds.left ||
                left - spacing >= bounds.right ||
                top + height + spacing <= bounds.top ||
                top - spacing >= bounds.bottom;

            if (!noOverlap) {
                return false;
            }
        }

        return true;
    }

    updateActionMenu() {
        if (!this.selectedDOMElement) {
            this.actionMenu.hide();
            return;
        }
        this.actionMenu.show();
    }

    hideActionMenu() {
        this.actionMenu.hide();
    }

    findElementAtPoint(event) {
        let x = event.clientX;
        let y = event.clientY;

        if (event.touches) {
            if (!event.touches.length) {
                return;
            }

            x = event.touches[0].clientX;
            y = event.touches[0].clientY;
        }

        const elements = document.elementsFromPoint(x, y);

        // Filter to get only clickable shape elements
        const clickable = elements.filter((el) => {
            const style = window.getComputedStyle(el);
            return style.pointerEvents !== "none";
        });

        const shapeElements = clickable
            .map((el) => el.closest(".o_fp_shape"))
            .filter((el) => el !== null);

        // Check each shape element in order
        for (const shapeElement of shapeElements) {
            const uuid = this.getTableUuidFromDOMEl(shapeElement);
            if (this.canElementBeSelectedAtPoint(uuid, event)) {
                return uuid;
            }
        }

        return null;
    }

    canElementBeSelectedAtPoint(uuid, event) {
        const element = this.floorPlanStore.getElementByUuid(uuid);

        if (!element) {
            return false;
        }

        // If element has no transparent area, it's clickable
        if (!element.hasTransparentArea) {
            return true;
        }

        // If element has transparent area, check if click is on border
        const transparentInfo = element.getTransparentAreaInfo();
        const borderInfo = element.getTransparentAreaBorderInfo();
        const canvasRect = this.canvasRef.el.getBoundingClientRect();

        // Convert canvas coordinates to screen coordinates
        // transparentInfo.left/top are relative to canvas, canvasRect gives us canvas position in viewport
        const centerX = canvasRect.left + transparentInfo.left + transparentInfo.width / 2;
        const centerY = canvasRect.top + transparentInfo.top + transparentInfo.height / 2;

        return isClickOnBorder(event.clientX, event.clientY, {
            width: transparentInfo.width,
            height: transparentInfo.height,
            borderRadius: borderInfo.borderRadius || 0,
            borderThickness: transparentInfo.borderWidth || 0,
            x: centerX,
            y: centerY,
            rotation: element.rotation || 0,
            scale: element.scale || 1,
            hiddenBordersSet: element.hiddenBordersSet,
        });
    }

    startDrag(event, floorElemUuid) {
        if (!floorElemUuid || this.operation) {
            return;
        }

        // Ignore right-click
        if (!event.touches && event.button > 1) {
            return;
        }

        let startedOnTransparentArea = false;
        if (this.selectedElement?.uuid === floorElemUuid) {
            startedOnTransparentArea = !this.canElementBeSelectedAtPoint(floorElemUuid, event);
        } else {
            //No selection
            const detectElementId = this.findElementAtPoint(event);
            if (!detectElementId) {
                this.floorPlanStore.selectElementByUuid(null);
                return;
            }
            this.floorPlanStore.selectElementByUuid(detectElementId);
        }

        this.operation = new MoveOperation(this.getActionContext(event));
        this.operation.startedOnTransparentArea = startedOnTransparentArea;
    }

    onDblclick(event, floorElemUuid) {
        if (this.selectedElement?.uuid !== floorElemUuid) {
            floorElemUuid = this.findElementAtPoint(event);
            if (!floorElemUuid) {
                return;
            }

            this.floorPlanStore.selectElementByUuid(floorElemUuid);
        }
        this.onEdit(floorElemUuid, true);
    }

    startResize(position, event) {
        if (!this.selectedDOMElement || this.operation) {
            return;
        }
        this.hideActionMenu();

        // Check if this is a line element
        const selectedElement = this.floorPlanStore.getSelectedElement();
        if (
            selectedElement?.shape === "line" &&
            (position === "line-start" || position === "line-end")
        ) {
            this.operation = new LineResizeOperation(
                this.getActionContext(event, { position, event })
            );
        } else {
            this.operation = new ResizeOperation(this.getActionContext(event, { position }));
        }
    }

    startRotate(event) {
        if (!this.selectedDOMElement || this.operation) {
            return;
        }
        this.hideActionMenu();
        this.operation = new RotationOperation(this.getActionContext(event));
    }

    handleMove(event) {
        if (!this.operation) {
            return;
        }
        // required for touch devices
        event.preventDefault();
        event.stopPropagation();
        if (this.operation.isStarted()) {
            this.hideActionMenu();
        }

        this.operation.onMove(event);
    }

    handleEnd(event) {
        if (this.textSelectionInProgress) {
            setTimeout(() => {
                this.textSelectionInProgress = false;
            });
        }

        if (!this.operation) {
            return;
        }

        event.stopPropagation();
        event.preventDefault();
        const data = this.operation.stop();

        this.cancelCanvasClick = true;
        if (!data && this.operation.startedOnTransparentArea) {
            // The operation is not started and the user clicked on a transparent area
            // Find the first element at click point that should be selected
            const elementId = this.findElementAtPoint(event);
            if (elementId) {
                this.floorPlanStore.selectElementByUuid(elementId);
            } else {
                this.floorPlanStore.selectElementByUuid(null);
            }
        } else if (data) {
            this.floorPlanStore.updateElement(this.floorPlanStore.selectedElementUuid, data);
        }

        this.operation = null;
        this.ensureBoardFits();
        this.updateActionMenu();

        //little delay to avoid issues with click events
        setTimeout(() => {
            this.cancelCanvasClick = false;
        });
    }

    deleteSelected() {
        const floorElemId = this.floorPlanStore.selectedElementUuid;
        if (floorElemId) {
            this.floorPlanStore.removeElement(floorElemId);
        }
    }

    duplicateSelected() {
        this.duplicateShape(this.floorPlanStore.selectedElementUuid);
    }

    editSelected() {
        if (!this.selectedElement) {
            return;
        }

        this.floorPlanStore.toggleEditSelectedElement();
    }

    updatedCanvasTranslateX() {
        this.state.canvasTranslateX = 0;
        if (!this.floorPlanStore.elementEditMode || !this.selectedElement) {
            this.state.canvasTranslateX = 0;
            return;
        }

        if (this.ui.size > SIZES.XS) {
            const bounds = this.selectedElement.getBounds();
            const containerRect = this.containerRef.el.getBoundingClientRect();
            const scrollLeft = this.containerRef.el.scrollLeft;
            const elementRightInViewport = bounds.left + bounds.width - scrollLeft;
            let spaceLeft = 0;
            if (elementRightInViewport < containerRect.width) {
                spaceLeft = containerRect.width - elementRightInViewport - 20; //Some space
            }

            if (spaceLeft < SETTING_MENU_SPACE) {
                this.state.canvasTranslateX = -(SETTING_MENU_SPACE - spaceLeft);
                return;
            }
        }
        this.state.canvasTranslateX = 0;
    }

    onEdit(uuid, keepOpen = false) {
        if (!uuid) {
            return;
        }

        if (
            keepOpen &&
            this.floorPlanStore.elementEditMode &&
            this.floorPlanStore.selectedElementUuid === uuid
        ) {
            return; //Ignore if already in edit mode for the same element
        }

        this.floorPlanStore.selectElementByUuid(uuid);
        this.editSelected(keepOpen);
    }

    updateElement(uuid, values, options) {
        if (this.textEditHandler.isEditing(uuid)) {
            this.textEditHandler.handleChange(values, options);
            return;
        }

        this.floorPlanStore.updateElement(uuid, values, options);
    }

    moveLayer(uuid, position) {
        this.floorPlanStore.moveLayer(uuid, position);
    }

    onTextInput(event, element) {
        this.textEditHandler.handleInput();
    }

    onTextMouseDown(event) {
        this.textSelectionInProgress = true;
    }

    onTextPaste(event) {
        this.textEditHandler.handlePaste(event);
    }

    get selectedElement() {
        return this.floorPlanStore.getSelectedElement();
    }

    get selectedFloor() {
        return this.floorPlanStore.selectedFloor;
    }

    duplicateShape(uuid) {
        if (!uuid) {
            return;
        }
        this.floorPlanStore.duplicateElement(uuid);
    }

    handleBeforeUnload(ev) {
        if (this.floorPlanStore.canUndo()) {
            ev.preventDefault();
            return (ev.returnValue = _t("If you proceed, your changes will be lost"));
        }
    }

    addFloor() {
        this.dialog.add(TextInputPopup, {
            title: _t("New Floor"),
            placeholder: _t("Floor name"),
            getPayload: async (newName) => {
                this.floorPlanStore.addFloor(newName);
            },
        });
    }

    startEditFloor() {
        this.floorPlanStore.startEditFloor();
    }

    endEditFloor() {
        this.floorPlanStore.endEditFloor();
    }

    getScrollContainerStyles() {
        return `transform:translateX(${this.state.canvasTranslateX}px);${this.getContainerStyle()}`;
    }

    ensureBoardFits(keepCanvasSize = true) {
        if (!this.selectedFloor) {
            return;
        }

        const floorSize = this.selectedFloor.getSize();
        let maxW = floorSize.width;
        let maxH = floorSize.height;

        const scrollContainerEl = this.containerRef.el;

        if (scrollContainerEl) {
            const containerWidth = scrollContainerEl.clientWidth;
            const containerHeight = scrollContainerEl.clientHeight;

            if (maxW < containerWidth) {
                maxW = 0; // 100 % width
            }
            if (maxH < containerHeight) {
                maxH = 0; // 100 % height
            }
        }
        //keepCanvasSize will Avoid resizing down the anvas when the user expand it when moving element
        this.state.canvasWidth = Math.max(maxW, keepCanvasSize ? this.state.canvasWidth : 0);
        this.state.canvasHeight = Math.max(maxH, keepCanvasSize ? this.state.canvasHeight : 0);
    }

    getActionContext(event, args) {
        const result = {
            event,
            el: this.getDOMFloorElement(this.floorPlanStore.selectedElementUuid),
            floorElement: this.floorPlanStore.getSelectedElement(),
            floorPlanStore: this.floorPlanStore,
            canvasEl: this.canvasRef.el,
            scrollContainerEl: this.containerRef.el,
            snapping: this.snapping,
            handles: this.handles,
            actionMenu: this.actionMenu,
        };

        if (args) {
            Object.assign(result, args);
        }
        return result;
    }
}
