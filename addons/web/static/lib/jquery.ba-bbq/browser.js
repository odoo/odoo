/*
This chunk of code is the (slightly adapted) browser helper from jQuery, deprecated
since the 1.9 version. As we don't want to include jquery.migrate and we don't want to monkey-patch
jquery, we set the browser variable on the window object. This is a temporary solution as we should
stop using jquery.bbq: it's not maintained anymore.
https://github.com/jquery/jquery-migrate/blob/master/src/core.js#L67
https://github.com/cowboy/jquery-bbq
*/
(function() {

if ( !window.browser ) {
    uaMatch = function( ua ) {
        ua = ua.toLowerCase();

        var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
            /(webkit)[ \/]([\w.]+)/.exec( ua ) ||
            /(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
            /(msie) ([\w.]+)/.exec( ua ) ||
            ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) ||
            [];

        return {
            browser: match[ 1 ] || "",
            version: match[ 2 ] || "0"
        };
    };

    var matched = uaMatch( navigator.userAgent );
    var browser = {};

    if ( matched.browser ) {
        browser[ matched.browser ] = true;
        browser.version = matched.version;
    }

    // Chrome is Webkit, but Webkit is also Safari.
    if ( browser.chrome ) {
        browser.webkit = true;
    } else if ( browser.webkit ) {
        browser.safari = true;
    }

    window.browser = browser;
}

})();
