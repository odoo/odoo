import { beforeEach, expect, test, describe } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountGanttView } from "./web_gantt_test_helpers";
import { ResUsers, TASKS_STAGE_SELECTION, Tasks, defineGanttModels } from "./gantt_mock_models";

function randomName(length) {
    const CHARS = "abcdefghijklmnopqrstuvwxyzàùéèâîûêôäïüëö";
    return [...Array(length)]
        .map(() => {
            const char = CHARS[Math.floor(Math.random() * CHARS.length)];
            return Math.random() < 0.5 ? char : char.toUpperCase();
        })
        .join("");
}

defineGanttModels();
beforeEach(() => mockDate("2018-12-20T08:00:00", +1));

describe.current.tags("manual testing");

test.skip("large amount of records (ungrouped)", async () => {
    const NB_TASKS = 10000;

    Tasks._records = [...Array(NB_TASKS)].map((_, i) => ({
        id: i + 1,
        name: `Task ${i + 1}`,
        start: `2018-12-01 00:00:00`,
        stop: `2018-12-01 23:00:00`,
    }));

    console.time("makeView");
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
    });
    console.timeEnd("makeView");
    expect(1).toBe(1);
});

test.skip("large amount of records (one level grouped)", async () => {
    const NB_USERS = 10000;
    const NB_TASKS = 10000;

    ResUsers._records = [...Array(NB_USERS)].map((_, i) => ({
        id: i + 1,
        name: `${randomName(Math.floor(Math.random() * 8) + 8)} (${i + 1})`,
    }));
    Tasks._records = [...Array(NB_TASKS)].map((_, i) => {
        let day1 = (i % 30) + 1;
        let day2 = (i % 30) + 2;
        if (day1 < 10) {
            day1 = "0" + day1;
        }
        if (day2 < 10) {
            day2 = "0" + day2;
        }
        return {
            id: i + 1,
            name: `Task ${i + 1}`,
            user_id: Math.floor(Math.random() * Math.floor(NB_USERS)) + 1,
            start: `2018-12-${day1} 00:00:00`,
            stop: `2018-12-${day2} 00:00:00`,
        };
    });

    console.time("makeView");
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        groupBy: ["user_id"],
    });
    console.timeEnd("makeView");

    queryFirst(".o_content").style = "max-height: 600px; overflow-y: scroll;";
    expect(1).toBe(1);
});

test.skip("large amount of records (two level grouped)", async () => {
    const NB_USERS = 100;
    const NB_TASKS = 10000;

    ResUsers._records = [...Array(NB_USERS)].map((_, i) => ({
        id: i + 1,
        name: `${randomName(Math.floor(Math.random() * 8) + 8)} (${i + 1})`,
    }));
    Tasks._records = [...Array(NB_TASKS)].map((_, i) => ({
        id: i + 1,
        name: `Task ${i + 1}`,
        stage: TASKS_STAGE_SELECTION[i % 2][0],
        user_id: (i % NB_USERS) + 1,
        start: "2018-12-01 00:00:00",
        stop: "2018-12-02 00:00:00",
    }));

    console.time("makeView");
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        groupBy: ["user_id", "stage"],
    });
    console.timeEnd("makeView");
    expect(1).toBe(1);
});
