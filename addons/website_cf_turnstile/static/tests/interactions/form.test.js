import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { session } from "@web/session";
import { startInteractionsWithSnippet } from "@website/../tests/interactions/helpers";
import { patchTurnStile } from "@website_cf_turnstile/../tests/helpers";

patchTurnStile();

setupInteractionWhiteList("website.form");
describe.current.tags("interaction_dev");

test("turnstile captcha gets added to form snippets", async () => {
    session.turnstile_site_key = "test";
    const { core } = await startInteractionsWithSnippet("s_website_form");
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("form script.s_turnstile")).toHaveLength(1);
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
    expect(queryAll("form script.s_turnstile")).toHaveLength(0);
});
