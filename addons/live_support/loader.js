
require.config({
    context: "oelivesupport",
    baseUrl: {{url | json}} + "/live_support/static/ext/static/js",
    shim: {
        underscore: {
            init: function() {
                return _.noConflict();
            },
        },
    },
})(["livesupport", "jquery"], function(livesupport, jQuery) {
    jQuery.noConflict();
    livesupport.main({{url | json}}, {{db | json}}, "anonymous", "anonymous", {{channel | json}}, {
        buttonText: {{buttonText | json}},
        inputPlaceholder: {{inputPlaceholder | json}},
        defaultMessage: {{(defaultMessage or None) | json}},
        auto: window.oe_live_support_auto || false,
    });
});
