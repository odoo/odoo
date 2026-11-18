import { describe, expect, test } from "@odoo/hoot";
import {
    MockServer,
    defineModels,
    fields,
    getService,
    makeTestApp,
    makeMockServer,
    models,
} from "@web/../tests/web_test_helpers";

class Oui extends models.Model {
    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "John Doe",
        },
    ];
}

defineModels([Oui]);
describe.current.tags("headless");

test("model name can be implicitly extracted from its constructor name", async () => {
    const [AnonymousClass, Foo, ResCurrency, ResPartner] = [
        class extends models.Model {},
        class Foo extends models.Model {},
        class ResCurrency extends models.Model {
            _name = "project.task";
        },
        class ResPartner extends models.Model {},
    ];

    defineModels([AnonymousClass, Foo, ResCurrency, ResPartner]);

    await makeMockServer();

    expect(MockServer.env["anonymous"]).toBeInstanceOf(AnonymousClass);
    expect(MockServer.env["foo"]).toBeInstanceOf(Foo);
    expect(MockServer.env["project.task"]).toBeInstanceOf(ResCurrency);
    expect(MockServer.env["res.partner"]).toBeInstanceOf(ResPartner);

    expect(() => MockServer.env["res.currency"]).toThrow(
        "could not get model from server environment"
    );
});

test("model should be defined on the mock server", async () => {
    await makeTestApp();

    await expect(getService("orm").searchRead("oui", [], ["id", "name"])).resolves.toEqual([
        {
            id: 1,
            name: "John Doe",
        },
    ]);
});

test("models can be extended by having the same name", async () => {
    class First extends models.Model {
        _name = "same.model";

        description = fields.Char();

        same_method() {
            return "1";
        }
    }

    class Second extends models.Model {
        _name = "same.model";

        description = fields.Text();

        second_method() {
            return "added by 2";
        }

        same_method() {
            return [super.same_method(), "2"].join(" & ");
        }
    }

    class Third extends models.Model {
        _name = "same.model";

        title = fields.Char();

        third_method() {
            return "added by 3";
        }

        same_method() {
            return "overridden by 3";
        }
    }

    defineModels([First, Second]);

    await makeTestApp();

    expect(MockServer.env["same.model"]).toBeInstanceOf(Second);
    expect(MockServer.env["same.model"]._fields.description.type).toBe("text");
    expect(MockServer.env["same.model"]._fields).not.toInclude("title");

    const orm = getService("orm");

    await expect(orm.call("same.model", "same_method")).resolves.toBe("1 & 2");
    await expect(orm.call("same.model", "second_method")).resolves.toBe("added by 2");
    await expect(orm.call("same.model", "third_method")).rejects.toThrow();

    defineModels([Third]);

    expect(MockServer.env["same.model"]).toBeInstanceOf(Third);
    expect(MockServer.env["same.model"]._fields.description.type).toBe("text");
    expect(MockServer.env["same.model"]._fields.title.type).toBe("char");

    await expect(orm.call("same.model", "same_method")).resolves.toBe("overridden by 3");
    await expect(orm.call("same.model", "second_method")).resolves.toBe("added by 2");
    await expect(orm.call("same.model", "third_method")).resolves.toBe("added by 3");
});

test("cannot access _records on models after init", async () => {
    expect(Oui._records).toHaveLength(1);
    expect(() => MockServer.env["oui"]).toThrow();

    const { env } = await makeMockServer();

    expect(Oui._records).toHaveLength(0);
    expect(env["oui"]).toBe(MockServer.env["oui"]);
    expect(env["oui"]).toHaveLength(1);
});

test("can create generic field", async () => {
    Oui._fields.generic = fields.Generic({ type: "blublu" });

    const { env } = await makeMockServer();

    expect(env["oui"]._fields.generic.type).toBe("blublu");
});

test("cannot create generic field without type", async () => {
    Oui._fields.generic = fields.Generic();

    await expect(makeMockServer()).rejects.toThrow(/missing key/i);
});

describe("level 1", () => {
    Oui._fields.age = fields.Integer();
    Oui._records[0].age = 42;

    test("model can be overridden at a suite level", async () => {
        await makeTestApp();

        await expect(
            getService("orm").searchRead("oui", [], ["id", "name", "age"])
        ).resolves.toEqual([
            {
                id: 1,
                name: "John Doe",
                age: 42,
            },
        ]);
    });

    test("model can be overridden at a test level", async () => {
        Oui._fields.surname = fields.Char();
        Oui._records[0].surname = "doedoe";

        await makeTestApp();

        await expect(
            getService("orm").searchRead("oui", [], ["id", "name", "age", "surname", "create_date"])
        ).resolves.toEqual([
            {
                id: 1,
                create_date: luxon.DateTime.utc().toSQL().slice(0, 19),
                name: "John Doe",
                age: 42,
                surname: "doedoe",
            },
        ]);
    });

    describe("level 2", () => {
        Oui._fields.email = fields.Char();
        Oui._records[0].email = "john@doe.com";

        test("model overrides are incremental", async () => {
            await makeTestApp();

            await expect(
                getService("orm").searchRead("oui", [], ["id", "name", "age", "email"])
            ).resolves.toEqual([
                {
                    id: 1,
                    name: "John Doe",
                    age: 42,
                    email: "john@doe.com",
                },
            ]);
        });
    });
});

describe("parent_of operator", () => {
    class PofCompany extends models.Model {
        _name = "pof.company";

        name = fields.Char();
        parent_id = fields.Many2one({ relation: "pof.company" });

        _records = [
            { id: 1, name: "Main", parent_id: false },
            { id: 2, name: "Branch", parent_id: 1 },
            { id: 3, name: "Other", parent_id: false },
        ];
    }

    class PofTag extends models.Model {
        _name = "pof.tag";

        name = fields.Char();
        active = fields.Boolean({ default: true });
        parent_id = fields.Many2one({ relation: "pof.tag" });

        _records = [
            { id: 1, name: "Tag root", active: true, parent_id: false },
            { id: 2, name: "Tag child", active: true, parent_id: 1 },
            { id: 3, name: "Tag archived", active: false, parent_id: 1 },
        ];
    }

    class PofNode extends models.Model {
        _name = "pof.node";

        name = fields.Char();
        parent_id = fields.Many2one({ relation: "pof.node" });
        child_ids = fields.One2many({ relation: "pof.node", relation_field: "parent_id" });
        coach_id = fields.Many2one({ relation: "pof.node" });
        company_id = fields.Many2one({ relation: "pof.company" });
        tag_ids = fields.Many2many({ relation: "pof.tag" });

        _records = [
            // Root -> Mid -> Leaf (via parent_id)
            { id: 1, name: "Root", parent_id: false, child_ids: [2], company_id: 1, tag_ids: [2] },
            { id: 2, name: "Mid", parent_id: 1, child_ids: [3], coach_id: 4, company_id: 2 },
            { id: 3, name: "Leaf", parent_id: 2, child_ids: [], company_id: 3, tag_ids: [3] },
            // Mid -> Coach -> Head coach (via coach_id)
            { id: 4, name: "Coach", parent_id: false, child_ids: [], coach_id: 5 },
            { id: 5, name: "Head coach", parent_id: false, child_ids: [] },
            // Cycle and self parent
            { id: 6, name: "Cycle A", parent_id: 7, child_ids: [7] },
            { id: 7, name: "Cycle B", parent_id: 6, child_ids: [6] },
            { id: 8, name: "Self", parent_id: 8, child_ids: [8] },
        ];
    }

    defineModels([PofCompany, PofTag, PofNode]);

    const search = (domain) => MockServer.env["pof.node"].search(domain);

    test("same model many2one: the record and all its ancestors, on id", async () => {
        await makeMockServer();
        expect(search([["parent_id", "parent_of", 3]])).toEqual([1, 2, 3]);
        expect(search([["parent_id", "parent_of", 1]])).toEqual([1]);
    });

    test("'id' uses the model _parent_name", async () => {
        await makeMockServer();
        expect(search([["id", "parent_of", 3]])).toEqual([1, 2, 3]);
    });

    test("another self many2one follows that field, not _parent_name", async () => {
        await makeMockServer();
        expect(search([["coach_id", "parent_of", 2]])).toEqual([2, 4, 5]);
    });

    test("a list of ids merges the ancestors of each id", async () => {
        await makeMockServer();
        expect(search([["parent_id", "parent_of", [3, 4]]])).toEqual([1, 2, 3, 4]);
    });

    test("cycles and self parents do not loop", async () => {
        await makeMockServer();
        expect(search([["parent_id", "parent_of", 6]])).toEqual([6, 7]);
        expect(search([["parent_id", "parent_of", 8]])).toEqual([8]);
    });

    test("false or an empty list matches nothing", async () => {
        await makeMockServer();
        expect(search([["parent_id", "parent_of", false]])).toEqual([]);
        expect(search([["parent_id", "parent_of", []]])).toEqual([]);
    });

    test("a string value is resolved by display_name ilike", async () => {
        await makeMockServer();
        expect(search([["parent_id", "parent_of", "mid"]])).toEqual([1, 2]);
        expect(search([["parent_id", "parent_of", "unknown"]])).toEqual([]);
    });

    test("many2one to another model walks the comodel and keeps the field", async () => {
        await makeMockServer();
        // Branch(2) -> Main(1): nodes whose company is Main or Branch
        expect(search([["company_id", "parent_of", 2]])).toEqual([1, 2]);
        // Other(3) has no parent
        expect(search([["company_id", "parent_of", 3]])).toEqual([3]);
    });

    test("many2many ids are searched first (archived ones are dropped)", async () => {
        await makeMockServer();
        // Tag child(2) -> Tag root(1): nodes tagged with 1 or 2
        expect(search([["tag_ids", "parent_of", 2]])).toEqual([1]);
        // Tag archived(3) is filtered out by the active test, as on the server
        expect(search([["tag_ids", "parent_of", 3]])).toEqual([]);
    });

    test("self one2many follows the one2many and keeps the field", async () => {
        await makeMockServer();
        // walk child_ids from Root: {1, 2, 3}, then nodes whose child_ids intersect it
        expect(search([["child_ids", "parent_of", 1]])).toEqual([1, 2]);
    });

    test("can be negated", async () => {
        await makeMockServer();
        expect(search([["company_id", "!=", false], "!", ["parent_id", "parent_of", 3]])).toEqual(
            []
        );
        expect(search(["!", ["parent_id", "parent_of", 2]])).toEqual([3, 4, 5, 6, 7, 8]);
    });

    test("non relational field throws, as on the server", async () => {
        await makeMockServer();
        expect(() => search([["name", "parent_of", 1]])).toThrow(
            "Cannot execute parent_of for name, works only for relational fields"
        );
    });
});
