import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { onRpc } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.form");
describe.current.tags("interaction_dev");

test("only checkout form submits via main button", async () => {
    onRpc("/website/form/shop.sale.order", async (a) => {
        expect.step("checkoutForm");
    });
    onRpc("/website/form/mail.mail", async (a) => {
        expect.step("customForm");
    });

    await startInteractions(`
        <div id="wrapwrap">
            <section class="s_website_form">
                <form action="/website/form/" data-model_name="mail.mail" data-force_action="shop.sale.order" data-success-mode="nothing">
                    <input type="hidden" name="email_to" value="test@test.com"/>
                    <input type="hidden" name="name" value="checkout"/>
                    <span id="s_website_form_result"></span>
                </form>
            </section>
            <section class="s_website_form">
                <form action="/website/form/" data-model_name="mail.mail" data-success-mode="nothing">
                    <input type="hidden" name="email_to" value="test@test.com"/>
                    <input type="hidden" name="name" value="custom"/>
                    <span id="s_website_form_result"></span>
                </form>
            </section>
            <button name="website_sale_main_button">Checkout</button>
        </div>
    `);

    await click('[name="website_sale_main_button"]');
    expect.verifySteps(["checkoutForm"]);
});
