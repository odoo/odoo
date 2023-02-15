/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import BatchEndpoint, { Request, ServerData } from "@spreadsheet/data_sources/server_data";

QUnit.module("spreadsheet server data", {}, () => {
    QUnit.test("simple synchronous get", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(
            () => serverData.get("partner", "get_something", [5]),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        await nextTick();
        assert.verifySteps(["partner/get_something", "data-fetched-notification"]);
        assert.deepEqual(serverData.get("partner", "get_something", [5]), 5);
        assert.verifySteps([]);
    });

    QUnit.test("synchronous get which returns an error", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                throw new Error("error while fetching data");
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(
            () => serverData.get("partner", "get_something", [5]),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        await nextTick();
        assert.verifySteps(["partner/get_something", "data-fetched-notification"]);
        assert.throws(() => serverData.get("partner", "get_something", [5]), Error);
        assert.verifySteps([]);
    });

    QUnit.test("simple async fetch", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        const result = await serverData.fetch("partner", "get_something", [5]);
        assert.deepEqual(result, 5);
        assert.verifySteps(["partner/get_something"]);
        assert.deepEqual(await serverData.fetch("partner", "get_something", [5]), 5);
        assert.verifySteps([]);
    });

    QUnit.test("async fetch which throws an error", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                throw new Error("error while fetching data");
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.rejects(serverData.fetch("partner", "get_something", [5]));
        assert.verifySteps(["partner/get_something"]);
        assert.rejects(serverData.fetch("partner", "get_something", [5]));
        assert.verifySteps([]);
    });

    QUnit.test("two identical concurrent async fetch", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        const [result1, result2] = await Promise.all([
            serverData.fetch("partner", "get_something", [5]),
            serverData.fetch("partner", "get_something", [5]),
        ]);
        assert.verifySteps(["partner/get_something"], "it should have fetch the data once");
        assert.deepEqual(result1, 5);
        assert.deepEqual(result2, 5);
        assert.verifySteps([]);
    });

    QUnit.test("batch get with a single item", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 5),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        await nextTick();
        assert.verifySteps(["partner/get_something_in_batch", "data-fetched-notification"]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 5), 5);
        assert.verifySteps([]);
    });

    QUnit.test("batch get with multiple items", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 5),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 6),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        await nextTick();
        assert.verifySteps(["partner/get_something_in_batch", "data-fetched-notification"]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 5), 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 6), 6);
        assert.verifySteps([]);
    });

    QUnit.test("batch get with one error", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                if (args[0].includes(5)) {
                    throw new Error("error while fetching data");
                }
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 4),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 5),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        assert.throws(
            () => serverData.batch.get("partner", "get_something_in_batch", 6),
            LoadingDataError,
            "it should throw when it's not loaded"
        );
        await nextTick();
        assert.verifySteps([
            // one call for the batch
            "partner/get_something_in_batch",
            // retries one by one
            "partner/get_something_in_batch",
            "partner/get_something_in_batch",
            "partner/get_something_in_batch",
            "data-fetched-notification",
        ]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 4), 4);
        assert.throws(() => serverData.batch.get("partner", "get_something_in_batch", 5), Error);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 6), 6);
        assert.verifySteps([]);
    });

    QUnit.test("concurrently fetch then get the same request", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        const promise = serverData.fetch("partner", "get_something", [5]);
        assert.throws(() => serverData.get("partner", "get_something", [5]), LoadingDataError);
        const result = await promise;
        await nextTick();
        assert.verifySteps(
            ["partner/get_something", "partner/get_something", "data-fetched-notification"],
            "it loads the data independently"
        );
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.get("partner", "get_something", [5]), 5);
        assert.verifySteps([]);
    });

    QUnit.test("concurrently get then fetch the same request", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(() => serverData.get("partner", "get_something", [5]), LoadingDataError);
        const result = await serverData.fetch("partner", "get_something", [5]);
        assert.verifySteps(
            ["partner/get_something", "partner/get_something", "data-fetched-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.get("partner", "get_something", [5]), 5);
        assert.verifySteps([]);
    });

    QUnit.test("concurrently batch get then fetch the same request", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(() => serverData.batch.get("partner", "get_something", 5), LoadingDataError);
        const result = await serverData.fetch("partner", "get_something", [5]);
        await nextTick();
        assert.verifySteps(
            ["partner/get_something", "partner/get_something", "data-fetched-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something", 5), 5);
        assert.verifySteps([]);
    });

    QUnit.test("concurrently get and batch get the same request", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataIsFetched: () => assert.step("data-fetched-notification"),
        });
        assert.throws(() => serverData.batch.get("partner", "get_something", 5), LoadingDataError);
        assert.throws(() => serverData.get("partner", "get_something", [5]), LoadingDataError);
        await nextTick();
        assert.verifySteps(
            ["partner/get_something", "data-fetched-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(serverData.get("partner", "get_something", [5]), 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something", 5), 5);
        assert.verifySteps([]);
    });

    QUnit.test("Call the correct callback after a batch result", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                if (args[0].includes(5)) {
                    throw new Error("error while fetching data");
                }
                return args[0];
            },
        };
        const batchEndpoint = new BatchEndpoint(orm, "partner", "get_something", {
            whenDataIsFetched: () => {},
            successCallback: () => assert.step("success-callback"),
            failureCallback: () => assert.step("failure-callback"),
        });
        const request = new Request("partner", "get_something", [4]);
        const request2 = new Request("partner", "get_something", [5]);
        batchEndpoint.call(request);
        batchEndpoint.call(request2);
        assert.verifySteps([]);
        await nextTick();
        console.log("Passe");
        assert.verifySteps(["success-callback", "failure-callback"]);
    });
});
