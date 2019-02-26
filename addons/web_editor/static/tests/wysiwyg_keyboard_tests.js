odoo.define('web_editor.wysiwyg.keyboard_tests', function (require) {
"use strict";

var weTestUtils = require('web_editor.test_utils');

//--------------------------------------------------------------------------
// tests
//--------------------------------------------------------------------------

QUnit.module('web_editor', {}, function () {
QUnit.module('wysiwyg', {}, function () {

//--------------------------------------------------------------------------
// Unbreakable tests
//--------------------------------------------------------------------------
QUnit.module('Unbreakable');

var unbreakableTestDom = [
    '    <noteditable id="a">',
    '        content_a_0',
    '        <noteditable id="b">content_b_0</noteditable>',
    '        <editable id="c">',
    '            content_c_0',
    '            <noteditable id="d">content_d_0</noteditable>',
    '            <noteditable id="e">',
    '                content_e_0',
    '                <editable id="f">content_f_0</editable>',
    '                content_e_1',
    '            </noteditable>',
    '            content_c_4',
    '        </editable>',
    '        <noteditable id="g">content_g_0</noteditable>',
    '        <editable id="h">',
    '            content_h_0',
    '            <noteditable id="i">content_i_0</noteditable>',
    '            content_h_2',
    '        </editable>',
    '        <editable id="j">',
    '            content_j_0',
    '            <editable id="k">content_k_0</editable>',
    '            <editable id="l">content_l_0</editable>',
    '            content_j_4',
    '        </editable>',
    '    </noteditable>',
    '    <editable id="m">content_m_0</editable>',
    '    <editable id="n">content_n_0</editable>',
    ''
].join('\n');
var UnbreakableTests = [{
        name: "nothing to do",
        content: unbreakableTestDom,
        steps: [{
            start: "#c:contents()[0]->13",
            end: "#c:contents()[0]->15",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->13",
            end: "#c:contents()[0]->15",
        },
    },
    {
        name: "nothing to do 2",
        content: unbreakableTestDom,
        steps: [{
            start: "#j:contents()[0]->13",
            end: "#l:contents()[0]->5",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#j:contents()[0]->13",
            end: "#l:contents()[0]->5",
        },
    },
    {
        name: "nothing to do 3",
        content: unbreakableTestDom,
        steps: [{
            start: "#k:contents()[0]->3",
            end: "#l:contents()[0]->5",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#k:contents()[0]->3",
            end: "#l:contents()[0]->5",
        },
    },
    {
        name: "find the first allowed node",
        content: unbreakableTestDom,
        steps: [{
            start: "#a:contents()[0]->13",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->0",
            end: "#c:contents()[0]->0",
        },
    },
    {
        name: "find the first allowed node and collapse the selection",
        content: unbreakableTestDom,
        steps: [{
            start: "#a:contents()[0]->10",
            end: "#b:contents()[0]->3",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->0",
            end: "#c:contents()[0]->0",
        },
    },
    {
        name: "resize the range to the allowed end",
        content: unbreakableTestDom,
        steps: [{
            start: "#a:contents()[0]->10",
            end: "#c:contents()[0]->14",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->0",
            end: "#c:contents()[0]->14",
        },
    },
    {
        name: "resize the range to the allowed start",
        content: unbreakableTestDom,
        steps: [{
            start: "#c:contents()[0]->15",
            end: "#d:contents()[0]->4",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->15",
            end: "#c:contents()[0]->37",
        },
    },
    {
        name: "resize the range to the allowed node that contains unbreakable node",
        content: unbreakableTestDom,
        steps: [{
            start: "#g:contents()[0]->5",
            end: "#h:contents()[2]->15",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#h:contents()[0]->0",
            end: "#h:contents()[2]->15",
        },
    },
    {
        name: "resize the range to the allowed node between the start and the end",
        content: unbreakableTestDom,
        steps: [{
            start: "#e:contents()[0]->15",
            end: "#c:contents()[4]->15",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#f:contents()[0]->0",
            end: "#f:contents()[0]->11",
        },
    },
    {
        name: "resize the range to the allowed start with the entirety of the unbreakable node",
        content: unbreakableTestDom,
        steps: [{
            start: "#c:contents()[0]->15",
            end: "#e:contents()[0]->15",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#c:contents()[0]->15",
            end: "#d->1",
        },
    },
    {
        name: "resize the range to the allowed start and delete content",
        content: unbreakableTestDom,
        steps: [{
            start: "#c:contents()[0]->15",
            end: "#e:contents()[0]->15",
            key: "DELETE",
        }],
        test: {
            content: unbreakableTestDom
                // when we remove, we clean the invisible space before and after the deleted area
                .replace(/>[\s]+content_c_0[\s\S]+content_d_0<\/noteditable>\s+/, '>co')
                .replace(/^\s+/, ''), // corner effect of the clean and normalize
            start: "#c:contents()[0]->2",
            end: "#c:contents()[0]->2",
        },
    },
    {
        name: "delete unbreakable nodes in a breakable",
        content: unbreakableTestDom,
        steps: [{
            start: "#c:contents()[0]->15",
            end: "#c:contents()[4]->19",
            key: "DELETE",
        }],
        test: {
            content: unbreakableTestDom
                // when we remove, we clean the invisible space before and after the deleted area
                .replace(/>[\s]+content_c_0[\s\S]*content_c_4\s*/, '>cot_c_4')
                .replace(/^\s+/, ''), // corner effect of the clean and normalize
            start: "#c:contents()[0]->2",
            end: "#c:contents()[0]->2",
        },
    },
    {
        name: "select range with 2 nodes on the root",
        content: unbreakableTestDom,
        steps: [{
            start: "#m:contents()[0]->5",
            end: "#n:contents()[0]->5",
        }],
        test: {
            content: unbreakableTestDom,
            start: "#m:contents()[0]->5",
            end: "#n:contents()[0]->5",
        },
    },
    {
        name: "ENTER in an unbreakable p",
        content: "<p class='unbreakable'>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:contents()[0]->1",
            key: 'ENTER',
        }],
        test: {
            content: '<p class="unbreakable">d<br>om to edit</p>',
            start: "p:contents()[2]->0",
        },
    },
];

QUnit.test('Unbreakable selection and edition', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
        useOnlyTestUnbreakable: true,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, UnbreakableTests).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

//--------------------------------------------------------------------------
// Keyboard integration
//--------------------------------------------------------------------------

QUnit.module('Keyboard');

var keyboardTestsChar = [{
        name: "visible char in a p tag",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->3",
            keyCode: 66,
        }],
        test: {
            content: "<p>domB to edit</p>",
            start: "p:contents()[0]->4",
            end: null,
            check: function ($editable, assert) {
                assert.ok(true);
            },
        },
    },
    {
        name: "visible char in a link tag entirely selected",
        content: '<div><a href="#">dom to edit</a></div>',
        steps: [{
            start: "a:contents()[0]->0",
            end: "a:contents()[0]->11",
            key: 'a',
        }],
        test: {
            content: '<div><a href="#">&#8203;a&#8203;</a></div>',
            start: "a:contents()[0]->2",
        },
    },
    {
        name: "'a' on a selection of all the contents of a complex dom",
        content: "<p><b>dom</b></p><p><b>to<br>completely</b>remov<i>e</i></p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "i:contents()[0]->1",
            key: 'a',
        }],
        test: {
            content: "<p><b>a</b></p>",
            start: "b:contents()[0]->1",
        },
    },
    {
        name: "'a' on a selection of all the contents of a complex dom (2)",
        content: "<h1 class=\"a\"><font style=\"font-size: 62px;\"><b>dom to</b>edit</font></h1>",
        steps: [{
            start: "font:contents()[0]->0",
            end: "font:contents()[1]->4",
            key: 'a',
        }],
        test: {
            content: "<h1 class=\"a\"><font style=\"font-size: 62px;\"><b>a</b></font></h1>",
            start: "b:contents()[0]->1",
        },
    },
    {
        name: "'a' before an image",
        content: '<p>xxx <img src="/web_editor/static/src/img/transparent.png"> yyy</p>',
        steps: [{
            start: "p:contents()[0]->4",
            key: 'a',
        }],
        test: {
            content: '<p>xxx a<img data-src="/web_editor/static/src/img/transparent.png"> yyy</p>',
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "'a' before an image (2)",
        content: '<p>xxx <img src="/web_editor/static/src/img/transparent.png"> yyy</p>',
        steps: [{
            start: "img->0",
            key: 'a',
        }],
        test: {
            content: '<p>xxx a<img data-src="/web_editor/static/src/img/transparent.png"> yyy</p>',
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "'a' before an image in table",
        content: '<table><tbody><tr><td><p>xxx</p></td><td><p><img src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
        steps: [{
            start: "img->0",
            key: 'a',
        }],
        test: {
            content: '<table><tbody><tr><td><p>xxx</p></td><td><p>a<img data-src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' on invisible text before an image in table",
        content: '<table><tbody><tr><td><p>xxx</p></td><td><p><img src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
        steps: [{
            start: "p:eq(1)->0",
            key: 'a',
        }],
        test: {
            content: '<table><tbody><tr><td><p>xxx</p></td><td><p>a<img data-src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' before an image in table without spaces",
        content: '<table><tbody><tr><td><p>xxx</p></td><td><p><img src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
        steps: [{
            start: "img->0",
            key: 'a',
        }],
        test: {
            content: '<table><tbody><tr><td><p>xxx</p></td><td><p>a<img data-src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' before an image in table without spaces (2)",
        content: '<table><tbody><tr><td><p>xxx</p></td><td><p><img src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
        steps: [{
            start: "td:eq(1)->0",
            key: 'a',
        }],
        test: {
            content: '<table><tbody><tr><td><p>xxx</p></td><td><p>a<img data-src="/web_editor/static/src/img/transparent.png"></p></td><td><p>yyy</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' before an image in table with spaces",
        content:
            '<table><tbody>\n' +
            '   <tr>\n' +
            '       <td>\n' +
            '           <p>xxx</p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p><img src="/web_editor/static/src/img/transparent.png"></p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p>yyy</p>\n' +
            '       </td>\n' +
            '   </tr>\n' +
            '</tbody></table>',
        steps: [{
            start: "img->0",
            key: 'a',
        }],
        test: {
            content:
                '<table><tbody>\n' +
                '   <tr>\n' +
                '       <td>\n' +
                '           <p>xxx</p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>a<img data-src="/web_editor/static/src/img/transparent.png"></p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>yyy</p>\n' +
                '       </td>\n' +
                '   </tr>\n' +
                '</tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' before an image in table with spaces (2)",
        content:
            '<table><tbody>\n' +
            '   <tr>\n' +
            '       <td>\n' +
            '           <p>xxx</p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p><img src="/web_editor/static/src/img/transparent.png"></p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p>yyy</p>\n' +
            '       </td>\n' +
            '   </tr>\n' +
            '</tbody></table>',
        steps: [{
            start: "td:eq(1)->1",
            key: 'a',
        }],
        test: {
            content:
                '<table><tbody>\n' +
                '   <tr>\n' +
                '       <td>\n' +
                '           <p>xxx</p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>a<img data-src="/web_editor/static/src/img/transparent.png"></p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>yyy</p>\n' +
                '       </td>\n' +
                '   </tr>\n' +
                '</tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' before an image in table with spaces (3)",
        content:
            '<table><tbody>\n' +
            '   <tr>\n' +
            '       <td>\n' +
            '           <p>xxx</p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p><img src="/web_editor/static/src/img/transparent.png"></p>\n' +
            '       </td>\n' +
            '       <td>\n' +
            '           <p>yyy</p>\n' +
            '       </td>\n' +
            '   </tr>\n' +
            '</tbody></table>',
        steps: [{
            start: "td:eq(1):contents()[0]->12",
            key: 'a',
        }],
        test: {
            content:
                '<table><tbody>\n' +
                '   <tr>\n' +
                '       <td>\n' +
                '           <p>xxx</p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>a<img data-src="/web_editor/static/src/img/transparent.png"></p>\n' +
                '       </td>\n' +
                '       <td>\n' +
                '           <p>yyy</p>\n' +
                '       </td>\n' +
                '   </tr>\n' +
                '</tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "'a' on begin of a span with fake_editable",
        content:
            '<div class="o_fake_not_editable" contentEditable="false">\n' +
            '   <div>\n' +
            '     <label>\n' +
            '       <input type="checkbox"/>\n' +
            '       <span class="o_fake_editable" contentEditable="true">\n' +
            '         dom to edit\n' +
            '       </span>\n' +
            '     </label>\n' +
            '   </div>\n' +
            '</div>',
        steps: [{
            start: "span:contents(0)->10",
            key: 'a',
        }],
        test: {
            content:
                '<div>\n' +
                '   <div>\n' +
                '     <label>\n' +
                '       <input type="checkbox">\n' +
                '       <span>\n' +
                '         adom to edit\n' +
                '       </span>\n' +
                '     </label>\n' +
                '   </div>\n' +
                '</div>',
            start: "span:contents(0)->11",
        },
    },
    {
        name: "'a' on all contents of p starting with an icon",
        content: '<p><span class="fa fa-star"></span>bbb</p>',
        steps: [{
            start: "span->0",
            end: 'p:contents(1)->3',
            key: 'a',
        }],
        test: {
            content: '<p>a</p>',
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "' ' at start of p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->0",
            key: ' ',
        }],
        test: {
            content: '<p>&nbsp;dom to edit</p>',
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "' ' at end of p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->11",
            key: ' ',
        }],
        test: {
            content: '<p>dom to edit&nbsp;</p>',
            start: "p:contents()[0]->12",
        },
    },
    {
        name: "' ' within p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->2",
            key: ' ',
        }],
        test: {
            content: '<p>do m to edit</p>',
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "' ' before space within p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->3",
            key: ' ',
        }],
        test: {
            content: '<p>dom&nbsp;&nbsp;to edit</p>',
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "' ' after space within p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->4",
            key: ' ',
        }],
        test: {
            content: '<p>dom&nbsp;&nbsp;to edit</p>',
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "3x ' ' at start of p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->0",
            key: ' ',
        }, {
            key: ' ',
        }, {
            key: ' ',
        }],
        test: {
            content: '<p>&nbsp;&nbsp;&nbsp;dom to edit</p>',
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "3x ' ' at end of p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->11",
            key: ' ',
        }, {
            key: ' ',
        }, {
            key: ' ',
        }],
        test: {
            content: '<p>dom to edit&nbsp;&nbsp;&nbsp;</p>',
            start: "p:contents()[0]->14",
        },
    },
    {
        name: "3x ' ' within p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->2",
            key: ' ',
        }, {
            key: ' ',
        }, {
            key: ' ',
        }],
        test: {
            content: '<p>do&nbsp;&nbsp;&nbsp;m to edit</p>',
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "3x ' ' before space in p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->3",
            key: ' ',
        }, {
            key: ' ',
        }, {
            key: ' ',
        }],
        test: {
            content: '<p>dom&nbsp;&nbsp;&nbsp;&nbsp;to edit</p>',
            start: "p:contents()[0]->6",
        },
    },
    {
        name: "3x ' ' after space in p",
        content: '<p>dom to edit</p>',
        steps: [{
            start: "p:contents()[0]->4",
            key: ' ',
        }, {
            key: ' ',
        }, {
            key: ' ',
        }],
        test: {
            content: '<p>dom&nbsp;&nbsp;&nbsp;&nbsp;to edit</p>',
            start: "p:contents()[0]->7",
        },
    },
    {
        name: "'a' in unbreakable with font",
        content: '<div class="unbreakable">dom <span class="fa fa-heart"></span>to edit</div>',
        steps: [{
            start: "div:contents(2)->2",
            key: 'a',
        }],
        test: {
            content: '<div class="unbreakable">dom <span class="fa fa-heart"></span>toa edit</div>',
            start: "div:contents(2)->3",
        },
    },
    {
        name: "'a' on begin of unbreakable inline node",
        content: 'dom <strong class="unbreakable">to</strong> edit',
        steps: [{
            start: "strong:contents(0)->0",
            key: 'a',
        }],
        test: {
            content: 'dom <strong class="unbreakable">ato</strong> edit',
            start: "strong:contents(0)->1",
        },
    },
    {
        name: "'a' on end of unbreakable inline node",
        content: '<div>dom <strong class="unbreakable">to</strong> edit</div>',
        steps: [{
            start: "strong:contents(0)->2",
            key: 'a',
        }],
        test: {
            content: '<div>dom <strong class="unbreakable">toa</strong> edit</div>',
            start: "strong:contents(0)->3",
        },
    },
    {
        name: "'1' on begin of value of a field currency",
        content:
            '<noteditable>\n' +
                  '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">750.00</span></b>\n' +
            '</noteditable>',
        steps: [{
            start: "span:contents(0)->0",
            key: '1',
        }],
        test: {
            content:
                '<noteditable>\n' +
                      '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">1750.00</span></b>\n' +
                '</noteditable>',
            start: "span:contents(0)->1",
        },
    },
    {
        name: "'1' on end of value of a field currency",
        content:
            '<noteditable>\n' +
                  '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">750.00</span></b>\n' +
            '</noteditable>',
        steps: [{
            start: "span:contents(0)->6",
            key: '1',
        }],
        test: {
            content:
                '<noteditable>\n' +
                      '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">750.001</span></b>\n' +
                '</noteditable>',
            start: "span:contents(0)->7",
        },
    },
    {
        name: "'1' on begin of editable in noteditable",
        content:
            '<noteditable contenteditable="false">\n' +
                  '<b data-oe-type="monetary" class="oe_price editable" contenteditable="true">$&nbsp;<span class="oe_currency_value">750.00</span></b>\n' +
            '</noteditable>',
        steps: [{
            start: "span:contents(0)->0",
            key: '1',
        }],
        test: {
            content:
                '<noteditable>\n' +
                      '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">1750.00</span></b>\n' +
                '</noteditable>',
            start: "span:contents(0)->1",
        },
    },
    {
        name: "'1' on end of editable in noteditable",
        content:
            '<noteditable contenteditable="false">\n' +
                  '<b data-oe-type="monetary" class="oe_price editable" contenteditable="true">$&nbsp;<span class="oe_currency_value">750.00</span></b>\n' +
            '</noteditable>',
        steps: [{
            start: "span:contents(0)->6",
            key: '1',
        }],
        test: {
            content:
                '<noteditable>\n' +
                      '<b data-oe-type="monetary" class="oe_price editable">$&nbsp;<span class="oe_currency_value">750.001</span></b>\n' +
                '</noteditable>',
            start: "span:contents(0)->7",
        },
    },
    {
        name: "'a' on editable with before&after in noteditable",
        content:
            '<style>#test-before-after:before { content: "placeholder";} #test-before-after:after { content: "\\00a0";}</style>\n' +
            '<noteditable contenteditable="false">\n' +
                  '<b id="test-before-after" class="editable" contenteditable="true"></b>\n' +
            '</noteditable>',
        steps: [{
            start: "b->0",
            key: 'a',
        }],
        test: {
            content:
                '<style>#test-before-after:before { content: "placeholder";} #test-before-after:after { content: "\\00a0";}</style>\n' +
                '<noteditable>\n' +
                      '<b id="test-before-after" class="editable">a</b>\n' +
                '</noteditable>',
            start: "b:contents(0)->1",
        },
    },
];

QUnit.test('Char', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsChar).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

var keyboardTestsEnter = [{
        name: "in p: ENTER",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'ENTER',
        }],
        test: {
            content: "<p>d</p><p>om to edit</p>",
            start: "p:contents()[1]->0",
        },
    },
    {
        name: "in p: 2x ENTER",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<p>d</p><p><br></p><p>om to edit</p>",
            start: "p:contents()[2]->0",
        },
    },
    {
        name: "in p: SHIFT+ENTER",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p>d<br>om to edit</p>",
            start: "p:contents()[2]->0",
        },
    },
    {
        name: "in empty-p: SHIFT+ENTER",
        content: "<p><br></p>",
        steps: [{
            start: "p->1",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><br><br></p>",
            start: "br:eq(1)->0",
        },
    },
    {
        name: "in p: 2x SHIFT+ENTER",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p>d<br><br>om to edit</p>",
            start: "p:contents()[3]->0",
        },
    },
    {
        name: "in empty-p: 2x SHIFT+ENTER",
        content: "<p><br></p>",
        steps: [{
            start: "p->1",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><br><br><br></p>",
            start: "br:eq(2)->0",
        },
    },
    {
        name: "in p: ENTER -> SHIFT+ENTER",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'ENTER',
        }, {
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p>d</p><p><br>om to edit</p>",
            start: "p:eq(1):contents()[1]->0",
        },
    },
    {
        name: "in p: ENTER on selection",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:contents()[0]->7",
            key: 'ENTER',
        }],
        test: {
            content: "<p>d</p><p>edit</p>",
            start: "p:contents()[1]->0",
            end: "p:contents()[1]->0",
        },
    },
    {
        name: "in p: SHIFT+ENTER on selection",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:contents()[0]->7",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p>d<br>edit</p>",
            start: "p:contents()[2]->0",
        },
    },

    // list UL / OL

    {
        name: "in li: SHIFT+ENTER at start",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li><br>dom to edit</li></ul>",
            start: "li:contents()[1]->0",
        },
    },
    {
        name: "in li: SHIFT+ENTER within contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->5",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li>dom t<br>o edit</li></ul>",
            start: "li:contents()[2]->0",
        },
    },
    {
        name: "in empty-li: SHIFT+ENTER",
        content: "<ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li><br><br></li></ul>",
            start: "br:eq(1)->0",
        },
    },
    {
        name: "in li: SHIFT+ENTER on selection",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:contents()[0]->7",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li>d<br>edit</li></ul>",
            start: "li:contents()[2]->0",
        },
    },
    {
        name: "in li: ENTER at start",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li><br></li><li>dom to edit</li></ul>",
            start: "li:contents()[1]->0",
        },
    },
    {
        name: "in li: ENTER within contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->5",
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li>dom t</li><li>o edit</li></ul>",
            start: "li:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in li: ENTER on selection",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:contents()[0]->7",
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li>d</li><li>edit</li></ul>",
            start: "li:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in li: ENTER on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'ENTER',
        }],
        test: {
            content: "<p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in li: ENTER -> 'a' on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>a</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "across 2 li: ENTER on partial selection",
        content: "<ul><li>dom to edit</li><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:eq(1):contents()[0]->4",
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li>d</li><li>to edit</li></ul>",
            start: "li:eq(1):contents()[0]->0", // we are after the <br>, the carret is on the li with an offset equal to the node length
        },
    },
    {
        name: "in li: ENTER at end",
        content: "<ul><li><p>dom to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->11",
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li><p>dom to edit</p></li><li><p><br></p></li></ul>",
            start: "br->0",
        },
    },
    {
        name: "in li: 2x ENTER at end",
        content: "<ul><li><p>dom to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li><p>dom to edit</p></li></ul><p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in ul.list-group > li: ENTER at end",
        content: '<ul class="list-group"><li><p>dom to edit</p></li></ul>',
        steps: [{
            start: "p:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }],
        test: {
            content: '<ul class="list-group"><li><p>dom to edit</p></li><li><p><br></p></li><li><p><br></p></li></ul>',
            start: "p:eq(2) br->0",
        },
    },
    {
        name: "in indented-li: 2x ENTER at end",
        content: "<ul><li><p>aaa</p></li><ul><li><p>dom to edit</p></li></ul><li><p>bbb</p></li></ul>",
        steps: [{
            start: "ul ul p:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li><p>aaa</p></li><ul><li><p>dom to edit</p></li></ul><li><p><br></p></li><li><p>bbb</p></li></ul>",
            start: "p:eq(2) br->0",
        },
    },
    {
        name: "in indented-li with font: 2x ENTER at end",
        content: "<ul><li><p>aaa</p></li><ul><li><p><font style=\"color\">dom to edit</font></p></li></ul><li><p>bbb</p></li></ul>",
        steps: [{
            start: "font:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<ul><li><p>aaa</p></li><ul><li><p><font style=\"color\">dom to edit</font></p></li></ul><li><p><font style=\"color\"><br></font></p></li><li><p>bbb</p></li></ul>",
            start: "p:eq(2) br->0",
        },
    },
    {
        name: "in li > empty-p: ENTER",
        content: "<ul><li><p><br></p></li></ul>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'ENTER',
        }],
        test: {
            content: "<p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in li > p > empty-b: ENTER",
        content: "<ul><li><p><b><br></b></p></li></ul>",
        steps: [{
            start: "b:contents()[0]->0",
            key: 'ENTER',
        }],
        test: {
            content: "<p><b><br></b></p>",
            start: "br->0",
        },
    },

    // end list UL / OL

    {
        name: "after p > b: SHIFT+ENTER",
        content: "<p><b>dom</b> to edit</p>",
        steps: [{
            start: "p:contents()[1]->0",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><b>dom</b><br>&nbsp;to edit</p>",
            start: "p:contents()[2]->0",
        },
    },
    {
        name: "in p > b: ENTER -> 'a'",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->2",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>do</b></p><p><b>am to edit</b></p>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "after p > b: ENTER -> 'a'",
        content: "<p><b>dom</b> to edit</p>",
        steps: [{
            start: "p:contents()[1]->0",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom</b></p><p>a to edit</p>",
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "after p > b: SHIFT+ENTER -> 'a'",
        content: "<p><b>dom</b>&nbsp;to edit</p>",
        steps: [{
            start: "p:contents()[1]->0",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom</b><br>a to edit</p>",
            start: "p:contents()[2]->1",
        },
    },
    {
        name: "in p (other-p > span.a before - p > span.b after): ENTER at beginning",
        content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'ENTER',
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\"><br></span></p><p><span class=\"b\">edit</span></p>",
            start: "span:eq(2):contents()[0]->0",
        },
    },
    {
        name: "in p (other-p > span.a before - p > span.b after): ENTER -> 'a' at beginning",
        content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\"><br></span></p><p><span class=\"b\">aedit</span></p>",
            start: "span:eq(2):contents()[0]->1",
        },
    },
    {
        name: "in p (other-p > span.a before - p > span.b after): SHIFT+ENTER at beginning",
        content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\"><br>edit</span></p>",
            start: "span:eq(1):contents()[1]->0",
        },
    },
    {
        name: "in p (other-p > span.a before - p > span.b after): SHIFT+ENTER -> 'a' at beginning",
        content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\"><br>aedit</span></p>",
            start: "span:eq(1):contents()[1]->1",
        },
    },
    {
        name: "in p: ENTER on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'ENTER',
        }],
        test: {
            content: "<p><br></p><p><br></p>",
            start: "p:eq(1) br->0",
        },
    },
    {
        name: "in p: ENTER -> 'a' on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><br></p><p>a</p>",
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in p: SHIFT+ENTER on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><br><br></p>",
            start: "br:eq(1)->0",
        },
    },
    {
        name: "in p: SHIFT+ENTER -> 'a' on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><br>a</p>",
            start: "p:contents()[1]->1",
        },
    },
    {
        name: "in p: 2x ENTER -> 'a' on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->3",
            key: 'ENTER',
        }, {
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom</p><p><br></p><p>a to edit</p>",
            start: "p:eq(2):contents()[0]->1",
        },
    },
    {
        name: "in p > b: ENTER at start",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->0",
            key: 'ENTER',
        }],
        test: {
            content: "<p><b><br></b></p><p><b>dom to edit</b></p>",
            start: "b:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in p > b: ENTER",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
        }],
        test: {
            content: "<p><b>dom</b></p><p><b>&nbsp;to edit</b></p>",
            start: "b:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in p > b: SHIFT+ENTER -> ENTER",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<p><b>dom<br>&#8203;</b></p><p><b>&nbsp;to edit</b></p>",
            start: "b:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in p > b: ENTER -> a'",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom</b></p><p><b>a to edit</b></p>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in p > b: SHIFT+ENTER",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p><b>dom<br>&nbsp;to edit</b></p>",
            start: "b:contents()[2]->0",
        },
    },
    {
        name: "in p > b: SHIFT+ENTER -> 'a'",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom<br>a to edit</b></p>",
            start: "b:contents()[2]->1",
        },
    },
    {
        name: "in p > b: SHIFT+ENTER -> ENTER -> 'a'",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom<br>&#8203;</b></p><p><b>a to edit</b></p>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in span > b: ENTER",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
        }],
        test: {
            content: "<span><b>dom</b></span><br><span><b>&#8203;&nbsp;to edit</b></span>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER -> ENTER",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }],
        test: {
            content: "<span><b>dom<br></b></span><br><span><b>&#8203;&nbsp;to edit</b></span>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in span > b: ENTER -> a'",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<span><b>dom</b></span><br><span><b>a to edit</b></span>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<span><b>dom<br>&nbsp;to edit</b></span>",
            start: "b:contents()[2]->0",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER -> 'a'",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<span><b>dom<br>a to edit</b></span>",
            start: "b:contents()[2]->1",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER -> ENTER -> 'a'",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<span><b>dom<br></b></span><br><span><b>a to edit</b></span>",
            start: "b:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in p: 2x SHIFT+ENTER -> 'a'",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom<br><br>a to edit</p>",
            start: "p:contents()[3]->1",
        },
    },
    {
        name: "in p: ENTER -> SHIFT+ENTER -> 'a'",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->3",
            key: 'ENTER',
        }, {
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom</p><p><br>a to edit</p>",
            start: "p:eq(1):contents()[1]->1",
        },
    },
    {
        name: "in empty-p (p before and after): ENTER -> 'a'",
        content: "<p>dom </p><p><br></p><p>to edit</p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom </p><p><br></p><p>a</p><p>to edit</p>",
            start: "p:eq(2):contents()[0]->1",
        },
    },
    {
        name: "in p: SHIFT+ENTER at end",
        content: "<p>dom </p><p>to edit</p>",
        steps: [{
            start: "p:first:contents()[0]->4",
            key: 'ENTER',
            shiftKey: true,
        }],
        test: {
            content: "<p>dom <br>&#8203;</p><p>to edit</p>",
            start: "p:first:contents()[2]->0",
        },
    },
    {
        name: "in p: SHIFT+ENTER at end -> '寺'",
        content: "<p>dom </p><p>to edit</p>",
        steps: [{
            start: "p:first:contents()[0]->4",
            key: 'ENTER',
            shiftKey: true,
        }, {
            keyCode: 23546, /*temple in chinese*/
        }],
        test: {
            content: "<p>dom <br>寺</p><p>to edit</p>",
            start: "p:first:contents()[2]->1",
        },
    },
    {
        name: "in empty-p (div > a after): 3x SHIFT+ENTER -> 'a'",
        content: "<p><br></p><div><a href='#'>dom to edit</a></div>",
        steps: [{
                start: "p->1",
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'a',
            }
        ],
        test: {
            content: "<p><br><br><br>a</p><div><a href=\"#\">dom to edit</a></div>",
            start: "p:contents()[3]->1",
        },
    },

    // Buttons

    {
        name: "in div > a.btn: ENTER -> 'a' at start (before invisible space)",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->0",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">Label</a><a class=\"btn\" href=\"#\">&#8203;adom to edit&#8203;</a></div>",
            // split button has no text so the placeholder text is selected then replaced by 'a'
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' at start (after invisible space)",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->1",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">Label</a><a class=\"btn\" href=\"#\">&#8203;adom to edit&#8203;</a></div>",
            // split button has no text so the placeholder text is selected then replaced by 'a'
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' within contents",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->6",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom t</a><a class=\"btn\" href=\"#\">&#8203;ao edit&#8203;</a></div>",
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' at end (before invisible space)",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->12",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom to edit</a><a class=\"btn\" href=\"#\">&#8203;a&#8203;</a></div>",
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' at end (after invisible space)",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->13",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom to edit</a><a class=\"btn\" href=\"#\">&#8203;a&#8203;</a></div>",
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > button.btn: ENTER -> 'a' at end (after invisible space)",
        content: "<div class=\"unbreakable\"><button class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</button></div>",
        steps: [{
            start: "button:contents()[0]->13",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><button class=\"btn\" href=\"#\">dom to edit</button><button class=\"btn\" href=\"#\">&#8203;a&#8203;</button></div>",
            start: "button:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' on partial selection",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">&#8203;dom to edit&#8203;</a></div>",
        steps: [{
            start: "a:contents()[0]->4",
            end: "a:contents()[0]->8",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom</a><a class=\"btn\" href=\"#\">&#8203;aedit&#8203;</a></div>",
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "in div > a.btn: ENTER -> 'a' on selection of all visible text",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom to edit</a></div>",
        steps: [{
            start: "a:contents()[0]->0",
            end: "a:contents()[0]->11",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">Label</a><a class=\"btn\" href=\"#\">&#8203;a&#8203;</a></div>",
            // Removing all text in a link replaces that text with "Label"
            start: "a:eq(1):contents()[0]->2",
        },
    },
    {
        name: "across 2 a.btn: ENTER on selection across two a.btn",
        content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">dom not to edit</a><a class=\"btn\" href=\"#\">other dom not to edit</a></div>",
        steps: [{
            start: "a:contents()[0]->0",
            end: "a:eq(1):contents()[0]->11",
            key: 'ENTER',
        }],
        test: {
            content: "<div class=\"unbreakable\"><a class=\"btn\" href=\"#\">Label</a><a class=\"btn\" href=\"#\">&#8203;ot to edit&#8203;</a></div>",
            start: "a:eq(1):contents()[0]->1",
        },
    },
];

QUnit.test('Enter', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsEnter).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

var keyboardTestsComplex = [{
        name: "in span > b: SHIFT+ENTER -> BACKSPACE -> 'a'",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<span><b>doma to edit</b></span>",
            start: "b:contents()[0]->4",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER -> ENTER -> BACKSPACE",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<span><b>dom<br>&nbsp;to edit</b></span>",
            start: "b:contents(2)->0",
        },
    },
    {
        name: "in span > b: SHIFT+ENTER -> ENTER -> BACKSPACE -> 'a'",
        content: "<span><b>dom to edit</b></span>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<span><b>dom<br>a to edit</b></span>",
            start: "b:contents()[2]->1",
        },
    },
    {
        name: "in p > b: 2x SHIFT+ENTER -> BACKSPACE",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><b>dom<br>&nbsp;to edit</b></p>",
            start: "b:contents()[2]->0",
        },
    },
    {
        name: "in p > b: 2x ENTER -> 2x BACKSPACE",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: false
        }, {
            key: 'ENTER',
            shiftKey: false
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><b>dom&nbsp;to edit</b></p>",
            start: "b:contents()[0]->3",
        },
    },
    {
        name: "in empty-p: 2x ENTER -> 2x BACKSPACE",
        content: "<p><br></p>",
        steps: [{
            start: "p->1",
            key: 'ENTER',
            shiftKey: false
        }, {
            key: 'ENTER',
            shiftKey: false
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in empty-p (p before): ENTER -> 2x BACKSPACE",
        content: "<p>dom not to edit</p><p><br></p>",
        steps: [{
            start: "p:eq(1)->1",
            key: 'ENTER',
            shiftKey: false
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom not to edit</p>",
            start: "p:first:contents()[0]->15",
        },
    },
    {
        name: "in p > b: 2x SHIFT+ENTER -> BACKSPACE -> 'a'",
        content: "<p><b>dom to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'ENTER',
            shiftKey: true,
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><b>dom<br>a to edit</b></p>",
            start: "b:contents()[2]->1",
        },
    },
    {
        name: "in li -> ENTER before br -> 'a'",
        content: "<ul><li><p>dom<br/>&nbsp;to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->3",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>dom</p></li><li><p>a<br>&nbsp;to edit</p></li></ul>",
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in li -> ENTER after br -> 'a'",
        content: "<ul><li><p>dom<br/>&nbsp;to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[2]->0",
            key: 'ENTER',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>dom<br>&#8203;</p></li><li><p>a to edit</p></li></ul>",
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "within p (p before and after): 3x SHIFT+ENTER -> 3x BACKSPACE",
        content: "<p>dom not to edit</p><p>dom to edit</p><p>dom not to edit</p>",
        steps: [{
                start: "p:eq(1):contents()[0]->5",
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'ENTER',
                shiftKey: true,
            },
            {
                key: 'BACKSPACE',
            },
            {
                key: 'BACKSPACE',
            },
            {
                key: 'BACKSPACE',
            }
        ],
        test: {
            content: "<p>dom not to edit</p><p>dom to edit</p><p>dom not to edit</p>",
            start: "p:eq(1):contents()[0]->5",
        },
    },
    {
        name: "in h1.a > font: 'a' on selection of all contents",
        content: "<h1 class=\"a\"><font style=\"font-size: 62px;\">dom to edit</font></h1>",
        steps: [{
            start: "h1->0",
            end: "h1->1",
            key: 'a',
        }],
        test: {
            content: "<h1 class=\"a\"><font style=\"font-size: 62px;\">a</font></h1>",
            start: "font:contents()[0]->1",
        },
    },
    {
        name: "in complex-dom: BACKSPACE on partial selection (requires merging non-similar blocks)",
        content: "<p class=\"a\">pif</p><p><span><b>paf</b></span></p><ul><li><p>p<i>ouf</i></p></li></ul>",
        steps: [{
            start: 'p:contents()[0]->2',
            end: 'i:contents()[0]->2',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p class=\"a\">pi<i>f</i></p>',
            start: "p:contents()[0]->2",
        },
    },
    {
        name: "in complex-dom: DELETE on partial selection (requires merging non-similar blocks)",
        content: "<p class=\"a\">pif</p><p><span><b>paf</b></span></p><ul><li><p>p<i>ouf</i></p></li></ul>",
        steps: [{
            start: 'p:contents()[0]->2',
            end: 'i:contents()[0]->2',
            key: 'DELETE',
        }],
        test: {
            content: '<p class=\"a\">pi<i>f</i></p>',
            start: "p:contents()[0]->2",
        },
    },

    // paragraph outdent

    {
        name: "in p (h1 before): TAB -> BACKSPACE at start (must indent then outdent)",
        content: "<h1>dom not to edit</h1><p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'TAB',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<h1>dom not to edit</h1><p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p (h1 before): TAB -> 2x BACKSPACE at start (must indent then outdent, then merge blocks)",
        content: "<h1>dom not to edit</h1><p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'TAB',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<h1>dom not to editdom to edit</h1>",
            start: "h1:contents()[0]->15",
        },
    },
];

QUnit.test('Complex', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsComplex).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

var keyboardTestsTab = [{
        name: "in li: TAB at start",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'TAB',
        }],
        test: {
            content: "<ul><li class=\"o_indent\"><ul><li>dom to edit</li></ul></li></ul>",
            start: "ul ul li:contents()[0]->0",
        },
    },
    {
        name: "in indented-li: SHIFT+TAB at start",
        content: "<ul><ul><li>dom to edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'TAB',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li>dom to edit</li></ul>",
            start: "li:contents()[0]->0",
        },
    },
    {
        name: "in li: TAB within contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->5",
            key: 'TAB',
        }],
        test: {
            content: "<ul><li>dom t&nbsp;&nbsp;&nbsp;&nbsp;o edit</li></ul>",
            start: "li:contents()[0]->9",
        },
    },
    {
        name: "in li: SHIFT+TAB within contents (should do nothing)",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->5",
            key: 'TAB',
            shiftKey: true,
        }],
        test: {
            content: "<ul><li>dom to edit</li></ul>",
            start: "li:contents()[0]->5",
        },
    },
    {
        name: "in td > p: TAB within contents",
        content: "<table><tbody><tr><td><p>dom to edit</p></td><td><p>node</p></td></tr></tbody></table>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'TAB',
        }],
        test: {
            content: "<table><tbody><tr><td><p>dom to edit</p></td><td><p>node</p></td></tr></tbody></table>",
            start: "td:eq(1) p:contents(0)->0",
        },
    },
    {
        name: "in p: TAB at start",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'TAB',
        }],
        test: {
            content: "<p style=\"margin-left: 1.5em;\">dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in indented-p: SHIFT+TAB at start",
        content: "<p style=\"margin-left: 1.5em;\">dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'TAB',
            shiftKey: true,
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p: TAB -> BACKSPACE at start",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'TAB',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p > b: TAB at start",
        content: "<p>dom <b>to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->0",
            key: 'TAB',
        }],
        test: {
            content: "<p>dom <b>&nbsp;&nbsp;&nbsp;&nbsp;to edit</b></p>",
            start: "b:contents()[0]->4",
        },
    },
    {
        name: "in p > b: TAB -> BACKSPACE at start",
        content: "<p>dom <b>to edit</b></p>",
        steps: [{
            start: "b:contents()[0]->0",
            key: 'TAB',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom <b>&nbsp;&nbsp;&nbsp;to edit</b></p>",
            start: "b:contents()[0]->3",
        },
    },
];

QUnit.test('Tab', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsTab).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

var keyboardTestsBackspace = [{
        name: "in p: BACKSPACE after span.fa",
        content: '<p>aaa<span class="fa fa-star"></span>bbb</p>',
        steps: [{
            start: "p:contents()[2]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>aaabbb</p>',
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "in empty-p (no br): BACKSPACE (must insert br)",
        content: "<p></p>",
        steps: [{
            start: "p->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>", // The br is there to ensure the carret can enter the p tag
            start: "br->0",
        },
    },
    {
        name: "in empty-p: BACKSPACE (must leave it unchanged)",
        content: "<p><br></p>",
        steps: [{
            start: "p->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>", // The br is there to ensure the carret can enter the p tag
            start: "br->0",
        },
    },
    {
        name: "in p (empty-p before): BACKSPACE",
        content: "<p><br></p><p>dom to edit</p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p (empty-p.a before): BACKSPACE",
        content: "<p class=\"a\"><br></p><p>dom to edit</p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p: BACKSPACE within text",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom o edit</p>", // The br is there to ensure the carret can enter the p tag
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in p: 2x BACKSPACE within text",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>domo edit</p>", // The br is there to ensure the carret can enter the p tag
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "in p (p > span.a before - span.b after): BACKSPACE at beginning (must attach them)",
        content: "<p><span class=\"a\">dom to</span></p><p><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span><span class=\"b\">edit</span></p>",
            start: "span:eq(0):contents()[0]->6",
        },
    },
    {
        name: "in p (p > span.a before - span.a after): BACKSPACE (must merge them)",
        content: "<p><span class=\"a\">dom to&nbsp;</span></p><p><span class=\"a\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><span class=\"a\">dom to&nbsp;edit</span></p>",
            start: "span:contents()[0]->7",
        },
    },
    {
        name: "in p (b before): BACKSPACE",
        content: "<p><b>dom</b> to edit</p>",
        steps: [{
            start: "p:contents()[1]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><b>do</b>&nbsp;to edit</p>",
            start: "b:contents()[0]->2",
        },
    },
    {
        name: "in p (div > span.a before - span.a after): BACKSPACE at beginning (must do nothing)",
        content: "<div><span class=\"a\">dom to&nbsp;</span></div><p><span class=\"a\">edit</span></p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<div><span class=\"a\">dom to&nbsp;</span></div><p><span class=\"a\">edit</span></p>",
            start: "span:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in p: BACKSPACE on partial selection",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:contents()[0]->7",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dedit</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "across 2 p's: BACKSPACE on partial selection",
        content: "<p>dom</p><p>to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:eq(1):contents()[0]->3",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dedit</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in p: BACKSPACE within text, with space at beginning",
        content: "<p>     dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->10",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom o edit</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in p: BACKSPACE within text, with one space at beginning",
        content: "<p> dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->6",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>&nbsp;dom o edit</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: BACKSPACE within text, with space at end",
        content: "<p>dom to edit     </p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom o edit</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in p: BACKSPACE within text, with one space at end",
        content: "<p>dom to edit </p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom o edit&nbsp;</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in p: BACKSPACE within text, with space at beginning and end",
        content: "<p>     dom to edit     </p>",
        steps: [{
            start: "p:contents()[0]->10",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom o edit</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in p: BACKSPACE within text, with one space at beginning and one at end",
        content: "<p> dom to edit </p>",
        steps: [{
            start: "p:contents()[0]->6",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>&nbsp;dom o edit&nbsp;</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: BACKSPACE after \\w<br>\\w",
        content: "<p>dom to edi<br>t</p>",
        steps: [{
            start: "p:contents()[2]->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edi<br>&#8203;</p>",
            start: "p:contents()[2]->1",
        },
    },
    {
        name: "in p: BACKSPACE -> 'a' within text, after \\s\\w",
        content: "<p>dom t</p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom a</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with space at beginning",
        content: "<pre>     dom to edit</pre>",
        steps: [{
            start: "pre:contents()[0]->10",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre>     dom o edit</pre>",
            start: "pre:contents()[0]->9",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with one space at beginning",
        content: "<pre> dom to edit</pre>",
        steps: [{
            start: "pre:contents()[0]->6",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre> dom o edit</pre>",
            start: "pre:contents()[0]->5",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with space at end",
        content: "<pre>dom to edit     </pre>",
        steps: [{
            start: "pre:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre>dom o edit     </pre>",
            start: "pre:contents()[0]->4",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with one space at end",
        content: "<pre>dom to edit </pre>",
        steps: [{
            start: "pre:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre>dom o edit </pre>",
            start: "pre:contents()[0]->4",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with space at beginning and end",
        content: "<pre>     dom to edit     </pre>",
        steps: [{
            start: "pre:contents()[0]->10",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre>     dom o edit     </pre>",
            start: "pre:contents()[0]->9",
        },
    },
    {
        name: "in pre: BACKSPACE within text, with one space at beginning and one at end",
        content: "<pre> dom to edit </pre>",
        steps: [{
            start: "pre:contents()[0]->6",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<pre> dom o edit </pre>",
            start: "pre:contents()[0]->5",
        },
    },

    // list UL / OL

    {
        name: "from p to ul > li: BACKSPACE on whole list",
        content: "<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->15",
            end: "p:eq(1):contents()[0)->11",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom not to edit</p>",
            start: "p:contents()[0]->15",
        },
    },
    {
        name: "in ul > second-li > p: BACKSPACE within text",
        content: "<ul><li><p>dom to</p></li><li><p>edit</p></li></ul>",
        steps: [{
            start: "p:eq(1):contents()[0]->4",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p>dom to</p></li><li><p>edi</p></li></ul>",
            start: "p:eq(1):contents()[0]->3",
        },
    },
    {
        name: "in ul > second-li > empty-p: BACKSPACE at beginning",
        content: "<ul><li><p><br></p></li><li><p><br></p></li></ul>",
        steps: [{
            start: "p:eq(1)->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p><br></p></li></ul>",
            start: "p:first:contents()[0]->0",
        },
    },
    {
        name: "in ul > indented-li (no other li - p before): BACKSPACE at beginning",
        content: "<p>dom to</p><ul><ul><li>edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to</p><ul><li>edit</li></ul>",
            start: "li:contents()[0]->0",
        },
    },
    {
        name: "in ul > indented-li (no other li - p before): BACKSPACE -> 'a' at beginning",
        content: "<p>dom to</p><ul><ul><li>edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>dom to</p><ul><li>aedit</li></ul>",
            start: "li:contents()[0]->1",
        },
    },
    {
        name: "in ul > indented-li (no other li - none before): BACKSPACE at beginning",
        content: "<ul><ul><li>dom to edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li>dom to edit</li></ul>",
            start: "li:contents()[0]->0",
        },
    },
    {
        name: "in li: BACKSPACE on partial selection",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:contents()[0]->7",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li>dedit</li></ul>",
            start: "li:contents()[0]->1",
        },
    },
    {
        name: "across 2 li: BACKSPACE on partial selection",
        content: "<ul><li>dom to edit</li><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:eq(1):contents()[0]->7",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li>dedit</li></ul>",
            start: "li:contents()[0]->1",
        },
    },
    {
        name: "in li (no other li): BACKSPACE on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><br></li></ul>",
            start: "li->0",
        },
    },
    {
        name: "in li (no other li): BACKSPACE -> 'a' on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>a</p></li></ul>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in empty-li: BACKSPACE (must remove list)",
        content: "<ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in empty-li (no other li - empty-p before): BACKSPACE -> 'a'",
        content: "<p><br></p><ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p><br></p><p>a</p>",
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in empty-li (no other li - p before): BACKSPACE",
        content: "<p>toto</p><ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>toto</p><p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in li (no other li - p before): BACKSPACE at start",
        content: "<p>toto</p><ul><li>&nbsp;<img src='/web_editor/static/src/img/transparent.png'></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>toto</p><p>&nbsp;<img data-src=\"/web_editor/static/src/img/transparent.png\"></p>",
            start: "p:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in empty-indented-li (other li - no other indented-li): BACKSPACE",
        content: "<ul><li><p>toto</p></li><ul><li><br></li></ul><li><p>tutu</p></li></ul>",
        steps: [{
            start: "ul ul li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><br></li><li><p>tutu</p></li></ul>",
            start: "li:eq(1) br->0",
        },
    },
    {
        name: "in empty-indented-li (other li - other indented-li): BACKSPACE",
        content: "<ul><li><p>toto</p></li><ul><li><br></li><li><br></li></ul><li><p>tutu</p></li></ul>",
        steps: [{
            start: "ul ul li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><br></li><ul><li><br></li></ul><li><p>tutu</p></li></ul>",
            start: "li:eq(1) br->0",
        },
    },
    {
        name: "in empty-indented-li (no other li, no other indented-li): BACKSPACE",
        content: "<ul><ul><li><br></li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><br></li></ul>",
            start: "br->0",
        },
    },
    {
        name: "in indented-li (other li, other indented-li): BACKSPACE at start",
        content: "<ul><li><p>toto</p></li><ul><li><p>xxx</p></li><li><p>yyy</p></li></ul><li><p>tutu</p></li></ul>",
        steps: [{
            start: "ul ul li:contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><p>xxx</p></li><ul><li><p>yyy</p></li></ul><li><p>tutu</p></li></ul>",
            start: "p:eq(1):contents()[0]->0",
        },
    },
    {
        name: "in li > second-p: BACKSPACE at start",
        content: "<ul><li><p>toto</p></li><li><p>xxx</p><p>yyy</p></li><li><p>tutu</p></li></ul>",
        steps: [{
            start: "li:eq(1) p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><p>xxxyyy</p></li><li><p>tutu</p></li></ul>",
            start: "li:eq(1) p:contents()[0]->3",
        },
    },
    {
        name: "in li (li after): BACKSPACE at start, with spaces",
        content: "<p>dom to edit&nbsp;    </p><ul><li><p>    &nbsp; dom to edit</p></li><li><p>dom not to edit</p></li></ul>",
        steps: [{
            start: "p:eq(1):contents()[0]->6",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edit&nbsp;dom to edit</p><ul><li><p>dom not to edit</p></li></ul>",
            start: "p:contents()[0]->12",
        },
    },
    {
        name: "in li > p: BACKSPACE after single character",
        content: "<ul><li><p>a</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<ul><li><p><br></p></li></ul>",
            start: "br->0",
        },
    },
    {
        name: "in li > p: BACKSPACE -> 'a' after single character",
        content: "<ul><li><p>a</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->1",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>a</p></li></ul>",
            start: "p:contents()[0]->1",
        },
    },

    // end list UL / OL

    {
        name: "in p: BACKSPACE on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>",
            start: "p->0",
        },
    },
    {
        name: "in p: BACKSPACE -> 'a' on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>a</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in complex-dom: BACKSPACE on selection of most contents",
        content: "<p><b>dom</b></p><p><b>to<br>partially</b>re<i>m</i>ove</p>",
        steps: [{
            start: "b:contents()[0]->2",
            end: "i:contents()[0]->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><b>do</b>ove</p>",
            start: "b:contents()[0]->2",
        },
    },
    {
        name: "in complex-dom: BACKSPACE on selection of all contents",
        content: "<p><b>dom</b></p><p><b>to<br>completely</b>remov<i>e</i></p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "i:contents()[0]->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in p: BACKSPACE after br",
        content: "<p>dom <br>to edit</p>",
        steps: [{
            start: "p:contents()[2]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in complex-dom (span > b -> ENTER in contents)",
        content: "<span><b>dom<br></b></span><br><span><b>&nbsp;to edit</b></span>",
        steps: [{
            start: "b:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<span><b>dom<br>&nbsp;to edit</b></span>",
            start: "b:contents(2)->0",
        },
    },
    {
        name: "in complex-dom (span > b -> ENTER in contents): 2 x BACKSPACE",
        content: "<span><b>dom<br></b></span><br><span><b>a to edit</b></span>",
        steps: [{
            start: "b:eq(1):contents()[0]->1",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<span><b>dom<br>&nbsp;to edit</b></span>",
            start: "b:contents(2)->0",
        },
    },
    {
        name: "in p (hr before): BACKSPACE",
        content: '<p>aaa</p><hr><p>bbb</p>',
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>aaabbb</p>',
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "in p with multi br[id] (p before and after) (1)",
        content: '<p>dom not to edit</p><p><br id="br-1"><br id="br-2"><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
        steps: [{
            start: "p:eq(1)->2",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br id="br-1"><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
            start: "p:eq(1)->1",
        },
    },
    {
        name: "in p with multi br[id] (p before and after) (2)",
        content: '<p>dom not to edit</p><p><br id="br-1"><br id="br-2"><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
        steps: [{
            start: "br:eq(2)->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br id="br-1"><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
            start: "p:eq(1)->1",
        },
    },
    {
        name: "in p with multi br[id] (p before and after): 2x BACKSPACE",
        content: '<p>dom not to edit</p><p><br id="br-1"><br id="br-2"><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
        steps: [{
            start: "p:eq(1)->2",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br id="br-3"><br id="br-4"></p><p>dom not to edit</p>',
            start: "p:eq(1)->0",
        },
    },
    {
        name: "in p with multi br (p before and after) (1)",
        content: '<p>dom not to edit</p><p><br><br><br><br></p><p>dom not to edit</p>',
        steps: [{
            start: "p:eq(1)->2",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br><br><br></p><p>dom not to edit</p>',
            start: "p:eq(1)->1",
        },
    },
    {
        name: "in p with multi br (p before and after) (2)",
        content: '<p>dom not to edit</p><p><br><br><br><br></p><p>dom not to edit</p>',
        steps: [{
            start: "br:eq(2)->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br><br><br></p><p>dom not to edit</p>',
            start: "p:eq(1)->1",
        },
    },
    {
        name: "in p with multi br (p before and after): 2x BACKSPACE",
        content: '<p>dom not to edit</p><p><br><br><br><br></p><p>dom not to edit</p>',
        steps: [{
            start: "p:eq(1)->2",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom not to edit</p><p><br><br></p><p>dom not to edit</p>',
            start: "p:eq(1)->0",
        },
    },
    {
        name: "in p: BACKSPACE within text after \w+<br>",
        content: '<p>dom to<br>edit</p>',
        steps: [{
            start: "p:contents()[2]->3",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>dom to<br>edt</p>',
            start: "p:contents()[2]->2",
        },
    },

    // table

    {
        name: "in empty-td (td before): BACKSPACE -> 'a' at start",
        content: '<table class="table table-bordered"><tbody><tr><td><p><br></p></td><td><p><br></p></td></tr></tbody></table>',
        steps: [{
            start: "p:eq(1)->1",
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p><br></p></td><td><p>a</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in td (td before): 2x BACKSPACE -> 'a' after first character",
        content: '<table class="table table-bordered"><tbody><tr><td><p>dom not to edit</p></td><td><p>dom to edit</p></td></tr></tbody></table>',
        steps: [{
            start: "p:eq(1):contents()[0]->1",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>dom not to edit</p></td><td><p>aom to edit</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in td (no other td): BACKSPACE within text",
        content: '<table class="table table-bordered"><tbody><tr><td><p>dom to edit</p></td></tr></tbody></table>',
        steps: [{
            start: "p:contents()[0]->5",
            key: 'BACKSPACE',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>dom o edit</p></td></tr></tbody></table>',
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in complex-dom (empty-td (td before) -> 2x SHIFT-ENTER): 3x BACKSPACE -> 'a'",
        content: '<table class="table table-bordered"><tbody><tr><td><p>dom not to edit</p></td><td><p><br><br><br></p></td></tr></tbody></table>',
        steps: [{
            start: 'p:eq(1)->3',
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>dom not to edit</p></td><td><p>a</p></td></tr></tbody></table>',
            start: "p:eq(1):contents()[0]->1",
        },
    },
    {
        name: "in h1: BACKSPACE on full selection -> 'a'",
        content: '<h1>dom to delete</h1>',
        steps: [{
            start: 'h1:contents()[0]->0',
            end: 'h1:contents()[0]->13',
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<h1>a</h1>',
            start: "h1:contents()[0]->1",
        },
    },
    {
        name: "in h1: BACKSPACE on full selection -> BACKSPACE -> 'a'",
        content: '<h1>dom to delete</h1>',
        steps: [{
            start: 'h1:contents()[0]->0',
            end: 'h1:contents()[0]->13',
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<p>a</p>',
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in h1: BACKSPACE on full selection -> DELETE -> 'a'",
        content: '<h1>dom to delete</h1>',
        steps: [{
            start: 'h1:contents()[0]->0',
            end: 'h1:contents()[0]->13',
            key: 'BACKSPACE',
        }, {
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<h1>a</h1>',
            start: "h1:contents()[0]->1",
        },
    },

    // merging non-similar blocks

    {
        name: "in p (h1 before): BACKSPACE at start",
        content: '<h1>node to merge with</h1><p>node to merge</p>',
        steps: [{
            start: 'p:contents()[0]->0',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<h1>node to merge withnode to merge</h1>',
            start: "h1:contents()[0]->18",
        },
    },
    {
        name: "in empty-p (h1 before): BACKSPACE",
        content: "<h1>dom to edit</h1><p><br></p>",
        steps: [{
            start: "p->1",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<h1>dom to edit</h1>",
            start: "h1:contents()[0]->11",
        },
    },
    {
        name: "in empty-p (h1 before): 2x BACKSPACE",
        content: "<h1>dom to edit</h1><p><br></p>",
        steps: [{
            start: "p->1",
            key: 'BACKSPACE',
        }, {
            key: 'BACKSPACE',
        }],
        test: {
            content: "<h1>dom to edi</h1>",
            start: "h1:contents()[0]->10",
        },
    },
    {
        name: "in p (ul before): BACKSPACE at start",
        content: '<ul><li><p>node to merge with</p></li></ul><p>node to merge</p>',
        steps: [{
            start: 'p:eq(1):contents()[0]->0',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<ul><li><p>node to merge withnode to merge</p></li></ul>',
            start: "p:contents()[0]->18",
        },
    },
    {
        name: "in p > b (ul before, i after): BACKSPACE at start",
        content: '<ul><li><p>node to merge with</p></li></ul><p><b>node</b><i> to merge</i></p>',
        steps: [{
            start: 'b:contents()[0]->0',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<ul><li><p>node to merge with<b>node</b><i> to merge</i></p></li></ul>',
            start: "p:contents()[0]->18",
        },
    },
    {
        name: "in p > b (ul > i before, i after): BACKSPACE at start",
        content: '<ul><li><p><i>node to merge with</i></p></li></ul><p><b>node</b><i> to merge</i></p>',
        steps: [{
            start: 'b:contents()[0]->0',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<ul><li><p><i>node to merge with</i><b>node</b><i> to merge</i></p></li></ul>',
            start: "i:contents()[0]->18",
        },
    },
    {
        name: "in p.c (p.a > span.b before - span.b after): BACKSPACE at beginning",
        content: "<p class=\"a\"><span class=\"b\">dom to&nbsp;</span></p><p class=\"c\"><span class=\"b\">edit</span></p>",
        steps: [{
            start: "p:eq(1):contents()[0]->0",
            key: 'BACKSPACE',
        }],
        test: {
            content: "<p class=\"a\"><span class=\"b\">dom to&nbsp;edit</span></p>",
            start: "span:eq(0):contents()[0]->7",
        },
    },
    {
        name: "from h1 to p: BACKSPACE",
        content: '<h1>node to merge with</h1><p>node to merge</p>',
        steps: [{
            start: 'h1:contents()[0]->5',
            end: 'p:contents()[0]->2',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<h1>node de to merge</h1>',
            start: "h1:contents()[0]->5",
        },
    },
    {
        name: "from h1 to p: BACKSPACE at start",
        content: '<h1><b>node to merge with</b></h1><p>node to merge</p>',
        steps: [{
            start: 'b:contents()[0]->0',
            end: 'p:contents()[0]->2',
            key: 'BACKSPACE',
        }],
        test: {
            content: '<p>de to merge</p>',
            start: "p:contents()[0]->0",
        },
    },
];

QUnit.test('Backspace', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsBackspace).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

var keyboardTestsDelete = [{
        name: "in empty-p (no br): DELETE (must insert br)",
        content: "<p></p>",
        steps: [{
            start: "p->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p><br></p>", // The br is there to ensure the carret can enter the p tag
            start: "br->0",
        },
    },
    {
        name: "in empty-p: DELETE (must leave it unchanged)",
        content: "<p><br></p>",
        steps: [{
            start: "p->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p><br></p>", // The br is there to ensure the carret can enter the p tag
            start: "p->0",
        },
    },
    {
        name: "in empty-p: DELETE (must leave it unchanged) (2)",
        content: "<p>\n    <br>\n</p>",
        steps: [{
            start: "p->1",
            key: 'DELETE',
        }],
        test: {
            content: "<p>\n    <br>\n</p>", // The br is there to ensure the carret can enter the p tag
            start: "p:contents()[1]->0",
        },
    },
    {
        name: "in empty-p (p after): DELETE",
        content: "<p><br></p><p>dom to edit</p>",
        steps: [{
            start: "p->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in empty-p (p after): DELETE (2)",
        content: "<p>\n    <br>\n</p><p>\n    dom to edit</p>",
        steps: [{
            start: "p:contents()[1]->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in empty-p.a (p after): DELETE",
        content: "<p class=\"a\"><br></p><p>dom to edit</p>",
        steps: [{
            start: "p->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in empty-p.a (p after): DELETE (2)",
        content: "<p class=\"a\"><br></p><p>dom to edit</p>",
        steps: [{
            start: "p->1",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom to edit</p>",
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p: DELETE at start",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'DELETE',
        }],
        test: {
            content: "<p>om to edit</p>", // The br is there to ensure the carret can enter the p tag
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p: 2x DELETE at start",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }],
        test: {
            content: "<p>m to edit</p>", // The br is there to ensure the carret can enter the p tag
            start: "p:contents()[0]->0",
        },
    },
    {
        name: "in p: DELETE within text",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom t edit</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: DELETE within text, with space at beginning",
        content: "<p>     dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->10",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom t edit</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: DELETE within text, with one space at beginning",
        content: "<p> dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->6",
            key: 'DELETE',
        }],
        test: {
            content: "<p>&nbsp;dom t edit</p>",
            start: "p:contents()[0]->6",
        },
    },
    {
        name: "in p: DELETE within text, with space at end",
        content: "<p>dom to edit     </p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom t edit</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: DELETE within text, with one space at end",
        content: "<p>dom to edit </p>",
        steps: [{
            start: "p:contents()[0]->5",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom t edit&nbsp;</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: DELETE within text, with space at beginning and end",
        content: "<p>     dom to edit     </p>",
        steps: [{
            start: "p:contents()[0]->10",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom t edit</p>",
            start: "p:contents()[0]->5",
        },
    },
    {
        name: "in p: DELETE within text, with one space at beginning and one at end",
        content: "<p> dom to edit </p>",
        steps: [{
            start: "p:contents()[0]->6",
            key: 'DELETE',
        }],
        test: {
            content: "<p>&nbsp;dom t edit&nbsp;</p>",
            start: "p:contents()[0]->6",
        },
    },
    {
        name: "in p: DELETE -> 'a' within text, before \\w\\s",
        content: "<p>dom t</p>",
        steps: [{
            start: "p:contents()[0]->2",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>doa t</p>",
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "in pre: DELETE within text, with space at beginning",
        content: "<pre>     dom to edit</pre>",
        steps: [{
            start: "pre:contents()[0]->10",
            key: 'DELETE',
        }],
        test: {
            content: "<pre>     dom t edit</pre>",
            start: "pre:contents()[0]->10",
        },
    },
    {
        name: "in pre: DELETE within text, with one space at beginning",
        content: "<pre> dom to edit</pre>",
        steps: [{
            start: "pre:contents()[0]->6",
            key: 'DELETE',
        }],
        test: {
            content: "<pre> dom t edit</pre>",
            start: "pre:contents()[0]->6",
        },
    },
    {
        name: "in pre: DELETE within text, with space at end",
        content: "<pre>dom to edit     </pre>",
        steps: [{
            start: "pre:contents()[0]->5",
            key: 'DELETE',
        }],
        test: {
            content: "<pre>dom t edit     </pre>",
            start: "pre:contents()[0]->5",
        },
    },
    {
        name: "in pre: DELETE within text, with one space at end",
        content: "<pre>dom to edit </pre>",
        steps: [{
            start: "pre:contents()[0]->5",
            key: 'DELETE',
        }],
        test: {
            content: "<pre>dom t edit </pre>",
            start: "pre:contents()[0]->5",
        },
    },
    {
        name: "in pre: DELETE within text, with space at beginning and end",
        content: "<pre>     dom to edit     </pre>",
        steps: [{
            start: "pre:contents()[0]->10",
            key: 'DELETE',
        }],
        test: {
            content: "<pre>     dom t edit     </pre>",
            start: "pre:contents()[0]->10",
        },
    },
    {
        name: "in pre: DELETE within text, with one space at beginning and one at end",
        content: "<pre> dom to edit </pre>",
        steps: [{
            start: "pre:contents()[0]->6",
            key: 'DELETE',
        }],
        test: {
            content: "<pre> dom t edit </pre>",
            start: "pre:contents()[0]->6",
        },
    },

    // list UL / OL

    {
        name: "in empty-li (no other li): DELETE (must do nothing)",
        content: "<ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><br></li></ul>",
            start: "li->0",
        },
    },
    {
        name: "from p to li > p: DELETE on whole list",
        content: "<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->15",
            end: "p:eq(1):contents()[0)->11",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom not to edit</p>",
            start: "p:contents()[0]->15",
        },
    },
    {
        name: "in empty-li (no other li): DELETE -> 'a' (must write into it)",
        content: "<ul><li><br></li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>a</p></li></ul>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in li (li after): DELETE at end (must move contents of second li to carret)",
        content: "<ul><li>dom to&nbsp;</li><li>edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->7",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li>dom to&nbsp;edit</li></ul>",
            start: "li:contents()[0]->7",
        },
    },
    {
        name: "in li (li after): DELETE -> 'a' at end (must move contents of second li to carret, then write)",
        content: "<ul><li>dom to&nbsp;</li><li>edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->7",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li>dom to aedit</li></ul>",
            start: "li:contents()[0]->8",
        },
    },
    {
        name: "in li > p: DELETE before single character",
        content: "<ul><li><p>a</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><p><br></p></li></ul>",
            start: "br->0",
        },
    },
    {
        name: "in li > p: DELETE -> 'a' before single character",
        content: "<ul><li><p>a</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->0",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>a</p></li></ul>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in li > p (p after): DELETE at end",
        content: "<ul><li><p>toto</p></li><li><p>xxx</p><p>yyy</p></li><li><p>tutu</p></li></ul>",
        steps: [{
            start: "li:eq(1) p:eq(0):contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><p>xxxyyy</p></li><li><p>tutu</p></li></ul>",
            start: "li:eq(1) p:eq(0):contents()[0]->3",
        },
    },
    {
        name: "in li > p (b before - p after): DELETE at end",
        content: "<ul><li><p>toto</p></li><li><p><b>x</b>xx</p><p><b>y</b>yy</p></li><li><p>tutu</p></li></ul>",
        steps: [{
            start: "li:eq(1) p:eq(0):contents()[1]->2",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><p><b>x</b>xx<b>y</b>yy</p></li><li><p>tutu</p></li></ul>",
            start: "li:eq(1) p:eq(0):contents()[1]->2",
        },
    },
    {
        name: "in li > p (p.o_default_snippet_text after): DELETE at end",
        content: '<ul><li><p>toto</p></li><li><p>xxx</p><p class="o_default_snippet_text">yyy</p></li><li><p>tutu</p></li></ul>',
        steps: [{
            start: "li:eq(1) p:eq(0):contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><p>toto</p></li><li><p>xxxyyy</p></li><li><p>tutu</p></li></ul>",
            start: "li:eq(1) p:eq(0):contents()[0]->3",
        },
    },
    {
        name: "in indented-ul > li: DELETE at end (must do nothing)",
        content: "<ul><ul><li>dom to edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><ul><li>dom to edit</li></ul></ul>",
            start: "li:contents()[0]->11",
        },
    },
    {
        name: "in indented-ul > li: DELETE at end -> 'a' at end (must write)",
        content: "<ul><ul><li>dom to edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->11",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><ul><li>dom to edita</li></ul></ul>",
            start: "li:contents()[0]->12",
        },
    },
    {
        name: "in indented-ul > li (non-indented-li after): DELETE at end",
        content: "<ul><ul><li>dom to edit</li></ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><ul><li>dom to editdom to edit</li></ul></ul>",
            start: "li:contents()[0]->11",
        },
    },
    {
        name: "in ul > li (indented-li after): DELETE at end",
        content: "<ul><li>dom to edit</li><ul><li>dom to edit</li></ul></ul>",
        steps: [{
            start: "li:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li>dom to editdom to edit</li></ul>",
            start: "li:contents()[0]->11",
        },
    },
    {
        name: "in li: DELETE on partial selection",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:contents()[0]->7",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li>dedit</li></ul>",
            start: "li:contents()[0]->1",
        },
    },
    {
        name: "across 2 li: DELETE on partial selection",
        content: "<ul><li>dom to edit</li><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->1",
            end: "li:eq(1):contents()[0]->7",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li>dedit</li></ul>",
            start: "li:contents()[0]->1",
        },
    },
    {
        name: "in li: DELETE on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<ul><li><br></li></ul>",
            start: "li->0",
        },
    },
    {
        name: "in li: DELETE -> 'a' on selection of all contents",
        content: "<ul><li>dom to edit</li></ul>",
        steps: [{
            start: "li:contents()[0]->0",
            end: "li:contents()[0]->11",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<ul><li><p>a</p></li></ul>",
            start: "p:contents()[0]->1",
        },
    },

    // end list UL / OL

    {
        name: "in p (b before): DELETE",
        content: "<p><b>dom</b>to edit</p>",
        steps: [{
            start: "b:contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: "<p><b>dom</b>o edit</p>",
            start: "p:contents(1)->0",
        },
    },
    {
        name: "in p > span.a (div > span.a after): DELETE at end (must do nothing)",
        content: "<p><span class=\"a\">dom to</span></p><div><span class=\"a\">edit</span></div>",
        steps: [{
            start: "span:contents()[0]->6",
            key: 'DELETE',
        }],
        test: {
            content: "<p><span class=\"a\">dom to</span></p><div><span class=\"a\">edit</span></div>",
            start: "span:contents()[0]->6",
        },
    },
    {
        name: "in p: DELETE on partial selection",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:contents()[0]->7",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dedit</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "across 2 p: DELETE on partial selection",
        content: "<p>dom</p><p>to edit</p>",
        steps: [{
            start: "p:contents()[0]->1",
            end: "p:eq(1):contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dedit</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in p: DELETE on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<p><br></p>",
            start: "p->0",
        },
    },
    {
        name: "in p: DELETE -> 'a' on selection of all contents",
        content: "<p>dom to edit</p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "p:contents()[0]->11",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: "<p>a</p>",
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in p: DELETE before br",
        content: "<p>dom <br>to edit</p>",
        steps: [{
            start: "p:contents()[0]->4",
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom&nbsp;to edit</p>",
            start: "p:contents()[0]->4",
        },
    },
    {
        name: "in complex-dom: DELETE on selection of most contents",
        content: "<p><b>dom</b></p><p><b>to<br>partially</b>re<i>m</i>ove</p>",
        steps: [{
            start: "b:contents()[0]->2",
            end: "i:contents()[0]->1",
            key: 'DELETE',
        }],
        test: {
            content: "<p><b>do</b>ove</p>",
            start: "b:contents()[0]->2",
        },
    },
    {
        name: "in complex-dom: DELETE on selection of all contents",
        content: "<p><b>dom</b></p><p><b>to<br>completely</b>remov<i>e</i></p>",
        steps: [{
            start: "p:contents()[0]->0",
            end: "i:contents()[0]->1",
            key: 'DELETE',
        }],
        test: {
            content: "<p><br></p>",
            start: "br->0",
        },
    },
    {
        name: "in complex-dom (span > b -> ENTER): DELETE",
        content: "<span><b>dom</b></span><br><span><b> to edit</b></span>",
        steps: [{
            start: "b:eq(0):contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: "<span><b>dom&nbsp;to edit</b></span>",
            start: "b:contents()[0]->3",
        },
    },
    {
        name: "in p (span.fa after): DELETE",
        content: '<p>aaa<span class="fa fa-star"></span>bbb</p>',
        steps: [{
            start: "p:contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: '<p>aaabbb</p>',
            start: "p:contents()[0]->3",
        },
    },
    {
        name: "in p (hr after): DELETE",
        content: '<p>aaa</p><hr><p>bbb</p>',
        steps: [{
            start: "p:eq(0):contents()[0]->3",
            key: 'DELETE',
        }],
        test: {
            content: '<p>aaabbb</p>',
            start: "p:contents()[0]->3",
        },
    },

    // table

    {
        name: "in empty-td (td after): DELETE -> 'a' at start",
        content: '<table class="table table-bordered"><tbody><tr><td><p><br></p></td><td><p><br></p></td></tr></tbody></table>',
        steps: [{
            start: "p->1",
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>a</p></td><td><p><br></p></td></tr></tbody></table>',
            start: "p:contents()[0]->1",
        },
    },
    {
        name: "in td (td after): 2x DELETE -> 'a' after first character",
        content: '<table class="table table-bordered"><tbody><tr><td><p>dom to edit</p></td><td><p>dom not to edit</p></td></tr></tbody></table>',
        steps: [{
            start: "p:contents()[0]->1",
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }, {
            key: 'a',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>da to edit</p></td><td><p>dom not to edit</p></td></tr></tbody></table>',
            start: "p:contents()[0]->2",
        },
    },
    {
        name: "in td: DELETE within text",
        content: '<table class="table table-bordered"><tbody><tr><td><p>dom to edit</p></td></tr></tbody></table>',
        steps: [{
            start: "p:contents()[0]->4",
            key: 'DELETE',
        }],
        test: {
            content: '<table class="table table-bordered"><tbody><tr><td><p>dom o edit</p></td></tr></tbody></table>',
            start: "p:contents()[0]->4",
        },
    },

    // merging non-similar blocks

    {
        name: "in p (ul after, with spaces): DELETE at end (must bring contents of first li to end of p)",
        content: "<p>dom to edit&nbsp;    </p><ul><li><p>    &nbsp; dom to edit</p></li><li><p>dom not to edit</p></li></ul>",
        steps: [{
            start: "p:contents()[0]->11",
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }],
        test: {
            content: "<p>dom to editdom to edit</p><ul><li><p>dom not to edit</p></li></ul>",
            start: "p:contents()[0]->11",
        },
    },
    {
        name: "in h1 (p after): DELETE at end",
        content: '<h1>node to merge with</h1><p>node to merge</p>',
        steps: [{
            start: 'h1:contents()[0]->18',
            key: 'DELETE',
        }],
        test: {
            content: '<h1>node to merge withnode to merge</h1>',
            start: "h1:contents()[0]->18",
        },
    },
    {
        name: "in h1 (empty-p after): DELETE at end",
        content: "<h1>dom to edit</h1><p><br></p>",
        steps: [{
            start: "h1:contents()[0]->11",
            key: 'DELETE',
        }],
        test: {
            content: "<h1>dom to edit</h1>",
            start: "h1:contents()[0]->11",
        },
    },
    {
        name: "in h1 (empty-p after): 2x DELETE at end",
        content: "<h1>dom to edit</h1><p><br></p>",
        steps: [{
            start: "h1:contents()[0]->11",
            key: 'DELETE',
        }, {
            key: 'DELETE',
        }],
        test: {
            content: "<h1>dom to edit</h1>",
            start: "h1:contents()[0]->11",
        },
    },
    {
        name: "in li > p (p after): DELETE at end",
        content: '<ul><li><p>node to merge with</p></li></ul><p>node to merge</p>',
        steps: [{
            start: 'p:contents()[0]->18',
            key: 'DELETE',
        }],
        test: {
            content: '<ul><li><p>node to merge withnode to merge</p></li></ul>',
            start: "p:contents()[0]->18",
        },
    },
    {
        name: "in li > p (i before - p > b after): DELETE at end",
        content: '<ul><li><p><i>node to merge</i> with</p></li></ul><p><b>node</b> to merge</p>',
        steps: [{
            start: 'p:contents()[1]->5',
            key: 'DELETE',
        }],
        test: {
            content: '<ul><li><p><i>node to merge</i>&nbsp;with<b>node</b> to merge</p></li></ul>',
            start: "p:contents()[1]->5",
        },
    },
    {
        name: "in li > p > i (b before - p > b after): DELETE at end",
        content: '<ul><li><p><b>node to </b><i>merge with</i></p></li></ul><p><b>node</b> to merge</p>',
        steps: [{
            start: 'i:contents()[0]->10',
            key: 'DELETE',
        }],
        test: {
            content: '<ul><li><p><b>node to </b><i>merge with</i><b>node</b> to merge</p></li></ul>',
            start: "i:contents()[0]->10",
        },
    },
    {
        name: "in p.a > span.b (p.c > span.b after): DELETE at end",
        content: "<p class=\"a\"><span class=\"b\">dom to&nbsp;</span></p><p class=\"c\"><span class=\"b\">edit</span></p>",
        steps: [{
            start: "span:contents()[0]->7",
            key: 'DELETE',
        }],
        test: {
            content: "<p class=\"a\"><span class=\"b\">dom to&nbsp;edit</span></p>",
            start: "span:contents()[0]->7",
        },
    },
];

var keyboardTestsDeleteDOM = [
    '<div style="margin:0px; padding:0px;">',
    '    <p style="margin:0px; padding:0px;">',
    '        Dear Ready Mat',
    '        <br><br>',
    '        Here is',
    '            the quotation <strong>SO003</strong>',
    '        amounting in <strong>$&nbsp;1,127.50</strong>',
    '        from YourCompany.',
    '        <br><br>',
    '        Do not hesitate to contact us if you have any question.',
    '        <br><br>',
    '    </p>',
    '    <table width="100%">',
    '        <tbody><tr>',
    '            <td>',
    '                <strong>Virtual Interior Design</strong><br>On Site ',
    '            </td>',
    '            <td width="100px" align="right">',
    '                10 Hour(s)',
    '            </td>',
    '        </tr>',
    '    </tbody></table>',
    '</div>',
    '            '
].join('\n');
keyboardTestsDelete.push({
    name: "in complex-dom: DELETE text selection",
    content: keyboardTestsDeleteDOM,
    steps: [{
            start: "p:contents()[0]->20",
            end: 'p:contents()[0]->23',
            key: 'DELETE',
        },
        {
            start: "p:contents()[10]->55",
            end: 'p:contents()[10]->63',
            key: 'DELETE',
        },
    ],
    test: {
        content: keyboardTestsDeleteDOM.replace('question', '').replace('Mat', ''),
        start: "p:contents()[10]->55",
    },
}, {
    name: "in complex-dom: DELETE br",
    content: keyboardTestsDeleteDOM,
    steps: [{
        start: "p->2",
        key: 'DELETE',
    }, ],
    test: {
        content: keyboardTestsDeleteDOM.replace('<br>', ''),
        start: "p:contents()[2]->0",
    },
}, {
    name: "in complex-dom: DELETE selection (all strong text content)",
    content: keyboardTestsDeleteDOM,
    steps: [{
        start: "strong:eq(0):contents()[0]->0",
        end: 'strong:eq(0):contents()[0]->5',
        key: 'DELETE',
    }, ],
    test: {
        content: keyboardTestsDeleteDOM.replace(/<strong>SO003<\/strong>\s+/, '&nbsp;'),
        start: "p:contents()[3]->43",
    },
}, {
    name: "in complex-dom: DELETE selection (in strong text content before br)",
    content: keyboardTestsDeleteDOM,
    steps: [{
        start: "strong:eq(2):contents()[0]->17",
        end: 'strong:eq(2):contents()[0]->23',
        key: 'DELETE',
    }, ],
    test: {
        content: keyboardTestsDeleteDOM.replace(/Design/, ''),
        start: "strong:eq(2):contents()[0]->17",
    },
});

QUnit.test('Delete', function (assert) {
    var done = assert.async();
    weTestUtils.createWysiwyg({
        data: this.data,
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        weTestUtils.testKeyboard($editable, assert, keyboardTestsDelete).then(function () {
            wysiwyg.destroy();
            done();
        });
    });
});

});
});
});
