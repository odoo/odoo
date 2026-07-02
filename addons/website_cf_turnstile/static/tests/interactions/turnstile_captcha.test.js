import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { session } from "@web/session";
import { patchTurnStile } from "@website_cf_turnstile/../tests/helpers";

patchTurnStile();

setupInteractionWhiteList("website_cf_turnstile.turnstile_captcha");
describe.current.tags("interaction_dev");

beforeEach(() => {
    history.pushState({}, "", window.location.pathname);
});

test("turnstile captcha gets added to a data-captcha form", async () => {
    session.turnstile_site_key = "test";
    const { core } = await startInteractions(`
        <form data-captcha="test">
            <input name="test"/>
            <button type="submit">Submit</a>
        </form>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("form script.s_turnstile")).toHaveLength(1);
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
    expect(queryAll("form script.s_turnstile")).toHaveLength(0);
});

test("turnstile appearance defaults to interaction-only", async () => {
    session.turnstile_site_key = "test";
    const { core } = await startInteractions(`
        <form data-captcha="test">
            <input name="test"/>
            <button type="submit">Submit</a>
        </form>
    `);
    expect(queryOne("form .cf-turnstile")).toHaveAttribute("data-appearance", "interaction-only");
    core.stopInteractions();
});

test("turnstile appearance is always with ?cf=show", async () => {
    history.pushState({}, "", `${window.location.pathname}?cf=show`);
    session.turnstile_site_key = "test";
    const { core } = await startInteractions(`
        <form data-captcha="test">
            <input name="test"/>
            <button type="submit">Submit</a>
        </form>
    `);
    expect(queryOne("form .cf-turnstile")).toHaveAttribute("data-appearance", "always");
    core.stopInteractions();
});
