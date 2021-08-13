/** @odoo-module **/

import { MockServer } from "./helpers/mock_server";

QUnit.module("Mock Server", {
    beforeEach() {
        this.data = {
            models: {
                "res.partner": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "string",
                        },
                        email: {
                            string: "Email",
                            type: "string",
                        },
                        active: {
                            string: "Active",
                            type: "bool",
                            default: true,
                        },
                    },
                    records: [
                        { id: 1, name: "Jean-Michel", email: "jean.michel@example.com" },
                        { id: 2, name: "Raoul", email: "raoul@example.com", active: false },
                    ],
                },
            },
        };
    },
});

QUnit.test("performRPC: search with active_test=false", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search",
        args: [[]],
        kwargs: {
            context: { active_test: false },
        },
    });
    const ids = result.map((record) => record.id);
    assert.deepEqual(ids, [1, 2]);
});

QUnit.test("performRPC: search with active_test=true", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search",
        args: [[]],
        kwargs: {
            context: { active_test: true },
        },
    });
    const ids = result.map((record) => record.id);
    assert.deepEqual(ids, [1]);
});

QUnit.test("performRPC: search_read with active_test=false", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search_read",
        args: [[]],
        kwargs: {
            fields: ["name"],
            context: { active_test: false },
        },
    });
    assert.deepEqual(result, [
        { id: 1, name: "Jean-Michel" },
        { id: 2, name: "Raoul" },
    ]);
});

QUnit.test("performRPC: search_read with active_test=true", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search_read",
        args: [[]],
        kwargs: {
            fields: ["name"],
            context: { active_test: true },
        },
    });
    assert.deepEqual(result, [{ id: 1, name: "Jean-Michel" }]);
});
