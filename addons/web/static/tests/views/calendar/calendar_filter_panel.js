/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { click, triggerEvent } from "../../helpers/utils";
import { makeEnv, makeFakeModel, mountComponent } from "./calendar_helpers";

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarFilterPanel, env, {
        model,
        ...props,
    });
}

QUnit.module("CalendarFilterPanel");

QUnit.skipWOWL("render filter panel", async (assert) => {
    const panel = await start({});

    assert.containsN(panel.el, ".o-calendar-filter-panel--section", 2);
    const sections = panel.el.querySelectorAll(".o-calendar-filter-panel--section");

    let header = sections[0].querySelector(".o-calendar-filter-panel--section-header");
    assert.strictEqual(header.textContent, "Attendees");
    assert.containsN(sections[0], ".o-calendar-filter-panel--filter", 4);

    header = sections[1].querySelector(".o-calendar-filter-panel--section-header");
    assert.strictEqual(header.textContent, "Users");
    assert.containsN(sections[1], ".o-calendar-filter-panel--filter", 2);
});

QUnit.skipWOWL("filters are correctly sorted", async (assert) => {
    const panel = await start({});

    assert.containsN(panel.el, ".o-calendar-filter-panel--section", 2);
    const sections = panel.el.querySelectorAll(".o-calendar-filter-panel--section");

    let header = sections[0].querySelector(".o-calendar-filter-panel--section-header");
    assert.strictEqual(header.textContent, "Attendees");
    assert.containsN(sections[0], ".o-calendar-filter-panel--filter", 4);
    assert.strictEqual(
        sections[0].textContent.trim(),
        "AttendeesMitchell AdminMarc DemoBrandon FreemanEverybody's calendar"
    );

    header = sections[1].querySelector(".o-calendar-filter-panel--section-header");
    assert.strictEqual(header.textContent, "Users");
    assert.containsN(sections[1], ".o-calendar-filter-panel--filter", 2);
    assert.strictEqual(sections[1].textContent.trim(), "UsersMarc DemoBrandon Freeman");
});

QUnit.skipWOWL("section can collapse", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    assert.containsOnce(section, ".o-calendar-filter-panel--section-header > i");
    assert.doesNotHaveClass(section, "o-calendar-filter-panel--section-collapsed");
    assert.containsN(section, ".o-calendar-filter-panel--filter", 4);

    await click(section, ".o-calendar-filter-panel--section-header");
    assert.hasClass(section, "o-calendar-filter-panel--section-collapsed");
    assert.containsNone(section, ".o-calendar-filter-panel--filter");

    await click(section, ".o-calendar-filter-panel--section-header");
    assert.doesNotHaveClass(section, "o-calendar-filter-panel--section-collapsed");
    assert.containsN(section, ".o-calendar-filter-panel--filter", 4);
});

QUnit.skipWOWL("section cannot collapse", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[1];
    assert.containsNone(section, ".o-calendar-filter-panel--section-header > i");
    assert.doesNotHaveClass(section, "o-calendar-filter-panel--section-collapsed");
    assert.containsN(section, ".o-calendar-filter-panel--filter", 2);

    await click(section, ".o-calendar-filter-panel--section-header");
    assert.doesNotHaveClass(section, "o-calendar-filter-panel--section-collapsed");
    assert.containsN(section, ".o-calendar-filter-panel--filter", 2);
});

QUnit.skipWOWL("filters can have avatar", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    const filters = section.querySelectorAll(".o-calendar-filter-panel--filter");

    assert.containsN(section, ".o-calendar-filter-panel--filter-with-avatar", 4);
    assert.containsN(section, ".o-calendar-filter-panel--filter-avatar", 4);
    assert.containsN(section, "img.o-calendar-filter-panel--filter-avatar", 3);
    assert.containsOnce(section, "i.o-calendar-filter-panel--filter-avatar");

    assert.hasAttrValue(
        filters[0].querySelector(".o-calendar-filter-panel--filter-avatar"),
        "src",
        "/web/image/res.partner/3/avatar_128"
    );
    assert.hasAttrValue(
        filters[1].querySelector(".o-calendar-filter-panel--filter-avatar"),
        "src",
        "/web/image/res.partner/6/avatar_128"
    );
    assert.hasAttrValue(
        filters[2].querySelector(".o-calendar-filter-panel--filter-avatar"),
        "src",
        "/web/image/res.partner/4/avatar_128"
    );
});

QUnit.skipWOWL("filters cannot have avatar", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[1];
    assert.containsN(section, ".o-calendar-filter-panel--filter", 2);
    assert.containsNone(section, ".o-calendar-filter-panel--filter-with-avatar");
    assert.containsNone(section, ".o-calendar-filter-panel--filter-avatar");
});

QUnit.skipWOWL("filter can have remove button", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    const filters = section.querySelectorAll(".o-calendar-filter-panel--filter");

    assert.containsN(section, ".o-calendar-filter-panel--filter", 4);
    assert.containsN(section, ".o-calendar-filter-panel--filter-remove", 2);
    assert.containsNone(filters[0], ".o-calendar-filter-panel--filter-remove");
    assert.containsOnce(filters[1], ".o-calendar-filter-panel--filter-remove");
    assert.containsOnce(filters[2], ".o-calendar-filter-panel--filter-remove");
    assert.containsNone(filters[3], ".o-calendar-filter-panel--filter-remove");
});

QUnit.skipWOWL("click on remove button", async (assert) => {
    assert.expect(3);

    const panel = await start({
        model: {
            unlinkFilter(fieldName, recordId) {
                assert.step(`${fieldName} ${recordId}`);
            },
        },
    });

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    const filters = section.querySelectorAll(".o-calendar-filter-panel--filter");

    await click(filters[1], ".o-calendar-filter-panel--filter-remove");
    await click(filters[2], ".o-calendar-filter-panel--filter-remove");
    assert.verifySteps(["partner_ids 2", "partner_ids 1"]);
});

QUnit.skipWOWL("click on filter", async (assert) => {
    assert.expect(6);

    const panel = await start({
        model: {
            updateFilter(fieldName, filterValue, active) {
                assert.step(`${fieldName} ${filterValue} ${active}`);
            },
        },
    });

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    const filters = section.querySelectorAll(".o-calendar-filter-panel--filter");

    await click(filters[0], ".o-calendar-filter-panel--filter-input");
    await click(filters[1], ".o-calendar-filter-panel--filter-input");
    await click(filters[2], ".o-calendar-filter-panel--filter-input");
    await click(filters[3], ".o-calendar-filter-panel--filter-input");
    await click(filters[3], ".o-calendar-filter-panel--filter-input");
    assert.verifySteps([
        "partner_ids 3 false",
        "partner_ids 6 true",
        "partner_ids 4 false",
        "partner_ids all true",
        "partner_ids all false",
    ]);
});

QUnit.skipWOWL("hover filter opens tooltip", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    const filters = section.querySelectorAll(".o-calendar-filter-panel--filter");

    assert.hasClass(filters[0], "o-calendar-filter-panel--filter-with-avatar");
    await triggerEvent(filters[0], null, "mouseenter");
    assert.containsOnce(panel.el, ".o-calendar-filter--tooltip");
    assert.strictEqual(
        panel.el.querySelector(".o-calendar-filter--tooltip").textContent,
        "Mitchell Admin"
    );
    assert.hasAttrValue(
        filters[0].querySelector(".o-calendar-filter-panel--filter-avatar"),
        "src",
        "/web/image/res.partner/3/avatar_128"
    );
    await triggerEvent(filters[0], null, "mouseleave");
    assert.containsNone(panel.el, ".o-calendar-filter--tooltip");

    assert.hasClass(filters[3], "o-calendar-filter-panel--filter-with-avatar");
    await triggerEvent(filters[3], null, "mouseenter");
    assert.containsNone(panel.el, ".o-calendar-filter--tooltip");
    await triggerEvent(filters[3], null, "mouseleave");
    assert.containsNone(panel.el, ".o-calendar-filter--tooltip");
});

// todos

QUnit.skipWOWL("section can have input to add filter", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[0];
    assert.containsOnce(section, ".o-calendar-filter-panel--section-input");

    assert.ok(false); // test passes if at least 1 assert fails

    panel.destroy();
});

QUnit.skipWOWL("section cannot have input to add filter", async (assert) => {
    const panel = await start({});

    const section = panel.el.querySelectorAll(".o-calendar-filter-panel--section")[1];
    assert.containsNone(section, ".o-calendar-filter-panel--section-input");

    assert.ok(false); // test passes if at least 1 assert fails

    panel.destroy();
});

QUnit.skipWOWL("filter can have color", async (assert) => {});
