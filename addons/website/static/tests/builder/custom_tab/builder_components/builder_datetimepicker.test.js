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
    expect(".o_datetime_picker").not.toHaveCount();
});

test("defaults to now if undefined", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    const expectedDateTime = DateTime.now();
    expect(".we-bg-options-container input.o-hb-input-base").toHaveValue(
        formatDateTime(expectedDateTime)
    );
    await contains(".we-bg-options-container input.form-check-input").click();
    expect(".we-bg-options-container input.o-hb-input-base").toHaveValue(
        formatDateTime(expectedDateTime)
    );
});

test("defaults to last one when invalid date provided", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    await contains(".we-bg-options-container input").edit("INVALID DATE");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");
});

test("defaults to now when no date is selected", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    const expectedDateTime = DateTime.now();
    await contains(".we-bg-options-container input").edit("");
    expect(".we-bg-options-container input").toHaveValue(formatDateTime(expectedDateTime));
});

test("defaults to now when clicking on clear button", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    await contains(".we-bg-options-container input").click();
    await contains(".o_datetime_buttons button .fa-eraser").click();
    await contains(".options-container").click();
    const expectedDateTime = DateTime.now();
    expect(".we-bg-options-container input").toHaveValue(formatDateTime(expectedDateTime));
});

test("selects a date and properly applies it", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
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

test("selects a date and synchronize the input field, while still in preview", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    const expectedDateTime = DateTime.now().plus({ days: 1 });

    await contains(".we-bg-options-container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();

    const formattedDateTime = formatDateTime(expectedDateTime);
    expect(".we-bg-options-container input").toHaveValue(formattedDateTime);

    const timestamp = expectedDateTime.toUnixInteger().toString();
    expect(":iframe .test-options-target").toHaveAttribute("data-date", timestamp);
});
