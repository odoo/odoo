import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class CodeEditor extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".o_website_links_edit_code";
    dynamicContent = {
        ".o_website_links_cancel_edit": {
            "t-on-click.prevent": this.onEditCancelClick,
        },
        ".o_website_links_ok_edit": {
            "t-on-click.prevent": this.onEditValidate,
        },
        "#edit-code-form": {
            "t-on-submit.prevent": this.onEditValidate,
        },
        ".copy-to-clipboard": {
            "t-on-click.prevent": this.onCopyToClipboardClick,
            "t-att-class": () => ({ "d-none": this.isEditing }),
            "t-att-data-clipboard-text": () => this.hostContent + this.codeContent,
        },
        ".o_website_links_edit_code": {
            "t-on-click": this.onEditClick,
            "t-att-class": () => ({ "d-none": this.isEditing }),
        },
        ".o_website_links_code_error": {
            "t-att-class": () => ({ "d-none": !this.errorMessage }),
            "t-out": () => this.errorMessage,
        },
        "#o_website_links_code": {
            "t-out": () => this.codeContent,
        },
        ".o_website_links_edit_tools": {
            "t-att-class": () => ({ "d-none": !this.isEditing }),
        },
    };

    setup() {
        this.codeContent = "";
        this.hostContent = "";
        this.errorMessage = "";
        this.isEditing = false;
    }

    /**
     * @param {String} newCode
     */
    updateCode(newCode) {
        this.isEditing = false;
        this.codeContent = newCode;
        this.hostContent = document.querySelector("#short-url-host").innerHTML;
        this.errorMessage = "";

        document.querySelector("#o_website_links_code form").remove();
    }

    async onCopyToClipboardClick() {
        const copyBtn = this.el.querySelector(".copy-to-clipboard");
        const tooltip = Tooltip.getOrCreateInstance(copyBtn, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        this.waitForTimeout(async () => await this.waitFor(browser.navigator.clipboard.writeText(copyBtn.dataset.clipboardText)));
        tooltip.show();
        this.waitForTimeout(() => tooltip.hide(), 1200);
    }

    onEditClick() {
        this.isEditing = true;

        const formEl = document.createElement("form");
        formEl.style.display = "inline";
        formEl.setAttribute("id", "edit-code-form");

        const inputOldCodeEl = document.createElement("input");
        inputOldCodeEl.setAttribute("id", "init_code");
        inputOldCodeEl.setAttribute("type", "hidden");
        inputOldCodeEl.setAttribute("value", this.codeContent);

        const inputNewCodeEl = document.createElement("input");
        inputNewCodeEl.setAttribute("id", "new_code");
        inputNewCodeEl.setAttribute("type", "text");
        inputNewCodeEl.setAttribute("value", this.codeContent);

        formEl.append(inputOldCodeEl, inputNewCodeEl);
        this.codeContent = formEl.toString();
    }

    onEditCancelClick() {
        this.isEditing = false;
        this.updateCode(document.querySelector("#o_website_links_code form #init_code").value);
    }

    async onEditValidate() {
        const formEl = document.querySelector("#o_website_links_code form");
        const initCode = formEl.querySelectr("#init_code").value;
        const newCode = formEl.querySelectr("#new_code").value;

        if (newCode === "") {
            this.errorMessage = _t("The code cannot be left empty");
            return;
        }

        if (initCode === newCode) {
            this.updateCode(newCode);
        } else {
            const result = await this.waitFor(rpc("/website_links/add_code", {
                init_code: initCode,
                new_code: newCode,
            }));
            if (result) {
                this.updateCode(result[0].code);
            } else {
                this.errorMessage = _t("This code is already taken");
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_links.code_editor", CodeEditor);
