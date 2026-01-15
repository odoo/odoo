import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class WebsiteLinksCodeEditor extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".o_website_links_edit_code";
    dynamicContent = {
        ".copy-to-clipboard": {
            "t-on-click.prevent": this.onCopyToClipboardClick,
            "t-att-class": () => ({ "d-none": this.editing }),
        },
        ".o_website_links_edit_code": {
            "t-on-click": this.onEditCodeClick,
            "t-att-class": () => ({ "d-none": this.editing }),
        },
        ".o_website_links_edit_tools": { "t-att-class": () => ({ "d-none": !this.editing }) },
        ".o_website_links_code_error": { "t-att-class": () => ({ "d-none": !this.error }) },
        ".o_website_links_cancel_edit": { "t-on-click.prevent": this.onCancelEditClick },
        "#edit-code-form": { "t-on-submit.prevent": this.onEditCodeFormSubmit },
        ".o_website_links_ok_edit": { "t-on-click.prevent": this.onEditCodeFormSubmit },
    };

    setup() {
        this.codeEl = this.el.querySelector("#o_website_links_code");
        this.copyButtonEl = this.el.querySelector(".copy-to-clipboard");
        this.codeErrorEl = this.el.querySelector(".o_website_links_code_error");
        this.editing = false;
        this.error = false;
    }

    onCopyToClipboardClick(event) {
        const copyButtonEl = event.currentTarget;
        const tooltip = window.Tooltip.getOrCreateInstance(copyButtonEl, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        browser.navigator.clipboard.writeText(copyButtonEl.dataset.clipboardText);
        tooltip.show();
        this.waitForTimeout(() => tooltip.hide(), 1200);
    }

    onEditCodeClick() {
        const oldCode = this.codeEl.textContent;
        const formEl = document.createElement("form");
        formEl.style.display = "inline";
        formEl.id = "edit-code-form";
        const oldCodeInputEl = document.createElement("input");
        oldCodeInputEl.type = "hidden";
        oldCodeInputEl.id = "init_code";
        oldCodeInputEl.value = oldCode;
        const newCodeInputEl = document.createElement("input");
        newCodeInputEl.type = "text";
        newCodeInputEl.id = "new_code";
        newCodeInputEl.value = oldCode;
        formEl.replaceChildren(oldCodeInputEl, newCodeInputEl);
        this.codeEl.replaceChildren();
        this.insert(formEl, this.codeEl);
        this.editing = true;
    }

    onCancelEditClick() {
        this.codeEl.replaceChildren(this.codeEl.querySelector("#edit-code-form #init_code").value);
        this.editing = false;
        this.error = false;
    }

    showNewCode(newCode) {
        this.codeEl.querySelector("form")?.remove();
        this.codeEl.replaceChildren(newCode);
        const host = this.el.querySelector("#short-url-host").textContent;
        this.copyButtonEl.dataset.clipboardText = `${host}${newCode}`;
        this.editing = false;
        this.error = false;
    }

    async onEditCodeFormSubmit() {
        const newCode = this.codeEl.querySelector("#edit-code-form #new_code").value;
        if (newCode === "") {
            this.codeErrorEl.textContent = _t("The code cannot be left empty");
            this.error = true;
            return;
        }

        const oldCode = this.codeEl.querySelector("#edit-code-form #init_code").value;
        if (oldCode === newCode) {
            this.showNewCode(newCode);
        } else {
            try {
                const result = await this.waitFor(
                    rpc("/website_links/add_code", {
                        init_code: oldCode,
                        new_code: newCode,
                    })
                );
                this.showNewCode(result[0].code);
            } catch {
                this.codeErrorEl.textContent = _t("This code is already taken");
                this.error = true;
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_links.WebsiteLinksCodeEditor", WebsiteLinksCodeEditor);
