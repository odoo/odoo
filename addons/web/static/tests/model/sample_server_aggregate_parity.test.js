// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { FLOAT_PRECISION } from "@web/model/sample_data";
import { SampleServer } from "@web/model/sample_server";

class DeterministicSampleServer extends SampleServer {
    constructor(modelName, fields, relatedModels) {
        super(modelName, fields, relatedModels);
        this.arrayElCpt = 0;
        this.boolCpt = 0;
        this.subRecordIdCpt = 0;
    }
    _getRandomArrayEl(array) {
        return array[this.arrayElCpt++ % array.length];
    }
    _getRandomBool() {
        return Boolean(this.boolCpt++ % 2);
    }
    _getRandomSubRecordId() {
        return (this.subRecordIdCpt++ % SampleServer.SUB_RECORDSET_SIZE) + 1;
    }
}

const FIELDS = {
    display_name: { string: "Name", type: "char" },
    profession: {
        string: "Profession",
        type: "selection",
        selection: [
            ["gardener", "Gardener"],
            ["brewer", "Brewer"],
        ],
    },
    weight: { string: "Weight", type: "float" },
    age: { string: "Age", type: "integer" },
};

function decimals(value) {
    const text = String(value);
    return text.includes(".") ? text.split(".")[1].length : 0;
}

function readGroup(server, aggregates) {
    return server.mockRpc({
        method: "web_read_group",
        model: "hobbit",
        groupBy: ["profession"],
        aggregates,
    });
}

describe("SampleServer aggregate parity across the two group paths", () => {
    test("field counts exclude missing values but retain zero and false", () => {
        const server = new DeterministicSampleServer("hobbit", FIELDS);
        const result = server._aggregateFields(
            [
                { fieldName: "weight", func: "count", name: "weight:count" },
                { fieldName: "__count", func: "__count", name: "__count" },
            ],
            [{ weight: 0 }, { weight: false }, { weight: 10 }, { weight: null }, {}],
        );
        expect(result).toEqual({ "weight:count": 3, __count: 5 });
    });

    test("float sums are rounded on the pure-sample path", async () => {
        const server = new DeterministicSampleServer("hobbit", FIELDS);
        const result = await readGroup(server, ["weight:sum", "__count"]);
        for (const group of result.groups) {
            expect(decimals(group["weight:sum"])).toBeLessThan(FLOAT_PRECISION + 1);
        }
    });

    test("float sums are rounded on the existing-groups path too", async () => {
        const server = new DeterministicSampleServer("hobbit", FIELDS);
        server.setExistingGroups([
            { profession: "gardener", count: 0, __records: [] },
            { profession: "brewer", count: 0, __records: [] },
        ]);
        const result = await readGroup(server, ["weight:sum", "__count"]);
        expect(result.groups).toHaveLength(2);
        for (const group of result.groups) {
            expect(decimals(group["weight:sum"])).toBeLessThan(FLOAT_PRECISION + 1);
        }
    });

    test("integer sums are unaffected on the existing-groups path", async () => {
        const server = new DeterministicSampleServer("hobbit", FIELDS);
        server.setExistingGroups([
            { profession: "gardener", count: 0, __records: [] },
            { profession: "brewer", count: 0, __records: [] },
        ]);
        const result = await readGroup(server, ["age:sum", "__count"]);
        for (const group of result.groups) {
            expect(Number.isInteger(group["age:sum"])).toBe(true);
        }
    });
});
