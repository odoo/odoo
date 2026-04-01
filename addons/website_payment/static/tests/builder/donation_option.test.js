import { beforeEach, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { queryAll } from "@odoo/hoot-dom";

defineWebsiteModels();

beforeEach(async () => {
    await setupWebsiteBuilderWithSnippet("s_donation");
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
