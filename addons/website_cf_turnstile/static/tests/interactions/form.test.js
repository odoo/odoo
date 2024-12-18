import { describe, expect, test } from "@odoo/hoot";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { session } from "@web/session";

setupInteractionWhiteList("website.form");
describe.current.tags("interaction_dev");

test("turnstile captcha gets added to form snippets", async () => {
    session.turnstile_site_key = "test";
    const { core, el } = await startInteractions(`
        <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
            </form>
        </section>
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
