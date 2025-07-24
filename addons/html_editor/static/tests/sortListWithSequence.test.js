import { sortListWithSequence, withSequence } from "@html_editor/utils/resource";
import { test, describe, expect } from "@odoo/hoot";

describe("sortListWithSequence", () => {
    test("sortListWithSequence", () => {
        expect(
            sortListWithSequence([
                "A",
                withSequence(5, "B"),
                "C",
                withSequence({ id: "foo1" }, "D"),
                withSequence({ sequenceBefore: "foo1", id: "foo2" }, "E"),
                withSequence({ sequenceAfter: "foo2" }, "F"),
                withSequence({ sequenceNumber: 4 }, "G"),
            ])
        ).toEqual(["G", "B", "A", "C", "E", "F", "D"]);
    });
});
// test("sortListWithSequence", () => {
//     expect(
//         sortListWithSequence([
//             withSequence({ id: "foo1" }, "D"),
//             withSequence({ before: "foo1", id: "foo2" }, "E"),
//         ])
//     ).toEqual(["G", "B", "A", "C", "E", "F", "D"]);
// });
// });
