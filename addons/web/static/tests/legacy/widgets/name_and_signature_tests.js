/** @odoo-module **/

    import { NameAndSignature } from "@web/legacy/js/widgets/name_and_signature";
    import makeTestEnvironment from "../helpers/test_env";
    import { patchWithCleanup } from "@web/../tests/helpers/utils";
    import { Component } from "@odoo/owl";

    const MockedNameAndSignature = NameAndSignature.extend({
        events: {
            ...NameAndSignature.prototype.events,
            'signature_changed': () => {},
        },
        _onChangeSignature: () => {},
        _drawCurrentName: () => {},
    });

    async function MockedNameAndSignatureGenerator (options) {
        const parent = $("#qunit-fixture");
        patchWithCleanup(Component, {
            env: await makeTestEnvironment({}, (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return Promise.resolve();
                }
            }),
        });
        const mockedNameAndSignature = new MockedNameAndSignature(parent, options);
        await mockedNameAndSignature.appendTo(parent);
        await mockedNameAndSignature.resetSignature();
        return mockedNameAndSignature;
    }

    QUnit.module('widgets legacy', {}, function () {
        QUnit.module('name_and_signature', {
            beforeEach: function () {
                this.defaultName = 'Don Toliver'
            },
        }, function () {
            QUnit.test("test name_and_signature widget", async function (assert) {
                assert.expect(5);
                const nameAndSignature = await MockedNameAndSignatureGenerator({
                    defaultName: this.defaultName
                });
                assert.equal(nameAndSignature.signMode, 'auto');
                const nameInput = nameAndSignature.$el.find('.o_web_sign_name_input');
                assert.ok(nameInput.length);
                assert.equal(this.defaultName, nameInput.val());
                const drawButton = nameAndSignature.$el.find('.o_web_sign_draw_button');
                assert.ok(drawButton.length);
                await drawButton.click();
                assert.equal(nameAndSignature.signMode, 'draw');
            });

            QUnit.test("test name_and_signature widget without name", async function (assert) {
                assert.expect(4);
                const nameAndSignature = await MockedNameAndSignatureGenerator({});
                assert.equal(nameAndSignature.signMode, 'auto');
                assert.ok(nameAndSignature.signatureAreaHidden);
                const nameInput = nameAndSignature.$el.find('.o_web_sign_name_input');
                assert.ok(nameInput.length);
                await nameInput.val(this.defaultName).trigger('input');
                assert.notOk(nameAndSignature.signatureAreaHidden);
            });

            QUnit.test("test name_and_signature widget with noInputName and default name", async function (assert) {
                assert.expect(1);
                const nameAndSignature = await MockedNameAndSignatureGenerator({
                    noInputName: true,
                    defaultName: this.defaultName
                });
                assert.equal(nameAndSignature.signMode, 'auto');
            });

            QUnit.test("test name_and_signature widget with noInputName", async function (assert) {
                assert.expect(1);
                const nameAndSignature = await MockedNameAndSignatureGenerator({
                    noInputName: true,
                });
                assert.equal(nameAndSignature.signMode, 'draw');
            });
        });
    });
