/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { LoadableDataSource } from "@spreadsheet/data_sources/data_source";
import { Deferred } from "@web/core/utils/concurrency";
import { makeServerError } from "@web/../tests/helpers/mock_server";

QUnit.module("spreadsheet data source", {}, () => {
    QUnit.test(
        "data source is ready after all concurrent requests are resolved",
        async (assert) => {
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
                notify: () => {},
            });
            dataSource.load();
            dataSource.load({ reload: true });
            assert.strictEqual(dataSource.isReady(), false);
            def1.resolve();
            await nextTick();
            assert.strictEqual(dataSource.isReady(), false);
            def2.resolve();
            await nextTick();
            assert.strictEqual(dataSource.isReady(), true);
        }
    );

    QUnit.test("Datasources handle errors thrown at _load", async (assert) => {
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
            notify: () => {},
            orm: {
                call: () => {
                    throw makeServerError({ description: "Ya done!" });
                },
            },
        });
        await dataSource.load();
        assert.ok(dataSource._isFullyLoaded);
        assert.notOk(dataSource._isValid);
        assert.equal(dataSource._loadErrorMessage, "Ya done!");
    });
});
