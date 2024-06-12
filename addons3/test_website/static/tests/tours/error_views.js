/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_error_website', {
    test: true,
    url: '/test_error_view',
    steps: () => [
    // RPC ERROR
    {
        content: "trigger rpc user error",
        trigger: 'a[href="/test_user_error_json"]',
    }, {
        content: "rpc user error modal has message",
        extra_trigger: 'div.o_notification_content:contains("This is a user rpc test")',
        trigger: 'button.o_notification_close',
    }, {
        content: "trigger rpc access error",
        trigger: 'a[href="/test_access_error_json"]',
    }, {
        content: "rpc access error modal has message",
        extra_trigger: 'div.o_notification_content:contains("This is an access rpc test")',
        trigger: 'button.o_notification_close',
    }, {
        content: "trigger validation rpc error",
        trigger: 'a[href="/test_validation_error_json"]',
    }, {
        content: "rpc validation error modal has message",
        extra_trigger: 'div.o_notification_content:contains("This is a validation rpc test")',
        trigger: 'button.o_notification_close',
    }, {
        content: "trigger rpc missing error",
        trigger: 'a[href="/test_missing_error_json"]',
    }, {
        content: "rpc missing error modal has message",
        extra_trigger: 'div.o_notification_content:contains("This is a missing rpc test")',
        trigger: 'button.o_notification_close',
    }, {
        content: "trigger rpc error 403",
        trigger: 'a[href="/test_access_denied_json"]',
    }, {
        content: "rpc error 403 modal has message",
        extra_trigger: 'div.o_notification_content:contains("This is an access denied rpc test")',
        trigger: 'button.o_notification_close',
    }, {
        content: "trigger rpc error 500",
        trigger: 'a[href="/test_internal_error_json"]',
    }, {
        content: "rpc error 500 modal is an ErrorDialog",
        extra_trigger: 'div.o_error_dialog.modal-content',
        trigger: '.modal-footer button.btn.btn-primary',
    },
    // HTTP ERROR
    {
        content: "trigger http user error",
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/test_user_error_http?debug=0';
        },
    }, {
        content: "http user error page has title and message",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div.container pre:contains("This is a user http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_user_error_http?debug=1';
        },
    }, {
        content: "http user error page debug has title and message open",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div#error_main.collapse.show pre:contains("This is a user http test")',
        run: function () {},
    }, {
        content: "http user error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_validation_error_http?debug=0';
        },
    }, {
        content: "http validation error page has title and message",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div.container pre:contains("This is a validation http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_validation_error_http?debug=1';
        },
    }, {
        content: "http validation error page debug has title and message open",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div#error_main.collapse.show pre:contains("This is a validation http test")',
        run: function () {},
    }, {
        content: "http validation error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_access_error_http?debug=0';
        },
    }, {
        content: "http access error page has title and message",
        extra_trigger: 'h1:contains("403: Forbidden")',
        trigger: 'div.container pre:contains("This is an access http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_access_error_http?debug=1';
        },
    }, {
        content: "http access error page debug has title and message open",
        extra_trigger: 'h1:contains("403: Forbidden")',
        trigger: 'div#error_main.collapse.show pre:contains("This is an access http test")',
        run: function () {},
    }, {
        content: "http access error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
                window.location.href = window.location.origin + '/test_missing_error_http?debug=0';
        },
    }, {
        content: "http missing error page has title and message",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div.container pre:contains("This is a missing http test")',
        run: function () {
                window.location.href = window.location.origin + '/test_missing_error_http?debug=1';
        },
    }, {
        content: "http missing error page debug has title and message open",
        extra_trigger: 'h1:contains("Something went wrong.")',
        trigger: 'div#error_main.collapse.show pre:contains("This is a missing http test")',
        run: function () {},
    }, {
        content: "http missing error page debug has traceback closed",
        trigger: 'body:has(div#error_traceback.collapse:not(.show) pre#exception_traceback)',
        run: function () {
            window.location.href = window.location.origin + '/test_access_denied_http?debug=0';
        },
    }, {
        content: "http error 403 page has title but no message",
        extra_trigger: 'h1:contains("403: Forbidden")',
        trigger: 'div#wrap:not(:has(pre:contains("This is an access denied http test"))', //See ir_http.py handle_exception, the exception is replaced so there is no message !
        run: function () {
            window.location.href = window.location.origin + '/test_access_denied_http?debug=1';
        },
    }, {
        content: "http 403 error page debug has title but no message",
        extra_trigger: 'h1:contains("403: Forbidden")',
        trigger: 'div#debug_infos:not(:has(#error_main))',
        run: function () {},
    }, {
        content: "http 403 error page debug has traceback open",
        trigger: 'body:has(div#error_traceback.collapse.show pre#exception_traceback)',
        run: function () {},
    },
]});
