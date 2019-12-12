odoo.define('web.test_utils', async function (require) {
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
    var relationalFields = require('web.relational_fields');
    var session = require('web.session');
    var testUtilsAsync = require('web.test_utils_async');
    const testUtilsActionManager = require('web.test_utils_action_manager');
    const testUtilsControlPanel = require('web.test_utils_control_panel');
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
        const msg = `Helper 'testUtils.${fn.name}' is deprecated. ` +
            `Please use 'testUtils.${type}.${fn.name}' instead.`;
        return tools.deprecated(fn, msg);
    }

    // Loading static files cannot be properly simulated when their real content is
    // really needed. This is the case for static XML files so we load them here,
    // before starting the qunit test suite.
    // (session.js is in charge of loading the static xml bundle and we also have
    // to load xml files that are normally lazy loaded by specific widgets).
    await Promise.all([
        session.is_bound,
        ajax.loadXML('/web/static/src/xml/debug.xml', core.qweb),
        ajax.loadXML('/web/static/src/xml/dialog.xml', core.qweb),
        ajax.loadXML('/web/static/src/xml/translation_dialog.xml', core.qweb),
    ]);
    setTimeout(function () {
        // jquery autocomplete refines the search in a setTimeout() parameterized
        // with a delay, so we force this delay to 0 s.t. the dropdown is filtered
        // directly on the next tick
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        // this is done with the hope that tests are
        // only started all together...
        QUnit.start();
    }, 0);
    return {
        actionManager: {
            doAction: testUtilsActionManager.doAction,
            loadState: testUtilsActionManager.loadState,
        },
        mock: {
            addMockEnvironment: testUtilsMock.addMockEnvironment,
            setMockedOwlEnv: testUtilsMock.setMockedOwlEnv,
            intercept: testUtilsMock.intercept,
            patch: testUtilsMock.patch,
            patchDate: testUtilsMock.patchDate,
            unpatch: testUtilsMock.unpatch,
            fieldsViewGet: testUtilsMock.fieldsViewGet,
            patchSetTimeout: testUtilsMock.patchSetTimeout,
        },
        controlPanel: {
            // Generic interactions
            toggleMenu: testUtilsControlPanel.toggleMenu,
            toggleMenuItem: testUtilsControlPanel.toggleMenuItem,
            toggleMenuItemOption: testUtilsControlPanel.toggleMenuItemOption,
            isItemSelected: testUtilsControlPanel.isItemSelected,
            isOptionSelected: testUtilsControlPanel.isOptionSelected,
            getMenuItemTexts: testUtilsControlPanel.getMenuItemTexts,
            // Button interactions
            getButtons: testUtilsControlPanel.getButtons,
            // FilterMenu interactions
            toggleFilterMenu: testUtilsControlPanel.toggleFilterMenu,
            toggleAddCustomFilter: testUtilsControlPanel.toggleAddCustomFilter,
            applyFilter: testUtilsControlPanel.applyFilter,
            // GroupByMenu interactions
            toggleGroupByMenu: testUtilsControlPanel.toggleGroupByMenu,
            toggleAddCustomGroup: testUtilsControlPanel.toggleAddCustomGroup,
            selectGroup: testUtilsControlPanel.selectGroup,
            applyGroup: testUtilsControlPanel.applyGroup,
            // FavoriteMenu interactions
            toggleFavoriteMenu: testUtilsControlPanel.toggleFavoriteMenu,
            toggleSaveFavorite: testUtilsControlPanel.toggleSaveFavorite,
            editFavoriteName: testUtilsControlPanel.editFavoriteName,
            saveFavorite: testUtilsControlPanel.saveFavorite,
            deleteFavorite: testUtilsControlPanel.deleteFavorite,
            // TimeRangeMenu interactions
            toggleTimeRangeMenu: testUtilsControlPanel.toggleTimeRangeMenu,
            selectField: testUtilsControlPanel.selectField,
            selectRange: testUtilsControlPanel.selectRange,
            selectComparisonRange: testUtilsControlPanel.selectComparisonRange,
            toggleTimeRangeMenuBox: testUtilsControlPanel.toggleTimeRangeMenuBox,
            applyTimeRange: testUtilsControlPanel.applyTimeRange,
            // SearchBar interactions
            getFacetTexts: testUtilsControlPanel.getFacetTexts,
            removeFacet: testUtilsControlPanel.removeFacet,
            editSearch: testUtilsControlPanel.editSearch,
            validateSearch: testUtilsControlPanel.validateSearch,
            // Action menus interactions
            toggleActionMenu: testUtilsControlPanel.toggleActionMenu,
            // Pager interactions
            pagerPrevious: testUtilsControlPanel.pagerPrevious,
            pagerNext: testUtilsControlPanel.pagerNext,
            getPagerValue: testUtilsControlPanel.getPagerValue,
            getPagerSize: testUtilsControlPanel.getPagerSize,
            setPagerValue: testUtilsControlPanel.setPagerValue,
            // View switcher
            switchView: testUtilsControlPanel.switchView,
        },
        dom: {
            triggerKeypressEvent: testUtilsDom.triggerKeypressEvent,
            triggerMouseEvent: testUtilsDom.triggerMouseEvent,
            triggerPositionalMouseEvent: testUtilsDom.triggerPositionalMouseEvent,
            dragAndDrop: testUtilsDom.dragAndDrop,
            getNode: testUtilsDom.getNode,
            openDatepicker: testUtilsDom.openDatepicker,
            click: testUtilsDom.click,
            clickFirst: testUtilsDom.clickFirst,
            clickLast: testUtilsDom.clickLast,
            triggerEvents: testUtilsDom.triggerEvents,
            triggerEvent: testUtilsDom.triggerEvent,
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
            triggerKey: testUtilsFields.triggerKey,
            triggerKeydown: testUtilsFields.triggerKeydown,
            triggerKeyup: testUtilsFields.triggerKeyup,
        },
        file: {
            createFile: testUtilsFile.createFile,
            dragoverFile: testUtilsFile.dragoverFile,
            dropFile: testUtilsFile.dropFile,
            dropFiles: testUtilsFile.dropFiles,
        },

        createAsyncView: testUtilsCreate.createView,
        createCalendarView: testUtilsCreate.createCalendarView,
        createComponent: testUtilsCreate.createComponent,
        createControlPanel: testUtilsCreate.createControlPanel,
        createView: testUtilsCreate.createView,
        createModel: testUtilsCreate.createModel,
        createParent: testUtilsCreate.createParent,
        createWebClient: testUtilsCreate.createWebClient,
        makeTestPromise: testUtilsAsync.makeTestPromise,
        makeTestPromiseWithAssert: testUtilsAsync.makeTestPromiseWithAssert,
        nextMicrotaskTick: testUtilsAsync.nextMicrotaskTick,
        nextTick: testUtilsAsync.nextTick,
        owlCompatibilityExtraNextTick: testUtilsAsync.owlCompatibilityExtraNextTick,
        prepareTarget: testUtilsCreate.prepareTarget,
        returnAfterNextAnimationFrame: testUtilsDom.returnAfterNextAnimationFrame,

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
