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

    const ActionMenus = require('web.ActionMenus');
    const concurrency = require('web.concurrency');
    const ControlPanel = require('web.ControlPanel');
    const { useListener } = require("@web/core/utils/hooks");
    const dom = require('web.dom');
    const makeTestEnvironment = require('web.test_env');
    const ActionModel = require('web.ActionModel');
    const Registry = require('web.Registry');
    const testUtilsMock = require('web.test_utils_mock');
    const Widget = require('web.Widget');
    const { destroy, getFixture, mount, useChild } = require('@web/../tests/helpers/utils');
    const { registerCleanup } = require("@web/../tests/helpers/cleanup");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { Component, onMounted, onWillStart, useState, xml } = owl;

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
        // prepend reset the scrollTop to zero so we restore it manually
        let fcScroller = document.querySelector('.fc-scroller');
        const scrollPosition = fcScroller.scrollTop;
        viewElements.forEach(el => document.body.prepend(el));
        fcScroller = document.querySelector('.fc-scroller');
        fcScroller.scrollTop = scrollPosition;

        const destroy = calendar.destroy;
        calendar.destroy = () => {
            viewElements.forEach(el => el.remove());
            destroy();
        };
        await concurrency.delay(0);
        return calendar;
    }

    /**
     * Create a simple component environment with a basic Parent component, an
     * extensible env and a mocked server. The returned value is the instance of
     * the given constructor.
     * @param {class} constructor Component class to instantiate
     * @param {Object} [params = {}]
     * @param {boolean} [params.debug]
     * @param {Object} [params.env]
     * @param {Object} [params.intercepts] object in which the keys represent the
     *      intercepted event names and the values are their callbacks.
     * @param {Object} [params.props]
     * @returns {Promise<Component>} instance of `constructor`
     */
    async function createComponent(constructor, params = {}) {
        if (!constructor) {
            throw new Error(`Missing argument "constructor".`);
        }
        if (!(constructor.prototype instanceof Component)) {
            throw new Error(`Argument "constructor" must be an Owl Component.`);
        }
        const cleanUp = await testUtilsMock.addMockEnvironmentOwl(Component, params);
        class Parent extends LegacyComponent {
            setup() {
                this.Component = constructor;
                this.state = useState(params.props || {});
                for (const eventName in params.intercepts || {}) {
                    useListener(eventName, params.intercepts[eventName]);
                }
                useChild();
            }
        }
        Parent.template = xml`<t t-component="Component" t-props="state"/>`;

        const target = getFixture();
        const env = Component.env;
        const parent = await mount(Parent, target, { env });
        registerCleanup(cleanUp);
        registerCleanup(() => {
            destroy(parent);
        });
        return parent.child;
    }

    /**
     * Create a Control Panel instance, with an extensible environment and
     * its related Control Panel Model. Event interception is done through
     * params['get-controller-query-params'] and params.search, for the two
     * available event handlers respectively.
     * @param {Object} [params={}]
     * @param {Object} [params.cpProps]
     * @param {Object} [params.cpModelConfig]
     * @param {boolean} [params.debug]
     * @param {Object} [params.env]
     * @returns {Object} useful control panel testing elements:
     *  - controlPanel: the control panel instance
     *  - el: the control panel HTML element
     *  - helpers: a suite of bound helpers (see above functions for all
     *    available helpers)
     */
    async function createControlPanel(params = {}) {
        const env = makeTestEnvironment(params.env || {});
        const props = Object.assign({
            action: {},
            fields: {},
        }, params.cpProps);
        const globalConfig = Object.assign({
            context: {},
            domain: [],
        }, params.cpModelConfig);

        if (globalConfig.arch && globalConfig.fields) {
            const model = "__mockmodel__";
            const serverParams = {
                model,
                data: { [model]: { fields: globalConfig.fields, records: [] } },
            };
            const mockServer = await testUtilsMock.addMockEnvironment(
                new Widget(),
                serverParams,
            );
            const { arch } = testUtilsMock.getView(mockServer, {
                arch: globalConfig.arch,
                fields: globalConfig.fields,
                model,
                viewOptions: { context: globalConfig.context },
            });
            Object.assign(globalConfig, { arch });
        }

        globalConfig.env = env;
        const archs = (globalConfig.arch && { search: globalConfig.arch, }) || {};
        const { ControlPanel: controlPanelInfo, } = ActionModel.extractArchInfo(archs);
        const extensions = {
            ControlPanel: { archNodes: controlPanelInfo.children, },
        };

        class Parent extends LegacyComponent {
            setup() {
                this.searchModel = new ActionModel(extensions, globalConfig);
                this.state = useState(props);
                useChild();
                onWillStart(async () => {
                    await this.searchModel.load();
                });
                onMounted(() => {
                    if (params['get-controller-query-params']) {
                        this.searchModel.on('get-controller-query-params', this,
                            params['get-controller-query-params']);
                    }
                    if (params.search) {
                        this.searchModel.on('search', this, params.search);
                    }
                });
            }
        }
        Parent.components = { ControlPanel };
        Parent.template = xml`
            <ControlPanel
                t-props="state"
                searchModel="searchModel"
            />`;

        const target = getFixture();
        const parent = await mount(Parent, target, { env });
        const controlPanel = parent.child;
        controlPanel.getQuery = () => parent.searchModel.get("query");
        registerCleanup(() => {
            destroy(parent);
        });
        return controlPanel;
    }

    /**
     * Create a model from given parameters.
     *
     * @param {Object} params This object will be given to addMockEnvironment, so
     *   any parameters from that method applies
     * @param {Class} params.Model the model class to use
     * @returns {Model}
     */
    async function createModel(params) {
        const widget = new Widget();

        const model = new params.Model(widget, params);

        await testUtilsMock.addMockEnvironment(widget, params);

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
     * @returns {Promise<Widget>}
     */
    async function createParent(params) {
        const widget = new Widget();
        await testUtilsMock.addMockEnvironment(widget, params);
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
     * @param {Object[]} [params.favoriteFilters] the favorite filters one would like to have at initialization
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
     * @param {Boolean} [params.touchScreen=false] will add the o_touch_device to the webclient (flag used to define a
     *   device with a touch screen. Default value is false
     * @returns {Promise<AbstractController>} the instance of the view
     */
    async function createView(params) {
        const target = prepareTarget(params.debug);
        const widget = new Widget();
        // reproduce the DOM environment of views
        const webClient = Object.assign(document.createElement('div'), {
            className: params.touchScreen ? 'o_web_client o_touch_device' : 'o_web_client',
        });
        const actionManager = Object.assign(document.createElement('div'), {
            className: 'o_action_manager',
        });
        const dialogContainer = Object.assign(document.createElement('div'), {
            className: 'o_dialog_container',
        });
        target.prepend(webClient);
        webClient.append(actionManager);
        webClient.append(dialogContainer);

        // add mock environment: mock server, session, fieldviewget, ...
        const mockServer = await testUtilsMock.addMockEnvironment(widget, params);
        const viewInfo = testUtilsMock.getView(mockServer, params);

        params.server = mockServer;

        // create the view
        const View = params.View;
        const modelName = params.model || 'foo';
        const defaultAction = {
            res_model: modelName,
            context: {},
            type: 'ir.actions.act_window',
        };
        const viewOptions = Object.assign({
            action: Object.assign(defaultAction, params.action),
            view: { ...viewInfo, fields: mockServer.fieldsGet(params.model) },
            modelName: modelName,
            ids: 'res_id' in params ? [params.res_id] : undefined,
            currentId: 'res_id' in params ? params.res_id : undefined,
            domain: params.domain || [],
            context: params.context || {},
            hasActionMenus: false,
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
            view = new params.View({ viewInfo, modelName });
        } else {
            viewOptions.controlPanelFieldsView = Object.assign(testUtilsMock.getView(mockServer, {
                arch: params.archs && params.archs[params.model + ',false,search'] || '<search/>',
                fields: viewInfo.fields,
                model: params.model,
            }), { favoriteFilters: params.favoriteFilters });

            view = new params.View(viewInfo, viewOptions);
        }

        if (params.interceptsPropagate) {
            for (const name in params.interceptsPropagate) {
                testUtilsMock.intercept(widget, name, params.interceptsPropagate[name], true);
            }
        }

        // Override the ActionMenus registry unless told otherwise.
        let actionMenusRegistry = ActionMenus.registry;
        if (params.actionMenusRegistry !== true) {
            ActionMenus.registry = new Registry();
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
            if (params.actionMenusRegistry !== true) {
                ActionMenus.registry = actionMenusRegistry;
            }
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
        createCalendarView,
        createComponent,
        createControlPanel,
        createModel,
        createParent,
        createView,
        prepareTarget,
    };
});
