
require.config({
    context: "oelivesupport",
    baseUrl: {{url | json}} + "/im_livechat/static/ext/static/js",
    shim: {
        underscore: {
            init: function() {
                return _.noConflict();
            },
        },
        "jquery.achtung": {
            deps: ['jquery'],
        },
    },
})(["livesupport", "jquery"], function(livesupport, jQuery) {
    jQuery.noConflict();
    livesupport.main({{url | json}}, {{db | json}}, "anonymous", "anonymous", {{channel | json}}, {
        buttonText: {{buttonText | json}},
        inputPlaceholder: {{inputPlaceholder | json}},
        defaultMessage: {{(defaultMessage or None) | json}},
        auto: window.oe_im_livechat_auto || false,
        userName: {{userName | json}} || undefined,
    });
});
