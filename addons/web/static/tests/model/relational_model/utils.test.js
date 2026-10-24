import { describe, expect, test } from "@odoo/hoot";
import { composeChanges } from "@web/model/relational_model/utils";

describe.current.tags("headless");

const fields = {
    name: { type: "char" },
    line_ids: { type: "one2many" },
    tag_ids: { type: "many2many" },
};

test("composeChanges: values of the next changes override the previous ones", () => {
    expect(composeChanges({ name: "a", tag_ids: [[4, 1]] }, { name: "b" }, fields)).toEqual({
        name: "b",
        tag_ids: [[4, 1]],
    });
});

test("composeChanges: x2many commands are applied in sequence", () => {
    const changes = { tag_ids: [[4, 1]], line_ids: [[1, 5, { name: "x" }]] };
    const nextChanges = { tag_ids: [[3, 2]], line_ids: [[2, 6]] };
    expect(composeChanges(changes, nextChanges, fields)).toEqual({
        tag_ids: [
            [4, 1],
            [3, 2],
        ],
        line_ids: [
            [1, 5, { name: "x" }],
            [2, 6],
        ],
    });
});

test("composeChanges: a command on a record created before is merged into its creation", () => {
    const changes = { line_ids: [[0, "virtual_1", { name: "a", qty: 1 }]] };
    expect(
        composeChanges(changes, { line_ids: [[1, "virtual_1", { name: "b" }]] }, fields)
    ).toEqual({ line_ids: [[0, "virtual_1", { name: "b", qty: 1 }]] });
    expect(composeChanges(changes, { line_ids: [[2, "virtual_1"]] }, fields)).toEqual({
        line_ids: [],
    });
    expect(composeChanges(changes, { line_ids: [[3, "virtual_1"]] }, fields)).toEqual({
        line_ids: [],
    });
});

test("composeChanges: CLEAR and SET drop the previous changes of the relation", () => {
    const changes = {
        tag_ids: [
            [0, "virtual_1", { name: "new tag" }],
            [1, "virtual_1", { name: "renamed" }],
            [4, 1],
            [3, 2],
            [1, 3, { name: "existing tag" }],
        ],
    };
    expect(composeChanges(changes, { tag_ids: [[6, false, [12]]] }, fields)).toEqual({
        tag_ids: [
            [1, 3, { name: "existing tag" }],
            [6, false, [12]],
        ],
    });
    expect(composeChanges(changes, { tag_ids: [[5]] }, fields)).toEqual({
        tag_ids: [[1, 3, { name: "existing tag" }], [5]],
    });
});

test("composeChanges: the previous changes are not modified", () => {
    const changes = { tag_ids: [[4, 1]], line_ids: [[0, "virtual_1", { name: "a" }]] };
    const result = composeChanges(changes, { line_ids: [[2, "virtual_1"]] }, fields);
    result.tag_ids.push([4, 2]);
    expect(changes).toEqual({ tag_ids: [[4, 1]], line_ids: [[0, "virtual_1", { name: "a" }]] });
});
