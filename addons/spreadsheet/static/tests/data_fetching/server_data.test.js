import { animationFrame } from "@odoo/hoot-mock";
import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { BatchEndpoint, Request, ServerData } from "@spreadsheet/data_sources/server_data";
import { Deferred } from "@web/core/utils/concurrency";
import { describe, expect, test } from "@odoo/hoot";
import { defineSpreadsheetActions, defineSpreadsheetModels } from "../helpers/data";

describe.current.tags("headless");

defineSpreadsheetModels();
defineSpreadsheetActions();

test("simple synchronous get", async () => {
    const orm = {
        call: async (model, method, args) => {
            expect.step(`${model}/${method}`);
            return args[0];
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.get("partner", "get_something", [5])).toThrow(LoadingDataError, {
        message: "it should throw when it's not loaded",
    });
    expect.verifySteps(["partner/get_something", "data-fetching-notification"]);
    await animationFrame();
    expect(serverData.get("partner", "get_something", [5])).toBe(5);
    expect.verifySteps([]);
});

test("synchronous get which returns an error", async () => {
    const orm = {
        call: async (model, method, args) => {
            expect.step(`${model}/${method}`);
            throw new Error("error while fetching data");
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.get("partner", "get_something", [5])).toThrow(LoadingDataError, {
        message: "it should throw when it's not loaded",
    });
    expect.verifySteps(["partner/get_something", "data-fetching-notification"]);
    await animationFrame();
    expect(() => serverData.get("partner", "get_something", [5])).toThrow(Error);
    expect.verifySteps([]);
});

test("batch get with a single item", async () => {
    const deferred = new Deferred();
    const orm = {
        call: async (model, method, args) => {
            await deferred;
            expect.step(`${model}/${method}`);
            return args[0];
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 5)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    await animationFrame(); // wait for the next tick for the batch to be called
    expect.verifySteps(["data-fetching-notification"]);
    deferred.resolve();
    await animationFrame();
    expect.verifySteps(["partner/get_something_in_batch"]);
    expect(serverData.batch.get("partner", "get_something_in_batch", 5)).toBe(5);
    expect.verifySteps([]);
});

test("batch get with multiple items", async () => {
    const orm = {
        call: async (model, method, args) => {
            expect.step(`${model}/${method}`);
            return args[0];
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 5)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 6)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    await animationFrame();
    expect.verifySteps(["partner/get_something_in_batch", "data-fetching-notification"]);
    expect(serverData.batch.get("partner", "get_something_in_batch", 5)).toBe(5);
    expect(serverData.batch.get("partner", "get_something_in_batch", 6)).toBe(6);
    expect.verifySteps([]);
});

test("batch get with one error", async () => {
    const orm = {
        call: async (model, method, args) => {
            expect.step(`${model}/${method}`);
            if (args[0].includes(5)) {
                throw new Error("error while fetching data");
            }
            return args[0];
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 4)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 5)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 6)).toThrow(
        LoadingDataError,
        { message: "it should throw when it's not loaded" }
    );
    await animationFrame();
    expect.verifySteps([
        // one call for the batch
        "partner/get_something_in_batch",
        "data-fetching-notification",
        // retries one by one
        "partner/get_something_in_batch",
        "partner/get_something_in_batch",
        "partner/get_something_in_batch",
    ]);
    expect(serverData.batch.get("partner", "get_something_in_batch", 4)).toBe(4);
    expect(() => serverData.batch.get("partner", "get_something_in_batch", 5)).toThrow(Error);
    expect(serverData.batch.get("partner", "get_something_in_batch", 6)).toBe(6);
    expect.verifySteps([]);
});

test("concurrently get and batch get the same request", async () => {
    const orm = {
        call: async (model, method, args) => {
            expect.step(`${model}/${method}`);
            return args[0];
        },
    };
    const serverData = new ServerData(orm, {
        whenDataStartLoading: () => expect.step("data-fetching-notification"),
    });
    expect(() => serverData.batch.get("partner", "get_something", 5)).toThrow(LoadingDataError);
    expect(() => serverData.get("partner", "get_something", [5])).toThrow(LoadingDataError);
    await animationFrame();
    // it should have fetch the data once
    expect.verifySteps(["partner/get_something", "data-fetching-notification"]);
    expect(serverData.get("partner", "get_something", [5])).toBe(5);
    expect(serverData.batch.get("partner", "get_something", 5)).toBe(5);
    expect.verifySteps([]);
});

test("Call the correct callback after a batch result", async () => {
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
        successCallback: () => expect.step("success-callback"),
        failureCallback: () => expect.step("failure-callback"),
    });
    const request = new Request("partner", "get_something", [4]);
    const request2 = new Request("partner", "get_something", [5]);
    batchEndpoint.call(request);
    batchEndpoint.call(request2);
    expect.verifySteps([]);
    await animationFrame();
    expect.verifySteps(["success-callback", "failure-callback"]);
});
