odoo.define('web.public.lazyloader', function (require) {
'use strict';

var doResolve = null;
var _allScriptsLoaded = new Promise(function (resolve) {
    if (doResolve) {
        resolve();
    } else {
        doResolve = resolve;
    }
});

window.addEventListener('load', function () {
    setTimeout(_loadScripts, 0);
});

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
