/** @odoo-module **/

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers"
import { dom } from 'web.test_utils';

let target;
let serverData;

QUnit.module('mail', {}, function () {
    QUnit.module('onchange on keydown', {
        async beforeEach() {
            target = getFixture();
            serverData = {
                models: {
                    'res.partner': {
                        fields: {
                            id: {type: 'integer'},
                            description: {type: 'text'},
                        },
                        records: [{
                            id: 1,
                            description: '',
                        }],
                        onchanges: {
                            description: () => {},
                        },
                    }
                }
            };
            setupViewRegistries();
        }
    }, function () {
        QUnit.test('Test that onchange_on_keydown option triggers the onchange properly', async function (assert) {
            assert.expect(3);

            await makeView({
                type: "form",
                resModel: 'res.partner',
                serverData,
                arch: '<form><field name="description" onchange_on_keydown="True" keydown_debounce_delay="0"/></form>',
                mockRPC(route, params) {
                    if (params.method === 'onchange') {
                        // the onchange will be called twice: at record creation & when keydown is detected
                        // the second call should have our description value completed.
                        assert.ok(true);
                        if (params.args[1] && params.args[1].description === 'testing the keydown event') {
                            assert.ok(true);
                        }
                        return {};
                    }
                }
            });

            const textarea = target.querySelector('textarea[id="description"]');
            await dom.click(textarea);
            for (let key of 'testing the keydown event') {
                // trigger each key separately to simulate a user typing
                textarea.value = textarea.value + key;
                await dom.triggerEvent(textarea, 'input', { key: key });
            };

            // only trigger the keydown when typing ends to avoid getting a lot of onchange since the
            // delay is set to 0 for test purposes
            // for real use cases there will be a debounce delay set to avoid spamming the event
            await dom.triggerEvent(textarea, 'keydown');
            await nextTick();
        });
    });
});
