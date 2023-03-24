/** @odoo-module **/
import weUtils from 'web_editor.utils';

QUnit.module('web_editor', {}, function () {
QUnit.module('utils', {}, function () {
    QUnit.module('Utils functions');
    // Test weUtils

    QUnit.test('compare CSS property values', async function (assert) {
        assert.expect(86);

        let $div = $(`<div>abc</div>`);
        let currentProperty = 'font-size';
        function compare(expected, value1, value2, property = currentProperty, $target = $div) {
            // Comparisons are done in both directions if values are different.
            assert.strictEqual(weUtils.areCssValuesEqual(value1, value2, property, $target), expected,
                `'${value1}' should be ${expected ? 'equal to' : 'different from'} '${value2}'`
            );
            if (value1 !== value2) {
                assert.strictEqual(weUtils.areCssValuesEqual(value2, value1, property, $target), expected,
                    `'${value2}' should be ${expected ? 'equal to' : 'different from'} '${value1}'`
                );
            }
        }
        compare(true, '', '');
        compare(true, 'auto', 'auto');
        compare(true, '', 'auto');
        compare(true, '15px', '15px');
        compare(true, '15.0px', '15px');
        compare(true, '15 px', '15px');
        compare(false, '15px', '25px');
        compare(false, '15px', '');
        compare(false, '15px', 'auto');
        compare(true, '15px', '1.5e+1px');
        compare(true, '15px', '1.5e1px');
        compare(true, '15px', '150e-1px');

        currentProperty = 'background-size';
        compare(true, '', '');
        compare(true, 'auto', 'auto');
        compare(true, '', 'auto');
        compare(true, '15px', '15px');
        compare(true, '15.0px', '15px');
        compare(false, '15px', '25px');
        compare(false, '15px', '');
        compare(false, '15px', 'auto');
        compare(true, '', 'auto auto');
        compare(true, 'auto', 'auto auto');
        compare(true, 'auto auto', 'auto auto');
        compare(true, '15px 15px', '15px 15px');
        compare(false, '15px 25px', '15px 15px');
        compare(false, '25px 15px', '15px 15px');
        compare(true, 'auto 15px', 'auto 15px');
        compare(true, '15px auto', '15px auto');
        compare(true, '15px', '15px auto');
        compare(false, 'auto 25px', 'auto 15px');
        compare(false, '25px auto', '15px auto');
        compare(false, '25px', '15px auto');
        compare(true, '15px 15px', '1.5e+1px 1.5e+1px');
        compare(true, '15px 15px', '1.5e1px 1.5e1px');
        compare(true, '15px 15px', '150e-1px 150e-1px');

        currentProperty = 'color';
        compare(true, '', '');
        compare(false, '', '#123456');
        compare(true, '#123456', '#123456');
        compare(false, '#123456', '#654321');
        compare(true, 'rgb(255, 0, 0)', '#FF0000');
        compare(false, 'rgb(255, 0, 0)', '#EE0000');

        currentProperty = 'background-image';
        compare(true, '', '');
        compare(false, '', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(true, 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(false, 'linear-gradient(0deg, rgb(10, 0, 0) 0%, rgb(1, 1, 1) 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(false, 'linear-gradient(10deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(false, 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(10, 1, 1) 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(false, 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(9, 9, 9) 50%, rgb(1, 1, 1) 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(true, 'linear-gradient(0deg, #000000 0%, #010101 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
        compare(false, 'linear-gradient(0deg, #FF0000 0%, #010101 100%)', 'linear-gradient(0deg, rgb(0, 0, 0) 0%, rgb(1, 1, 1) 100%)');
    });
});
});
