odoo.define('web.data_manager_tests', function (require) {
    "use strict";

    const config = require('web.config');
    const DataManager = require('web.DataManager');
    const MockServer = require('web.MockServer');
    const rpc = require('web.rpc');
    const testUtils = require('web.test_utils');

    /**
     * Create a simple data manager with mocked functions:
     * - mockRPC -> rpc.query
     * - isDebug -> config.isDebug
     * @param {Object} params
     * @param {Object} params.archs
     * @param {Object} params.data
     * @param {Function} params.isDebug
     * @param {Function} params.mockRPC
     * @returns {DataManager}
     */
    function createDataManager({ archs, data, isDebug, mockRPC }) {
        const dataManager = new DataManager();
        const server = new MockServer(data, { archs });

        const serverMethods = {
            async load_views({ kwargs, model }) {
                const { options, views } = kwargs;
                const fields = server.fieldsGet(model);
                const fields_views = {};
                for (const [viewId, viewType] of views) {
                    const arch = archs[[model, viewId || false, viewType].join()];
                    fields_views[viewType] = server.fieldsViewGet({ arch, model, viewId });
                }
                const result = { fields, fields_views };
                if (options.load_filters) {
                    result.filters = data['ir.filters'].records.filter(r => r.model_id === model);
                }
                return result;
            },
            async get_filters({ args, model }) {
                return data[model].records.filter(r => r.model_id === args[0]);
            },
            async create_or_replace({ args }) {
                const id = data['ir.filters'].records.reduce((i, r) => Math.max(i, r.id), 0) + 1;
                const filter = Object.assign(args[0], { id });
                data['ir.filters'].records.push(filter);
                return id;
            },
            async unlink({ args }) {
                data['ir.filters'].records = data['ir.filters'].records.filter(
                    r => r.id !== args[0]
                );
                return true;
            },
        };

        testUtils.mock.patch(rpc, {
            async query({ method }) {
                this._super = serverMethods[method].bind(this, ...arguments);
                return mockRPC.apply(this, arguments);
            },
        });
        testUtils.mock.patch(config, { isDebug });

        return dataManager;
    }

    QUnit.module("Services", {
        beforeEach() {
            this.archs = {
                'oui,10,kanban': '<kanban/>',
                'oui,20,search': '<search/>',
            };
            this.data = {
                oui: { fields: {}, records: [] },
                'ir.filters': {
                    fields: {
                        context: { type: "Text", string: "Context" },
                        domain: { type: "Text", string: "Domain" },
                        model_id: { type: "Selection", string: "Model" },
                        name: { type: "Char", string: "Name" },
                    },
                    records: [{
                        id: 2,
                        context: '{}',
                        domain: '[]',
                        model_id: 'oui',
                        name: "Favorite",
                    }]
                }
            };
            this.loadViewsParams = {
                model: "oui",
                context: {},
                views_descr: [
                    [10, 'kanban'],
                    [20, 'search'],
                ],
            };
        },
        afterEach() {
            testUtils.mock.unpatch(rpc);
            testUtils.mock.unpatch(config);
        },
    }, function () {

        QUnit.module("Data manager");

        QUnit.test("Load views with filters (non-debug mode)", async function (assert) {
            assert.expect(4);

            const dataManager = createDataManager({
                archs: this.archs,
                data: this.data,
                isDebug() {
                    return false;
                },
                async mockRPC({ method, model }) {
                    assert.step([model, method].join('.'));
                    return this._super(...arguments);
                },
            });

            const firstLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            const secondLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            const filters = await dataManager.load_filters({ modelName: 'oui' });

            assert.deepEqual(firstLoad, secondLoad,
                "query with same params and options should yield the same results");
            assert.deepEqual(firstLoad.search.favoriteFilters, filters,
                "load filters should yield the same result as the first load_views' filters");
            assert.verifySteps(['oui.load_views'],
                "only load once when not in assets debugging");
        });

        QUnit.test("Load views with filters (debug mode)", async function (assert) {
            assert.expect(6);

            const dataManager = createDataManager({
                archs: this.archs,
                data: this.data,
                isDebug() {
                    return true; // assets
                },
                async mockRPC({ method, model }) {
                    assert.step([model, method].join('.'));
                    return this._super(...arguments);
                },
            });

            const firstLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            const secondLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            const filters = await dataManager.load_filters({ modelName: 'oui' });

            assert.deepEqual(firstLoad, secondLoad,
                "query with same params and options should yield the same results");
            assert.deepEqual(firstLoad.search.favoriteFilters, filters,
                "load filters should yield the same result as the first load_views' filters");
            assert.verifySteps([
                'oui.load_views',
                'oui.load_views',
                'ir.filters.get_filters',
            ], "reload each time when in assets debugging");
        });

        QUnit.test("Cache invalidation and filters addition/deletion", async function (assert) {
            assert.expect(10);

            const dataManager = createDataManager({
                archs: this.archs,
                data: this.data,
                isDebug() {
                    return false; // Cache only works if 'debug !== assets'
                },
                async mockRPC({ method, model }) {
                    assert.step([model, method].join('.'));
                    return this._super(...arguments);
                },
            });

            // A few unnecessary 'load_filters' are done in this test to assert
            // that the cache invalidation mechanics are working.
            let filters;

            const firstLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            // Cache is valid -> should not trigger an RPC
            filters = await dataManager.load_filters({ modelName: 'oui' });
            assert.deepEqual(firstLoad.search.favoriteFilters, filters,
                "load_filters and load_views.search should return the same filters");

            const filterId = await dataManager.create_filter({
                context: "{}",
                domain: "[]",
                model_id: 'oui',
                name: "Temp",
            });
            // Cache is not valid anymore -> triggers a 'get_filters'
            filters = await dataManager.load_filters({ modelName: 'oui' });
            // Cache is valid -> should not trigger an RPC
            filters = await dataManager.load_filters({ modelName: 'oui' });

            assert.strictEqual(filters.length, 2,
                "A new filter should have been added");
            assert.ok(filters.find(f => f.id === filterId) === filters[filters.length - 1],
                "Create filter should return the id of the last created filter");

            await dataManager.delete_filter(filterId);

            // Views cache is valid but filters cache is not -> triggers a 'get_filters'
            const secondLoad = await dataManager.load_views(this.loadViewsParams, {
                load_filters: true,
            });
            filters = secondLoad.search.favoriteFilters;
            // Filters cache is once again valid -> no RPC
            const expectedFilters = await dataManager.load_filters({ modelName: 'oui' });

            assert.deepEqual(filters, expectedFilters,
                "Filters loaded by the load_views should be equal to the result of a load_filters");

            assert.verifySteps([
                'oui.load_views',
                'ir.filters.create_or_replace',
                'ir.filters.get_filters',
                'ir.filters.unlink',
                'ir.filters.get_filters',
            ], "server should have been called only when needed");
        });
    });
});
