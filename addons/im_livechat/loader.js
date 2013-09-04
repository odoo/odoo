
(function() {

var tmpQWeb2 = window.QWeb2;

require.config({
    context: "oelivesupport",
    baseUrl: {{url | json}},
    paths: {
        jquery: "im_livechat/static/ext/static/lib/jquery/jquery",
        underscore: "im_livechat/static/ext/static/lib/underscore/underscore",
        qweb2: "im_livechat/static/ext/static/lib/qweb/qweb2",
        openerp: "web/static/src/js/openerpframework",
        "jquery.achtung": "im_livechat/static/ext/static/lib/jquery-achtung/src/ui.achtung",
        livesupport: "im_livechat/static/ext/static/js/livesupport",
        im_common: "im/static/src/js/im_common"
    },
    shim: {
        underscore: {
            init: function() {
                return _.noConflict();
            },
        },
        qweb2: {
            init: function() {
                var QWeb2 = window.QWeb2;
                window.QWeb2 = tmpQWeb2;
                return QWeb2;
            },
        },
        "jquery.achtung": {
            deps: ['jquery'],
        },
    },
})(["livesupport", "jquery"], function(livesupport, jQuery) {
    jQuery.noConflict();
    console.log("loaded live support");
    livesupport.main({{url | json}}, {{db | json}}, "public", "public", {{channel | json}}, {
        buttonText: {{buttonText | json}},
        inputPlaceholder: {{inputPlaceholder | json}},
        defaultMessage: {{(defaultMessage or None) | json}},
        auto: window.oe_im_livechat_auto || false,
        userName: {{userName | json}} || undefined,
    });
});

})();
