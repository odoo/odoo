/** @odoo-module **/

import { getFixture, nextTick, patchDate } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { CLASSES, SELECTORS } from "./helpers";

let serverData;
/** @type {HTMLElement} */
let target;
QUnit.module("Views > GanttView - Mobile", {
    beforeEach() {
        patchDate(2018, 11, 20, 8, 0, 0);
        setupViewRegistries();
        target = getFixture();
        serverData = {
            models: {
                tasks: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Stop Date", type: "datetime" },
                        user_id: { string: "Assign To", type: "many2one", relation: "users" },
                    },
                    records: [
                        {
                            id: 1,
                            start: "2018-11-30 18:30:00",
                            stop: "2018-12-31 18:29:59",
                            user_id: 1,
                        },
                        {
                            id: 2,
                            start: "2018-12-17 11:30:00",
                            stop: "2018-12-22 06:29:59",
                            user_id: 2,
                        },
                        {
                            id: 3,
                            start: "2018-12-27 06:30:00",
                            stop: "2019-01-03 06:29:59",
                            user_id: 2,
                        },
                        {
                            id: 4,
                            start: "2018-12-19 22:30:00",
                            stop: "2018-12-20 06:29:59",
                            user_id: 1,
                        },
                        {
                            id: 5,
                            start: "2018-11-08 01:53:10",
                            stop: "2018-12-04 01:34:34",
                            user_id: 1,
                        },
                    ],
                },
                users: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "User 1" },
                        { id: 2, name: "User 2" },
                    ],
                },
            },
        };
    },
});

QUnit.test("Progressbar: check the progressbar percentage visibility.", async (assert) => {
    assert.expect(19);
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
        mockRPC(route, { method, model, args }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 50, max_value: 100 },
                        2: { value: 25, max_value: 200 },
                    },
                };
            }
        },
    });

    assert.containsN(target, SELECTORS.progressBar, 2);
    const [progressBar1, progressBar2] = target.querySelectorAll(SELECTORS.progressBar);
    assert.hasClass(progressBar1, "o_gantt_group_success");
    assert.hasClass(progressBar2, "o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    assert.ok(rowHeader1.matches(SELECTORS.rowHeader));
    assert.ok(rowHeader2.matches(SELECTORS.rowHeader));
    assert.doesNotHaveClass(rowHeader1, CLASSES.group);
    assert.doesNotHaveClass(rowHeader2, CLASSES.group);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarBackground)].map((el) => el.style.width),
        ["50%", "12.5%"]
    );
    assert.containsN(target, SELECTORS.progressBarForeground, 2, "foreground is visible in mobile");
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarForeground)].map((el) => el.textContent),
        ["50h / 100h", "25h / 200h"]
    );

    // Check the style of one of the progress bars
    assert.strictEqual(rowHeader1.children.length, 2);
    const rowTitle1 = rowHeader1.children[0];
    assert.ok(rowTitle1.matches(SELECTORS.rowTitle));
    assert.strictEqual(rowTitle1.nextElementSibling, progressBar1);

    assert.strictEqual(window.getComputedStyle(rowHeader1).gridTemplateRows, "36px 35px");
    assert.strictEqual(window.getComputedStyle(rowTitle1).height, "36px");
    assert.strictEqual(window.getComputedStyle(progressBar1).height, "35px");
});

QUnit.test("Progressbar: grouped row", async (assert) => {
    assert.expect(19);
    // Here the view is grouped twice on the same field.
    // This is not a common use case, but it is possible to achieve it
    // bu saving a default favorite with a groupby then apply it twice
    // on the same field through the groupby menu.
    // In this case, the progress bar should be displayed only once,
    // on the first level of grouping.
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" date_stop="stop" default_scale="week" scales="week" default_group_by="user_id,user_id" progress_bar="user_id">
                <field name="user_id"/>
            </gantt>
        `,
        mockRPC(route, { method, model, args }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 50, max_value: 100 },
                        2: { value: 25, max_value: 200 },
                    },
                };
            }
        },
    });

    assert.containsN(target, SELECTORS.progressBar, 2);
    const [progressBar1, progressBar2] = target.querySelectorAll(SELECTORS.progressBar);
    assert.hasClass(progressBar1, "o_gantt_group_success");
    assert.hasClass(progressBar2, "o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    assert.ok(rowHeader1.matches(SELECTORS.rowHeader));
    assert.ok(rowHeader2.matches(SELECTORS.rowHeader));
    assert.hasClass(rowHeader1, CLASSES.group);
    assert.hasClass(rowHeader2, CLASSES.group);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarBackground)].map((el) => el.style.width),
        ["50%", "12.5%"]
    );
    assert.containsN(target, SELECTORS.progressBarForeground, 2, "foreground is visible in mobile");
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarForeground)].map((el) => el.textContent),
        ["50h / 100h", "25h / 200h"]
    );

    // Check the style of one of the progress bars
    assert.strictEqual(rowHeader1.children.length, 2);
    const rowTitle1 = rowHeader1.children[0];
    assert.ok(rowTitle1.matches(SELECTORS.rowTitle));
    assert.strictEqual(rowTitle1.nextElementSibling, progressBar1);

    assert.strictEqual(window.getComputedStyle(rowHeader1).gridTemplateRows, "24px 35px");
    assert.strictEqual(window.getComputedStyle(rowTitle1).height, "24px");
    assert.strictEqual(window.getComputedStyle(progressBar1).height, "35px");
});

QUnit.test("horizontal scroll applies to the content [SMALL SCREEN]", async (assert) => {
    // for this test, we need the elements to be visible in the viewport
    target = document.body;
    target.classList.add("debug");
    registerCleanup(() => target.classList.remove("debug"));

    serverData.views = {
        "tasks,false,search": `<search/>`,
        "tasks,false,gantt": `
                <gantt date_start="start" date_stop="stop"><field name="user_id"/></gantt>
            `,
    };
    const webclient = await createWebClient({ serverData, target });
    await doAction(webclient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    });

    const o_view_controller = target.querySelector(".o_view_controller");
    const o_content = target.querySelector(".o_content");
    const firstHeaderCell = target.querySelector(SELECTORS.headerCell);
    const initialXHeaderCell = firstHeaderCell.getBoundingClientRect().x;

    assert.hasClass(
        o_view_controller,
        "o_action_delegate_scroll",
        "the 'o_view_controller' should be have the 'o_action_delegate_scroll'."
    );
    assert.strictEqual(
        window.getComputedStyle(o_view_controller).overflow,
        "hidden",
        "The view controller should have overflow hidden"
    );
    assert.strictEqual(
        window.getComputedStyle(o_content).overflow,
        "auto",
        "The view content should have the overflow auto"
    );
    assert.strictEqual(o_content.scrollLeft, 0, "Te o_content should not have scroll value");

    // Horizontal scroll
    o_content.scrollLeft = 100;
    await nextTick();

    assert.strictEqual(
        o_content.scrollLeft,
        100,
        "the o_content should be 100 due to the overflow auto"
    );
    assert.ok(
        firstHeaderCell.getBoundingClientRect().x === initialXHeaderCell - 100,
        "the gantt header cell x position value should be lower after the scroll"
    );
});
