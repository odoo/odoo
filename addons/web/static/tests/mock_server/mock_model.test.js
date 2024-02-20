import { describe, expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    getService,
    makeMockEnv,
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
