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

var basic_fields = require('web.basic_fields');
var config = require('web.config');
var core = require('web.core');
var dom = require('web.dom');
var MockServer = require('web.MockServer');
var session = require('web.session');

var DebouncedField = basic_fields.DebouncedField;

//------------------------------------------------------------------------------
// Private functions
//------------------------------------------------------------------------------

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
 * Removes the src attribute on images and iframes to prevent not found errors,
 * and optionally triggers an rpc with the src url as route on a widget.
 * This method is critical and must be fastest (=> no jQuery, no underscore)
 *
 * @param {DOM Node} el
 * @param {[Widget]} widget the widget on which the rpc should be performed
 */
function removeSrcAttribute(el, widget) {
    var nodes;
    if (el.nodeName === 'IMG' || el.nodeName === 'IFRAME') {
        nodes = [el];
    } else {
        nodes = Array.prototype.slice.call(el.getElementsByTagName('img'))
            .concat(Array.prototype.slice.call(el.getElementsByTagName('iframe')));
    }
    var node;
    while (node = nodes.pop()) {
        var src = node.attributes.src && node.attributes.src.value;
        if (src && src !== 'about:blank') {
            node.setAttribute('data-src', src);
            if (node.nodeName === 'IMG') {
                node.attributes.removeNamedItem('src');
            } else {
                node.setAttribute('src', 'about:blank');
            }
            if (widget) {
                widget._rpc({ route: src });
            }
        }
    }
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
 * @returns {MockServer} the instance of the mock server, created by this
 *   function. It is necessary for createAsyncView so that method can call some
 *   other methods on it.
 */
function addMockEnvironment(widget, params) {
    var Server = MockServer;
    params.services = params.services || {};
    if (params.mockRPC) {
        Server = MockServer.extend({ _performRpc: params.mockRPC });
    }
    if (params.debug) {
        _observe(widget);
        var separator = window.location.href.indexOf('?') !== -1 ? "&" : "?";
        var url = window.location.href + separator + 'testId=' + QUnit.config.current.testId;
        console.log('%c[debug] debug mode activated', 'color: blue; font-weight: bold;', url);
    }

    var mockServer = new Server(params.data, {
        actions: params.actions,
        archs: params.archs,
        currentDate: params.currentDate,
        debug: params.debug,
        widget: widget,
    });

    // make sure images do not trigger a GET on the server
    $('body').on('DOMNodeInserted.removeSRC', function (event) {
        removeSrcAttribute(event.target, widget);
    });

    // make sure the debounce value for input fields is set to 0
    var initialDebounceValue = DebouncedField.prototype.DEBOUNCE;
    DebouncedField.prototype.DEBOUNCE = params.fieldDebounce || 0;
    var initialDOMDebounceValue = dom.DEBOUNCE;
    dom.DEBOUNCE = 0;
    var initialSession, initialConfig, initialParameters, initialDebounce, initialThrottle;
    initialSession = _.extend({}, session);
    session.getTZOffset = function () {
        return 0; // by default, but may be overriden in specific tests
    };
    if ('session' in params) {
        _.extend(session, params.session);
    }
    if ('config' in params) {
        initialConfig = _.clone(config);
        initialConfig.device = _.clone(config.device);
        if ('device' in params.config) {
            _.extend(config.device, params.config.device);
        }
        if ('debug' in params.config) {
            config.debug = params.config.debug;
        }
    }
    if ('translateParameters' in params) {
        initialParameters = _.extend({}, core._t.database.parameters);
        _.extend(core._t.database.parameters, params.translateParameters);
    }
    if (params.debounce === false) {
        initialDebounce = _.debounce;
        _.debounce = function (func) {
            return func;
        };
    }
    if (!('throttle' in params) || !params.throttle) {
        initialThrottle = _.throttle;
        _.throttle = function (func) {
            return func;
        };
    }

    var widgetDestroy = widget.destroy;
    widget.destroy = function () {
        // clear the caches (e.g. data_manager, ModelFieldSelector) when the
        // widget is destroyed, at the end of each test to avoid collisions
        core.bus.trigger('clear_cache');

        _(services).chain()
            .compact() // services can be defined but null (e.g. ajax)
            .reject(function (s) { return s.isDestroyed(); })
            .invoke('destroy');

        DebouncedField.prototype.DEBOUNCE = initialDebounceValue;
        dom.DEBOUNCE = initialDOMDebounceValue;
        if (params.debounce === false) {
            _.debounce = initialDebounce;
        }
        if (!('throttle' in params) || !params.throttle) {
            _.throttle = initialThrottle;
        }

        var key;
        if ('session' in params) {
            for (key in session) {
                delete session[key];
            }
        }
        _.extend(session, initialSession);
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

        $('body').off('DOMNodeInserted.removeSRC');
        $('.blockUI').remove();

        widgetDestroy.call(this);
    };

    // Dispatch service calls
    // Note: some services could call other services at init,
    // Which is why we have to init services after that
    var services = {};
    intercept(widget, 'call_service', function (ev) {
        var args, result;
        if (services[ev.data.service]) {
            var service = services[ev.data.service];
            args = (ev.data.args || []);
            result = service[ev.data.method].apply(service, args);
        } else if (ev.data.service === 'ajax') {
            // use ajax service that is mocked by the server
            var route = ev.data.args[0];
            args = ev.data.args[1];
            result = mockServer.performRpc(route, args);
        }
        ev.data.callback(result);
    });

    intercept(widget, 'load_action', function (event) {
        mockServer.performRpc('/web/action/load', {
            kwargs: {
                action_id: event.data.actionID,
                additional_context: event.data.context,
            },
        }).then(function (action) {
            event.data.on_success(action);
        });
    });

    intercept(widget, "load_views", function (event) {
        mockServer.performRpc('/web/dataset/call_kw/' + event.data.modelName, {
            args: [],
            kwargs: {
                context: event.data.context,
                options: event.data.options,
                views: event.data.views,
            },
            method: 'load_views',
            model: event.data.modelName,
        }).then(function (views) {
            views = _.mapObject(views, function (viewParams) {
                return fieldsViewGet(mockServer, viewParams);
            });
            event.data.on_success(views);
        });
    });

    intercept(widget, "get_session", function (event) {
        event.data.callback(session);
    });

    intercept(widget, "load_filters", function (event) {
        if (params.debug) {
            console.log('[mock] load_filters', event.data);
        }
        event.data.on_success([]);
    });

    // make sure all Odoo events bubbling up are intercepted
    if ('intercepts' in params) {
        _.each(params.intercepts, function (cb, name) {
            intercept(widget, name, cb);
        });
    }

    // Deploy services
    var done = false;
    var servicesToDeploy = _.clone(params.services);
    if (!servicesToDeploy.ajax) {
        services.ajax = null; // use mocked ajax from mocked server
    }
    while (!done) {
        var serviceName = _.findKey(servicesToDeploy, function (Service) {
            return !_.some(Service.prototype.dependencies, function (depName) {
                return !_.has(services, depName);
            });
        });
        if (serviceName) {
            var Service = servicesToDeploy[serviceName];
            var service = services[serviceName] = new Service(widget);
            delete servicesToDeploy[serviceName];

            intercept(service, "get_session", function (event) {
                event.data.callback(session);
            });

            service.start();
        } else {
            var serviceNames = _.keys(servicesToDeploy);
            if (serviceNames.length) {
                console.warn("Non loaded services:", serviceNames);
            }
            done = true;
        }
    }

    return mockServer;
}

/**
 * performs a fields_view_get, and mocks the postprocessing done by the
 * data_manager to return an equivalent structure.
 *
 * @param {MockServer} server
 * @param {Object} params
 * @param {string} params.model
 * @returns {Object} an object with 3 keys: arch, fields and viewFields
 */
function fieldsViewGet(server, params) {
    var fieldsView = server.fieldsViewGet(params);
    // mock the structure produced by the DataManager
    fieldsView.viewFields = fieldsView.fields;
    fieldsView.fields = server.fieldsGet(params.model);
    return fieldsView;
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
 * Patch window.Date so that the time starts its flow from the provided Date.
 *
 * Usage:
 *
 *  ```
 *  var unpatchDate = testUtils.mock.patchDate(2018, 0, 10, 17, 59, 30)
 *  new window.Date(); // "Wed Jan 10 2018 17:59:30 GMT+0100 (Central European Standard Time)"
 *  ... // 5 hours delay
 *  new window.Date(); // "Wed Jan 10 2018 22:59:30 GMT+0100 (Central European Standard Time)"
 *  ...
 *  unpatchDate();
 *  new window.Date(); // actual current date time
 *  ```
 *
 * @param {integer} year
 * @param {integer} month index of the month, starting from zero.
 * @param {integer} day the day of the month.
 * @param {integer} hours the digits for hours (24h)
 * @param {integer} minutes
 * @param {integer} seconds
 * @returns {function} a callback to unpatch window.Date.
 */
function patchDate(year, month, day, hours, minutes, seconds) {
    var RealDate = window.Date;
    var actualDate = new RealDate();
    var fakeDate = new RealDate(year, month, day, hours, minutes, seconds);
    var timeInterval = actualDate.getTime() - (fakeDate.getTime());

    Date = (function (NativeDate) {
        function Date(Y, M, D, h, m, s, ms) {
            var length = arguments.length;
            if (arguments.length > 0) {
                var date = length == 1 && String(Y) === Y ? // isString(Y)
                    // We explicitly pass it through parse:
                    new NativeDate(Date.parse(Y)) :
                    // We have to manually make calls depending on argument
                    // length here
                    length >= 7 ? new NativeDate(Y, M, D, h, m, s, ms) :
                    length >= 6 ? new NativeDate(Y, M, D, h, m, s) :
                    length >= 5 ? new NativeDate(Y, M, D, h, m) :
                    length >= 4 ? new NativeDate(Y, M, D, h) :
                    length >= 3 ? new NativeDate(Y, M, D) :
                    length >= 2 ? new NativeDate(Y, M) :
                    length >= 1 ? new NativeDate(Y) :
                                  new NativeDate();
                // Prevent mixups with unfixed Date object
                date.constructor = Date;
                return date;
            } else {
                var date = new NativeDate();
                var time = date.getTime();
                time -= timeInterval;
                date.setTime(time);
                return date;
            }
        }

        // Copy any custom methods a 3rd party library may have added
        for (var key in NativeDate) {
            Date[key] = NativeDate[key];
        }

        // Copy "native" methods explicitly; they may be non-enumerable
        Date.now = NativeDate.now;
        Date.UTC = NativeDate.UTC;
        Date.prototype = NativeDate.prototype;
        Date.prototype.constructor = Date;

        // Upgrade Date.parse to handle simplified ISO 8601 strings
        Date.parse = NativeDate.parse;
        return Date;
    })(Date);

    return function () { window.Date = RealDate; };
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


return {
    addMockEnvironment: addMockEnvironment,
    fieldsViewGet: fieldsViewGet,
    intercept: intercept,
    patchDate: patchDate,
    patch: patch,
    unpatch: unpatch,
};

});
