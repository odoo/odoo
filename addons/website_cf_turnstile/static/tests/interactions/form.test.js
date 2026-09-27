import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { session } from "@web/session";
import { patchTurnStile } from "@website_cf_turnstile/../tests/helpers";

patchTurnStile();

setupInteractionWhiteList("website.form");
describe.current.tags("interaction_dev");

test("turnstile captcha gets added to form snippets", async () => {
    session.turnstile_site_key = "test";
    const { core } = await startInteractions(`
        <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
            </form>
        </section>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("form script.s_turnstile")).toHaveLength(1);
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
    expect(queryAll("form script.s_turnstile")).toHaveLength(0);
});
