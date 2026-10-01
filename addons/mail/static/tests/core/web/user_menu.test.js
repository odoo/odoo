import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { defineParams } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

/** User menu avatar icon placement, with horizontal centers in avatar units (from 0 to 32). */
function getIconPlacement() {
    const avatar = queryOne(".o_user_menu .o-mail-DiscussAvatar");
    const avatarRect = avatar.getBoundingClientRect();
    const iconBox = queryOne(".o_user_menu .o-mail-DiscussAvatar g foreignObject");
    const icon = queryOne(".o-mail-ImStatus", { root: iconBox });
    const iconRect = icon.getBoundingClientRect();
    // the glyph is the `::before` of the icon, at its inline start
    const glyphWidth =
        (parseFloat(getComputedStyle(icon, "::before").width) * iconRect.width) / icon.offsetWidth;
    const glyphLeft =
        getComputedStyle(icon).direction === "rtl" ? iconRect.right - glyphWidth : iconRect.left;
    const hole = queryOne(".o_user_menu .o-mail-DiscussAvatar mask rect[color=black]");
    const holeMatrix = hole.transform.baseVal.consolidate().matrix;
    return {
        iconCenter: ((glyphLeft + glyphWidth / 2 - avatarRect.left) / avatarRect.width) * 32,
        holeCenter: holeMatrix.e + (holeMatrix.a * hole.width.baseVal.value) / 2,
        isIconMirrored: iconBox.getScreenCTM().a < 0,
    };
}

test("user menu IM status is on the bottom-right corner", async () => {
    await start();
    const { iconCenter, holeCenter, isIconMirrored } = getIconPlacement();
    expect(holeCenter).toBeGreaterThan(16);
    expect(iconCenter).toBeCloseTo(holeCenter, { margin: 1 });
    expect(isIconMirrored).toBe(false);
});

test("user menu IM status is on the bottom-left corner in RTL", async () => {
    defineParams({ lang_parameters: { direction: "rtl" } });
    // done by the rtl assets bundle, not loaded in tests
    getFixture().style.direction = "rtl";
    await start();
    const { iconCenter, holeCenter, isIconMirrored } = getIconPlacement();
    expect(holeCenter).toBeLessThan(16);
    expect(iconCenter).toBeCloseTo(holeCenter, { margin: 1 });
    expect(isIconMirrored).toBe(false);
});
