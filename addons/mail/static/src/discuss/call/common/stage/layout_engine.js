/** @typedef {import("@mail/discuss/call/common/stage/surface_manager").StagePipeline} StagePipeline */

/**
 * The second step of the {@link StagePipeline}.
 *
 * Turns a stage size and the desired surfaces into per-surface rectangles, with no DOM in sight.
 * The stage is one area shared by the three {@link SURFACE_PLACEMENT}: the tile grid, the sidebar
 * that reserves its room out of the grid's, and the inset overlaying the first tile.
 */

/** @typedef {typeof SURFACE_PLACEMENT[keyof typeof SURFACE_PLACEMENT]} SurfacePlacement */

/** Where the layout puts a surface inside the stage. */
export const SURFACE_PLACEMENT = Object.freeze({
    MAIN: "main",
    SIDEBAR: "sidebar",
    INSET: "inset",
});

/** @typedef {typeof SURFACE_CORNER[keyof typeof SURFACE_CORNER]} SurfaceCorner */

/** Corner of the main tile an overlay surface is pinned to. */
export const SURFACE_CORNER = Object.freeze({
    TOP_LEFT: "top-left",
    TOP_RIGHT: "top-right",
    BOTTOM_LEFT: "bottom-left",
    BOTTOM_RIGHT: "bottom-right",
});

/** Width (px) of the sidebar column. */
export const SIDEBAR_WIDTH = 230;
/** Width (px) of the sidebar column on a stage too narrow for the regular one. */
export const SIDEBAR_WIDTH_SMALL = 160;
/** Height (px) of the bottom sidebar strip of a portrait stage: the narrow column on its side. */
export const SIDEBAR_STRIP_HEIGHT = (SIDEBAR_WIDTH_SMALL * 9) / 16;
/**
 * Stage width (px) under which the layout switches to its cramped variants. Measured on the stage,
 * never on the viewport: a chat window is a few hundred pixels wide whatever the screen is.
 */
export const NARROW_STAGE_WIDTH = 576;

/**
 * Height of the inset, as a fraction of the main tile it overlays — not of the stage, whose
 * letterbox bars it would then spill over.
 */
export const INSET_HEIGHT_RATIO = 0.25;
/** Largest height (px) of the inset surface. */
export const INSET_MAX_HEIGHT = 125;
/** Gap (px) between the inset surface and the edges of the main tile. */
export const INSET_MARGIN = 8;

/**
 * @typedef Rect
 * @property {number} x
 * @property {number} y
 * @property {number} width
 * @property {number} height
 */

/**
 * Gives back the rectangle of every surface, plus the `stageHeight` an auto-height caller has to
 * assign, the `maxTileCount` the caller caps at, and whether the caller has to crop.
 *
 * @param {Object} param0
 * @param {number} param0.width stage width (px)
 * @param {number} param0.height stage height (px). Ignored when `autoHeight` is set.
 * @param {boolean} [param0.autoHeight=false] the stage has no height of its own. A property of the
 *  layout mode, never derived from `height`: a stage not laid out yet also measures 0.
 * @param {number} param0.aspectRatio tile aspect ratio (width / height)
 * @param {Array<{key: string, placement: SurfacePlacement}>} param0.surfaces desired surfaces, in
 *  render order. Synthetic entries are allowed, to reserve a slot.
 * @param {boolean} [param0.capColumnsAtThree=false] cap the tiled grid at 3 columns
 * @param {number} [param0.minTileWidth=320] smallest tile width before the grid overflows
 * @param {boolean} [param0.fillMainWidth=false] the focused surface spans the whole main area
 * @param {SurfaceCorner} [param0.insetCorner] corner the user dropped the inset in. Unset until
 *  they move it, in which case the layout takes the corner the stage has room for.
 * @param {number} [param0.insetBottomMargin=INSET_MARGIN] bottom gap (px) of an inset in a bottom
 *  corner, for the callers whose main tile has its bottom covered
 */
export function computeLayout({
    width,
    height,
    autoHeight = false,
    aspectRatio,
    surfaces,
    capColumnsAtThree = false,
    minTileWidth = 320,
    fillMainWidth = false,
    insetCorner,
    insetBottomMargin = INSET_MARGIN,
}) {
    const rects = {};
    const mainSurfaces = surfaces.filter((surface) => surface.placement === SURFACE_PLACEMENT.MAIN);
    const sidebarSurfaces = surfaces.filter(
        (surface) => surface.placement === SURFACE_PLACEMENT.SIDEBAR
    );
    const tileCount = mainSurfaces.length;
    const stage = divideStage({
        width,
        height,
        autoHeight,
        fillMainWidth,
        sidebarCount: sidebarSurfaces.length,
        tileCount,
    });
    const grid = resolveGrid(stage, { aspectRatio, capColumnsAtThree, minTileWidth, tileCount });
    placeMainSurfaces(rects, mainSurfaces, stage, grid, { aspectRatio, fillMainWidth });
    placeSidebarSurfaces(rects, sidebarSurfaces, stage);
    placeInset(
        rects,
        surfaces.find((s) => s.placement === SURFACE_PLACEMENT.INSET),
        {
            // Pinned inside the main tile, not the stage: it must not drift onto the letterbox.
            anchor: rects[mainSurfaces[0]?.key] ?? { x: 0, y: 0, width, height },
            aspectRatio,
            insetCorner,
            insetBottomMargin,
            stageWidth: width,
        }
    );
    return {
        rects,
        stageHeight: autoHeight
            ? Math.ceil(tileCount / grid.columnCount) * grid.tileHeight
            : undefined,
        maxTileCount: tileCapacity(stage, { aspectRatio, minTileWidth }),
        cropsTiles: grid.cropsTiles,
    };
}

/**
 * @typedef Stage how the box divides up before a single tile is sized
 * @property {number} width
 * @property {number} height
 * @property {boolean} autoHeight
 * @property {number} mainAreaWidth room left for the tile grid once the sidebar has its share
 * @property {number} mainAreaHeight
 * @property {number} heightLimit `mainAreaHeight`, or unbounded on an auto-height stage
 * @property {number} sidebarWidth width the sidebar column would take
 * @property {boolean} hasSidebarStrip the sidebar runs along the bottom instead of the right edge
 * @property {boolean} isPortrait the tile grid fills a stage taller than it is wide, cropping
 */

/**
 * Divide the stage between the sidebar and the tile grid. A sidebar spends whichever dimension it
 * is laid along, so a portrait stage — where width is the scarce one — lays it along the bottom.
 *
 * @param {Object} param0
 * @param {number} param0.width
 * @param {number} param0.height
 * @param {boolean} param0.autoHeight
 * @param {boolean} param0.fillMainWidth
 * @param {number} param0.sidebarCount
 * @param {number} param0.tileCount
 */
function divideStage({ width, height, autoHeight, fillMainWidth, sidebarCount, tileCount }) {
    // On the stage, not the main area: a sidebar eating half the width is not a phone upright.
    const isPortraitStage = !autoHeight && height > width;
    const hasSidebarStrip = isPortraitStage && sidebarCount > 0;
    // From the stage, not the viewport: a chat window is cramped on the widest of screens.
    const sidebarWidth = width < NARROW_STAGE_WIDTH ? SIDEBAR_WIDTH_SMALL : SIDEBAR_WIDTH;
    const mainAreaWidth =
        sidebarCount && !hasSidebarStrip ? Math.max(0, width - sidebarWidth) : width;
    const mainAreaHeight = Math.max(0, height - (hasSidebarStrip ? SIDEBAR_STRIP_HEIGHT : 0));
    return {
        width,
        height,
        autoHeight,
        mainAreaWidth,
        mainAreaHeight,
        heightLimit: autoHeight ? Number.POSITIVE_INFINITY : mainAreaHeight,
        sidebarWidth,
        hasSidebarStrip,
        isPortrait: isPortraitStage && !fillMainWidth && tileCount > 0,
    };
}

/**
 * How many tiles fit at `minTileWidth` without shrinking further: the point past which the caller
 * has to drop entries instead of shrinking them again.
 *
 * @param {Stage} stage
 * @param {{aspectRatio: number, minTileWidth: number}} param1
 */
function tileCapacity({ mainAreaWidth, mainAreaHeight }, { aspectRatio, minTileWidth }) {
    const capColumns = Math.max(1, Math.floor(mainAreaWidth / minTileWidth));
    const capRows = Math.max(1, Math.floor(mainAreaHeight / (minTileWidth / aspectRatio)));
    return capColumns * capRows;
}

/**
 * @typedef Grid
 * @property {number} columnCount at least 1, even with nothing to lay out
 * @property {number} tileWidth
 * @property {number} tileHeight
 * @property {boolean} cropsTiles tiles no longer have `aspectRatio`, so their content has to fill
 *  them by cropping rather than letterbox inside them
 */

/**
 * @param {Stage} stage
 * @param {{aspectRatio: number, capColumnsAtThree: boolean, minTileWidth: number, tileCount: number}} params
 */
function resolveGrid(stage, params) {
    const maxColumnCount = params.capColumnsAtThree
        ? Math.min(params.tileCount, 3)
        : params.tileCount;
    const grid = stage.autoHeight
        ? autoHeightGrid(stage, params, maxColumnCount)
        : stage.isPortrait
        ? portraitGrid(stage, params, maxColumnCount)
        : landscapeGrid(stage, params, maxColumnCount);
    return { ...grid, columnCount: Math.max(1, grid.columnCount) };
}

/**
 * With no height, maximizing the tile area would collapse the grid to one full-width column. Size
 * it from the width instead: as many columns as fit at `minTileWidth`.
 */
function autoHeightGrid({ mainAreaWidth }, { aspectRatio, minTileWidth }, maxColumnCount) {
    const columnCount = Math.max(
        1,
        Math.min(maxColumnCount, Math.floor(mainAreaWidth / minTileWidth))
    );
    const tileWidth = Math.floor(mainAreaWidth / columnCount);
    return {
        columnCount,
        tileWidth,
        tileHeight: Math.floor(tileWidth / aspectRatio),
        cropsTiles: false,
    };
}

/**
 * A 16:9 tile in a 390x600 stage leaves two thirds black, so a portrait stage frees the tile shape
 * and the caller crops. Largest tile still wins, between the source ratio (nothing would fill the
 * sides) and the area's, which hands a taller phone its extra height instead of banding it off.
 */
function portraitGrid(
    { mainAreaWidth, mainAreaHeight },
    { aspectRatio, tileCount },
    maxColumnCount
) {
    const areaRatio = mainAreaWidth / mainAreaHeight;
    let best = { columnCount: 0, tileWidth: 0, tileHeight: 0, cropsTiles: false };
    let bestArea = 0;
    for (let columnCount = 1; columnCount <= maxColumnCount; columnCount++) {
        const rowCount = Math.ceil(tileCount / columnCount);
        const cellWidth = mainAreaWidth / columnCount;
        const cellHeight = mainAreaHeight / rowCount;
        const tileRatio = Math.min(Math.max(cellWidth / cellHeight, areaRatio), aspectRatio);
        let tileWidth = Math.floor(cellWidth);
        let tileHeight = Math.floor(tileWidth / tileRatio);
        if (tileHeight > cellHeight) {
            tileHeight = Math.floor(cellHeight);
            tileWidth = Math.floor(tileHeight * tileRatio);
        }
        const area = tileHeight * tileWidth;
        if (area <= bestArea) {
            continue;
        }
        bestArea = area;
        best = { columnCount, tileWidth, tileHeight, cropsTiles: tileRatio < aspectRatio };
    }
    return best;
}

/** Maximizes the tile area across every possible column count, at the source ratio. */
function landscapeGrid({ mainAreaWidth, heightLimit }, { aspectRatio, tileCount }, maxColumnCount) {
    let best = { columnCount: 0, tileWidth: 0, tileHeight: 0, cropsTiles: false };
    let bestArea = 0;
    for (let columnCount = 1; columnCount <= maxColumnCount; columnCount++) {
        const rowCount = Math.ceil(tileCount / columnCount);
        const potentialHeight = mainAreaWidth / (columnCount * aspectRatio);
        const potentialWidth = heightLimit / rowCount;
        let tileHeight;
        let tileWidth;
        if (potentialHeight > potentialWidth) {
            tileHeight = Math.floor(potentialWidth);
            tileWidth = Math.floor(tileHeight * aspectRatio);
        } else {
            tileWidth = Math.floor(mainAreaWidth / columnCount);
            tileHeight = Math.floor(tileWidth / aspectRatio);
        }
        const area = tileHeight * tileWidth;
        if (area <= bestArea) {
            continue;
        }
        bestArea = area;
        best = { columnCount, tileWidth, tileHeight, cropsTiles: false };
    }
    return best;
}

/**
 * Centers what the grid could not fill: the block vertically, each row horizontally.
 *
 * @param {Object<string, Rect>} rects written in place
 * @param {Array<{key: string}>} mainSurfaces
 * @param {Stage} stage
 * @param {Grid} grid
 * @param {{aspectRatio: number, fillMainWidth: boolean}} param4
 */
function placeMainSurfaces(rects, mainSurfaces, stage, grid, { aspectRatio, fillMainWidth }) {
    const { mainAreaWidth, mainAreaHeight } = stage;
    const { columnCount, tileWidth, tileHeight } = grid;
    if (fillMainWidth) {
        const surface = mainSurfaces[0];
        if (surface) {
            rects[surface.key] = {
                x: 0,
                y: 0,
                width: mainAreaWidth,
                height: mainAreaWidth / aspectRatio,
            };
        }
        return;
    }
    const tileCount = mainSurfaces.length;
    const rowCount = Math.ceil(tileCount / columnCount);
    const offsetY = Math.max(0, (mainAreaHeight - rowCount * tileHeight) / 2);
    mainSurfaces.forEach((surface, index) => {
        const row = Math.floor(index / columnCount);
        const columnsInRow = Math.min(columnCount, tileCount - row * columnCount);
        const offsetX = Math.max(0, (mainAreaWidth - columnsInRow * tileWidth) / 2);
        rects[surface.key] = {
            x: offsetX + (index % columnCount) * tileWidth,
            y: offsetY + row * tileHeight,
            width: tileWidth,
            height: tileHeight,
        };
    });
}

/**
 * Lay the sidebar surfaces, one 16:9 surface per slot. They shrink rather than overflow: the
 * sidebar shares the stage's scroll, so overflowing it would scroll the focused tile out of view.
 *
 * @param {Object<string, Rect>} rects written in place
 * @param {Array<{key: string}>} sidebarSurfaces
 * @param {Stage} stage
 */
function placeSidebarSurfaces(rects, sidebarSurfaces, stage) {
    const { width, height, heightLimit, sidebarWidth, hasSidebarStrip } = stage;
    const slotCount = Math.max(1, sidebarSurfaces.length);
    if (hasSidebarStrip) {
        const surfaceWidth = Math.min((SIDEBAR_STRIP_HEIGHT * 16) / 9, width / slotCount);
        const surfaceHeight = (surfaceWidth * 9) / 16;
        const stripY = height - SIDEBAR_STRIP_HEIGHT + (SIDEBAR_STRIP_HEIGHT - surfaceHeight) / 2;
        const stripX = Math.max(0, (width - sidebarSurfaces.length * surfaceWidth) / 2);
        sidebarSurfaces.forEach((surface, index) => {
            rects[surface.key] = {
                x: stripX + index * surfaceWidth,
                y: stripY,
                width: surfaceWidth,
                height: surfaceHeight,
            };
        });
        return;
    }
    const surfaceHeight = Math.min((sidebarWidth * 9) / 16, heightLimit / slotCount);
    const surfaceWidth = (surfaceHeight * 16) / 9;
    const columnX = width - sidebarWidth + (sidebarWidth - surfaceWidth) / 2;
    sidebarSurfaces.forEach((surface, index) => {
        rects[surface.key] = {
            x: columnX,
            y: index * surfaceHeight,
            width: surfaceWidth,
            height: surfaceHeight,
        };
    });
}

/**
 * Pin the inset surface inside a corner of the tile it overlays.
 *
 * @param {Object<string, Rect>} rects written in place
 * @param {{key: string}|undefined} insetSurface
 * @param {Object} param2
 * @param {Rect} param2.anchor the tile the inset rests in
 * @param {number} param2.aspectRatio
 * @param {string} [param2.insetCorner]
 * @param {number} param2.insetBottomMargin
 * @param {number} param2.stageWidth
 */
function placeInset(
    rects,
    insetSurface,
    { anchor, aspectRatio, insetCorner, insetBottomMargin, stageWidth }
) {
    if (!insetSurface) {
        return;
    }
    const insetHeight = Math.min(anchor.height * INSET_HEIGHT_RATIO, INSET_MAX_HEIGHT);
    // A narrow stage has its call controls spanning the bottom corners.
    const corner =
        insetCorner ??
        (stageWidth < NARROW_STAGE_WIDTH ? SURFACE_CORNER.TOP_LEFT : SURFACE_CORNER.BOTTOM_RIGHT);
    const isTop = [SURFACE_CORNER.TOP_LEFT, SURFACE_CORNER.TOP_RIGHT].includes(corner);
    const isLeft = [SURFACE_CORNER.TOP_LEFT, SURFACE_CORNER.BOTTOM_LEFT].includes(corner);
    const insetWidth = insetHeight * aspectRatio;
    rects[insetSurface.key] = {
        x: isLeft ? anchor.x + INSET_MARGIN : anchor.x + anchor.width - insetWidth - INSET_MARGIN,
        y: isTop
            ? anchor.y + INSET_MARGIN
            : anchor.y + anchor.height - insetHeight - insetBottomMargin,
        width: insetWidth,
        height: insetHeight,
    };
}
