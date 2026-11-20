/** @odoo-module **/
import convertInline from '@web_editor/js/backend/convert_inline';
import {getGridHtml, getTableHtml, getRegularGridHtml, getRegularTableHtml, getTdHtml, removeComments} from '@web_editor/../tests/test_utils';

const TEST_WIDTH = 800;
const TEST_HEIGHT = 600;

QUnit.module('web_editor', {}, function () {
QUnit.module('convert_inline', {}, function () {
    QUnit.module('Convert Bootstrap grids to tables', {
        beforeEach: function (assert) {
            this.editable = document.createElement('div');
            this.editable.style.setProperty('width', TEST_WIDTH + 'px');
            this.editable.style.setProperty('height', TEST_HEIGHT + 'px');
            document.querySelector('#qunit-fixture').append(this.editable);
            this.testConvertGrid = ({ before, after, title, stepFunction }) => {
                this.editable.innerHTML = before;
                (stepFunction || convertInline.bootstrapToTable)(this.editable);
                // Remove class that is added by `bootstrapToTable` for use in
                // further methods of `toInline`, and removed at the end of it.
                this.editable.querySelectorAll('.o_converted_col').forEach(node => {
                    node.classList.remove('o_converted_col');
                    if (!node.classList.length) {
                        node.removeAttribute('class');
                    }
                });
                assert.strictEqual(removeComments(this.editable.innerHTML), after, title);
            }
        }
    });
    // Test bootstrapToTable, cardToTable and listGroupToTable

    QUnit.test('convert a single-row regular grid', async function (assert) {
        assert.expect(4);

        // 1x1
        this.testConvertGrid({
            before: getRegularGridHtml(1, 1),
            after: getRegularTableHtml(1, 1, 12, 100, TEST_WIDTH),
            title: "should have converted a 1x1 grid to an equivalent table",
        });

        // 1x2
        this.testConvertGrid({
            before: getRegularGridHtml(1, 2),
            after: getRegularTableHtml(1, 2, 6, 50, TEST_WIDTH),
            title: "should have converted a 1x2 grid to an equivalent table",
        });

        // 1x3
        this.testConvertGrid({
            before: getRegularGridHtml(1, 3),
            after: getRegularTableHtml(1, 3, 4, 33.33, TEST_WIDTH),
            title: "should have converted a 1x3 grid to an equivalent table",
        });

        // 1x12
        this.testConvertGrid({
            before: getRegularGridHtml(1, 12),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH),
            title: "should have converted a 1x12 grid to an equivalent table",
        });
    });
    QUnit.test('convert a single-row regular overflowing grid', async function (assert) {
        assert.expect(4);

        // 1x13
        this.testConvertGrid({
            before: getRegularGridHtml(1, 13),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(0, 12)', TEST_WIDTH) + getTdHtml(11, '', TEST_WIDTH) +
                `</tr></table>`,
            title: "should have converted a 1x13 grid to an equivalent table (overflowing)",
        });

        // 1x14
        this.testConvertGrid({
            before: getRegularGridHtml(1, 14),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(0, 12)', TEST_WIDTH) + getTdHtml(1, '(0, 13)', TEST_WIDTH) + getTdHtml(10, '', TEST_WIDTH) +
                `</tr></table>`,
            title: "should have converted a 1x14 grid to an equivalent table (overflowing)",
        });

        // 1x25
        this.testConvertGrid({
            before: getRegularGridHtml(1, 25),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).slice(0, -8) +
                getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).replace(/\(0, (\d+)\)/g, (s, c) => `(0, ${+c + 12})`)
                    .replace(/^<table[^<]*>/, '').slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(0, 24)', TEST_WIDTH) + getTdHtml(11, '', TEST_WIDTH) +
                `</tr></table>`,
            title: "should have converted a 1x25 grid to an equivalent table (overflowing)",
        });

        // 1x26
        this.testConvertGrid({
            before: getRegularGridHtml(1, 26),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).slice(0, -8) +
                getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).replace(/\(0, (\d+)\)/g, (s, c) => `(0, ${+c + 12})`)
                    .replace(/^<table[^<]*>/, '').slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(0, 24)', TEST_WIDTH) + getTdHtml(1, '(0, 25)', TEST_WIDTH) + getTdHtml(10, '', TEST_WIDTH) +
                `</tr></table>`,
            title: "should have converted a 1x26 grid to an equivalent table (overflowing)",
        });
    });
    QUnit.test('convert a multi-row regular grid', async function (assert) {
        assert.expect(4);

        // 2x1
        this.testConvertGrid({
            before: getRegularGridHtml(2, 1),
            after: getRegularTableHtml(2, 1, 12, 100, TEST_WIDTH),
            title: "should have converted a 2x1 grid to an equivalent table",
        });

        // 2x[1,2]
        this.testConvertGrid({
            before: getRegularGridHtml(2, [1, 2]),
            after: getRegularTableHtml(2, [1, 2], [12, 6], [100, 50], TEST_WIDTH),
            title: "should have converted a 2x[1,2] grid to an equivalent table",
        });

        // 3x3
        this.testConvertGrid({
            before: getRegularGridHtml(3, 3),
            after: getRegularTableHtml(3, 3, 4, 33.33, TEST_WIDTH),
            title: "should have converted a 3x3 grid to an equivalent table",
        });

        // 3x[3,2,1]
        this.testConvertGrid({
            before: getRegularGridHtml(3, [3,2,1]),
            after: getRegularTableHtml(3, [3, 2, 1], [4, 6, 12], [33.33, 50, 100], TEST_WIDTH),
            title: "should have converted a 3x[3,2,1] grid to an equivalent table",
        });
    });
    QUnit.test('convert a multi-row regular overflowing grid', async function (assert) {
        assert.expect(4);

        // 2x[13,1]
        this.testConvertGrid({
            before: getRegularGridHtml(2, [13, 1]),
            after: getRegularTableHtml(1, 12, 1, 8.33, TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(0, 12)', TEST_WIDTH) +
                getTdHtml(11, '', TEST_WIDTH) + // 13 overflowed the row by 1 -> fill up
                `</tr>` +
                `<tr>${getTdHtml(12, '(1, 0)', TEST_WIDTH)}</tr></table>`, // 1 col with no size == col-12
            title: "should have converted a 2x[13,1] grid to an equivalent table (overflowing)",
        });

        // 2x[1,13]
        this.testConvertGrid({
            before: getRegularGridHtml(2, [1, 13]),
            after: getRegularTableHtml(2, [1, 12], [12, 1], [100, 8.33], TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(1, 12)', TEST_WIDTH) +
                getTdHtml(11, '', TEST_WIDTH) + // 13 overflowed the row by 1 -> fill up
                `</tr></table>`,
            title: "should have converted a 2x[1,13] grid to an equivalent table (overflowing)",
        });

        // 3x[1,13,6]
        this.testConvertGrid({
            before: getRegularGridHtml(3, [1, 13, 6]),
            after: getRegularTableHtml(2, [1, 12], [12, 1], [100, 8.33], TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(1, 12)', TEST_WIDTH) +
                getTdHtml(11, '', TEST_WIDTH) + // 13 overflowed the row by 1 -> fill up
                `</tr>` +
                getRegularTableHtml(1, 6, 2, 16.67, TEST_WIDTH).replace(/\(0,/g, `(2,`).replace(/^<table[^<]*>/, ''),
            title: "should have converted a 3x[1,13,6] grid to an equivalent table (overflowing)",
        });

        // 3x[1,6,13]
        this.testConvertGrid({
            before: getRegularGridHtml(3, [1, 6, 13]),
            after: getRegularTableHtml(3, [1, 6, 12], [12, 2, 1], [100, 16.67, 8.33], TEST_WIDTH).slice(0, -8) +
                `<tr>` +
                getTdHtml(1, '(2, 12)', TEST_WIDTH) +
                getTdHtml(11, '', TEST_WIDTH) + // 13 overflowed the row by 1 -> fill up
                `</tr></table>`,
            title: "should have converted a 3x[1,6,13] grid to an equivalent table (overflowing)",
        });
    });
    QUnit.test('convert a single-row irregular grid', async function (assert) {
        assert.expect(2);

        // 1x2
        this.testConvertGrid({
            before: getGridHtml([[8, 4]]),
            after: getTableHtml([[[8, 66.67], [4, 33.33]]], TEST_WIDTH),
            title: "should have converted a 1x2 irregular grid to an equivalent table",
        });

        // 1x3
        this.testConvertGrid({
            before: getGridHtml([[2, 3, 7]]),
            after: getTableHtml([[[2, 16.67], [3, 25], [7, 58.33]]], TEST_WIDTH),
            title: "should have converted a 1x3 grid to an equivalent table",
        });
    });
    QUnit.test('convert a single-row irregular overflowing grid', async function (assert) {
        assert.expect(2);

        // 1x2
        this.testConvertGrid({
            before: getGridHtml([[8, 5]]),
            after: getTableHtml([
                [[8, 66.67], [4, 33.33, '']],
                [[5, 41.67, '(0, 1)'], [7, 58.33, '']],
            ], TEST_WIDTH),
            title: "should have converted a 1x2 irregular overflowing grid to an equivalent table",
        });

        // 1x3
        this.testConvertGrid({
            before: getGridHtml([[7, 6, 9]]),
            after: getTableHtml([
                [[7, 58.33], [5, 41.67, '']],
                [[6, 50, '(0, 1)'], [6, 50, '']],
                [[9, 75, '(0, 2)'], [3, 25, '']],
            ], TEST_WIDTH),
            title: "should have converted a 1x3 irregular overflowing grid to an equivalent table",
        });
    });
    QUnit.test('convert a multi-row irregular grid', async function (assert) {
        assert.expect(2);

        // 2x2
        this.testConvertGrid({
            before: getGridHtml([[1, 11], [2, 10]]),
            after: getTableHtml([[[1, 8.33], [11, 91.67]], [[2, 16.67], [10, 83.33]]], TEST_WIDTH),
            title: "should have converted a 2x2 irregular grid to an equivalent table",
        });

        // 2x[2,3]
        this.testConvertGrid({
            before: getGridHtml([[3, 9], [4, 6, 2]]),
            after: getTableHtml([[[3, 25], [9, 75]], [[4, 33.33], [6, 50], [2, 16.67]]], TEST_WIDTH),
            title: "should have converted a 2x[2,3] irregular grid to an equivalent table",
        });
    });
    QUnit.test('convert a multi-row irregular overflowing grid', async function (assert) {
        assert.expect(3);

        // 2x2 (both rows overflow)
        this.testConvertGrid({
            before: getGridHtml([[6, 8], [7, 9]]),
            after: getTableHtml([
                [[6, 50], [6, 50, '']],
                [[8, 66.67, '(0, 1)'], [4, 33.33, '']],
                [[7, 58.33, '(1, 0)'], [5, 41.67, '']],
                [[9, 75, '(1, 1)'], [3, 25, '']],
            ], TEST_WIDTH),
            title: "should have converted a 2x[1,13] irregular grid to an equivalent table (both rows overflowing)",
        });

        // 2x[2,3] (first row overflows)
        this.testConvertGrid({
            before: getGridHtml([[5, 8], [4, 2, 6]]),
            after: getTableHtml([
                [[5, 41.67], [7, 58.33, '']],
                [[8, 66.67, '(0, 1)'], [4, 33.33, '']],
                [[4, 33.33, '(1, 0)'], [2, 16.67, '(1, 1)'], [6, 50, '(1, 2)']],
            ], TEST_WIDTH),
            title: "should have converted a 2x[2,3] irregular grid to an equivalent table (first row overflowing)",
        });

        // 2x[3,2] (second row overflows)
        this.testConvertGrid({
            before: getGridHtml([[4, 2, 6], [5, 8]]),
            after: getTableHtml([
                [[4, 33.33], [2, 16.67], [6, 50]],
                [[5, 41.67], [7, 58.33, '']],
                [[8, 66.67, '(1, 1)'], [4, 33.33, '']],
            ], TEST_WIDTH),
            title: "should have converted a 2x[3,2] irregular grid to an equivalent table (second row overflowing)",
        });
    });
    QUnit.test('convert a card to a table', async function (assert) {
        assert.expect(1);

        this.testConvertGrid({
            title: "should have converted a card structure into a table",
            before:
                `<div class="card">` +
                    `<div class="card-header">` +
                        `<span>HEADER</span>` +
                    `</div>` +
                    `<div class="card-body">` +
                        `<h2 class="card-title">TITLE</h2>` +
                        `<small>BODY <img></small>` +
                    `</div>` +
                    `<div class="card-footer">` +
                        `<a href="#" class="btn">FOOTER</a>` +
                    `</div>` +
                `</div>`,
            stepFunction: convertInline.cardToTable,
            after: getRegularTableHtml(3, 1, 12, 100)
                .replace('role=\"presentation\"', 'role=\"presentation\" class=\"card\"')
                .replace(/<td[^>]*>\(0, 0\)<\/td>/,
                    `<td>` +
                        `<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\" align=\"center\" ` +
                        `role=\"presentation\" style=\"width: 100% !important; border-collapse: collapse; text-align: inherit; ` +
                        `font-size: unset; line-height: inherit;\"><tr>` +
                            `<td class="card-header"><span>HEADER</span></td>` +
                        `</tr></table></td>`)
                .replace(/<td[^>]*>\(1, 0\)<\/td>/,
                    `<td>` +
                        `<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\" align=\"center\" ` +
                        `role=\"presentation\" style=\"width: 100% !important; border-collapse: collapse; text-align: inherit; ` +
                        `font-size: unset; line-height: inherit;\"><tr>` +
                            `<td class="card-body"><h2 class="card-title">TITLE</h2><small>BODY <img></small></td>` +
                        `</tr></table></td>`)
                .replace(/<td[^>]*>\(2, 0\)<\/td>/,
                    `<td>` +
                        `<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\" align=\"center\" ` +
                        `role=\"presentation\" style=\"width: 100% !important; border-collapse: collapse; text-align: inherit; ` +
                        `font-size: unset; line-height: inherit;\"><tr>` +
                            `<td class="card-footer"><a href="#" class="btn">FOOTER</a></td>` +
                        `</tr></table></td>`),
        });
    });
    QUnit.test('convert a list group to a table', async function (assert) {
        assert.expect(1);

        this.testConvertGrid({
            title: "should have converted a list group structure into a table",
            before:
                `<ul class="list-group list-group-flush">` +
                    `<li class="list-group-item">` +
                        `<strong>(0, 0)</strong>` +
                    `</li>` +
                    `<li class="list-group-item a">` +
                        `(1, 0)` +
                    `</li>` +
                    `<li><img></li>` +
                    `<li class="list-group-item">` +
                        `<strong class="b">(2, 0)</strong>` +
                    `</li>` +
                `</ul>`,
            stepFunction: convertInline.listGroupToTable,
            after: getRegularTableHtml(3, 1, 12, 100)
                .split('style="').join('class="list-group-flush" style="')
                .replace(/<td[^>]*>(\(0, 0\))<\/td>/, '<td><strong>$1</strong></td>')
                .replace(/<td[^>]*>(\(1, 0\))<\/td>/, '<td class="a">$1</td>')
                .replace(/<tr><td[^>]*>(\(2, 0\))<\/td>/, '<img><tr><td><strong class="b">$1</strong></td>'),
        });
    });
    QUnit.test('convert a grid with offsets to a table', async function (assert) {
        assert.expect(2);

        this.testConvertGrid({
            before: '<div class="container"><div class="row"><div class="col-6 offset-4">(0, 0)</div></div>',
            after: getTableHtml([[[4, 33.33, ''], [6, 50, '(0, 0)'], [2, 16.67, '']]], TEST_WIDTH),
            title: "should have converted a column with an offset to two columns, then completed the column",
        });

        this.testConvertGrid({
            before: '<div class="container"><div class="row"><div class="col-6 offset-4">(0, 0)</div><div class="col-6 offset-1">(0, 1)</div></div>',
            after: getTableHtml([
                [[4, 33.33, ''], [6, 50, '(0, 0)'], [1, 8.33, ''], [1, 8.33, '']],
                [[6, 50, '(0, 1)'], [6, 50, '']]
            ], TEST_WIDTH),
            title: "should have converted a column with an offset to two columns, then completed the column (overflowing)",
        });
    });

    QUnit.module('Normalize styles');
    // Test normalizeColors, normalizeRem and formatTables

    QUnit.test('convert rgb color to hexadecimal', async function (assert) {
        assert.expect(1);

        const $editable = $(
            `<div><div style="color: rgb(0, 0, 0);">` +
                `<div class="a" style="padding: 0; background-color:rgb(255,255,255)" width="100%">` +
                    `<p style="border: 1px rgb(50, 100,200 ) solid; color: rgb(35, 134, 54);">Test</p>` +
                `</div>` +
            `</div></div>`
        );
        convertInline.normalizeColors($editable);
        assert.strictEqual($editable.html(),
            `<div style="color: #000000;">` +
                `<div class="a" style="padding: 0; background-color:#ffffff" width="100%">` +
                    `<p style="border: 1px #3264c8 solid; color: #238636;">Test</p>` +
                `</div>` +
            `</div>`,
            "should have converted several rgb colors to hexadecimal"
        );
    });
    QUnit.test('convert rem sizes to px', async function (assert) {
        assert.expect(2);

        const testDom = `<div style="font-size: 2rem;">` +
            `<div class="a" style="color: #000000; padding: 2.5 rem" width="100%">` +
                `<p style="border: 1.2rem #aaaaaa solid; margin: 3.79rem;">Test</p>` +
            `</div>` +
        `</div>`;

        let $editable = $(`<div>${testDom}</div>`);
        document.body.append($editable[0]);
        convertInline.normalizeRem($editable);
        assert.strictEqual($editable.html(),
            `<div style="font-size: 32px;">` +
                `<div class="a" style="color: #000000; padding: 40px" width="100%">` +
                    `<p style="border: 19.2px #aaaaaa solid; margin: 60.64px;">Test</p>` +
                `</div>` +
            `</div>`,
            "should have converted several rem sizes to px using the default rem size"
        );
        $editable.remove();

        $editable = $(`<div>${testDom}</div>`);
        document.body.append($editable[0]);
        convertInline.normalizeRem($editable, 20);
        assert.strictEqual($editable.html(),
            `<div style="font-size: 40px;">` +
                `<div class="a" style="color: #000000; padding: 50px" width="100%">` +
                    `<p style="border: 24px #aaaaaa solid; margin: 75.8px;">Test</p>` +
                `</div>` +
            `</div>`,
            "should have converted several rem sizes to px using a set rem size"
        );
        $editable.remove();
    });
    QUnit.test('move padding from snippet containers to cells', async function (assert) {
        assert.expect(1);

        const testTable = `<table class="o_mail_snippet_general" style="padding: 10px 20px 30px 40px;">` +
            `<tbody>` +
                `<tr>` +
                    `<td style="padding-top: 1px; padding-right: 2px;">(0, 0, 0)</td>` +
                    `<td style="padding: 3px 4px 5px 6px;">(0, 1, 0)</td>` +
                    `<td style="padding: 7px;">(0, 2, 0)</td>` +
                    `<td style="padding: 8px 9px;">(0, 3, 0)</td>` +
                    `<td style="padding-right: 9.1px;">(0, 4, 0)</td>` +
                `</tr>` +
                `<tr>` +
                    `<td>` +
                        `<table style="padding: 50px 60px 70px 80px;">` +
                            `<tbody>` +
                                `<tr>` +
                                    `<td style="padding: 1px 2px 3px 4px;">(0, 0, 1)</td>` +
                                    `<td style="padding: 5px;">(0, 1, 1)</td>` +
                                    `<td style="padding: 6px 7px;">(0, 2, 1)</td>` +
                                    `<td style="padding-top: 8px; padding-right: 9px;">(0, 3, 1)</td>` +
                                `</tr>` +
                            `</tbody>` +
                        `</table>` +
                    `</td>` +
                `</tr>` +
                `<tr>` +
                    `<td style="padding-left: 9.1px;">(1, 0, 0)</td>` +
                    `<td style="padding: 9px 8px 7px 6px;">(1, 1, 0)</td>` +
                    `<td style="padding: 5px;">(1, 2, 0)</td>` +
                    `<td style="padding: 4px 3px;">(1, 3, 0)</td>` +
                    `<td style="padding-bottom: 2px; padding-right: 1px;">(1, 4, 0)</td>` +
                `</tr>` +
            `</tbody>` +
        `</table>`;

        const expectedTable = `<table class="o_mail_snippet_general" style="">` +
            `<tbody>` +
                `<tr>` +
                    `<td style="padding-top: 11px; padding-right: 2px; padding-left: 40px;">(0, 0, 0)</td>` + // TL
                    `<td style="padding: 13px 4px 5px 6px;">(0, 1, 0)</td>` + // T
                    `<td style="padding: 17px 7px 7px;">(0, 2, 0)</td>` + // T
                    `<td style="padding: 18px 9px 8px;">(0, 3, 0)</td>` + // T
                    `<td style="padding-right: 29.1px; padding-top: 10px;">(0, 4, 0)</td>` + // TR
                `</tr>` +
                `<tr>` +
                    `<td style="padding-right: 20px; padding-left: 40px;">` + // LR
                        `<table style="">` +
                            `<tbody>` +
                                `<tr>` +
                                    `<td style="padding: 51px 2px 73px 84px;">(0, 0, 1)</td>` + // TBL
                                    `<td style="padding: 55px 5px 75px;">(0, 1, 1)</td>` + // TB
                                    `<td style="padding: 56px 7px 76px;">(0, 2, 1)</td>` + // TB
                                    `<td style="padding-top: 58px; padding-right: 69px; padding-bottom: 70px;">(0, 3, 1)</td>` + // TBR
                                `</tr>` +
                            `</tbody>` +
                        `</table>` +
                    `</td>` +
                `</tr>` +
                `<tr>` +
                    `<td style="padding-left: 49.1px; padding-bottom: 30px;">(1, 0, 0)</td>` + // BL
                    `<td style="padding: 9px 8px 37px 6px;">(1, 1, 0)</td>` + // B
                    `<td style="padding: 5px 5px 35px;">(1, 2, 0)</td>` + // B
                    `<td style="padding: 4px 3px 34px;">(1, 3, 0)</td>` + // B
                    `<td style="padding-bottom: 32px; padding-right: 21px;">(1, 4, 0)</td>` + // BR
                `</tr>` +
            `</tbody>` +
        `</table>`;

        // table.o_mail_snippet_general
        const $editable = $(`<div>${testTable}</div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), expectedTable,
            "should have moved the padding from table.o_mail_snippet_general and table in it to their respective cells"
        );
    });
    QUnit.test('add a tbody to any table that doesn\'t have one', async function (assert) {
        assert.expect(1);

        const $editable = $(`<div>${`<table><tr><td>I don't have a body :'(</td></tr></table>`}</div>`);
        $editable.find('tr').unwrap();
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody style="vertical-align: top;"><tr><td>I don't have a body :'(</td></tr></tbody></table>`,
            "should have added a tbody to a table that didn't have one"
        );
    });
    QUnit.test('add number heights to parents of elements with percent heights', async function (assert) {
        assert.expect(3);

        let $editable = $(`<div>${`<table><tbody><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`}</div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody style="height: 0px;"><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`,
            "should have added a 0 height to the parent of a 100% height element"
        );

        $editable = $(`<div>${`<table><tbody style="height: 200px;"><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`}</div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody style="height: 200px;"><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`,
            "should not have changed the height of the parent of a 100% height element"
        );

        $editable = $(`<div>${`<table><tbody style="height: 50%;"><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`}</div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table style="height: 0px;"><tbody style="height: 50%;"><tr style="height: 100%;"><td>yup</td></tr></tbody></table>`,
            "should have changed the height of the grandparent of a 100% height element"
        );
    });
    QUnit.test('express align-self with vertical-align on table cells', async function (assert) {
        assert.expect(3);

        let $editable = $(`<div><table><tbody><tr><td style="align-self: start;">yup</td></tr></tbody></table></div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody><tr><td style="align-self: start; vertical-align: top;">yup</td></tr></tbody></table>`,
            "should have added a top vertical alignment"
        );

        $editable = $(`<div><table><tbody><tr><td style="align-self: center;">yup</td></tr></tbody></table></div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody><tr><td style="align-self: center; vertical-align: middle;">yup</td></tr></tbody></table>`,
            "should have added a middle vertical alignment"
        );

        $editable = $(`<div><table><tbody><tr><td style="align-self: end;">yup</td></tr></tbody></table></div>`);
        convertInline.formatTables($editable);
        assert.strictEqual($editable.html(), `<table><tbody><tr><td style="align-self: end; vertical-align: bottom;">yup</td></tr></tbody></table>`,
            "should have added a bottom vertical alignment"
        );
    });

    QUnit.module('Convert snippets and mailing bodies to tables');
    // Test addTables

    QUnit.test('convert snippets to tables', async function (assert) {
        assert.expect(2);

        let $editable = $(
            `<div><div class="o_mail_snippet_general">` +
                `<div>Snippet</div>` +
            `</div></div>`
        );
        convertInline.addTables($editable);
        assert.strictEqual($editable.html(),
            getRegularTableHtml(1, 1, 12, 100)
                .split('style=').join('class="o_mail_snippet_general" style=')
                .replace(/<td[^>]*>\(0, 0\)/, '<td>' + getRegularTableHtml(1, 1, 12, 100).replace(/<td[^>]*>\(0, 0\)/, '<td><div>Snippet</div>')),
            "should have converted .o_mail_snippet_general to a special table structure with a table in it"
        );

        $editable = $(
            `<div><div class="o_mail_snippet_general">` +
                `<table><tbody><tr><td>Snippet</td></tr></tbody></table>` +
            `</div></div>`
        );
        convertInline.addTables($editable);
        assert.strictEqual($editable.html(),
            getRegularTableHtml(1, 1, 12, 100)
                .split('style=').join('class="o_mail_snippet_general" style=')
                .replace(/<td[^>]*>\(0, 0\)/, '<td><table><tbody><tr><td>Snippet</td></tr></tbody></table>'),
            "should have converted .o_mail_snippet_general to a special table structure, keeping the table in it"
        );
    });
    QUnit.test('convert mailing bodies to tables', async function (assert) {
        assert.expect(2);

        let $editable = $(
            `<div><div class="o_layout">` +
                `<div>Mailing</div>` +
            `</div></div>`
        );
        convertInline.addTables($editable);
        assert.strictEqual($editable.html(),
            getRegularTableHtml(1, 1, 12, 100)
                .split('style=').join('class="o_layout" style=')
                .replace(' font-size: unset; line-height: inherit;', '') // o_layout keeps those default values
                .replace(/<td[^>]*>\(0, 0\)/, '<td>' + getRegularTableHtml(1, 1, 12, 100).replace(/<td[^>]*>\(0, 0\)/, '<td><div>Mailing</div>')),
            "should have converted .o_layout to a special table structure with a table in it"
        );

        $editable = $(
            `<div><div class="o_layout">` +
                `<table><tbody><tr><td>Mailing</td></tr></tbody></table>` +
            `</div></div>`
        );
        convertInline.addTables($editable);
        assert.strictEqual($editable.html(),
            getRegularTableHtml(1, 1, 12, 100)
                .split('style=').join('class="o_layout" style=')
                .replace(' font-size: unset; line-height: inherit;', '') // o_layout keeps those default values
                .replace(/<td[^>]*>\(0, 0\)/, '<td><table><tbody><tr><td>Mailing</td></tr></tbody></table>'),
            "should have converted .o_layout to a special table structure, keeping the table in it"
        );
    });

    QUnit.module('Convert classes to inline styles');
    // Test classToStyle

    QUnit.test('convert Bootstrap classes to inline styles', async function (assert) {
        assert.expect(1);

        const $editable = $(`<div><div class="container"><div class="row"><div class="col">Hello</div></div></div></div>`);
        $(document.body).append($editable); // editable needs to be in the DOM to compute its dynamic styles.
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        // Some positional properties (eg., padding-right, margin-left) are not
        // concatenated (eg., as padding, margin) because they were defined with
        // variables (var) or calculated (calc).
        const containerStyle = `margin: 0px auto; box-sizing: border-box; max-width: 1320px; padding-left: 16px; padding-right: 16px; width: 100%;`;
        const rowStyle = `box-sizing: border-box; margin-left: -16px; margin-right: -16px; margin-top: 0px;`;
        const colStyle = `box-sizing: border-box; margin-top: 0px; padding-left: 16px; padding-right: 16px; max-width: 100%; width: 100%;`;
        assert.strictEqual($editable.html(),
            `<div class="container" style="${containerStyle}" width="100%">` +
            `<div class="row" style="${rowStyle}">` +
            `<div class="col" style="${colStyle}" width="100%">Hello</div></div></div>`,
            "should have converted the classes of a simple Bootstrap grid to inline styles"
        );
        $editable.remove();
    });
    QUnit.test('simplify border/margin/padding styles', async function (assert) {
        assert.expect(12);

        const $styleSheet = $('<style type="text/css" title="test-stylesheet"/>');
        document.head.appendChild($styleSheet[0])
        const styleSheet = [...document.styleSheets].find(sheet => sheet.title === 'test-stylesheet');

        // border-radius
        styleSheet.insertRule(`
            .test-border-radius {
                border-top-right-radius: 10%;
                border-bottom-right-radius: 20%;
                border-bottom-left-radius: 30%;
                border-top-left-radius: 40%;
            }
        `, 0);
        let $editable = $(`<div>${`<div class="test-border-radius"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-radius" style="border-radius:30%;box-sizing:border-box;"></div>`,
            "should have converted border-[position]-radius styles (from class) to border-radius");
        styleSheet.deleteRule(0);

        // convert all positional styles to a style in the form `property: a b c d`

        styleSheet.insertRule(`
            .test-border {
                border-top-style: dotted;
                border-right-style: dashed;
                border-left-style: solid;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-border"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border" style="border-style:dotted dashed none solid;box-sizing:border-box;"></div>`,
            "should have converted border-[position]-style styles (from class) to border-style");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-margin {
                margin-right: 20px;
                margin-bottom: 30px;
                margin-left: 40px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-margin"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-margin" style="margin:0 20px 30px 40px;box-sizing:border-box;"></div>`,
            "should have converted margin-[position] styles (from class) to margin");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-padding {
                padding-top: 10px;
                padding-bottom: 30px;
                padding-left: 40px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-padding"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-padding" style="padding:10px 0 30px 40px;box-sizing:border-box;"></div>`,
            "should have converted padding-[position] styles (from class) to padding");
        styleSheet.deleteRule(0);

        // convert all positional styles to a style in the form `property: a`

        styleSheet.insertRule(`
            .test-border-uniform {
                border-top-style: dotted;
                border-right-style: dotted;
                border-bottom-style: dotted;
                border-left-style: dotted;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-border-uniform"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-uniform" style="border-style:dotted;box-sizing:border-box;"></div>`,
            "should have converted uniform border-[position]-style styles (from class) to border-style");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-margin-uniform {
                margin-top: 10px;
                margin-right: 10px;
                margin-bottom: 10px;
                margin-left: 10px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-margin-uniform"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-margin-uniform" style="margin:10px;box-sizing:border-box;"></div>`,
            "should have converted uniform margin-[position] styles (from class) to margin");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-padding-uniform {
                padding-top: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
                padding-left: 10px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-padding-uniform"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-padding-uniform" style="padding:10px;box-sizing:border-box;"></div>`,
            "should have converted uniform padding-[position] styles (from class) to padding");
        styleSheet.deleteRule(0);

        // do not convert positional styles that include an "inherit" value

        styleSheet.insertRule(`
            .test-border-inherit {
                border-top-style: dotted;
                border-right-style: dashed;
                border-bottom-style: inherit;
                border-left-style: solid;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-border-inherit"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-inherit" style="box-sizing:border-box;border-left-style:solid;border-bottom-style:inherit;border-right-style:dashed;border-top-style:dotted;"></div>`,
            "should not have converted border-[position]-style styles (from class) to border-style as they include an inherit");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-margin-inherit {
                margin-top: 10px;
                margin-right: inherit;
                margin-bottom: 30px;
                margin-left: 40px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-margin-inherit"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-margin-inherit" style="box-sizing:border-box;margin-left:40px;margin-bottom:30px;margin-right:inherit;margin-top:10px;"></div>`,
            "should not have converted margin-[position] styles (from class) to margin as they include an inherit");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-padding-inherit {
                padding-top: 10px;
                padding-right: 20px;
                padding-bottom: inherit;
                padding-left: 40px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-padding-inherit"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-padding-inherit" style="box-sizing:border-box;padding-left:40px;padding-bottom:inherit;padding-right:20px;padding-top:10px;"></div>`,
            "should have converted padding-[position] styles (from class) to padding as they include an inherit");
        styleSheet.deleteRule(0);

        // do not convert positional styles that include an "initial" value

        // note: `border: initial` is automatically removed (tested in "remove
        // unsupported styles")
        styleSheet.insertRule(`
            .test-margin-initial {
                margin-top: initial;
                margin-right: 20px;
                margin-bottom: 30px;
                margin-left: 40px;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-margin-initial"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-margin-initial" style="box-sizing:border-box;margin-left:40px;margin-bottom:30px;margin-right:20px;margin-top:initial;"></div>`,
            "should not have converted margin-[position] styles (from class) to margin as they include an initial");
        styleSheet.deleteRule(0);

        styleSheet.insertRule(`
            .test-padding-initial {
                padding-top: 10px;
                padding-right: 20px;
                padding-bottom: 30px;
                padding-left: initial;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-padding-initial"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-padding-initial" style="box-sizing:border-box;padding-left:initial;padding-bottom:30px;padding-right:20px;padding-top:10px;"></div>`,
            "should not have converted padding-[position] styles (from class) to padding as they include an initial");
        styleSheet.deleteRule(0);

        $styleSheet.remove();
    });
    QUnit.test('remove unsupported styles', async function (assert) {
        assert.expect(9);

        const $styleSheet = $('<style type="text/css" title="test-stylesheet"/>');
        document.head.appendChild($styleSheet[0])
        const styleSheet = [...document.styleSheets].find(sheet => sheet.title === 'test-stylesheet');

        // text-decoration-[prop]
        styleSheet.insertRule(`
            .test-decoration {
                text-decoration-line: underline;
                text-decoration-color: red;
                text-decoration-style: solid;
                text-decoration-thickness: 10px;
            }
        `, 0);
        let $editable = $(`<div>${`<div class="test-decoration"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-decoration" style="text-decoration:underline;box-sizing:border-box;"></div>`,
            "should have removed all text-decoration-[prop] styles (from class) and kept a simple text-decoration");
        styleSheet.deleteRule(0);

        // border[\w-]*: initial
        styleSheet.insertRule(`
            .test-border-initial {
                border-top-style: dotted;
                border-right-style: dashed;
                border-bottom-style: double;
                border-left-style: initial;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-border-initial"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-initial" style="box-sizing:border-box;border-bottom-style:double;border-right-style:dashed;border-top-style:dotted;"></div>`,
            "should have removed border initial");
        styleSheet.deleteRule(0);

        // display: block
        styleSheet.insertRule(`
            .test-block {
                display: block;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-block"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-block" style="box-sizing:border-box;"></div>`,
            "should have removed display block");
        styleSheet.deleteRule(0);

        // !important
        styleSheet.insertRule(`
            .test-unimportant-color {
                color: blue;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-unimportant-color"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-unimportant-color" style="box-sizing:border-box;color:blue;"></div>`,
            "should have converted a simple color");
        styleSheet.insertRule(`
            .test-important-color {
                color: red !important;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-important-color test-unimportant-color"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-important-color test-unimportant-color" style="box-sizing:border-box;color:red;"></div>`,
            "should have converted an important color and removed the !important");
        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);

        // animation
        styleSheet.insertRule(`
            .test-animation {
                animation: example 5s linear 2s infinite alternate;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-animation"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-animation" style="box-sizing:border-box;"></div>`,
            "should have removed animation style");
        styleSheet.deleteRule(0);
        styleSheet.insertRule(`
            .test-animation-specific {
                animation-name: example;
                animation-duration: 5s;
                animation-timing-function: linear;
                animation-delay: 2s;
                animation-iteration-count: infinite;
                animation-direction: alternate;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-animation-specific"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-animation-specific" style="box-sizing:border-box;"></div>`,
            "should have removed all specific animation styles");
        styleSheet.deleteRule(0);

        // flex
        styleSheet.insertRule(`
            .test-flex {
                flex: 0 1 auto;
                flex-flow: column wrap;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-flex"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-flex" style="box-sizing:border-box;"></div>`,
            "should have removed all flex styles");
        styleSheet.deleteRule(0);
        styleSheet.insertRule(`
            .test-flex-specific {
                display: flex;
                flex-direction: row;
                flex-wrap: wrap;
                flex-basis: auto;
                flex-shrink: 3;
                flex-grow: 4;
            }
        `, 0);
        $editable = $(`<div>${`<div class="test-flex-specific"></div>`}</div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-flex-specific" style="box-sizing:border-box;"></div>`,
            "should have removed all specific flex styles");
        styleSheet.deleteRule(0);

        $styleSheet.remove();
    });
    QUnit.test('give .o_layout the styles of the body', async function (assert) {
        assert.expect(1);

        const $iframe = $('<iframe></iframe>');
        $(document.body).append($iframe);
        const $iframeEditable = $('<div/>');
        $iframe.contents().find('body').append($iframeEditable);
        const $styleSheet = $('<style type="text/css" title="test-stylesheet"/>');
        $iframe.contents().find('head').append($styleSheet);
        const styleSheet = [...$iframe.contents()[0].styleSheets].find(sheet => sheet.title === 'test-stylesheet');

        styleSheet.insertRule(`
            body {
                background-color: red;
                color: white;
                font-size: 50px;
            }
        `, 0);
        $iframeEditable.append(`<div class="o_layout" style="padding: 50px;"></div>`);
        convertInline.classToStyle($iframeEditable, convertInline.getCSSRules($iframeEditable[0].ownerDocument));
        assert.strictEqual($iframeEditable.html(),
            `<div class="o_layout" style="box-sizing:border-box;font-size:50px;color:white;background-color:red;padding: 50px;"></div>`,
            "should have given all styles of body to .o_layout");
        styleSheet.deleteRule(0);

        $iframe.remove();
    });
    QUnit.test('convert classes to styles, preserving specificity', async function (assert) {
        assert.expect(4);

        const $styleSheet = $('<style type="text/css" title="test-stylesheet"/>');
        document.head.appendChild($styleSheet[0])
        const styleSheet = [...document.styleSheets].find(sheet => sheet.title === 'test-stylesheet');

        styleSheet.insertRule(`
            div.test-color {
                color: green;
            }
        `, 0);
        styleSheet.insertRule(`
            .test-color {
                color: red;
            }
        `, 1);
        styleSheet.insertRule(`
            .test-color {
                color: blue;
            }
        `, 2);

        let $editable = $(`<div><span class="test-color"></span></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<span class="test-color" style="box-sizing:border-box;color:blue;"></span>`,
            "should have prioritized the last defined style");

        $editable = $(`<div><div class="test-color"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-color" style="box-sizing:border-box;color:green;"></div>`,
            "should have prioritized the more specific style");

        $editable = $(`<div><div class="test-color" style="color: yellow;"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-color" style="box-sizing:border-box;color: yellow;"></div>`,
            "should have prioritized the inline style");

        styleSheet.insertRule(`
            .test-color {
                color: black !important;
            }
        `, 0);
        $editable = $(`<div><div class="test-color"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-color" style="box-sizing:border-box;color:black;"></div>`,
            "should have prioritized the important style");

        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);

        $styleSheet.remove();
    });

    QUnit.test('Create mso properly', async function (assert) {
        assert.strictEqual(convertInline.createMso('<div>abcde</div>').nodeValue,
            '[if mso]><div>abcde</div><![endif]',
            "Should wrap the content in mso condition");

        assert.strictEqual(convertInline.createMso('<div>ef<!--[if mso]><div>abcd</div><![endif]-->gh</div>').nodeValue,
            '[if mso]><div>ef<div>abcd</div>gh</div><![endif]',
            "Should wrap the content inside one mso condition");

        assert.strictEqual(convertInline.createMso('<div>ef<!--[if !mso]><div>abcd</div><![endif]-->gh</div>').nodeValue,
            '[if mso]><div>efgh</div><![endif]',
            "Should remove nested mso hide condition");
    });

    QUnit.test('Correct border attributes for outlook', async function (assert) {
        assert.expect(3);

        const $styleSheet = $('<style type="text/css" title="test-stylesheet"/>');
        document.head.appendChild($styleSheet[0])
        const styleSheet = [...document.styleSheets].find(sheet => sheet.title === 'test-stylesheet');

        styleSheet.insertRule(`
            .test-border-zero {
                border-bottom-width: 0px;
                border-left-width: 0px;
                border-right-width: 0px;
                border-top-width: 0px;
                border-style: solid;
            }
        `, 0);

        styleSheet.insertRule(`
            .test-border-one {
                border-bottom-width: 1px;
                border-left-width: 1px;
                border-right-width: 1px;
                border-top-width: 1px;
                border-style: solid;
            }
        `, 1);

        styleSheet.insertRule(`
            .test-border-background {
                background-image: url("data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==");
            }
        `, 2);

        let $editable = $(`<div><div class="test-border-zero"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-zero" style="border-style:none;box-sizing:border-box;border-top-width:0px;border-right-width:0px;border-left-width:0px;border-bottom-width:0px;"></div>`,
            "Should change border-style to none",
        );

        $editable = $(`<div><div class="test-border-one"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-one" style="border-style:solid;box-sizing:border-box;border-top-width:1px;border-right-width:1px;border-left-width:1px;border-bottom-width:1px;"></div>`,
            "Should keep border style solid"
        );

        $editable = $(`<div><div class="test-border-zero test-border-background"></div></div>`);
        convertInline.classToStyle($editable, convertInline.getCSSRules($editable[0].ownerDocument));
        assert.strictEqual($editable.html(),
            `<div class="test-border-zero test-border-background" style="border-style:none;box-sizing:border-box;background-image:url(&quot;data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==&quot;);border-top-width:0px;border-right-width:0px;border-left-width:0px;border-bottom-width:0px;"></div>`,
            "Should keep background-image",
        );

        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);
        styleSheet.deleteRule(0);
        $styleSheet.remove();
    });
});

});
