import {
    click,
    defineMailModels,
    hover,
    insertText,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, getFixture, test, waitFor } from "@odoo/hoot";
import { animationFrame, press, queryOne } from "@odoo/hoot-dom";
import { defineParams, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("User menu shows im_status icon", async () => {
    await start();
    await waitFor(".o_user_menu .o-mail-ImStatus");
});

/** User menu avatar icon placement, with horizontal centers in avatar units (from 0 to 32). */
function getIconPlacement() {
    const avatar = queryOne(".o_user_menu .o-mail-DiscussAvatar");
    const iconBox = queryOne("g foreignObject", { root: avatar });
    const icon = queryOne(".o-mail-ImStatus", { root: iconBox });
    // the cutout is the masked glyph, or a rect when there is no glyph
    const hole = queryOne("mask :is(use, rect[fill=black])", { root: avatar });
    const avatarRect = avatar.getBoundingClientRect();
    const iconRect = icon.getBoundingClientRect();
    const toAvatarUnits = 32 / avatarRect.width;
    // the glyph is the `::before` of the icon, always LTR so at its left
    const glyphWidth =
        parseFloat(getComputedStyle(icon, "::before").width) *
        (iconRect.width / icon.offsetWidth) *
        toAvatarUnits;
    const holeWidth = hole.tagName === "use" ? glyphWidth : hole.width.baseVal.value;
    const holeMatrix = hole.transform.baseVal.consolidate().matrix;
    return {
        iconCenter: (iconRect.left - avatarRect.left) * toAvatarUnits + glyphWidth / 2,
        holeCenter: holeMatrix.e + (holeMatrix.a * holeWidth) / 2,
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

test("set status message writes field on user", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_user_menu");
    await hover(".dropdown-menu a:has(.o-mail-ImStatus)");
    await insertText(
        ".o-mail-ImStatusDropdown input[placeholder='Set a status message']",
        "I am busy"
    );
    await animationFrame();
    expect(
        pyEnv["res.users"].read([serverState.userId], ["status_message"])[0].status_message
    ).toBe("I am busy");
});

test("Enter in the status message keeps the IM status", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "busy" });
    await start();
    await click(".o_user_menu");
    await hover(".dropdown-menu a:has(.o-mail-ImStatus)");
    await waitFor(".dropdown-item.active:contains('Do Not Disturb'):count(1)");
    await insertText(
        ".o-mail-ImStatusDropdown input[placeholder='Set a status message']",
        "In a meeting"
    );
    await press("Enter");
    await animationFrame();
    await waitFor(".dropdown-item.active:contains('Do Not Disturb'):count(1)");
    expect(
        pyEnv["res.users"].read([serverState.userId], ["status_message"])[0].status_message
    ).toBe("In a meeting");
});
