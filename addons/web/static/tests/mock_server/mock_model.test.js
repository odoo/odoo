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

test("model name can be implicitly extracted from its constructor name", async () => {
    const [AnonymousClass, Foo, ResCurrency, ResPartner] = defineModels([
        class extends models.Model {},
        class Foo extends models.Model {},
        class ResCurrency extends models.Model {
            _name = "project.task"; //
        },
        class ResPartner extends models.Model {},
    ]);

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
