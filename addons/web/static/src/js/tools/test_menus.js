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
    var blackListedMenus = ['base.menu_theme_store', 'base.menu_third_party', 'account.menu_action_account_bank_journal_form', 'pos_adyen.menu_pos_adyen_account'];
    var appsMenusOnly = false;
    let isEnterprise = odoo.session_info.server_version_info[5] === 'e';

    function createWebClientHooks() {
        var AbstractController = odoo.__DEBUG__.services['web.AbstractController'];
        var DiscussWidget = odoo.__DEBUG__.services['mail/static/src/widgets/discuss/discuss.js'];
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

        if (DiscussWidget) {
            DiscussWidget.include({
                /**
                 * Overriding a method that is called every time the discuss
                 * component is updated.
                 */
                _updateControlPanel: async function () {
                    await this._super(...arguments);
                    viewUpdateCount++;
                },
            });
        }
    }

    function clickEverywhere(xmlId, light){
        appsMenusOnly = light;
        setTimeout(_clickEverywhere, 1000, xmlId);
    }

    // Main function that starts orchestration of tests
    async function _clickEverywhere(xmlId){
        console.log("Starting ClickEverywhere test");
        var startTime = performance.now();
        createWebClientHooks();
        testedApps = [];
        testedMenus = [];
        // finding applications menus
        let appMenuItems;
        if (isEnterprise) {
            console.log("Odoo flavor: Enterprise");
            appMenuItems = document.querySelectorAll(xmlId ?
                `a.o_app.o_menuitem[data-menu-xmlid="${xmlId}"]` :
                'a.o_app.o_menuitem'
            );
        } else {
            console.log("Odoo flavor: Community");
            appMenuItems = document.querySelectorAll(xmlId ?
                `a.o_app[data-menu-xmlid="${xmlId}"]` :
                'a.o_app'
            );
        }
        console.log("Found", appMenuItems.length, "apps to test");
        try {
            for (const app of appMenuItems) {
                await testApp(app);
            }
            console.log("Test took", (performance.now() - startTime) / 1000, "seconds");
            console.log("Successfully tested", testedApps.length, " apps");
            console.log("Successfully tested", testedMenus.length - testedApps.length, "menus");
            console.log("test successful");
        } catch (err) {
            console.log("Test took", (performance.now() - startTime) / 1000, "seconds");
            console.error(err || "test failed");
        }
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
    async function testApp(element) {
        console.log("Testing app menu:", element.dataset.menuXmlid);
        if (testedApps.indexOf(element.dataset.menuXmlid) >= 0) return; // Another infinite loop protection
        testedApps.push(element.dataset.menuXmlid);
        await testMenuItem(element);
        if (appsMenusOnly === true) return;
        const subMenuItems = document.querySelectorAll('.o_menu_entry_lvl_1, .o_menu_entry_lvl_2, .o_menu_entry_lvl_3, .o_menu_entry_lvl_4');
        for (const subMenuItem of subMenuItems) {
            await testMenuItem(subMenuItem);
        }
        if (isEnterprise) {
            const homeMenu = document.querySelector('nav.o_main_navbar > a.o_menu_toggle.fa-th');
            return triggerClick(homeMenu, "home menu toggle button");
        }
    }


    /**
     * Test a menu item by:
     *  1 - clikcing on the menuItem
     *  2 - Orchestrate the view switch
     *
     *  @param {DomElement} element: the menu item
     *  @returns {Promise}
     */
    async function testMenuItem(element){
        if (testedMenus.indexOf(element.dataset.menuXmlid) >= 0) return Promise.resolve(); // Avoid infinite loop
        var menuDescription = element.innerText.trim() + " " + element.dataset.menuXmlid;
        var menuTimeLimit = 10000;
        console.log("Testing menu", menuDescription);
        testedMenus.push(element.dataset.menuXmlid);
        if (blackListedMenus.includes(element.dataset.menuXmlid)) return Promise.resolve(); // Skip black listed menus
        if (element.innerText.trim() == 'Settings') menuTimeLimit = 20000;
        var startActionCount = clientActionCount;
        await triggerClick(element, `menu item "${element.innerText.trim()}"`);
        var isModal = false;
        return waitForCondition(function () {
            // sometimes, the app is just a modal that needs to be closed
            var $modal = $('.modal[role="dialog"][open="open"]');
            if ($modal.length > 0) {
                const closeButton = document.querySelector('header > button.close');
                if (closeButton) {
                    closeButton.focus();
                    triggerClick(closeButton, "modal close button");
                } else { $modal.modal('hide'); }
                isModal = true;
                return true;
            }
            return startActionCount !== clientActionCount;
        }, menuTimeLimit).then(function() {
            if (!isModal) {
                return testFilters();
            }
        }).then(function () {
            if (!isModal) {
                return testViews();
            }
        }).catch(function (err) {
            console.error("Error while testing", menuDescription);
            return Promise.reject(err);
        });
    };


    /**
     * Orchestrate the test of views
     * This function finds the buttons that permit to switch views and orchestrate
     * the click on each of them
     * @returns {Promise}
     */
    async function testViews() {
        if (appsMenusOnly === true) {
            return;
        }
        const switchButtons = document.querySelectorAll('nav.o_cp_switch_buttons > button.o_switch_view:not(.active):not(.o_map)');
        for (const switchButton of switchButtons) {
            // Only way to get the viewType from the switchButton
            const viewType = [...switchButton.classList]
                .find(cls => cls !== 'o_switch_view' && cls.startsWith('o_'))
                .slice(2);
            console.log("Testing view switch:", viewType);
            // timeout to avoid click debounce
            setTimeout(function () {
                const target = document.querySelector(`nav.o_cp_switch_buttons > button.o_switch_view.o_${viewType}`);
                if (target) {
                    triggerClick(target, `${viewType} view switcher`);
                }
            }, 250);
            await waitForCondition(() => document.querySelector('.o_action_manager > .o_action.o_view_controller').dataset.viewType === viewType);
            await testFilters();
        }
    }

    /**
     * Test filters
     * Click on each filter in the control pannel
     */
    async function testFilters() {
        if (appsMenusOnly === true) {
            return;
        }
        const filterMenuButton = document.querySelector('.o_control_panel .o_filter_menu > button');
        if (!filterMenuButton) {
            return;
        }
        // Open the filter menu dropdown
        await triggerClick(filterMenuButton, `toggling menu "${filterMenuButton.innerText.trim()}"`);

        const filterMenuItems = document.querySelectorAll('.o_control_panel .o_filter_menu > ul > li.o_menu_item');
        console.log("Testing", filterMenuItems.length, "filters");

        for (const filter of filterMenuItems) {
            const currentViewCount = viewUpdateCount;
            const filterLink = filter.querySelector('a');
            await triggerClick(filterLink, `filter "${filter.innerText.trim()}"`);
            if (filterLink.classList.contains('o_menu_item_parent')) {
                // If a fitler has options, it will simply unfold and show all options.
                // We then click on the first one.
                const firstOption = filter.querySelector('.o_menu_item_options > li.o_item_option > a');
                console.log();
                await triggerClick(firstOption, `filter option "${firstOption.innerText.trim()}"`);
            }
            await waitForCondition(() => currentViewCount !== viewUpdateCount);
        }
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

    const MOUSE_EVENTS = [
        'mouseover',
        'mouseenter',
        'mousedown',
        'mouseup',
        'click',
    ];

    /**
     * Simulate all of the mouse events triggered during a click action.
     * @param {EventTarget} target the element on which to perform the click
     * @param {string} elDescription description of the item
     * @returns {Promise} resolved after next animation frame
     */
    async function triggerClick(target, elDescription) {
        if (target) {
            console.log("Clicking on", elDescription);
        } else {
            throw new Error(`No element "${elDescription}" found.`);
        }
        MOUSE_EVENTS.forEach(type => {
            const event = new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
            target.dispatchEvent(event);
        });
        await new Promise(setTimeout);
        await new Promise(r => requestAnimationFrame(r));
    }

    exports.clickEverywhere = clickEverywhere;
})(window);
