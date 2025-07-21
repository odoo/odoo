import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('passkeys_tour_delete', {
    url: '/odoo',
    steps: () => [
        {
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
            content: "Ensure there is only one passkey",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                let amount = document.querySelectorAll("div[name='auth_passkey_key_ids'] article").length;
                if(amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        }, {
            content: "Open Passkey dropdown",
            trigger: '.o_dropdown_kanban .o-dropdown:not(:visible)',
            run: 'click',
        }, {
            content: "Delete Passkey",
            trigger: 'a[name="action_delete_passkey"]',
            run: 'click',
        }, {
            content: "Identitycheck: use password",
            trigger: 'button[name="action_use_password"]',
            run: 'click',
        }, {
            content: "Check that we have to enter enhanced security mode",
            trigger: ".modal div:contains(entering your password)",
        }, {
            content: "Input password",
            trigger: '.modal [name=password] input',
            run: "edit admin",
        }, {
            content: "Confirm",
            trigger: ".modal button:contains(Confirm Password)",
            run: "click",
        }, {
            content: 'Open user account menu',
            trigger: '.o_user_menu .dropdown-toggle',
            run: 'click',
        }, {
            content: "Open preferences / profile screen",
            trigger: '[data-menu=settings]',
            run: 'click',
        }, {
            // The HR module causes the switch to security tab to trigger on the old DOM, before the new one is loaded
            content: "Make sure the Preferences tab is open",
            trigger: 'label:contains("Email Signature")',
        }, {
            content: "Switch to security tab",
            trigger: 'a[role=tab]:contains("Account Security")',
            run: 'click',
        }, {
            content: "Ensure there are no more passkeys",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                let amount = document.querySelectorAll("div[name='auth_passkey_key_ids'] article").length;
                if(amount != 0) {
                    throw Error("Amount of Passkeys must be 0");
                }
            },
        }
    ]
})
