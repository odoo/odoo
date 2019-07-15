odoo.define('web.ajax', function (require) {
"use strict";

var config = require('web.config');
var concurrency = require('web.concurrency');
var core = require('web.core');
var time = require('web.time');
var download = require('web.download');
var contentdisposition = require('web.contentdisposition');

var _t = core._t;

// Create the final object containing all the functions first to allow monkey
// patching them correctly if ever needed.
var ajax = {};

function _genericJsonRpc (fct_name, params, settings, fct) {
    var shadow = settings.shadow || false;
    delete settings.shadow;
    if (!shadow) {
        core.bus.trigger('rpc_request');
    }

    var data = {
        jsonrpc: "2.0",
        method: fct_name,
        params: params,
        id: Math.floor(Math.random() * 1000 * 1000 * 1000)
    };
    var xhr = fct(data);
    var result = xhr.then(function(result) {
        core.bus.trigger('rpc:result', data, result);
        if (result.error !== undefined) {
            if (result.error.data.arguments[0] !== "bus.Bus not available in test mode") {
                console.debug(
                    "Server application error\n",
                    "Error code:", result.error.code, "\n",
                    "Error message:", result.error.message, "\n",
                    "Error data message:\n", result.error.data.message, "\n",
                    "Error data debug:\n", result.error.data.debug
                );
            }
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
                core.bus.trigger('rpc_response');
            }
            resolve(result);
        }, function (reason) {
            var type = reason.type;
            var error = reason.error;
            var textStatus = reason.textStatus;
            var errorThrown = reason.errorThrown;
            if (type === "server") {
                if (!shadow) {
                    core.bus.trigger('rpc_response');
                }
                if (error.code === 100) {
                    core.bus.trigger('invalidate_session');
                }
                reject({message: error, event: $.Event()});
            } else {
                if (!shadow) {
                    core.bus.trigger('rpc_response_failed');
                }
                var nerror = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {
                        type: "xhr"+textStatus,
                        debug: error.responseText,
                        objects: [error, errorThrown]
                    },
                };
                reject({message: nerror, event: $.Event()});
            }
        });
    });

    // FIXME: jsonp?
    promise.abort = function () {
        rejection({
            message: "XmlHttpRequestError abort",
            event: $.Event('abort')
        });
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
 * Load css asynchronously: fetch it from the url parameter and add a link tag
 * to <head>.
 * If the url has already been requested and loaded, the promise will resolve
 * immediately.
 *
 * @param {String} url of the css to be fetched
 * @returns {Promise} resolved when the css has been loaded.
 */
var loadCSS = (function () {
    var urlDefs = {};

    return function loadCSS(url) {
        if (url in urlDefs) {
            // nothing to do here
        } else if ($('link[href="' + url + '"]').length) {
            // the link is already in the DOM, the promise can be resolved
            urlDefs[url] = Promise.resolve();
        } else {
            var $link = $('<link>', {
                'href': url,
                'rel': 'stylesheet',
                'type': 'text/css'
            });
            urlDefs[url] = new Promise(function (resolve, reject) {
                $link.on('load', function () {
                    resolve();
                });
            });
            $('head').append($link);
        }
        return urlDefs[url];
    };
})();

var loadJS = (function () {
    var dependenciesPromise = {};

    var load = function loadJS(url) {
        // Check the DOM to see if a script with the specified url is already there
        var alreadyRequired = ($('script[src="' + url + '"]').length > 0);

        // If loadJS was already called with the same URL, it will have a registered promise indicating if
        // the script has been fully loaded. If not, the promise has to be initialized.
        // This is initialized as already resolved if the script was already there without the need of loadJS.
        if (url in dependenciesPromise) {
            return dependenciesPromise[url];
        }
        var scriptLoadedPromise = new Promise(function (resolve, reject) {
            if (alreadyRequired) {
                resolve();
            } else {
                // Get the script associated promise and returns it after initializing the script if needed. The
                // promise is marked to be resolved on script load and rejected on script error.
                var script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = url;
                script.onload = script.onreadystatechange = function() {
                    if ((script.readyState && script.readyState !== "loaded" && script.readyState !== "complete") || script.onload_done) {
                        return;
                    }
                    script.onload_done = true;
                    resolve(url);
                };
                script.onerror = function () {
                    console.error("Error loading file", script.src);
                    reject(url);
                };
                var head = document.head || document.getElementsByTagName('head')[0];
                head.appendChild(script);
            }
        });

        dependenciesPromise[url] = scriptLoadedPromise;
        return scriptLoadedPromise;
    };

    return load;
})();


/**
 * Cooperative file download implementation, for ajaxy APIs.
 *
 * Requires that the server side implements an httprequest correctly
 * setting the `fileToken` cookie to the value provided as the `token`
 * parameter. The cookie *must* be set on the `/` path and *must not* be
 * `httpOnly`.
 *
 * It would probably also be a good idea for the response to use a
 * `Content-Disposition: attachment` header, especially if the MIME is a
 * "known" type (e.g. text/plain, or for some browsers application/json
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
    data.append('token', 'dummy-because-api-expects-one');
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
            } catch (e) { // Arbitrary uncaught python side exception
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
                message: _("Something happened while trying to contact the server, check that the server is online and that you still have a working network connection."),
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
 * Loads an XML file according to the given URL and adds its associated qweb
 * templates to the given qweb engine. The function can also be used to get
 * the promise which indicates when all the calls to the function are finished.
 *
 * Note: "all the calls" = the calls that happened before the current no-args
 * one + the calls that will happen after but when the previous ones are not
 * finished yet.
 *
 * @param {string} [url] - an URL where to find qweb templates
 * @param {QWeb} [qweb] - the engine to which the templates need to be added
 * @returns {Promise}
 *          If no argument is given to the function, the promise's state
 *          indicates if "all the calls" are finished (see main description).
 *          Otherwise, it indicates when the templates associated to the given
 *          url have been loaded.
 */
var loadXML = (function () {
    // Some "static" variables associated to the loadXML function
    var isLoading = false;
    var loadingsData = [];
    var seenURLs = [];

    return function (url, qweb) {
        function _load() {
            isLoading = true;
            if (loadingsData.length) {
                // There is something to load, load it, resolve the associated
                // promise then start loading the next one
                var loadingData = loadingsData[0];
                loadingData.qweb.add_template(loadingData.url, function () {
                    // Remove from array only now so that multiple calls to
                    // loadXML with the same URL returns the right promise
                    loadingsData.shift();
                    loadingData.resolve();
                    _load();
                });
            } else {
                // There is nothing to load anymore, so resolve the
                // "all the calls" promise
                isLoading = false;
            }
        }

        // If no argument, simply returns the promise which indicates when
        // "all the calls" are finished
        if (!url || !qweb) {
            return Promise.resolve();
        }

        // If the given URL has already been seen, do nothing but returning the
        // associated promise
        if (_.contains(seenURLs, url)) {
            var oldLoadingData = _.findWhere(loadingsData, {url: url});
            return oldLoadingData ? oldLoadingData.def : Promise.resolve();
        }
        seenURLs.push(url);


        // Add the information about the new data to load: the url, the qweb
        // engine and the associated promise
        var newLoadingData = {
            url: url,
            qweb: qweb,
        };
        newLoadingData.def = new Promise(function (resolve, reject) {
            newLoadingData.resolve = resolve;
            newLoadingData.reject = reject;
        });
        loadingsData.push(newLoadingData);

        // If not already started, start the loading loop (reinitialize the
        // "all the calls" promise to an unresolved state)
        if (!isLoading) {
            _load();
        }

        // Return the promise associated to the new given URL
        return newLoadingData.def;
    };
})();

/**
 * Loads a template file according to the given xmlId.
 *
 * @param {string} [xmlId] - the template xmlId
 * @returns {Deferred} resolved with an object
 *          cssLibs: list of css files
 *          cssContents: list of style tag contents
 *          jsLibs: list of JS files
 *          jsContents: list of script tag contents
 */
var loadAsset = (function () {
    var cache = {};

    var load = function loadAsset(xmlId) {
        if (cache[xmlId]) {
            return Promise.resolve(cache[xmlId]);
        }
        var params = {
            args: [xmlId, {
                debug: config.isDebug()
            }],
            kwargs: {
                context: odoo.session_info.user_context,
            },
            method: 'render_template',
            model: 'ir.ui.view',
        };
        return rpc('/web/dataset/call_kw/ir.ui.view/render_template', params).then(function (xml) {
            var $xml = $(xml);
            cache[xmlId] = {
                cssLibs: $xml.filter('link[href]:not([type="image/x-icon"])').map(function () {
                    return $(this).attr('href');
                }).get(),
                cssContents: $xml.filter('style').map(function () {
                    return $(this).html();
                }).get(),
                jsLibs: $xml.filter('script[src]').map(function () {
                    return $(this).attr('src');
                }).get(),
                jsContents: $xml.filter('script:not([src])').map(function () {
                    return $(this).html();
                }).get(),
            };
            return cache[xmlId];
        });
    };

    return load;
})();

/**
 * Loads the given js/css libraries and asset bundles. Note that no library or
 * asset will be loaded if it was already done before.
 *
 * @param {Object} libs
 * @param {Array<string|string[]>} [libs.assetLibs=[]]
 *      The list of assets to load. Each list item may be a string (the xmlID
 *      of the asset to load) or a list of strings. The first level is loaded
 *      sequentially (so use this if the order matters) while the assets in
 *      inner lists are loaded in parallel (use this for efficiency but only
 *      if the order does not matter, should rarely be the case for assets).
 * @param {string[]} [libs.cssLibs=[]]
 *      The list of CSS files to load. They will all be loaded in parallel but
 *      put in the DOM in the given order (only the order in the DOM is used
 *      to determine priority of CSS rules, not loaded time).
 * @param {Array<string|string[]>} [libs.jsLibs=[]]
 *      The list of JS files to load. Each list item may be a string (the URL
 *      of the file to load) or a list of strings. The first level is loaded
 *      sequentially (so use this if the order matters) while the files in inner
 *      lists are loaded in parallel (use this for efficiency but only
 *      if the order does not matter).
 * @param {string[]} [libs.cssContents=[]]
 *      List of inline styles to add after loading the CSS files.
 * @param {string[]} [libs.jsContents=[]]
 *      List of inline scripts to add after loading the JS files.
 *
 * @returns {Promise}
 */
function loadLibs(libs) {
    var mutex = new concurrency.Mutex();
    mutex.exec(function () {
        var defs = [];
        var cssLibs = [libs.cssLibs || []];  // Force loading in parallel
        defs.push(_loadArray(cssLibs, ajax.loadCSS).then(function () {
            if (libs.cssContents && libs.cssContents.length) {
                $('head').append($('<style/>', {
                    html: libs.cssContents.join('\n'),
                }));
            }
        }));
        defs.push(_loadArray(libs.jsLibs || [], ajax.loadJS).then(function () {
            if (libs.jsContents && libs.jsContents.length) {
                $('head').append($('<script/>', {
                    html: libs.jsContents.join('\n'),
                }));
            }
        }));
        return Promise.all(defs);
    });
    mutex.exec(function () {
        return _loadArray(libs.assetLibs || [], function (xmlID) {
            return ajax.loadAsset(xmlID).then(function (asset) {
                return ajax.loadLibs(asset);
            });
        });
    });

    function _loadArray(array, loadCallback) {
        var _mutex = new concurrency.Mutex();
        array.forEach(function (urlData) {
            _mutex.exec(function () {
                if (typeof urlData === 'string') {
                    return loadCallback(urlData);
                }
                return Promise.all(urlData.map(loadCallback));
            });
        });
        return _mutex.getUnlockedDef();
    }

    return mutex.getUnlockedDef();
}

_.extend(ajax, {
    jsonRpc: jsonRpc,
    rpc: rpc,
    loadCSS: loadCSS,
    loadJS: loadJS,
    loadXML: loadXML,
    loadAsset: loadAsset,
    loadLibs: loadLibs,
    get_file: get_file,
    post: post,
});

return ajax;

});
