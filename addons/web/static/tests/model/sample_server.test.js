import { describe, expect, test } from "@odoo/hoot";
import { SampleServer } from "@web/model/sample_server";

const {
    MAIN_RECORDSET_SIZE,
    SEARCH_READ_LIMIT, // Limits
    SAMPLE_COUNTRIES,
    SAMPLE_PEOPLE,
    SAMPLE_TEXTS, // Text values
    MAX_COLOR_INT,
    MAX_FLOAT,
    MAX_INTEGER,
    MAX_MONETARY, // Number values
    SUB_RECORDSET_SIZE, // Records sise
} = SampleServer;

/**
 * Transforms random results into deterministic ones.
 */
class DeterministicSampleServer extends SampleServer {
    constructor() {
        super(...arguments);
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
        return (this.subRecordIdCpt++ % SUB_RECORDSET_SIZE) + 1;
    }
}

const fields = {
    "res.users": {
        display_name: { string: "Name", type: "char" },
        name: { string: "Reference", type: "char" },
        email: { string: "Email", type: "char" },
        phone_number: { string: "Phone number", type: "char" },
        website_url: { string: "URL", type: "char" },
        urlemailphone: { string: "Whatever", type: "char" },
        active: { string: "Active", type: "boolean" },
        is_alive: { string: "Is alive", type: "boolean" },
        description: { string: "Description", type: "text" },
        birthday: { string: "Birthday", type: "date" },
        arrival_date: { string: "Date of arrival", type: "datetime" },
        height: { string: "Height", type: "float" },
        color: { string: "Color", type: "integer" },
        age: { string: "Age", type: "integer" },
        salary: { string: "Salary", type: "monetary" },
        currency: {
            string: "Currency",
            type: "many2one",
            relation: "res.currency",
        },
        manager_id: {
            string: "Manager",
            type: "many2one",
            relation: "res.users",
        },
        cover_image_id: {
            string: "Cover Image",
            type: "many2one",
            relation: "ir.attachment",
        },
        managed_ids: {
            string: "Managing",
            type: "one2many",
            relation: "res.users",
        },
        tag_ids: { string: "Tags", type: "many2many", relation: "tag" },
        type: {
            string: "Type",
            type: "selection",
            selection: [
                ["client", "Client"],
                ["partner", "Partner"],
                ["employee", "Employee"],
            ],
        },
    },
    "res.country": {
        display_name: { string: "Name", type: "char" },
    },
    hobbit: {
        display_name: { string: "Name", type: "char" },
        profession: {
            string: "Profession",
            type: "selection",
            selection: [
                ["gardener", "Gardener"],
                ["brewer", "Brewer"],
                ["adventurer", "Adventurer"],
            ],
        },
        age: { string: "Age", type: "integer" },
    },
    "ir.attachment": {
        display_name: { string: "Name", type: "char" },
    },
};

describe.current.tags("headless");

describe("Sample data", () => {
    test("people type + all field names", async () => {
        const specification = {};
        for (const fieldName in fields["res.users"]) {
            specification[fieldName] = {};
            if (fields["res.users"][fieldName].type === "many2one") {
                specification[fieldName] = {
                    fields: { display_name: {} },
                };
            }
        }
        const server = new DeterministicSampleServer("res.users", fields["res.users"]);
        const { records } = await server.mockRpc({
            method: "web_search_read",
            model: "res.users",
            specification,
        });
        const rec = records[0];
        // Basic fields
        expect(SAMPLE_PEOPLE).toInclude(rec.display_name);
        expect(SAMPLE_PEOPLE).toInclude(rec.name);
        expect(rec.email).toBe(`${rec.display_name.replace(/ /, ".").toLowerCase()}@sample.demo`);
        expect(rec.phone_number).toMatch(/\+1 555 754 000\d/);
        expect(rec.website_url).toMatch(/http:\/\/sample\d\.com/);
        expect(rec.urlemailphone).toBe(false);
        expect(rec.active).toBe(true);
        expect(rec.is_alive).toBeOfType("boolean");
        expect(SAMPLE_TEXTS).toInclude(rec.description);
        expect(rec.birthday).toMatch(/\d{4}-\d{2}-\d{2}/);
        expect(rec.arrival_date).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/);
        expect(rec.height).toBeWithin(0, MAX_FLOAT);
        expect(rec.color).toBeWithin(0, MAX_COLOR_INT - 1);
        expect(rec.age).toBeWithin(0, MAX_INTEGER - 1);
        expect(rec.salary).toBeWithin(0, MAX_MONETARY - 1);
        // check float field have 2 decimal rounding
        expect(rec.height).toBe(parseFloat(parseFloat(rec.height).toFixed(2)));
        const selectionValues = fields["res.users"].type.selection.map((sel) => sel[0]);
        expect(selectionValues).toInclude(rec.type);
        // Relational fields
        expect(rec.currency.id).toBe(1);
        // Currently we expect the currency name to be a latin string, which
        // is not important; in most case we only need the ID. The following
        // assertion can be removed if needed.
        expect(SAMPLE_TEXTS).toInclude(rec.currency.display_name);
        expect(rec.manager_id.id).toBeOfType("number");
        expect(SAMPLE_PEOPLE).toInclude(rec.manager_id.display_name);
        expect(rec.cover_image_id).toBe(false);
        expect(rec.managed_ids).toHaveLength(2);
        expect(rec.managed_ids.every((id) => typeof id === "number")).toBe(true);
        expect(rec.tag_ids).toHaveLength(2);
        expect(rec.tag_ids.every((id) => typeof id === "number")).toBe(true);
    });

    test("country type", async () => {
        const server = new DeterministicSampleServer("res.country", fields["res.country"]);
        const { records } = await server.mockRpc({
            method: "web_search_read",
            model: "res.country",
            specification: { display_name: {} },
        });
        expect(SAMPLE_COUNTRIES).toInclude(records[0].display_name);
    });

    test("any type", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const { records } = await server.mockRpc({
            method: "web_search_read",
            model: "hobbit",
            specification: { display_name: {} },
        });
        expect(SAMPLE_TEXTS).toInclude(records[0].display_name);
    });
});

describe("RPC calls", () => {
    test("'search_read': valid field names", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "web_search_read",
            model: "hobbit",
            specification: { display_name: {} },
        });
        expect(Object.keys(result.records[0])).toEqual(["id", "display_name"]);
        expect(result.length).toBe(SEARCH_READ_LIMIT);
        expect(result.records[0].display_name).toMatch(/\w+/, {
            message: "Display name has been mocked",
        });
    });

    test("'search_read': many2one fields", async () => {
        const server = new DeterministicSampleServer("res.users", fields["res.users"]);
        const result = await server.mockRpc({
            method: "web_search_read",
            model: "res.users",
            specification: {
                manager_id: {
                    fields: { display_name: {} },
                },
            },
        });
        expect(Object.keys(result.records[0])).toEqual(["id", "manager_id"]);
        expect(result.records[0].manager_id.id).toBe(1);
        expect(result.records[0].manager_id.display_name).toMatch(/\w+/);
    });

    test("'web_read_group': no group", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        server.setExistingGroups(null);
        const result = await server.mockRpc({
            method: "web_read_group",
            model: "hobbit",
            groupBy: ["profession"],
        });
        expect(result).toEqual({
            groups: [
                {
                    __domain: [],
                    profession: "adventurer",
                    profession_count: 5,
                },
                {
                    __domain: [],
                    profession: "brewer",
                    profession_count: 5,
                },
                {
                    __domain: [],
                    profession: "gardener",
                    profession_count: 6,
                },
            ],
            length: 3,
        });
    });

    test("'web_read_group': 2 groups", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const existingGroups = [
            { profession: "gardener", count: 0 }, // fake group
            { profession: "adventurer", count: 0 }, // fake group
        ];
        server.setExistingGroups(existingGroups);
        const result = await server.mockRpc({
            method: "web_read_group",
            model: "hobbit",
            groupBy: ["profession"],
            fields: [],
        });
        expect(result).toHaveLength(2);
        expect(result.groups).toHaveLength(2);
        expect(result.groups.map((g) => g.profession)).toEqual(["gardener", "adventurer"]);
        expect(result.groups.reduce((acc, g) => acc + g.profession_count, 0)).toBe(
            MAIN_RECORDSET_SIZE
        );
        expect(result.groups.every((g) => g.profession_count === g.__recordIds.length)).toBe(true);
    });

    test("'web_read_group': all groups", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const existingGroups = [
            { profession: "gardener", count: 0 }, // fake group
            { profession: "brewer", count: 0 }, // fake group
            { profession: "adventurer", count: 0 }, // fake group
        ];
        server.setExistingGroups(existingGroups);
        const result = await server.mockRpc({
            method: "web_read_group",
            model: "hobbit",
            groupBy: ["profession"],
            fields: [],
        });
        expect(result.length).toBe(3);
        expect(result.groups).toHaveLength(3);
        expect(result.groups.map((g) => g.profession)).toEqual([
            "gardener",
            "brewer",
            "adventurer",
        ]);
        expect(result.groups.reduce((acc, g) => acc + g.profession_count, 0)).toBe(
            MAIN_RECORDSET_SIZE
        );
        expect(result.groups.every((g) => g.profession_count === g.__recordIds.length)).toBe(true);
    });

    test("'read_group': no group", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read_group",
            model: "hobbit",
            fields: [],
            groupBy: [],
        });
        expect(result).toEqual([
            {
                __count: MAIN_RECORDSET_SIZE,
                __domain: [],
            },
        ]);
    });

    test("'read_group': groupBy", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read_group",
            model: "hobbit",
            fields: [],
            groupBy: ["profession"],
        });
        expect(result).toHaveLength(3);
        expect(result.map((g) => g.profession)).toEqual(["adventurer", "brewer", "gardener"]);
        expect(result.reduce((acc, g) => acc + g.profession_count, 0)).toBe(MAIN_RECORDSET_SIZE);
    });

    test("'read_group': groupBy and field", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read_group",
            model: "hobbit",
            fields: ["age:sum"],
            groupBy: ["profession"],
        });
        expect(result).toHaveLength(3);
        expect(result.map((g) => g.profession)).toEqual(["adventurer", "brewer", "gardener"]);
        expect(result.reduce((acc, g) => acc + g.profession_count, 0)).toBe(MAIN_RECORDSET_SIZE);
        expect(result.reduce((acc, g) => acc + g.age, 0)).toBe(
            server.data.hobbit.records.reduce((acc, g) => acc + g.age, 0)
        );
    });

    test("'read_group': multiple groupBys and lazy", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read_group",
            model: "hobbit",
            fields: [],
            groupBy: ["profession", "age"],
        });
        expect("profession" in result[0]).toBe(true);
        expect("age" in result[0]).toBe(false);
    });

    test("'read_group': multiple groupBys and not lazy", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read_group",
            model: "hobbit",
            fields: [],
            groupBy: ["profession", "age"],
            lazy: false,
        });
        expect("profession" in result[0]).toBe(true);
        expect("age" in result[0]).toBe(true);
    });

    test("'read_group': multiple groupBys among which a many2many", async () => {
        const server = new DeterministicSampleServer("res.users", fields["res.users"]);
        const result = await server.mockRpc({
            method: "read_group",
            model: "res.users",
            fields: [],
            groupBy: ["height", "tag_ids"],
            lazy: false,
        });
        expect(result[0].tag_ids[0]).toBeOfType("number");
        expect(result[0].tag_ids[1]).toBeOfType("string");
    });

    test("'read': no id", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read",
            model: "hobbit",
            args: [[], ["display_name"]],
        });
        expect(result).toEqual([]);
    });

    test("'read': one id", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const result = await server.mockRpc({
            method: "read",
            model: "hobbit",
            args: [[1], ["display_name"]],
        });
        expect(result).toHaveLength(1);
        expect(result[0].display_name).toMatch(/\w+/);
        expect(result[0].id).toBe(1);
    });

    test("'read': more than all available ids", async () => {
        const server = new DeterministicSampleServer("hobbit", fields.hobbit);
        const amount = MAIN_RECORDSET_SIZE + 3;
        const ids = new Array(amount).fill().map((_, i) => i + 1);
        const result = await server.mockRpc({
            method: "read",
            model: "hobbit",
            args: [ids, ["display_name"]],
        });
        expect(result).toHaveLength(MAIN_RECORDSET_SIZE);
    });

    test("'read_group': partial support of array_agg", async () => {
        fields["res.users"].id = { type: "integer", name: "ID" };
        const server = new DeterministicSampleServer("res.users", fields["res.users"]);
        const result = await server.mockRpc({
            method: "read_group",
            model: "res.users",
            fields: ["unused_label:array_agg(id)"],
            groupBy: [],
            lazy: false,
        });
        expect(result).toHaveLength(1);
        const ids = new Array(16).fill(0).map((_, index) => index + 1);
        expect(result[0].id).toEqual(ids);
    });
});
