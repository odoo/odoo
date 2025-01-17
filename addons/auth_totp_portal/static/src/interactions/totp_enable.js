import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { handleCheckIdentity } from "@portal/js/portal_security";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

import { markup } from "@odoo/owl";

/**
 * Replaces specific <field> elements by normal HTML, strip out the rest entirely
 */
function fromField(f, record) {
    switch (f.getAttribute("name")) {
        case "qrcode":
            const qrcode = document.createElement("img");
            qrcode.setAttribute("class", "img img-fluid");
            qrcode.setAttribute("src", "data:image/png;base64," + record["qrcode"]);
            return qrcode;
        case "url":
            const url = document.createElement("a");
            url.setAttribute("href", record["url"]);
            url.textContent = f.getAttribute("text") || record["url"];
            return url;
        case "code":
            const code = document.createElement("input");
            code.setAttribute("name", "code");
            code.setAttribute("class", "form-control col-10 col-md-6");
            code.setAttribute("placeholder", "6-digit code");
            code.required = true;
            code.maxLength = 6;
            code.minLength = 6;
            return code;
        case "secret":
            // As CopyClipboard wizard is backend only, mimic his behaviour to use it in frontend.
            // Field
            const secretSpan = document.createElement("span");
            secretSpan.setAttribute("name", "secret");
            secretSpan.setAttribute("class", "o_field_copy_url");
            secretSpan.textContent = record["secret"];

            // Copy Button
            const copySpanIcon = document.createElement("span");
            copySpanIcon.setAttribute("class", "fa fa-clipboard");
            const copySpanText = document.createElement("span");
            copySpanText.textContent = _t(" Copy");

            const copyButton = document.createElement("button");
            copyButton.setAttribute("class", "btn btn-sm btn-primary o_clipboard_button o_btn_char_copy py-0 px-2");
            copyButton.onclick = async function (event) {
                event.preventDefault();
                $(copyButton).tooltip({ title: _t("Copied!"), trigger: "manual", placement: "bottom" });
                await browser.navigator.clipboard.writeText($(secretSpan)[0].innerText);
                $(copyButton).tooltip("show");
                setTimeout(() => $(copyButton).tooltip("hide"), 800);
            };

            copyButton.appendChild(copySpanIcon);
            copyButton.appendChild(copySpanText);

            // CopyClipboard Div
            const secretDiv = document.createElement("div");
            secretDiv.setAttribute("class", "o_field_copy d-flex justify-content-center align-items-center");
            secretDiv.appendChild(secretSpan);
            secretDiv.appendChild(copyButton);

            return secretDiv;
        default: // just display the field's data
            return document.createTextNode(record[f.getAttribute("name")] || "");
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
            if (oldNode.tagName === "field") {
                node = fromField(oldNode, record);
                switch (oldNode.getAttribute("name")) {
                    case "qrcode":
                        qrcode = node;
                        break;
                    case "code":
                        code = node;
                        break
                }
                break; // no need to recurse here
            }
            node = document.createElement(oldNode.tagName);
            for (let i = 0; i < oldNode.attributes.length; ++i) {
                const attr = oldNode.attributes[i];
                node.setAttribute(attr.name, attr.value);
            }
            for (let j = 0; j < oldNode.childNodes.length; ++j) {
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

export class TOTPEnable extends Interaction {
    static selector = "#auth_totp_portal_enable";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        const data = await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("res.users", "action_totp_enable_wizard", [user.userId])),
            this.services.orm,
            this.services.dialog,
        ));

        if (!data) {
            // TOTP probably already enabled, just reload page
            location.reload()
            return;
        }

        const model = data.res_model;
        const wizard_id = data.res_id;
        const record = (await this.services.orm.read(model, [wizard_id], []))[0];

        const doc = new DOMParser().parseFromString(
            document.getElementById("totp_wizard_view").textContent,
            "application/xhtml+xml"
        );

        const xmlBody = doc.querySelector("sheet *");
        const [body, ,] = fixupViewBody(xmlBody, record);

        this.services.dialog.add(InputConfirmationDialog, {
            body: markup(body.outerHTML),
            onInput: ({ inputEl }) => { inputEl.setCustomValidity("") },
            confirmLabel: _t("Activate"),
            confirm: async ({ inputEl }) => {
                if (!inputEl.reportValidity()) {
                    inputEl.classList.add("is-invalid");
                    return false;
                }

                try {
                    await this.services.orm.write(model, [record.id], { code: inputEl.value });
                    await handleCheckIdentity(
                        this.waitFor(this.services.orm.call(model, "enable", [record.id])),
                        this.services.orm,
                        this.services.dialog
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
                location.reload();
            },
            cancel: () => { },
        });
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.totp_enable", TOTPEnable);
