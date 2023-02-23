odoo.define('barcodes.barcode_mobile_tests', function (require) {
    "use strict";

    const {barcodeService} = require("@barcodes/barcode_service");
    const {barcodeRemapperService} = require("@barcodes/js/barcode_events");
    const { makeTestEnv } = require("@web/../tests/helpers/mock_env");
    const { registry } = require("@web/core/registry");
    var testUtils = require('web.test_utils');

    const maxTimeBetweenKeysInMs = barcodeService.maxTimeBetweenKeysInMs;
    const isMobileChrome = barcodeService.isMobileChrome;
    var triggerEvent = testUtils.dom.triggerEvent;

    function triggerKeyDown(char, target = document.body) {
        let keycode;
        if (char === 'Enter') {
            keycode = $.ui.keyCode.ENTER;
        } else if (char === "Tab") {
            keycode = $.ui.keyCode.TAB;
        } else {
            keycode = char.charCodeAt(0);
        }
        triggerEvent(target, 'keydown', {
            key: char,
            keyCode: keycode,
        });
    }
    
    QUnit.module('Barcodes', {
        before() {
            barcodeService.maxTimeBetweenKeysInMs = 0;
            barcodeService.isMobileChrome = true;
            registry.category("services").add("barcode", barcodeService, { force: true});
            // remove this one later
            registry.category("services").add("barcode_remapper", barcodeRemapperService);
            this.env = makeTestEnv();
        },
        after() {
            barcodeService.maxTimeBetweenKeysInMs = maxTimeBetweenKeysInMs;
            barcodeService.isMobileChrome = isMobileChrome;
        },
    }, function () {

        QUnit.module('Barcodes Mobile');

        QUnit.test('barcode field automatically focus behavior', function (assert) {
            assert.expect(10);

            var $form = $(
                '<form>' +
                    '<input name="email" type="email"/>' +
                    '<input name="number" type="number"/>' +
                    '<input name="password" type="password"/>' +
                    '<input name="tel" type="tel"/>' +
                    '<input name="text"/>' +
                    '<input name="explicit_text" type="text"/>' +
                    '<textarea></textarea>' +
                    '<div contenteditable="true"></div>' +
                    '<select name="select">' +
                        '<option value="option1">Option 1</option>' +
                        '<option value="option2">Option 2</option>' +
                    '</select>' +
                '</form>');
            $('#qunit-fixture').append($form);

            // Some elements doesn't need to keep the focus
            triggerKeyDown('a', document.body)
            assert.strictEqual(document.activeElement.name, 'barcode',
                "hidden barcode input should have the focus");

            var $element = $form.find('select');
            $element.focus();
            triggerKeyDown('b', $element[0]);
            assert.strictEqual(document.activeElement.name, 'barcode',
                "hidden barcode input should have the focus");

            // Those elements absolutely need to keep the focus:
            // inputs elements:
            var keepFocusedElements = ['email', 'number', 'password', 'tel',
                'text', 'explicit_text'];
            for (var i = 0; i < keepFocusedElements.length; ++i) {
                $element = $form.find('input[name=' + keepFocusedElements[i] + ']');
                $element.focus();
                triggerKeyDown('c', $element[0]);
    
                assert.strictEqual(document.activeElement, $element[0],
                    "input " + keepFocusedElements[i] + " should keep focus");
            }
            // textarea element
            $element = $form.find('textarea');
            $element.focus().keydown();
            assert.strictEqual(document.activeElement, $element[0],
                "textarea should keep focus");
            // contenteditable elements
            $element = $form.find('[contenteditable=true]');
            $element.focus();
            triggerKeyDown('d', $element[0]);
            assert.strictEqual(document.activeElement, $element[0],
                "contenteditable should keep focus");

            $('#qunit-fixture').empty();
            document.querySelector('input[name=barcode]').remove();
        });
    });
    });
