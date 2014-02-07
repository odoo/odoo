(function () {
    'use strict';

    var website = openerp.website;

    website.Tour.LoginEdit = website.Tour.extend({
        id: 'login_edit',
        name: "Try to log as admin and check editor",
        path: '/',
        init: function () {
            var self = this;
            self.steps = [
                {
                    title:     "click login",
                    element:   '#top_menu a[href*="/web/login"]',
                },
                {
                    title:     "insert login",
                    element:   '.oe_login_form input[name="login"]',
                    sampleText: "admin",
                },
                {
                    title:     "insert password",
                    waitFor:   '.oe_login_form input[name="login"][value!=""]',
                    element:   '.oe_login_form input[name="password"]',
                    sampleText: "admin",
                },
                {
                    title:     "select 2 Standard tickets",
                    waitFor:   '.oe_login_form input[name="password"][value!=""]',
                    element:   '.oe_login_form button',
                },
                {
                    title:     "go back to website from backend",
                    element:   'a[data-action-model="ir.actions.act_url"]:contains("Website")',
                },
                {
                    title:     'try to edit',
                    waitNot:   '#wrap .carousel',
                    element:   'button[data-action=edit]:visible',
                },
                {
                    title:     'check edit mode',
                    waitFor:   'button[data-action=save]:visible',
                },
                {
                    title:     'check branding',
                    waitFor:   '#wrap[data-oe-model="ir.ui.view"]',
                },
                {
                    title:     'check rte',
                    waitFor:   '#oe_rte_toolbar',
                },
                {
                    title:     'check insert block button',
                    element:   '[data-action="snippet"]:visible',
                },
                {
                    title:     'add snippets',
                    snippet:   'carousel',
                },
                {
                    title:     'try to save',
                    waitFor:   '.oe_overlay_options .oe_options:visible',
                    element:   'button[data-action=save]:visible',
                },
                {
                    title:     'check saved',
                    waitFor:   '#wrap div.carousel',
                    element:   'button[data-action=edit]:visible',
                },
                {
                    title:      'try to re-edit',
                    waitFor:    'button[data-action=save]:visible',
                    element:    '#wrap .carousel',
                },
                {
                    title:      'remove snippet',
                    element:    '.oe_snippet_remove',
                },
                {
                    title:     'try to re-save',
                    waitNot:   '#wrap .carousel',
                    element:   'button[data-action=save]:visible',
                },
                {
                    title:     "click admin",
                    waitFor:   'button[data-action=edit]:visible',
                    element:   'a:contains("Administrator")',
                },
                {
                    title:     "click logout",
                    element:   '#top_menu a[href*="/logout"]',
                },
                {
                    title:     "check logout",
                    waitFor:   '#top_menu a[href*="/web/login"]',
                },
            ];
            return this._super();
        },
    });
    // for test without editor bar
    website.Tour.add(website.Tour.LoginEdit);

}());
