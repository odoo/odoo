odoo.define('web.public.lazyloader', function (require) {
'use strict';

var blockEvents = ['submit', 'click'];
var blockFunction = function (ev) {
    ev.preventDefault();
    ev.stopImmediatePropagation();
};

// Track when all JS files have been lazy loaded. Will allow to unblock the
// related DOM sections when the whole JS have been loaded and executed.
let allScriptsLoadedResolve = null;
const _allScriptsLoaded = new Promise(resolve => {
    allScriptsLoadedResolve = resolve;
}).then(stopWaitingLazy);

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

// As soon as the document is fully loaded, start loading the whole remaining JS
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
        allScriptsLoadedResolve();
        return;
    }
    const script = scripts[index];
    script.addEventListener('load', _loadScripts.bind(this, scripts, index + 1));
    script.src = script.dataset.src;
    script.removeAttribute('data-src');
}

return {
    loadScripts: _loadScripts,
    allScriptsLoaded: _allScriptsLoaded,
};
});
