odoo.define('web.test_utils_create', function (require) {
    "use strict";

    /**
     * Create Test Utils
     *
     * This module defines various utility functions to help creating mock widgets
     *
     * Note that all methods defined in this module are exported in the main
     * testUtils file.
     */

    const ActionManager = require('web.ActionManager');
    const concurrency = require('web.concurrency');
    const config = require('web.config');
    const ControlPanelView = require('web.ControlPanelView');
    const DebugManager = require('web.DebugManager.Backend');
    const dom = require('web.dom');
    const testUtilsMock = require('web.test_utils_mock');
    const Widget = require('web.Widget');

    /**
     * Create and return an instance of ActionManager with all rpcs going through a
     * mock method using the data, actions and archs objects as sources.
     *
     * @param {Object} [params={}]
     * @param {Object} [params.actions] the actions given to the mock server
     * @param {Object} [params.archs] this archs given to the mock server
     * @param {Object} [params.data] the business data given to the mock server
     * @param {function} [params.mockRPC]
     * @returns {Promise<ActionManager>}
     */
    async function createActionManager(params = {}) {
        const target = prepareTarget(params.debug);

        const widget = new Widget();
        // when 'document' addon is installed, the sidebar does a 'search_read' on
        // model 'ir_attachment' each time a record is open, so we monkey-patch
        // 'mockRPC' to mute those RPCs, so that the tests can be written uniformly,
        // whether or not 'document' is installed
        const mockRPC = params.mockRPC;
        Object.assign(params, {
            async mockRPC(route, args) {
                if (args.model === 'ir.attachment') {
                    return [];
                }
                if (mockRPC) {
                    return mockRPC.apply(this, arguments);
                }
                return this._super(...arguments);
            },
        });
        testUtilsMock.addMockEnvironment(widget, Object.assign({ debounce: false }, params));
        await widget.prependTo(target);
        widget.el.classList.add('o_web_client');
        if (config.device.isMobile) {
            widget.el.classList.add('o_touch_device');
        }

        const userContext = params.context && params.context.user_context || {};
        const actionManager = new ActionManager(widget, userContext);

        const originalDestroy = ActionManager.prototype.destroy;
        actionManager.destroy = function () {
            actionManager.destroy = originalDestroy;
            widget.destroy();
        };
        const fragment = document.createDocumentFragment();
        await actionManager.appendTo(fragment);
        dom.append(widget.el, fragment, {
            callbacks: [{ widget: actionManager }],
            in_DOM: true,
        });
        return actionManager;
    }

    /**
     * Similar as createView, but specific for calendar views. Some calendar
     * tests need to trigger positional clicks on the DOM produced by fullcalendar.
     * Those tests must use this helper with option positionalClicks set to true.
     * This will move the rendered calendar to the body (required to do positional
     * clicks), and wait for a setTimeout(0) before returning, because fullcalendar
     * makes the calendar scroll to 6:00 in a setTimeout(0), which might have an
     * impact according to where we want to trigger positional clicks.
     *
     * @param {Object} params @see createView
     * @param {Object} [options]
     * @param {boolean} [options.positionalClicks=false]
     * @returns {Promise<CalendarController>}
     */
    async function createCalendarView(params, options) {
        const calendar = await createView(params);
        if (!options || !options.positionalClicks) {
            return calendar;
        }
        const viewElements = [...document.getElementById('qunit-fixture').children];
        viewElements.forEach(el => document.body.prepend(el));

        const destroy = calendar.destroy;
        calendar.destroy = () => {
            viewElements.forEach(el => el.remove());
            destroy();
        };
        await concurrency.delay(0);
        return calendar;
    }

    /**
     * Create a controlPanel from various parameters.
     *
     * It returns an instance of ControlPanelController
     *
     * @param {Object} [params={}]
     * @param {Object} [params.action={}]
     * @param {Object} [params.context={}]
     * @param {string} [params.domain=[]]
     * @param {integer} [params.fieldDebounce=0] the debounce value to use for the
     *   duration of the test.
     * @param {Object} params.intercepts an object with event names as key, and
     *   callback as value.  Each key,value will be used to intercept the event.
     *   Note that this is particularly useful if you want to intercept events going
     *   up in the init process of the view, because there are no other way to do it
     *   after this method returns
     * @param {string} [params.modelName]
     * @param {string[]} [params.searchMenuTypes = ['filter', 'groupBy', 'favorite']]
     *   determines search menus displayed.
     * @param {string} [params.template] the QWeb template to render
     * @param {Object} [params.viewInfo={arch: '<controlpanel/>', fields: {}}]
         a controlpanel (or search) fieldsview
     * @param {string} [params.viewInfo.arch]
     * @param {boolean} [params.context.no_breadcrumbs=false] if set to true,
     *   breadcrumbs won't be rendered
     * @param {boolean} [params.withBreadcrumbs=true] if set to false,
     *   breadcrumbs won't be rendered
     * @param {boolean} [params.withSearchBar=true] if set to false, no default
     *   search bar will be rendered
     *
     * @returns {Promise<ControlPanel>} resolves with an instance of the ControlPanelController
     */
    async function createControlPanel(params) {
        params = params || {};
        const target = prepareTarget(params.debug);
        // reproduce the DOM environment of a view control panel
        const $webClient = $('<div>').addClass('o_web_client').prependTo(target);
        const $actionManager = $('<div>').addClass('o_action_manager').appendTo($webClient);
        const $action = $('<div>').addClass('o_action').appendTo($actionManager);

        const widget = new Widget();
        // add mock environment: mock server, session, fieldviewget, ...
        const mockServer = testUtilsMock.addMockEnvironment(widget, params);
        if (!params.viewInfo) {
            try {
                params.viewInfo = testUtilsMock.fieldsViewGet(mockServer, params);
            } catch (e) {
                // if an error occurs we keep params.viewInfo undefined.
                // It will be set to {arch: '<controlpanel/>', fields: {}} in
                // ControlPanelView init function.
            }
        }

        const viewOptions = Object.assign({
            context: params.context,
            modelName: params.model,
            searchMenuTypes: params.searchMenuTypes,
            viewInfo: params.viewInfo,
        }, params.viewOptions);
        const controlPanelView = new ControlPanelView(viewOptions);
        const controlPanel = await controlPanelView.getController(widget);
        // override the controlPanel's 'destroy' so that it calls 'destroy' on
        // the widget instead, as the widget is the parent of the controlPanel
        // and the mockServer.
        controlPanel.__destroy = controlPanel.destroy;
        controlPanel.destroy = function () {
            // remove the override to properly destroy the controlPanel and its
            // children when it will be called the second time (by its parent)
            delete controlPanel.destroy;
            widget.destroy();
            $webClient.remove();
        };

        // render the controlPanel in a fragment as it must be able to render
        // correctly without being in the DOM
        const fragment = document.createDocumentFragment();
        await controlPanel.appendTo(fragment);
        dom.prepend($action, fragment, {
            callbacks: [{ widget: controlPanel }],
            in_DOM: true,
        });
        return controlPanel;
    }

    /**
     * Create and return an instance of DebugManager with all rpcs going through a
     * mock method, assuming that the user has access rights, and is an admin.
     *
     * @param {Object} [params={}]
     * @returns {DebugManager}
     */
    function createDebugManager(params = {}) {
        const mockRPC = params.mockRPC;
        Object.assign(params, {
            async mockRPC(route, args) {
                if (args.method === 'check_access_rights') {
                    return true;
                }
                if (args.method === 'xmlid_to_res_id') {
                    return true;
                }
                if (mockRPC) {
                    return mockRPC.apply(this, arguments);
                }
                return this._super(...arguments);
            },
            session: {
                async user_has_group(group) {
                    if (group === 'base.group_no_one') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
        });
        const debugManager = new DebugManager();
        testUtilsMock.addMockEnvironment(debugManager, params);
        return debugManager;
    }

    /**
     * Create a model from given parameters.
     *
     * @param {Object} params This object will be given to addMockEnvironment, so
     *   any parameters from that method applies
     * @param {Class} params.Model the model class to use
     * @returns {Model}
     */
    function createModel(params) {
        const widget = new Widget();

        const model = new params.Model(widget);

        testUtilsMock.addMockEnvironment(widget, params);

        // override the model's 'destroy' so that it calls 'destroy' on the widget
        // instead, as the widget is the parent of the model and the mockServer.
        model.destroy = function () {
            // remove the override to properly destroy the model when it will be
            // called the second time (by its parent)
            delete model.destroy;
            widget.destroy();
        };

        return model;
    }

    /**
     * Create a widget parent from given parameters.
     *
     * @param {Object} params This object will be given to addMockEnvironment, so
     *   any parameters from that method applies
     * @returns {Widget}
     */
    function createParent(params) {
        const widget = new Widget();
        testUtilsMock.addMockEnvironment(widget, params);
        return widget;
    }

    /**
     * Create a view from various parameters.  Here, a view means a javascript
     * instance of an AbstractView class, such as a form view, a list view or a
     * kanban view.
     *
     * It returns the instance of the view, properly created, with all rpcs going
     * through a mock method using the data object as source, and already loaded/
     * started.
     *
     * @param {Object} params
     * @param {string} params.arch the xml (arch) of the view to be instantiated
     * @param {any[]} [params.domain] the initial domain for the view
     * @param {Object} [params.context] the initial context for the view
     * @param {string[]} [params.groupBy] the initial groupBy for the view
     * @param {integer} [params.fieldDebounce=0] the debounce value to use for the
     *   duration of the test.
     * @param {AbstractView} params.View the class that will be instantiated
     * @param {string} params.model a model name, will be given to the view
     * @param {Object} params.intercepts an object with event names as key, and
     *   callback as value.  Each key,value will be used to intercept the event.
     *   Note that this is particularly useful if you want to intercept events going
     *   up in the init process of the view, because there are no other way to do it
     *   after this method returns
     * @param {Boolean} [params.doNotDisableAHref=false] will not preventDefault on the A elements of the view if true.
     *    Default is false.
     * @returns {Promise<AbstractController>} the instance of the view
     */
    async function createView(params) {
        const target = prepareTarget(params.debug);
        const widget = new Widget();
        // reproduce the DOM environment of views
        const webClient = Object.assign(document.createElement('div'), {
            className: 'o_web_client',
        });
        const actionManager = Object.assign(document.createElement('div'), {
            className: 'o_action_manager',
        });
        target.prepend(webClient);
        webClient.append(actionManager);

        // add mock environment: mock server, session, fieldviewget, ...
        const mockServer = testUtilsMock.addMockEnvironment(widget, params);
        const viewInfo = testUtilsMock.fieldsViewGet(mockServer, params);

        // create the view
        const View = params.View;
        const viewOptions = Object.assign({
            modelName: params.model || 'foo',
            ids: 'res_id' in params ? [params.res_id] : undefined,
            currentId: 'res_id' in params ? params.res_id : undefined,
            domain: params.domain || [],
            context: params.context || {},
            hasSidebar: false,
        }, params.viewOptions);
        // patch the View to handle the groupBy given in params, as we can't give it
        // in init (unlike the domain and context which can be set in the action)
        testUtilsMock.patch(View, {
            _updateMVCParams() {
                this._super(...arguments);
                this.loadParams.groupedBy = params.groupBy || viewOptions.groupBy || [];
                testUtilsMock.unpatch(View);
            },
        });
        if ('hasSelectors' in params) {
            viewOptions.hasSelectors = params.hasSelectors;
        }

        let view;
        if (viewInfo.type === 'controlpanel' || viewInfo.type === 'search') {
            // TODO: probably needs to create an helper just for that
            view = new params.View({
                viewInfo: viewInfo,
                modelName: params.model || 'foo',
            });
        } else {
            viewOptions.controlPanelFieldsView = testUtilsMock.fieldsViewGet(mockServer, {
                arch: params.archs && params.archs[params.model + ',false,search'] || '<search/>',
                fields: viewInfo.fields,
                model: params.model,
            });
            view = new params.View(viewInfo, viewOptions);
        }

        if (params.interceptsPropagate) {
            for (const name in params.interceptsPropagate) {
                testUtilsMock.intercept(widget, name, params.interceptsPropagate[name], true);
            }
        }

        const viewController = await view.getController(widget);
        // override the view's 'destroy' so that it calls 'destroy' on the widget
        // instead, as the widget is the parent of the view and the mockServer.
        viewController.__destroy = viewController.destroy;
        viewController.destroy = function () {
            // remove the override to properly destroy the viewController and its children
            // when it will be called the second time (by its parent)
            delete viewController.destroy;
            widget.destroy();
            webClient.remove();
        };

        // render the viewController in a fragment as they must be able to render correctly
        // without being in the DOM
        const fragment = document.createDocumentFragment();
        await viewController.appendTo(fragment);
        dom.prepend(actionManager, fragment, {
            callbacks: [{ widget: viewController }],
            in_DOM: true,
        });

        if (!params.doNotDisableAHref) {
            [...viewController.el.getElementsByTagName('A')].forEach(elem => {
                elem.addEventListener('click', ev => {
                    ev.preventDefault();
                });
            });
        }
        return viewController;
    }

    /**
     * Get the target (fixture or body) of the document and adds event listeners
     * to intercept custom or DOM events.
     *
     * @param {boolean} [debug=false] if true, the widget will be appended in
     *      the DOM. Also, RPCs and uncaught OdooEvent will be logged
     * @returns {HTMLElement}
     */
    function prepareTarget(debug = false) {
        document.body.classList.toggle('debug', debug);
        return debug ? document.body : document.getElementById('qunit-fixture');
    }

    return {
        createActionManager,
        createCalendarView,
        createControlPanel,
        createDebugManager,
        createModel,
        createParent,
        createView,
        prepareTarget,
    };
});
