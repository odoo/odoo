odoo.define('web.test_utils', function (require) {
"use strict";

/**
 * Test Utils
 *
 * In this module, we define various utility functions to help simulate a mock
 * environment as close as possible as a real environment.  The main function is
 * certainly createView, which takes a bunch of parameters and give you back an
 * instance of a view, appended in the dom, ready to be tested.
 */

var ajax = require('web.ajax');
var core = require('web.core');
var session = require('web.session');
var testUtilsCreate = require('web.test_utils_create');
var testUtilsDom = require('web.test_utils_dom');
var testUtilsFields = require('web.test_utils_fields');
var testUtilsFile = require('web.test_utils_file');
var testUtilsForm = require('web.test_utils_form');
var testUtilsGraph = require('web.test_utils_graph');
var testUtilsKanban = require('web.test_utils_kanban');
var testUtilsMock = require('web.test_utils_mock');
var testUtilsModal = require('web.test_utils_modal');
var testUtilsPivot = require('web.test_utils_pivot');
var tools = require('web.tools');

function deprecated(fn, type) {
    var msg = `Helper 'testUtils.${fn.name}' is deprecated. ` +
        `Please use 'testUtils.${type}.${fn.name}' instead.`;
    return tools.deprecated(fn, msg);
}

// Loading static files cannot be properly simulated when their real content is
// really needed. This is the case for static XML files so we load them here,
// before starting the qunit test suite.
// (session.js is in charge of loading the static xml bundle and we also have
// to load xml files that are normally lazy loaded by specific widgets).
return $.when(
    session.is_bound,
    ajax.loadXML('/web/static/src/xml/dialog.xml', core.qweb)
).then(function () {
    setTimeout(function () {
        // this is done with the hope that tests are
        // only started all together...
        QUnit.start();
    }, 0);
    return {
        mock: {
            addMockEnvironment: testUtilsMock.addMockEnvironment,
            intercept: testUtilsMock.intercept,
            patch: testUtilsMock.patch,
            patchDate: testUtilsMock.patchDate,
            unpatch: testUtilsMock.unpatch,
            fieldsViewGet: testUtilsMock.fieldsViewGet,
        },
        dom: {
            triggerKeypressEvent: testUtilsDom.triggerKeypressEvent,
            triggerMouseEvent: testUtilsDom.triggerMouseEvent,
            triggerPositionalMouseEvent: testUtilsDom.triggerPositionalMouseEvent,
            dragAndDrop: testUtilsDom.dragAndDrop,
            openDatepicker: testUtilsDom.openDatepicker,
            click: testUtilsDom.click,
            clickFirst: testUtilsDom.clickFirst,
            clickLast: testUtilsDom.clickLast,
        },
        form: {
            clickEdit: testUtilsForm.clickEdit,
            clickSave: testUtilsForm.clickSave,
            clickCreate: testUtilsForm.clickCreate,
            clickDiscard: testUtilsForm.clickDiscard,
            reload: testUtilsForm.reload,
        },
        graph: {
            reload: testUtilsGraph.reload,
        },
        kanban: {
            reload: testUtilsKanban.reload,
            clickCreate: testUtilsKanban.clickCreate,
            quickCreate: testUtilsKanban.quickCreate,
            toggleGroupSettings: testUtilsKanban.toggleGroupSettings,
            toggleRecordDropdown: testUtilsKanban.toggleRecordDropdown,
        },
        modal: {
            clickButton: testUtilsModal.clickButton,
        },
        pivot: {
            clickMeasure: testUtilsPivot.clickMeasure,
            toggleMeasuresDropdown: testUtilsPivot.toggleMeasuresDropdown,
            reload: testUtilsPivot.reload,
        },
        fields: {
            many2one: {
                clickOpenDropdown: testUtilsFields.clickOpenM2ODropdown,
                clickHighlightedItem: testUtilsFields.clickM2OHighlightedItem,
				clickItem: testUtilsFields.clickM2OItem,
                searchAndClickItem: testUtilsFields.searchAndClickM2OItem,
            },
            editInput: testUtilsFields.editInput,
            editSelect: testUtilsFields.editSelect,
            editAndTrigger: testUtilsFields.editAndTrigger,
        },
        file: {
            createFile: testUtilsFile.createFile,
            dragoverFile: testUtilsFile.dragoverFile,
            dropFile: testUtilsFile.dropFile,
        },

        createActionManager: testUtilsCreate.createActionManager,
        createDebugManager: testUtilsCreate.createDebugManager,
        createAsyncView: testUtilsCreate.createAsyncView,
        createControlPanel: testUtilsCreate.createControlPanel,
        createView: testUtilsCreate.createView,
        createModel: testUtilsCreate.createModel,
        createParent: testUtilsCreate.createParent,

        // backward-compatibility
        addMockEnvironment: deprecated(testUtilsMock.addMockEnvironment, 'mock'),
        dragAndDrop: deprecated(testUtilsDom.dragAndDrop, 'dom'),
        fieldsViewGet: deprecated(testUtilsMock.fieldsViewGet, 'mock'),
        intercept: deprecated(testUtilsMock.intercept, 'mock'),
        openDatepicker: deprecated(testUtilsDom.openDatepicker, 'dom'),
        patch: deprecated(testUtilsMock.patch, 'mock'),
        patchDate: deprecated(testUtilsMock.patchDate, 'mock'),
        triggerKeypressEvent: deprecated(testUtilsDom.triggerKeypressEvent, 'dom'),
        triggerMouseEvent: deprecated(testUtilsDom.triggerMouseEvent, 'dom'),
        triggerPositionalMouseEvent: deprecated(testUtilsDom.triggerPositionalMouseEvent, 'dom'),
        unpatch: deprecated(testUtilsMock.unpatch, 'mock'),
    };
});

});
