odoo.define('web.mockserver_tests', function (require) {
"use strict";

const MockServer = require("web.MockServer");

QUnit.module("MockServer", {
    beforeEach() {
        this.data = {
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
        };
    },
}, function () {
    QUnit.test("performRpc: search_read with an empty array of fields", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search_read",
            args: [],
            kwargs: {
                fields: [],
            },
        });
        const expectedFields = ["id", "email", "name", "display_name"];
        assert.strictEqual(_.difference(expectedFields, Object.keys(result[0])).length, 0,
            "should contains all the fields");
    });

    QUnit.test("performRpc: search_read without fields", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search_read",
            args: [],
            kwargs: {},
        });
        const expectedFields = ["id", "email", "name", "display_name"];
        assert.strictEqual(_.difference(expectedFields, Object.keys(result[0])).length, 0,
            "should contains all the fields");
    });

    QUnit.test("performRpc: name_get with no args", async function (assert) {
        assert.expect(2);
        const server = new MockServer(this.data, {});
        try {
            await server.performRpc("", {
                model: "res.partner",
                method: "name_get",
                args: [],
                kwargs: {},
            });
        } catch (error) {
            assert.step("name_get failed")
        }
        assert.verifySteps(["name_get failed"])
    });

    QUnit.test("performRpc: name_get with undefined arg", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "name_get",
            args: [undefined],
            kwargs: {},
        });
        assert.deepEqual(result, [])
    });

    QUnit.test("performRpc: name_get with a single id", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "name_get",
            args: [1],
            kwargs: {},
        });
        assert.deepEqual(result, [[1, "Jean-Michel"]]);
    });

    QUnit.test("performRpc: name_get with array of ids", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "name_get",
            args: [[1]],
            kwargs: {},
        });
        assert.deepEqual(result, [[1, "Jean-Michel"]]);
    });

    QUnit.test("performRpc: name_get with invalid id", async function (assert) {
        assert.expect(2);
        const server = new MockServer(this.data, {});
        try {
            await server.performRpc("", {
                model: "res.partner",
                method: "name_get",
                args: [11111],
                kwargs: {},
            });
        } catch (error) {
            assert.step("name_get failed")
        }
        assert.verifySteps(["name_get failed"])
    });

    QUnit.test("performRpc: name_get with id and undefined id", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "name_get",
            args: [[undefined, 1]],
            kwargs: {},
        });
        assert.deepEqual(result, [[null, "False"], [1, "Jean-Michel"]]);
    });

    QUnit.test("performRpc: search with active_test=false", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search",
            args: [[]],
            kwargs: {
                context: { active_test: false },
            },
        });
        assert.deepEqual(result, [1, 2]);
    });

    QUnit.test("performRpc: search with active_test=true", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search",
            args: [[]],
            kwargs: {
                context: { active_test: true },
            },
        });
        assert.deepEqual(result, [1]);
    });

    QUnit.test("performRpc: search_read with active_test=false", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["name"],
                context: { active_test: false },
            },
        });
        assert.deepEqual(result, [{id: 1, name: "Jean-Michel"}, {id: 2, name: "Raoul"}]);
    });

    QUnit.test("performRpc: search_read with active_test=true", async function (assert) {
        assert.expect(1);
        const server = new MockServer(this.data, {});
        const result = await server.performRpc("", {
            model: "res.partner",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["name"],
                context: { active_test: true },
            },
        });
        assert.deepEqual(result, [{id: 1, name: "Jean-Michel"}]);
    });
});
});
