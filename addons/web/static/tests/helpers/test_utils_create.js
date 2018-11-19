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
var ControlPanel = require('web.ControlPanel');
var dom = require('web.dom');
var DebugManager = require('web.DebugManager');
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
function createActionManager (params) {
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
                return $.when([]);
            }
            if (mockRPC) {
                return mockRPC.apply(this, arguments);
            }
            return this._super.apply(this, arguments);
        },
    });
    testUtilsMock.addMockEnvironment(widget, _.defaults(params, { debounce: false }));
    widget.prependTo($target);
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
    actionManager.appendTo(widget.$el);

    return actionManager;
}

/**
 * create a view from various parameters.  Here, a view means a javascript
 * instance of an AbstractView class, such as a form view, a list view or a
 * kanban view.
 *
 * It returns the instance of the view, properly created, with all rpcs going
 * through a mock method using the data object as source, and already loaded/
 * started.
 *
 * Most views can be tested synchronously (@see createView), but some view have
 * external dependencies (like lazy loaded libraries). In that case, it is
 * necessary to use this method.
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
 * @returns {Deferred<AbstractView>} resolves with the instance of the view
 */
function createAsyncView(params) {
    var $target = $('#qunit-fixture');
    var widget = new Widget();
    if (params.debug) {
        $target = $('body');
        $target.addClass('debug');
    }

    // add mock environment: mock server, session, fieldviewget, ...
    var mockServer = testUtilsMock.addMockEnvironment(widget, params);
    var viewInfo = testUtilsMock.fieldsViewGet(mockServer, params);
    // create the view
    var viewOptions = {
        modelName: params.model || 'foo',
        ids: 'res_id' in params ? [params.res_id] : undefined,
        currentId: 'res_id' in params ? params.res_id : undefined,
        domain: params.domain || [],
        context: params.context || {},
        groupBy: params.groupBy || [],
    };
    if (params.hasSelectors) {
        viewOptions.hasSelectors = params.hasSelectors;
    }

    _.extend(viewOptions, params.viewOptions);

    var view = new params.View(viewInfo, viewOptions);

    // reproduce the DOM environment of views
    var $web_client = $('<div>').addClass('o_web_client').prependTo($target);
    var controlPanel = new ControlPanel(widget);
    controlPanel.appendTo($web_client);
    var $content = $('<div>').addClass('o_content').appendTo($web_client);

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
        };

        // link the view to the control panel
        view.set_cp_bus(controlPanel.get_bus());

        // render the view in a fragment as they must be able to render correctly
        // without being in the DOM
        var fragment = document.createDocumentFragment();
        return view.appendTo(fragment).then(function () {
            dom.append($content, fragment, {
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
 * Create and return an instance of DebugManager with all rpcs going through a
 * mock method, assuming that the user has access rights, and is an admin.
 *
 * @param {Object} [params={}]
 */
function createDebugManager (params) {
    params = params || {};
    var mockRPC = params.mockRPC;
    _.extend(params, {
        mockRPC: function (route, args) {
            if (args.method === 'check_access_rights') {
                return $.when(true);
            }
            if (args.method === 'xmlid_to_res_id') {
                return $.when(true);
            }
            if (mockRPC) {
                return mockRPC.apply(this, arguments);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            user_has_group: function (group) {
                if (group === 'base.group_no_one') {
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
        },
    });
    var debugManager = new DebugManager();
    testUtilsMock.addMockEnvironment(debugManager, params);
    return debugManager;
}

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

/**
 * create a view synchronously.  This method uses the createAsyncView method.
 * Most views are synchronous, so the deferred can be resolved immediately and
 * this method will work.
 *
 * Be careful, if for some reason a view is async, this method will crash.
 * @see createAsyncView
 *
 * @param {Object} params will be given to createAsyncView
 * @returns {AbstractView}
 */
function createView(params) {
    var view;
    createAsyncView(params).then(function (result) {
        view = result;
    });
    if (!view) {
        throw "The view that you are trying to create is async. Please use createAsyncView instead";
    }
    return view;
}


return {
    createActionManager: createActionManager,
    createAsyncView: createAsyncView,
    createDebugManager: createDebugManager,
    createModel: createModel,
    createParent: createParent,
    createView: createView,
};

});
