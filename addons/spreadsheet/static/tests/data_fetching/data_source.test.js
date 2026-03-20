import { animationFrame } from "@odoo/hoot-mock";
import { LoadableDataSource } from "@spreadsheet/data_sources/data_source";
import { Deferred } from "@web/core/utils/concurrency";
import { makeServerError } from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineSpreadsheetActions, defineSpreadsheetModels } from "../helpers/data";

describe.current.tags("headless");

defineSpreadsheetModels();
defineSpreadsheetActions();

test("data source is ready after all concurrent requests are resolved", async () => {
    const def1 = new Deferred();
    const def2 = new Deferred();
    let req = 0;
    class TestDataSource extends LoadableDataSource {
        constructor() {
            super(...arguments);
            this.data = null;
        }
        async _load() {
            this.data = null;
            switch (++req) {
                case 1:
                    await def1;
                    break;
                case 2:
                    await def2;
                    break;
            }
            this.data = "something";
        }
    }
    const dataSource = new TestDataSource({
        odooDataProvider: {
            notify: () => expect.step("notify"),
            notifyWhenPromiseResolves: () => expect.step("notify-from-promise"),
            cancelPromise: () => expect.step("cancel-promise"),
        },
    });
    dataSource.load();
    expect.verifySteps(["notify-from-promise"]);
    dataSource.load({ reload: true });
    expect(dataSource.isReady()).toBe(false);
    def1.resolve();
    await animationFrame();
    expect.verifySteps(["cancel-promise", "notify-from-promise"]);
    expect(dataSource.isReady()).toBe(false);
    def2.resolve();
    await animationFrame();
    expect(dataSource.isReady()).toBe(true);
    expect.verifySteps([]);
});

test("Datasources handle errors thrown at _load", async () => {
    class TestDataSource extends LoadableDataSource {
        constructor() {
            super(...arguments);
            this.data = null;
        }
        async _load() {
            this.data = await this._orm.call();
        }
    }

    const dataSource = new TestDataSource({
        odooDataProvider: {
            notify: () => expect.step("notify"),
            notifyWhenPromiseResolves: () => expect.step("notify-from-promise"),
            cancelPromise: () => expect.step("cancel-promise"),
            orm: {
                call: () => {
                    throw makeServerError({ description: "Ya done!" });
                },
            },
        },
    });
    await dataSource.load();
    expect.verifySteps(["notify-from-promise"]);
    expect(dataSource._isFullyLoaded).toBe(true);
    expect(dataSource._isValid).toBe(false);
    expect(dataSource._loadError.message).toBe("Ya done!");
});
