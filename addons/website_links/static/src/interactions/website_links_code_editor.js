import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class WebsiteLinksCodeEditor extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".o_website_links_edit_code";
    dynamicContent = {
        ".copy-to-clipboard": {
            "t-on-click.prevent.withTarget": this.onCopyToClipboardClick,
            "t-att-style": () => ({
                "display": this.isEditing ? "none" : undefined,
            }),
            "t-att-data-clipboard-text": () => this.clipboardContent,
        },
        ".o_website_links_edit_code": {
            "t-on-click": this.onEditCodeClick,
            "t-att-style": () => ({
                "display": this.isEditing ? "none" : undefined,
            }),
        },
        ".o_website_links_cancel_edit": {
            "t-on-click.prevent": this.onCancelEditClick,
        },
        ".o_website_links_ok_edit": {
            "t-on-click.prevent": this.onCodeSubmit,
        },
        "#edit-code-form": {
            "t-on-submit.prevent": this.onCodeSubmit,
        },
        ".o_website_links_code_error": {
            "t-out": () => this.errorMessage,
            "t-att-style": () => ({
                "display": this.errorMessage ? "block" : "none",
            }),
        },
        ".o_website_links_edit_tools": {
            "t-att-style": () => ({
                "display": this.isEditing ? undefined : "none",
            }),
        },
    };

    setup() {
        this.codeEl = document.getElementById("o_website_links_code");
        this.clipboardContent = this.el.querySelector(".copy-to-clipboard").dataset.clipboardText || undefined;
        this.errorMessage = "";
        this.isEditing = false;
        this.wasTaken = false;
    }

    onCopyToClipboardClick(ev, currentTargetEl) {
        const tooltip = Tooltip.getOrCreateInstance(currentTargetEl, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        const url = currentTargetEl.dataset.clipboardText;
        setTimeout(async () => await browser.navigator.clipboard.writeText(url));
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    }

    updateCode(newCode) {
        const hostURL = document.getElementById("short-url-host").innerText;
        this.codeEl.querySelector("form").remove();
        this.codeEl.innerText = newCode;
        this.clipboardContent = hostURL + newCode;
        // Update display here because otherwise the switch between the buttons
        // would be visible.
        this.updateContent();
    }

    async onCodeSubmit() {
        const initCode = document.getElementById("init_code").value.trim();
        const newCode = document.getElementById("new_code").value.trim();
        document.getElementById("new_code").value = newCode;

        if (newCode === "") {
            this.errorMessage = _t("The code cannot be left empty");
            return;
        }

        this.isEditing = false;
        this.updateCode(newCode);

        if (initCode === newCode) {
            this.errorMessage = this.wasTaken ? _t("This code is already taken") : "";
        } else {
            try {
                await this.waitFor(rpc("/website_links/add_code", {
                    init_code: initCode,
                    new_code: newCode,
                }));
                this.wasTaken = false;
                this.errorMessage = "";
            } catch {
                this.wasTaken = true;
                this.errorMessage = _t("This code is already taken");
            }
        }
    }

    onEditCodeClick() {
        this.isEditing = true;
        const initCode = this.codeEl.innerText;

        const formEl = document.createElement("form");
        formEl.style.display = "inline";
        formEl.id = "edit-code-form";

        const initInputEl = document.createElement("input");
        initInputEl.type = "hidden";
        initInputEl.id = "init_code";
        initInputEl.value = initCode;

        const newInputEl = document.createElement("input");
        newInputEl.type = "text";
        newInputEl.id = "new_code";
        newInputEl.value = initCode;

        formEl.append(initInputEl);
        formEl.append(newInputEl);

        this.codeEl.innerText = "";
        this.insert(formEl, this.codeEl);
    }

    onCancelEditClick() {
        this.isEditing = false;
        this.errorMessage = this.wasTaken ? _t("This code is already taken") : "";

        const initCode = document.getElementById("init_code").value;
        this.codeEl.querySelector("form").remove();
        this.codeEl.innerText = initCode;

        document.getElementById("code-error")?.remove();
    }
}

registry
    .category("public.interactions")
    .add("website_links.website_links_code_editor", WebsiteLinksCodeEditor);
