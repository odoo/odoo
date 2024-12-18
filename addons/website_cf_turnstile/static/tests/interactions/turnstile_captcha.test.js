import { describe, expect, test } from "@odoo/hoot";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { session } from "@web/session";

setupInteractionWhiteList("website_cf_turnstile.turnstile_captcha");
describe.current.tags("interaction_dev");

test("turnstile captcha gets added to a data-captcha form", async () => {
    session.turnstile_site_key = "test";
    const { core, el } = await startInteractions(`
        <form data-captcha="test">
            <input name="test"/>
            <button type="submit">Submit</a>
        </form>
    `);
    expect(core.interactions.length).toBe(1);
    let scriptEls = el.querySelectorAll("form script.s_turnstile");
    expect(scriptEls.length).toBe(2);
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions.length).toBe(0);
    scriptEls = el.querySelectorAll("form script.s_turnstile");
    expect(scriptEls.length).toBe(0);
});
