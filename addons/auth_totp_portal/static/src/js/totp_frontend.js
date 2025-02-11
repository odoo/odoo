/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { handleCheckIdentity } from "@portal/js/portal_security";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";

/**
 * Replaces specific <field> elements by normal HTML, strip out the rest entirely
 */
function fromField(f, record) {
    switch (f.getAttribute('name')) {
    case 'qrcode':
        const qrcode = document.createElement('img');
        qrcode.setAttribute('class', 'img img-fluid');
        qrcode.setAttribute('src', 'data:image/png;base64,' + record['qrcode']);
        return qrcode;
    case 'url':
        const url = document.createElement('a');
        url.setAttribute('href', record['url']);
        url.textContent = f.getAttribute('text') || record['url'];
        return url;
    case 'code':
        const code = document.createElement('input');
        code.setAttribute('name', 'code');
        code.setAttribute('class', 'form-control col-10 col-md-6');
        code.setAttribute('placeholder', '6-digit code');
        code.required = true;
        code.maxLength = 6;
        code.minLength = 6;
        return code;
    case 'secret':
        // As CopyClipboard wizard is backend only, mimic his behaviour to use it in frontend.
        // Field
        const secretSpan = document.createElement('span');
        secretSpan.setAttribute('name', 'secret');
        secretSpan.setAttribute('class', 'o_field_copy_url');
        secretSpan.textContent = record['secret'];

        // Copy Button
        const copySpanIcon = document.createElement('span');
        copySpanIcon.setAttribute('class', 'fa fa-clipboard');
        const copySpanText = document.createElement('span');
        copySpanText.textContent = _t(' Copy');

        const copyButton = document.createElement('button');
        copyButton.setAttribute('class', 'btn btn-sm btn-primary o_clipboard_button o_btn_char_copy py-0 px-2');
        copyButton.onclick = async function(event) {
            event.preventDefault();
            $(copyButton).tooltip({title: _t("Copied!"), trigger: "manual", placement: "bottom"});
            await browser.navigator.clipboard.writeText($(secretSpan)[0].innerText);
            $(copyButton).tooltip('show');
            setTimeout(() => $(copyButton).tooltip("hide"), 800);
        };

        copyButton.appendChild(copySpanIcon);
        copyButton.appendChild(copySpanText);

        // CopyClipboard Div
        const secretDiv = document.createElement('div');
        secretDiv.setAttribute('class', 'o_field_copy d-flex justify-content-center align-items-center');
        secretDiv.appendChild(secretSpan);
        secretDiv.appendChild(copyButton);

        return secretDiv;
    default: // just display the field's data
        return document.createTextNode(record[f.getAttribute('name')] || '');
    }
}

/**
 * Apparently chrome literally absolutely can't handle parsing XML and using
 * those nodes in an HTML document (even when parsing as application/xhtml+xml),
 * this results in broken rendering and a number of things not working (e.g.
 * classes) without any specific warning in the console or anything, things are
 * just broken with no indication of why.
 *
 * So... rebuild the entire f'ing body using document.createElement to ensure
 * we have HTML elements.
 *
 * This is a recursive implementation so it's not super efficient but the views
 * to fixup *should* be relatively simple.
 */
function fixupViewBody(oldNode, record) {
    let qrcode = null, code = null, node = null;

    switch (oldNode.nodeType) {
        case 1: // element
            if (oldNode.tagName === 'field') {
                node = fromField(oldNode, record);
                switch (oldNode.getAttribute('name')) {
                case 'qrcode':
                    qrcode = node;
                    break;
                case 'code':
                    code = node;
                    break
                }
                break; // no need to recurse here
            }
            node = document.createElement(oldNode.tagName);
            for(let i=0; i<oldNode.attributes.length; ++i) {
                const attr = oldNode.attributes[i];
                node.setAttribute(attr.name, attr.value);
            }
            for(let j=0; j<oldNode.childNodes.length; ++j) {
                const [ch, qr, co] = fixupViewBody(oldNode.childNodes[j], record);
                if (ch) { node.appendChild(ch); }
                if (qr) { qrcode = qr; }
                if (co) { code = co; }
            }
            break;
        case 3: case 4: // text, cdata
            node = document.createTextNode(oldNode.data);
            break;
        default:
            // don't care about PI & al
    }

    return [node, qrcode, code]
}

publicWidget.registry.TOTPButton = publicWidget.Widget.extend({
    selector: '#auth_totp_portal_enable',
    events: {
        click: '_onClick',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e) {
        e.preventDefault();

        const w = await handleCheckIdentity(
            this.orm.call("res.users", "action_totp_enable_wizard", [session.user_id]),
            this.orm,
            this.dialog
        );

        if (!w) {
            // TOTP probably already enabled, just reload page
            window.location = window.location;
            return;
        }

        const {res_model: model, res_id: wizard_id} = w;

        const record = await this.orm.read(model, [wizard_id], []).then(ar => ar[0]);

        const doc = new DOMParser().parseFromString(
            document.getElementById('totp_wizard_view').textContent,
            'application/xhtml+xml'
        );

        const xmlBody = doc.querySelector('sheet *');
        const [body, ,] = fixupViewBody(xmlBody, record);

        this.call("dialog", "add", InputConfirmationDialog, {
            body: markup(body.outerHTML),
            onInput: ({ inputEl }) => {
                inputEl.setCustomValidity("");
            },
            confirmLabel: _t("Activate"),
            confirm: async ({ inputEl }) => {
                if (!inputEl.reportValidity()) {
                    inputEl.classList.add("is-invalid");
                    return false;
                }

                try {
                    await this.orm.write(model, [record.id], { code: inputEl.value });
                    await handleCheckIdentity(
                        this.orm.call(model, "enable", [record.id]),
                        this.orm,
                        this.dialog
                    );
                } catch (e) {
                    const errorMessage = (
                        !e.message ? e.toString()
                      : !e.message.data ? e.message.message
                      : e.message.data.message || _t("Operation failed for unknown reason.")
                    );
                    inputEl.classList.add("is-invalid");
                    // show custom validity error message
                    inputEl.setCustomValidity(errorMessage);
                    inputEl.reportValidity();
                    return false;
                }
                // reloads page, avoid window.location.reload() because it re-posts forms
                window.location = window.location;
            },
            cancel: () => {},
        });
    },
});
publicWidget.registry.DisableTOTPButton = publicWidget.Widget.extend({
    selector: '#auth_totp_portal_disable',
    events: {
        click: '_onClick'
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e) {
        e.preventDefault();
        await handleCheckIdentity(
            this.orm.call("res.users", "action_totp_disable", [session.user_id]),
            this.orm,
            this.dialog
        )
        window.location = window.location;
    }
});
publicWidget.registry.RevokeTrustedDeviceButton = publicWidget.Widget.extend({
    selector: '#totp_wizard_view + * .fa.fa-trash.text-danger',
    events: {
        click: '_onClick'
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e){
        e.preventDefault();
        await handleCheckIdentity(
            this.orm.call("auth_totp.device", "remove", [parseInt(this.el.id)]),
            this.orm,
            this.dialog
        );
        window.location = window.location;
    }
});
publicWidget.registry.RevokeAllTrustedDevicesButton = publicWidget.Widget.extend({
    selector: '#auth_totp_portal_revoke_all_devices',
    events: {
        click: '_onClick'
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e){
        e.preventDefault();
        await handleCheckIdentity(
            this.orm.call("res.users", "revoke_all_devices", [session.user_id]),
            this.orm,
            this.dialog
        );
        window.location = window.location;
    }
});
