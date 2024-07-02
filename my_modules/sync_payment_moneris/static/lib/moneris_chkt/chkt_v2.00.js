window.onload = function ()
{
    window.onbeforeunload = function (e)
    {
        e = e || window.event;
        var msg = {};
        msg["handler"] = "page_closed";
        msg["response_code"] = "001";
        window.parent.postMessage(JSON.stringify(msg), '*');
    };
};
var monerisCheckout = (function()
    {
        var mode = "";
        var request_url = "";
        var checkout_div = "moneris-checkout";
        var fullscreen = "T";
        //Callbacks that modify checkout behaviour
        var update_callbacks = {payment_submit: "", //Delay starting transaction until callback is complete.
                                remove_back_button: ""}; //set this callback to remove back button from checkout form and receipt page.

        var callbacks ={page_loaded : "",
                        cancel_transaction : "",
                        payment_receipt : "",
                        payment_complete : "",
                        error_event : "",
                        payment_submit: "",
                        remove_back_button: "",
                        page_closed: "",
                        payment_submitted: "",
                        validation_event: "",
                    };

        function monerisCheckout ()
        {
            var me = this;
            /*
            window.addEventListener('message', function(e)
                {
                console.log("setting receive message");
                me.receivePostMessage(e);
            });
            */

            var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
            var eventHandler = window[eventMethod];
            var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";
            eventHandler(messageEvent, me.receivePostMessage, false);
        };

        monerisCheckout.prototype.logConfig = function()
        {
            //console.log("callbacks: " + JSON.stringify(callbacks));
            console.log("request_url: " + request_url);
            console.log("checkout_div: " + checkout_div);
        };

        monerisCheckout.prototype.setCheckoutDiv = function(name)
        {
            checkout_div = name;
        };

        monerisCheckout.prototype.setMode = function(setmode)
        {
            mode = setmode;
            console.log("mode: ", mode)
            //Verify src environment of chkt.js
            var scriptSource = document.querySelector('script[src*="chkt_v2.00.js"]');
            if (scriptSource)
            {
                var currentScript = scriptSource.src;
                if (currentScript)
                {
                    var scriptURLPattern = currentScript.match(/^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i); //extract host name
                    var scriptHostName = scriptURLPattern && scriptURLPattern[1];
                    if (scriptHostName)
                    {
                        checkoutHostNames = {'dev': 'gatewaydev.moneris.com', 'intl': 'gatewayqa.moneris.com', 'qa': 'gatewayt.moneris.com', 'prod': 'gateway.moneris.com'}
                        if (checkoutHostNames[mode] !== scriptHostName)
                        {
                            console.warn("setMode environment does not match src environment of chkt_v1.00.js");
                        }
                    }
                }
            }

            if (mode == 'dev')
            {
                if (currentScript)
                {
                    const pathArray = currentScript.match((/gatewaydev.moneris.com\/[\S]+\/js/))[0].split("/");
                    var scriptPathName = pathArray.slice(1, pathArray.length-1).join("/");
                }
                else
                {
                    var scriptPathName = "chkt";
                }

                request_url = "https://gatewaydev.moneris.com/" + scriptPathName + "/display/index.php";
            }
            else if (mode == 'intl')
            {
                request_url = "https://gatewayqa.moneris.com/chktv2/display/index.php";
            }
            else if (mode == 'qa')
            {
                request_url = "https://gatewayt.moneris.com/chktv2/display/index.php";
            }
            else
            {
                request_url = "https://gateway.moneris.com/chktv2/display/index.php";
            }
        };

        monerisCheckout.prototype.setCallback = function(name,func)
        {
            if (name in callbacks)
            {
                callbacks[name] = func;

                if (name in update_callbacks)
                {
                    update_callbacks[name] = true;
                }
            }
            else
            {
                console.log("setCallback - Invalid callback defined: " + name);
            }
        };

        monerisCheckout.prototype.startCheckout = function(ticket)
        {
            fullscreen = ticket.slice(-1);

            console.log("fullscreen is : " + fullscreen);

            document.getElementById(checkout_div).innerHTML = "";
            checkoutUrl = request_url + "?tck="+ticket;

            var chkt_target =  document.getElementById(checkout_div);

            this.showLoadingSpinner(checkout_div); //Start client side spinner

            if (navigator.userAgent.match(/(iPod|iPhone|iPad)/))
            {
                //$("#"+checkout_div).css({ "position":"absolute", "left":"0", "top":"0", "border":"none", "background":"#FAFAFA", "z-index":"100000","min-width":"100%","width":"100%","min-height":"100%","height":"100%" });

                if (fullscreen == 'T')
                {
                    chkt_target.style.position = 'absolute';
                    chkt_target.style.left = '0';
                    chkt_target.style.top = '0';
                }

                chkt_target.style.border = 'none';
                chkt_target.style.background = '#FAFAFA';
                chkt_target.style.zindex = '100000';
                chkt_target.style.minWidth = '100%';
                chkt_target.style.width = '100%';
                chkt_target.style.minHeight = '100%';
                chkt_target.style.height = '100%';

                var chkt_iframe = document.createElement('iframe');
                chkt_iframe.setAttribute('id', checkout_div+'-Frame');
                chkt_iframe.setAttribute('src', checkoutUrl);
                chkt_iframe.setAttribute('allowpaymentrequest', 'true');
                chkt_iframe.setAttribute('title', 'Payment Details');
                chkt_iframe.style.width = '100%';
                chkt_iframe.style.height = '100%';
                chkt_iframe.style.border = 'none';

                chkt_target.appendChild(chkt_iframe);

                if (fullscreen == 'T')
                {

                    var chkt_html_css = document.createElement('style');
                    chkt_html_css.type = 'text/css';
                    var chkt_html_style = ".checkoutHtmlStyleFromiFrame { max-width:100%; width:100%; overflow:hidden !important; }"

                    if (chkt_html_css.styleSheet) chkt_html_css.styleSheet.cssText = chkt_html_style;
                    else chkt_html_css.appendChild(document.createTextNode(chkt_html_style));

                    document.body.classList.add("checkoutHtmlStyleFromiFrame");
                }
            }
            else
            {
                if (fullscreen == 'T')
                {
                    chkt_target.style.position = 'fixed';
                    chkt_target.style.left = '0';
                    chkt_target.style.top = '0';
                }
                chkt_target.style.border = 'none';
                chkt_target.style.background = '#FAFAFA';
                chkt_target.style.zindex = '100000';
                chkt_target.style.minWidth = '100%';
                chkt_target.style.width = '100%';
                chkt_target.style.minHeight = '100%';
                chkt_target.style.height = '100%';

                var chkt_iframe = document.createElement('iframe');
                chkt_iframe.setAttribute('id', checkout_div+'-Frame');
                chkt_iframe.setAttribute('src', checkoutUrl);
                chkt_iframe.setAttribute('allowpaymentrequest', 'true');
                chkt_iframe.setAttribute('title', 'Payment Details');
                chkt_iframe.style.width = '100%';
                chkt_iframe.style.height = '100%';
                chkt_iframe.style.border = 'none';

                chkt_target.appendChild(chkt_iframe);

                if (fullscreen == 'T')
                {
                    var chkt_html_css = document.createElement('style');
                    chkt_html_css.type = 'text/css';
                    var chkt_html_style = ".checkoutHtmlStyleFromiFrame { position:fixed; width:100%; overflow:hidden !important; }"

                    if (chkt_html_css.styleSheet) chkt_html_css.styleSheet.cssText = chkt_html_style;
                    else chkt_html_css.appendChild(document.createTextNode(chkt_html_style));

                    document.body.classList.add("checkoutHtmlStyleFromiFrame");
                }
            }

            chkt_iframe.onload = function() //Hide spinner when checkout iframe has loaded
            {
                document.getElementById("moneris-loading-container").style.display = "none"; //Hide client side spinner
            }

            return;
        };

        monerisCheckout.prototype.showLoadingSpinner = function(checkout_div)
        {
            var spinner_div = document.createElement('div');
            spinner_div.setAttribute('id', 'moneris-loading-container');

            /* Add styling/animation for spinner */
            var link = document.createElement('link');
            link.setAttribute('rel', 'stylesheet');
            var root_url = request_url.split('/').slice(0,-2).join('/'); //remove /display/index.php
            link.setAttribute('href', root_url + '/style/loading-spinner.css');
            document.head.appendChild(link);

            /* SPINNER HTML */
            var spinner = "<div class=\"moneris-spinner-1\"></div><div class=\"moneris-spinner-2\"></div>";
            spinner_div.innerHTML = spinner;

            /* Add to main checkout div */
            var chkt_target =  document.getElementById(checkout_div);
            chkt_target.appendChild(spinner_div);
        };

        monerisCheckout.prototype.startCheckoutHandler = function(response)
        {
            if (response.success == 'true')
            {
                console.log(response.url);
                //insert iframe into div #moneris-checkout
            }
            else
            {
                callbacks.error_event(response.error);
            }
        };

        monerisCheckout.prototype.sendFrameMessage = function(requestAction)
        {
            var frameRef = document.getElementById(checkout_div+"-Frame").contentWindow;
            var request = JSON.stringify({action: requestAction});
            frameRef.postMessage(request, request_url);
        };

        monerisCheckout.prototype.sendPostMessage = function(request)
        {
            var frameRef = document.getElementById(checkout_div+"-Frame").contentWindow;
            frameRef.postMessage(request,request_url+'chkt/display/request.php');
            return false;
        };

        monerisCheckout.prototype.receivePostMessage = function(resp)
        {
            try
            {
                var response_json = resp.data;
                var respObj = JSON.parse(response_json);

                if (respObj.rev_action == 'height_change')
                {
                    console.log ("this is new height:" + respObj.outerHeight);

                    document.getElementById(checkout_div+"-Frame").style.height = respObj.outerHeight + "px";

                //  $("#"+checkout_div+"-Frame").css({"height":  respObj.outerHeight + "px"});
                //  $("#"+checkout_div).css({"height":  respObj.outerHeight + "px"});

                }
                else
                {
                    if (respObj["handler"] == "close_checkout")
                    {
                        var chkt_target =  document.getElementById(checkout_div);

                        chkt_target.style.position = 'static';
                        chkt_target.style.width = '0px';
                        chkt_target.style.minHeight = '0px';
                        chkt_target.style.height = '0px%';

                        document.getElementById(checkout_div).innerHTML = "";
                        document.body.classList.remove("checkoutHtmlStyleFromiFrame");
                    }
                    else if (respObj["handler"] == "get_callbacks")
                    {
                        //Update checkout on which update_callbacks are registered.
                        var frameRef = document.getElementById(checkout_div+"-Frame").contentWindow;
                        var request = JSON.stringify({action: "callbacks", data: update_callbacks});
                        frameRef.postMessage(request, request_url);
                    }
                    else if (respObj["handler"].split('_')[0] == 'ap')
                    {
                        var frameRef = document.getElementById(checkout_div+"-Frame").contentWindow;
                        if (respObj["handler"] == "ap_button_request")
                        {
                            if (window.ApplePaySession)
                            {
                                if (ApplePaySession.canMakePayments() && ApplePaySession.supportsVersion(3))
                                {
                                    var request = JSON.stringify({action: "ap_display_button"});
                                    frameRef.postMessage(request, request_url);
                                }
                                else
                                {
                                    var request = JSON.stringify({action: "ap_disable"});
                                    frameRef.postMessage(request, request_url);
                                }
                            }
                            else
                            {
                                var request = JSON.stringify({action: "ap_disable"});
                                frameRef.postMessage(request, request_url);
                            }
                        }
                        else if (respObj["handler"] == "ap_start_session")
                        {
                            session = new ApplePaySession(3, respObj["data"]); //version 3 minimum

                            session.oncancel = function(event) {
                                var request = JSON.stringify({action: "ap_cancel"});
                                frameRef.postMessage(request, request_url);
                            };

                            session.onvalidatemerchant = function(event) {
                                var request = JSON.stringify({action: "ap_request_session_validation", data: event.validationURL});
                                frameRef.postMessage(request, request_url);
                            };

                            session.onpaymentauthorized = function(event) {
                                var request = JSON.stringify({action: "ap_start_transaction", data: event.payment});
                                frameRef.postMessage(request, request_url);
                            };

                            session.begin();
                        }
                        else if (respObj["handler"] == "ap_complete_session_validation")
                        {
                            if (respObj["data"].success === "true")
                            {
                                session.completeMerchantValidation(JSON.parse(respObj["data"].session));
                            }
                            else
                            {
                                session.abort(); //Dismiss payment window
                            }
                        }
                        else if (respObj["handler"] == "ap_error")
                        {
                            apErrs = []; //can be multiple errors
                            for (var key in respObj["data"])
                            {
                                if (respObj["data"][key].field.charAt(0) == 'b') //billing errors
                                {
                                    apFieldError = new ApplePayError("billingContactInvalid", respObj["data"][key].apError, respObj["data"][key].message);

                                }
                                else //shipping errors
                                {
                                    apFieldError = new ApplePayError("shippingContactInvalid", respObj["data"][key].apError, respObj["data"][key].message);

                                }
                                apErrs.push(apFieldError);
                            }
                            session.completePayment({
                                        status: ApplePaySession.STATUS_FAILURE,
                                        errors: apErrs
                            });
                        }
                        else if (respObj["handler"] == "ap_complete_transaction")
                        {
                            if (respObj["data"] === "a")
                            {
                                session.completePayment(ApplePaySession.STATUS_SUCCESS);
                            }
                            else
                            {
                                session.completePayment(ApplePaySession.STATUS_FAILURE);
                            }
                        }
                    }
                    else if (respObj["handler"] == "page_loaded")
                    {
                        document.getElementById("moneris-loading-container").style.display = "none"; //Hide client side spinner

                        //Resume flow with merchants callback
                        var callback = callbacks[respObj["handler"]];
                        if (typeof callback === "function")
                        {
                            callback(response_json);
                        }
                    }
                    else
                    {
                        var callback = callbacks[respObj["handler"]];
                        if (typeof callback === "function")
                        {
                            callback(response_json);
                        }
                    }
                }
            }
            catch(e)
            {
                //console.log("got a non standard post message");
                console.log(e);
            }
        };

        monerisCheckout.prototype.closeCheckout = function()
        {
            this.sendFrameMessage("close_request");
        };

        monerisCheckout.prototype.setNewShippingRates = function(json)
        {
            this.sendPostMessage(json);
        };

        monerisCheckout.prototype.startTransaction = function(json)
        {
            this.sendFrameMessage("start_transaction");
        };

        return monerisCheckout;
    })();


