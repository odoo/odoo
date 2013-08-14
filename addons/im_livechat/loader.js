
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
    },
    shim: {
        underscore: {
            init: function() {
                return _.noConflict();
            },
        },
        qweb2: {
            init: function() {
                // TODO: better solution to avoid contamination of global namespace
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
    /*
    livesupport.main({{url | json}}, {{db | json}}, "anonymous", "anonymous", {{channel | json}}, {
        buttonText: {{buttonText | json}},
        inputPlaceholder: {{inputPlaceholder | json}},
        defaultMessage: {{(defaultMessage or None) | json}},
        auto: window.oe_im_livechat_auto || false,
        userName: {{userName | json}} || undefined,
    });*/
});
