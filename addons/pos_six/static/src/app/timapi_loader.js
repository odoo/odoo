/** @odoo-module ignore **/
(function () {
    window.Module = window.Module || {};
    window.Module.locateFile = function (path, scriptDirectory) {
        if (path.endsWith("timapi.wasm")) {
            return "/pos_six/static/lib/six_timapi/timapi.wasm";
        }
        return (scriptDirectory || "") + path;
    };
})();
