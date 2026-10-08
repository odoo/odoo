import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
const { DateTime } = luxon;

describe.current.tags("desktop");

const TIME_TOLERANCE = 2;

// To avoid indeterminism in tests, we use a tolerance
function isExpectedDateTime({
    dateString,
    expectedDateTime = DateTime.now(),
    tolerance = TIME_TOLERANCE,
}) {
    const actualTimestamp = DateTime.fromFormat(dateString, "MM/dd/yyyy HH:mm").toUnixInteger();
    const expectedTimestamp = 60 * Math.floor(expectedDateTime.toUnixInteger() / 60);
    const difference = Math.abs(actualTimestamp - expectedTimestamp);
    return difference <= tolerance;
}

test("opens DateTimePicker on focus, closes on blur", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".o_hb_bg_options_container input").click();
    expect(".o_datetime_picker").toBeDisplayed();
    await contains(".o_hb_options_container").click();
    expect(".o_datetime_picker").not.toHaveCount();
});

test("defaults to now if undefined", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    let dateString = queryOne(".o_hb_bg_options_container input.o_hb_input_base").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);

    await contains(".o_hb_bg_options_container input.form-check-input").click();
    dateString = queryOne(".o_hb_bg_options_container input.o_hb_input_base").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);
});

test("defaults to last one when invalid date provided", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target" data-date="1554219400">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_bg_options_container input").toHaveValue("04/02/2019 16:36");

    await contains(".o_hb_bg_options_container input").edit("INVALID DATE");
    expect(".o_hb_bg_options_container input").toHaveValue("04/02/2019 16:36");

    await contains(".o_hb_bg_options_container input").edit("04/01/2019 10:00");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019 10:00");

    await contains(".o_hb_bg_options_container input").edit("INVALID DATE");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019 10:00");
});

test("defaults to last one when invalid date provided (date)", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker type="'date'" dataAttributeAction="'date'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target" data-date="1554219400">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_bg_options_container input").toHaveValue("04/02/2019");

    await contains(".o_hb_bg_options_container input").edit("INVALID DATE");
    expect(".o_hb_bg_options_container input").toHaveValue("04/02/2019");

    await contains(".o_hb_bg_options_container input").edit("04/01/2019 10:00");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019");

    await contains(".o_hb_bg_options_container input").edit("INVALID DATE");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019");
});

test("defaults to now when no date is selected", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".o_hb_bg_options_container input").edit("04/01/2019 10:00");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019 10:00");

    await contains(".o_hb_bg_options_container input").edit("");
    const dateString = queryOne(".o_hb_bg_options_container input").value;
    expect(isExpectedDateTime({ dateString })).toBe(true);
});

test("defaults to now when clicking on clear button", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".o_hb_bg_options_container input").edit("04/01/2019 10:00");
    expect(".o_hb_bg_options_container input").toHaveValue("04/01/2019 10:00");

    for (let i = 0; i < 3; i++) {
        await contains(".o_hb_bg_options_container input").click();
        await contains(".o_datetime_buttons button [data-icon='ink_eraser']").click();
        await contains(".o_hb_options_container").click();
        const dateString = queryOne(".o_hb_bg_options_container input").value;
        expect(isExpectedDateTime({ dateString })).toBe(true);
    }
});

test("selects a date and properly applies it", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".o_hb_bg_options_container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();
    await contains(".o_hb_options_container").click();

    const dateString = queryOne(".o_hb_bg_options_container input").value;
    const expectedDateTime = DateTime.now().plus({ days: 1 });
    expect(isExpectedDateTime({ dateString, expectedDateTime })).toBe(true);

    const expectedDateTimestamp = expectedDateTime.toUnixInteger();
    const dateTimestamp = parseFloat(queryOne(":iframe .test-options-target").dataset.date);
    expect(Math.abs(expectedDateTimestamp - dateTimestamp)).toBeLessThan(TIME_TOLERANCE);
});

test("selects a date and synchronize the input field, while still in preview", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'" acceptEmptyDate="false"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".o_hb_bg_options_container input").click();
    await contains(".o_date_item_cell.o_today + .o_date_item_cell").click();

    const dateString = queryOne(".o_hb_bg_options_container input").value;
    const expectedDateTime = DateTime.now().plus({ days: 1 });
    expect(isExpectedDateTime({ dateString, expectedDateTime })).toBe(true);

    const expectedDateTimestamp = expectedDateTime.toUnixInteger();
    const dateTimestamp = parseFloat(queryOne(":iframe .test-options-target").dataset.date);
    expect(Math.abs(expectedDateTimestamp - dateTimestamp)).toBeLessThan(TIME_TOLERANCE);
});

test("edit a date with the datetime picker should correctly apply the mutation", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker dataAttributeAction="'date'"/>`,
    });
    await setupHTMLBuilder(`
        <div class="test-options-target" data-date="1554219400">b</div>
        <div class="another-target">c</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".o_hb_bg_options_container input").click();
    await contains(".o_date_item_cell:contains('9')").click();
    expect(".o_hb_bg_options_container input").toHaveValue("04/09/2019 16:36");

    await contains(".o_datetime_buttons .btn:contains('apply')").click();
    expect(".o_hb_bg_options_container input").toHaveValue("04/09/2019 16:36");
    expect(":iframe .test-options-target").toHaveAttribute("data-date", "1554824160");

    // refresh the Edit tab
    await contains(":iframe .another-target").click();
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_bg_options_container input").toHaveValue("04/09/2019 16:36");
    expect(":iframe .test-options-target").toHaveAttribute("data-date", "1554824160");
});

test("toggles today as a relative date", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderDateTimePicker type="'date'" dataAttributeAction="'date'" allowRelativeDate="true"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    const inputSelector = ".o_hb_bg_options_container input.o_hb_input_base";
    const todayButtonSelector = ".o_hb_bg_options_container button:has([data-icon='today'])";

    await contains(inputSelector).edit("01/01/2025");
    await waitFor(":iframe .test-options-target[data-date]");
    const dateTimestamp = queryOne(":iframe .test-options-target").dataset.date;
    expect(inputSelector).toHaveValue("01/01/2025");

    await contains(todayButtonSelector).click();
    await waitFor(":iframe .test-options-target[data-date='today']");
    await waitFor(`${inputSelector}:disabled`);
    expect(inputSelector).toHaveValue("Today");
    expect(todayButtonSelector).toHaveClass("active");

    await contains(todayButtonSelector).click();
    await waitFor(`:iframe .test-options-target[data-date='${dateTimestamp}']`);
    await waitFor(`${inputSelector}:not(:disabled)`);
    expect(inputSelector).toHaveValue("01/01/2025");
});
