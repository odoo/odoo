odoo.define('web.test_utils_mock', function (require) {
"use strict";

/**
 * Mock Test Utils
 *
 * This module defines various utility functions to help mocking data.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

const AbstractStorageService = require('web.AbstractStorageService');
const AjaxService = require('web.AjaxService');
const basic_fields = require('web.basic_fields');
const Bus = require('web.Bus');
const config = require('web.config');
const core = require('web.core');
const dom = require('web.dom');
const FormController = require('web.FormController');
const makeTestEnvironment = require('web.test_env');
const MockServer = require('web.MockServer');
const RamStorage = require('web.RamStorage');
const session = require('web.session');
const { patchDate } = require("@web/../tests/helpers/utils");
const { processArch } = require("@web/legacy/legacy_load_views");

const { Component } = owl;
const DebouncedField = basic_fields.DebouncedField;


//------------------------------------------------------------------------------
// Private functions
//------------------------------------------------------------------------------

/**
 * Returns a mocked environment to be used by OWL components in tests, with
 * requested services (+ ajax, local_storage and session_storage) deployed.
 *
 * @private
 * @param {Object} params
 * @param {Bus} [params.bus]
 * @param {boolean} [params.debug]
 * @param {Object} [params.env]
 * @param {Bus} [params.env.bus]
 * @param {Object} [params.env.dataManager]
 * @param {Object} [params.env.services]
 * @param {Object[]} [params.favoriteFilters]
 * @param {Object} [params.services]
 * @param {Object} [params.session]
 * @param {MockServer} [mockServer]
 * @returns {Promise<Object>} env
 */
async function _getMockedOwlEnv(params, mockServer) {
    params.env = params.env || {};

    const database = {parameters: params.translateParameters || {}};

    // build the env
    const favoriteFilters = params.favoriteFilters;
    const debug = params.debug;
    const services = {};
    const env = Object.assign({}, params.env, {
        _t: params.env && params.env._t || Object.assign((s => s), { database }),
        browser: Object.assign({
            fetch: (resource, init) => mockServer.performFetch(resource, init),
        }, params.env.browser),
        bus: params.bus || params.env.bus || new Bus(),
        dataManager: Object.assign({
            load_action: (actionID, context) => {
                return mockServer.performRpc('/web/action/load', {
                    action_id: actionID,
                    additional_context: context,
                });
            },
            load_views: (params, options) => {
                return mockServer.performRpc('/web/dataset/call_kw/' + params.model, {
                    args: [],
                    kwargs: {
                        context: params.context,
                        options: options,
                        views: params.views_descr,
                    },
                    method: 'get_views',
                    model: params.model,
                }).then(function (views) {
                    views = _.mapObject(views, viewParams => {
                        return getView(mockServer, viewParams);
                    });
                    if (favoriteFilters && 'search' in views) {
                        views.search.favoriteFilters = favoriteFilters;
                    }
                    return views;
                });
            },
            load_filters: params => {
                if (debug) {
                    console.log('[mock] load_filters', params);
                }
                return Promise.resolve([]);
            },
        }, params.env.dataManager),
        services: Object.assign(services, params.env.services),
        session: params.env.session || params.session || {},
    });

    // deploy services into the env
    // determine services to instantiate (classes), and already register function services
    const servicesToDeploy = {};
    for (const name in params.services || {}) {
        const Service = params.services[name];
        if (Service.constructor.name === 'Class') {
            servicesToDeploy[name] = Service;
        } else {
            services[name] = Service;
        }
    }
    // always deploy ajax, local storage and session storage
    if (!servicesToDeploy.ajax) {
        const MockedAjaxService = AjaxService.extend({
            rpc: mockServer.performRpc.bind(mockServer),
        });
        services.ajax = new MockedAjaxService(env);
    }
    const RamStorageService = AbstractStorageService.extend({
        storage: new RamStorage(),
    });
    if (!servicesToDeploy.local_storage) {
        services.local_storage = new RamStorageService(env);
    }
    if (!servicesToDeploy.session_storage) {
        services.session_storage = new RamStorageService(env);
    }
    // deploy other requested services
    let done = false;
    while (!done) {
        const serviceName = Object.keys(servicesToDeploy).find(serviceName => {
            const Service = servicesToDeploy[serviceName];
            return Service.prototype.dependencies.every(depName => {
                return env.services[depName];
            });
        });
        if (serviceName) {
            const Service = servicesToDeploy[serviceName];
            services[serviceName] = new Service(env);
            delete servicesToDeploy[serviceName];
            services[serviceName].start();
        } else {
            const serviceNames = _.keys(servicesToDeploy);
            if (serviceNames.length) {
                console.warn("Non loaded services:", serviceNames);
            }
            done = true;
        }
    }
    // wait for asynchronous services to properly start
    await new Promise(setTimeout);

    return env;
}
/**
 * This function is used to mock global objects (session, config...) in tests.
 * It is necessary for legacy widgets. It returns a cleanUp function to call at
 * the end of the test.
 *
 * The function could be removed as soon as we do not support legacy widgets
 * anymore.
 *
 * @private
 * @param {Object} params
 * @param {Object} [params.config] if given, it is used to extend the global
 *   config,
 * @param {Object} [params.session] if given, it is used to extend the current,
 *   real session.
 * @param {Object} [params.translateParameters] if given, it will be used to
 *   extend the core._t.database.parameters object.
 * @returns {function} a cleanUp function to restore everything, to call at the
 *   end of the test
 */
function _mockGlobalObjects(params) {
    // store initial session state (for restoration)
    const initialSession = Object.assign({}, session);
    const sessionPatch = Object.assign({
        getTZOffset() { return 0; },
        async user_has_group() { return false; },
    }, params.session);
    // patch session
    Object.assign(session, sessionPatch);

    // patch config
    let initialConfig;
    if ('config' in params) {
        initialConfig = Object.assign({}, config);
        initialConfig.device = Object.assign({}, config.device);
        if ('device' in params.config) {
            Object.assign(config.device, params.config.device);
        }
        if ('debug' in params.config) {
            odoo.debug = params.config.debug;
        }
    }

    // patch translate params
    let initialParameters;
    if ('translateParameters' in params) {
        initialParameters = Object.assign({}, core._t.database.parameters);
        Object.assign(core._t.database.parameters, params.translateParameters);
    }

    // build the cleanUp function to restore everything at the end of the test
    function cleanUp() {
        let key;
        for (key in sessionPatch) {
            delete session[key];
        }
        Object.assign(session, initialSession);
        if ('config' in params) {
            for (key in config) {
                delete config[key];
            }
            _.extend(config, initialConfig);
        }
        if ('translateParameters' in params) {
            for (key in core._t.database.parameters) {
                delete core._t.database.parameters[key];
            }
            _.extend(core._t.database.parameters, initialParameters);
        }
    }

    return cleanUp;
}
/**
 * logs all event going through the target widget.
 *
 * @param {Widget} widget
 */
function _observe(widget) {
    var _trigger_up = widget._trigger_up.bind(widget);
    widget._trigger_up = function (event) {
        console.log('%c[event] ' + event.name, 'color: blue; font-weight: bold;', event);
        _trigger_up(event);
    };
}

//------------------------------------------------------------------------------
// Public functions
//------------------------------------------------------------------------------

/**
 * performs a get_view, and mocks the postprocessing done by the
 * data_manager to return an equivalent structure.
 *
 * @param {MockServer} server
 * @param {Object} params
 * @param {string} params.model
 * @returns {Object} an object with 3 keys: arch, fields and viewFields
 */
function getView(server, params) {
    var view = server.getView(params);
    const fields = server.fieldsGet(params.model);
    // mock the structure produced by the DataManager
    const models = { [params.model]: fields };
    for (const modelName of view.models) {
        models[modelName] = models[modelName] || server.fieldsGet(modelName);
    }
    const { arch, viewFields } = processArch(view.arch, view.type, params.model, models);
    return {
        arch,
        fields,
        model: view.model,
        toolbar: view.toolbar,
        type: view.type,
        viewFields,
        view_id: view.id,
    };
}

/**
 * intercepts an event bubbling up the widget hierarchy. The event intercepted
 * must be a "custom event", i.e. an event generated by the method 'trigger_up'.
 *
 * Note that this method really intercepts the event if @propagate is not set.
 * It will not be propagated further, and even the handlers on the target will
 * not fire.
 *
 * @param {Widget} widget the target widget (any Odoo widget)
 * @param {string} eventName description of the event
 * @param {function} fn callback executed when the even is intercepted
 * @param {boolean} [propagate=false]
 */
function intercept(widget, eventName, fn, propagate) {
    var _trigger_up = widget._trigger_up.bind(widget);
    widget._trigger_up = function (event) {
        if (event.name === eventName) {
            fn(event);
            if (!propagate) { return; }
        }
        _trigger_up(event);
    };
}

/**
 * Add a mock environment to test Owl Components. This function generates a test
 * env and sets it on the given Component. It also has several side effects,
 * like patching the global session or config objects. It returns a cleanup
 * function to call at the end of the test.
 *
 * @param {Component} Component
 * @param {Object} [params]
 * @param {Object} [params.actions]
 * @param {Object} [params.archs]
 * @param {string} [params.currentDate]
 * @param {Object} [params.data]
 * @param {boolean} [params.debug]
 * @param {function} [params.mockFetch]
 * @param {function} [params.mockRPC]
 * @param {number} [params.fieldDebounce=0] the value of the DEBOUNCE attribute
 *   of fields
 * @param {boolean} [params.debounce=true] if false, patch _.debounce to remove
 *   its behavior
 * @param {boolean} [params.throttle=false] by default, _.throttle is patched to
 *   remove its behavior, except if this params is set to true
 * @param {boolean} [params.mockSRC=false] if true, redirect src GET requests to
 *   the mockServer
 * @param {MockServer} [mockServer]
 * @returns {Promise<function>} the cleanup function
 */
async function addMockEnvironmentOwl(Component, params, mockServer) {
    params = params || {};

    // instantiate a mockServer if not provided
    if (!mockServer) {
        let Server = MockServer;
        if (params.mockFetch) {
            Server = MockServer.extend({ _performFetch: params.mockFetch });
        }
        if (params.mockRPC) {
            Server = Server.extend({ _performRpc: params.mockRPC });
        }
        mockServer = new Server(params.data, {
            actions: params.actions,
            archs: params.archs,
            currentDate: params.currentDate,
            debug: params.debug,
        });
    }

    // remove the multi-click delay for the quick edit in form view
    const initialQuickEditDelay = FormController.prototype.multiClickTime;
    FormController.prototype.multiClickTime = params.formMultiClickTime || 0;

    // make sure the debounce value for input fields is set to 0
    const initialDebounceValue = DebouncedField.prototype.DEBOUNCE;
    DebouncedField.prototype.DEBOUNCE = params.fieldDebounce || 0;
    const initialDOMDebounceValue = dom.DEBOUNCE;
    dom.DEBOUNCE = 0;

    // patch underscore debounce/throttle functions
    const initialDebounce = _.debounce;
    if (params.debounce === false) {
        _.debounce = function (func) {
            return func;
        };
    }
    // fixme: throttle is inactive by default, should we make it explicit ?
    const initialThrottle = _.throttle;
    if (!('throttle' in params) || !params.throttle) {
        _.throttle = function (func) {
            return func;
        };
    }

    // mock global objects for legacy widgets (session, config...)
    const restoreMockedGlobalObjects = _mockGlobalObjects(params);

    // set the test env on owl Component
    const env = await _getMockedOwlEnv(params, mockServer);
    const originalEnv = Component.env;
    const __env = makeTestEnvironment(env, mockServer.performRpc.bind(mockServer));
    owl.Component.env = __env;

    // while we have a mix between Owl and legacy stuff, some of them triggering
    // events on the env.bus (a new Bus instance especially created for the current
    // test), the others using core.bus, we have to ensure that events triggered
    // on env.bus are also triggered on core.bus (note that outside the testing
    // environment, both are the exact same instance of Bus)
    const envBusTrigger = env.bus.trigger;
    env.bus.trigger = function () {
        core.bus.trigger(...arguments);
        envBusTrigger.call(env.bus, ...arguments);
    };

    // build the clean up function to call at the end of the test
    function cleanUp() {
        env.bus.destroy();
        Object.keys(env.services).forEach(function (s) {
            var service = env.services[s] || {};
            if (service.destroy && !service.isDestroyed()) {
                service.destroy();
            }
        });

        FormController.prototype.multiClickTime = initialQuickEditDelay;

        DebouncedField.prototype.DEBOUNCE = initialDebounceValue;
        dom.DEBOUNCE = initialDOMDebounceValue;
        _.debounce = initialDebounce;
        _.throttle = initialThrottle;

        // clear the caches (e.g. data_manager, ModelFieldSelector) at the end
        // of each test to avoid collisions
        core.bus.trigger('clear_cache');

        $('body').off('DOMNodeInserted.removeSRC');
        $('.blockUI').remove(); // fixme: move to qunit_config in OdooAfterTestHook?

        restoreMockedGlobalObjects();

        Component.env = originalEnv;
    }

    return cleanUp;
}

/**
 * Add a mock environment to a widget.  This helper function can simulate
 * various kind of side effects, such as mocking RPCs, changing the session,
 * or the translation settings.
 *
 * The simulated environment lasts for the lifecycle of the widget, meaning it
 * disappears when the widget is destroyed.  It is particularly relevant for the
 * session mocks, because the previous session is restored during the destroy
 * call.  So, it means that you have to be careful and make sure that it is
 * properly destroyed before another test is run, otherwise you risk having
 * interferences between tests.
 *
 * @param {Widget} widget
 * @param {Object} params
 * @param {Object} [params.archs] a map of string [model,view_id,view_type] to
 *   a arch object. It is used to mock answers to 'load_views' custom events.
 *   This is useful when the widget instantiate a formview dialog that needs
 *   to load a particular arch.
 * @param {string} [params.currentDate] a string representation of the current
 *   date. It is given to the mock server.
 * @param {Object} params.data the data given to the created mock server. It is
 *   used to generate mock answers for every kind of routes supported by odoo
 * @param {number} [params.debug] if set to true, logs RPCs and uncaught Odoo
 *   events.
 * @param {Object} [params.bus] the instance of Bus that will be used (in the env)
 * @param {function} [params.mockFetch] a function that will be used to override
 *   the _performFetch method from the mock server. It is really useful to add
 *   some custom fetch mocks, or to check some assertions.
 * @param {function} [params.mockRPC] a function that will be used to override
 *   the _performRpc method from the mock server. It is really useful to add
 *   some custom rpc mocks, or to check some assertions.
 * @param {Object} [params.session] if it is given, it will be used as answer
 *   for all calls to this.getSession() by the widget, of its children.  Also,
 *   it will be used to extend the current, real session. This side effect is
 *   undone when the widget is destroyed.
 * @param {Object} [params.translateParameters] if given, it will be used to
 *   extend the core._t.database.parameters object. After the widget
 *   destruction, the original parameters will be restored.
 * @param {Object} [params.intercepts] an object with event names as key, and
 *   callback as value.  Each key,value will be used to intercept the event.
 *   Note that this is particularly useful if you want to intercept events going
 *   up in the init process of the view, because there are no other way to do it
 *   after this method returns. Some events ('call_service', "load_views",
 *   "get_session", "load_filters") have a special treatment beforehand.
 * @param {Object} [params.services={}] list of services to load in
 *   addition to the ajax service. For instance, if a test needs the local
 *   storage service in order to work, it can provide a mock version of it.
 * @param {boolean} [debounce=true] set to false to completely remove the
 *   debouncing, forcing the handler to be called directly (not on the next
 *   execution stack, like it does with delay=0).
 * @param {boolean} [throttle=false] set to true to keep the throttling, which
 *   is completely removed by default.
 *
 * @returns {Promise<MockServer>} the instance of the mock server, created by this
 *   function. It is necessary for createView so that method can call some
 *   other methods on it.
 */
async function addMockEnvironment(widget, params) {
    // log events triggered up if debug flag is true
    if (params.debug) {
        _observe(widget);
        var separator = window.location.href.indexOf('?') !== -1 ? "&" : "?";
        var url = window.location.href + separator + 'testId=' + QUnit.config.current.testId;
        console.log('%c[debug] debug mode activated', 'color: blue; font-weight: bold;', url);
    }

    // instantiate mock server
    var Server = MockServer;
    if (params.mockFetch) {
        Server = MockServer.extend({ _performFetch: params.mockFetch });
    }
    if (params.mockRPC) {
        Server = Server.extend({ _performRpc: params.mockRPC });
    }
    var mockServer = new Server(params.data, {
        actions: params.actions,
        archs: params.archs,
        currentDate: params.currentDate,
        debug: params.debug,
        widget: widget,
    });

    // build and set the Owl env on Component
    if (!('mockSRC' in params)) { // redirect src rpcs to the mock server
        params.mockSRC = true;
    }
    const cleanUp = await addMockEnvironmentOwl(Component, params, mockServer);
    const env = Component.env;

    // ensure to clean up everything when the widget will be destroyed
    const destroy = widget.destroy;
    widget.destroy = function () {
        cleanUp();
        destroy.call(this, ...arguments);
    };

    // intercept service/data manager calls and redirect them to the env
    intercept(widget, 'call_service', function (ev) {
        if (env.services[ev.data.service]) {
            var service = env.services[ev.data.service];
            const result = service[ev.data.method].apply(service, ev.data.args || []);
            ev.data.callback(result);
        }
    });
    intercept(widget, 'load_action', async ev => {
        const action = await env.dataManager.load_action(ev.data.actionID, ev.data.context);
        ev.data.on_success(action);
    });
    intercept(widget, "load_views", async ev => {
        const params = {
            model: ev.data.modelName,
            context: ev.data.context,
            views_descr: ev.data.views,
        };
        const views = await env.dataManager.load_views(params, ev.data.options);
        if ('search' in views && params.favoriteFilters) {
            views.search.favoriteFilters = params.favoriteFilters;
        }
        ev.data.on_success(views);
    });
    intercept(widget, "get_session", ev => {
        ev.data.callback(session);
    });
    intercept(widget, "load_filters", async ev => {
        const filters = await env.dataManager.load_filters(ev.data);
        ev.data.on_success(filters);
    });

    // make sure all other Odoo events bubbling up are intercepted
    Object.keys(params.intercepts || {}).forEach(function (name) {
        intercept(widget, name, params.intercepts[name]);
    });

    return mockServer;
}

/**
 * Patch window.Date so that the time starts its flow from the provided Date.
 *
 * Usage:
 *
 *  ```
 *  testUtils.mock.patchDate(2018, 0, 10, 17, 59, 30)
 *  new window.Date(); // "Wed Jan 10 2018 17:59:30 GMT+0100 (Central European Standard Time)"
 *  ... // 5 hours delay
 *  new window.Date(); // "Wed Jan 10 2018 22:59:30 GMT+0100 (Central European Standard Time)"
 *  ```
 *
 * The returned function is there to preserve the former API. Before it was
 * necessary to call that function to unpatch the date. Now the unpatch is
 * done automatically via a call to registerCleanup.
 *
 * @param {integer} year
 * @param {integer} month index of the month, starting from zero.
 * @param {integer} day the day of the month.
 * @param {integer} hours the digits for hours (24h)
 * @param {integer} minutes
 * @param {integer} seconds
 * @returns {Function} callback function is now useless
 */
function legacyPatchDate(year, month, day, hours, minutes, seconds) {
    patchDate(year, month, day, hours, minutes, seconds);
    return function () {}; // all calls to that function are now useless
}

var patches = {};
/**
 * Patches a given Class or Object with the given properties.
 *
 * @param {Class|Object} target
 * @param {Object} props
 */
function patch(target, props) {
    var patchID = _.uniqueId('patch_');
    target.__patchID = patchID;
    patches[patchID] = {
        target: target,
        otherPatchedProps: [],
        ownPatchedProps: [],
    };
    if (target.prototype) {
        _.each(props, function (value, key) {
            if (target.prototype.hasOwnProperty(key)) {
                patches[patchID].ownPatchedProps.push({
                    key: key,
                    initialValue: target.prototype[key],
                });
            } else {
                patches[patchID].otherPatchedProps.push(key);
            }
        });
        target.include(props);
    } else {
        _.each(props, function (value, key) {
            if (key in target) {
                var oldValue = target[key];
                patches[patchID].ownPatchedProps.push({
                    key: key,
                    initialValue: oldValue,
                });
                if (typeof value === 'function') {
                    target[key] = function () {
                        var oldSuper = this._super;
                        this._super = oldValue;
                        var result = value.apply(this, arguments);
                        if (oldSuper === undefined) {
                            delete this._super;
                        } else {
                            this._super = oldSuper;
                        }
                        return result;
                    };
                } else {
                    target[key] = value;
                }
            } else {
                patches[patchID].otherPatchedProps.push(key);
                target[key] = value;
            }
        });
    }
}

/**
 * Unpatches a given Class or Object.
 *
 * @param {Class|Object} target
 */
function unpatch(target) {
    var patchID = target.__patchID;
    var patch = patches[patchID];
    if (target.prototype) {
        _.each(patch.ownPatchedProps, function (p) {
            target.prototype[p.key] = p.initialValue;
        });
        _.each(patch.otherPatchedProps, function (key) {
            delete target.prototype[key];
        });
    } else {
        _.each(patch.ownPatchedProps, function (p) {
            target[p.key] = p.initialValue;
        });
        _.each(patch.otherPatchedProps, function (key) {
            delete target[key];
        });
    }
    delete patches[patchID];
    delete target.__patchID;
}

window.originalSetTimeout = window.setTimeout;
function patchSetTimeout() {
    var original = window.setTimeout;
    var self = this;
    window.setTimeout = function (handler, delay) {
        console.log("calling setTimeout on " + (handler.name || "some function") + "with delay of " + delay);
        console.trace();
        var handlerArguments = Array.prototype.slice.call(arguments, 1);
        return original(function () {
            handler.bind(self, handlerArguments)();
            console.log('after doing the action of the setTimeout');
        }, delay);
    };

    return function () {
        window.setTimeout = original;
    };
}

return {
    addMockEnvironment: addMockEnvironment,
    getView: getView,
    addMockEnvironmentOwl: addMockEnvironmentOwl,
    intercept: intercept,
    patchDate: legacyPatchDate,
    patch: patch,
    unpatch: unpatch,
    patchSetTimeout: patchSetTimeout,
};

});
