import { click, describe, edit, expect, test } from "@odoo/hoot";
import { keyUp, pointerDown, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList(["web.caps_lock_warning", "web.show_password"]);

describe.current.tags("interaction_dev");

const template = `
    <div class="mb-3 field-password pt-2 o_caps_lock_warning">
        <label for="password" class="form-label">Password</label>
        <div class="input-group mb-1">
            <input type="password" name="password" id="password"
            class="form-control"/>
        </div>
    </div>`;

test("caps_lock_warning is started when there is a presence of password input field inside `.o_caps_lock_warning`", async () => {
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);
});

test("caps lock alert is displayed when CapsLock is turned on", async () => {
    await startInteractions(template);
    await pointerDown(queryOne("#password"));
    await keyUp("a");
    await keyUp("CapsLock");
    expect(".o_caps_lock_warning_text").toBeVisible();
});

test("caps lock alert is displayed even when CapsLock has been pressed while not focused on the password field", async () => {
    const loginField = `
        <div class="mb-3 field-login">
            <label for="login" class="form-label">Email</label>
            <div class="input-group mb-1">
                <input type="text" name="login" id="login"
                class="form-control"/>
            </div>
        </div>`;
    await startInteractions(loginField + template);
    await pointerDown(queryOne("#login"));
    await keyUp("a");
    await keyUp("CapsLock");
    await pointerDown(queryOne("#password"));
    expect(".o_caps_lock_warning_text").toBeVisible();
    await keyUp("CapsLock");
    expect(".o_caps_lock_warning_text").not.toBeVisible();
});

test("show the password, type something, and then hide the password back, caps lock alert should be available", async () => {
    const templateWithEye = `
        <div class="mb-3 field-password pt-2 o_caps_lock_warning">
            <label for="password" class="form-label">Password</label>
            <div class="input-group mb-1">
                <input type="password" name="password" id="password"
                class="form-control"/>
                <button type="button" class="btn btn-sm border o_show_password">
                    <i class="fa fa-eye"></i>
                </button>
            </div>
        </div>`;
    await startInteractions(templateWithEye);
    await click("button.o_show_password");
    await click("#password");
    await edit("secureinfo");
    await click("button.o_show_password");
    await click("#password");
    await keyUp("CapsLock");
    expect(".o_caps_lock_warning_text").toBeVisible();
});
