odoo.define('barcodes.barcode_mobile_tests', function () {
    "use strict";

    QUnit.module('Barcodes', {}, function () {

        QUnit.module('Barcodes Mobile');

        QUnit.test('barcode field automatically focus behavior', function (assert) {
            assert.expect(10);

            // Mock Chrome mobile environment
            var barcodeEvents = odoo.__DEBUG__.services["barcodes.BarcodeEvents"].BarcodeEvents;
            var __isChromeMobile = barcodeEvents.isChromeMobile;
            barcodeEvents.isChromeMobile = true;
            // Rebind keyboard events
            barcodeEvents.stop();
            barcodeEvents.start();

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
            $('body').keydown();
            assert.strictEqual(document.activeElement.name, 'barcode',
                "hidden barcode input should have the focus");

            var $element = $form.find('select');
            $element.focus().keydown();
            assert.strictEqual(document.activeElement.name, 'barcode',
                "hidden barcode input should have the focus");

            // Those elements absolutely need to keep the focus:
            // inputs elements:
            var keepFocusedElements = ['email', 'number', 'password', 'tel',
                'text', 'explicit_text'];
            for (var i = 0; i < keepFocusedElements.length; ++i) {
                $element = $form.find('input[name=' + keepFocusedElements[i] + ']');
                $element.focus().keydown();
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
            $element.focus().keydown();
            assert.strictEqual(document.activeElement, $element[0],
                "contenteditable should keep focus");

            $('#qunit-fixture').empty();
            barcodeEvents.isChromeMobile = __isChromeMobile;
            // Rebind keyboard events
            barcodeEvents.stop();
            barcodeEvents.start();

            document.querySelector('input[name=barcode]').remove();
        });
    });
    });
