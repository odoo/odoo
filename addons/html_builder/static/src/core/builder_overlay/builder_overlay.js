import { renderToElement } from "@web/core/utils/render";
import {
    addBackgroundGrid,
    getGridProperties,
    getGridItemProperties,
    resizeGrid,
    setElementToMaxZindex,
} from "@html_builder/utils/grid_layout_utils";

// TODO move them elsewhere.
export const sizingY = {
    selector: "section, .row > div, .parallax, .s_hr, .carousel-item, .s_rating",
    exclude:
        "section:has(> .carousel), .s_image_gallery .carousel-item, .s_col_no_resize.row > div, .s_col_no_resize",
};
export const sizingX = {
    selector: ".row > div",
    exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
};
export const sizingGrid = {
    selector: ".row > div",
    exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
};

export class BuilderOverlay {
    constructor(
        overlayTarget,
        {
            iframe,
            overlayContainer,
            history,
            hasOverlayOptions,
            next,
            isMobileView,
            mobileBreakpoint,
            isRtl,
        }
    ) {
        this.history = history;
        this.next = next;
        this.hasOverlayOptions = hasOverlayOptions;
        this.iframe = iframe;
        this.overlayContainer = overlayContainer;
        this.overlayElement = renderToElement("html_builder.BuilderOverlay");
        this.overlayTarget = overlayTarget;
        this.hasSizingHandles = this.hasSizingHandles();
        this.handlesWrapperEl = this.overlayElement.querySelector(".o_handles");
        this.handleEls = this.overlayElement.querySelectorAll(".o_handle");
        // Avoid "querySelectoring" the handles every time.
        this.yHandles = this.handlesWrapperEl.querySelectorAll(
            `.n:not(.o_grid_handle), .s:not(.o_grid_handle)`
        );
        this.xHandles = this.handlesWrapperEl.querySelectorAll(
            `.e:not(.o_grid_handle), .w:not(.o_grid_handle)`
        );
        this.gridHandles = this.handlesWrapperEl.querySelectorAll(".o_grid_handle");
        this.isMobileView = isMobileView;
        this.mobileBreakpoint = mobileBreakpoint;
        this.isRtl = isRtl;

        this.initHandles();
        this.initSizing();
        this.refreshHandles();
    }

    hasSizingHandles() {
        if (!this.hasOverlayOptions) {
            return false;
        }
        return this.isResizableY() || this.isResizableX() || this.isResizableGrid();
    }

    // displayOverlayOptions(el) {
    //     // TODO when options will be more clear:
    //     // - moving
    //     // - timeline
    //     // (maybe other where `displayOverlayOptions: true`)
    // }

    isActive() {
        // TODO active still necessary ? (check when we have preview mode)
        return this.overlayElement.matches(".oe_active, .o_we_overlay_preview");
    }

    refreshPosition() {
        if (!this.isActive()) {
            return;
        }

        const openModalEl = this.overlayTarget.querySelector(".modal.show");
        const overlayTarget = openModalEl ? openModalEl : this.overlayTarget;
        // TODO transform
        const iframeRect = this.iframe.getBoundingClientRect();
        const overlayContainerRect = this.overlayContainer.getBoundingClientRect();
        const targetRect = overlayTarget.getBoundingClientRect();
        const isMobile = this.isMobileView(overlayTarget);
        const iframeScaleX = isMobile ? iframeRect.width / this.iframe.offsetWidth : 1;
        const iframeScaleY = isMobile ? iframeRect.height / this.iframe.offsetHeight : 1;

        Object.assign(this.overlayElement.style, {
            width: `${targetRect.width * iframeScaleX}px`,
            height: `${targetRect.height * iframeScaleY}px`,
            top: `${
                iframeRect.y - overlayContainerRect.y + window.scrollY + targetRect.y * iframeScaleY
            }px`,
            left: `${
                iframeRect.x - overlayContainerRect.x + window.scrollX + targetRect.x * iframeScaleX
            }px`,
        });
        this.handlesWrapperEl.style.height = `${targetRect.height * iframeScaleY}px`;
    }

    refreshHandles() {
        if (!this.hasSizingHandles || !this.isActive()) {
            return;
        }

        if (this.overlayTarget.parentNode?.classList.contains("row")) {
            const isMobile = this.isMobileView(this.overlayTarget);
            const isGridOn = this.overlayTarget.classList.contains("o_grid_item");
            const isGrid = !isMobile && isGridOn;
            // Hiding/showing the correct resize handles if we are in grid mode
            // or not.
            this.handleEls.forEach((handleEl) => {
                const isGridHandle = handleEl.classList.contains("o_grid_handle");
                handleEl.classList.toggle("d-none", isGrid ^ isGridHandle);
                // Disabling the vertical resize if we are in mobile view.
                const isVerticalSizing = handleEl.matches(".n, .s");
                handleEl.classList.toggle("readonly", isMobile && isVerticalSizing && isGridOn);
            });
        }

        this.updateHandleY();
    }

    toggleOverlay(show) {
        this.overlayElement.classList.toggle("oe_active", show);
        this.refreshPosition();
        this.refreshHandles();
    }

    toggleOverlayPreview(show) {
        this.overlayElement.classList.toggle("o_we_overlay_preview", show);
        this.refreshPosition();
        this.refreshHandles();
    }

    toggleOverlayVisibility(show) {
        if (!this.isActive()) {
            return;
        }
        this.overlayElement.classList.toggle("o_overlay_hidden", !show);
    }

    destroy() {
        if (!this.hasSizingHandles) {
            return;
        }

        this.handleEls.forEach((handleEl) =>
            handleEl.removeEventListener("pointerdown", this._onSizingStart)
        );
    }

    //--------------------------------------------------------------------------
    // Sizing
    //--------------------------------------------------------------------------

    isResizableY() {
        return (
            this.overlayTarget.matches(sizingY.selector) &&
            !this.overlayTarget.matches(sizingY.exclude)
        );
    }

    isResizableX() {
        return (
            this.overlayTarget.matches(sizingX.selector) &&
            !this.overlayTarget.matches(sizingX.exclude)
        );
    }

    isResizableGrid() {
        return (
            this.overlayTarget.matches(sizingGrid.selector) &&
            !this.overlayTarget.matches(sizingGrid.exclude)
        );
    }

    initHandles() {
        if (!this.hasSizingHandles) {
            return;
        }
        if (this.isResizableY()) {
            this.yHandles.forEach((handleEl) => handleEl.classList.remove("readonly"));
        }
        if (this.isResizableX()) {
            this.xHandles.forEach((handleEl) => handleEl.classList.remove("readonly"));
        }
        if (this.isResizableGrid()) {
            this.gridHandles.forEach((handleEl) => handleEl.classList.remove("readonly"));
        }
    }

    initSizing() {
        if (!this.hasSizingHandles) {
            return;
        }

        this._onSizingStart = this.onSizingStart.bind(this);
        this.handleEls.forEach((handleEl) =>
            handleEl.addEventListener("pointerdown", this._onSizingStart)
        );
    }

    replaceSizingClass(classRegex, newClass) {
        const newClassName = (this.overlayTarget.className || "").replace(classRegex, "");
        this.overlayTarget.className = newClassName;
        this.overlayTarget.classList.add(newClass);
    }

    getSizingYConfig() {
        const isTargetHR = this.overlayTarget.matches("hr");
        const nClass = isTargetHR ? "mt" : "pt";
        const nProperty = isTargetHR ? "margin-top" : "padding-top";
        const sClass = isTargetHR ? "mb" : "pb";
        const sProperty = isTargetHR ? "margin-bottom" : "padding-bottom";

        const values = [0, 4];
        for (let i = 1; i <= 256 / 8; i++) {
            values.push(i * 8);
        }

        return {
            n: { classes: values.map((v) => nClass + v), values: values, cssProperty: nProperty },
            s: { classes: values.map((v) => sClass + v), values: values, cssProperty: sProperty },
        };
    }

    onResizeY(compass, initialClasses, currentIndex) {
        this.updateHandleY();
    }

    updateHandleY() {
        this.yHandles.forEach((handleEl) => {
            const topOrBottom = handleEl.matches(".n") ? "top" : "bottom";
            const padding = window.getComputedStyle(this.overlayTarget)[`padding-${topOrBottom}`];
            handleEl.style.height = padding; // TODO outerHeight (deduce borders ?)
        });
    }

    getSizingXConfig() {
        const resolutionModifier = this.isMobile ? "" : `${this.mobileBreakpoint}-`;
        const rowWidth = this.overlayTarget.closest(".row").getBoundingClientRect().width;
        const valuesE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        const valuesW = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
        return {
            e: {
                classes: valuesE.map((v) => `col-${resolutionModifier}${v}`),
                values: valuesE.map((v) => (rowWidth / 12) * v),
                cssProperty: "width",
            },
            w: {
                classes: valuesW.map((v) => `offset-${resolutionModifier}${v}`),
                values: valuesW.map((v) => (rowWidth / 12) * v),
                cssProperty: "margin-left",
            },
        };
    }

    onResizeX(compass, initialClasses, currentIndex) {
        const resolutionModifier = this.isMobile ? "" : `${this.mobileBreakpoint}-`;
        // (?!\S): following char cannot be a non-space character
        const offsetRegex = new RegExp(`(?:^|\\s+)offset-${resolutionModifier}(\\d{1,2})(?!\\S)`);
        const colRegex = new RegExp(`(?:^|\\s+)col-${resolutionModifier}(\\d{1,2})(?!\\S)`);

        const initialOffset = Number(initialClasses.match(offsetRegex)?.[1] || 0);

        if (compass === "w") {
            // Replacing the col class so the right border does not move when we
            // change the offset.
            const initialCol = Number(initialClasses.match(colRegex)?.[1] || 12);
            let offset = Number(this.overlayTarget.className.match(offsetRegex)?.[1] || 0);
            const offsetClass = `offset-${resolutionModifier}${offset}`;

            let colSize = initialCol - (offset - initialOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = initialOffset + initialCol - 1;
            }
            this.overlayTarget.classList.remove(offsetClass);
            this.replaceSizingClass(colRegex, `col-${resolutionModifier}${colSize}`);
            if (offset > 0) {
                this.overlayTarget.classList.add(`offset-${resolutionModifier}${offset}`);
            }

            // Add/remove the `offset-lg-0` class when needed.
            if (this.isMobile && offset === 0) {
                this.overlayTarget.classList.remove(`offset-${this.mobileBreakpoint}-0`);
            } else {
                const className = this.overlayTarget.className;
                const hasDesktopClass = !!className.match(
                    new RegExp(`(^|\\s+)offset-${this.mobileBreakpoint}-\\d{1,2}(?!\\S)`)
                );
                const hasMobileClass = !!className.match(/(^|\s+)offset-\d{1,2}(?!\S)/);
                if (
                    (this.isMobile && offset > 0 && !hasDesktopClass) ||
                    (!this.isMobile && offset === 0 && hasMobileClass)
                ) {
                    this.overlayTarget.classList.add(`offset-${this.mobileBreakpoint}-0`);
                }
            }
        } else if (initialOffset > 0) {
            const col = Number(this.overlayTarget.className.match(colRegex)?.[1] || 0);
            // Avoid overflowing to the right if the column size + the offset
            // exceeds 12.
            if (col + initialOffset > 12) {
                this.replaceSizingClass(colRegex, `col-${resolutionModifier}${12 - initialOffset}`);
            }
        }
    }

    getSizingGridConfig() {
        const rowEl = this.overlayTarget.closest(".row");
        const gridProp = getGridProperties(rowEl);
        const { rowStart, rowEnd, columnStart, columnEnd } = getGridItemProperties(
            this.overlayTarget
        );

        const valuesN = [];
        const valuesS = [];
        for (let i = 1; i < parseInt(rowEnd) + 12; i++) {
            valuesN.push(i);
            valuesS.push(i + 1);
        }
        const valuesW = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        const valuesE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

        return {
            n: {
                classes: valuesN.map((v) => "g-height-" + (rowEnd - v)),
                values: valuesN.map((v) => (gridProp.rowSize + gridProp.rowGap) * (v - 1)),
                cssProperty: "grid-row-start",
            },
            s: {
                classes: valuesS.map((v) => "g-height-" + (v - rowStart)),
                values: valuesS.map((v) => (gridProp.rowSize + gridProp.rowGap) * (v - 1)),
                cssProperty: "grid-row-end",
            },
            w: {
                classes: valuesW.map((v) => `g-col-${this.mobileBreakpoint}-` + (columnEnd - v)),
                values: valuesW.map((v) => (gridProp.columnSize + gridProp.columnGap) * (v - 1)),
                cssProperty: "grid-column-start",
            },
            e: {
                classes: valuesE.map((v) => `g-col-${this.mobileBreakpoint}-` + (v - columnStart)),
                values: valuesE.map((v) => (gridProp.columnSize + gridProp.columnGap) * (v - 1)),
                cssProperty: "grid-column-end",
            },
        };
    }

    onResizeGrid(compass, initialClasses, currentIndex) {
        const style = this.overlayTarget.style;
        if (compass === "n") {
            const rowEnd = parseInt(style.gridRowEnd);
            if (currentIndex < 0) {
                style.gridRowStart = 1;
            } else if (currentIndex + 1 >= rowEnd) {
                style.gridRowStart = rowEnd - 1;
            } else {
                style.gridRowStart = currentIndex + 1;
            }
        } else if (compass === "s") {
            const rowStart = parseInt(style.gridRowStart);
            const rowEnd = parseInt(style.gridRowEnd);
            if (currentIndex + 2 <= rowStart) {
                style.gridRowEnd = rowStart + 1;
            } else {
                style.gridRowEnd = currentIndex + 2;
            }

            // Updating the grid height.
            const rowEl = this.overlayTarget.parentNode;
            const rowCount = parseInt(rowEl.dataset.rowCount);
            const backgroundGridEl = rowEl.querySelector(".o_we_background_grid");
            const backgroundGridRowEnd = parseInt(backgroundGridEl.style.gridRowEnd);
            let rowMove = 0;
            if (style.gridRowEnd > rowEnd && style.gridRowEnd > rowCount + 1) {
                rowMove = style.gridRowEnd - rowEnd;
            } else if (style.gridRowEnd < rowEnd && style.gridRowEnd >= rowCount + 1) {
                rowMove = style.gridRowEnd - rowEnd;
            }
            backgroundGridEl.style.gridRowEnd = backgroundGridRowEnd + rowMove;
        } else if (compass === "w") {
            const columnEnd = parseInt(style.gridColumnEnd);
            if (currentIndex < 0) {
                style.gridColumnStart = 1;
            } else if (currentIndex + 1 >= columnEnd) {
                style.gridColumnStart = columnEnd - 1;
            } else {
                style.gridColumnStart = currentIndex + 1;
            }
        } else if (compass === "e") {
            const columnStart = parseInt(style.gridColumnStart);
            if (currentIndex + 2 > 13) {
                style.gridColumnEnd = 13;
            } else if (currentIndex + 2 <= columnStart) {
                style.gridColumnEnd = columnStart + 1;
            } else {
                style.gridColumnEnd = currentIndex + 2;
            }
        }

        if (compass === "n" || compass === "s") {
            const numberRows = style.gridRowEnd - style.gridRowStart;
            this.replaceSizingClass(/\s*(g-height-)([0-9-]+)/g, `g-height-${numberRows}`);
        }

        if (compass === "w" || compass === "e") {
            const numberColumns = style.gridColumnEnd - style.gridColumnStart;
            this.replaceSizingClass(
                new RegExp(`\\s*(g-col-${this.mobileBreakpoint}-)([0-9-]+)`, "g"),
                `g-col-${this.mobileBreakpoint}-${numberColumns}`
            );
        }
    }

    getDirections(ev, handleEl, sizingConfig) {
        let compass = false;
        let XY = false;
        if (handleEl.matches(".n")) {
            compass = "n";
            XY = "Y";
        } else if (handleEl.matches(".s")) {
            compass = "s";
            XY = "Y";
        } else if (handleEl.matches(".e")) {
            compass = "e";
            XY = "X";
        } else if (handleEl.matches(".w")) {
            compass = "w";
            XY = "X";
        } else if (handleEl.matches(".nw")) {
            compass = "nw";
            XY = "YX";
        } else if (handleEl.matches(".ne")) {
            compass = "ne";
            XY = "YX";
        } else if (handleEl.matches(".sw")) {
            compass = "sw";
            XY = "YX";
        } else if (handleEl.matches(".se")) {
            compass = "se";
            XY = "YX";
        }

        if (this.isRtl) {
            if (compass.includes("e")) {
                compass = compass.replace("e", "w");
            } else if (compass.includes("w")) {
                compass = compass.replace("w", "e");
            }
        }

        const currentConfig = [];
        for (let i = 0; i < compass.length; i++) {
            currentConfig.push(sizingConfig[compass[i]]);
        }

        const directions = [];
        for (const [i, config] of currentConfig.entries()) {
            // Compute the current index based on the current class/style.
            let currentIndex = 0;
            const cssProperty = config.cssProperty;
            const cssPropertyValue = parseInt(
                window.getComputedStyle(this.overlayTarget)[cssProperty]
            );
            config.classes.forEach((c, index) => {
                if (this.overlayTarget.classList.contains(c)) {
                    currentIndex = index;
                } else if (config.values[index] === cssPropertyValue) {
                    currentIndex = index;
                }
            });

            directions.push({
                config,
                currentIndex,
                initialIndex: currentIndex,
                initialClasses: this.overlayTarget.className,
                classRegex: new RegExp(
                    "\\s*" + config.classes[currentIndex].replace(/[-]*[0-9]+/, "[-]*[0-9]+"),
                    "g"
                ),
                initialPageXY: ev["page" + XY[i]],
                XY: XY[i],
                compass: compass[i],
            });
        }

        return directions;
    }

    onSizingStart(ev) {
        ev.preventDefault();
        const pointerDownTime = ev.timeStamp;

        // Lock the mutex.
        let sizingResolve;
        const sizingProm = new Promise((resolve) => (sizingResolve = () => resolve()));
        this.next(async () => await sizingProm, { withLoadingEffect: false, canTimeout: false });
        const cancelSizing = this.history.makeSavePoint();

        const handleEl = ev.currentTarget;
        const isGridHandle = handleEl.classList.contains("o_grid_handle");
        this.isMobile = this.isMobileView(this.overlayTarget);

        // If we are in grid mode, add a background grid and place it in front
        // of the other elements.
        let rowEl, backgroundGridEl;
        if (isGridHandle) {
            rowEl = this.overlayTarget.parentNode;
            backgroundGridEl = addBackgroundGrid(rowEl, 0);
            setElementToMaxZindex(backgroundGridEl, rowEl);
        }

        let sizingConfig, onResize;
        if (isGridHandle) {
            sizingConfig = this.getSizingGridConfig();
            onResize = this.onResizeGrid.bind(this);
        } else if (handleEl.matches(".n, .s")) {
            sizingConfig = this.getSizingYConfig();
            onResize = this.onResizeY.bind(this);
        } else {
            sizingConfig = this.getSizingXConfig();
            onResize = this.onResizeX.bind(this);
        }

        const directions = this.getDirections(ev, handleEl, sizingConfig);

        // Set the cursor.
        const cursorClass = `${window.getComputedStyle(handleEl)["cursor"]}-important`;
        window.document.body.classList.add(cursorClass);
        // Prevent the iframe from absorbing the pointer events.
        const iframeEl = this.overlayTarget.ownerDocument.defaultView.frameElement;
        iframeEl.classList.add("o_resizing");

        this.overlayElement.classList.remove("o_handlers_idle");

        const onSizingMove = (ev) => {
            for (const dir of directions) {
                const configValues = dir.config.values;
                const currentIndex = dir.currentIndex;
                const currentValue = configValues[currentIndex];

                // Get the number of pixels by which the pointer moved, compared
                // to the initial position of the handle.
                let deltaRaw = ev[`page${dir.XY}`] - dir.initialPageXY;
                // In RTL mode, reverse only horizontal movement (X axis).
                if (dir.XY === "X" && this.isRtl) {
                    deltaRaw = -deltaRaw;
                }
                const delta = deltaRaw + configValues[dir.initialIndex];

                // Compute the indexes of the next step and the step before it,
                // based on the delta.
                let nextIndex, beforeIndex;
                if (delta > currentValue) {
                    const nextValue = configValues.find((v) => v > delta);
                    nextIndex = nextValue
                        ? configValues.indexOf(nextValue)
                        : configValues.length - 1;
                    beforeIndex = nextIndex > 0 ? nextIndex - 1 : currentIndex;
                } else if (delta < currentValue) {
                    const nextValue = configValues.findLast((v) => v < delta);
                    nextIndex = nextValue ? configValues.indexOf(nextValue) : 0;
                    beforeIndex =
                        nextIndex < configValues.length - 1 ? nextIndex + 1 : currentIndex;
                }

                let change = false;
                if (delta !== currentValue) {
                    // First, catch up with the pointer (in the case we moved
                    // really fast).
                    if (beforeIndex !== currentIndex) {
                        this.replaceSizingClass(dir.classRegex, dir.config.classes[beforeIndex]);
                        dir.currentIndex = beforeIndex;
                        change = true;
                    }
                    // If the pointer moved by at least 2/3 of the space between
                    // the current and the next step, the handle is snapped to
                    // the next step and the class is replaced by the one
                    // matching this step.
                    const threshold =
                        (2 * configValues[nextIndex] + configValues[dir.currentIndex]) / 3;
                    if (
                        (delta > currentValue && delta > threshold) ||
                        (delta < currentValue && delta < threshold)
                    ) {
                        this.replaceSizingClass(dir.classRegex, dir.config.classes[nextIndex]);
                        dir.currentIndex = nextIndex;
                        change = true;
                    }
                }

                if (change) {
                    onResize(dir.compass, dir.initialClasses, dir.currentIndex);
                    // TODO notify other options (e.g. steps)
                }
            }
        };

        const onSizingStop = (ev) => {
            ev.preventDefault();
            window.removeEventListener("pointermove", onSizingMove);
            window.removeEventListener("pointerup", onSizingStop);
            window.document.body.classList.remove(cursorClass);
            iframeEl.classList.remove("o_resizing");
            this.overlayElement.classList.add("o_handlers_idle");

            // If we are in grid mode, removes the background grid.
            // Also sync the col-* class with the g-col-* class so the
            // toggle to normal mode and the mobile view are well done.
            if (isGridHandle) {
                backgroundGridEl.remove();
                resizeGrid(rowEl);

                const colClass = [...this.overlayTarget.classList].find((c) => /^col-/.test(c));
                const gColClass = [...this.overlayTarget.classList].find((c) => /^g-col-/.test(c));
                this.overlayTarget.classList.remove(colClass);
                this.overlayTarget.classList.add(gColClass.substring(2));
            }

            // Cancel the sizing if the element was not resized (to not have
            // mutations).
            const wasResized = !directions.every((dir) => dir.initialIndex === dir.currentIndex);
            if (wasResized) {
                this.history.addStep();
            } else {
                cancelSizing();
            }

            // Free the mutex.
            sizingResolve();

            // If no resizing happened and if the pointer was down less than
            // 500 ms, we assume that the user wanted to click on the element
            // behind the handle.
            if (!wasResized) {
                const pointerUpTime = ev.timeStamp;
                const pointerDownDuration = pointerUpTime - pointerDownTime;
                if (pointerDownDuration < 500) {
                    // Find the first element behind the overlay.
                    const sameCoordinatesEls = this.overlayTarget.ownerDocument.elementsFromPoint(
                        ev.pageX,
                        ev.pageY
                    );
                    // Check if it has native JS `click` function
                    const toBeClickedEl = sameCoordinatesEls.find(
                        (el) =>
                            !this.overlayContainer.contains(el) &&
                            !el.matches(".o_loading_screen") &&
                            typeof el.click === "function"
                    );
                    if (toBeClickedEl) {
                        toBeClickedEl.click();
                    }
                }
            }
        };

        window.addEventListener("pointermove", onSizingMove);
        window.addEventListener("pointerup", onSizingStop);
    }
}
