odoo.define('website.tour_reset_password', function (require) {
'use strict';

var localStorage = require('web.local_storage');
var rpc = require('web.rpc');
var tour = require('web_tour.tour');
require('web.dom_ready');

var currentDomain = window.location.protocol + '//' + window.location.hostname;
var emailsUrl = '/web#action=mail.action_view_mail_mail&view_type=list';
var usersUrl = '/web#action=base.action_res_users&view_type=list';
var resetLinkKey = 'website.tour_reset_password.resetLink';

tour.register('website_reset_password', {
    test: true,
    url: '/web',
},
[
    {
        content: "Change the domain of the websites and go to users page",
        trigger: '.oe_topbar_name:contains("Admin")',
        run: function () {
            // We could do it with the UI but this is not the goal of this test,
            // so we just make an RPC to be faster.

            // We change the domain of the website to test that the email that
            // will be sent uses the correct domain for its links.
            var def1 = rpc.query({
                'model': 'website',
                'method': 'write',
                'args': [[1], {
                    'domain': "my-test-domain.com",
                }],
            });
            // We need to change the domain of all the websites otherwise the
            // website selector will return the website 2 since the domain we
            // set on website 1 doesn't actually match our test server.
            var def2 = rpc.query({
                'model': 'website',
                'method': 'write',
                'args': [[2], {
                    'domain': "https://domain-not-used.fr",
                }],
            });
            // Set a website on "Admin" partner to test the URL of the website.
            var def3 = rpc.query({
                model: 'res.partner',
                method: 'name_search',
                kwargs: {'name': 'Mitchell Admin', 'args': [['company_id', '=', 1]]},
            }).then(function (res) {
                return rpc.query({
                    'model': 'res.partner',
                    'method': 'write',
                    'args': [[res[0][0]], {
                        'website_id': 1,
                    }],
                });
            });

            return Promise.all([def1, def2, def3]).then(function () {
                window.location.href = usersUrl;
            });
        },
    },
    {
        content: "click on Admin",
        trigger: '.o_data_cell:contains("Admin")',
    },
    {
        content: "click on reset password",
        trigger: '.btn[name="action_reset_password"]',
    },
    {
        content: "wait mail to be sent, and go see it",
        trigger: 'a[name="signup_url"][href^="http://my-test-domain.com"]',
        run: function () {
            window.location.href = emailsUrl;
        },
    },
    {
        content: "click on the first email",
        trigger: '.o_data_cell:contains("Password reset"):eq(0)',
    },
    {
        content: "check email has the button",
        trigger: 'div.oe_form_field_html[name="body_html"] a:contains("Change password")',
        run: function () {},
    },
    {
        content: "check the URL is correct too",
        trigger: 'div.oe_form_field_html[name="body_html"] a:contains("Change password")[href^="http://my-test-domain.com"]',
        run: function () {
            // reset the domain of the websites, go to users page
            return rpc.query({
                'model': 'website',
                'method': 'write',
                'args': [[1, 2], {
                    'domain': "",
                }],
            }).then(function () {
                window.location.href = usersUrl;
            });
        },
    },
    {
        content: "click on Admin",
        trigger: '.o_data_cell:contains("Admin")',
    },
    {
        content: "click on reset password",
        trigger: '.btn[name="action_reset_password"]',
    },
    {
        content: "wait mail to be sent, and go see it",
        trigger: 'a[name="signup_url"][href^="' + currentDomain + '"]',
        run: function () {
            window.location.href = emailsUrl;
        },
    },
    {
        content: "click on the first email",
        trigger: '.o_data_cell:contains("Password reset"):eq(0)',
    },
    {
        content: "check the link has the current host, save the link, logout",
        trigger: 'div.oe_form_field_html[name="body_html"] a:contains("Change password")[href^="' + currentDomain + '"]',
        run: function () {
            var link = $('div.oe_form_field_html[name="body_html"] a:contains("Change password")').attr('href');
            localStorage.setItem(resetLinkKey, link);
            window.location.href = "/web/session/logout?redirect=/";
        },
    },
    {
        content: "go to the reset link",
        trigger: 'a[href="/web/login"]',
        run: function () {
            window.location.href = localStorage.getItem(resetLinkKey);
        },
    },
    {
        content: "fill new password and submit",
        trigger: '.oe_reset_password_form',
        run: function () {
            var $form = $('.oe_reset_password_form');
            $form.find('input[name="password"]').val('adminadmin');
            // password must be at least 8 if the module `auth_password_policy`
            // is installed which is the case on runbot
            $form.find('input[name="confirm_password"]').val('adminadmin');
            $form.find('button[type="submit"]').click();
        },
    },
    {
        content: "check logged in, and reset admin website",
        trigger: '.oe_topbar_name:contains("Admin")',
        run: function () {
            return rpc.query({
                model: 'res.partner',
                method: 'name_search',
                kwargs: {'name': 'Admin'},
            }).then(function (res) {
                return rpc.query({
                    'model': 'res.partner',
                    'method': 'write',
                    'args': [[res[0][0]], {
                        'website_id': false,
                    }],
                });
            });
        },
    },
]);
});
