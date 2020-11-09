odoo.define('web_editor.test_utils', function (require) {
"use strict";

var ajax = require('web.ajax');
var MockServer = require('web.MockServer');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var Wysiwyg = require('web_editor.wysiwyg');
var snippetOptions = require('web_editor.snippets.options');

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
snippetOptions.registry.option_test = snippetOptions.SnippetOptionWidget.extend({
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
 */
async function createWysiwyg() {
    patch();
    var params = {data: wysiwygData({})};

    var parent = new Widget();
    await testUtils.mock.addMockEnvironment(parent, params);

    var wysiwygOptions = _.extend(this._getWysiwygOptions(), await this._getWysiwygOptions(), {
        recordInfo: {
            context: {},
            res_model: 'module.test',
            res_id: 1,
        },
        useOnlyTestUnbreakable: params.useOnlyTestUnbreakable,
    });
    this.wysiwyg = new WysiwygTest(this, wysiwygOptions);
    this.wysiwyg._parentToDestroyForTest = this;

    var self = this
    return this.wysiwyg.attachTo(this).then(function () {
        self._appendTranslateButton();
        if (wysiwygOptions.snippets) {
            var defSnippets = testUtils.makeTestPromise();
            testUtils.mock.intercept(self.wysiwyg, "snippets_loaded", function () {
                defSnippets.resolve(self.wysiwyg);
            });
            return defSnippets;
        }
        return self.wysiwyg;
    });
}


/**
 * Char codes.
 */
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
    select: select,
    keydown: keydown,
    patch: patch,
    unpatch: unpatch,
};


});
