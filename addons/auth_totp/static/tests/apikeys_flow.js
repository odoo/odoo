import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const openUserPreferenceSecurity = () => [{
    content: 'Open user account menu',
    trigger: '.o_user_menu .dropdown-toggle',
    run: 'click',
}, {
    content: "Open preferences / profile screen",
    trigger: '[data-menu=preferences]',
    run: 'click',
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Security")',
    run: 'click',
}]

registry.category("web_tour.tours").add('apikeys_tour_setup', {
    url: '/odoo?debug=1', // Needed as API key part is now only displayed in debug mode
    steps: () => [
    ...openUserPreferenceSecurity(), {
    content: "Open API keys wizard",
    trigger: 'button:contains("Add API Key")',
    run: "click",
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: ".modal div:contains(Enter your current password)",
}, {
    content: "Input password",
    trigger: '.modal [name=password] input',
    run: "edit test_user",
}, {
    content: "Confirm",
    trigger: ".modal button:contains(Confirm Password)",
    run: "click",
}, {
    content: "Check that we're now on the key description dialog",
    trigger: '.modal p:contains("Enter a description of and purpose for the key.")',
}, {
    content: "Enter description",
    trigger: '.modal [name=name] input',
    run: "edit my key",
}, {
    content: "Confirm key creation",
    trigger: '.modal button:contains("Generate key")',
    run: "click",
}, {
    content: "Check that we're on the last step & grab key",
    trigger: '.modal p:contains("Here is your new API key")',
    run: async () => {
        const key = document.querySelector("code [name=key] span").textContent;
        await rpc('/web/dataset/call_kw', {
            model: 'ir.logging', method: 'send_key',
            args: [key],
            kwargs: {},
        });
    }
},
{
    trigger: "button:contains(Done)",
    run: "click",
},
...openUserPreferenceSecurity(),
{
    content: "check that our key is present",
    trigger: '[name=api_key_ids] .o_kanban_record:contains("my key")',
}]});

// deletes the previously created key
registry.category("web_tour.tours").add('apikeys_tour_teardown', {
    url: '/odoo?debug=1', // Needed as API key part is now only displayed in debug mode
    steps: () => [{
    content: 'Open preferences',
    trigger: '.o_user_menu .dropdown-toggle',
    run: "click",
}, {
    trigger: '[data-menu=preferences]',
    run: "click",
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Security")',
    run: 'click',
}, {
    content: "Open kanban dropdown menu of the key",
    trigger: '[name=api_key_ids] .o_kanban_record:contains("my key") .oe_kanban_action[name="remove"]',
    run: 'click',
}, {
    content: "Input password for security mode again",
    trigger: ".modal [name=password] input",
    run: "edit test_user",
}, {
    content: "And confirm",
    trigger: ".modal button:contains(Confirm Password)",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    content: 'Re-open preferences again',
    trigger: '.o_user_menu .dropdown-toggle',
    run: "click",
}, {
    trigger: '[data-menu=preferences]',
    run: "click",
}, {
    content: "Switch to security tab",
    trigger: 'a[role=tab]:contains("Security")',
    run: 'click',
}, {
    content: "Check that there's no more keys",
    trigger: "body:not(:has(.o_notebook [name=api_key_ids]))",
}]});
