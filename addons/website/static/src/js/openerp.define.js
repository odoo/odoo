(function () {
    'use strict';

var containsDefine = typeof(define) !== "undefined" ? define : undefined;

openerp.Define = function (parse) {
    var scripts = openerp.Define.scripts;
    
    return containsDefine ?
        containsDefine :
        function (required, list, callback) {

            var def = $.Deferred();
            def.openerpDefine = true;

            if (!callback) {
                callback = list;
                list = null;
            }
            if (list) {
                required = list;
            }

            if (required instanceof Array) {
                var defs = [];
                var args = [];
                _.each(required, function (js, index) {
                    var path = parse(js);

                    if (scripts[path] === undefined) {

                        scripts[path] = $.Deferred();
                        scripts[path].openerpDefine = true;

                        $.ajax({ 'url': path, 'dataType': 'html', 'async': false })
                            .then(function (data) {
                                var code = new Function("return "+data)();
                                if (code.openerpDefine) {
                                    code.then(function (code) {
                                        scripts[path].resolve(code);
                                        scripts[path] = code;
                                    });
                                } else {
                                    scripts[path].resolve(code);
                                    scripts[path] = code;
                                }
                            });

                    }

                    if (scripts[path] && scripts[path].openerpDefine) {
                        scripts[path].then(function (code) {
                            args[index] = code;
                        });
                        defs.push(scripts[path]);
                    } else {
                        args[index] = scripts[path] = scripts[path] || null;
                    }
                });

                $.when.apply($, defs).then(function () {
                    def.resolve(callback.apply(window, args));
                });

            } else {

                def = scripts[required] = scripts[required] || callback() || null;

            }

            return def;

        };
};

openerp.Define.scripts = {
    'jquery': jQuery
};


openerp.activeDefine = function () {
    window.define = openerp.Define(function (id) {

        if (id.slice(0,10) === 'summernote') {
            return '/website/static/lib/summernote/src/js' + id.slice(10,Infinity) + '.js';
        }
        return id;
    });
};
openerp.desactiveDefine = function () {
    window.define = containsDefine;
};


})();