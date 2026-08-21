/**
 * Pure layout engine of the meeting stage: turns the stage size and the desired surfaces into
 * per-surface rectangles. It is fully deterministic and side-effect free (no DOM, no OWL, no
 * reactive state), so it can be unit-tested in isolation and shared by every future layout mode
 * (grid, spotlight, sidebar, presentation, ...).
 *
 * The stage is a single area; the layout decides:
 * - where every {@link SURFACE_PLACEMENT.MAIN} surface goes: the tile grid is computed to
 *   maximize the tile area (same heuristic as the pre-refactor flex layout), centered
 *   horizontally, top-aligned. A portrait stage instead fills its height, cropping the tiles;
 * - where every {@link SURFACE_PLACEMENT.SIDEBAR} surface goes: a 16:9 card stack at the right
 *   edge — or along the bottom on a portrait stage, where width is the scarce dimension —
 *   reserving its room so main tiles are never hidden behind it;
 * - where the {@link SURFACE_PLACEMENT.INSET} surface goes: a small picture-in-picture box pinned
 *   to a corner of the main tile it overlays.
 */

/** Where the layout puts a surface inside the stage. */
export const SURFACE_PLACEMENT = Object.freeze({
    MAIN: "main",
    SIDEBAR: "sidebar",
    INSET: "inset",
});

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
/**
 * Height (px) of the sidebar strip a portrait stage lays along its bottom edge. The narrow column
 * on its side: same 16:9 card, arranged along the other axis.
 */
export const SIDEBAR_STRIP_HEIGHT = (SIDEBAR_WIDTH_SMALL * 9) / 16;
/**
 * Stage width (px) under which the layout switches to its cramped variants. Measured on the stage,
 * never on the viewport: a chat window is a few hundred pixels wide whatever the screen is.
 */
export const NARROW_STAGE_WIDTH = 576;

/**
 * Height of the inset surface, as a fraction of the main tile it overlays. Relative to the tile
 * and not to the stage: a stage taller than its tile is mostly letterbox bars, and an inset sized
 * against those would cover the video instead of sitting in a corner of it.
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
 * Compute the layout of the meeting stage.
 *
 * @param {Object} param0
 * @param {number} param0.width stage width (px)
 * @param {number} param0.height stage height (px). Ignored when `autoHeight` is set.
 * @param {boolean} [param0.autoHeight=false] the stage has no height of its own (compact chat
 *  window): the grid is sized from the width alone and the caller receives the resulting
 *  `stageHeight` to assign to the stage. This is a property of the layout mode, never something
 *  to derive from `height`: every surface is absolutely positioned, so a stage that has not been
 *  laid out yet measures 0 exactly like a genuine auto-height one, and tiling it would produce a
 *  full-width single column whose content height then makes the next measurement agree.
 * @param {number} param0.aspectRatio tile aspect ratio (width / height)
 * @param {Array<{key: string, placement: string}>} param0.surfaces desired surfaces, in render
 *  order. The caller may append synthetic entries (e.g. the "more participants" indicator) to
 *  reserve a tile slot.
 * @param {boolean} [param0.capColumnsAtThree=false] cap the tiled grid at 3 columns (the
 *  "auto" layout in fullscreen).
 * @param {number} [param0.minTileWidth=320] smallest tile width before the grid is considered
 *  overflowed; used for the `maxTileCount` cap.
 * @param {boolean} [param0.fillMainWidth=false] the focused card spans the whole main area
 *  instead of keeping the grid's tile size (compact mode).
 * @param {string} [param0.insetCorner] corner the inset rests in, i.e. where the user dropped it.
 *  Unset until they move it, in which case the layout takes the corner the stage has room for.
 * @param {number} [param0.insetBottomMargin=INSET_MARGIN] bottom gap (px) of an inset resting in
 *  a bottom corner, for the callers whose main tile has its bottom covered (the floating call
 *  controls of a chat window).
 * @returns {{ rects: Object<string, Rect>, stageHeight: number|undefined, maxTileCount: number,
 *  cropsTiles: boolean }} `stageHeight` is returned when the stage is auto-height; `maxTileCount` is
 *  the column/row cap used by the "Prioritize tiles with video" filter; `cropsTiles` tells the
 *  caller that main tiles no longer have `aspectRatio`, so their video has to fill them by cropping
 *  rather than letterbox inside them.
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
            // The inset overlays the main tile instead of sharing the stage with it: it takes no room
            // in the grid above and is pinned inside the tile it is shown over, so it never drifts onto
            // the letterbox bars of a main tile narrower or shorter than the stage.
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
 * Divide the stage between the sidebar and the tile grid.
 *
 * A sidebar spends whichever dimension it is laid along. On a stage taller than it is wide the
 * width is the scarce one — a 230px column is well over a third of a phone — so the cards go along
 * the bottom and the main window keeps the full width. Either way the main area only covers what is
 * left, so the focused tile never hides behind the sidebar.
 *
 * @param {Object} param0
 * @param {number} param0.width
 * @param {number} param0.height
 * @param {boolean} param0.autoHeight
 * @param {boolean} param0.fillMainWidth
 * @param {number} param0.sidebarCount
 * @param {number} param0.tileCount
 * @returns {Stage}
 */
function divideStage({ width, height, autoHeight, fillMainWidth, sidebarCount, tileCount }) {
    // Measured on the stage and not on the main area: a sidebar eating half the width does not
    // make a desktop window a phone held upright.
    const isPortraitStage = !autoHeight && height > width;
    const hasSidebarStrip = isPortraitStage && sidebarCount > 0;
    // The sidebar width comes from the stage it has to fit in, which is the only thing that decides
    // whether there is room for it — a chat window is cramped on the widest of screens.
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
 * How many tiles fit at `minTileWidth` without shrinking further. Used by the "Prioritize tiles
 * with video" filter to decide when video-less tiles must be dropped.
 *
 * @param {Stage} stage
 * @param {{aspectRatio: number, minTileWidth: number}} param1
 * @returns {number}
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
 * @property {boolean} cropsTiles tiles no longer have `aspectRatio`, so their video has to fill
 *  them by cropping rather than letterbox inside them
 */

/**
 * Size the tile grid. The three cases are exclusive and each has its own reason to exist: a stage
 * with no height of its own cannot maximize anything, a portrait stage must stop preserving the
 * source ratio, and everything else is the pre-refactor flex heuristic.
 *
 * @param {Stage} stage
 * @param {{aspectRatio: number, capColumnsAtThree: boolean, minTileWidth: number, tileCount: number}} params
 * @returns {Grid}
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
 * With no height every column count has unlimited room, so maximizing the tile area would always
 * collapse the grid to a single full-width column. Size it from the width instead: as many columns
 * as fit at `minTileWidth`.
 *
 * @returns {Grid}
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
 * A stage taller than it is wide (a phone held upright) cannot be filled with tiles of the source
 * ratio: a single 16:9 tile in a 390x600 stage leaves two thirds of the screen black. Here the
 * layout stops preserving the ratio and fills the stage instead, letting the caller crop.
 *
 * Same criterion as {@link landscapeGrid} — the largest tile wins — except shape stays free, which
 * is what makes the area worth maximizing at all. The two bounds are the source and the area to
 * fill: a tile is never wider than the video it shows (there would be nothing to fill the sides
 * with) and never narrower than the area itself. Taking the area rather than a fixed floor is what
 * lets a taller phone hand its tiles the extra height instead of banding it off.
 *
 * @returns {Grid}
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

/**
 * The tiled grid maximizes the tile area across every possible column count, at the source ratio.
 *
 * @returns {Grid}
 */
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
 * Lay the main tiles out inside the main area, centering what the grid could not fill: the block
 * vertically, and each row — including a partial last one — horizontally. The grid only ever
 * maximizes the tile area, so whichever dimension it did not run out of is leftover: two tiles on
 * a wide stage are limited by width and leave a third of the height empty.
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
        // In compact mode the focused card fills the whole width.
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
 * Lay the sidebar cards along the sidebar, one 16:9 card per slot. They shrink (keeping their
 * ratio, centered across the sidebar) rather than overflowing the stage: every surface shares a
 * single stage, so an overflowing sidebar would scroll the focused tile out of view instead of
 * scrolling on its own.
 *
 * @param {Object<string, Rect>} rects written in place
 * @param {Array<{key: string}>} sidebarSurfaces
 * @param {Stage} stage
 */
function placeSidebarSurfaces(rects, sidebarSurfaces, stage) {
    const { width, height, heightLimit, sidebarWidth, hasSidebarStrip } = stage;
    const slotCount = Math.max(1, sidebarSurfaces.length);
    if (hasSidebarStrip) {
        const cardWidth = Math.min((SIDEBAR_STRIP_HEIGHT * 16) / 9, width / slotCount);
        const cardHeight = (cardWidth * 9) / 16;
        const stripY = height - SIDEBAR_STRIP_HEIGHT + (SIDEBAR_STRIP_HEIGHT - cardHeight) / 2;
        const stripX = Math.max(0, (width - sidebarSurfaces.length * cardWidth) / 2);
        sidebarSurfaces.forEach((surface, index) => {
            rects[surface.key] = {
                x: stripX + index * cardWidth,
                y: stripY,
                width: cardWidth,
                height: cardHeight,
            };
        });
        return;
    }
    const cardHeight = Math.min((sidebarWidth * 9) / 16, heightLimit / slotCount);
    const cardWidth = (cardHeight * 16) / 9;
    const columnX = width - sidebarWidth + (sidebarWidth - cardWidth) / 2;
    sidebarSurfaces.forEach((surface, index) => {
        rects[surface.key] = {
            x: columnX,
            y: index * cardHeight,
            width: cardWidth,
            height: cardHeight,
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
    // A narrow stage has its call controls spanning the bottom, over the corner the inset would
    // otherwise rest in.
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
