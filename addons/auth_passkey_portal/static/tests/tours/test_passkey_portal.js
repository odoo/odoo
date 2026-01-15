import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import * as passkeyLib from "@auth_passkey/../lib/simplewebauthn";

let unpatchPasskeyRegistrationPortal;

registry.category("web_tour.tours").add("passkeys_portal_create", {
    url: "/my/security",
    steps: () => [
        {
            content: "Ensure there are no passkeys already",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                const amount = document.querySelectorAll(".o_passkey_portal_entry").length;
                if (amount != 0) {
                    throw Error("Amount of Passkeys must be 0");
                }
            },
        }, {
            content: "Add a Passkey",
            trigger: 'button:contains("Add Passkey")',
            run: "click",
        }, {
            content: "Check that we have to enter enhanced security mode",
            trigger: "form strong:contains(Please enter your password to confirm you own this account)",
        }, {
            content: "Input password",
            trigger: "form input[name=password]",
            run: "edit passkey_portal",
        }, {
            content: "Confirm",
            trigger: ".modal-footer button:contains(Confirm Password)",
            run: "click",
        }, {
            content: "Ready to create Passkey",
            trigger: ".modal-title:contains(Create Passkey)",
        }, {
            content: "Input passkey name",
            trigger: 'input[name="keyname"]',
            run: "edit test_passkey_one",
        }, {
            content: "Override startRegistration",
            trigger: "body",
            run: () => {
                unpatchPasskeyRegistrationPortal = patch(passkeyLib, {
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
            trigger: ".modal-content button:contains(Create)",
            run: "click",
            expectUnloadPage: true,
        }, {
            content: "Return startRegistration to original state",
            trigger: "body",
            run: () => {
                if (unpatchPasskeyRegistrationPortal) {
                    unpatchPasskeyRegistrationPortal();
                }
            },
        }, {
            content: "Ensure there is one passkey",
            trigger: ".o_passkey_name",
            run: () => {
                const amount = document.querySelectorAll(".o_passkey_portal_entry").length;
                if (amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("passkeys_portal_rename", {
    url: "/my/security",
    steps: () => [
        {
            content: "Ensure there is one passkey",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                const amount = document.querySelectorAll(".o_passkey_portal_entry").length;
                if (amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        }, {
            content: "Click rename",
            trigger: '.o_passkey_portal_rename',
            run: "click",
        }, {
            content: "Input passkey name",
            trigger: 'input[name="keyname"]',
            run: "edit edited_key",
        }, {
            content: "Confirm the rename",
            trigger: ".modal-content button:contains(Rename)",
            run: "click",
            expectUnloadPage: true,
        }, {
            content: "Ensure the rename occurred",
            trigger: ".o_passkey_name:contains(edited_key)",
        },
    ],
});

registry.category("web_tour.tours").add("passkeys_portal_delete", {
    url: "/my/security",
    steps: () => [
        {
            content: "Ensure there is one passkey",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                const amount = document.querySelectorAll(".o_passkey_portal_entry").length;
                if (amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        }, {
            content: "Click delete",
            trigger: '.o_passkey_portal_delete',
            run: "click",
        }, {
            content: "Check that we have to enter enhanced security mode",
            trigger: "form strong:contains(Please enter your password to confirm you own this account)",
        }, {
            content: "Input password",
            trigger: "form input[name=password]",
            run: "edit passkey_portal",
        }, {
            content: "Confirm",
            trigger: ".modal-footer button:contains(Confirm Password)",
            run: "click",
            expectUnloadPage: true,
        }, {
            content: "Ensure there are no more passkeys",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                const amount = document.querySelectorAll(".o_passkey_portal_entry").length;
                if (amount != 0) {
                    throw Error("Amount of Passkeys must be 0");
                }
            },
        },
    ],
});
