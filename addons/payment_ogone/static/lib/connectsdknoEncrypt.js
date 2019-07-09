(function (global) {
    var connectsdk = {}, modules = {};

    /* SDK internal function */
    connectsdk.define = function (module, dependencies, fn) {
        if (dependencies && dependencies.length) {
            for (var i = 0; i < dependencies.length; i++) {
                dependencies[i] = modules[dependencies[i]];
            }
        }
        modules[module] = fn.apply(this, dependencies || []);
    };

    // Export `connectsdk` based on environment.
    global.connectsdk = connectsdk;

    if (typeof exports !== 'undefined') {
        exports.connectsdk = connectsdk;
    }

    connectsdk.define('connectsdk.core', [], function () {
        return connectsdk;
    });

    // use require.js if available otherwise we use our own
    if (typeof define === 'undefined') {
        global.define = connectsdk.define;
    }
} (typeof window === 'undefined' ? this : window));

// (re)define core
define("connectsdk.core", [], function () {
    var global = typeof window === 'undefined' ? this : window;
    var connectsdk = {};
    global.connectsdk = connectsdk;
    if (typeof exports !== 'undefined') {
        exports.connectsdk = connectsdk;
    }
    return connectsdk;
});

define('connectsdk.promise', ['connectsdk.core'], function(turing) {
	function PromiseModule(global) {
		/**
		 * The Promise class.
		 */
		function Promise(singleton) {
			var self = this;
			this.pending = [];

			/**
			 * Resolves a promise.
			 *
			 * @param {Object} A value
			 */
			this.resolve = function(result) {
				self.complete('resolve', result);
			},

			/**
			 * Rejects a promise.
			 *
			 * @param {Object} A value
			 */
			this.reject = function(result) {
				self.complete('reject', result);
			};

			if (singleton) {
				this.isSingleton = true;
			}
		}


		Promise.prototype = {
			/**
			 * Adds a success and failure handler for completion of this Promise object.
			 *
			 * @param {Function} success The success handler
			 * @param {Function} success The failure handler
			 * @returns {Promise} `this`
			 */
			then : function(success, failure) {
				this.pending.push({
					resolve : success,
					reject : failure
				});
				return this;
			},

			/**
			 * Runs through each pending 'thenable' based on type (resolve, reject).
			 *
			 * @param {String} type The thenable type
			 * @param {Object} result A value
			 */
			complete : function(type, result) {
				while (this.pending[0]) {
					this.pending.shift()[type](result);
				}
			}
		};

		global.Promise = Promise;
	}
	PromiseModule(connectsdk);

	return connectsdk.Promise;
});
define('connectsdk.net', ['connectsdk.core'], function(connectsdk) {
  var net = {};

  /**
    * Ajax request options:
    *
    *   - `method`: {String} HTTP method - GET, POST, etc.
    *   - `success`: {Function} A callback to run when a request is successful
    *   - `error`: {Function} A callback to run when the request fails
    *   - `asynchronous`: {Boolean} Defaults to asynchronous
    *   - `postBody`: {String} The HTTP POST body
    *   - `contentType`: {String} The content type of the request, default is `application/x-www-form-urlencoded`
    *
    */

  /**
    * Removes leading and trailing whitespace.
    * @param {String}
    * @return {String}
    */
  var trim = ''.trim
    ? function(s) { return s.trim(); }
    : function(s) { return s.replace(/^\s\s*/, '').replace(/\s\s*$/, ''); };

  function xhr() {
    if (typeof XMLHttpRequest !== 'undefined' && (window.location.protocol !== 'file:' || !window.ActiveXObject)) {
      return new XMLHttpRequest();
    } else {
      try {
        return new ActiveXObject('Msxml2.XMLHTTP.6.0');
      } catch(e) { }
      try {
        return new ActiveXObject('Msxml2.XMLHTTP.3.0');
      } catch(e) { }
      try {
        return new ActiveXObject('Msxml2.XMLHTTP');
      } catch(e) { }
    }
    return false;
  }

  function successfulRequest(request) {
    return (request.status >= 200 && request.status < 300) ||
        request.status == 304 ||
        (request.status == 0 && request.responseText);
  }

  /**
    * Serialize JavaScript for HTTP requests.
    *
    * @param {Object} object An Array or Object
    * @returns {String} A string suitable for a GET or POST request
    */
  net.serialize = function(object) {
    if (!object) return;

    if (typeof object === 'string') {
      return object;
    }

    var results = [];
    for (var key in object) {
      results.push(encodeURIComponent(key) + '=' + encodeURIComponent(object[key]));
    }
    return results.join('&');
  };

  /**
    * JSON.parse support can be inferred using `connectsdk.detect('JSON.parse')`.
    */
  //connectsdk.addDetectionTest('JSON.parse', function() {
  //  return window.JSON && window.JSON.parse;
  //});

  /**
    * Parses JSON represented as a string.
    *
    * @param {String} string The original string
    * @returns {Object} A JavaScript object
    */
  net.parseJSON = function(string) {
    if (typeof string !== 'string' || !string) return null;
    string = trim(string);
    /*
    return connectsdk.detect('JSON.parse') ?
      window.JSON.parse(string) :
      (new Function('return ' + string))();
    */
    return window.JSON.parse(string);
  };

  /**
    * Parses XML represented as a string.
    *
    * @param {String} string The original string
    * @returns {Object} A JavaScript object
    */
  if (window.DOMParser) {
    net.parseXML = function(text) {
      return new DOMParser().parseFromString(text, 'text/xml');
    };
  } else {
    net.parseXML = function(text) {
      var xml = new ActiveXObject('Microsoft.XMLDOM');
      xml.async = 'false';
      xml.loadXML(text);
      return xml;
    };
  }

  /**
    * Creates an Ajax request.  Returns an object that can be used
    * to chain calls.  For example:
    *
    *      $t.post('/post-test')
    *        .data({ key: 'value' })
    *        .end(function(res) {
    *          assert.equal('value', res.responseText);
    *        });
    *
    *      $t.get('/get-test')
    *        .set('Accept', 'text/html')
    *        .end(function(res) {
    *          assert.equal('Sample text', res.responseText);
    *        });
    *
    * The available chained methods are:
    *
    * `set` -- set a HTTP header
    * `data` -- the postBody
    * `end` -- send the request over the network, and calls your callback with a `res` object
    * `send` -- sends the request and calls `data`: `.send({ data: value }, function(res) { });`
    *
    * @param {String} The URL to call
    * @param {Object} Optional settings
    * @returns {Object} A chainable object for further configuration
    */
  function ajax(url, options) {
    var request = xhr(),
        promise,
        then,
        response = {},
        chain;
    if (connectsdk.Promise) {
      promise = new connectsdk.Promise();
    }


    function respondToReadyState(readyState) {
      if (request.readyState == 4) {
        var contentType = request.mimeType || request.getResponseHeader('content-type') || '';

        response.status = request.status;
        response.responseText = request.responseText;
        if (/json/.test(contentType)) {
          response.responseJSON = net.parseJSON(request.responseText);
        } else if (/xml/.test(contentType)) {
          response.responseXML = net.parseXML(request.responseText);
      	}

        response.success = successfulRequest(request);

        if (options.callback) {
          return options.callback(response, request);
        }

        if (response.success) {
          if (options.success) options.success(response, request);
          if (promise) promise.resolve(response, request);
        } else {
          if (options.error) options.error(response, request);
          if (promise) promise.reject(response, request);
        }
      }
    }

    // Set the HTTP headers
    function setHeaders() {
      var defaults = {
        'Accept': 'text/javascript, application/json, text/html, application/xml, text/xml, */*',
        'Content-Type': 'application/json'
      };

      /**
       * Merge headers with defaults.
       */
      for (var name in defaults) {
        if (!options.headers.hasOwnProperty(name))
          options.headers[name] = defaults[name];
      }
      for (var name in options.headers) {
        request.setRequestHeader(name, options.headers[name]);
      }

    }

    if (typeof options === 'undefined') options = {};

    options.method = options.method ? options.method.toLowerCase() : 'get';
    options.asynchronous = options.asynchronous || true;
    options.postBody = options.postBody || '';
    request.onreadystatechange = respondToReadyState;
    request.open(options.method, url, options.asynchronous);

    options.headers = options.headers || {};
    if (options.contentType) {
      options.headers['Content-Type'] = options.contentType;
    }

    if (typeof options.postBody !== 'string') {
      // Serialize JavaScript
      options.postBody = net.serialize(options.postBody);
    }

    // setHeaders();

    function send() {
      try {
      	setHeaders();
        request.send(options.postBody);
      } catch (e) {
        if (options.error) {
          options.error();
        }
      }
    }

    chain = {
      set: function(key, value) {
        options.headers[key] = value;
        return chain;
      },

      send: function(data, callback) {
        options.postBody = net.serialize(data);
        options.callback = callback;
        send();
        return chain;
      },

      end: function(callback) {
        options.callback = callback;
        send();
        return chain;
      },

      data: function(data) {
        options.postBody = net.serialize(data);
        return chain;
      },

      then: function() {
        chain.end();
        if (promise) promise.then.apply(promise, arguments);
        return chain;
      }
    };

    return chain;
  }

  function JSONPCallback(url, success, failure) {
    var self = this;
    this.url = url;
    this.methodName = '__connectsdk_jsonp_' + parseInt(new Date().getTime());
    this.success = success;
    this.failure = failure;

    function runCallback(json) {
      self.success(json);
      self.teardown();
    }

    window[this.methodName] = runCallback;
  }

  JSONPCallback.prototype.run = function() {
    this.scriptTag = document.createElement('script');
    this.scriptTag.id = this.methodName;
    this.scriptTag.src = this.url.replace('{callback}', this.methodName);
    var that = this;
    this.scriptTag.onerror = function() {
    	that.failure();
    };
    document.body.appendChild(this.scriptTag);
  };

  JSONPCallback.prototype.teardown = function() {
    window[this.methodName] = null;
    try {
    	delete window[this.methodName];
    } catch (e) {}
    if (this.scriptTag) {
      document.body.removeChild(this.scriptTag);
    }
  };

  /**
   * An Ajax GET request.
   *
   *      $t.get('/get-test')
   *        .set('Accept', 'text/html')
   *        .end(function(res) {
   *          assert.equal('Sample text', res.responseText);
   *        });
   *
   * @param {String} url The URL to request
   * @param {Object} options The Ajax request options
   * @returns {Object} A chainable object for further configuration
   */
  net.get = function(url, options) {
    if (typeof options === 'undefined') options = {};
    options.method = 'get';
    return ajax(url, options);
  };

  /**
   * An Ajax POST request.
   *
   *      $t.post('/post-test')
   *        .data({ key: 'value' })
   *        .end(function(res) {
   *          assert.equal('value', res.responseText);
   *        });
   *
   * @param {String} url The URL to request
   * @param {Object} options The Ajax request options (`postBody` may come in handy here)
   * @returns {Object} An object for further chaining with promises
   */
  net.post = function(url, options) {
    if (typeof options === 'undefined') options = {};
    options.method = 'post';
    return ajax(url, options);
  };

  /**
   * A jsonp request.  Example:
   *
   *     var url = 'http://feeds.delicious.com/v1/json/';
   *     url += 'alex_young/javascript?callback={callback}';
   *
   *     connectsdk.net.jsonp(url, {
   *       success: function(json) {
   *         console.log(json);
   *       }
   *     });
   *
   * @param {String} url The URL to request
   */
  net.jsonp = function(url, options) {
    if (typeof options === 'undefined') options = {};
    var callback = new JSONPCallback(url, options.success, options.failure);
    callback.run();
  };

  /**
    * The Ajax methods are mapped to the `connectsdk` object:
    *
    *      connectsdk.get();
    *      connectsdk.post();
    *      connectsdk.json();
    *
    */
  connectsdk.get = net.get;
  connectsdk.post = net.post;
  connectsdk.jsonp = net.jsonp;

  net.ajax = ajax;
  connectsdk.net = net;
  return net;
});
define("connectsdk.Util", ["connectsdk.core"], function (connectsdk) {

	// Create a singleton from Util so the same util function can be used in different modules
	var Util = (function () {
		var instance;

		function createInstance() {
			// private variables to use in the public methods
			var applePayPaymentProductId = 302;
			var googlePayPaymentProductId = 320;
			var bancontactPaymentProductId = 3012;

			return {
				applePayPaymentProductId: applePayPaymentProductId,
				googlePayPaymentProductId: googlePayPaymentProductId,
				bancontactPaymentProductId: bancontactPaymentProductId,
				getMetadata: function () {
					return {
						screenSize: window.innerWidth + "x" + window.innerHeight,
						platformIdentifier: window.navigator.userAgent,
						sdkIdentifier: ((document.GC && document.GC.rppEnabledPage) ? 'rpp-' : '') + 'JavaScriptClientSDK/v3.13.2',
						sdkCreator: 'Ingenico'
					};
				},
				collectDeviceInformation: function () {
					return {
						"timezoneOffsetUtcMinutes": new Date().getTimezoneOffset(),
						"locale": navigator.language,
						"browserData": {
							"javaScriptEnabled": true,
							"javaEnabled": navigator.javaEnabled(),
							"colorDepth": screen.colorDepth,
							"screenHeight": screen.height,
							"screenWidth": screen.width,
							"innerHeight": window.innerHeight,
							"innerWidth": window.innerWidth
						}
					};
				},
				base64Encode: function (data) {
					if (typeof data === "object") {
						try {
							data = JSON.stringify(data);
						} catch (e) {
							throw "data must be either a String or a JSON object";
						}
					}

					var b64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
					var o1, o2, o3, h1, h2, h3, h4, bits, i = 0, ac = 0, enc = '', tmp_arr = [];

					if (!data) {
						return data;
					}

					do {// pack three octets into four hexets
						o1 = data.charCodeAt(i++);
						o2 = data.charCodeAt(i++);
						o3 = data.charCodeAt(i++);

						bits = o1 << 16 | o2 << 8 | o3;

						h1 = bits >> 18 & 0x3f;
						h2 = bits >> 12 & 0x3f;
						h3 = bits >> 6 & 0x3f;
						h4 = bits & 0x3f;

						// use hexets to index into b64, and append result to encoded string
						tmp_arr[ac++] = b64.charAt(h1) + b64.charAt(h2) + b64.charAt(h3) + b64.charAt(h4);
					} while (i < data.length);

					enc = tmp_arr.join('');

					var r = data.length % 3;

					return (r ? enc.slice(0, r - 3) : enc) + '==='.slice(r || 3);
				},
				filterOutProductsThatAreNotSupportedInThisBrowser: function (json) {
					for (var i = json.paymentProducts.length - 1, il = 0; i >= il; i--) {
						var product = json.paymentProducts[i];
						if (product && this.paymentProductsThatAreNotSupportedInThisBrowser.indexOf(product.id) > -1) {
							json.paymentProducts.splice(i, 1);
						}
					}
				},
				paymentProductsThatAreNotSupportedInThisBrowser: [applePayPaymentProductId]
			}
		}

		return {
			getInstance: function () {
				if (!instance) {
					instance = createInstance();
				}
				return instance;
			}
		};
	})();

	connectsdk.Util = Util;
	return Util;
});

define("connectsdk.GooglePay", ["connectsdk.core", "connectsdk.promise", "connectsdk.Util"], function (connectsdk, Promise, Util) {

    var _util = Util.getInstance();
    var _C2SCommunicator = null;
    var _paymentProductSpecificInputs = null;
    var _context = null;
    var _gateway = null;
    var _networks = null;
    var paymentsClient = null;

    // Only base is needed to trigger isReadyToPay
    var _getBaseCardPaymentMethod = function () {
        return {
            type: 'CARD',
            parameters: {
                allowedAuthMethods: ["PAN_ONLY", "CRYPTOGRAM_3DS"],
                allowedCardNetworks: _networks
            }
        }
    };

    var _getTokenizationSpecification = function () {
        return {
            type: 'PAYMENT_GATEWAY',
            parameters: {
                'gateway': _gateway,
                'gatewayMerchantId': _paymentProductSpecificInputs.googlePay.gatewayMerchantId
            }
        }
    };

    // To prefetch payment data we need base + tokenizationSpecification
    var _getCardPaymentMethod = function () {
        return Object.assign(
            {},
            _getBaseCardPaymentMethod(),
            {
                tokenizationSpecification: _getTokenizationSpecification()
            }
        );
    };

    var _getTransactionInfo = function () {
        return {
            "totalPriceStatus": "NOT_CURRENTLY_KNOWN",
            "currencyCode": _context.currency
        };
    };

    var _getMerchantInfo = function () {
        return {
            "merchantName": _paymentProductSpecificInputs.googlePay.merchantName
        };
    };

    var _getGooglePaymentDataRequest = function () {
        return {
            apiVersion: 2,
            apiVersionMinor: 0,
            allowedPaymentMethods: [_getBaseCardPaymentMethod()]
        };
    };

    var _getGooglePaymentDataRequestForPrefetch = function () {
        // transactionInfo must be set but does not affect cache
        return {
            apiVersion: 2,
            apiVersionMinor: 0,
            allowedPaymentMethods: [_getCardPaymentMethod()],
            transactionInfo: _getTransactionInfo(),
            merchantInfo: _getMerchantInfo()
        };
    };

    function _getGooglePaymentsClient() {
        if (paymentsClient === null) {
            var googlePayEnvironment = 'TEST';
            if (_context.environment === 'PROD') {
                googlePayEnvironment = 'PROD';
            }
            if (window.google) {
                paymentsClient = new google.payments.api.PaymentsClient({environment: googlePayEnvironment});
            } else {
                console.error("The Google Pay API script was not loaded https://developers.google.com/pay/api/web/guides/tutorial#js-load");
            }
        }
        return paymentsClient;
    }

    /**
     * Prefetch payment data to improve performance
     *
     * @see {@link https://developers.google.com/pay/api/web/reference/client#prefetchPaymentData|prefetchPaymentData()}
     */
    function prefetchGooglePaymentData() {
        var paymentDataRequest = _getGooglePaymentDataRequestForPrefetch();

        var paymentsClient = _getGooglePaymentsClient();

        // Prefetching is only effective when all information is provided
        if (_paymentProductSpecificInputs.googlePay.gatewayMerchantId &&
            _paymentProductSpecificInputs.googlePay.merchantName) {
            paymentsClient.prefetchPaymentData(paymentDataRequest);
        } else {
            console.warn("Prefetching payment data was not triggered because of missing information. " +
                "gatewayMerchantId: " + _paymentProductSpecificInputs.googlePay.gatewayMerchantId +
                ", merchantName: " + _paymentProductSpecificInputs.googlePay.merchantName)
        }
    }

    var GooglePay = function (C2SCommunicator) {
        _C2SCommunicator = C2SCommunicator;
        this.isGooglePayAvailable = function (context, paymentProductSpecificInputs, googlePayData) {
            _context = context;
            _paymentProductSpecificInputs = paymentProductSpecificInputs;
            if (googlePayData && googlePayData.networks) {
                _gateway = googlePayData.gateway;
                _networks = googlePayData.networks;
            } else {
                _gateway = "ingenicoglobalcollect";
                _networks = googlePayData;
            }
            var promise = new Promise();
            // This setTimeout is essential to make the following (not fully asynchronous) code work in a promise way in all scenarios. (not needed in happy flow)
            // The SDK has it's only PolyFill for the promise which is not feature complete.
            setTimeout(function () {
                if (_networks && _networks.length > 0) {
                    var paymentsClient = _getGooglePaymentsClient();
                    if (!paymentsClient) {
                        _util.paymentProductsThatAreNotSupportedInThisBrowser.push(_util.googlePayPaymentProductId);
                        promise.reject("The Google Pay API script was not loaded https://developers.google.com/pay/api/web/guides/tutorial#js-load");
                    } else {
                        paymentsClient.isReadyToPay(_getGooglePaymentDataRequest())
                            .then(function (response) {
                                promise.resolve(response);

                                prefetchGooglePaymentData();
                            })
                            .catch(function () {
                                _util.paymentProductsThatAreNotSupportedInThisBrowser.push(_util.googlePayPaymentProductId);
                                promise.reject('failed to run isReadyToPay() with Google Pay API');
                            });
                    }
                } else {
                    _util.paymentProductsThatAreNotSupportedInThisBrowser.push(_util.googlePayPaymentProductId);
                    promise.reject('There are no product networks available');
                }
            }, 0);
            return promise;
        };

        this.isMerchantIdProvided = function (paymentProductSpecificInputs) {
            if (paymentProductSpecificInputs.googlePay.merchantId) {
                return paymentProductSpecificInputs.googlePay.merchantId;
            } else {
                _util.paymentProductsThatAreNotSupportedInThisBrowser.push(_util.googlePayPaymentProductId);
                return false;
            }
        }
    };
    connectsdk.GooglePay = GooglePay;
    return GooglePay;
});

define("connectsdk.PublicKeyResponse", ["connectsdk.core"], function(connectsdk) {

	var PublicKeyResponse = function(json) {
		this.json = json;
		this.keyId = json.keyId;
		this.publicKey = json.publicKey;
	};

	connectsdk.PublicKeyResponse = PublicKeyResponse;
	return PublicKeyResponse;
});
define("connectsdk.C2SCommunicatorConfiguration", ["connectsdk.core"], function (connectsdk) {

    var C2SCommunicatorConfiguration = function (sessionDetails, apiVersion) {
        this.endpoints = {
            PROD: {
                EU: {
                    API: "https://ams1.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay1.secured-by-ingenico.com"
                },
                US: {
                    API: "https://us.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay2.secured-by-ingenico.com"
                },
                AMS: {
                    API: "https://ams2.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay3.secured-by-ingenico.com"
                },
                PAR: {
                    API: "https://par.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay4.secured-by-ingenico.com"
                }
            },
            PREPROD: {
                EU: {
                    API: "https://ams1.preprod.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay1.preprod.secured-by-ingenico.com"
                },
                US: {
                    API: "https://us.preprod.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay2.preprod.secured-by-ingenico.com"
                },
                AMS: {
                    API: "https://ams2.preprod.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay3.preprod.secured-by-ingenico.com"
                },
                PAR: {
                    API: "https://par-preprod.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay4.preprod.secured-by-ingenico.com"
                }
            },
            SANDBOX: {
                EU: {
                    API: "https://ams1.sandbox.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay1.sandbox.secured-by-ingenico.com"
                },
                US: {
                    API: "https://us.sandbox.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay2.sandbox.secured-by-ingenico.com"
                },
                AMS: {
                    API: "https://ams2.sandbox.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay3.sandbox.secured-by-ingenico.com"
                },
                PAR: {
                    API: "https://par.sandbox.api-ingenico.com/client/v1",
                    ASSETS: "https://assets.pay4.sandbox.secured-by-ingenico.com"
                }
            }

            // Non public settings. Only needed in GC development environment. Do not use
            // these, they will not work outside GC.
            ,
            INTEGRATION: {
                EU: {
                    API: "https://int-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.int-test-rpp.gcsip.nl:4443"
                },
                US: {
                    API: "https://int-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.int-test-rpp.gcsip.nl:4443"
                },
                AMS: {
                    API: "https://int-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.int-test-rpp.gcsip.nl:4443"
                },
                PAR: {
                    API: "https://int-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.int-test-rpp.gcsip.nl:4443"
                }
            },
            DEV_NAMI: {
                EU: {
                    API: "https://nami-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.nami-test-rpp.gcsip.nl:4443"
                },
                US: {
                    API: "https://nami-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.nami-test-rpp.gcsip.nl:4443"
                },
                AMS: {
                    API: "https://nami-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.nami-test-rpp.gcsip.nl:4443"
                },
                PAR: {
                    API: "https://nami-test-api.gcsip.nl:4443/client/v1",
                    ASSETS: "https://assets.nami-test-rpp.gcsip.nl:4443"
                }
            },
            DEV_ISC: {
                EU: {
                    API: "//api.gc-dev.isaac.local/client/v1",
                    ASSETS: "//rpp.gc-dev.isaac.local"
                },
                US: {
                    API: "//api.gc-ci-dev.isaac.local/client/v1",
                    ASSETS: "//rpp.gc-ci-dev.isaac.local"
                },
                AMS: {
                    API: "//api.gc-dev.isaac.local/client/v1",
                    ASSETS: "//rpp.gc-dev.isaac.local"
                },
                PAR: {
                    API: "//api.gc-dev.isaac.local/client/v1",
                    ASSETS: "//rpp.gc-dev.isaac.local"
                }
            }
        };

        // clientSessionID, assetBaseUrl and apiBaseUrl are deprecated but still may be used. Here we check for presense of new variables, if they dont exist... Use the old variables.
        if (!sessionDetails.clientSessionId) {
            sessionDetails.clientSessionId = sessionDetails.clientSessionID;
        } else if (sessionDetails.clientSessionID) {
            throw new Error("You cannot use both the clientSessionId and the clientSessionID at the same time, please use the clientSessionId only.");
        }
        if (!sessionDetails.assetUrl) {
            sessionDetails.assetUrl = sessionDetails.assetsBaseUrl
        } else if (sessionDetails.assetsBaseUrl) {
            throw new Error("You cannot use both the assetUrl and the assetsBaseUrl at the same time, please use the assetUrl only.");
        }
        if (!sessionDetails.clientApiUrl) {
            sessionDetails.clientApiUrl = sessionDetails.apiBaseUrl
        } else if (sessionDetails.apiBaseUrl) {
            throw new Error("You cannot use both the clientApiUrl and the apiBaseUrl at the same time, please use the clientApiUrl only.");
        }

        this.clientSessionId = sessionDetails.clientSessionId;
        this.customerId = sessionDetails.customerId;

        // can be removed in a newer version of the SDK from this line
        if (sessionDetails.region && !sessionDetails.clientApiUrl) {
            // use regions; old stuff
            console.warn("Using regions is deprecated, switch to clientApiUrl");
            this.clientApiUrl = this.endpoints[sessionDetails.environment][sessionDetails.region].API;
            this.assetUrl = this.endpoints[sessionDetails.environment][sessionDetails.region].ASSETS;
        } else {
            // till this line; normal behaviour is below
            // ignore the region here
            this.clientApiUrl = sessionDetails.clientApiUrl;
            this.assetUrl = sessionDetails.assetUrl;
            if (!this.clientApiUrl) {
                throw new Error("This version of the connectSDK requires an clientApiUrl, which you did not provide.");
            }
            if (!this.assetUrl) {
                throw new Error("This version of the connectSDK requires an assetUrl, which you did not provide.");
            }

            // now that the clientApiUrl is set check when if the api version is set in the URL, its the correct version break if not.
            if (this.clientApiUrl.indexOf("//") === -1) {
                throw new Error("A valid URL is required for the clientApiUrl, you provided '" + this.clientApiUrl + "'");
            }
            var tester = this.clientApiUrl.split("/"); // [0] = (http(s): || "") , [1] = "", [2] = "host:port", [3+] = path
            if (tester[0] !== "" && tester[0].indexOf("http") !== 0) {
                throw new Error("A valid URL is required for the clientApiUrl, you provided '" + this.clientApiUrl + "'");
            }
            // if you cannot provide an URL that starts with (http(s)::)// and want an error: please provide a PR :)

            var path = tester.splice(3).join("/"); // the path (if no path; path = "").
            if (!path) { //If path == ""
                this.clientApiUrl += "/" + apiVersion;
            } else if (path === 'client') { //If path == client
                this.clientApiUrl += "/" + apiVersion.split('/')[1];
            } else if (path.indexOf(apiVersion) !== 0 || path.length !== apiVersion.length) {
                throw new Error("This version of the connectSDK is only compatible with " + apiVersion + ", you supplied: '" + path + "'");
            }
        }
    };
    connectsdk.C2SCommunicatorConfiguration = C2SCommunicatorConfiguration;
    return C2SCommunicatorConfiguration;
});
define("connectsdk.IinDetailsResponse", ["connectsdk.core", "connectsdk.promise"], function(connectsdk, Promise) {

	var IinDetailsResponse = function () {
		this.status = '';
		this.countryCode = '';
		this.paymentProductId = '';
		this.isAllowedInContext = '';
		this.coBrands = [];
	};
	connectsdk.IinDetailsResponse = IinDetailsResponse;
	return IinDetailsResponse;
});
define("connectsdk.C2SCommunicator", ["connectsdk.core", "connectsdk.promise", "connectsdk.net", "connectsdk.Util", "connectsdk.PublicKeyResponse", "connectsdk.IinDetailsResponse", "connectsdk.GooglePay"], function (connectsdk, Promise, Net, Util, PublicKeyResponse, IinDetailsResponse, GooglePay) {
	var C2SCommunicator = function (c2SCommunicatorConfiguration, paymentProduct) {
		var _c2SCommunicatorConfiguration = c2SCommunicatorConfiguration;
		var _util = Util.getInstance();
		var _cache = {};
		var _providedPaymentProduct = paymentProduct;
		var that = this;
		var _GooglePay = new GooglePay(that);

		var _mapType = {
			"expirydate": "tel",
			"string": "text",
			"numericstring": "tel",
			"integer": "number",
			"expirationDate": "tel"
		};

		var formatUrl = function (url) {
			return (url && endsWith(url, '/')) ? url : url + '/';
		};

		var formatImageUrl = function(url, imageUrl) {
			url = formatUrl(url);
			// _cleanJSON can be called multiple times with the same data (which is cached between calls).
			// Don't prepend the url after the first time.
			if (startsWith(imageUrl, url)) {
				return imageUrl;
			}
			return url + imageUrl;
		};

		var startsWith = function(string, prefix) {
			return string.indexOf(prefix) === 0;
		};

		var endsWith = function(string, suffix) {
			return string.indexOf(suffix, string.length - suffix.length) !== -1;
		};

		var _cleanJSON = function (json, url) {
			for (var i = 0, il = json.fields.length; i < il; i++) {
				var field = json.fields[i];
				field.type = (field.displayHints && field.displayHints.obfuscate) ? "password" : _mapType[field.type];

				// helper code for templating tools like Handlebars
				for (validatorKey in field.dataRestrictions.validators) {
					field.validators = field.validators || [];
					field.validators.push(validatorKey);
				}
				if (field.displayHints && field.displayHints.formElement && field.displayHints.formElement.type === 'list') {
					field.displayHints.formElement.list = true;
				}

				// full image paths
				if (field.displayHints && field.displayHints.tooltip && field.displayHints.tooltip.image) {
					field.displayHints.tooltip.image = formatImageUrl(url, field.displayHints.tooltip.image);
				}
			}
			// The server orders in a different way, so we apply the sortorder
			json.fields.sort(function (a, b) {
				if (a.displayHints.displayOrder < b.displayHints.displayOrder) {
					return -1;
				}
				return 1;
			});
			// set full image path
			json.displayHints.logo = formatImageUrl(url, json.displayHints.logo);
			return json;
		};

		var _extendLogoUrl = function (json, url, postfix) {
			for (var i = 0, il = json["paymentProduct" + postfix].length; i < il; i++) {
				var product = json["paymentProduct" + postfix][i];
				product.displayHints.logo = formatImageUrl(url, product.displayHints.logo);
			}
			json["paymentProduct" + postfix].sort(function (a, b) {
				if (a.displayHints.displayOrder < b.displayHints.displayOrder) {
					return -1;
				}
				return 1;
			});
			return json;
		};

		var _isPaymentProductInList = function (list, paymentProductId) {
			for (var i = list.length - 1, il = 0; i >= il; i--) {
				var product = list[i];
				if (product && (product.id === paymentProductId)) {
					return true;
				}
			}
			return false;
		};

        var _getGooglePayData = function (list, paymentProductId) {
            for (var i = list.length - 1, il = 0; i >= il; i--) {
                var product = list[i];
                if (product && (product.id === paymentProductId)) {
                    return product.paymentProduct320SpecificData;
                }
            }
            return false;
        };

		var metadata = _util.getMetadata();

		this.getBasicPaymentProducts = function (context, paymentProductSpecificInputs) {
			var cacheKeyLocale= context.locale ? context.locale + "_" : '';
			paymentProductSpecificInputs = paymentProductSpecificInputs || {};
			var promise = new Promise()
				, cacheBust = new Date().getTime()
				, cacheKey = "getPaymentProducts-" + context.totalAmount + "_" + context.countryCode + "_"
					+ cacheKeyLocale + context.isRecurring + "_" + context.currency + "_" + JSON.stringify(paymentProductSpecificInputs);

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				var urlParameterLocale = context.locale ? "&locale=" + context.locale: '';
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId
					+ "/products" + "?countryCode=" + context.countryCode + "&isRecurring=" + context.isRecurring
					+ "&amount=" + context.totalAmount + "&currencyCode=" + context.currency
					+ "&hide=fields" + urlParameterLocale + "&cacheBust=" + cacheBust)
					.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							var json = _extendLogoUrl(res.responseJSON, _c2SCommunicatorConfiguration.assetUrl, "s");
							if (_isPaymentProductInList(json.paymentProducts, _util.googlePayPaymentProductId)) {
								if (_GooglePay.isMerchantIdProvided(paymentProductSpecificInputs)) {
									var googlePayData = _getGooglePayData(json.paymentProducts, _util.googlePayPaymentProductId);
									_GooglePay.isGooglePayAvailable(context, paymentProductSpecificInputs, googlePayData).then(function (isGooglePayAvailable) {
										_util.filterOutProductsThatAreNotSupportedInThisBrowser(json);
										if (json.paymentProducts.length === 0) {
											promise.reject('No payment products available');
										}
										_cache[cacheKey] = json;
										promise.resolve(json);
									}, function () {
										_util.filterOutProductsThatAreNotSupportedInThisBrowser(json);
										if (json.paymentProducts.length === 0) {
											promise.reject('No payment products available');
										}
										_cache[cacheKey] = json;
										promise.resolve(json);
									});
								} else {
									//GooglePay does not have merchantId
									_util.filterOutProductsThatAreNotSupportedInThisBrowser(json);
									console.warn('You have not provided a merchantId for Google Pay, you can set this in the paymentProductSpecificInputs object');
									promise.resolve(json);
								}
							} else {
								_util.filterOutProductsThatAreNotSupportedInThisBrowser(json);
								if (json.paymentProducts.length === 0) {
									promise.reject('No payment products available');
								}
								_cache[cacheKey] = json;
								promise.resolve(json);
							}
						} else {
							promise.reject('failed to retrieve Basic Payment Products', res);
						}
					});
			}
			return promise;
		};

		this.getBasicPaymentProductGroups = function (context) {
			var cacheKeyLocale = context.locale ? context.locale + "_" : '';
			var promise = new Promise()
				, cacheBust = new Date().getTime()
				, cacheKey = "getPaymentProductGroups-" + context.totalAmount + "_" + context.countryCode + "_"
					+ cacheKeyLocale + context.isRecurring + "_" + context.currency;

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				var urlParameterLocale = context.locale ? "&locale=" + context.locale: '';
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId
					+ "/productgroups" + "?countryCode=" + context.countryCode + "&isRecurring=" + context.isRecurring
					+ "&amount=" + context.totalAmount + "&currencyCode=" + context.currency
					+ "&hide=fields" + urlParameterLocale + "&cacheBust=" + cacheBust)
					.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							var json = _extendLogoUrl(res.responseJSON, _c2SCommunicatorConfiguration.assetUrl, "Groups");
							_cache[cacheKey] = json;
							promise.resolve(json);
						} else {
							promise.reject();
						}
					});
			}
			return promise;
		};

		this.getPaymentProduct = function (paymentProductId, context, paymentProductSpecificInputs) {
			paymentProductSpecificInputs = paymentProductSpecificInputs || {};
			var cacheKeyLocale = context.locale ? context.locale + "_" : '';
			var promise = new Promise()
				, cacheBust = new Date().getTime()
				, cacheKey = "getPaymentProduct-" + paymentProductId + "_" + context.totalAmount + "_"
					+ context.countryCode + "_" + cacheKeyLocale + context.isRecurring + "_"
					+ context.currency + "_" + JSON.stringify(paymentProductSpecificInputs);
			if (_util.paymentProductsThatAreNotSupportedInThisBrowser.indexOf(paymentProductId) > -1) {
				setTimeout(function () {
					promise.reject({
						"errorId": "48b78d2d-1b35-4f8b-92cb-57cc2638e901",
						"errors": [{
							"code": "1007",
							"propertyName": "productId",
							"message": "UNKNOWN_PRODUCT_ID",
							"httpStatusCode": 404
						}]
					});
				}, 0);
			} else {
				if (_providedPaymentProduct && _providedPaymentProduct.id === paymentProductId) {
					if (!_cache[cacheKey]) {
						_cache[cacheKey] = _cleanJSON(_providedPaymentProduct, _c2SCommunicatorConfiguration.assetUrl);
					}
					setTimeout(function () {
						promise.resolve(_cache[cacheKey]);
					}, 0);
				} else if (_cache[cacheKey]) {
					setTimeout(function () {
						promise.resolve(_cache[cacheKey]);
					}, 0);
				} else {
					var urlParameterlocale = context.locale ? "&locale=" + context.locale: '';
					var getPaymentProductUrl = formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId
						+ "/products/" + paymentProductId + "?countryCode=" + context.countryCode
						+ "&isRecurring=" + context.isRecurring + "&amount=" + context.totalAmount
						+ "&currencyCode=" + context.currency + urlParameterlocale;

					if ((paymentProductId === _util.bancontactPaymentProductId) &&
					paymentProductSpecificInputs &&
					paymentProductSpecificInputs.bancontact &&
					paymentProductSpecificInputs.bancontact.forceBasicFlow) {
						// Add query parameter to products call to force basic flow for bancontact
						getPaymentProductUrl += "&forceBasicFlow=" + paymentProductSpecificInputs.bancontact.forceBasicFlow
					}

					getPaymentProductUrl += "&cacheBust=" + cacheBust;

					Net.get(getPaymentProductUrl)
						.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
						.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
						.end(function (res) {
							if (res.success) {
								var cleanedJSON = _cleanJSON(res.responseJSON, c2SCommunicatorConfiguration.assetUrl);
								if (paymentProductId === _util.googlePayPaymentProductId) {
									if (_GooglePay.isMerchantIdProvided(paymentProductSpecificInputs)) {
                                        var networks = cleanedJSON.paymentProduct320SpecificData.networks;
										_GooglePay.isGooglePayAvailable(context, paymentProductSpecificInputs, networks).then(function (isGooglePayAvailable) {
											if (isGooglePayAvailable) {
												_cache[cacheKey] = cleanedJSON;
												promise.resolve(cleanedJSON);
											} else {
												_cache[cacheKey] = cleanedJSON;
												//_isGooglePayAvailable returned false so google pay is not available, so reject getPaymentProduct
												promise.reject(cleanedJSON);
											}
										}, function () {
											_cache[cacheKey] = cleanedJSON;
											//_isGooglePayAvailable rejected so not available
											promise.reject(cleanedJSON);
										});
									} else {
										_cache[cacheKey] = cleanedJSON;
										// merchantId is not provided so reject
										promise.reject(cleanedJSON);
									}
								} else {
									_cache[cacheKey] = cleanedJSON;
									promise.resolve(cleanedJSON);
								}
							} else {
								promise.reject('failed to retrieve Payment Product', res);
							}
						});
				}
			}
			return promise;
		};

		this.getPaymentProductGroup = function (paymentProductGroupId, context) {
			var cacheKeyLocale = context.locale ? context.locale + "_" : '';
			var promise = new Promise()
				, cacheBust = new Date().getTime()
				, cacheKey = "getPaymentProductGroup-" + paymentProductGroupId + "_" + context.totalAmount + "_"
					+ context.countryCode + "_" + cacheKeyLocale + context.isRecurring + "_"
					+ context.currency;
			if (_providedPaymentProduct && _providedPaymentProduct.id === paymentProductGroupId) {
				if (_cache[cacheKey]) {
					setTimeout(function () {
						promise.resolve(_cache[cacheKey]);
					}, 0);
				} else {
					_cache[cacheKey] = _cleanJSON(_providedPaymentProduct, _c2SCommunicatorConfiguration.assetUrl);
					setTimeout(function () {
						promise.resolve(_cache[cacheKey]);
					}, 0);
				}
			} else if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				var urlParameterlocale = context.locale ? "&locale=" + context.locale: '';
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId
					+ "/productgroups/" + paymentProductGroupId + "?countryCode=" + context.countryCode
					+ "&isRecurring=" + context.isRecurring + "&amount=" + context.totalAmount
					+ "&currencyCode=" + context.currency + urlParameterlocale + "&cacheBust=" + cacheBust)
					.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							var cleanedJSON = _cleanJSON(res.responseJSON, c2SCommunicatorConfiguration.assetUrl);
							_cache[cacheKey] = cleanedJSON;
							promise.resolve(cleanedJSON);
						} else {
							promise.reject();
						}
					});
			}
			return promise;
		};

		this.getPaymentProductIdByCreditCardNumber = function (partialCreditCardNumber, context) {
			var promise = new Promise()
				, iinDetailsResponse = new IinDetailsResponse()
				, cacheKey = "getPaymentProductIdByCreditCardNumber-" + partialCreditCardNumber;

			var that = this;
			this.context = context;
			if (_cache[cacheKey]) {// cache is based on digit 1-6
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				var isEnoughDigits = function (partialCreditCardNumber) {
					return partialCreditCardNumber.length >= 6;
				};
				if (isEnoughDigits(partialCreditCardNumber)) {
					Net.post(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/services/getIINdetails")
						.data(JSON.stringify(this.convertContextToIinDetailsContext(partialCreditCardNumber, this.context)))
						.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
						.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
						.end(function (res) {
							if (res.success) {
								iinDetailsResponse.json = res.responseJSON;
								iinDetailsResponse.countryCode = res.responseJSON.countryCode;
								iinDetailsResponse.paymentProductId = res.responseJSON.paymentProductId;
								iinDetailsResponse.isAllowedInContext = res.responseJSON.isAllowedInContext;
								iinDetailsResponse.coBrands = res.responseJSON.coBrands;
								// check if this card is supported
								// if isAllowedInContext is available in the response set status and resolve
								if (res.responseJSON.hasOwnProperty('isAllowedInContext')) {
									iinDetailsResponse.status = "SUPPORTED";
									if (iinDetailsResponse.isAllowedInContext === false) {
										iinDetailsResponse.status = "EXISTING_BUT_NOT_ALLOWED";
									}
									_cache[cacheKey] = iinDetailsResponse;
									promise.resolve(iinDetailsResponse);
								} else {
									//if isAllowedInContext is not available get the payment product again to determine status and resolve
									that.getPaymentProduct(iinDetailsResponse.paymentProductId, that.context).then(function (paymentProduct) {
										if (paymentProduct) {
											iinDetailsResponse.status = "SUPPORTED";
										} else {
											iinDetailsResponse.status = "UNSUPPORTED";
										}
										_cache[cacheKey] = iinDetailsResponse;
										promise.resolve(iinDetailsResponse);
									}, function () {
										iinDetailsResponse.status = "UNKNOWN";
										promise.reject(iinDetailsResponse);
									});
								}
							} else {
								iinDetailsResponse.status = "UNKNOWN";
								promise.reject(iinDetailsResponse);
							}
						});
				} else {
					iinDetailsResponse.status = "NOT_ENOUGH_DIGITS";
					setTimeout(function () {
						promise.resolve(iinDetailsResponse);
					}, 0);
				}
			}
			return promise;
		};

		this.convertContextToIinDetailsContext = function (partialCreditCardNumber, context) {
			var payload = {
				"bin": partialCreditCardNumber,
				"paymentContext": {
					"countryCode": context.countryCode,
					"isRecurring": context.isRecurring,
					"amountOfMoney": {
						"amount": context.totalAmount,
						"currencyCode": context.currency
					}
				}
			};

			// Account on file id is needed only in case when the merchant
			// uses multiple payment platforms at the same time.
			if (typeof context.accountOnFileId !== 'undefined') {
				payload.accountOnFileId = context.accountOnFileId;
			}

			return payload;
		};

		this.getPublicKey = function () {
			var promise = new Promise()
				, cacheKey = "publicKey";

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/crypto/publickey")
					.set("X-GCS-ClientMetaInfo", _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							var publicKeyResponse = new PublicKeyResponse(res.responseJSON);
							_cache[cacheKey] = publicKeyResponse;
							promise.resolve(publicKeyResponse);
						} else {
							promise.reject("unable to get public key");
						}
					});
			}
			return promise;
		};

		this.getPaymentProductNetworks = function (paymentProductId, context) {
			var promise = new Promise()
				, cacheKey = "paymentProductNetworks-" + paymentProductId + "_" + context.countryCode + "_" + context.currency + "_"
					+ context.totalAmount + "_" + context.isRecurring;

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId
					+ "/products/" + paymentProductId + "/networks" + "?countryCode=" + context.countryCode + "&currencyCode=" + context.currency
					+ "&amount=" + context.totalAmount + "&isRecurring=" + context.isRecurring)
					.set('X-GCS-ClientMetaInfo', _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							_cache[cacheKey] = res.responseJSON;
							promise.resolve(res.responseJSON);
						} else {
							promise.reject();
						}
					});
			}
			return promise;
		};

		this.getPaymentProductDirectory = function (paymentProductId, currencyCode, countryCode) {
			var promise = new Promise()
				, cacheKey = "getPaymentProductDirectory-" + paymentProductId + "_" + currencyCode + "_" + countryCode;

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/products/" + paymentProductId + "/directory?countryCode=" + countryCode + "&currencyCode=" + currencyCode)
					.set("X-GCS-ClientMetaInfo", _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							_cache[cacheKey] = res.responseJSON;
							promise.resolve(res.responseJSON);
						} else {
							promise.reject("unable to retrieve payment product directory");
						}
					});
			}
			return promise;
		};

		this.convertAmount = function (amount, source, target) {
			var promise = new Promise()
				, cacheKey = "convertAmount-" + amount + "_" + source + "_" + target;

			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/services/convert/amount?source=" + source + "&target=" + target + "&amount=" + amount)
					.set("X-GCS-ClientMetaInfo", _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							_cache[cacheKey] = res.responseJSON;
							promise.resolve(res.responseJSON);
						} else {
							promise.reject("unable to convert amount");
						}
					});
			}
			return promise;
		};

		this.getThirdPartyPaymentStatus = function (paymentId) {
			var promise = new Promise();

			Net.get(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/payments/" + paymentId + "/thirdpartystatus")
				.set("X-GCS-ClientMetaInfo", _util.base64Encode(metadata))
				.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
				.end(function (res) {
					if (res.success) {
						promise.resolve(res.responseJSON);
					} else {
						promise.reject("unable to retrieve third party status");
					}
				});
			return promise;
		};

		this.getCustomerDetails = function(paymentProductId, context) {

			var promise = new Promise();
			var cacheKey = "getCustomerDetails_" + context.countryCode;
			cacheKey = constructCacheKeyFromKeyValues(cacheKey, context.values);
			if (_cache[cacheKey]) {
				setTimeout(function () {
					promise.resolve(_cache[cacheKey]);
				}, 0);
			} else {
				Net.post(formatUrl(_c2SCommunicatorConfiguration.clientApiUrl) + _c2SCommunicatorConfiguration.customerId + "/products/" + paymentProductId + "/customerDetails")
					.data(JSON.stringify(context))
					.set("X-GCS-ClientMetaInfo", _util.base64Encode(metadata))
					.set('Authorization', 'GCS v1Client:' + _c2SCommunicatorConfiguration.clientSessionId)
					.end(function (res) {
						if (res.success) {
							_cache[cacheKey] = res.responseJSON;
							promise.resolve(res.responseJSON);
						} else {
							promise.reject(res.responseJSON);
						}
					});
			}
			return promise;
		};

		var constructCacheKeyFromKeyValues = function(prefix, values) {
			var cacheKey = prefix;
			for (var key in values){
				if (values.hasOwnProperty(key)) {
					cacheKey += "_" + values[key].key + "_" + values[key].value;
				}
			}
			return cacheKey;
		};

        /* Transforms the JSON representation of a payment product (group) so it matches the result of getPaymentProduct and getPaymentProductGroup. */
        this.transformPaymentProductJSON = function (json) {
            return _cleanJSON(json, _c2SCommunicatorConfiguration.assetUrl)
        };
	};

	connectsdk.C2SCommunicator = C2SCommunicator;
	return C2SCommunicator;
});

define("connectsdk.LabelTemplateElement", ["connectsdk.core"], function(connectsdk) {

	var LabelTemplateElement = function (json) {
		this.json = json;
		this.attributeKey = json.attributeKey;
		this.mask = json.mask;
		this.wildcardMask = json.mask ? json.mask.replace(/9/g, "*") : "";
	};

	connectsdk.LabelTemplateElement = LabelTemplateElement;
	return LabelTemplateElement;
});
define("connectsdk.Attribute", ["connectsdk.core"], function(connectsdk) {

	var Attribute = function (json) {
		this.json = json;
		this.key = json.key;
		this.value = json.value;
		this.status = json.status;
		this.mustWriteReason = json.mustWriteReason;
	};

	connectsdk.Attribute = Attribute;
	return Attribute;
});
define("connectsdk.AccountOnFileDisplayHints", ["connectsdk.core", "connectsdk.LabelTemplateElement"], function(connectsdk, LabelTemplateElement) {

	var _parseJSON = function (_json, _labelTemplate, _labelTemplateElementByAttributeKey) {
		if (_json.labelTemplate) {
			for (var i = 0, l = _json.labelTemplate.length; i < l; i++) {
				var labelTemplateElement = new LabelTemplateElement(_json.labelTemplate[i]);
				_labelTemplate.push(labelTemplateElement);
				_labelTemplateElementByAttributeKey[labelTemplateElement.attributeKey] = labelTemplateElement;
			}
		}
	};

	var AccountOnFileDisplayHints = function (json) {
		this.json = json;
		this.labelTemplate = [];
		this.labelTemplateElementByAttributeKey = {};

		_parseJSON(json, this.labelTemplate, this.labelTemplateElementByAttributeKey);
	};

	connectsdk.AccountOnFileDisplayHints = AccountOnFileDisplayHints;
	return AccountOnFileDisplayHints;
});
define("connectsdk.AccountOnFile", ["connectsdk.core" ,"connectsdk.AccountOnFileDisplayHints", "connectsdk.Attribute"], function(connectsdk, AccountOnFileDisplayHints, Attribute) {

	var _parseJSON = function (_json, _attributes, _attributeByKey) {
		if (_json.attributes) {
			for (var i = 0, l = _json.attributes.length; i < l; i++) {
				var attribute = new Attribute(_json.attributes[i]);
				_attributes.push(attribute);
				_attributeByKey[attribute.key] = attribute;
			}
		}
	};

	var AccountOnFile = function (json) {
		var that = this;
		this.json = json;
		this.attributes = [];
		this.attributeByKey = {};
		this.displayHints = new AccountOnFileDisplayHints(json.displayHints);
		this.id = json.id;
		this.paymentProductId = json.paymentProductId;

		this.getMaskedValueByAttributeKey = function(attributeKey) {
			var value = this.attributeByKey[attributeKey].value;
			var wildcardMask;
			try {
				wildcardMask = this.displayHints.labelTemplateElementByAttributeKey[attributeKey].wildcardMask;
			} catch (e) {}
			if (value !== undefined && wildcardMask !== undefined) {
				var maskingUtil = new connectsdk.MaskingUtil();
				return maskingUtil.applyMask(wildcardMask, value);
			}
			return undefined;
		};

		_parseJSON(json, this.attributes, this.attributeByKey);
	};

	connectsdk.AccountOnFile = AccountOnFile;
	return AccountOnFile;
});
define("connectsdk.PaymentProduct302SpecificData", ["connectsdk.core"], function(connectsdk) {

	var PaymentProduct302SpecificData = function (json) {
		this.json = json;
		this.networks = json.networks;
	};

	connectsdk.PaymentProduct302SpecificData = PaymentProduct302SpecificData;
	return PaymentProduct302SpecificData;
});
define("connectsdk.PaymentProduct320SpecificData", ["connectsdk.core"], function(connectsdk) {

	var PaymentProduct320SpecificData = function (json) {
		this.json = json;
		this.gateway = json.gateway;
		this.networks = json.networks;
	};

	connectsdk.PaymentProduct320SpecificData = PaymentProduct320SpecificData;
	return PaymentProduct320SpecificData;
});
define("connectsdk.PaymentProduct863SpecificData", ["connectsdk.core"], function(connectsdk) {

	var PaymentProduct863SpecificData = function (json) {
		this.json = json;
		this.integrationTypes = json.integrationTypes;
	};

	connectsdk.PaymentProduct863SpecificData = PaymentProduct863SpecificData;
	return PaymentProduct863SpecificData;
});
define("connectsdk.PaymentProductDisplayHints", ["connectsdk.core"], function(connectsdk) {

	var PaymentProductDisplayHints = function (json) {
		this.json = json;
		this.displayOrder = json.displayOrder;
		this.label = json.label;
		this.logo = json.logo;
	};

	connectsdk.PaymentProductDisplayHints = PaymentProductDisplayHints;
	return PaymentProductDisplayHints;
});
define("connectsdk.BasicPaymentProduct", ["connectsdk.core", "connectsdk.AccountOnFile", "connectsdk.PaymentProductDisplayHints", "connectsdk.PaymentProduct302SpecificData", "connectsdk.PaymentProduct320SpecificData", "connectsdk.PaymentProduct863SpecificData"], function(connectsdk, AccountOnFile, PaymentProductDisplayHints, PaymentProduct302SpecificData, PaymentProduct320SpecificData, PaymentProduct863SpecificData) {

	var _parseJSON = function (_json, _paymentProduct, _accountsOnFile, _accountOnFileById) {
		if (_json.accountsOnFile) {
			for (var i = 0, il = _json.accountsOnFile.length; i < il; i++) {
				var accountOnFile = new AccountOnFile(_json.accountsOnFile[i]);
				_accountsOnFile.push(accountOnFile);
				_accountOnFileById[accountOnFile.id] = accountOnFile;
			}
		}
		if (_json.paymentProduct302SpecificData) {
			_paymentProduct.paymentProduct302SpecificData = new PaymentProduct302SpecificData(_json.paymentProduct302SpecificData);
		}
		if (_json.paymentProduct320SpecificData) {
			_paymentProduct.paymentProduct320SpecificData = new PaymentProduct320SpecificData(_json.paymentProduct320SpecificData);
		}
		if (_json.paymentProduct863SpecificData) {
			_paymentProduct.paymentProduct863SpecificData = new PaymentProduct863SpecificData(_json.paymentProduct863SpecificData);
		}
	};

	var BasicPaymentProduct = function (json) {
		this.json = json;
		this.json.type = "product";
		this.accountsOnFile = [];
		this.accountOnFileById = {};
		this.allowsRecurring = json.allowsRecurring;
		this.allowsTokenization = json.allowsTokenization;
		this.autoTokenized  = json.autoTokenized ;
		this.displayHints = new PaymentProductDisplayHints(json.displayHints);
		this.id = json.id;
		this.maxAmount = json.maxAmount;
		this.minAmount = json.minAmount;
		this.paymentMethod = json.paymentMethod;
		this.mobileIntegrationLevel = json.mobileIntegrationLevel;
		this.usesRedirectionTo3rdParty = json.usesRedirectionTo3rdParty;
		this.paymentProductGroup = json.paymentProductGroup;

		_parseJSON(json, this, this.accountsOnFile, this.accountOnFileById);
	};

	connectsdk.BasicPaymentProduct = BasicPaymentProduct;
	return BasicPaymentProduct;
});
define("connectsdk.BasicPaymentProductGroup", ["connectsdk.core", "connectsdk.AccountOnFile", "connectsdk.PaymentProductDisplayHints"], function(connectsdk, AccountOnFile, PaymentProductDisplayHints) {

	var _parseJSON = function (_json, _accountsOnFile, _accountOnFileById) {
		if (_json.accountsOnFile) {
			for (var i = 0, il = _json.accountsOnFile.length; i < il; i++) {
				var accountOnFile = new AccountOnFile(_json.accountsOnFile[i]);
				_accountsOnFile.push(accountOnFile);
				_accountOnFileById[accountOnFile.id] = accountOnFile;
			}
		}
	};

	var BasicPaymentProductGroup = function (json) {
		this.json = json;
		this.json.type = "group";
		this.id = json.id;
		this.displayHints = new PaymentProductDisplayHints(json.displayHints);
		this.accountsOnFile = [];
		this.accountOnFileById = {};
		_parseJSON(json, this.accountsOnFile, this.accountOnFileById);
	};

	connectsdk.BasicPaymentProductGroup = BasicPaymentProductGroup;
	return BasicPaymentProductGroup;
});
define("connectsdk.MaskedString", ["connectsdk.core"], function(connectsdk) {

	var MaskedString = function(formattedValue, cursorIndex) {

		this.formattedValue = formattedValue;
		this.cursorIndex = cursorIndex;
	};

	connectsdk.MaskedString = MaskedString;
	return MaskedString;
});
define("connectsdk.MaskingUtil", ["connectsdk.core", "connectsdk.MaskedString"], function(connectsdk, MaskedString) {

	var _fillBuffer = function(index, offset, buffer, tempMask, valuec) {
		if (index+offset < valuec.length && index < tempMask.length) {
			if ((tempMask[index] === "9" && Number(valuec[index+offset]) > -1 && valuec[index+offset] !== " ") || tempMask[index] === "*") {
				buffer.push(valuec[index+offset]);
			} else {
				if (valuec[index+offset] === tempMask[index]) {
					buffer.push(valuec[index+offset]);
				} else if (tempMask[index] !== "9" && tempMask[index] !== "*") {
					buffer.push(tempMask[index]);
					offset--;
				} else {
					// offset++;
					valuec.splice(index+offset, 1);
					index--;
				}
			}
			_fillBuffer(index+1, offset, buffer, tempMask, valuec);
		}
	};

	var MaskingUtil = function () {
		this.applyMask = function (mask, newValue, oldValue) {
			var buffer = [],
					valuec = newValue.split("");
			if (mask) {
				var maskc = mask.split(""),
						tempMask = [];
				for (var i = 0, il = maskc.length; i < il; i++) {
					// the char '{' and '}' should ALWAYS be ignored
					var c = maskc[i];
					if (c === "{" || c === "}") {
						// ignore
					} else {
						tempMask.push(c);
					}
				}
				// tempmask now contains the replaceable chars and the non-replaceable masks at the correct index
				_fillBuffer(0, 0, buffer, tempMask, valuec);
			} else {
				// send back as is
				for (var i = 0, il = valuec.length; i < il; i++) {
					var c = valuec[i];
					buffer.push(c);
				}
			}
			newValue = buffer.join("");
			var cursor = 1;
			// calculate the cursor index
			if (oldValue) {
				var tester = oldValue.split("");
				for (var i = 0, il = buffer.length; i < il; i++) {
					if (buffer[i] !== tester[i]) {
						cursor = i+1;
						break;
					}
				}
			}
			if (newValue.substring(0, newValue.length -1) === oldValue) {
				cursor = newValue.length + 1;
			}
			return new MaskedString(newValue, cursor);
		};
		
		this.getMaxLengthBasedOnMask = function (mask) {
			if (mask) {
				var maskc = mask.split(""),
						newLength = -1;
				for (var i = 0, il = maskc.length; i < il; i++) {
					newLength++;
					var c = maskc[i];
					if (c === "{" || c === "}") {
						newLength--;
					}
				}
				return newLength;
			}
		};

		this.removeMask = function (mask, value) {
			// remove the mask from the masked input
			var buffer = [],
					valuec = (value) ? value.split("") : [];
			if (mask) {
				var maskc = mask.split(""),
						valueIndex = -1,
						inMask = false;
				for (var i = 0, il = maskc.length; i < il; i++) {
					valueIndex++;
					// the char '{' and '}' should ALWAYS be ignored
					var c = maskc[i];
					if (c === "{" || c === "}") {
						valueIndex--;
						if (c === "{") {
							inMask = true;
						} else if (c === "}") {
							inMask = false;
						}
					} else {
						if (inMask && valuec[valueIndex]) {
							buffer.push(valuec[valueIndex]);
						}
					}
				}
			} else {
				// send back as is
				for (var i = 0, il = valuec.length; i < il; i++) {
					var c = valuec[i];
					buffer.push(c);
				}
			}
			return buffer.join("").trim();
		};
	};

	connectsdk.MaskingUtil = MaskingUtil;
	return MaskingUtil;
});
define("connectsdk.ValidationRuleLuhn", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleLuhn = function (json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
		this.validate = function (value) {
			var luhnArr = [[0,2,4,6,8,1,3,5,7,9],[0,1,2,3,4,5,6,7,8,9]]
				,sum = 0;
				
	   		value.replace(/\D+/g,"").replace(/[\d]/g, function(c, p, o) {
		        sum += luhnArr[ (o.length-p)&1 ][ parseInt(c,10) ];
		    });
		    return (sum%10 === 0) && (sum > 0);
		};
	};

	connectsdk.ValidationRuleLuhn = ValidationRuleLuhn;
	return ValidationRuleLuhn;
});
define("connectsdk.ValidationRuleExpirationDate", ["connectsdk.core"], function (connectsdk) {

	var _validateDateFormat = function (value) {
		// value is mmYY or mmYYYY
		var pattern = /\d{4}|\d{6}$/g;
		return pattern.test(value);
	};

	var ValidationRuleExpirationDate = function (json) {
		this.json = json;
		this.type = json.type;
		this.errorMessageId = json.type;

		this.validate = function (value) {

			value = value.replace(/[^\d]/g, '');
			if (!_validateDateFormat(value)) {
				return false;
			}

			var split;
			if (value.length === 4) {
				split = [value.substring(0, 2), "20" + value.substring(2, 4)];
			} else if (value.length === 6) {
				split = [value.substring(0, 2), value.substring(2, 6)];
			} else {
				return false;
			}

			// The month is zero-based, so subtract one.
			var expirationMonth = split[0] - 1;
			var expirationYear = split[1];
			var expirationDate = new Date(expirationYear, expirationMonth, 1);

			// Compare the input with the parsed date, to check if the date rolled over.
			if (expirationDate.getMonth() !== Number(expirationMonth) || expirationDate.getFullYear() !== Number(expirationYear)) {
				return false;
			}

			// For comparison, set the current year & month and the maximum allowed expiration date.
			var nowWithDay = new Date();
			var now = new Date(nowWithDay.getFullYear(), nowWithDay.getMonth(), 1);
			var maxExpirationDate = new Date(nowWithDay.getFullYear() + 25, 11, 1);

			// The card is still valid if it expires this month.
			return expirationDate >= now && expirationDate <= maxExpirationDate;
		};
	};

	connectsdk.ValidationRuleExpirationDate = ValidationRuleExpirationDate;
	return ValidationRuleExpirationDate;
});

define("connectsdk.ValidationRuleFixedList", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleFixedList = function (json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
		this.allowedValues = json.attributes.allowedValues;
		
		this.validate = function (value) {
			for (var i = 0, il = this.allowedValues.length; i < il; i++) {
				if (this.allowedValues[i] === value) {
					return true;
				}
			}
			return false;
		};
	};

	connectsdk.ValidationRuleFixedList = ValidationRuleFixedList;
	return ValidationRuleFixedList;
});
define("connectsdk.ValidationRuleLength", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleLength = function (json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
        this.maxLength = json.attributes.maxLength;
		this.minLength = json.attributes.minLength;
		
		this.validate = function (value) {
			return this.minLength <= value.length && value.length <= this.maxLength;
		};
	};

	connectsdk.ValidationRuleLength = ValidationRuleLength;
	return ValidationRuleLength;
});
define("connectsdk.ValidationRuleRange", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleRange = function(json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
        this.maxValue = json.attributes.maxValue;
		this.minValue = json.attributes.minValue;
		
		this.validate = function(value) {
			if (isNaN(value)) {
				return false;
			}
			value = Number(value);
			return this.minValue <= value && value <= this.maxValue;
		};
	};

	connectsdk.ValidationRuleRange = ValidationRuleRange;
	return ValidationRuleRange;
});
define("connectsdk.ValidationRuleRegularExpression", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleRegularExpression = function(json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
		this.regularExpression = json.attributes.regularExpression;
		
		this.validate = function(value) {
			var regexp = new RegExp(this.regularExpression);
			return regexp.test(value);
		};
	};

	connectsdk.ValidationRuleRegularExpression = ValidationRuleRegularExpression;
	return ValidationRuleRegularExpression;
});
define("connectsdk.ValidationRuleEmailAddress", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleEmailAddress = function(json) {
		this.json = json;
		this.type = json.type,
		this.errorMessageId = json.type;

		this.validate = function(value) {
			var regexp = new RegExp(/^[^@\.]+(\.[^@\.]+)*@([^@\.]+\.)*[^@\.]+\.[^@\.][^@\.]+$/i);
			return regexp.test(value);
		};
	};

	connectsdk.ValidationRuleEmailAddress = ValidationRuleEmailAddress;
	return ValidationRuleEmailAddress;
});
define("connectsdk.ValidationRuleTermsAndConditions", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleTermsAndConditions = function(json) {
		this.json = json;
		this.type = json.type,
		this.errorMessageId = json.type;

		this.validate = function(value) {
			return true === value || "true" === value;
		};
	};

	connectsdk.ValidationRuleTermsAndConditions = ValidationRuleTermsAndConditions;
	return ValidationRuleTermsAndConditions;
});
define("connectsdk.ValidationRuleBoletoBancarioRequiredness", ["connectsdk.core"], function(connectsdk) {

	var ValidationRuleBoletoBancarioRequiredness = function (json) {
		this.json = json;
        this.type = json.type,
        this.errorMessageId = json.type;
        this.fiscalNumberLength = json.attributes.fiscalNumberLength;
		
		this.validate = function (value, fiscalNumberValue) {
			if (typeof fiscalNumberValue === 'undefined') {
				fiscalNumberValue = '';
			}

			return (fiscalNumberValue.length === this.fiscalNumberLength && value.length > 0) || fiscalNumberValue.length !== this.fiscalNumberLength;
		};
	};

	connectsdk.ValidationRuleBoletoBancarioRequiredness = ValidationRuleBoletoBancarioRequiredness;
	return ValidationRuleBoletoBancarioRequiredness;
});
define('connectsdk.ValidationRuleIban', ['connectsdk.core'], function (connectsdk) {

  /**
   * Sanitize value by remove all unwanted chars of a Iban format
   *
   * @param {String} value
   * @returns {string}
   * @private
   */
  var _sanitizeValue = function (value) {
    return value.replace(/[^\d\w]+/g, '').toUpperCase();
  };

  /**
   * Get state if given value is a valid Iban format
   *
   * @param {String} value
   * @returns {boolean}
   * @private
   */
  var _isValidFormat = function (value) {
    return typeof value === 'string' && /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(_sanitizeValue(value));
  };

  /**
   * Convert a value to a string needed for validation calculations
   *
   * @param {String} value
   * @returns {string}
   * @private
   */
  var _toComputedString = function (value) {
    return _sanitizeValue(value)

    // place the first 4 chars to the end
      .replace(/(^.{4})(.*)/, '$2$1')

      // replace letters by corresponding numbers A=10 / Z=35
      .replace(/[A-Z]/g, function (d) {
        return d.charCodeAt(0) - 55;
      });
  }

  /**
   * Validate Iban by given json
   *
   * @param {Object} json
   * @constructor
   */
  var ValidationRuleIban = function (json) {
    this.json           = json;
    this.type           = json.type;
    this.errorMessageId = json.type;

    /**
     * Validate Iban nrule
     *
     * @see https://github.com/arhs/iban.js/blob/master/iban.js
     *
     * @param   {string} value
     * @returns {boolean}
     */
    this.validate = function (value) {

      // bail if format is invalid
      if (!_isValidFormat(value)) {
        return false;
      }

      // Check if reminder module 97 equals 1
      // only then it should pass the validation
      var remainder = _toComputedString(value),
          block;

      while (remainder.length > 2) {
        block     = remainder.slice(0, 9);
        remainder = parseInt(block, 10) % 97 + remainder.slice(block.length);
      }

      return (parseInt(remainder, 10) % 97) === 1;
    };
  };

  connectsdk.ValidationRuleIban = ValidationRuleIban;
  return ValidationRuleIban;
});
define("connectsdk.ValidationRuleFactory", ["connectsdk.core", "connectsdk.ValidationRuleEmailAddress", "connectsdk.ValidationRuleTermsAndConditions", "connectsdk.ValidationRuleExpirationDate", "connectsdk.ValidationRuleFixedList", "connectsdk.ValidationRuleLength", "connectsdk.ValidationRuleLuhn", "connectsdk.ValidationRuleRange", "connectsdk.ValidationRuleRegularExpression", "connectsdk.ValidationRuleBoletoBancarioRequiredness", "connectsdk.ValidationRuleIban"], function (connectsdk, ValidationRuleEmailAddress, ValidationRuleTermsAndConditions, ValidationRuleExpirationDate, ValidationRuleFixedList, ValidationRuleLength, ValidationRuleLuhn, ValidationRuleRange, ValidationRuleRegularExpression, ValidationRuleBoletoBancarioRequiredness, ValidationRuleIban) {

    var ValidationRuleFactory = function () {

        this.makeValidator = function (json) {
            // create new class based on the rule
            try {
                var classType = json.type.charAt(0).toUpperCase() + json.type.slice(1), // camel casing
                    className = eval("ValidationRule" + classType);
                return new className(json);
            } catch (e) {
                console.warn('no validator for ', classType);
            }
            return null;
        };
    };

    connectsdk.ValidationRuleFactory = ValidationRuleFactory;
    return ValidationRuleFactory;
});
define("connectsdk.DataRestrictions", ["connectsdk.core", "connectsdk.ValidationRuleExpirationDate", "connectsdk.ValidationRuleFixedList", "connectsdk.ValidationRuleLength", "connectsdk.ValidationRuleLuhn", "connectsdk.ValidationRuleRange", "connectsdk.ValidationRuleRegularExpression", "connectsdk.ValidationRuleEmailAddress", "connectsdk.ValidationRuleTermsAndConditions", "connectsdk.ValidationRuleIban", "connectsdk.ValidationRuleFactory"], function(connectsdk, ValidationRuleExpirationDate, ValidationRuleFixedList, ValidationRuleLength, ValidationRuleLuhn, ValidationRuleRange, ValidationRuleRegularExpression, ValidationRuleEmailAddress, ValidationRuleTermsAndConditions, ValidationRuleIban, ValidationRuleFactory) {

	var DataRestrictions = function (json, mask) {

		var _parseJSON = function (_json, _validationRules, _validationRuleByType) {
		    var validationRuleFactory = new ValidationRuleFactory();
			if (_json.validators) {
				for (var key in _json.validators) {
					var validationRule = validationRuleFactory.makeValidator({type: key, attributes: _json.validators[key]});
					if (validationRule) {
						_validationRules.push(validationRule);
						_validationRuleByType[validationRule.type] = validationRule;
					}
				}
			}
		};

		this.json = json;
		this.isRequired = json.isRequired;
		this.validationRules = [];
		this.validationRuleByType = {};

		_parseJSON(json, this.validationRules, this.validationRuleByType);
	};

	connectsdk.DataRestrictions = DataRestrictions;
	return DataRestrictions;
});
define("connectsdk.ValueMappingElement", ["connectsdk.core"], function(connectsdk) {

	var ValueMappingElement = function (json) {
		this.json = json;
		this.displayName = json.displayName;
		this.value = json.value;
	};

	connectsdk.ValueMappingElement = ValueMappingElement;
	return ValueMappingElement;
});
define("connectsdk.FormElement", ["connectsdk.core", "connectsdk.ValueMappingElement"], function(connectsdk, ValueMappingElement) {

	var FormElement = function (json) {

		var _parseJSON = function (_json, _valueMapping) {
			if (_json.valueMapping) {
				for (var i = 0, l = _json.valueMapping.length; i < l; i++) {
					_valueMapping.push(new ValueMappingElement(_json.valueMapping[i]));
				}
			}
		};

		this.json = json;
		this.type = json.type;
		this.valueMapping = [];
		
		_parseJSON(json, this.valueMapping);
	};

	connectsdk.FormElement = FormElement;
	return FormElement;
});
define("connectsdk.Tooltip", ["connectsdk.core"], function(connectsdk) {

	var Tooltip = function (json) {
		this.json = json;
		this.image = json.image;
		this.label = json.label;
	};

	connectsdk.Tooltip = Tooltip;
	return Tooltip;
});
define("connectsdk.PaymentProductFieldDisplayHints", ["connectsdk.core", "connectsdk.Tooltip", "connectsdk.FormElement"], function(connectsdk, Tooltip, FormElement) {

	var PaymentProductFieldDisplayHints = function (json) {
		this.json = json;
 		this.displayOrder = json.displayOrder;
		if (json.formElement) {
			this.formElement = new FormElement(json.formElement);
		}
		this.label = json.label;
		this.mask = json.mask;
		this.obfuscate = json.obfuscate;
		this.placeholderLabel = json.placeholderLabel;
		this.preferredInputType = json.preferredInputType;
		this.tooltip = json.tooltip? new Tooltip(json.tooltip): undefined;
		this.alwaysShow = json.alwaysShow;
		this.wildcardMask = json.mask ? json.mask.replace(/9/g, "*") : "";
	};

	connectsdk.PaymentProductFieldDisplayHints = PaymentProductFieldDisplayHints;
	return PaymentProductFieldDisplayHints;
});
define("connectsdk.PaymentProductField", ["connectsdk.core", "connectsdk.PaymentProductFieldDisplayHints", "connectsdk.DataRestrictions", "connectsdk.MaskingUtil"], function(connectsdk, PaymentProductFieldDisplayHints, DataRestrictions, MaskingUtil) {
	var PaymentProductField = function (json) {
		this.json = json;
		this.displayHints = json.displayHints ? new PaymentProductFieldDisplayHints(json.displayHints) : '';
		this.dataRestrictions = new DataRestrictions(json.dataRestrictions, this.displayHints ? this.displayHints.mask : '');
		this.id = json.id;
		this.type = json.type;
		var _errorCodes = [];

		this.getErrorCodes = function (value) {
			if (value) {
				_errorCodes = [];
				this.isValid(value);
			}
			return _errorCodes;
		};
		this.isValid = function (value) {
			// isValid checks all datarestrictions
			var validators = this.dataRestrictions.validationRules;
			var hasError = false;

			// Apply masking value first
			var maskedValue = this.applyMask(value);
			value = this.removeMask(maskedValue.formattedValue);
			for (var i = 0, il = validators.length; i < il; i++) {
				var validator = validators[i];
				if (!validator.validate(value)) {
					hasError = true;
					_errorCodes.push(validator.errorMessageId);
				}
			}
			return !hasError;
		};
		this.applyMask = function (newValue, oldValue) {
			var maskingUtil = new MaskingUtil();
			return maskingUtil.applyMask(this.displayHints.mask, newValue, oldValue);
		};
		this.applyWildcardMask = function (newValue, oldValue) {
			var maskingUtil = new MaskingUtil();
			return maskingUtil.applyMask(this.displayHints.wildcardMask, newValue, oldValue);
		};
		this.removeMask = function (value) {
			var maskingUtil = new MaskingUtil();
			return maskingUtil.removeMask(this.displayHints.mask, value);
		};
	};

	connectsdk.PaymentProductField = PaymentProductField;
	return PaymentProductField;
});
define("connectsdk.PaymentProduct", ["connectsdk.core", "connectsdk.BasicPaymentProduct", "connectsdk.PaymentProductField"], function(connectsdk, BasicPaymentProduct, PaymentProductField) {

	var _parseJSON = function (_json, _paymentProductFields, _paymentProductFieldById) {
		if (_json.fields) {
			for (var i = 0, il = _json.fields.length; i < il; i++) {
				var paymentProductField = new PaymentProductField(_json.fields[i]);
				_paymentProductFields.push(paymentProductField);
				_paymentProductFieldById[paymentProductField.id] = paymentProductField;
			}
		}
	};

	var PaymentProduct = function (json) {
		var basicPaymentProduct = new BasicPaymentProduct(json);
		basicPaymentProduct.paymentProductFields = [];
		basicPaymentProduct.paymentProductFieldById = {};

		_parseJSON(basicPaymentProduct.json, basicPaymentProduct.paymentProductFields, basicPaymentProduct.paymentProductFieldById);

		return basicPaymentProduct;
	};

	connectsdk.PaymentProduct = PaymentProduct;
	return PaymentProduct;
});

define("connectsdk.PaymentProductGroup", ["connectsdk.core", "connectsdk.BasicPaymentProduct", "connectsdk.PaymentProductField"], function(connectsdk, BasicPaymentProduct, PaymentProductField) {

	var _parseJSON = function (_json, _paymentProductFields, _paymentProductFieldById) {
		if (_json.fields) {
			for (var i = 0, il = _json.fields.length; i < il; i++) {
				var paymentProductField = new PaymentProductField(_json.fields[i]);
				_paymentProductFields.push(paymentProductField);
				_paymentProductFieldById[paymentProductField.id] = paymentProductField;
			}
		}
	};

	var PaymentProductGroup = function (json) {
		var basicPaymentProduct = new BasicPaymentProduct(json);
		basicPaymentProduct.json = json;
		basicPaymentProduct.json.type = "group";
		basicPaymentProduct.paymentProductFields = [];
		basicPaymentProduct.paymentProductFieldById = {};

		_parseJSON(basicPaymentProduct.json, basicPaymentProduct.paymentProductFields, basicPaymentProduct.paymentProductFieldById);

		return basicPaymentProduct;
	};

	connectsdk.PaymentProductGroup = PaymentProductGroup;
	return PaymentProductGroup;
});
define("connectsdk.BasicPaymentProducts", ["connectsdk.core", "connectsdk.BasicPaymentProduct"], function(connectsdk, BasicPaymentProduct) {

	var _parseJson = function (_json, _paymentProducts, _accountsOnFile, _paymentProductById, _accountOnFileById, _paymentProductByAccountOnFileId) {
		if (_json.paymentProducts) {
			for (var i = 0, il = _json.paymentProducts.length; i < il; i++) {
				var paymentProduct = new BasicPaymentProduct(_json.paymentProducts[i]);
				_paymentProducts.push(paymentProduct);
				_paymentProductById[paymentProduct.id] = paymentProduct;

				if (paymentProduct.accountsOnFile) {
					var aofs = paymentProduct.accountsOnFile;
					for (var j = 0, jl = aofs.length; j < jl; j++) {
						var aof = aofs[j];
						_accountsOnFile.push(aof);
						_accountOnFileById[aof.id] = aof;
						_paymentProductByAccountOnFileId[aof.id] = paymentProduct;
					}
				}
			}
		}
	};

	var BasicPaymentProducts = function (json) {
		this.basicPaymentProducts = [];
		this.basicPaymentProductById = {};
		this.basicPaymentProductByAccountOnFileId = {};
		this.accountsOnFile = [];
		this.accountOnFileById = {};
		this.json = json;

		_parseJson(json, this.basicPaymentProducts, this.accountsOnFile, this.basicPaymentProductById, this.accountOnFileById, this.basicPaymentProductByAccountOnFileId);
	};

	connectsdk.BasicPaymentProducts = BasicPaymentProducts;
	return BasicPaymentProducts;
});
define("connectsdk.BasicPaymentProductGroups", ["connectsdk.core", "connectsdk.BasicPaymentProductGroup"], function(connectsdk, BasicPaymentProductGroup) {

	var _parseJson = function (_json, _paymentProductGroups, _accountsOnFile, _paymentProductGroupById, _accountOnFileById) {
		if (_json.paymentProductGroups) {
			for (var i = 0, il = _json.paymentProductGroups.length; i < il; i++) {
				var paymentProductGroup = new BasicPaymentProductGroup(_json.paymentProductGroups[i]);
				_paymentProductGroups.push(paymentProductGroup);
				_paymentProductGroupById[paymentProductGroup.id] = paymentProductGroup;

				if (paymentProductGroup.accountsOnFile) {
					var aofs = paymentProductGroup.accountsOnFile;
					for (var j = 0, jl = aofs.length; j < jl; j++) {
						var aof = aofs[j];
						_accountsOnFile.push(aof);
						_accountOnFileById[aof.id] = aof;
					}
				}
			}
		}
	};

	var BasicPaymentProductGroups = function (json) {
		this.basicPaymentProductGroups = [];
		this.basicPaymentProductGroupById = {};
		this.accountsOnFile = [];
		this.accountOnFileById = {};
		this.json = json;

		_parseJson(json, this.basicPaymentProductGroups, this.accountsOnFile, this.basicPaymentProductGroupById, this.accountOnFileById);
	};

	connectsdk.BasicPaymentProductGroups = BasicPaymentProductGroups;
	return BasicPaymentProductGroups;
});
define("connectsdk.BasicPaymentItems", ["connectsdk.core"], function(connectsdk) {
	"use strict";

		var _parseJson = function (_products, _groups, _basicPaymentItems) {
		var doRemove = [];
		if (_groups) {
			for (var i = 0, il = _groups.basicPaymentProductGroups.length; i < il; i++) {
				var groupId = _groups.basicPaymentProductGroups[i].id,
						groupReplaced = false;
				for (var j = 0, jl = _products.basicPaymentProducts.length; j < jl; j++) {
					var productMethod = _products.basicPaymentProducts[j].paymentProductGroup;
					if (productMethod === groupId && groupReplaced === false) {
						// replace instance by group
						_products.basicPaymentProducts.splice(j, 1, _groups.basicPaymentProductGroups[i]);
						groupReplaced = true;
					} else if (productMethod === groupId && groupReplaced === true) {
						// mark for removal
						doRemove.push(j);
					}
				}
			}
			for (var i = doRemove.length -1, il = 0; i >= il; i--) {
				_products.basicPaymentProducts.splice(doRemove[i], 1);
			}
		}
		_basicPaymentItems.basicPaymentItems = JSON.parse(JSON.stringify(_products.basicPaymentProducts));
		for (var i = 0, il = _basicPaymentItems.basicPaymentItems.length; i < il; i++) {
			var basicPaymentItem = _basicPaymentItems.basicPaymentItems[i];
			_basicPaymentItems.basicPaymentItemById[basicPaymentItem.id] = basicPaymentItem;
			if (basicPaymentItem.accountsOnFile) {
				var aofs = basicPaymentItem.accountsOnFile;
				for (var j = 0, jl = aofs.length; j < jl; j++) {
					var aof = aofs[j];
					_basicPaymentItems.accountsOnFile.push(aof);
					_basicPaymentItems.accountOnFileById[aof.id] = aof;
				}
			}
		};
	};

	var BasicPaymentItems = function (products, groups) {
		this.basicPaymentItems = [];
		this.basicPaymentItemById = {};
		this.accountsOnFile = [];
		this.accountOnFileById = {};
		_parseJson(products, groups, this);
	};
	connectsdk.BasicPaymentItems = BasicPaymentItems;
	return BasicPaymentItems;
});
define("connectsdk.PaymentRequest", ["connectsdk.core"], function(connectsdk) {
  var PaymentRequest = function(clientSessionID) {
    var _clientSessionID = clientSessionID;
    var _fieldValues = {};
    var _paymentProduct = null;
    var _accountOnFile = null;
    var _tokenize = false;

    this.isValid = function() {
      var errors = this.getErrorMessageIds();
      // besides checking the fields for errors check if all mandatory fields are present as well
      var paymentProduct = this.getPaymentProduct();
      if (!paymentProduct) {
        return false;
      }
      var allRequiredFieldsPresent = true;
      for (var i = 0; i < paymentProduct.paymentProductFields.length; i++) {
        var field = paymentProduct.paymentProductFields[i];
        if (field.dataRestrictions.isRequired) {
          // is this field present in the request?
          var storedValue = this.getValue(field.id);
          if (!storedValue && !this.getAccountOnFile()) {
              // if we have an acoount on file the account on file could have the field, so we can ignore it
            allRequiredFieldsPresent = false;
          }
        }
      }
      return errors.length === 0 && allRequiredFieldsPresent;
    };
    this.setValue = function(paymentProductFieldId, value) {
      _fieldValues[paymentProductFieldId] = value;
    };
    this.setTokenize = function(tokenize) {
      _tokenize = tokenize;
    };
    this.getTokenize = function() {
      return _tokenize;
    };
    this.getErrorMessageIds = function() {
      var errors = [];
      for (key in _fieldValues) {
        var paymentProductField = _paymentProduct.paymentProductFieldById[key];
        if (paymentProductField) {
          errors = errors.concat(paymentProductField.getErrorCodes(_fieldValues[key]));
        }
      }
      return errors;
    };
    this.getValue = function(paymentProductFieldId) {
      return _fieldValues[paymentProductFieldId];
    };
    this.getValues = function() {
      return _fieldValues;
    };
    this.getMaskedValue = function(paymentProductFieldId) {
      var paymentProductField = _paymentProduct.paymentProductFieldById[paymentProductFieldId];
      var maskedString = paymentProductField.applyMask(this.getValue(paymentProductFieldId));
      return maskedString.formattedValue();
    };
    this.getMaskedValues = function() {
      var fields = _fieldValues;
      var result = [];
      for (var paymentProductFieldId in fields) {
        var paymentProductField = _paymentProduct.paymentProductFieldById[paymentProductFieldId];
        var maskedString = paymentProductField.applyMask(this.getValue(paymentProductFieldId));
        result[paymentProductFieldId] = maskedString.formattedValue;
      }
      return result;
    };
    this.getUnmaskedValues = function() {
      var fields = _fieldValues;
      var result = [];
      for (var paymentProductFieldId in fields) {
        var paymentProductField = _paymentProduct.paymentProductFieldById[paymentProductFieldId];
        if (paymentProductField) {
          var maskedString = paymentProductField.applyMask(this.getValue(paymentProductFieldId));
          var formattedValue = maskedString.formattedValue;
          result[paymentProductFieldId] = paymentProductField.removeMask(formattedValue);
        }
      }
      return result;
    };
    this.setPaymentProduct = function(paymentProduct) {
      if (paymentProduct.type === "group") {
        return;
      }
      _paymentProduct = paymentProduct;
    };
    this.getPaymentProduct = function() {
      return _paymentProduct;
    };
    this.setAccountOnFile = function(accountOnFile) {
      for (var i = 0, il = accountOnFile.attributes.length; i < il; i++) {
        var attribute = accountOnFile.attributes[i];
        delete _fieldValues[attribute.key];
      }
      _accountOnFile = accountOnFile;
    };
    this.getAccountOnFile = function() {
      return _accountOnFile;
    };
    this.getClientSessionID = function() {
		    return clientSessionID;
    };
  };
  connectsdk.PaymentRequest = PaymentRequest;
  return PaymentRequest;
});
define("connectsdk.C2SPaymentProductContext", ["connectsdk.core"], function(connectsdk) {

    var C2SPaymentProductContext = function (payload) {
        this.totalAmount = typeof payload.totalAmount !== 'undefined' ? payload.totalAmount : '';
        this.countryCode = payload.countryCode;
        this.isRecurring = typeof payload.isRecurring !== 'undefined' ? payload.isRecurring : '';
        this.currency = payload.currency;

        if (typeof payload.locale !== 'undefined') {
            this.locale = payload.locale;
        }

        if (typeof payload.accountOnFileId !== 'undefined') {
            this.accountOnFileId = parseInt(payload.accountOnFileId);
        }
    };

  connectsdk.C2SPaymentProductContext = C2SPaymentProductContext;
  return C2SPaymentProductContext;
});

define("connectsdk.JOSEEncryptor", ["connectsdk.core"], function(connectsdk) {

	var pki = forge.pki;
	var asn1 = forge.asn1;
	var CEKKEYLENGTH = 512;
	var IVLENGTH = 128;

	var base64UrlEncode = function(str) {
		str = forge.util.encode64(str);
		str = str.split('=')[0];
		str = str.replace(/\+/g, '-');
		str = str.replace(/\//g, '_');
		return str;
	};

	var createProtectedHeader = function(kid) {
		var JOSEHeader = {
			"alg" : "RSA-OAEP",
			"enc" : "A256CBC-HS512",
			"kid" : kid
		};
		return JSON.stringify(JOSEHeader);
	};

	var decodePemPublicKey = function(publickeyB64Encoded) {
		// step 1: base64decode
		var publickeyB64Decoded = forge.util.decode64(publickeyB64Encoded);
		// create a bytebuffer with these bytes
		var buffer2 = forge.util.createBuffer(publickeyB64Decoded, 'raw');
		// convert DER to ASN1 object
		var publickeyObject2 = forge.asn1.fromDer(buffer2);
		// convert to publicKey object
		var publicKey2 = pki.publicKeyFromAsn1(publickeyObject2);
		return publicKey2;
	};

	var encryptContentEncryptionKey = function(CEK, publicKey) {
		// encrypt CEK with OAEP+SHA-1+MGF1Padding
		var encryptedCEK = publicKey.encrypt(CEK, 'RSA-OAEP');
		return encryptedCEK;
	};

	var encryptPayload = function(payload, encKey, initializationVector) {
		var cipher = forge.cipher.createCipher('AES-CBC', encKey);
		cipher.start({
			iv : initializationVector
		});
		cipher.update(forge.util.createBuffer(payload));
		cipher.finish();
		return cipher.output.bytes();
	};

	var calculateAdditionalAuthenticatedDataLength = function(encodededProtectedHeader) {
		var buffer = forge.util.createBuffer(encodededProtectedHeader);
		var lengthInBits = buffer.length() * 8;

		var buffer2 = forge.util.createBuffer();
		// convert int to 64bit big endian
		buffer2.putInt32(0);
		buffer2.putInt32(lengthInBits);
		return buffer2.bytes();
	};

	var calculateHMAC = function(macKey, encodededProtectedHeader, initializationVector, cipherText, al) {
		var buffer = forge.util.createBuffer();
		buffer.putBytes(encodededProtectedHeader);
		buffer.putBytes(initializationVector);
		buffer.putBytes(cipherText);
		buffer.putBytes(al);

		var hmacInput = buffer.bytes();

		var hmac = forge.hmac.create();
		hmac.start(forge.sha512.create(), macKey);
		hmac.update(hmacInput);
		return hmac.digest().bytes();
	};

	var JOSEEncryptor = function() {

		this.encrypt = function(plainTextValues, publicKeyResponse) {
			// Create protected header and encode it with Base64 encoding
			var payload = JSON.stringify(plainTextValues);
			var protectedHeader = createProtectedHeader(publicKeyResponse.keyId);
			var encodededProtectedHeader = base64UrlEncode(protectedHeader);

			// Create ContentEncryptionKey, is a random byte[]
			var CEK = forge.random.getBytesSync(CEKKEYLENGTH / 8);
			var publicKey = decodePemPublicKey(publicKeyResponse.publicKey);

			// Encrypt the contentEncryptionKey with the GC gateway publickey and encode it with Base64 encoding
			var encryptedContentEncryptionKey = encryptContentEncryptionKey(CEK, publicKey);
			var encodedEncryptedContentEncryptionKey = base64UrlEncode(encryptedContentEncryptionKey);

			// Split the contentEncryptionKey in ENC_KEY and MAC_KEY for using hmac
			var macKey = CEK.substring(0, CEKKEYLENGTH / 2 / 8);
			var encKey = CEK.substring(CEKKEYLENGTH / 2 / 8);

			// Create Initialization Vector
			var initializationVector = forge.random.getBytesSync(IVLENGTH / 8);
			var encodededinitializationVector = base64UrlEncode(initializationVector);

			// Encrypt content with ContentEncryptionKey and Initialization Vector
			var cipherText = encryptPayload(payload, encKey, initializationVector);
			var encodedCipherText = base64UrlEncode(cipherText);

			// Create Additional Authenticated Data  and Additional Authenticated Data Length
			var al = calculateAdditionalAuthenticatedDataLength(encodededProtectedHeader);

			// Calculates HMAC
			var calculatedHmac = calculateHMAC(macKey, encodededProtectedHeader, initializationVector, cipherText, al);

			// Truncate HMAC Value to Create Authentication Tag
			var authenticationTag = calculatedHmac.substring(0, calculatedHmac.length / 2);
			var encodedAuthenticationTag = base64UrlEncode(authenticationTag);

			return encodededProtectedHeader + "." + encodedEncryptedContentEncryptionKey + "." + encodededinitializationVector + "." + encodedCipherText + "." + encodedAuthenticationTag;
		};
	};

	connectsdk.JOSEEncryptor = JOSEEncryptor;
	return JOSEEncryptor;
});
define("connectsdk.Encryptor", ["connectsdk.core", "connectsdk.promise", "connectsdk.JOSEEncryptor", "connectsdk.Util"], function(connectsdk, Promise, JOSEEncryptor, Util) {

	var _util = Util.getInstance();

	var Encryptor = function(publicKeyResponsePromise) {
		this.encrypt = function(paymentRequest) {
			var promise = new Promise();
			var encryptedString = '';
			publicKeyResponsePromise.then(function (publicKeyResponse) {
				if (paymentRequest.isValid()) {

					var blob = {
					   clientSessionId: paymentRequest.getClientSessionID()
					   ,nonce: forge.util.bytesToHex(forge.random.getBytesSync(16))
					   ,paymentProductId: paymentRequest.getPaymentProduct().id
                       ,tokenize: paymentRequest.getTokenize()
                    };

					if (paymentRequest.getAccountOnFile()) {
                        blob["accountOnFileId"] = paymentRequest.getAccountOnFile().id;
                    }

                    var paymentValues = [], values = paymentRequest.getUnmaskedValues();
                    var ownValues = Object.getOwnPropertyNames(values);
					for (var i = 0; i < ownValues.length; i++) {
						var propertyName = ownValues[i];
						if (propertyName !== "length") {
							paymentValues.push({
								key: propertyName,
								value: values[propertyName]
							})
						}
					}
                    blob["paymentValues"] = paymentValues;

					blob["collectedDeviceInformation"] = _util.collectDeviceInformation();

					// use blob to encrypt
					var joseEncryptor = new JOSEEncryptor();
					encryptedString = joseEncryptor.encrypt(blob, publicKeyResponse);
					promise.resolve(encryptedString);
				} else {
					promise.reject(paymentRequest.getErrorMessageIds());
				}
			}, function (error) {
				promise.reject(error);
			});
			return promise;
		};
	};

	connectsdk.Encryptor = Encryptor;
	return Encryptor;
});

define("connectsdk.Session", ["connectsdk.core", "connectsdk.C2SCommunicator", "connectsdk.C2SCommunicatorConfiguration", "connectsdk.IinDetailsResponse", "connectsdk.promise", "connectsdk.C2SPaymentProductContext", "connectsdk.BasicPaymentProducts", "connectsdk.BasicPaymentProductGroups", "connectsdk.PaymentProduct", "connectsdk.PaymentProductGroup", "connectsdk.BasicPaymentItems", "connectsdk.PaymentRequest", "connectsdk.Encryptor"], function (connectsdk, C2SCommunicator, C2SCommunicatorConfiguration, IinDetailsResponse, Promise, C2SPaymentProductContext, BasicPaymentProducts, BasicPaymentProductGroups, PaymentProduct, PaymentProductGroup, BasicPaymentItems, PaymentRequest, Encryptor) {
	var APIVERSION = "client/v1";
	var session = function (sessionDetails, paymentProduct) {

		var _c2SCommunicatorConfiguration = new C2SCommunicatorConfiguration(sessionDetails, APIVERSION),
			_c2sCommunicator = new C2SCommunicator(_c2SCommunicatorConfiguration, paymentProduct),
			_session = this,
			_paymentProductId, _paymentProduct, _paymentRequestPayload, _paymentRequest, _paymentProductGroupId, _paymentProductGroup;
		this.clientApiUrl = _c2SCommunicatorConfiguration.clientApiUrl;
		this.assetUrl = _c2SCommunicatorConfiguration.assetUrl;

		this.getBasicPaymentProducts = function (paymentRequestPayload, paymentProductSpecificInputs) {
			var promise = new Promise();
			var c2SPaymentProductContext = new C2SPaymentProductContext(paymentRequestPayload);
			_c2sCommunicator.getBasicPaymentProducts(c2SPaymentProductContext, paymentProductSpecificInputs).then(function (json) {
				_paymentRequestPayload = paymentRequestPayload;
				var paymentProducts = new BasicPaymentProducts(json);
				promise.resolve(paymentProducts);
			}, function () {
				promise.reject();
			});
			return promise;
		};

		this.getBasicPaymentProductGroups = function (paymentRequestPayload) {
			var promise = new Promise();
			var c2SPaymentProductContext = new C2SPaymentProductContext(paymentRequestPayload);
			_c2sCommunicator.getBasicPaymentProductGroups(c2SPaymentProductContext).then(function (json) {
				_paymentRequestPayload = paymentRequestPayload;
				var paymentProductGroups = new BasicPaymentProductGroups(json);
				promise.resolve(paymentProductGroups);
			}, function () {
				promise.reject();
			});
			return promise;
		};

		this.getBasicPaymentItems = function (paymentRequestPayload, useGroups, paymentProductSpecificInputs) {
			var promise = new Promise();
			// get products & groups
			if (useGroups) {
				_session.getBasicPaymentProducts(paymentRequestPayload, paymentProductSpecificInputs).then(function (products) {
					_session.getBasicPaymentProductGroups(paymentRequestPayload).then(function (groups) {
						var basicPaymentItems = new BasicPaymentItems(products, groups);
						promise.resolve(basicPaymentItems);
					}, function () {
						promise.reject();
					});
				}, function () {
					promise.reject();
				});
			} else {
				_session.getBasicPaymentProducts(paymentRequestPayload, paymentProductSpecificInputs).then(function (products) {
					var basicPaymentItems = new BasicPaymentItems(products, null);
					promise.resolve(basicPaymentItems);
				}, function () {
					promise.reject();
				});
			}
			return promise;
		};

		this.getPaymentProduct = function (paymentProductId, paymentRequestPayload, paymentProductSpecificInputs) {
			var promise = new Promise();
			_paymentProductId = paymentProductId;
			var c2SPaymentProductContext = new C2SPaymentProductContext(_paymentRequestPayload || paymentRequestPayload);
			_c2sCommunicator.getPaymentProduct(paymentProductId, c2SPaymentProductContext, paymentProductSpecificInputs).then(function (response) {
				_paymentProduct = new PaymentProduct(response);
				promise.resolve(_paymentProduct);
			}, function () {
				_paymentProduct = null;
				promise.reject();
			});
			return promise;
		};

		this.getPaymentProductGroup = function (paymentProductGroupId, paymentRequestPayload) {
			var promise = new Promise();
			_paymentProductGroupId = paymentProductGroupId;
			var c2SPaymentProductContext = new C2SPaymentProductContext(_paymentRequestPayload || paymentRequestPayload);
			_c2sCommunicator.getPaymentProductGroup(paymentProductGroupId, c2SPaymentProductContext).then(function (response) {
				_paymentProductGroup = new PaymentProductGroup(response);
				promise.resolve(_paymentProductGroup);
			}, function () {
				_paymentProductGroup = null;
				promise.reject();
			});
			return promise;
		};

		this.getIinDetails = function (partialCreditCardNumber, paymentRequestPayload) {
			partialCreditCardNumber = partialCreditCardNumber.replace(/ /g, '').substring(0, 6);
			var c2SPaymentProductContext = new C2SPaymentProductContext(_paymentRequestPayload || paymentRequestPayload);
			return _c2sCommunicator.getPaymentProductIdByCreditCardNumber(partialCreditCardNumber, c2SPaymentProductContext);
		};

		this.getPublicKey = function () {
			return _c2sCommunicator.getPublicKey();
		};

		this.getPaymentProductNetworks = function (paymentProductId, paymentRequestPayload) {
			var promise = new Promise();
			var c2SPaymentProductContext = new C2SPaymentProductContext(paymentRequestPayload);
			_c2sCommunicator.getPaymentProductNetworks(paymentProductId, c2SPaymentProductContext).then(function (response) {
				_paymentRequestPayload = paymentRequestPayload;
				promise.resolve(response);
			}, function () {
				promise.reject();
			});
			return promise;
		};

		this.getPaymentProductDirectory = function (paymentProductId, currencyCode, countryCode) {
			return _c2sCommunicator.getPaymentProductDirectory(paymentProductId, currencyCode, countryCode);
		};

		this.convertAmount = function (amount, source, target) {
			return _c2sCommunicator.convertAmount(amount, source, target);
		};

		this.getPaymentRequest = function () {
			if (!_paymentRequest) {
				_paymentRequest = new PaymentRequest(_c2SCommunicatorConfiguration.clientSessionId);
			}
			return _paymentRequest;
		};

		this.getEncryptor = function () {
			var publicKeyResponsePromise = _c2sCommunicator.getPublicKey();
			return new Encryptor(publicKeyResponsePromise);
		};

		this.getThirdPartyPaymentStatus = function (paymentId) {
			var promise = new Promise();
			_c2sCommunicator.getThirdPartyPaymentStatus(paymentId).then(function (response) {
				promise.resolve(response);
			}, function () {
				promise.reject();
			});
			return promise;
		};

		this.getCustomerDetails = function (paymentProductId, paymentRequestPayload) {
			return _c2sCommunicator.getCustomerDetails(paymentProductId, paymentRequestPayload);
		};

		/* In case a full JSON representation of a payment product is already available in context,
		   this method can be used instead of getPaymentProduct for the same (but synchronous) result. */
		this.transformPaymentProductJSON = function(json) {
			return new PaymentProduct(_c2sCommunicator.transformPaymentProductJSON(json))
		};

		/* In case a full JSON representation of a payment product group is already available in context,
		   this method can be used instead of getPaymentProductGroup for the same (but synchronous) result. */
		this.transformPaymentProductGroupJSON = function(json) {
			return new PaymentProductGroup(_c2sCommunicator.transformPaymentProductJSON(json))
		};
	};
	connectsdk.Session = session;
	return session;
});
