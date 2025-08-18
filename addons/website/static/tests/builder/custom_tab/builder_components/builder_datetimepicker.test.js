import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";
const { DateTime } = luxon;

const TIME_TOLERANCE = 2;

defineWebsiteModels();

// To avoid indeterminism in tests, we use a tolerance
function isExpectedDateTime({
    dateString,
    expectedDateTime = DateTime.now(),
    tolerance = TIME_TOLERANCE,
}) {
    const actualTimestamp = DateTime.fromFormat(dateString, "MM/dd/yyyy HH:mm:ss").toUnixInteger();
    const expectedTimestamp = expectedDateTime.toUnixInteger();
    const difference = Math.abs(actualTimestamp - expectedTimestamp);
    return difference <= tolerance;
}

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
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    let dateString = queryOne(".we-bg-options-container input.o-hb-input-base").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);

    await contains(".we-bg-options-container input.form-check-input").click();
    dateString = queryOne(".we-bg-options-container input.o-hb-input-base").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);
});

test("defaults to last one when invalid date provided", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-date="1554219400">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".we-bg-options-container input").toHaveValue("04/02/2019 16:36:40");

    await contains(".we-bg-options-container input").edit("INVALID DATE");
    expect(".we-bg-options-container input").toHaveValue("04/02/2019 16:36:40");

    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    await contains(".we-bg-options-container input").edit("INVALID DATE");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");
});

test("defaults to last one when invalid date provided (date)", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker type="'date'" dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-date="1554219400">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".we-bg-options-container input").toHaveValue("04/02/2019");

    await contains(".we-bg-options-container input").edit("INVALID DATE");
    expect(".we-bg-options-container input").toHaveValue("04/02/2019");

    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019");

    await contains(".we-bg-options-container input").edit("INVALID DATE");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019");
});

test("defaults to now when no date is selected", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    await contains(".we-bg-options-container input").edit("");
    const dateString = queryOne(".we-bg-options-container input").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);
});

test("defaults to now when clicking on clear button", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("04/01/2019 10:00:00");
    expect(".we-bg-options-container input").toHaveValue("04/01/2019 10:00:00");

    for (let i = 0; i < 3; i++) {
        await contains(".we-bg-options-container input").click();
        await contains(".o_datetime_buttons button .fa-eraser").click();
        await contains(".options-container").click();
        const dateString = queryOne(".we-bg-options-container input").value;
        expect(isExpectedDateTime({ dateString })).toBe(true);
    }
});

test("selects a date and properly applies it", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();
    await contains(".options-container").click();

    const dateString = queryOne(".we-bg-options-container input").value;
    const expectedDateTime = DateTime.now().plus({ days: 1 });
    expect(isExpectedDateTime({ dateString, expectedDateTime })).toBe(true);

    const expectedDateTimestamp = expectedDateTime.toUnixInteger();
    const dateTimestamp = parseFloat(queryOne(":iframe .test-options-target").dataset.date);
    expect(Math.abs(expectedDateTimestamp - dateTimestamp)).toBeLessThan(TIME_TOLERANCE);
});

test("selects a date and synchronize the input field, while still in preview", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();

    const dateString = queryOne(".we-bg-options-container input").value;
    const expectedDateTime = DateTime.now().plus({ days: 1 });
    expect(isExpectedDateTime({ dateString, expectedDateTime })).toBe(true);

    const expectedDateTimestamp = expectedDateTime.toUnixInteger();
    const dateTimestamp = parseFloat(queryOne(":iframe .test-options-target").dataset.date);
    expect(Math.abs(expectedDateTimestamp - dateTimestamp)).toBeLessThan(TIME_TOLERANCE);
});

test("edit a date with the datetime picker should correctly apply the mutation", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupWebsiteBuilder(`
        <div class="test-options-target" data-date="1554219400">b</div>
        <div class="another-target">c</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").click();
    await contains(".o_date_item_cell:contains('9')").click();
    expect(".we-bg-options-container input").toHaveValue("04/09/2019 16:36:40");

    await contains(".o_datetime_buttons .btn:contains('apply')").click();
    expect(".we-bg-options-container input").toHaveValue("04/09/2019 16:36:40");
    expect(":iframe .test-options-target").toHaveAttribute("data-date", "1554824200");

    // refresh the Edit tab
    await contains(":iframe .another-target").click();
    await contains(":iframe .test-options-target").click();
    expect(".we-bg-options-container input").toHaveValue("04/09/2019 16:36:40");
    expect(":iframe .test-options-target").toHaveAttribute("data-date", "1554824200");
});
