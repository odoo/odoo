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
                return this._super();
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
                    return this._super().then(function (){
                        viewUpdateCount++;
                    });
                },
            });
        }
    }

    function clickEverywhere(){
        setTimeout(_clickEverywhere, 1000);
    }

    // Main function that starts orchestration of tests
    function _clickEverywhere(){
        console.log("Starting ClickEverywhere test");
        var startTime = performance.now()
        createWebClientHooks();
        testedApps = [];
        testedMenus = [];
        var isEnterprise = odoo.session_info.server_version_info[5] === 'e';
        // finding applications menus
        var $listOfAppMenuItems;
        if (isEnterprise) {
            console.log("Odoo flavor: Enterprise")
            var $homeMenu = $("nav.o_main_navbar > a.o_menu_toggle.fa-th");
            $homeMenu.click()
            $listOfAppMenuItems = $(".o_app, .o_menuitem")
        } else {
            console.log("Odoo flavor: Community")
            $listOfAppMenuItems = $('a.o_app');
        }
        console.log('Found ', $listOfAppMenuItems.length, 'apps to test');

        var testDef = $.when();
        testDef = chainDeferred($listOfAppMenuItems, testDef, testApp);
        return testDef.then(function() {
            console.log("Successfully tested ", testedApps.length, " apps");
            console.log("Successfully tested ", testedMenus.length - testedApps.length, " menus");
            console.log("ok");
        }).always(function() {
            console.log("Test took ", (performance.now() - startTime)/1000, " seconds");
        }).fail(function () { 
            console.error("Error !")
        });
    } 


    /**
     * Test an "App" menu item by orchestrating the following actions:
     *  1 - clicking on its menuItem
     *  2 - clicking on each view
     *  3 - clicking on each menu
     *  3.1  - clicking on each view
     * @param {DomElement} element: the App menu item
     * @returns {Deferred}
     */
    function testApp(element){
        console.log("Testing app menu:", element.dataset.menuXmlid);
        if (testedApps.indexOf(element.dataset.menuXmlid) >= 0) return $.Deferred().resolve(); // Another infinite loop protection
        testedApps.push(element.dataset.menuXmlid);
        return testMenuItem(element).then(function () {
            var $subMenuItems;
            $subMenuItems = $('.o_menu_entry_lvl_1, .o_menu_entry_lvl_2, .o_menu_entry_lvl_3, .o_menu_entry_lvl_4');
            var testMenuDef = $.when();
            testMenuDef = chainDeferred($subMenuItems, testMenuDef, testMenuItem);
            return testMenuDef;
        }).then(function(){
                // no effect in community
                var $homeMenu = $("nav.o_main_navbar > a.o_menu_toggle.fa-th");
                $homeMenu.click();
        });
    }


    /**
     * Test a menu item by:
     *  1 - clikcing on the menuItem
     *  2 - Orchestrate the view switch
     *
     *  @param {DomElement} element: the menu item
     *  @returns {Deferred}
     */
    function testMenuItem(element){
        if (testedMenus.indexOf(element.dataset.menuXmlid) >= 0) return $.Deferred().resolve(); // Avoid infinite loop
        console.log("Testing menu", element.innerText.trim(), " ", element.dataset.menuXmlid);
        testedMenus.push(element.dataset.menuXmlid);
        var startActionCount = clientActionCount;
        element.click();
        var isModal = false;
        return waitForCondition(function() {
            // sometimes, the app is just a modal that needs to be closed
            var $modal = $('.modal[role="dialog"][open="open"]');
            if ($modal.length > 0) {
                $modal.modal('hide');
                isModal = true;
                return true;
            };
            return startActionCount != clientActionCount;
        }).then(function() {
            if (!isModal) {
                return testFilters();
            }
        }).then(function () {
            if (!isModal) {
                return testViews();
            }
        }).fail(function() {
            console.error("Error while testing", element);
        });
    };


    /**
     * Orchestrate the test of views
     * This function finds the buttons that permit to switch views and orchestrate
     * the click on each of them
     */
    function testViews() {
            var $switches = $("nav.o_cp_switch_buttons > button:not(.active):visible");
            var testSwitchDef = $.when();
            // chainDeferred($switches, testSwitchDef, testViewSwitch # FIXME
            _.each($switches, function(switchButton) {
                testSwitchDef = testSwitchDef.then(function () {
                    // get the view view-type data attribute
                    return testViewSwitch(switchButton.dataset.viewType);
                });
            });
            return testSwitchDef;
    }

    /**
     * Test a view button
     * @param {string} viewType: a string for the view type to test (list, kanban ...)
     * @returns {Deferred} a deferred that wait for the view to be loaded
     */
    function testViewSwitch(viewType){
        console.log("Testing view switch: ", viewType);
        // timeout to avoid click debounce
        setTimeout(function() {
            var $element = $("nav.o_cp_switch_buttons > button[data-view-type=" + viewType + "]");
            console.log('Clicking on: ', $element[0].dataset.viewType,  ' view switcher');
            $element.click();
        },250);
        var waitViewSwitch = waitForCondition(function(){
            return $('.o_content > .o_view_controller').data('view-type') === viewType;
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
        var filterDef = $.when();
        // var $filters = $('div.o_control_panel div.btn-group.o_dropdown > ul.o_filters_menu > li:not(.o_add_custom_filter)');
        var $filters = $('.o_filters_menu > .o_menu_item')
        console.log("Testing " + $filters.length + " filters");
        var filter_ids = _.compact(_.map($filters, function(f) { return f.dataset.id}));
        _.each(filter_ids, function(filter_id){
            filterDef = filterDef.then(function(){
                var currentViewCount = viewUpdateCount;
                var $filter = $('.o_menu_item[data-id="' + filter_id + '"] a');
                // with some customized search views, the filter cannot be found
                if ($filter[0] === undefined) {
                    console.warn('Filter with ID ', filter_id , 'cannot be found');
                    return $.Deferred().resolve();
                };
                console.log('Clicking on filter "', $filter.text().trim(), '"');
                $filter[0].click();
                setTimeout(function() {
                    var $filterOption = $('.o_menu_item .o_item_option[data-item_id="' + filter_id + '"]:not(.selected) a');
                    // In case the filter is a date filter, we need to click on the first filter option (like 'today','This week' ...)
                    if ($filterOption.length > 0) {
                        console.log('Clicking on filter option "', $filterOption[0], '"');
                        $filterOption[0].click();
                        console.log('And now on filter again');
                        $filter = $('.o_menu_item[data-id="' + filter_id + '"] a');
                        $filter[0].click(); // To avoid that the next view fold the options
                    }
                }, 250);
                return waitForCondition(function() {
                    return currentViewCount !== viewUpdateCount;
                });
            });
        });
        return filterDef;
    }

    // utility functions
    /**
     * Wait a certain amount of time for a condition to occur
     * @param stopCondition: a function that returns a boolean
     * @returns {Deferred} that is rejected if the timeout is exceeded
     */
    function waitForCondition(stopCondition) {
        var def = $.Deferred();
        var interval = 250;
        var timeLimit = 15000;
        function checkCondition() {
            if (stopCondition()) {
                def.resolve();
            } else {
                timeLimit -= interval;
                if (timeLimit > 0) {
                    // recursive call until the resolve or the timeout
                    setTimeout(checkCondition, interval);
                } else {
                    console.error("Timeout exceeded", stopCondition);
                    def.reject();
                }
            }
        }
        setTimeout(checkCondition, interval);
        return def;
    };

    
    /**
     * chain deferred actions
     * @param $elements: a list of jquery elements to be passed as arg to the function
     * @param deferred: the deferred on which other deferreds will be chained
     * @param f: the function to be deferred
     * @returns : the chained deferred
     */
    function chainDeferred($elements, deferred, f) {
        _.each($elements, function(el) {
            deferred = deferred.then(function () {
                return f(el);
            });
        });
        return deferred;
    }


    exports.clickEverywhere = clickEverywhere;
})(window);
