odoo.define('web.ajax', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
const {Markup} = require('web.utils');
var time = require('web.time');
var download = require('web.download');
var contentdisposition = require('web.contentdisposition');
const { session } = require('@web/session');

var _t = core._t;

// Create the final object containing all the functions first to allow monkey
// patching them correctly if ever needed.
var ajax = {};

function _genericJsonRpc (fct_name, params, settings, fct) {
    var shadow = settings.shadow || false;
    delete settings.shadow;
    var data = {
        jsonrpc: "2.0",
        method: fct_name,
        params: params,
        id: Math.floor(Math.random() * 1000 * 1000 * 1000)
    };

    if (!shadow) {
        core.bus.trigger('rpc_request', data.id);
    }

    var xhr = fct(data);
    var result = xhr.then(function(result) {
        core.bus.trigger('rpc:result', data, result);
        if (result.error !== undefined) {
            console.debug(
                "Server application error\n",
                "Error code:", result.error.code, "\n",
                "Error message:", result.error.message, "\n",
                "Error data message:\n", result.error.data.message, "\n",
                "Error data debug:\n", result.error.data.debug
            );
            return Promise.reject({type: "server", error: result.error});
        } else {
            return result.result;
        }
    }, function() {
        //console.error("JsonRPC communication error", _.toArray(arguments));
        var reason = {
            type: 'communication',
            error: arguments[0],
            textStatus: arguments[1],
            errorThrown: arguments[2],
        };
        return Promise.reject(reason);
    });

    var rejection;
    var promise = new Promise(function (resolve, reject) {
        rejection = reject;

        result.then(function (result) {
            if (!shadow) {
                core.bus.trigger('rpc_response', data.id);
            }
            resolve(result);
        }, function (reason) {
            var type = reason.type;
            var error = reason.error;
            var textStatus = reason.textStatus;
            var errorThrown = reason.errorThrown;
            if (type === "server") {
                if (!shadow) {
                    core.bus.trigger('rpc_response', data.id);
                }
                if (error.code === 100) {
                    core.bus.trigger('invalidate_session');
                }
                reject({message: error, event: $.Event()});
            } else {
                if (!shadow) {
                    core.bus.trigger('rpc_response_failed', data.id);
                }
                var nerror = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {
                        type: "xhr"+textStatus,
                        debug: error.responseText,
                        objects: [error, errorThrown],
                        arguments: [reason || textStatus]
                    },
                };
                reject({message: nerror, event: $.Event()});
            }
        });
    });

    // FIXME: jsonp?
    /**
     * @param {Boolean} rejectError Returns an error if true. Allows you to cancel
     *                  ignored rpc's in order to unblock the ui and not display an error.
     */
    promise.abort = function (rejectError = true) {
        if (rejectError) {
            rejection({
                message: "XmlHttpRequestError abort",
                event: $.Event('abort')
            });
        }

        if (!shadow) {
            core.bus.trigger('rpc_response');
        }

        if (xhr.abort) {
            xhr.abort();
        }
    };
    promise.guardedCatch(function (reason) { // Allow promise user to disable rpc_error call in case of failure
        setTimeout(function () {
            // we want to execute this handler after all others (hence
            // setTimeout) to let the other handlers prevent the event
            if (!reason.event.isDefaultPrevented()) {
                core.bus.trigger('rpc_error', reason.message, reason.event);
            }
        }, 0);
    });
    return promise;
};

function jsonRpc(url, fct_name, params, settings) {
    settings = settings || {};
    return _genericJsonRpc(fct_name, params, settings, function(data) {
        return $.ajax(url, _.extend({}, settings, {
            url: url,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(data, time.date_to_utc),
            contentType: 'application/json'
        }));
    });
}

// helper function to make a rpc with a function name hardcoded to 'call'
function rpc(url, params, settings) {
    return jsonRpc(url, 'call', params, settings);
}

/**
 * Cooperative file download implementation, for ajaxy APIs.
 *
 * @param {Object} options
 * @param {String} [options.url] used to dynamically create a form
 * @param {Object} [options.data] data to add to the form submission. If can be used without a form, in which case a form is created from scratch. Otherwise, added to form data
 * @param {HTMLFormElement} [options.form] the form to submit in order to fetch the file
 * @param {Function} [options.success] callback in case of download success
 * @param {Function} [options.error] callback in case of request error, provided with the error body
 * @param {Function} [options.complete] called after both ``success`` and ``error`` callbacks have executed
 * @returns {boolean} a false value means that a popup window was blocked. This
 *   mean that we probably need to inform the user that something needs to be
 *   changed to make it work.
 */
function get_file(options) {
    var xhr = new XMLHttpRequest();

    var data;
    if (options.form) {
        xhr.open(options.form.method, options.form.action);
        data = new FormData(options.form);
    } else {
        xhr.open('POST', options.url);
        data = new FormData();
        _.each(options.data || {}, function (v, k) {
            data.append(k, v);
        });
    }
    if (core.csrf_token) {
        data.append('csrf_token', core.csrf_token);
    }
    // IE11 wants this after xhr.open or it throws
    xhr.responseType = 'blob';

    // onreadystatechange[readyState = 4]
    // => onload (success) | onerror (error) | onabort
    // => onloadend
    xhr.onload = function () {
        var mimetype = xhr.response.type;
        if (xhr.status === 200 && mimetype !== 'text/html') {
            // replace because apparently we send some C-D headers with a trailing ";"
            // todo: maybe a lack of CD[attachment] should be interpreted as an error case?
            var header = (xhr.getResponseHeader('Content-Disposition') || '').replace(/;$/, '');
            var filename = header ? contentdisposition.parse(header).parameters.filename : null;

            download(xhr.response, filename, mimetype);
            // not sure download is going to be sync so this may be called
            // before the file is actually fetched (?)
            if (options.success) { options.success(); }
            return true;
        }

        if (!options.error) {
            return true;
        }
        var decoder = new FileReader();
        decoder.onload = function () {
            var contents = decoder.result;

            var err;
            var doc = new DOMParser().parseFromString(contents, 'text/html');
            var nodes = doc.body.children.length === 0 ? doc.body.childNodes : doc.body.children;
            try { // Case of a serialized Odoo Exception: It is Json Parsable
                var node = nodes[1] || nodes[0];
                err = JSON.parse(node.textContent);
            } catch (_e) { // Arbitrary uncaught python side exception
                err = {
                    message: nodes.length > 1 ? nodes[1].textContent : '',
                    data: {
                        name: String(xhr.status),
                        title: nodes.length > 0 ? nodes[0].textContent : '',
                    }
                };
            }
            options.error(err);
        };
        decoder.readAsText(xhr.response);
    };
    xhr.onerror = function () {
        if (options.error) {
            options.error({
                message: _t("Something happened while trying to contact the server, check that the server is online and that you still have a working network connection."),
                data: { title: _t("Could not connect to the server") }
            });
        }
    };
    if (options.complete) {
        xhr.onloadend = function () { options.complete(); };
    }

    xhr.send(data);
    return true;
}

function post (controller_url, data) {
    var postData = new FormData();

    $.each(data, function(i,val) {
        postData.append(i, val);
    });
    if (core.csrf_token) {
        postData.append('csrf_token', core.csrf_token);
    }

    return new Promise(function (resolve, reject) {
        $.ajax(controller_url, {
            data: postData,
            processData: false,
            contentType: false,
            type: 'POST'
        }).then(resolve).fail(reject);
    });
}


/**
 * Loads a template file according to the given xmlId.
 *
 * @param {string} [xmlId] - the template xmlId
 * @param {Object} [context]
 *        additionnal rpc context to be merged with the default one
 * @param {string} [tplRoute='/web/dataset/call_kw/']
 * @returns {Deferred} resolved with an object
 *          cssLibs: list of css files
 *          cssContents: list of style tag contents
 *          jsLibs: list of JS files
 *          jsContents: list of script tag contents
 */
var loadAsset = (function () {
    var cache = {};

    var load = function loadAsset(xmlId, context, tplRoute = '/web/dataset/call_kw/') {
        if (cache[xmlId]) {
            return cache[xmlId];
        }
        context = _.extend({}, session.user_context, context);
        const params = {
            args: [xmlId, {
                debug: config.isDebug()
            }],
            kwargs: {
                context: context,
            },
        };
        if (tplRoute === '/web/dataset/call_kw/') {
            Object.assign(params, {
                model: 'ir.ui.view',
                method: 'render_public_asset',
            });
        }
        cache[xmlId] = rpc(tplRoute, params).then(function (xml) {
            var $xml = $(xml);
            return {
                cssLibs: $xml.filter('link[href]:not([type="image/x-icon"])').map(function () {
                    return $(this).attr('href');
                }).get(),
                cssContents: $xml.filter('style').map(function () {
                    return Markup($(this).html());
                }).get(),
                jsLibs: $xml.filter('script[src]').map(function () {
                    return $(this).attr('src');
                }).get(),
                jsContents: $xml.filter('script:not([src])').map(function () {
                    return Markup($(this).html());
                }).get(),
            };
        }).guardedCatch(reason => {
            reason.event.preventDefault();
            throw `Unable to render the required templates for the assets to load: ${reason.message.message}`;
        });
        return cache[xmlId];
    };

    return load;
})();

_.extend(ajax, {
    jsonRpc: jsonRpc,
    rpc: rpc,
    loadAsset: loadAsset,
    get_file: get_file,
    post: post,
});

return ajax;

});
