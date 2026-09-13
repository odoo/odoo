// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    defineModels,
    getService,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { _makeUser, user } from "@web/core/user";
import { DENSITIES, nextDensity } from "@web/webclient/density/density_service";
import { DensityToggle } from "@web/webclient/density/density_toggle";

const { ResCompany, ResPartner, ResUsers, ResUsersSettings } = webModels;

defineModels([ResCompany, ResPartner, ResUsers, ResUsersSettings]);

describe.current.tags("desktop");

function seedUserSettings() {
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1 } }));
    onRpc(
        "res.users.settings",
        "set_res_users_settings",
        ({ kwargs }) => kwargs.new_settings,
    );
}

test("nextDensity walks the declared order and wraps", () => {
    expect(DENSITIES.map(nextDensity)).toEqual([...DENSITIES.slice(1), DENSITIES[0]]);
});

test("nextDensity is a full cycle over every density", () => {
    const seen = [];
    let density = DENSITIES[0];
    for (let i = 0; i < DENSITIES.length; i++) {
        seen.push(density);
        density = nextDensity(density);
    }
    expect(seen).toEqual(DENSITIES);
    expect(density).toBe(DENSITIES[0]);
});

test("cycling applies the body class and records the cookie", async () => {
    seedUserSettings();
    await makeMockEnv();
    const density = getService("density");
    expect(density.current).toBe("default");
    expect(document.body).not.toHaveClass("o-density-compact");

    await density.cycle();
    expect(density.current).toBe("compact");
    expect(document.body).toHaveClass("o-density-compact");
    expect(cookie.get("content_density")).toBe("compact");

    await density.cycle();
    expect(density.current).toBe("condensed");
    expect(document.body).toHaveClass("o-density-condensed");
    expect(document.body).not.toHaveClass("o-density-compact");

    await density.cycle();
    expect(density.current).toBe("default");
    expect(document.body).not.toHaveClass("o-density-condensed");
});

test("an unknown density is refused", async () => {
    await makeMockEnv();
    const density = getService("density");
    await density.set("enormous");
    expect(density.current).toBe("default");
});

test("the systray toggle tracks a density set from elsewhere", async () => {
    seedUserSettings();
    await makeMockEnv();
    const toggle = await mountWithCleanup(DensityToggle);
    const compactIcon = toggle.icon;

    await getService("density").set("condensed");
    await animationFrame();

    expect(toggle.icon).not.toBe(compactIcon);
    expect(toggle.icon).toBe("fa-solid fa-bars");
    expect(toggle.title).toInclude("Condensed");
    expect(toggle.title).toInclude("Default");
});

test("a failed persist rolls the density back instead of rejecting", async () => {
    await makeMockEnv();
    const density = getService("density");
    patchWithCleanup(user, {
        setUserSettings: async () => {
            throw new Error("offline");
        },
    });

    let rejection = null;
    await density.set("compact").catch((error) => (rejection = error));

    expect(rejection).toBe(null);
    expect(density.current).toBe("default");
    expect(cookie.get("content_density")).toBe("default");
    expect(document.body.classList.contains("o-density-compact")).toBe(false);
});

test("a stale failed persist does not clobber a density chosen since", async () => {
    await makeMockEnv();
    const density = getService("density");
    /** @type {(() => void)[]} */
    const pending = [];
    patchWithCleanup(user, {
        setUserSettings: (_key, value) =>
            new Promise((resolve, reject) => {
                pending.push(() =>
                    value === "compact" ? reject(new Error("offline")) : resolve(),
                );
            }),
    });

    const first = density.set("compact");
    const second = density.set("condensed");
    expect(density.current).toBe("condensed");

    await Promise.resolve();
    pending[0]();
    await first;
    await Promise.resolve();
    pending[1]();
    await Promise.all([first, second]);

    expect(density.current).toBe("condensed");
    expect(document.body.classList.contains("o-density-condensed")).toBe(true);
});

test("two failing persists do not strand a density the server never received", async () => {
    await makeMockEnv();
    const density = getService("density");
    /** @type {(() => void)[]} */
    const pending = [];
    patchWithCleanup(user, {
        setUserSettings: () =>
            new Promise((_resolve, reject) => {
                pending.push(() => reject(new Error("offline")));
            }),
    });

    const first = density.set("compact");
    const second = density.set("condensed");
    await Promise.resolve();
    pending[0]();
    await first;
    await Promise.resolve();
    pending[1]();
    await Promise.all([first, second]);

    expect(density.current).toBe("default");
    expect(document.body.classList.contains("o-density-compact")).toBe(false);
});

test("a queued failure restores the last successful density write", async () => {
    await makeMockEnv();
    const density = getService("density");
    const finish = new Deferred();
    patchWithCleanup(user, {
        setUserSettings: async (_key, value) => {
            expect.step(value);
            if (value === "compact") {
                await finish;
            } else {
                throw new Error("refused");
            }
        },
    });
    const first = density.set("compact");
    const second = density.set("condensed");
    await Promise.resolve();
    expect.verifySteps(["compact"]);
    expect(density.current).toBe("condensed");
    finish.resolve();
    await Promise.all([first, second]);
    expect.verifySteps(["condensed"]);
    expect(density.current).toBe("compact");
    expect(cookie.get("content_density")).toBe("compact");
});
