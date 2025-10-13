import { beforeEach, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { queryAll } from "@odoo/hoot-dom";

defineWebsiteModels();

beforeEach(async () => {
    await setupWebsiteBuilder(
        `<div class="s_donation" data-name="Donation Button" data-donation-email="info@yourcompany.example.com" data-custom-amount="freeAmount" data-prefilled-options="true" data-descriptions="true" data-donation-amounts="[&quot;10&quot;]" data-minimum-amount="5" data-maximum-amount="100" data-slider-step="5" data-default-amount="25" data-snippet="s_donation_button" data-display-options="true">
        <form class="s_donation_form" action="/donation/pay" method="post" enctype="multipart/form-data">
            <span id="s_donation_description_inputs">
                <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" name="donation_descriptions" value="value1">
            </span>
            <div class="s_donation_prefilled_buttons my-4">
                <div class="s_donation_btn_description o_not_editable o_translate_mode_hidden">
                    <button class="s_donation_btn" type="button" data-donation-value="10">
                        <span class="s_donation_currency">$</span>10
                    </button>
                    <p class="s_donation_description">value1</p>
                </div>
                <div>
                    <span class="s_donation_btn s_donation_custom_btn">
                        <span class="s_donation_currency">$</span>
                        <input id="s_donation_amount_input" type="number" placeholder="Custom Amount" aria-label="Amount" min="5" style="max-width: 162px;">
                    </span>
                </div>
            </div>
            <a href="#" type="button" class="s_donation_donate_btn">Donate Now</a>
        </form>
    </div>`
    );
});

test("display/hide donation options", async () => {
    await contains(":iframe .s_donation").click();
    expect(queryAll(":iframe .s_donation_btn")).not.toBeEmpty();
    expect(":iframe .s_donation_donate_btn").toBeVisible();
    await contains("div:has(> span:contains('Display Options')) + div input").click();
    expect(queryAll(":iframe .s_donation_btn")).toBeEmpty();
    expect(":iframe .s_donation_donate_btn").toBeVisible();
    await contains("div:has(> span:contains('Display Options')) + div input").click();
    expect(queryAll(":iframe .s_donation_btn")).not.toBeEmpty();
});

test("display/hide prefilled options", async () => {
    await contains(":iframe .s_donation").click();
    expect(":iframe .s_donation_prefilled_buttons").not.toBeEmpty();
    await contains("div:has(> span:contains('Pre-filled Options')) + div input").click();
    expect(":iframe .s_donation_prefilled_buttons").toHaveInnerHTML("");
    expect(":iframe .s_donation_range_slider_wrap").toBeVisible();
    await contains("div:has(> span:contains('Pre-filled Options')) + div input").click();
    expect(":iframe .s_donation_prefilled_buttons").not.toBeEmpty();
});

test("display/hide donation descriptions options", async () => {
    await contains(":iframe .s_donation").click();
    expect(queryAll(":iframe .s_donation_btn_description")).not.toBeEmpty();
    await contains("div:has(> span:contains('Descriptions')) + div input").click();
    expect(queryAll(":iframe .s_donation_btn_description")).toBeEmpty();
    await contains("div:has(> span:contains('Descriptions')) + div input").click();
    expect(queryAll(":iframe .s_donation_btn_description")).not.toBeEmpty();
});
