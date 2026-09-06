import {
    computeLayout,
    INSET_MARGIN,
    NARROW_STAGE_WIDTH,
    SIDEBAR_STRIP_HEIGHT,
    SIDEBAR_WIDTH,
    SIDEBAR_WIDTH_SMALL,
    SURFACE_CORNER,
    SURFACE_PLACEMENT,
} from "@mail/discuss/call/common/meeting_layout_engine";

import { describe, expect, test } from "@odoo/hoot";

/**
 * Phase 2 acceptance: the layout engine is a pure, deterministic module (no DOM, no OWL, no
 * state) that turns the stage size and the desired surfaces into per-surface rects.
 */

describe.current.tags("desktop");

const MAIN = SURFACE_PLACEMENT.MAIN;
const SIDEBAR = SURFACE_PLACEMENT.SIDEBAR;
const INSET = SURFACE_PLACEMENT.INSET;

function mainSurfaces(count, prefix = "s") {
    return Array.from({ length: count }, (_, i) => ({ key: `${prefix}${i}`, placement: MAIN }));
}

describe("meeting layout engine", () => {
    test("is deterministic", () => {
        const params = {
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
        };
        expect(computeLayout(params)).toEqual(computeLayout(params));
    });

    test("golden values: 3 tiles in a 1000x600 view", () => {
        const { rects } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(3),
        });
        // 2x2 of 500x281: the 562px block is centered in the 600px stage, and the lone tile of the
        // last row is centered across the width.
        expect(rects.s0).toEqual({ x: 0, y: 19, width: 500, height: 281 });
        expect(rects.s1).toEqual({ x: 500, y: 19, width: 500, height: 281 });
        expect(rects.s2).toEqual({ x: 250, y: 300, width: 500, height: 281 });
    });

    test("the tile block is centered on both axes, whichever dimension is left over", () => {
        // The grid maximizes the tile area, so it runs out of one dimension and leaves the other
        // over. Two people on a stage wider than 16:9 are limited by the width and would otherwise
        // sit against the top edge with a third of the stage black below them.
        const { rects } = computeLayout({
            width: 1200,
            height: 500,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(2),
        });
        expect(rects.s0).toEqual({ x: 0, y: 81.5, width: 600, height: 337 });
        expect(rects.s1).toEqual({ x: 600, y: 81.5, width: 600, height: 337 });
        // Same leftover above and below.
        expect(rects.s0.y).toBeCloseTo(500 - (rects.s0.y + rects.s0.height));
    });

    test("tiles are uniform, non-overlapping and inside the stage for 1..13 participants", () => {
        for (const count of [1, 2, 3, 4, 6, 9, 12, 13]) {
            const { rects } = computeLayout({
                width: 1280,
                height: 720,
                aspectRatio: 16 / 9,
                surfaces: mainSurfaces(count),
            });
            expect(Object.keys(rects)).toHaveLength(count);
            const rectList = Object.values(rects);
            for (const rect of rectList) {
                expect(rect.width).toBe(rectList[0].width);
                expect(rect.height).toBe(rectList[0].height);
                expect(rect.x).toBeWithin(0, 1280);
                expect(rect.y).toBeWithin(0, 720);
                expect(rect.x + rect.width).toBeWithin(0, 1280);
                expect(rect.y + rect.height).toBeWithin(0, 720);
            }
            for (let i = 0; i < rectList.length; i++) {
                for (let j = i + 1; j < rectList.length; j++) {
                    const a = rectList[i];
                    const b = rectList[j];
                    const overlaps =
                        a.x < b.x + b.width &&
                        b.x < a.x + a.width &&
                        a.y < b.y + b.height &&
                        b.y < a.y + a.height;
                    expect(overlaps).toBe(false);
                }
            }
        }
    });

    test("a single tile (spotlight) fills the stage", () => {
        const { rects } = computeLayout({
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(1),
        });
        expect(rects.s0).toEqual({ x: 0, y: 0, width: 1280, height: 720 });
    });

    test("sidebar reserves its width and stacks 16:9 cards at the right edge", () => {
        const { rects } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "sb0", placement: SIDEBAR },
                { key: "sb1", placement: SIDEBAR },
                { key: "sb2", placement: SIDEBAR },
            ],
        });
        // The main tile never goes under the sidebar column.
        expect(rects.main).toEqual({ x: 0, y: 83.5, width: 770, height: 433 });
        expect(rects.main.x + rects.main.width).toBeWithin(0, 1000 - 230);
        // Sidebar cards stack from the top, one 16:9 card per row.
        expect(rects.sb0).toEqual({ x: 770, y: 0, width: 230, height: 129.375 });
        expect(rects.sb1).toEqual({ x: 770, y: 129.375, width: 230, height: 129.375 });
        expect(rects.sb2).toEqual({ x: 770, y: 258.75, width: 230, height: 129.375 });
    });

    test("a narrow stage gets the narrow sidebar column", () => {
        // Measured on the stage, not on the viewport: a chat window is this cramped on a 4K screen
        // too, and a viewport breakpoint would hand it the full 230px column.
        const { rects } = computeLayout({
            width: NARROW_STAGE_WIDTH - 76,
            height: 400,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "sb0", placement: SIDEBAR },
            ],
        });
        expect(rects.sb0.width).toBe(SIDEBAR_WIDTH_SMALL);
        expect(rects.main.width).toBe(500 - SIDEBAR_WIDTH_SMALL);
        // One pixel wider than the threshold and the regular column is back.
        const wide = computeLayout({
            width: NARROW_STAGE_WIDTH,
            height: 400,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "sb0", placement: SIDEBAR },
            ],
        });
        expect(wide.rects.sb0.width).toBe(SIDEBAR_WIDTH);
    });

    test("a sidebar too tall for the stage shrinks to fit instead of overflowing", () => {
        const { rects } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                ...Array.from({ length: 8 }, (_, index) => ({
                    key: `sb${index}`,
                    placement: SIDEBAR,
                })),
            ],
        });
        // 8 cards at their natural 129.375px would need 1035px: they shrink to 600 / 8 instead, so
        // the last one still ends exactly at the bottom of the stage.
        expect(rects.sb0.height).toBe(75);
        expect(rects.sb7.y + rects.sb7.height).toBe(600);
        // The ratio is kept and the narrower card is centered in the reserved column.
        expect(rects.sb0.width).toBeCloseTo((75 * 16) / 9);
        expect(rects.sb0.x + rects.sb0.width / 2).toBeCloseTo(1000 - 230 / 2);
        // Shrinking the cards does not give the reserved width back to the main tile.
        expect(rects.main.x + rects.main.width).toBeWithin(0, 1000 - 230);
    });

    test("the inset is pinned inside the main tile and reserves no room", () => {
        const { rects } = computeLayout({
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "inset", placement: INSET },
            ],
        });
        // The main tile is laid out as if the inset were not there: it overlays, it does not share.
        expect(rects.main).toEqual({ x: 0, y: 0, width: 1280, height: 720 });
        // 25% of the tile height, capped at 125px, 16:9, bottom-right by default.
        expect(rects.inset.height).toBe(125);
        expect(rects.inset.width).toBeCloseTo((125 * 16) / 9);
        expect(rects.inset.x + rects.inset.width).toBeCloseTo(1280 - INSET_MARGIN);
        expect(rects.inset.y + rects.inset.height).toBeCloseTo(720 - INSET_MARGIN);
    });

    test("the inset follows the corner it was dropped in", () => {
        const surfaces = [
            { key: "main", placement: MAIN },
            { key: "inset", placement: INSET },
        ];
        const corners = {
            [SURFACE_CORNER.TOP_LEFT]: { left: true, top: true },
            [SURFACE_CORNER.TOP_RIGHT]: { left: false, top: true },
            [SURFACE_CORNER.BOTTOM_LEFT]: { left: true, top: false },
            [SURFACE_CORNER.BOTTOM_RIGHT]: { left: false, top: false },
        };
        for (const [insetCorner, { left, top }] of Object.entries(corners)) {
            const { rects } = computeLayout({
                width: 1000,
                height: 600,
                aspectRatio: 16 / 9,
                surfaces,
                insetCorner,
            });
            const { x, y, width, height } = rects.inset;
            expect(left ? x : 1000 - (x + width)).toBeCloseTo(INSET_MARGIN);
            // The main tile is 1000x562 (16:9) centered in a 600px stage, so both edges are the
            // tile's and not the stage's.
            const main = rects.main;
            expect(top ? y - main.y : main.y + main.height - (y + height)).toBeCloseTo(
                INSET_MARGIN
            );
        }
    });

    test("an inset the user never moved rests where the stage has room for it", () => {
        const surfaces = [
            { key: "main", placement: MAIN },
            { key: "inset", placement: INSET },
        ];
        // A narrow stage has its call controls spanning the bottom, so the default goes up top.
        const narrow = computeLayout({
            width: NARROW_STAGE_WIDTH - 1,
            height: 400,
            aspectRatio: 16 / 9,
            surfaces,
        });
        expect(narrow.rects.inset.y - narrow.rects.main.y).toBe(INSET_MARGIN);
        expect(narrow.rects.inset.x).toBe(INSET_MARGIN);
        // A roomy one keeps it out of the way, bottom right.
        const wide = computeLayout({ width: 1280, height: 720, aspectRatio: 16 / 9, surfaces });
        expect(wide.rects.inset.y + wide.rects.inset.height).toBeCloseTo(720 - INSET_MARGIN);
        expect(wide.rects.inset.x + wide.rects.inset.width).toBeCloseTo(1280 - INSET_MARGIN);
    });

    test("the inset stays over the video of a main tile that does not fill the stage", () => {
        // A stage taller than its 16:9 tile and narrowed by a sidebar: anchoring the inset to the
        // stage would drop it on the letterbox bar, or under the sidebar it is not part of.
        const { rects } = computeLayout({
            width: 1000,
            height: 800,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "inset", placement: INSET },
                { key: "sb0", placement: SIDEBAR },
            ],
        });
        expect(rects.main).toEqual({ x: 0, y: 183.5, width: 770, height: 433 });
        expect(rects.inset.x).toBeGreaterThan(rects.main.x);
        expect(rects.inset.x + rects.inset.width).toBeCloseTo(770 - INSET_MARGIN);
        expect(rects.inset.y + rects.inset.height).toBeCloseTo(183.5 + 433 - INSET_MARGIN);
        // Sized against the tile, so it keeps the same share of the video at any stage size.
        expect(rects.inset.height).toBeCloseTo(433 * 0.25);
    });

    test("insetBottomMargin lifts a bottom inset above the call controls", () => {
        const { rects } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "inset", placement: INSET },
            ],
            insetBottomMargin: 40,
        });
        expect(rects.main.y + rects.main.height - (rects.inset.y + rects.inset.height)).toBeCloseTo(
            40
        );
        // Only the bottom edge is affected; the side keeps the regular margin.
        expect(1000 - (rects.inset.x + rects.inset.width)).toBeCloseTo(INSET_MARGIN);
    });

    test("a portrait stage fills its height instead of letterboxing two thirds of it", () => {
        // A phone held upright, one spotlighted participant. A 16:9 tile would be 390x219 and
        // leave 381px of black below it.
        const { rects, cropsTiles } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(1),
        });
        expect(rects.s0).toEqual({ x: 0, y: 0, width: 390, height: 600 });
        expect(cropsTiles).toBe(true);
    });

    test("fillMainWidth switches the portrait fill off, so a portrait stage must not ask for it", () => {
        // The two are exclusive by construction: `fillMainWidth` sizes the card from the width at
        // the source ratio, which is how a stage with no height of its own learns the height to
        // take. A portrait stage has one, so asking for both spends three quarters of a phone on
        // black — the trap a stage profile falls into by copying the chat window's row.
        const surfaces = [
            { key: "main", placement: MAIN },
            { key: "inset", placement: INSET },
        ];
        const filled = computeLayout({
            width: 390,
            height: 844,
            aspectRatio: 16 / 9,
            surfaces,
            fillMainWidth: true,
        });
        expect(filled.rects.main).toEqual({ x: 0, y: 0, width: 390, height: 219.375 });
        expect(filled.cropsTiles).toBe(false);
        const portrait = computeLayout({ width: 390, height: 844, aspectRatio: 16 / 9, surfaces });
        expect(portrait.rects.main).toEqual({ x: 0, y: 0, width: 390, height: 844 });
        expect(portrait.cropsTiles).toBe(true);
        // The inset is sized against the tile it overlays, so it shrinks with it too.
        expect(portrait.rects.inset.height).toBeGreaterThan(filled.rects.inset.height);
    });

    test("a taller stage hands its tiles the extra height", () => {
        // The tile shape is bounded by the stage and not by a constant, so a phone that is more
        // elongated gets a more elongated — and bigger — tile, rather than the same tile with
        // more black around it.
        const tall = computeLayout({
            width: 390,
            height: 844,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(1),
        });
        expect(tall.rects.s0).toEqual({ x: 0, y: 0, width: 390, height: 844 });
        // A fixed floor would have banded the difference off instead: the same tile as on the
        // shorter phone, with more black around it.
        const shorter = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(1),
        });
        expect(shorter.rects.s0.height).toBe(600);
        expect(tall.rects.s0.height).toBeGreaterThan(shorter.rects.s0.height);
    });

    test("a portrait grid picks the column count with the largest tile", () => {
        // 4 participants: one column of 266x150 uncropped tiles is the *lesser* layout, even
        // though it needs no crop at all. 2x2 gives each of them 58500px² instead of 39900, and
        // between them they cover the stage exactly.
        const { rects, cropsTiles } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
        });
        expect(rects.s0).toEqual({ x: 0, y: 0, width: 195, height: 300 });
        expect(rects.s1).toEqual({ x: 195, y: 0, width: 195, height: 300 });
        expect(rects.s2).toEqual({ x: 0, y: 300, width: 195, height: 300 });
        expect(rects.s3).toEqual({ x: 195, y: 300, width: 195, height: 300 });
        expect(cropsTiles).toBe(true);
    });

    test("a portrait stage that the source ratio already fits is not cropped", () => {
        // 3 stacked cells are 390x200, i.e. wider than 16:9. The tile is never stretched past the
        // source ratio, so it letterboxes horizontally exactly like a landscape stage does — and
        // the full height is used, which was the point.
        const { rects, cropsTiles } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(3),
        });
        expect(rects.s0).toEqual({ x: 17.5, y: 0, width: 355, height: 200 });
        expect(rects.s2).toEqual({ x: 17.5, y: 400, width: 355, height: 200 });
        expect(cropsTiles).toBe(false);
    });

    test("a portrait stage centers a last row it could not fill", () => {
        const { rects } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(5),
        });
        // Two columns, so the 5th tile is alone on its row: centered rather than left-aligned.
        expect(rects.s3.y).toBe(rects.s2.y);
        expect(rects.s4.y).toBeGreaterThan(rects.s3.y);
        expect(rects.s4.x).toBe((390 - rects.s4.width) / 2);
    });

    test("a portrait stage lays its sidebar along the bottom instead of the right edge", () => {
        const { rects } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "sb0", placement: SIDEBAR },
                { key: "sb1", placement: SIDEBAR },
            ],
        });
        // A 230px column would be well over a third of a phone: the main window keeps the whole
        // width and pays in height instead.
        expect(rects.main.x).toBe(0);
        expect(rects.main.width).toBe(390);
        expect(rects.main.height).toBe(600 - SIDEBAR_STRIP_HEIGHT);
        // The cards run left to right along the bottom edge, centered across the strip.
        expect(rects.sb0.y).toBe(rects.sb1.y);
        expect(rects.sb1.x).toBeGreaterThan(rects.sb0.x);
        expect(rects.sb0.y).toBeGreaterThan(rects.main.y + rects.main.height - 1);
        expect(rects.sb0.y + rects.sb0.height).toBeWithin(0, 601);
        // Same 16:9 card the narrow column would have given them, laid along the other axis.
        expect(rects.sb0.width).toBe(SIDEBAR_WIDTH_SMALL);
    });

    test("a portrait sidebar strip shrinks its cards rather than running off the stage", () => {
        const { rects } = computeLayout({
            width: 390,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                ...Array.from({ length: 5 }, (_, i) => ({ key: `sb${i}`, placement: SIDEBAR })),
            ],
        });
        expect(rects.sb0.width).toBe(390 / 5);
        expect(rects.sb4.x + rects.sb4.width).toBe(390);
        // The strip still reserves its full height, so a shrunken card is centered in it.
        expect(rects.main.height).toBe(600 - SIDEBAR_STRIP_HEIGHT);
    });

    test("a landscape stage keeps the source ratio and never crops", () => {
        // The portrait branch is gated on the stage box alone, so a landscape stage still gets
        // 16:9 tiles and letterboxes whatever it cannot fill.
        const { rects, cropsTiles } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(3),
        });
        expect(rects.s0).toEqual({ x: 0, y: 19, width: 500, height: 281 });
        expect(rects.s2).toEqual({ x: 250, y: 300, width: 500, height: 281 });
        expect(cropsTiles).toBe(false);
        // A sidebar narrowing the main area is not what makes a stage portrait.
        expect(
            computeLayout({
                width: 1000,
                height: 800,
                aspectRatio: 16 / 9,
                surfaces: [
                    { key: "main", placement: MAIN },
                    { key: "sb0", placement: SIDEBAR },
                    { key: "sb1", placement: SIDEBAR },
                ],
            }).cropsTiles
        ).toBe(false);
    });

    test("auto-tiled caps the grid at 3 columns", () => {
        const { rects } = computeLayout({
            width: 2000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(6),
            capColumnsAtThree: true,
        });
        // 3 columns x 2 rows of 533x300 tiles, centered.
        expect(rects.s0).toEqual({ x: 200.5, y: 0, width: 533, height: 300 });
        expect(rects.s2).toEqual({ x: 1266.5, y: 0, width: 533, height: 300 });
        expect(rects.s3).toEqual({ x: 200.5, y: 300, width: 533, height: 300 });
        expect(rects.s5).toEqual({ x: 1266.5, y: 300, width: 533, height: 300 });
    });

    test("a filled main card (compact) takes the whole main area width", () => {
        const { rects, stageHeight } = computeLayout({
            width: 800,
            height: 0,
            autoHeight: true,
            aspectRatio: 16 / 9,
            surfaces: [{ key: "main", placement: MAIN }],
            fillMainWidth: true,
        });
        expect(rects.main).toEqual({ x: 0, y: 0, width: 800, height: 450 });
        expect(stageHeight).toBe(450);
    });

    test("auto-height stage (compact chat window) sizes tiles from the width and reports its height", () => {
        const { rects, stageHeight } = computeLayout({
            width: 400,
            height: 0,
            autoHeight: true,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(3),
        });
        // 400px fits a single 320px-wide column: 3 stacked full-width tiles.
        expect(rects.s0).toEqual({ x: 0, y: 0, width: 400, height: 225 });
        expect(rects.s1).toEqual({ x: 0, y: 225, width: 400, height: 225 });
        expect(rects.s2).toEqual({ x: 0, y: 450, width: 400, height: 225 });
        expect(stageHeight).toBe(675);
    });

    test("an auto-height stage fits as many columns as the width allows", () => {
        const { rects, stageHeight } = computeLayout({
            width: 1000,
            height: 0,
            autoHeight: true,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
            minTileWidth: 320,
        });
        // 1000 / 320 = 3 columns. Maximizing the tile area against an unbounded height would
        // instead give a single 1000px-wide column, i.e. a 4x too tall stage.
        expect(rects.s0).toEqual({ x: 0.5, y: 0, width: 333, height: 187 });
        expect(rects.s2).toEqual({ x: 666.5, y: 0, width: 333, height: 187 });
        // The 4th tile is alone on its row: centered, like every other partial row.
        expect(rects.s3).toEqual({ x: 333.5, y: 187, width: 333, height: 187 });
        expect(stageHeight).toBe(374);
    });

    test("a stage that is not laid out yet is not mistaken for an auto-height one", () => {
        // Same collapsed measurement, but the stage does have a height of its own: the caller
        // (arrangeTiles) skips such a pass entirely, and the engine must not invent a grid from
        // the width either. Maximizing the area against height 0 yields empty tiles, never the
        // full-width single column that a stageHeight write would then lock in.
        const { rects, stageHeight } = computeLayout({
            width: 1600,
            height: 0,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
        });
        expect(rects.s0.width).toBe(0);
        expect(rects.s0.height).toBe(0);
        expect(stageHeight).toBe(undefined);
    });

    test("a stage with a height of its own produces no stageHeight", () => {
        const { stageHeight } = computeLayout({
            width: 800,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(2),
        });
        expect(stageHeight).toBe(undefined);
    });

    test("maxTileCount follows the column/row cap", () => {
        const { maxTileCount } = computeLayout({
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(9),
            minTileWidth: 320,
        });
        // 4 columns x 4 rows at 320px (1280 / 320 = 4; 720 / 180 = 4).
        expect(maxTileCount).toBe(16);
    });

    test("empty surfaces produce an empty layout", () => {
        const { rects, stageHeight, maxTileCount } = computeLayout({
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: [],
        });
        expect(rects).toEqual({});
        expect(stageHeight).toBe(undefined);
        expect(maxTileCount).toBeGreaterThan(0);
    });

    test("a synthetic surface (e.g. the 'more' indicator) reserves a tile slot", () => {
        const { rects } = computeLayout({
            width: 1000,
            height: 600,
            aspectRatio: 16 / 9,
            surfaces: [...mainSurfaces(3), { key: "__more__", placement: MAIN }],
        });
        // 4 tiles in a 2x2 grid of 500x281 tiles; the indicator gets the last slot.
        expect(rects.s0).toEqual({ x: 0, y: 19, width: 500, height: 281 });
        expect(rects.s2).toEqual({ x: 0, y: 300, width: 500, height: 281 });
        expect(rects.__more__).toEqual({ x: 500, y: 300, width: 500, height: 281 });
    });

    test("a sidebar wider than the stage never produces negative main geometry", () => {
        const { rects, stageHeight } = computeLayout({
            width: 100,
            height: 0,
            autoHeight: true,
            aspectRatio: 16 / 9,
            surfaces: [
                { key: "main", placement: MAIN },
                { key: "sb0", placement: SIDEBAR },
            ],
        });
        expect(rects.main.width).toBeWithin(0, 100);
        expect(rects.main.height).toBeWithin(0, 100);
        expect(rects.main.x).toBeWithin(0, 100);
        // The sidebar is drawn off-stage in this degenerate case, without crashing the layout.
        expect(rects.sb0.x + rects.sb0.width).toBe(100);
        expect(stageHeight).toBeWithin(0, 1000);
    });

    test("resize only changes the geometry of the same surfaces", () => {
        const small = computeLayout({
            width: 640,
            height: 360,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
        });
        const large = computeLayout({
            width: 1280,
            height: 720,
            aspectRatio: 16 / 9,
            surfaces: mainSurfaces(4),
        });
        expect(Object.keys(small.rects)).toEqual(Object.keys(large.rects));
        expect(small.rects.s0).not.toEqual(large.rects.s0);
    });
});
