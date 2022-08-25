/** @odoo-module **/

import { multiTabService } from '../src/multi_tab_service';

import { browser } from '@web/core/browser/browser';
import { registry } from '@web/core/registry';
import { makeTestEnv } from '@web/../tests/helpers/mock_env';
import { patchWithCleanup, nextTick } from '@web/../tests/helpers/utils';

QUnit.module('bus', function () {
    QUnit.module('multi_tab_service_tests.js');

    QUnit.test('multi tab service elects new master on unload', async function (assert) {
        assert.expect(5);

        registry.category('services').add('multi_tab', multiTabService);

        const firstTabEnv = await makeTestEnv();
        assert.ok(firstTabEnv.services['multi_tab'].isOnMainTab(), 'only tab should be the main one');

        // prevent second tab from receiving unload event.
        patchWithCleanup(browser, {
            addEventListener(eventName, callback) {
                if (eventName === 'unload') {
                    return;
                }
                this._super(eventName, callback);
            },
        });
        const secondTabEnv = await makeTestEnv();
        firstTabEnv.services["multi_tab"].bus.addEventListener("no_longer_main_tab", () =>
            assert.step("tab1 no_longer_main_tab")
        );
        secondTabEnv.services["multi_tab"].bus.addEventListener("no_longer_main_tab", () =>
            assert.step("tab2 no_longer_main_tab")
        );
        window.dispatchEvent(new Event('unload'));

        // Let the multi tab elect a new main.
        await nextTick();
        assert.notOk(firstTabEnv.services['multi_tab'].isOnMainTab());
        assert.ok(secondTabEnv.services['multi_tab'].isOnMainTab());
        assert.verifySteps(['tab1 no_longer_main_tab']);
    });

    QUnit.test('multi tab allow to share values between tabs', async function (assert) {
        assert.expect(3);

        registry.category('services').add('multi_tab', multiTabService);

        const firstTabEnv = await makeTestEnv();
        const secondTabEnv = await makeTestEnv();

       firstTabEnv.services['multi_tab'].setSharedValue('foo', 1);
       assert.deepEqual(secondTabEnv.services['multi_tab'].getSharedValue('foo'), 1);
       firstTabEnv.services['multi_tab'].setSharedValue('foo', 2);
       assert.deepEqual(secondTabEnv.services['multi_tab'].getSharedValue('foo'), 2);

       firstTabEnv.services['multi_tab'].removeSharedValue('foo');
       assert.notOk(secondTabEnv.services['multi_tab'].getSharedValue('foo'));
    });

    QUnit.test('multi tab triggers shared_value_updated', async function (assert) {
        assert.expect(4);

        registry.category('services').add('multi_tab', multiTabService);

        const firstTabEnv = await makeTestEnv();
        const secondTabEnv = await makeTestEnv();

        secondTabEnv.services['multi_tab'].bus.addEventListener('shared_value_updated', ({ detail }) => {
            assert.step(`${detail.key} - ${JSON.parse(detail.newValue)}`);
        });
        firstTabEnv.services['multi_tab'].setSharedValue('foo', 'bar');
        firstTabEnv.services['multi_tab'].setSharedValue('foo', 'foo');
        firstTabEnv.services['multi_tab'].removeSharedValue('foo');

        await nextTick();
        assert.verifySteps([
            'foo - bar',
            'foo - foo',
            'foo - null',
        ]);
    });

    QUnit.test('multi tab triggers become_master', async function (assert) {
        registry.category('services').add('multi_tab', multiTabService);

        await makeTestEnv();
        // prevent second tab from receiving unload event.
        patchWithCleanup(browser, {
            addEventListener(eventName, callback) {
                if (eventName === 'unload') {
                    return;
                }
                this._super(eventName, callback);
            },
        });
        const secondTabEnv = await makeTestEnv();
        secondTabEnv.services['multi_tab'].bus.addEventListener('become_main_tab', () => assert.step('become_main_tab'));
        window.dispatchEvent(new Event('unload'));

        // Let the multi tab elect a new main.
        await nextTick();
        assert.verifySteps(['become_main_tab']);
    });
});
