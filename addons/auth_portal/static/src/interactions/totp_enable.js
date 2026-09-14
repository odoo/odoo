const log = makeLogger("portal.totp");

/** @odoo-module native */
import { markup } from "@odoo/owl";
import {
    guardedByIdentity,
    handleCheckIdentity,
    IdentityCheckCancelled,
} from "@portal/interactions/portal_security";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { Tooltip } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";

/**
 * Replaces specific <field> elements by normal HTML, strip out the rest entirely
 */
function createFieldNode(f, record) {
    switch (f.getAttribute("name")) {
        case "qrcode": {
            const qrcode = document.createElement("img");
            qrcode.setAttribute("class", "img img-fluid");
            qrcode.setAttribute("src", "data:image/png;base64," + record["qrcode"]);
            return qrcode;
        }
        case "url": {
            const url = document.createElement("a");
            url.setAttribute("href", record["url"]);
            url.textContent = f.getAttribute("text") || record["url"];
            return url;
        }
        case "code": {
            const code = document.createElement("input");
            code.setAttribute("name", "code");
            code.setAttribute("class", "form-control col-10 col-md-6");
            code.setAttribute("placeholder", "6-digit code");
            code.required = true;
            code.maxLength = 6;
            code.minLength = 6;
            return code;
        }
        case "secret": {
            // As CopyClipboard wizard is backend only, mimic his behaviour to use it in frontend.
            // Field
            const secretSpan = document.createElement("span");
            secretSpan.setAttribute("name", "secret");
            secretSpan.setAttribute("class", "o_field_copy_url");
            secretSpan.textContent = record["secret"];

            // Copy Button
            const copySpanIcon = document.createElement("span");
            copySpanIcon.setAttribute("class", "fa-solid fa-paste");
            const copySpanText = document.createElement("span");
            copySpanText.textContent = _t(" Copy");

            const copyButton = document.createElement("button");
            copyButton.setAttribute(
                "class",
                "btn btn-sm btn-primary o_clipboard_button o_btn_char_copy py-0 px-2",
            );
            copyButton.onclick = async function (event) {
                event.preventDefault();
                await browser.navigator.clipboard.writeText(secretSpan.innerText);
                const tooltip = new Tooltip(copyButton, {
                    title: _t("Copied!"),
                    trigger: "manual",
                    placement: "bottom",
                });
                tooltip.show();
                setTimeout(() => {
                    tooltip.hide();
                    tooltip.dispose();
                }, 800);
            };

            copyButton.appendChild(copySpanIcon);
            copyButton.appendChild(copySpanText);

            // CopyClipboard Div
            const secretDiv = document.createElement("div");
            secretDiv.setAttribute(
                "class",
                "o_field_copy d-flex justify-content-center align-items-center",
            );
            secretDiv.appendChild(secretSpan);
            secretDiv.appendChild(copyButton);

            return secretDiv;
        }
        default:
            // just display the field's data
            return document.createTextNode(record[f.getAttribute("name")] || "");
    }
}

/** Rebuild XML view nodes as HTML, replacing ORM fields with portal controls. */
function createViewNode(oldNode, record) {
    switch (oldNode.nodeType) {
        case Node.ELEMENT_NODE: {
            if (oldNode.tagName === "field") {
                return createFieldNode(oldNode, record);
            }
            const node = document.createElement(oldNode.tagName);
            for (const attr of oldNode.attributes) {
                node.setAttribute(attr.name, attr.value);
            }
            for (const child of oldNode.childNodes) {
                const converted = createViewNode(child, record);
                if (converted) {
                    node.appendChild(converted);
                }
            }
            return node;
        }
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            return document.createTextNode(oldNode.data);
        default:
            return null;
    }
}

export class TOTPEnable extends Interaction {
    static selector = "#auth_portal_totp_enable";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        return guardedByIdentity(async () => {
            const data = await this.waitFor(
                handleCheckIdentity(
                    this.waitFor(
                        this.services.orm.call(
                            "res.users",
                            "action_totp_enable_wizard",
                            [user.userId],
                        ),
                    ),
                    this.services.orm,
                    this.services.dialog,
                ),
            );

            if (!data) {
                // TOTP probably already enabled, just reload page
                location.reload();
                return;
            }

            const model = data.res_model;
            const wizard_id = data.res_id;
            const record = (await this.services.orm.read(model, [wizard_id], []))[0];

            const doc = new DOMParser().parseFromString(
                document.getElementById("totp_wizard_view").textContent,
                "application/xhtml+xml",
            );

            const xmlBody = doc.querySelector("sheet *");
            const body = createViewNode(xmlBody, record);

            this.services.dialog.add(InputConfirmationDialog, {
                body: markup(body.outerHTML),
                onInput: ({ inputEl }) => {
                    inputEl.setCustomValidity("");
                },
                confirmLabel: _t("Activate"),
                confirm: async ({ inputEl }) => {
                    try {
                        await this.waitFor(
                            handleCheckIdentity(
                                this.waitFor(
                                    this.services.orm.call(
                                        model,
                                        "enable",
                                        [record.id],
                                        {
                                            context: { code: inputEl.value },
                                        },
                                    ),
                                ),
                                this.services.orm,
                                this.services.dialog,
                            ),
                        );
                    } catch (e) {
                        if (e instanceof IdentityCheckCancelled) {
                            return false;
                        }
                        if (
                            !(e instanceof RPCError) ||
                            e.data?.name !== "odoo.exceptions.UserError"
                        ) {
                            throw e;
                        }
                        log.logic("activation validation failed");
                        const errorMessage =
                            e.data.message ||
                            _t("Operation failed for unknown reason.");
                        inputEl.classList.add("is-invalid");
                        // show custom validity error message
                        inputEl.setCustomValidity(errorMessage);
                        inputEl.reportValidity();
                        return false;
                    }
                    // reloads page, avoid window.location.reload() because it re-posts forms
                    location.reload();
                },
                cancel: () => {},
            });
        });
    }
}

registry.category("public.interactions").add("auth_portal.totp_enable", TOTPEnable);
