/** @odoo-module alias=web.test_utils **/

    /**
     * Test Utils
     *
     * In this module, we define various utility functions to help simulate a mock
     * environment as close as possible as a real environment.  The main function is
     * certainly createView, which takes a bunch of parameters and give you back an
     * instance of a view, appended in the dom, ready to be tested.
     */

    import testUtilsCreate from "web.test_utils_create";
    import testUtilsControlPanel from "web.test_utils_control_panel";
    import testUtilsDom from "web.test_utils_dom";
    import testUtilsFields from "web.test_utils_fields";
    import testUtilsFile from "web.test_utils_file";
    import testUtilsForm from "web.test_utils_form";
    import testUtilsGraph from "web.test_utils_graph";
    import testUtilsKanban from "web.test_utils_kanban";
    import testUtilsMock from "web.test_utils_mock";
    import testUtilsModal from "web.test_utils_modal";
    import testUtilsPivot from "web.test_utils_pivot";
    import tools from "web.tools";


    function deprecated(fn, type) {
        const msg = `Helper 'testUtils.${fn.name}' is deprecated. ` +
            `Please use 'testUtils.${type}.${fn.name}' instead.`;
        return tools.deprecated(fn, msg);
    }

    /**
     * Helper function, make a promise with a public resolve function. Note that
     * this is not standard and should not be used outside of tests...
     *
     * @returns {Promise + resolve and reject function}
     */
    function makeTestPromise() {
        let resolve;
        let reject;
        const promise = new Promise(function (_resolve, _reject) {
            resolve = _resolve;
            reject = _reject;
        });
        promise.resolve = function () {
            resolve.apply(null, arguments);
            return promise;
        };
        promise.reject = function () {
            reject.apply(null, arguments);
            return promise;
        };
        return promise;
    }

    /**
     * Make a promise with public resolve and reject functions (see
     * @makeTestPromise). Perform an assert.step when the promise is
     * resolved/rejected.
     *
     * @param {Object} assert instance object with the assertion methods
     * @param {function} assert.step
     * @param {string} str message to pass to assert.step
     * @returns {Promise + resolve and reject function}
     */
    function makeTestPromiseWithAssert(assert, str) {
        const prom = makeTestPromise();
        prom.then(() => assert.step('ok ' + str)).catch(function () { });
        prom.catch(() => assert.step('ko ' + str));
        return prom;
    }

    /**
     * Create a new promise that can be waited by the caller in order to execute
     * code after the next microtask tick and before the next jobqueue tick.
     *
     * @return {Promise} an already fulfilled promise
     */
    async function nextMicrotaskTick() {
        return Promise.resolve();
    }

    /**
     * Returns a promise that will be resolved after the tick after the
     * nextAnimationFrame
     *
     * This is usefull to guarantee that OWL has had the time to render
     *
     * @returns {Promise}
     */
    async function nextTick() {
        return testUtilsDom.returnAfterNextAnimationFrame();
    }

    /**
     * Awaits for an additionnal rendering frame initiated by the Owl
     * compatibility layer processing.
     *
     * By default a simple "nextTick" will handle the rendering of any widget/
     * component stuctures having at most 1 switch between the type of
     * entities (Component > Widget or Widget > Component). However more time
     * must be spent rendering in case we have additionnal switches. In such
     * cases this function must be used (1 call for each additionnal switch)
     * since it will be removed along with the compatiblity layer once the
     * framework has been entirely converted, and using this helper will make
     * it easier to wipe it from the code base.
     *
     * @returns {Promise}
     */
    async function owlCompatibilityExtraNextTick() {
        return testUtilsDom.returnAfterNextAnimationFrame();
    }

    export default {
        mock: {
            addMockEnvironment: testUtilsMock.addMockEnvironment,
            addMockEnvironmentOwl: testUtilsMock.addMockEnvironmentOwl,
            intercept: testUtilsMock.intercept,
            patch: testUtilsMock.patch,
            patchDate: testUtilsMock.patchDate,
            unpatch: testUtilsMock.unpatch,
            getView: testUtilsMock.getView,
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
            addCondition: testUtilsControlPanel.addCondition,
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
            // ComparisonMenu interactions
            toggleComparisonMenu: testUtilsControlPanel.toggleComparisonMenu,
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
            triggerPositionalTapEvents: testUtilsDom.triggerPositionalTapEvents,
            dragAndDrop: testUtilsDom.dragAndDrop,
            find: testUtilsDom.findItem,
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
                createAndEdit: testUtilsFields.clickM2OCreateAndEdit,
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
            inputFiles: testUtilsFile.inputFiles,
        },

        createComponent: testUtilsCreate.createComponent,
        createAsyncView: testUtilsCreate.createView,
        createCalendarView: testUtilsCreate.createCalendarView,
        createView: testUtilsCreate.createView,
        createModel: testUtilsCreate.createModel,
        createParent: testUtilsCreate.createParent,
        makeTestPromise: makeTestPromise,
        makeTestPromiseWithAssert: makeTestPromiseWithAssert,
        nextMicrotaskTick: nextMicrotaskTick,
        nextTick: nextTick,
        owlCompatibilityExtraNextTick,
        prepareTarget: testUtilsCreate.prepareTarget,
        returnAfterNextAnimationFrame: testUtilsDom.returnAfterNextAnimationFrame,

        // backward-compatibility
        addMockEnvironment: deprecated(testUtilsMock.addMockEnvironment, 'mock'),
        dragAndDrop: deprecated(testUtilsDom.dragAndDrop, 'dom'),
        getView: deprecated(testUtilsMock.getView, 'mock'),
        intercept: deprecated(testUtilsMock.intercept, 'mock'),
        openDatepicker: deprecated(testUtilsDom.openDatepicker, 'dom'),
        patch: deprecated(testUtilsMock.patch, 'mock'),
        patchDate: deprecated(testUtilsMock.patchDate, 'mock'),
        triggerKeypressEvent: deprecated(testUtilsDom.triggerKeypressEvent, 'dom'),
        triggerMouseEvent: deprecated(testUtilsDom.triggerMouseEvent, 'dom'),
        triggerPositionalMouseEvent: deprecated(testUtilsDom.triggerPositionalMouseEvent, 'dom'),
        unpatch: deprecated(testUtilsMock.unpatch, 'mock'),
    };
