import { describe, expect, test } from "@odoo/hoot";
import {
    MockServer,
    defineModels,
    fields,
    getService,
    makeMockEnv,
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
    await makeMockEnv();

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

    await makeMockEnv();

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

describe("level 1", () => {
    Oui._fields.age = fields.Integer();
    Oui._records[0].age = 42;

    test("model can be overridden at a suite level", async () => {
        await makeMockEnv();

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

        await makeMockEnv();

        await expect(
            getService("orm").searchRead("oui", [], ["id", "name", "age", "surname"])
        ).resolves.toEqual([
            {
                id: 1,
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
            await makeMockEnv();

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
