import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { keyDown, queryOne, pointerDown } from "@odoo/hoot-dom";

setupInteractionWhiteList("web.caps_lock_warning");

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
    await keyDown("CapsLock");
    expect(".o_caps_lock_warning_text").toBeVisible();
});
