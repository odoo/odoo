import { expect, test } from "@odoo/hoot";
import { listView } from "@web/views/list";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { AttendanceListModel } from "@hr_attendance/views/attendance_list_view";

defineMailModels();

const ACTIVE = ["employee_id.active", "=", true];

/**
 * Capture what the list model hands to its parent, without a server: the
 * question is which domain `super.load` is called with, and mounting a view to
 * ask it makes the answer depend on the action's own default filters.
 */
function captureSuperLoad() {
    const seen = [];
    patchWithCleanup(listView.Model.prototype, {
        async load(params) {
            seen.push(params);
            return params;
        },
    });
    return seen;
}

function modelWith(configDomain) {
    const model = Object.create(AttendanceListModel.prototype);
    model.config = { domain: configDomain };
    return model;
}

test("the archived-employee filter is added to a domain the view passes", async () => {
    const seen = captureSuperLoad();
    const model = modelWith([]);
    await model.load({ domain: [["check_out", "!=", false]] });
    expect(seen[0].domain).toEqual([["check_out", "!=", false], ACTIVE]);
});

test("the domain the caller passed is not mutated", async () => {
    captureSuperLoad();
    const domain = [["check_out", "!=", false]];
    await modelWith([]).load({ domain });
    expect(domain).toEqual([["check_out", "!=", false]], {
        message:
            "`params.domain` is the search model's own array. Pushing into it " +
            "wrote this view's filter into a domain the rest of the search " +
            "panel goes on reading.",
    });
});

test("a reload that passes no domain is still filtered", async () => {
    const seen = captureSuperLoad();
    const model = modelWith([["check_out", "!=", false]]);
    await model.load();
    expect(seen[0].domain).toEqual([["check_out", "!=", false], ACTIVE], {
        message:
            "every reload meaning 'same domain as before' -- after a save, " +
            "after a discard -- arrives with no domain at all, and used to " +
            "reach the right one only because the first load had mutated the " +
            "array still sitting in the config.",
    });
});

test("a caller that asks about archived employees is left alone", async () => {
    const seen = captureSuperLoad();
    const asked = [["employee_id.active", "=", false]];
    await modelWith([]).load({ domain: asked });
    expect(seen[0].domain).toEqual(asked);
});

test("an empty config domain does not throw", async () => {
    const seen = captureSuperLoad();
    const model = Object.create(AttendanceListModel.prototype);
    model.config = {};
    await model.load();
    expect(seen[0].domain).toEqual([ACTIVE]);
});
