odoo.define('web_editor.test_utils', function (require) {
"use strict";

var ajax = require('web.ajax');
var MockServer = require('web.MockServer');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var Wysiwyg = require('web_editor.wysiwyg');
var options = require('web_editor.snippets.options');

const COLOR_PICKER_TEMPLATE = `
    <t t-name="web_editor.colorpicker">
        <colorpicker>
            <div class="o_colorpicker_section" data-name="theme" data-display="Theme Colors" data-icon-class="fa fa-flask">
                <button data-color="o-color-1"/>
                <button data-color="o-color-2"/>
                <button data-color="o-color-3"/>
                <button data-color="o-color-4"/>
                <button data-color="o-color-5"/>
            </div>
            <div class="o_colorpicker_section" data-name="transparent_grayscale" data-display="Transparent Colors" data-icon-class="fa fa-eye-slash">
                <button class="o_btn_transparent"/>
                <button data-color="black-25"/>
                <button data-color="black-50"/>
                <button data-color="black-75"/>
                <button data-color="white-25"/>
                <button data-color="white-50"/>
                <button data-color="white-75"/>
            </div>
            <div class="o_colorpicker_section" data-name="common" data-display="Common Colors" data-icon-class="fa fa-paint-brush"/>
        </colorpicker>
    </t>`;
const SNIPPETS_TEMPLATE = `
    <h2 id="snippets_menu">Add blocks</h2>
    <div id="o_scroll">
        <div id="snippet_structure" class="o_panel">
            <div class="o_panel_header">First Panel</div>
            <div class="o_panel_body">
                <div name="Separator" data-oe-type="snippet" data-oe-thumbnail="/website/static/src/img/snippets_thumbs/s_separator.png">
                    <div class="s_hr pt32 pb32">
                        <hr class="s_hr_1px s_hr_solid w-100 mx-auto"/>
                    </div>
                </div>
                <div name="Content" data-oe-type="snippet" data-oe-thumbnail="/website/static/src/img/snippets_thumbs/s_text_block.png">
                    <section name="Content+Options" class="test_option_all pt32 pb32" data-oe-type="snippet" data-oe-thumbnail="/website/static/src/img/snippets_thumbs/s_text_block.png">
                        <div class="container">
                            <div class="row">
                                <div class="col-lg-10 offset-lg-1 pt32 pb32">
                                    <h2>Title</h2>
                                    <p class="lead o_default_snippet_text">Content</p>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    </div>
    <div id="snippet_options" class="d-none">
        <div data-js="many2one" data-selector="[data-oe-many2one-model]:not([data-oe-readonly])" data-no-check="true"/>
        <div data-js="content"
            data-selector=".s_hr, .test_option_all"
            data-drop-in=".note-editable"
            data-drop-near="p, h1, h2, h3, blockquote, .s_hr"/>
        <div data-js="sizing_y" data-selector=".s_hr, .test_option_all"/>
        <div data-selector=".test_option_all">
            <we-colorpicker string="Background Color" data-select-style="true" data-css-property="background-color" data-color-prefix="bg-"/>
        </div>
        <div data-js="BackgroundImage" data-selector=".test_option_all">
            <we-button data-choose-image="true" data-no-preview="true">
                <i class="fa fa-picture-o"/> Background Image
            </we-button>
        </div>
        <div data-js="option_test" data-selector=".s_hr">
            <we-select string="Alignment">
                <we-button data-select-class="align-items-start">Top</we-button>
                <we-button data-select-class="align-items-center">Middle</we-button>
                <we-button data-select-class="align-items-end">Bottom</we-button>
                <we-button data-select-class="align-items-stretch">Equal height</we-button>
            </we-select>
        </div>
    </div>`;

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Promise}
     */
    async _performRpc(route, args) {
        if (args.model === "ir.ui.view") {
            if (args.method === 'read_template' && args.args[0] === "web_editor.colorpicker") {
                return COLOR_PICKER_TEMPLATE;
            }
            if (args.method === 'render_public_asset' && args.args[0] === "web_editor.snippets") {
                return SNIPPETS_TEMPLATE;
            }
        }
        return this._super(...arguments);
    },
});

/**
 * Options with animation and edition for test.
 */
options.registry.option_test = options.Class.extend({
    cleanForSave: function () {
        this.$target.addClass('cleanForSave');
    },
    onBuilt: function () {
        this.$target.addClass('built');
    },
    onBlur: function () {
        this.$target.removeClass('focus');
    },
    onClone: function () {
        this.$target.addClass('clone');
        this.$target.removeClass('focus');
    },
    onFocus: function () {
        this.$target.addClass('focus');
    },
    onMove: function () {
        this.$target.addClass('move');
    },
    onRemove: function () {
        this.$target.closest('.note-editable').addClass('snippet_has_removed');
    },
});


/**
 * Constructor WysiwygTest why editable and unbreakable node used in test.
 */
var WysiwygTest = Wysiwyg.extend({
    _parentToDestroyForTest: null,
    /**
     * Override 'destroy' of discuss so that it calls 'destroy' on the parent.
     *
     * @override
     */
    destroy: function () {
        unpatch();
        this._super();
        this.$target.remove();
        this._parentToDestroyForTest.destroy();
    },
});


function patch() {
    testUtils.mock.patch(ajax, {
        loadAsset: function (xmlId) {
            if (xmlId === 'template.assets') {
                return Promise.resolve({
                    cssLibs: [],
                    cssContents: ['body {background-color: red;}']
                });
            }
            if (xmlId === 'template.assets_all_style') {
                return Promise.resolve({
                    cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                        return $(this).attr('href');
                    }).get(),
                    cssContents: ['body {background-color: red;}']
                });
            }
            throw 'Wrong template';
        },
    });
}

function unpatch() {
    testUtils.mock.unpatch(ajax);
}

/**
 * @param {object} data
 * @returns {object}
 */
function wysiwygData(data) {
    return _.defaults({}, data, {
        'ir.ui.view': {
            fields: {
                display_name: {
                    string: "Displayed name",
                    type: "char",
                },
            },
            records: [],
            read_template(args) {
                if (args[0] === 'web_editor.colorpicker') {
                    return COLOR_PICKER_TEMPLATE;
                }
            },
            render_template(args) {
                if (args[0] === 'web_editor.snippets') {
                    return SNIPPETS_TEMPLATE;
                }
            },
        },
        'ir.attachment': {
            fields: {
                display_name: {
                    string: "display_name",
                    type: 'char',
                },
                description: {
                    string: "description",
                    type: 'char',
                },
                mimetype: {
                    string: "mimetype",
                    type: 'char',
                },
                checksum: {
                    string: "checksum",
                    type: 'char',
                },
                url: {
                    string: "url",
                    type: 'char',
                },
                type: {
                    string: "type",
                    type: 'char',
                },
                res_id: {
                    string: "res_id",
                    type: 'integer',
                },
                res_model: {
                    string: "res_model",
                    type: 'char',
                },
                public: {
                    string: "public",
                    type: 'boolean',
                },
                access_token: {
                    string: "access_token",
                    type: 'char',
                },
                image_src: {
                    string: "image_src",
                    type: 'char',
                },
                image_width: {
                    string: "image_width",
                    type: 'integer',
                },
                image_height: {
                    string: "image_height",
                    type: 'integer',
                },
                original_id: {
                    string: "original_id",
                    type: 'many2one',
                    relation: 'ir.attachment',
                },
            },
            records: [{
                id: 1,
                name: 'image',
                description: '',
                mimetype: 'image/png',
                checksum: false,
                url: '/web/image/123/transparent.png',
                type: 'url',
                res_id: 0,
                res_model: false,
                public: true,
                access_token: false,
                image_src: '/web/image/123/transparent.png',
                image_width: 256,
                image_height: 256,
            }],
            generate_access_token: function () {
                return;
            },
        },
    });
}

/**
 * Create the wysiwyg instance for test (contains patch, usefull ir.ui.view, snippets).
 *
 * @param {object} params
 */
async function createWysiwyg(params) {
    patch();
    params.data = wysiwygData(params.data);

    var parent = new Widget();
    await testUtils.mock.addMockEnvironment(parent, params);

    var wysiwygOptions = _.extend({}, params.wysiwygOptions, {
        recordInfo: {
            context: {},
            res_model: 'module.test',
            res_id: 1,
        },
        useOnlyTestUnbreakable: params.useOnlyTestUnbreakable,
    });

    var wysiwyg = new WysiwygTest(parent, wysiwygOptions);
    wysiwyg._parentToDestroyForTest = parent;

    var $textarea = $('<textarea/>');
    if (wysiwygOptions.value) {
        $textarea.val(wysiwygOptions.value);
    }
    var selector = params.debug ? 'body' : '#qunit-fixture';
    $textarea.prependTo($(selector));
    if (params.debug) {
        $('body').addClass('debug');
    }
    return wysiwyg.attachTo($textarea).then(function () {
        if (wysiwygOptions.snippets) {
            var defSnippets = testUtils.makeTestPromise();
            testUtils.mock.intercept(wysiwyg, "snippets_loaded", function () {
                defSnippets.resolve(wysiwyg);
            });
            return defSnippets;
        }
        return wysiwyg;
    });
}


/**
 * Char codes.
 */
var dom = $.summernote.dom;
var keyboardMap = {
    "8": "BACKSPACE",
    "9": "TAB",
    "13": "ENTER",
    "16": "SHIFT",
    "17": "CONTROL",
    "18": "ALT",
    "19": "PAUSE",
    "20": "CAPS_LOCK",
    "27": "ESCAPE",
    "32": "SPACE",
    "33": "PAGE_UP",
    "34": "PAGE_DOWN",
    "35": "END",
    "36": "HOME",
    "37": "LEFT",
    "38": "UP",
    "39": "RIGHT",
    "40": "DOWN",
    "45": "INSERT",
    "46": "DELETE",
    "91": "OS_KEY", // 'left command': Windows Key (Windows) or Command Key (Mac)
    "93": "CONTEXT_MENU", // 'right command'
};
_.each(_.range(40, 127), function (keyCode) {
    if (!keyboardMap[keyCode]) {
        keyboardMap[keyCode] = String.fromCharCode(keyCode);
    }
});

/**
 * Perform a series of tests (`keyboardTests`) for using keyboard inputs.
 *
 * @see wysiwyg_keyboard_tests.js
 * @see wysiwyg_tests.js
 *
 * @param {jQuery} $editable
 * @param {object} assert
 * @param {object[]} keyboardTests
 * @param {string} keyboardTests.name
 * @param {string} keyboardTests.content
 * @param {object[]} keyboardTests.steps
 * @param {string} keyboardTests.steps.start
 * @param {string} [keyboardTests.steps.end] default: steps.start
 * @param {string} keyboardTests.steps.key
 * @param {object} keyboardTests.test
 * @param {string} [keyboardTests.test.content]
 * @param {string} [keyboardTests.test.start]
 * @param {string} [keyboardTests.test.end] default: steps.start
 * @param {function($editable, assert)} [keyboardTests.test.check]
 * @param {Number} addTests
 */
var testKeyboard = function ($editable, assert, keyboardTests, addTests) {
    var tests = _.compact(_.pluck(keyboardTests, 'test'));
    var testNumber = _.compact(_.pluck(tests, 'start')).length +
        _.compact(_.pluck(tests, 'content')).length +
        _.compact(_.pluck(tests, 'check')).length +
        (addTests | 0);
    assert.expect(testNumber);

    function keydown(target, keypress) {
        var $target = $(target.tagName ? target : target.parentNode);
        if (!keypress.keyCode) {
            keypress.keyCode = +_.findKey(keyboardMap, function (key) {
                return key === keypress.key;
            });
        } else {
            keypress.key = keyboardMap[keypress.keyCode] || String.fromCharCode(keypress.keyCode);
        }
        keypress.keyCode = keypress.keyCode;
        var event = $.Event("keydown", keypress);
        $target.trigger(event);

        if (!event.isDefaultPrevented()) {
            if (keypress.key.length === 1) {
                textInput($target[0], keypress.key);
            } else {
                console.warn('Native "' + keypress.key + '" is not supported in test');
            }
        }
        $target.trigger($.Event("keyup", keypress));
        return $target;
    }

    function _select(selector) {
        // eg: ".class:contents()[0]->1" selects the first contents of the 'class' class, with an offset of 1
        var reDOMSelection = /^(.+?)(:contents(\(\)\[|\()([0-9]+)[\]|\)])?(->([0-9]+))?$/;
        var sel = selector.match(reDOMSelection);
        var $node = $editable.find(sel[1]);
        var point = {
            node: sel[3] ? $node.contents()[+sel[4]] : $node[0],
            offset: sel[5] ? +sel[6] : 0,
        };
        if (!point.node || point.offset > (point.node.tagName ? point.node.childNodes : point.node.textContent).length) {
            assert.notOk("Node not found: '" + selector + "' " + (point.node ? "(container: '" + (point.node.outerHTML || point.node.textContent) + "')" : ""));
        }
        return point;
    }

    function selectText(start, end) {
        start = _select(start);
        var target = start.node;
        $(target.tagName ? target : target.parentNode).trigger("mousedown");
        if (end) {
            end = _select(end);
            Wysiwyg.setRange(start.node, start.offset, end.node, end.offset);
        } else {
            Wysiwyg.setRange(start.node, start.offset);
        }
        target = end ? end.node : start.node;
        $(target.tagName ? target : target.parentNode).trigger('mouseup');
    }

    function endOfAreaBetweenTwoNodes(point) {
        // move the position because some browser make the caret on the end of the previous area after normalize
        if (
            !point.node.tagName &&
            point.offset === point.node.textContent.length &&
            !/\S|\u00A0/.test(point.node.textContent)
        ) {
            point = dom.nextPoint(dom.nextPoint(point));
            while (point.node.tagName && point.node.textContent.length) {
                point = dom.nextPoint(point);
            }
        }
        return point;
    }

    var defPollTest = Promise.resolve();

    function pollTest(test) {
        var def = Promise.resolve();
        $editable.data('wysiwyg').setValue(test.content);

        function poll(step) {
            var def = testUtils.makeTestPromise();
            if (step.start) {
                selectText(step.start, step.end);
                if (!Wysiwyg.getRange($editable[0])) {
                    throw 'Wrong range! \n' +
                        'Test: ' + test.name + '\n' +
                        'Selection: ' + step.start + '" to "' + step.end + '"\n' +
                        'DOM: ' + $editable.html();
                }
            }
            setTimeout(function () {
                if (step.keyCode || step.key) {
                    var target = Wysiwyg.getRange($editable[0]).ec;
                    if (window.location.search.indexOf('notrycatch') !== -1) {
                        keydown(target, {
                            key: step.key,
                            keyCode: step.keyCode,
                            ctrlKey: !!step.ctrlKey,
                            shiftKey: !!step.shiftKey,
                            altKey: !!step.altKey,
                            metaKey: !!step.metaKey,
                        });
                    } else {
                        try {
                            keydown(target, {
                                key: step.key,
                                keyCode: step.keyCode,
                                ctrlKey: !!step.ctrlKey,
                                shiftKey: !!step.shiftKey,
                                altKey: !!step.altKey,
                                metaKey: !!step.metaKey,
                            });
                        } catch (e) {
                            assert.notOk(e.name + '\n\n' + e.stack, test.name);
                        }
                    }
                }
                setTimeout(function () {
                    if (step.keyCode || step.key) {
                        var $target = $(target.tagName ? target : target.parentNode);
                        $target.trigger($.Event('keyup', {
                            key: step.key,
                            keyCode: step.keyCode,
                            ctrlKey: !!step.ctrlKey,
                            shiftKey: !!step.shiftKey,
                            altKey: !!step.altKey,
                            metaKey: !!step.metaKey,
                        }));
                    }
                    setTimeout(def.resolve.bind(def));
                });
            });
            return def;
        }
        while (test.steps.length) {
            def = def.then(poll.bind(null, test.steps.shift()));
        }

        return def.then(function () {
            if (!test.test) {
                return;
            }

            if (test.test.check) {
                test.test.check($editable, assert);
            }

            // test content
            if (test.test.content) {
                var value = $editable.data('wysiwyg').getValue({
                    keepPopover: true,
                });
                var allInvisible = /\u200B/g;
                value = value.replace(allInvisible, '&#8203;');
                var result = test.test.content.replace(allInvisible, '&#8203;');
                assert.strictEqual(value, result, test.name);

                if (test.test.start && value !== result) {
                    assert.notOk("Wrong DOM (see previous assert)", test.name + " (carret position)");
                    return;
                }
            }

            $editable[0].normalize();

            // test carret position
            if (test.test.start) {
                var start = _select(test.test.start);
                var range = Wysiwyg.getRange($editable[0]);
                if ((range.sc !== range.ec || range.so !== range.eo) && !test.test.end) {
                    assert.ok(false, test.name + ": the carret is not colapsed and the 'end' selector in test is missing");
                    return;
                }
                var end = test.test.end ? _select(test.test.end) : start;
                if (start.node && end.node) {
                    range = Wysiwyg.getRange($editable[0]);
                    var startPoint = endOfAreaBetweenTwoNodes({
                        node: range.sc,
                        offset: range.so,
                    });
                    var endPoint = endOfAreaBetweenTwoNodes({
                        node: range.ec,
                        offset: range.eo,
                    });
                    var sameDOM = (startPoint.node.outerHTML || startPoint.node.textContent) === (start.node.outerHTML || start.node.textContent);
                    var stringify = function (obj) {
                        if (!sameDOM) {
                            delete obj.sameDOMsameNode;
                        }
                        return JSON.stringify(obj, null, 2)
                            .replace(/"([^"\s-]+)":/g, "\$1:")
                            .replace(/([^\\])"/g, "\$1'")
                            .replace(/\\"/g, '"');
                    };
                    assert.deepEqual(stringify({
                            startNode: startPoint.node.outerHTML || startPoint.node.textContent,
                            startOffset: startPoint.offset,
                            endPoint: endPoint.node.outerHTML || endPoint.node.textContent,
                            endOffset: endPoint.offset,
                            sameDOMsameNode: sameDOM && startPoint.node === start.node,
                        }),
                        stringify({
                            startNode: start.node.outerHTML || start.node.textContent,
                            startOffset: start.offset,
                            endPoint: end.node.outerHTML || end.node.textContent,
                            endOffset: end.offset,
                            sameDOMsameNode: true,
                        }),
                        test.name + " (carret position)");
                }
            }
        });
    }
    while (keyboardTests.length) {
        defPollTest = defPollTest.then(pollTest.bind(null, keyboardTests.shift()));
    }

    return defPollTest;
};


/**
 * Select a node in the dom with is offset.
 *
 * @param {String} startSelector
 * @param {String} endSelector
 * @param {jQuery} $editable
 * @returns {Object} {sc, so, ec, eo}
 */
var select = (function () {
    var __select = function (selector, $editable) {
        var sel = selector.match(/^(.+?)(:contents\(\)\[([0-9]+)\]|:contents\(([0-9]+)\))?(->([0-9]+))?$/);
        var $node = $editable.find(sel[1]);
        return {
            node: sel[2] ? $node.contents()[sel[3] ? +sel[3] : +sel[4]] : $node[0],
            offset: sel[5] ? +sel[6] : 0,
        };
    };
    return function (startSelector, endSelector, $editable) {
        var start = __select(startSelector, $editable);
        var end = endSelector ? __select(endSelector, $editable) : start;
        return {
            sc: start.node,
            so: start.offset,
            ec: end.node,
            eo: end.offset,
        };
    };
})();

/**
 * Trigger a keydown event.
 *
 * @param {String or Number} key (name or code)
 * @param {jQuery} $editable
 * @param {Object} [options]
 * @param {Boolean} [options.firstDeselect] (default: false) true to deselect before pressing
 */
var keydown = function (key, $editable, options) {
    var keyPress = {};
    if (typeof key === 'string') {
        keyPress.key = key;
        keyPress.keyCode = +_.findKey(keyboardMap, function (k) {
            return k === key;
        });
    } else {
        keyPress.key = keyboardMap[key] || String.fromCharCode(key);
        keyPress.keyCode = key;
    }
    var range = Wysiwyg.getRange($editable[0]);
    if (!range) {
        console.error("Editor have not any range");
        return;
    }
    if (options && options.firstDeselect) {
        range.sc = range.ec;
        range.so = range.eo;
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
    }
    var target = range.ec;
    var $target = $(target.tagName ? target : target.parentNode);
    var event = $.Event("keydown", keyPress);
    $target.trigger(event);

    if (!event.isDefaultPrevented()) {
        if (keyPress.key.length === 1) {
            textInput($target[0], keyPress.key);
        } else {
            console.warn('Native "' + keyPress.key + '" is not supported in test');
        }
    }
};

var textInput = function (target, char) {
    var ev = new CustomEvent('textInput', {
        bubbles: true,
        cancelBubble: false,
        cancelable: true,
        composed: true,
        data: char,
        defaultPrevented: false,
        detail: 0,
        eventPhase: 3,
        isTrusted: true,
        returnValue: true,
        sourceCapabilities: null,
        type: "textInput",
        which: 0,
    });
    ev.data = char;
    target.dispatchEvent(ev);

    if (!ev.defaultPrevented) {
        document.execCommand("insertText", 0, ev.data);
    }
};

return {
    wysiwygData: wysiwygData,
    createWysiwyg: createWysiwyg,
    testKeyboard: testKeyboard,
    select: select,
    keydown: keydown,
    patch: patch,
    unpatch: unpatch,
};


});
