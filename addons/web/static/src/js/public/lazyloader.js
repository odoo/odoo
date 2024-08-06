odoo.define('web.public.lazyloader', function (require) {
'use strict';

var blockEvents = ['submit', 'click'];
var blockFunction = function (ev) {
    ev.preventDefault();
    ev.stopImmediatePropagation();
};

var waitingLazy = false;

/**
 * Blocks the DOM sections which explicitly require the lazy loaded JS to be
 * working (those sections should be marked with the 'o_wait_lazy_js' class).
 *
 * @see stopWaitingLazy
 */
function waitLazy() {
    if (waitingLazy) {
        return;
    }
    waitingLazy = true;

    var lazyEls = document.querySelectorAll('.o_wait_lazy_js');
    for (var i = 0; i < lazyEls.length; i++) {
        var element = lazyEls[i];
        blockEvents.forEach(function (evType) {
            element.addEventListener(evType, blockFunction);
        });
    }

    document.body.classList.add('o_lazy_js_waiting');
}
/**
 * Unblocks the DOM sections blocked by @see waitLazy and removes the related
 * 'o_wait_lazy_js' class from the whole DOM.
 */
function stopWaitingLazy() {
    if (!waitingLazy) {
        return;
    }
    waitingLazy = false;

    var lazyEls = document.querySelectorAll('.o_wait_lazy_js');
    for (var i = 0; i < lazyEls.length; i++) {
        var element = lazyEls[i];
        blockEvents.forEach(function (evType) {
            element.removeEventListener(evType, blockFunction);
        });
        element.classList.remove('o_wait_lazy_js');
    }

    document.body.classList.remove('o_lazy_js_waiting');
}

// Start waiting for lazy loading as soon as the DOM is available
if (document.readyState !== 'loading') {
    waitLazy();
} else {
    document.addEventListener('DOMContentLoaded', function () {
        waitLazy();
    });
}

// As soon as everything is fully loaded, start loading all the remaining JS
// and unblock the related DOM section when all of it have been loaded and
// executed
var doResolve = null;
var _allScriptsLoaded = new Promise(function (resolve) {
    if (doResolve) {
        resolve();
    } else {
        doResolve = resolve;
    }
}).then(function () {
    stopWaitingLazy();
});
if (document.readyState === 'complete') {
    setTimeout(_loadScripts, 0);
} else {
    window.addEventListener('load', function () {
        setTimeout(_loadScripts, 0);
    });
}

/**
 * @param {DOMElement[]} scripts
 * @param {integer} index
 */
function _loadScripts(scripts, index) {
    if (scripts === undefined) {
        scripts = document.querySelectorAll('script[data-src]');
    }
    if (index === undefined) {
        index = 0;
    }
    if (index >= scripts.length) {
        if (typeof doResolve === 'function') {
            doResolve();
        } else {
            doResolve = true;
        }
        return;
    }
    var script = scripts[index];
    script.addEventListener('load', _loadScripts.bind(this, scripts, index + 1));
    script.src = script.dataset.src;
    script.removeAttribute('data-src');
}

return {
    loadScripts: _loadScripts,
    allScriptsLoaded: _allScriptsLoaded,
};
});
