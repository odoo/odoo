import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { formatDateTime } from "@web/core/l10n/dates";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";
const { DateTime } = luxon;

defineWebsiteModels();

test("opens DateTimePicker on focus, closes on blur", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").click();
    expect(".o_datetime_picker").toBeDisplayed();
    await contains(".options-container").click();
    expect(".o_datetime_picker").not.toBeDisplayed();
});

test("defaults to empty if undefined", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    expect(".we-bg-options-container input").toHaveValue("");
});

test("defaults to empty when invalid date provided", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("Invalid Date");
    expect(".we-bg-options-container input").toHaveValue("");
});

test("defaults to empty when no date is selected", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").click();
    await contains(".options-container").click();
    expect(".we-bg-options-container input").toHaveValue("");
});

test("defaults to default when invalid date provided", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" default="'now'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    const expectedDateTime = DateTime.now();

    await contains(".we-bg-options-container input").edit("Invalid Date");
    expect(".we-bg-options-container input").toHaveValue(formatDateTime(expectedDateTime));
});

test("defaults to empty (even with default) when no date is selected", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" default="'now'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").click();
    await contains(".options-container").click();
    expect(".we-bg-options-container input").toHaveValue("");
});

test("selects a date and properly applies it", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" default="'now'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    const expectedDateTime = DateTime.now().plus({ days: 1 });

    await contains(".we-bg-options-container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();
    await contains(".options-container").click();

    // To avoid indeterminism, don't check last digit of seconds
    const formattedDateTime = formatDateTime(expectedDateTime);
    expect(".we-bg-options-container input").toHaveValue(
        new RegExp(`^${formattedDateTime.slice(0, -1)}`)
    );

    // To avoid indeterminism, don't check last digit of the timestamp
    const timestamp = expectedDateTime.toUnixInteger().toString();
    expect(":iframe .test-options-target").toHaveAttribute(
        "data-date",
        new RegExp(`^${timestamp.slice(0, -1)}`)
    );
});

test("set a date to empty", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-date="666">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("");
    expect(".we-bg-options-container input").toHaveValue("");
    expect(":iframe .test-options-target").not.toHaveAttribute("data-date");
});
