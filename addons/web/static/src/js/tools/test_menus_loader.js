odoo.define('web.clickEverywhere', function (require) {
    "use strict";
    var ajax = require('web.ajax');
    function startClickEverywhere(xmlId, appsMenusOnly) {
        ajax.loadJS('web/static/src/js/tools/test_menus.js').then(
            function() {
                // eslint-disable-next-line no-undef
                clickEverywhere(xmlId, appsMenusOnly);
            }
        );
    }
    return startClickEverywhere;
});
