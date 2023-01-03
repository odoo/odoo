/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { click, getFixture } from "../../helpers/utils";
import { makeEnv, makeFakeModel, mountComponent } from "./helpers";

let target;

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarFilterPanel, env, {
        model,
        ...props,
    });
}

QUnit.module("CalendarView - FilterPanel", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.test("render filter panel", async (assert) => {
        await start({});

        assert.containsN(target, ".o_calendar_filter", 2);
        const sections = target.querySelectorAll(".o_calendar_filter");

        let header = sections[0].querySelector(".o_cw_filter_label");
        assert.strictEqual(header.textContent, "Attendees");
        assert.containsN(sections[0], ".o_calendar_filter_item", 4);

        header = sections[1].querySelector(".o_cw_filter_label");
        assert.strictEqual(header.textContent, "Users");
        assert.containsN(sections[1], ".o_calendar_filter_item", 2);
    });

    QUnit.test("filters are correctly sorted", async (assert) => {
        await start({});

        assert.containsN(target, ".o_calendar_filter", 2);
        const sections = target.querySelectorAll(".o_calendar_filter");

        let header = sections[0].querySelector(".o_cw_filter_label");
        assert.strictEqual(header.textContent, "Attendees");
        assert.containsN(sections[0], ".o_calendar_filter_item", 4);
        assert.strictEqual(
            sections[0].textContent.trim(),
            "AttendeesMitchell AdminMarc DemoBrandon FreemanEverybody's calendar"
        );

        header = sections[1].querySelector(".o_cw_filter_label");
        assert.strictEqual(header.textContent, "Users");
        assert.containsN(sections[1], ".o_calendar_filter_item", 2);
        assert.strictEqual(sections[1].textContent.trim(), "UsersMarc DemoBrandon Freeman");
    });

    QUnit.test("section can collapse", async (assert) => {
        await start({});

        const section = target.querySelectorAll(".o_calendar_filter")[0];
        assert.containsOnce(section, ".o_cw_filter_collapse_icon");
        assert.containsN(section, ".o_calendar_filter_item", 4);

        await click(section, ".o_cw_filter_label");
        assert.containsNone(section, ".o_calendar_filter_item");

        await click(section, ".o_cw_filter_label");
        assert.containsN(section, ".o_calendar_filter_item", 4);
    });

    QUnit.test("section cannot collapse", async (assert) => {
        await start({});

        const section = target.querySelectorAll(".o_calendar_filter")[1];
        assert.containsNone(section, ".o_cw_filter_label > i");
        assert.doesNotHaveClass(section, "o_calendar_filter-collapsed");
        assert.containsN(section, ".o_calendar_filter_item", 2);

        await click(section, ".o_cw_filter_label");
        assert.doesNotHaveClass(section, "o_calendar_filter-collapsed");
        assert.containsN(section, ".o_calendar_filter_item", 2);
    });

    QUnit.test("filters can have avatar", async (assert) => {
        await start({});

        const section = target.querySelectorAll(".o_calendar_filter")[0];
        const filters = section.querySelectorAll(".o_calendar_filter_item");

        assert.containsN(section, ".o_cw_filter_avatar", 4);
        assert.containsN(section, "img.o_cw_filter_avatar", 3);
        assert.containsOnce(section, "i.o_cw_filter_avatar");

        assert.hasAttrValue(
            filters[0].querySelector(".o_cw_filter_avatar"),
            "data-src",
            "/web/image/res.partner/3/avatar_128"
        );
        assert.hasAttrValue(
            filters[1].querySelector(".o_cw_filter_avatar"),
            "data-src",
            "/web/image/res.partner/6/avatar_128"
        );
        assert.hasAttrValue(
            filters[2].querySelector(".o_cw_filter_avatar"),
            "data-src",
            "/web/image/res.partner/4/avatar_128"
        );
    });

    QUnit.test("filters cannot have avatar", async (assert) => {
        await start({});

        const section = target.querySelectorAll(".o_calendar_filter")[1];
        assert.containsN(section, ".o_calendar_filter_item", 2);
        assert.containsNone(section, ".o_cw_filter_avatar");
    });

    QUnit.test("filter can have remove button", async (assert) => {
        await start({});

        const section = target.querySelectorAll(".o_calendar_filter")[0];
        const filters = section.querySelectorAll(".o_calendar_filter_item");

        assert.containsN(section, ".o_calendar_filter_item", 4);
        assert.containsN(section, ".o_calendar_filter_item .o_remove", 2);
        assert.containsNone(filters[0], ".o_remove");
        assert.containsOnce(filters[1], ".o_remove");
        assert.containsOnce(filters[2], ".o_remove");
        assert.containsNone(filters[3], ".o_remove");
    });

    QUnit.test("click on remove button", async (assert) => {
        assert.expect(3);

        await start({
            model: {
                unlinkFilter(fieldName, recordId) {
                    assert.step(`${fieldName} ${recordId}`);
                },
            },
        });

        const section = target.querySelectorAll(".o_calendar_filter")[0];
        const filters = section.querySelectorAll(".o_calendar_filter_item");

        await click(filters[1], ".o_calendar_filter_item .o_remove");
        await click(filters[2], ".o_calendar_filter_item .o_remove");
        assert.verifySteps(["partner_ids 2", "partner_ids 1"]);
    });

    QUnit.test("click on filter", async (assert) => {
        assert.expect(6);

        await start({
            model: {
                updateFilters(fieldName, args) {
                    assert.step(`${fieldName} ${Object.keys(args)[0]} ${Object.values(args)[0]}`);
                },
            },
        });

        const section = target.querySelectorAll(".o_calendar_filter")[0];
        const filters = section.querySelectorAll(".o_calendar_filter_item");

        await click(filters[0], "input");
        await click(filters[1], "input");
        await click(filters[2], "input");
        await click(filters[3], "input");
        await click(filters[3], "input");
        assert.verifySteps([
            "partner_ids 3 false",
            "partner_ids 6 true",
            "partner_ids 4 false",
            "partner_ids all true",
            "partner_ids all false",
        ]);
    });
});
