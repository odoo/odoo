import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_error_website', {
    url: '/test_error_view',
    steps: () => [
    // RPC ERROR
    {
        content: "trigger rpc user error",
        trigger: 'a[href="/test_user_error_json"]',
        run: "click",
    },
    {
        trigger: 'div.o_notification_content:contains("This is a user rpc test")',
    },
    {
        content: "rpc user error modal has message",
        trigger: 'button.o_notification_close',
        run: "click",
    }, {
        content: "trigger rpc access error",
        trigger: 'a[href="/test_access_error_json"]',
        run: "click",
    },
    {
        trigger: 'div.o_notification_content:contains("This is an access rpc test")',
    },
    {
        content: "rpc access error modal has message",
        trigger: 'button.o_notification_close',
        run: "click",
    }, {
        content: "trigger validation rpc error",
        trigger: 'a[href="/test_validation_error_json"]',
        run: "click",
    },
    {
        trigger: 'div.o_notification_content:contains("This is a validation rpc test")',
    },
    {
        content: "rpc validation error modal has message",
        trigger: 'button.o_notification_close',
        run: "click",
    }, {
        content: "trigger rpc missing error",
        trigger: 'a[href="/test_missing_error_json"]',
        run: "click",
    },
    {
        trigger: 'div.o_notification_content:contains("This is a missing rpc test")',
    },
    {
        content: "rpc missing error modal has message",
        trigger: 'button.o_notification_close',
        run: "click",
    }, {
        content: "trigger rpc error 403",
        trigger: 'a[href="/test_access_denied_json"]',
        run: "click",
    },
    {
        trigger: 'div.o_notification_content:contains("This is an access denied rpc test")',
    },
    {
        content: "rpc error 403 modal has message",
        trigger: 'button.o_notification_close',
        run: "click",
    }, {
        content: "trigger rpc error 500",
        trigger: 'a[href="/test_internal_error_json"]',
        run: "click",
    },
    {
        trigger: "div.o_error_dialog.modal-content",
    },
    {
        content: "rpc error 500 modal is an ErrorDialog",
        trigger: '.modal-footer button.btn.btn-primary',
        run: "click",
    },
    // HTTP ERROR
    {
        content: "trigger http user error",
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/test_user_error_http?debug=0';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Something went wrong.")',
    },
    {
        content: "http user error page has title and message",
        trigger: 'div.container pre:contains("This is a user http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_user_error_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Something went wrong.")',
    },
    {
        content: "http user error page debug has title and message open",
        trigger: 'div#error_main.collapse.show pre:contains("This is a user http test")',
    }, {
        content: "http user error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_validation_error_http?debug=0';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Something went wrong.")',
    },
    {
        content: "http validation error page has title and message",
        trigger: 'div.container pre:contains("This is a validation http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_validation_error_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Something went wrong.")',
    },
    {
        content: "http validation error page debug has title and message open",
        trigger: 'div#error_main.collapse.show pre:contains("This is a validation http test")',
    }, {
        content: "http validation error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_access_error_http?debug=0';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http access error page has title and message",
        trigger: 'div.container pre:contains("This is an access http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_access_error_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http access error page debug has title and message open",
        trigger: 'div#error_main.collapse.show pre:contains("This is an access http test")',
    }, {
        content: "http access error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_view_access_error?debug=0';
        },
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http access error page has title and message",
        trigger: 'div.container pre:contains("Uh-oh! Looks like you have stumbled upon some top-secret records.")',
        run: function () {
                window.location.href = window.location.origin + '/test_view_access_error?debug=1';
        },
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http access error page debug has title and message open",
        trigger: 'div#error_main.collapse.show pre:contains("Uh-oh! Looks like you have stumbled upon some top-secret records.")',
    }, {
        content: "http access error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_missing_error_http?debug=0';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Error 404")',
        run: function () {
                window.location.href = window.location.origin + '/test_missing_error_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("Error 404")',
        run: function () {
            window.location.href = window.location.origin + '/test_access_denied_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http error 403 page has title but no message",
        // See http.py _transactionning, the exception is replaced so there is no message !
        trigger: 'div#wrap:not(:has(pre:contains("Traceback"))',
        run: function () {
            window.location.href = window.location.origin + '/test_access_denied_http?debug=1';
        },
        expectUnloadPage: true,
    },
    {
        trigger: 'h1:contains("403: Forbidden")',
    },
    {
        content: "http 403 error page debug has title but no message",
        trigger: 'div#wrap:not(:has(pre:contains("Traceback"))',
    },
]});
