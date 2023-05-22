/** @odoo-module **/

import { SampleServer } from "@web/views/sample_server";

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

let fields;
QUnit.module(
    "Sample Server",
    {
        beforeEach() {
            fields = {
                "res.users": {
                    display_name: { string: "Name", type: "char" },
                    name: { string: "Reference", type: "char" },
                    email: { string: "Email", type: "char" },
                    phone_number: { string: "Phone number", type: "char" },
                    brol_machin_url_truc: { string: "URL", type: "char" },
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
        },
    },
    function () {
        QUnit.module("Basic behaviour");

        QUnit.test("Sample data: people type + all field names", async function (assert) {
            assert.expect(26);

            const allFieldNames = Object.keys(fields["res.users"]);
            const server = new DeterministicSampleServer("res.users", fields["res.users"]);
            const { records } = await server.mockRpc({
                method: "web_search_read",
                model: "res.users",
                fields: allFieldNames,
            });
            const rec = records[0];

            function assertFormat(fieldName, regex) {
                if (regex instanceof RegExp) {
                    assert.ok(
                        regex.test(rec[fieldName].toString()),
                        `Field "${fieldName}" has the correct format`
                    );
                } else {
                    assert.strictEqual(
                        typeof rec[fieldName],
                        regex,
                        `Field "${fieldName}" is of type ${regex}`
                    );
                }
            }
            function assertBetween(fieldName, min, max) {
                const val = rec[fieldName];
                assert.ok(
                    min <= val && val < max && parseInt(val, 10) === val,
                    `Field "${fieldName}" should be an integer between ${min} and ${max}: ${val}`
                );
            }

            // Basic fields
            assert.ok(SAMPLE_PEOPLE.includes(rec.display_name));
            assert.ok(SAMPLE_PEOPLE.includes(rec.name));
            assert.strictEqual(
                rec.email,
                `${rec.display_name.replace(/ /, ".").toLowerCase()}@sample.demo`
            );
            assertFormat("phone_number", /\+1 555 754 000\d/);
            assertFormat("brol_machin_url_truc", /http:\/\/sample\d\.com/);
            assert.strictEqual(rec.urlemailphone, false);
            assert.strictEqual(rec.active, true);
            assertFormat("is_alive", "boolean");
            assert.ok(SAMPLE_TEXTS.includes(rec.description));
            assertFormat("birthday", /\d{4}-\d{2}-\d{2}/);
            assertFormat("arrival_date", /\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/);
            assert.ok(
                rec.height >= 0 && rec.height <= MAX_FLOAT,
                "Field height should be between 0 and 100"
            );
            assertBetween("color", 0, MAX_COLOR_INT);
            assertBetween("age", 0, MAX_INTEGER);
            assertBetween("salary", 0, MAX_MONETARY);

            // check float field have 2 decimal rounding
            assert.strictEqual(rec.height, parseFloat(parseFloat(rec.height).toFixed(2)));

            const selectionValues = fields["res.users"].type.selection.map((sel) => sel[0]);
            assert.ok(selectionValues.includes(rec.type));

            // Relational fields
            assert.strictEqual(rec.currency[0], 1);
            // Currently we expect the currency name to be a latin string, which
            // is not important; in most case we only need the ID. The following
            // assertion can be removed if needed.
            assert.ok(SAMPLE_TEXTS.includes(rec.currency[1]));

            assert.strictEqual(typeof rec.manager_id[0], "number");
            assert.ok(SAMPLE_PEOPLE.includes(rec.manager_id[1]));

            assert.strictEqual(rec.cover_image_id, false);

            assert.strictEqual(rec.managed_ids.length, 2);
            assert.ok(rec.managed_ids.every((id) => typeof id === "number"));

            assert.strictEqual(rec.tag_ids.length, 2);
            assert.ok(rec.tag_ids.every((id) => typeof id === "number"));
        });

        QUnit.test("Sample data: country type", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("res.country", fields["res.country"]);
            const { records } = await server.mockRpc({
                method: "web_search_read",
                model: "res.country",
                fields: ["display_name"],
            });

            assert.ok(SAMPLE_COUNTRIES.includes(records[0].display_name));
        });

        QUnit.test("Sample data: any type", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const { records } = await server.mockRpc({
                method: "web_search_read",
                model: "hobbit",
                fields: ["display_name"],
            });

            assert.ok(SAMPLE_TEXTS.includes(records[0].display_name));
        });

        QUnit.module("RPC calls");

        QUnit.test("Send 'search_read' RPC: valid field names", async function (assert) {
            assert.expect(3);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "web_search_read",
                model: "hobbit",
                fields: ["display_name"],
            });

            assert.deepEqual(Object.keys(result.records[0]), ["id", "display_name"]);
            assert.strictEqual(result.length, SEARCH_READ_LIMIT);
            assert.ok(/\w+/.test(result.records[0].display_name), "Display name has been mocked");
        });

        QUnit.test("Send 'search_read' RPC: invalid field names", async function (assert) {
            assert.expect(3);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "web_search_read",
                model: "hobbit",
                fields: ["name"],
            });

            assert.deepEqual(Object.keys(result.records[0]), ["id", "name"]);
            assert.strictEqual(result.length, SEARCH_READ_LIMIT);
            assert.strictEqual(
                result.records[0].name,
                false,
                `Field "name" doesn't exist => returns false`
            );
        });

        QUnit.test("Send 'web_read_group' RPC: no group", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);
            server.setExistingGroups(null);

            const result = await server.mockRpc({
                method: "web_read_group",
                model: "hobbit",
                groupBy: ["profession"],
            });

            assert.deepEqual(result, {
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

        QUnit.test("Send 'web_read_group' RPC: 2 groups", async function (assert) {
            assert.expect(5);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);
            const existingGroups = [
                { value: "gardener", profession_count: 0 }, // fake group
                { value: "adventurer", profession_count: 0 }, // fake group
            ];
            server.setExistingGroups(existingGroups);

            const result = await server.mockRpc({
                method: "web_read_group",
                model: "hobbit",
                groupBy: ["profession"],
                fields: [],
            });

            assert.strictEqual(result.length, 2);
            assert.strictEqual(result.groups.length, 2);

            assert.deepEqual(
                result.groups.map((g) => g.value),
                ["gardener", "adventurer"]
            );

            assert.strictEqual(
                result.groups.reduce((acc, g) => acc + g.profession_count, 0),
                MAIN_RECORDSET_SIZE
            );
            assert.ok(result.groups.every((g) => g.profession_count === g.__data.length));
        });

        QUnit.test("Send 'web_read_group' RPC: all groups", async function (assert) {
            assert.expect(5);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);
            const existingGroups = [
                { value: "gardener", profession_count: 0 }, // fake group
                { value: "brewer", profession_count: 0 }, // fake group
                { value: "adventurer", profession_count: 0 }, // fake group
            ];
            server.setExistingGroups(existingGroups);

            const result = await server.mockRpc({
                method: "web_read_group",
                model: "hobbit",
                groupBy: ["profession"],
                fields: [],
            });

            assert.strictEqual(result.length, 3);
            assert.strictEqual(result.groups.length, 3);

            assert.deepEqual(
                result.groups.map((g) => g.value),
                ["gardener", "brewer", "adventurer"]
            );

            assert.strictEqual(
                result.groups.reduce((acc, g) => acc + g.profession_count, 0),
                MAIN_RECORDSET_SIZE
            );
            assert.ok(result.groups.every((g) => g.profession_count === g.__data.length));
        });

        QUnit.test("Send 'read_group' RPC: no group", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read_group",
                model: "hobbit",
                fields: [],
                groupBy: [],
            });

            assert.deepEqual(result, [
                {
                    __count: MAIN_RECORDSET_SIZE,
                    __domain: [],
                },
            ]);
        });

        QUnit.test("Send 'read_group' RPC: groupBy", async function (assert) {
            assert.expect(3);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read_group",
                model: "hobbit",
                fields: [],
                groupBy: ["profession"],
            });

            assert.strictEqual(result.length, 3);
            assert.deepEqual(
                result.map((g) => g.profession),
                ["adventurer", "brewer", "gardener"]
            );
            assert.strictEqual(
                result.reduce((acc, g) => acc + g.profession_count, 0),
                MAIN_RECORDSET_SIZE
            );
        });

        QUnit.test("Send 'read_group' RPC: groupBy and field", async function (assert) {
            assert.expect(4);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read_group",
                model: "hobbit",
                fields: ["age:sum"],
                groupBy: ["profession"],
            });

            assert.strictEqual(result.length, 3);
            assert.deepEqual(
                result.map((g) => g.profession),
                ["adventurer", "brewer", "gardener"]
            );
            assert.strictEqual(
                result.reduce((acc, g) => acc + g.profession_count, 0),
                MAIN_RECORDSET_SIZE
            );
            assert.strictEqual(
                result.reduce((acc, g) => acc + g.age, 0),
                server.data.hobbit.records.reduce((acc, g) => acc + g.age, 0)
            );
        });

        QUnit.test("Send 'read_group' RPC: multiple groupBys and lazy", async function (assert) {
            assert.expect(2);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read_group",
                model: "hobbit",
                fields: [],
                groupBy: ["profession", "age"],
            });

            assert.ok("profession" in result[0]);
            assert.notOk("age" in result[0]);
        });

        QUnit.test(
            "Send 'read_group' RPC: multiple groupBys and not lazy",
            async function (assert) {
                assert.expect(2);

                const server = new DeterministicSampleServer("hobbit", fields.hobbit);

                const result = await server.mockRpc({
                    method: "read_group",
                    model: "hobbit",
                    fields: [],
                    groupBy: ["profession", "age"],
                    lazy: false,
                });

                assert.ok("profession" in result[0]);
                assert.ok("age" in result[0]);
            }
        );

        QUnit.test(
            "Send 'read_group' RPC: multiple groupBys among which a many2many",
            async function (assert) {
                const server = new DeterministicSampleServer("res.users", fields["res.users"]);
                const result = await server.mockRpc({
                    method: "read_group",
                    model: "res.users",
                    fields: [],
                    groupBy: ["height", "tag_ids"],
                    lazy: false,
                });
                assert.ok(typeof result[0].tag_ids[0] === "number");
                assert.ok(typeof result[0].tag_ids[1] === "string");
            }
        );

        QUnit.test("Send 'read' RPC: no id", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read",
                model: "hobbit",
                args: [[], ["display_name"]],
            });

            assert.deepEqual(result, []);
        });

        QUnit.test("Send 'read' RPC: one id", async function (assert) {
            assert.expect(3);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const result = await server.mockRpc({
                method: "read",
                model: "hobbit",
                args: [[1], ["display_name"]],
            });

            assert.strictEqual(result.length, 1);
            assert.ok(/\w+/.test(result[0].display_name), "Display name has been mocked");
            assert.strictEqual(result[0].id, 1);
        });

        QUnit.test("Send 'read' RPC: more than all available ids", async function (assert) {
            assert.expect(1);

            const server = new DeterministicSampleServer("hobbit", fields.hobbit);

            const amount = MAIN_RECORDSET_SIZE + 3;
            const ids = new Array(amount).fill().map((_, i) => i + 1);
            const result = await server.mockRpc({
                method: "read",
                model: "hobbit",
                args: [ids, ["display_name"]],
            });

            assert.strictEqual(result.length, MAIN_RECORDSET_SIZE);
        });

        // To be implemented if needed
        // QUnit.test("Send 'read_progress_bar' RPC", async function (assert) { ... });
    }
);
