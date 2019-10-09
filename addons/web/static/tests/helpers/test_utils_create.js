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

var ActionManager = require('web.ActionManager');
var config = require('web.config');
var ControlPanelView = require('web.ControlPanelView');
var concurrency = require('web.concurrency');
var DebugManager = require('web.DebugManager.Backend');
var dom = require('web.dom');
var testUtilsMock = require('web.test_utils_mock');
var Widget = require('web.Widget');

/**
 * create and return an instance of ActionManager with all rpcs going through a
 * mock method using the data, actions and archs objects as sources.
 *
 * @param {Object} [params]
 * @param {Object} [params.actions] the actions given to the mock server
 * @param {Object} [params.archs] this archs given to the mock server
 * @param {Object} [params.data] the business data given to the mock server
 * @param {boolean} [params.debug]
 * @param {function} [params.mockRPC]
 * @returns {ActionManager}
 */
var createActionManager = async function (params) {
    params = params || {};
    var $target = $('#qunit-fixture');
    if (params.debug) {
        $target = $('body');
        $target.addClass('debug');
    }

    var widget = new Widget();
    // when 'document' addon is installed, the sidebar does a 'search_read' on
    // model 'ir_attachment' each time a record is open, so we monkey-patch
    // 'mockRPC' to mute those RPCs, so that the tests can be written uniformly,
    // whether or not 'document' is installed
    var mockRPC = params.mockRPC;
    _.extend(params, {
        mockRPC: function (route, args) {
            if (args.model === 'ir.attachment') {
                return Promise.resolve([]);
            }
            if (mockRPC) {
                return mockRPC.apply(this, arguments);
            }
            return this._super.apply(this, arguments);
        },
    });
    testUtilsMock.addMockEnvironment(widget, _.defaults(params, { debounce: false }));
    await widget.prependTo($target);
    widget.$el.addClass('o_web_client');
    if (config.device.isMobile) {
        widget.$el.addClass('o_touch_device');
    }

    var userContext = params.context && params.context.user_context || {};
    var actionManager = new ActionManager(widget, userContext);

    var originalDestroy = ActionManager.prototype.destroy;
    actionManager.destroy = function () {
        actionManager.destroy = originalDestroy;
        widget.destroy();
    };
    var fragment = document.createDocumentFragment();
    return actionManager.appendTo(fragment).then(function () {
        dom.append(widget.$el, fragment, {
            callbacks: [{ widget: actionManager }],
            in_DOM: true,
        });
        return actionManager;
    });
};

/**
 * create a view from various parameters.  Here, a view means a javascript
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
 * @param {Object} [params.debug=false] if true, the widget will be appended in
 *   the DOM. Also, RPCs and uncaught OdooEvent will be logged
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
 * @returns {Promise<AbstractController>} resolves with the instance of the view
 */
async function createView(params) {
    var $target = $('#qunit-fixture');
    var widget = new Widget();
    if (params.debug) {
        $target = $('body');
        $target.addClass('debug');
    }
    // reproduce the DOM environment of views
    var $webClient = $('<div>').addClass('o_web_client').prependTo($target);
    var $actionManager = $('<div>').addClass('o_action_manager').appendTo($webClient);


    // add mock environment: mock server, session, fieldviewget, ...
    var mockServer = testUtilsMock.addMockEnvironment(widget, params);
    var viewInfo = testUtilsMock.fieldsViewGet(mockServer, params);

    // create the view
    var View = params.View;
    var viewOptions = _.defaults({}, params.viewOptions, {
        modelName: params.model || 'foo',
        ids: 'res_id' in params ? [params.res_id] : undefined,
        currentId: 'res_id' in params ? params.res_id : undefined,
        domain: params.domain || [],
        context: params.context || {},
        hasSidebar: false,
    });
    // patch the View to handle the groupBy given in params, as we can't give it
    // in init (unlike the domain and context which can be set in the action)
    testUtilsMock.patch(View, {
        _updateMVCParams: function () {
            this._super.apply(this, arguments);
            this.loadParams.groupedBy = params.groupBy || viewOptions.groupBy || [];
            testUtilsMock.unpatch(View);
        },
    });
    if ('hasSelectors' in params) {
        viewOptions.hasSelectors = params.hasSelectors;
    }

    var view;
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
        _.each(params.interceptsPropagate, function (cb, name) {
            testUtilsMock.intercept(widget, name, cb, true);
        });
    }

    return view.getController(widget).then(function (view) {
        // override the view's 'destroy' so that it calls 'destroy' on the widget
        // instead, as the widget is the parent of the view and the mockServer.
        view.__destroy = view.destroy;
        view.destroy = function () {
            // remove the override to properly destroy the view and its children
            // when it will be called the second time (by its parent)
            delete view.destroy;
            widget.destroy();
            $webClient.remove();
        };

        // render the view in a fragment as they must be able to render correctly
        // without being in the DOM
        var fragment = document.createDocumentFragment();
        return view.appendTo(fragment).then(function () {
            dom.prepend($actionManager, fragment, {
                callbacks: [{ widget: view }],
                in_DOM: true,
            });

            view.$el.on('click', 'a', function (ev) {
                ev.preventDefault();
            });
            return view;
        });
    });
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
 * @param {Object} params see @createView
 * @param {Object} [options]
 * @param {boolean} [options.positionalClicks=false]
 * @returns {Promise<CalendarController>}
 */
async function createCalendarView(params, options) {
    var calendar = await createView(params);
    if (!options || !options.positionalClicks) {
        return calendar;
    }
    var $view = $('#qunit-fixture').contents();
    $view.prependTo('body');
    var destroy = calendar.destroy;
    calendar.destroy = function () {
        $view.remove();
        destroy();
    };
    await concurrency.delay(0);
    return calendar;
}

/**
 * create a controlPanel from various parameters.
 *
 * It returns an instance of ControlPanelController
 *
 * @param {Object} [params={}]
 * @param {Object} [params.action={}]
 * @param {Object} [params.context={}]
 * @param {Object} [params.debug=false] if true, the widget will be appended in
 *   the DOM. Also, RPCs and uncaught OdooEvent will be logged
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
function createControlPanel(params) {
    params = params || {};
    var $target = $('#qunit-fixture');
    if (params.debug) {
        $target = $('body');
        $target.addClass('debug');
    }
    // reproduce the DOM environment of a view control panel
    var $webClient = $('<div>').addClass('o_web_client').prependTo($target);
    var $actionManager = $('<div>').addClass('o_action_manager').appendTo($webClient);
    var $action = $('<div>').addClass('o_action').appendTo($actionManager);

    var widget = new Widget();
    // add mock environment: mock server, session, fieldviewget, ...
    var mockServer = testUtilsMock.addMockEnvironment(widget, params);
    if (!params.viewInfo) {
        try {
            params.viewInfo = testUtilsMock.fieldsViewGet(mockServer, params);
        } catch (e) {
            // if an error occurs we keep params.viewInfo undefined.
            // It will be set to {arch: '<controlpanel/>', fields: {}} in
            // ControlPanelView init function.
        }
    }

    var viewOptions = _.defaults({}, params.viewOptions, {
        context: params.context,
        modelName: params.model,
        searchMenuTypes: params.searchMenuTypes,
        viewInfo: params.viewInfo,
    });
    var controlPanelView = new ControlPanelView(viewOptions);
    return controlPanelView.getController(widget).then(function (controlPanel) {
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
        var fragment = document.createDocumentFragment();
        return controlPanel.appendTo(fragment).then(function () {
            dom.prepend($action, fragment, {
                callbacks: [{ widget: controlPanel }],
                in_DOM: true,
            });
            return controlPanel;
        });
    });
}
/**
 * Create and return an instance of DebugManager with all rpcs going through a
 * mock method, assuming that the user has access rights, and is an admin.
 *
 * @param {Object} [params={}]
 */
var createDebugManager = function (params) {
    params = params || {};
    var mockRPC = params.mockRPC;
    _.extend(params, {
        mockRPC: function (route, args) {
            if (args.method === 'check_access_rights') {
                return Promise.resolve(true);
            }
            if (args.method === 'xmlid_to_res_id') {
                return Promise.resolve(true);
            }
            if (mockRPC) {
                return mockRPC.apply(this, arguments);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            user_has_group: function (group) {
                if (group === 'base.group_no_one') {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
        },
    });
    var debugManager = new DebugManager();
    testUtilsMock.addMockEnvironment(debugManager, params);
    return debugManager;
};

/**
 * create a model from given parameters.
 *
 * @param {Object} params This object will be given to addMockEnvironment, so
 *   any parameters from that method applies
 * @param {Class} params.Model the model class to use
 * @returns {Model}
 */
function createModel(params) {
    var widget = new Widget();

    var model = new params.Model(widget);

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
 * create a widget parent from given parameters.
 *
 * @param {Object} params This object will be given to addMockEnvironment, so
 *   any parameters from that method applies
 * @returns {Widget}
 */
function createParent(params) {
    var widget = new Widget();
    testUtilsMock.addMockEnvironment(widget, params);
    return widget;
}

return {
    createActionManager: createActionManager,
    createCalendarView: createCalendarView,
    createControlPanel: createControlPanel,
    createDebugManager: createDebugManager,
    createModel: createModel,
    createParent: createParent,
    createView: createView,
};

});
