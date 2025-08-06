import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import * as passkeyLib from "../lib/simplewebauthn";

let unpatchPasskeyVerify;

registry.category("web_tour.tours").add('passkeys_tour_verify', {
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
            content: "Ensure there is one passkey",
            trigger: 'button:contains("Add Passkey")',
            run: () => {
                let amount = document.querySelectorAll("div[name='auth_passkey_key_ids'] article").length;
                if(amount != 1) {
                    throw Error("Amount of Passkeys must be 1");
                }
            },
        }, {
            content: "Trigger security prompt",
            trigger: 'button:contains("Add Passkey")',
            run: 'click',
        }, {
            content: "Override startAuthentication",
            trigger: 'body',
            run: () => {
                unpatchPasskeyVerify = patch(passkeyLib, {
                    async startAuthentication() {
                        return {
                            // test-yubikey
                            "id": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                            "rawId": "L2p6jvcWuCMTRmkZHKqqvQbz0Dhk3JbJOx1F8ci99nSNjlfx3Z7nkigMdUACLggB",
                            "response": {
                                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAw",
                                "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiREtydzVJZUZpTDB3X3k1b0IwUkFUUHJxRzFlRk9DMlA3eUVpWENzdEJSdVpZYlNCQmtBV2ZoQUlJbmtNcVdqWUlOOHZiS243SjNQTVhfVGh6bkhwcWciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwNjkiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
                                "signature": "MEUCIQD5iaPp48QMS3amx4PS89kv_EBAo3bBkaWnLzWlSgFSXgIgLWKEv9xR_ZwVXZbw2zx459RKbrQuAcd-UqD4gJw1lWY",
                                "userHandle": "Mg",
                            },
                            "type": "public-key",
                            "clientExtensionResults": {},
                            "authenticatorAttachment": "cross-platform",
                        };
                    },
                });
            },
        }, {
            content: "Click Use Passkey",
            trigger: 'button:contains("Use Passkey")',
            run: 'click',
        }, {
            content: "Ready to create Passkey",
            trigger: ".modal div:contains(Create Passkey)",
        }, {
            content: "Return startAuthentication to original state",
            trigger: 'body',
            run: () => {
                unpatchPasskeyVerify();
            },
        }
    ]
})
