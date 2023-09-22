/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('apikeys_tour_setup', {
    test: true,
    url: '/web?debug=1', // Needed as API key part is now only displayed in debug mode
    steps: () => [{
    content: 'Open user account menu',
    trigger: '.o_user_menu .dropdown-toggle',
    run: 'click',
}, {
    content: "Open preferences / profile screen",
    trigger: '[data-menu=settings]',
    run: 'click',
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Account Security")',
    run: 'click',
}, {
    content: "Open API keys wizard",
    trigger: 'button:contains("New API Key")',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password] input',
    run: 'text demo', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check that we're now on the key description dialog",
    trigger: 'p:contains("Enter a description of and purpose for the key.")',
    run: () => {},
}, {
    content: "Enter description",
    trigger: '[name=name] input',
    run: 'text my key',
}, {
    content: "Confirm key creation",
    trigger: 'button:contains("Generate key")'
}, {
    content: "Check that we're on the last step & grab key",
    trigger: 'p:contains("Here is your new API key")',
    run: async () => {
        const key = $('code [name=key] span').text();
        await jsonrpc('/web/dataset/call_kw', {
            model: 'ir.logging', method: 'send_key',
            args: [key],
            kwargs: {},
        });
        $('button:contains("Done")').click();
    }
}, {
    content: "check that our key is present",
    trigger: '[name=api_key_ids] td:contains("my key")',
    run() {},
}]});

// deletes the previously created key
registry.category("web_tour.tours").add('apikeys_tour_teardown', {
    test: true,
    url: '/web?debug=1', // Needed as API key part is now only displayed in debug mode
    steps: () => [{
    content: 'Open preferences',
    trigger: '.o_user_menu .dropdown-toggle',
}, {
    trigger: '[data-menu=settings]',
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Account Security")',
    run: 'click',
}, {
    content: "delete key",
    trigger: '[name=api_key_ids] i.fa-trash',
    run: 'click',
}, {
    content: "Input password for security mode again",
    trigger: '[name=password] input',
    run: 'text demo', // FIXME: better way to do this?
}, {
    content: "And confirm",
    trigger: 'button:contains(Confirm Password)',
}, {
    content: 'Re-open preferences again',
    trigger: '.o_user_menu .dropdown-toggle',
}, {
    trigger: '[data-menu=settings]',
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Account Security")',
    run: 'click',
}, {
    content: "Check that there's no more keys",
    trigger: '.o_notebook',
    run: function() {
        if (this.$anchor.find('[name=api_key_ids]:visible').length) {
            throw new Error("Expected API keys to be hidden (because empty), but it's not");
        };
    }
}]});
