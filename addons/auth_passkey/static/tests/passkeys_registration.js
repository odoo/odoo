import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import * as passkeyLib from "../lib/simplewebauthn";

let unpatchPasskeyRegistration;

registry.category("web_tour.tours").add('passkeys_tour_registration', {
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
            trigger: 'button[role=tab]:contains("Account Security")',
            run: 'click',
        }, {
            content: "Ensure there are no passkeys already",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                let amount = document.querySelectorAll("div[name='auth_passkey_key_ids'] article").length;
                if(amount != 0) {
                    throw Error("Amount of Passkeys must be 0");
                }
            },
        }, {
            content: "Add a Passkey",
            trigger: 'button:contains("Add Passkey")',
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
            content: "Ready to create Passkey",
            trigger: ".modal div:contains(Create Passkey)",
        }, {
            content: "Input passkey name",
            trigger: '.modal .o_field_char input',
            run: "edit test_passkey_one",
        }, {
            content: "Override startRegistration",
            trigger: 'body',
            run: () => {
                unpatchPasskeyRegistration = patch(passkeyLib, {
                    async startRegistration() {
                        return {
                            // test-yubikey
                            "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                            "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                            "response": {
                                "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjCSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI",
                                "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVW9hNk01akVQN0kzVG95SzlRQTB2ZjhJY3NlemZlSmswcmdzMXBMVVdyTWdGOXZkMC03RHY1aVYzeFc3cjcwLVlxa3dlUlhoQUNtRFBtaEhLdEFJZVEiLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                                "transports": [
                                    "nfc",
                                    "usb",
                                ],
                                "publicKeyAlgorithm": -7,
                                "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEL2p6jvcWuCMTRmkZHDEsgbnQviQ2WGPYMjKpJz9iJFLarpsvb4ignqP8aRVN188rLHxEXl7zDNf35mTfsDKQzw",
                                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2PFAAAAAgAAAAAAAAAAAAAAAAAAAAAAMC9qeo73FrgjE0ZpGRyqqr0G89A4ZNyWyTsdRfHIvfZ0jY5X8d2e55IoDHVAAi4IAaUBAgMmIAEhWCAvanqO9xa4IxNGaRkcMSyBudC-JDZYY9gyMqknP2IkUiJYINqumy9viKCeo_xpFU3XzyssfEReXvMM1_fmZN-wMpDPoWtjcmVkUHJvdGVjdAI",
                            },
                            "type": "public-key",
                            "clientExtensionResults": {},
                            "authenticatorAttachment": "cross-platform",
                        };
                    },
                });
            },
        }, {
            content: "Click the Create button",
            trigger: ".modal button:contains(Create)",
            run: "click",
        }, {
            content: 'Open user account menu',
            trigger: '.o_user_menu .dropdown-toggle',
            run: 'click',
        }, {
            content: "Return startRegistration to original state",
            trigger: 'body',
            run: () => {
                unpatchPasskeyRegistration();
            },
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
            trigger: 'button[role=tab]:contains("Account Security")',
            run: 'click',
        }, {
            content: "Ensure there is one passkey",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                let amount = document.querySelectorAll("div[name='auth_passkey_key_ids'] article").length;
                if(amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        },
    ]
})
