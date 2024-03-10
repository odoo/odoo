/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { BatchEndpoint, Request, ServerData } from "@spreadsheet/data_sources/server_data";
import { Deferred } from "@web/core/utils/concurrency";

QUnit.module("spreadsheet server data", {}, () => {
    QUnit.test("simple synchronous get", async (assert) => {
        const orm = {
            call: async (model, method, args) => {
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isPending(), true);
        assert.verifySteps(["partner/get_something", "data-fetching-notification"]);
        await nextTick();
        assert.deepEqual(serverData.get("partner", "get_something", [5]).value, 5);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isPending(), true);
        assert.verifySteps(["partner/get_something", "data-fetching-notification"]);
        await nextTick();
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isRejected(), true);
        assert.strictEqual(
            serverData.get("partner", "get_something", [5]).errorMessage,
            "error while fetching data"
        );
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        const result = await serverData.fetch("partner", "get_something", [5]);
        assert.deepEqual(result, 5);
        assert.verifySteps(["partner/get_something", "data-fetching-notification"]);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.rejects(serverData.fetch("partner", "get_something", [5]));
        assert.verifySteps(["partner/get_something", "data-fetching-notification"]);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        const [result1, result2] = await Promise.all([
            serverData.fetch("partner", "get_something", [5]),
            serverData.fetch("partner", "get_something", [5]),
        ]);
        assert.verifySteps(
            ["partner/get_something", "data-fetching-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(result1, 5);
        assert.deepEqual(result2, 5);
        assert.verifySteps([]);
    });

    QUnit.test("batch get with a single item", async (assert) => {
        const deferred = new Deferred();
        const orm = {
            call: async (model, method, args) => {
                await deferred;
                assert.step(`${model}/${method}`);
                return args[0];
            },
        };
        const serverData = new ServerData(orm, {
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 5).isPending(),
            true
        );
        await nextTick(); // wait for the next tick for the batch to be called
        assert.verifySteps(["data-fetching-notification"]);
        deferred.resolve();
        await nextTick();
        assert.verifySteps(["partner/get_something_in_batch"]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 5).value, 5);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 5).isPending(),
            true
        );
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 6).isPending(),
            true
        );
        await nextTick();
        assert.verifySteps(["partner/get_something_in_batch", "data-fetching-notification"]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 5).value, 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 6).value, 6);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 4).isPending(),
            true
        );
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 5).isPending(),
            true
        );
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 6).isPending(),
            true
        );
        await nextTick();
        assert.verifySteps([
            // one call for the batch
            "partner/get_something_in_batch",
            "data-fetching-notification",
            // retries one by one
            "partner/get_something_in_batch",
            "partner/get_something_in_batch",
            "partner/get_something_in_batch",
        ]);
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 4).value, 4);
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 5).isRejected(),
            true
        );
        assert.strictEqual(
            serverData.batch.get("partner", "get_something_in_batch", 5).errorMessage,
            "error while fetching data"
        );
        assert.deepEqual(serverData.batch.get("partner", "get_something_in_batch", 6).value, 6);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        const promise = serverData.fetch("partner", "get_something", [5]);
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isPending(), true);
        assert.verifySteps(
            ["partner/get_something", "data-fetching-notification"],
            "it loads the data independently"
        );
        const result = await promise;
        await nextTick();
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.get("partner", "get_something", [5]).value, 5);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isPending(), true);
        const result = await serverData.fetch("partner", "get_something", [5]);
        assert.verifySteps(
            ["partner/get_something", "data-fetching-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.get("partner", "get_something", [5]).value, 5);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(serverData.batch.get("partner", "get_something", 5).isPending(), true);
        const result = await serverData.fetch("partner", "get_something", [5]);
        await nextTick();
        assert.verifySteps(
            ["partner/get_something", "data-fetching-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(result, 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something", 5).value, 5);
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
            whenDataStartLoading: () => assert.step("data-fetching-notification"),
        });
        assert.strictEqual(serverData.batch.get("partner", "get_something", 5).isPending(), true);
        assert.strictEqual(serverData.get("partner", "get_something", [5]).isPending(), true);
        await nextTick();
        assert.verifySteps(
            ["partner/get_something", "data-fetching-notification"],
            "it should have fetch the data once"
        );
        assert.deepEqual(serverData.get("partner", "get_something", [5]).value, 5);
        assert.deepEqual(serverData.batch.get("partner", "get_something", 5).value, 5);
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
            whenDataStartLoading: () => {},
            successCallback: () => assert.step("success-callback"),
            failureCallback: () => assert.step("failure-callback"),
        });
        const request = new Request("partner", "get_something", [4]);
        const request2 = new Request("partner", "get_something", [5]);
        batchEndpoint.call(request);
        batchEndpoint.call(request2);
        assert.verifySteps([]);
        await nextTick();
        assert.verifySteps(["success-callback", "failure-callback"]);
    });
});
