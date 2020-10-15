(function (exports) {
    /**
     * The purpose of this test is to click on every installed App and then
     * open each view. On each view, click on each filter.
     */
    "use strict";
    var clientActionCount = 0;
    var viewUpdateCount = 0;
    var testedApps;
    var testedMenus;
    var blackListedMenus = ['base.menu_theme_store', 'base.menu_third_party'];

    function createWebClientHooks() {
        var AbstractController = odoo.__DEBUG__.services['web.AbstractController'];
        var Discuss = odoo.__DEBUG__.services['mail.Discuss'];
        var WebClient = odoo.__DEBUG__.services["web.WebClient"];

        WebClient.include({
            current_action_updated : function (action, controller) {
                this._super(action, controller);
                clientActionCount++;
            },
        });

        AbstractController.include({
            start: function(){
                this.$el.attr('data-view-type', this.viewType);
                return this._super.apply(this, arguments);
            },
            update: function(params, options) {
                return this._super(params, options).then(function (){
                    viewUpdateCount++;
                });
            },
        });

        if (Discuss) {
            Discuss.include({
                _fetchAndRenderThread: function() {
                    return this._super.apply(this, arguments).then(function (){
                        viewUpdateCount++;
                    });
                },
            });
        }
    }

    function clickEverywhere(menu_id){
        setTimeout(_clickEverywhere, 1000, menu_id);
    }

    // Main function that starts orchestration of tests
    function _clickEverywhere(menu_id){
        console.log("Starting ClickEverywhere test");
        var startTime = performance.now();
        createWebClientHooks();
        testedApps = [];
        testedMenus = [];
        var isEnterprise = odoo.session_info.server_version_info[5] === 'e';
        // finding applications menus
        var $listOfAppMenuItems;
        if (isEnterprise) {
            console.log("Odoo flavor: Enterprise");
            if (menu_id !== undefined) {
                $listOfAppMenuItems = $('a.o_app.o_menuitem[data-menu=' + menu_id + ']');
            } else {
                $listOfAppMenuItems = $('a.o_app.o_menuitem');
            }
        } else {
            console.log("Odoo flavor: Community");
            if (menu_id !== undefined) {
                $listOfAppMenuItems = $('a.o_app[data-menu-id=' + menu_id + ']');
            } else {
                $listOfAppMenuItems = $('a.o_app');
            }
        }
        console.log('Found ', $listOfAppMenuItems.length, 'apps to test');

        var testPromise = Promise.resolve();
        testPromise = chainDeferred($listOfAppMenuItems, testPromise, testApp);
        return testPromise.then(function () {
            console.log("Test took ", (performance.now() - startTime) / 1000, " seconds");
            console.log("Successfully tested ", testedApps.length, " apps");
            console.log("Successfully tested ", testedMenus.length - testedApps.length, " menus");
            console.log("test successful");
        }).catch(function (error) {
            console.log("Test took ", (performance.now() - startTime) / 1000, " seconds");
            console.error(error || 'test failed');
        });
    }


    /**
     * Test an "App" menu item by orchestrating the following actions:
     *  1 - clicking on its menuItem
     *  2 - clicking on each view
     *  3 - clicking on each menu
     *  3.1  - clicking on each view
     * @param {DomElement} element: the App menu item
     * @returns {Promise}
     */
    function testApp(element){
        console.log("Testing app menu:", element.dataset.menuXmlid);
        if (testedApps.indexOf(element.dataset.menuXmlid) >= 0) return Promise.resolve(); // Another infinite loop protection
        testedApps.push(element.dataset.menuXmlid);
        return testMenuItem(element).then(function () {
            var $subMenuItems;
            $subMenuItems = $('.o_menu_entry_lvl_1, .o_menu_entry_lvl_2, .o_menu_entry_lvl_3, .o_menu_entry_lvl_4');
            var testMenuPromise = Promise.resolve();
            testMenuPromise = chainDeferred($subMenuItems, testMenuPromise, testMenuItem);
            return testMenuPromise;
        }).then(function(){
                // no effect in community
                var $homeMenu = $("nav.o_main_navbar > a.o_menu_toggle.fa-th");
                _click($homeMenu);
                return new Promise(function(resolve){
                    setTimeout(function(){
                      resolve();
                    }, 0);
                });
        });
    }


    /**
     * Test a menu item by:
     *  1 - clikcing on the menuItem
     *  2 - Orchestrate the view switch
     *
     *  @param {DomElement} element: the menu item
     *  @returns {Promise}
     */
    function testMenuItem(element){
        if (testedMenus.indexOf(element.dataset.menuXmlid) >= 0) return Promise.resolve(); // Avoid infinite loop
        var menuDescription = element.innerText.trim() + " " + element.dataset.menuXmlid;
        var menuTimeLimit = 10000;
        console.log("Testing menu", menuDescription);
        testedMenus.push(element.dataset.menuXmlid);
        if (blackListedMenus.includes(element.dataset.menuXmlid)) return Promise.resolve(); // Skip black listed menus
        if (element.innerText.trim() == 'Settings') menuTimeLimit = 20000;
        var startActionCount = clientActionCount;
        _click($(element));
        var isModal = false;
        return waitForCondition(function() {
            // sometimes, the app is just a modal that needs to be closed
            var $modal = $('.modal[role="dialog"][open="open"]');
            if ($modal.length > 0) {
                var $closeButton = $('header > button.close');
                if ($closeButton.length > 0) {
                  $closeButton.focus();
                  _click($closeButton);
                } else { $modal.modal('hide'); }
                isModal = true;
                return true;
            }
            return startActionCount != clientActionCount;
        }, menuTimeLimit).then(function() {
            if (!isModal) {
                return testFilters();
            }
        }).then(function () {
            if (!isModal) {
                return testViews();
            }
        }).catch(function () {
            console.error("Error while testing", menuDescription);
            return Promise.reject();
        });
    };


    /**
     * Orchestrate the test of views
     * This function finds the buttons that permit to switch views and orchestrate
     * the click on each of them
     */
    function testViews() {
            var $switches = _.filter($("nav.o_cp_switch_buttons > button:not(.active):visible"), function(switchButton){
                return switchButton.dataset.viewType != 'map';
            });
            var testSwitchPromise = Promise.resolve();
            // chainDeferred($switches, testSwitchPromise, testViewSwitch # FIXME
            _.each($switches, function(switchButton) {
                testSwitchPromise = testSwitchPromise.then(function () {
                    // get the view view-type data attribute
                    return testViewSwitch(switchButton.dataset.viewType);
                });
            });
            return testSwitchPromise;
    }

    /**
     * Test a view button
     * @param {string} viewType: a string for the view type to test (list, kanban ...)
     * @returns {Promise} a promise that wait for the view to be loaded
     */
    function testViewSwitch(viewType){
        console.log("Testing view switch: ", viewType);
        // timeout to avoid click debounce
        setTimeout(function() {
            var $element = $("nav.o_cp_switch_buttons > button[data-view-type=" + viewType + "]");
            console.log('Clicking on: ', $element[0].dataset.viewType,  ' view switcher');
            _click($element);
        },250);
        var waitViewSwitch = waitForCondition(function(){
            return $('.o_action_manager> .o_action.o_view_controller').data('view-type') === viewType;
        });
        return waitViewSwitch.then(function() {
            return testFilters();
        });
    }

    /**
     * Test filters
     * Click on each filter in the control pannel
     */
    function testFilters() {
        var filterProm = Promise.resolve();
        // var $filters = $('div.o_control_panel div.btn-group.o_dropdown > ul.o_filters_menu > li:not(.o_add_custom_filter)');
        var $filters = $('.o_filters_menu > .o_menu_item:not(.d-none)');
        console.log("Testing " + $filters.length + " filters");
        var filter_ids = _.compact(_.map($filters, function(f) { return f.dataset.id}));
        filter_ids.forEach(function(filter_id){
            filterProm = filterProm.then(function(){
                var currentViewCount = viewUpdateCount;
                var $filter = $('.o_menu_item[data-id="' + filter_id + '"] a');
                // with some customized search views, the filter cannot be found
                if ($filter[0] === undefined) {
                    console.warn('Filter with ID ', filter_id , 'cannot be found');
                    return Promise.resolve();
                }
                console.log('Clicking on filter "', $filter.text().trim(), '"');
                _click($filter);
                setTimeout(function() {
                    var $filterOption = $('.o_menu_item .o_item_option[data-item_id="' + filter_id + '"]:not(.selected) a');
                    // In case the filter is a date filter, we need to click on the first filter option (like 'today','This week' ...)
                    if ($filterOption.length > 0) {
                        console.log('Clicking on filter option "', $filterOption[0], '"');
                        _click($filterOption);
                        console.log('And now on filter again');
                        $filter = $('.o_menu_item[data-id="' + filter_id + '"] a');
                        _click($filter); // To avoid that the next view fold the options
                    }
                }, 250);
                return waitForCondition(function() {
                    return currentViewCount !== viewUpdateCount;
                });
            });
        });
        return filterProm;
    }

    // utility functions
    /**
     * Wait a certain amount of time for a condition to occur
     * @param {function} stopCondition a function that returns a boolean
     * @returns {Promise} that is rejected if the timeout is exceeded
     */
    function waitForCondition(stopCondition, tl=10000) {
        var prom = new Promise(function (resolve, reject) {
            var interval = 250;
            var timeLimit = tl;

            function checkCondition() {
                if (stopCondition()) {
                    resolve();
                } else {
                    timeLimit -= interval;
                    if (timeLimit > 0) {
                        // recursive call until the resolve or the timeout
                        setTimeout(checkCondition, interval);
                    } else {
                        console.error('Timeout, the clicked element took more than', tl/1000,'seconds to load');
                        reject();
                    }
                }
            }
            setTimeout(checkCondition, interval);
        });
        return prom;
    }


    /**
     * Chain deferred actions.
     *
     * @param {jQueryElement} $elements a list of jquery elements to be passed as arg to the function
     * @param {Promise} promise the promise on which other promises will be chained
     * @param {function} f the function to be deferred
     * @returns {Promise} the chained promise
     */
    function chainDeferred($elements, promise, f) {
        _.each($elements, function(el) {
            promise = promise.then(function () {
                return f(el);
            });
        });
        return promise;
    }


    /*
     * More realistic click action.
     * @param {jQueryElement} $element the element on which to perform the click
     */
    function _click($element) {
        if ($element.length == 0) return;
        triggerMouseEvent($element, "mouseover");
        triggerMouseEvent($element, "mouseenter");
        triggerMouseEvent($element, "mousedown");
        triggerMouseEvent($element, "mouseup");
        triggerMouseEvent($element, "click");

        function triggerMouseEvent($el, type, count) {
            var e = document.createEvent("MouseEvents");
            e.initMouseEvent(type, true, true, window, count || 0, 0, 0, 0, 0, false, false, false, false, 0, $el[0]);
            $el[0].dispatchEvent(e);
        }
    }

    exports.clickEverywhere = clickEverywhere;
})(window);
