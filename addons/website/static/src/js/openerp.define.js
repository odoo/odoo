odoo.define('website.define', function () {
'use strict';

var containsDefine = typeof(define) !== "undefined" ? define : undefined;
var scripts = {
    'jquery': jQuery
};

function odoo_define(parse) {
    return function (name, list, callback) {

        var def = $.Deferred();
        def.openerpDefine = true;

        if (!callback) {
            callback = list;
            list = null;
        }
        if (!list) {
            list = name;
            if (odoo.website_next_define) {
                name = odoo.website_next_define;
                odoo.website_next_define = null;
            }
        }

        if (list instanceof Array) {
            var defs = [];
            var args = [];
            _.each(list, function (js, index) {
                var path = parse(js);

                if (!(path in scripts)) {

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
                var result = callback.apply(window, args);
                if  (name) {
                    scripts[name] = scripts[parse(name)] = result;
                }
                def.resolve(result);
            });

        } else {

            def = scripts[name] = scripts[parse(name)] = scripts[name] || callback() || null;

        }

        return def;
    }
}

function enable() {
    window.define = odoo_define(function (id) {

        if (id.slice(0,10) === 'summernote') {
            return '/website/static/lib/summernote/src/js' + id.slice(10,Infinity) + '.js';
        }
        return id;
    });
}

function disable() {
    window.define = containsDefine;
}

odoo.website_next_define = undefined;
odoo.enable_website_define = enable;
odoo.disable_website_define = disable;

return {
    enable: enable,
    disable: disable,
    define: odoo_define,
    scripts: scripts,
};

});
