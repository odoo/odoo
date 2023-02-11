odoo.define('web.abstract_model_tests', function (require) {
    "use strict";

    const AbstractModel = require('web.AbstractModel');
    const Domain = require('web.Domain');

    QUnit.module('Views', {}, function () {
        QUnit.module('AbstractModel');

        QUnit.test('leave sample mode when unknown route is called on sample server', async function (assert) {
            assert.expect(4);

            const Model = AbstractModel.extend({
                _isEmpty() {
                    return true;
                },
                async __load() {
                    if (this.isSampleModel) {
                        await this._rpc({ model: 'partner', method: 'unknown' });
                    }
                },
            });

            const model = new Model(null, {
                modelName: 'partner',
                fields: {},
                useSampleModel: true,
                SampleModel: Model,
            });

            assert.ok(model.useSampleModel);
            assert.notOk(model._isInSampleMode);

            await model.load({});

            assert.notOk(model.useSampleModel);
            assert.notOk(model._isInSampleMode);

            model.destroy();
        });

        QUnit.test("don't cath general error on sample server in sample mode", async function (assert) {
            assert.expect(5);

            const error = new Error();

            const Model = AbstractModel.extend({
                _isEmpty() {
                    return true;
                },
                async __reload() {
                    if (this.isSampleModel) {
                        await this._rpc({ model: 'partner', method: 'read_group' });
                    }
                },
                async _rpc() {
                    throw error;
                },
            });

            const model = new Model(null, {
                modelName: 'partner',
                fields: {},
                useSampleModel: true,
                SampleModel: Model,
            });

            assert.ok(model.useSampleModel);
            assert.notOk(model._isInSampleMode);

            await model.load({});

            assert.ok(model.useSampleModel);
            assert.ok(model._isInSampleMode);

            async function reloadModel() {
                try {
                    await model.reload();
                } catch (e) {
                    assert.strictEqual(e, error);
                }
            }

            await reloadModel();

            model.destroy();
        });

        QUnit.test('fetch sample data: concurrency', async function (assert) {
            assert.expect(3);

            const Model = AbstractModel.extend({
                _isEmpty() {
                    return true;
                },
                __get() {
                    return { isSample: !!this.isSampleModel };
                },
            });

            const model = new Model(null, {
                modelName: 'partner',
                fields: {},
                useSampleModel: true,
                SampleModel: Model,
            });

            await model.load({ domain: Domain.FALSE_DOMAIN, });

            const beforeReload = model.get(null, { withSampleData: true });

            const reloaded = model.reload(null, { domain: Domain.TRUE_DOMAIN });
            const duringReload = model.get(null, { withSampleData: true });

            await reloaded;

            const afterReload = model.get(null, { withSampleData: true });

            assert.strictEqual(beforeReload.isSample, true,
                "Sample data flag must be true before reload"
            );
            assert.strictEqual(duringReload.isSample, true,
                "Sample data flag must be true during reload"
            );
            assert.strictEqual(afterReload.isSample, false,
                "Sample data flag must be true after reload"
            );
        });
    });
});
