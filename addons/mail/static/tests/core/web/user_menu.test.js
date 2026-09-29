import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, getFixture, test, waitFor } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { defineParams } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("User menu shows im_status icon", async () => {
    await start();
    await waitFor(".o_user_menu .o-mail-ImStatus");
});

/** User menu avatar icon placement, with centers in avatar units (from 0 to 32). */
async function getIconPlacement() {
    // mask is fitted to the icon once it is laid out
    await waitFor(".o_user_menu .o-mail-DiscussAvatar mask use[transform]");
    const avatar = queryOne(".o_user_menu .o-mail-DiscussAvatar");
    const iconBox = queryOne(".o-mail-DiscussAvatar-icon", { root: avatar });
    const icon = queryOne(".o-mail-ImStatus", { root: iconBox });
    // the cutout is the masked glyph, or a rect when there is no glyph
    const hole = queryOne("mask :is(use, rect[fill=black])", { root: avatar });
    const avatarRect = avatar.getBoundingClientRect();
    const iconRect = icon.getBoundingClientRect();
    const toAvatarUnits = 32 / avatarRect.width;
    // mask is in CSS pixels of the avatar
    const maskToAvatarUnits = 32 / avatar.offsetWidth;
    // the glyph is the `::before` of the icon, always LTR so at its left
    const glyphWidth = parseFloat(getComputedStyle(icon, "::before").width);
    let holeCenter;
    if (hole.tagName === "use") {
        // the masked glyph starts at its translation and is vertically centered on it
        const holeMatrix = hole.transform.baseVal.consolidate().matrix;
        holeCenter = { x: holeMatrix.e + (holeMatrix.a * glyphWidth) / 2, y: holeMatrix.f };
    } else {
        holeCenter = {
            x: hole.x.baseVal.value + hole.width.baseVal.value / 2,
            y: hole.y.baseVal.value + hole.height.baseVal.value / 2,
        };
    }
    return {
        iconCenter: {
            x:
                (iconRect.left - avatarRect.left) * toAvatarUnits +
                (glyphWidth * (iconRect.width / icon.offsetWidth) * toAvatarUnits) / 2,
            y: (iconRect.top - avatarRect.top + iconRect.height / 2) * toAvatarUnits,
        },
        holeCenter: { x: holeCenter.x * maskToAvatarUnits, y: holeCenter.y * maskToAvatarUnits },
        isIconMirrored: new DOMMatrix(getComputedStyle(iconBox).transform).a < 0,
    };
}

test("user menu IM status is on the bottom-right corner", async () => {
    await start();
    const { iconCenter, holeCenter, isIconMirrored } = await getIconPlacement();
    expect(holeCenter.x).toBeGreaterThan(16);
    expect(holeCenter.y).toBeGreaterThan(16);
    expect(iconCenter.x).toBeCloseTo(holeCenter.x, { margin: 1 });
    expect(iconCenter.y).toBeCloseTo(holeCenter.y, { margin: 1 });
    expect(isIconMirrored).toBe(false);
});

test("user menu IM status is on the bottom-left corner in RTL", async () => {
    defineParams({ lang_parameters: { direction: "rtl" } });
    // done by the rtl assets bundle, not loaded in tests
    getFixture().style.direction = "rtl";
    await start();
    const { iconCenter, holeCenter, isIconMirrored } = await getIconPlacement();
    expect(holeCenter.x).toBeLessThan(16);
    expect(holeCenter.y).toBeGreaterThan(16);
    expect(iconCenter.x).toBeCloseTo(holeCenter.x, { margin: 1 });
    expect(iconCenter.y).toBeCloseTo(holeCenter.y, { margin: 1 });
    expect(isIconMirrored).toBe(false);
});
