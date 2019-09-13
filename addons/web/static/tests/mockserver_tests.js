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
                },
                records: [{ id: 1, name: "Jean-Michel", email: "jean.michel@example.com" }],
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
});
});
