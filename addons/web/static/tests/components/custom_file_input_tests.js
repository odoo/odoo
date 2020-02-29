odoo.define('web.custom_file_input_tests', function (require) {
    "use strict";

    const CustomFileInput = require('web.CustomFileInput');
    const makeTestEnvironment = require('web.test_env');
    const testUtils = require('web.test_utils');

    const { Component, tags, useState } = owl;
    const { xml } = tags;

    QUnit.module('Components', {}, function () {

        // This module cannot be tested as thoroughly as we want it to be:
        // browsers do not let scripts programmatically assign values to inputs
        // of type file
        QUnit.module('CustomFileInput', {}, function () {
            QUnit.test("Rendering of all props", async function (assert) {
                assert.expect(12);

                class Parent extends Component {
                    constructor() {
                        super(...arguments);
                        this.state = useState({ innerContent: '<a href="#">Trigger</a>' });
                    }
                    // Handlers
                    _onFileUploaded(ev) {
                        assert.strictEqual(ev.detail.files.length, 0,
                            "'files' property should be an empty array");
                    }
                }
                Parent.components = { CustomFileInput };
                Parent.env = makeTestEnvironment({
                    services: {
                        httpRequest: (route, params) => {
                            if (route === '/web/binary/upload') {
                                assert.deepEqual(params, {
                                    csrf_token: odoo.csrf_token,
                                    ufile: [],
                                });
                                assert.step(route);
                                return Promise.resolve('[]');
                            } else if (route === '/web/binary/upload_attachment') {
                                assert.deepEqual(params, {
                                    id: 5,
                                    model: 'res.model',
                                    csrf_token: odoo.csrf_token,
                                    ufile: [],
                                });
                                assert.step(route);
                                return Promise.resolve('[]');
                            }
                        },
                    },
                });
                Parent.template = xml`
                    <CustomFileInput
                        accepted_file_extensions="state.accepted_file_extensions"
                        action="state.action"
                        id="state.id"
                        model="state.model"
                        multi_upload="state.multi_upload"
                        t-on-uploaded="_onFileUploaded"
                        >
                        <t t-raw="state.innerContent"/>
                    </CustomFileInput>`;

                const parent = new Parent();
                await parent.mount(testUtils.prepareTarget());
                const fileInput = parent.el;
                const input = fileInput.querySelector('input');

                // Default props
                assert.strictEqual(fileInput.innerText.trim(), "Trigger",
                    "File input total text should match its given inner element's text");
                assert.strictEqual(input.accept, '*',
                    "Input should accept all files by default");
                await testUtils.dom.triggerEvent(input, 'change');
                assert.notOk(input.multiple,
                    "'multiple' attribute should not be set");

                // Change props
                Object.assign(parent.state, {
                    accepted_file_extensions: '.png',
                    action: '/web/binary/upload_attachment',
                    id: 5,
                    model: 'res.model',
                    multi_upload: true,
                });
                await testUtils.nextTick();

                assert.strictEqual(input.accept, '.png',
                    "Input should now only accept pngs");
                await testUtils.dom.triggerEvent(input, 'change');
                assert.ok(input.multiple,
                    "'multiple' attribute should be set");

                assert.verifySteps(['/web/binary/upload', '/web/binary/upload_attachment']);

                parent.destroy();
            });
        });
    });
});
