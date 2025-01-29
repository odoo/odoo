import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteLinksCodeEditor = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    selectorHas: '.o_website_links_edit_code',
    events: {
        'click .copy-to-clipboard': '_onCopyToClipboardClick',
        'click .o_website_links_edit_code': '_onEditCodeClick',
        'click .o_website_links_cancel_edit': '_onCancelEditClick',
        'submit #edit-code-form': '_onEditCodeFormSubmit',
        'click .o_website_links_ok_edit': '_onEditCodeFormSubmit',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCopyToClipboardClick: async function (ev) {
        ev.preventDefault();
        const copyBtn = ev.currentTarget;
        const tooltip = Tooltip.getOrCreateInstance(copyBtn, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        setTimeout(
            async () => await browser.navigator.clipboard.writeText(copyBtn.dataset.clipboardText)
        );
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    },

    /**
     * @private
     * @param {String} newCode
     */
    _showNewCode: function (newCode) {
        // Clear error message and hide error element
        const errorElement = this.el.querySelector(".o_website_links_code_error");
        errorElement.innerHTML = "";
        errorElement.classList.add("d-none");

        // Remove existing form element
        this.el.querySelector("#o_website_links_code form")?.remove();

        // Show new code
        const host = this.el.querySelector("#short-url-host").innerHTML;
        const codeElement = this.el.querySelector("#o_website_links_code");
        if (codeElement) {
            codeElement.innerHTML = newCode;

            // Update button copy to clipboard
            this.el
                .querySelector(".copy-to-clipboard")
                ?.setAttribute("data-clipboard-text", host + newCode);

            // Show action again
            this.el.querySelector(".o_website_links_edit_code").classList.remove("d-none");
            this.el.querySelector(".copy-to-clipboard").classList.remove("d-none");
            this.el.querySelector(".o_website_links_edit_tools").classList.add("d-none");
        }
    },

    /**
     * @private
     * @returns {Promise}
     */
    _submitCode: function () {
        const initCode = this.el.querySelector("#edit-code-form #init_code").value;
        const newCode = this.el.querySelector("#edit-code-form #new_code").value;
        var self = this;

        if (newCode === '') {
            self.el.querySelector(".o_website_links_code_error").innerHTML = _t(
                "The code cannot be left empty"
            );
            self.el.querySelector(".o_website_links_code_error").style.display = "";
            return;
        }

        this._showNewCode(newCode);

        if (initCode === newCode) {
            this._showNewCode(newCode);
        } else {
            return rpc('/website_links/add_code', {
                init_code: initCode,
                new_code: newCode,
            }).then(function (result) {
                self._showNewCode(result[0].code);
            }, function () {
                    document.querySelector(".o_website_links_code_error").style.display = "";
                    document.querySelector(".o_website_links_code_error").innerHTML = _t(
                        "This code is already taken"
                    );
            });
        }

        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onEditCodeClick: function () {
        const linksCodeEl = this.el.querySelector("#o_website_links_code");
        linksCodeEl.innerHTML =
            '<form style="display:inline;" id="edit-code-form"><input type="hidden" id="init_code" value="' +
            linksCodeEl.innerHTML +
            '"/><input type="text" id="new_code" value="' +
            linksCodeEl.innerHTML +
            '"/></form>';
        this.el.querySelector(".o_website_links_edit_code").classList.add("d-none");
        this.el.querySelector(".copy-to-clipboard").classList.add("d-none");
        const editTools = this.el
            .querySelector(".o_website_links_edit_tools")
            .classList.contains("d-none");
        editTools
            ? this.el.querySelector(".o_website_links_edit_tools").classList.remove("d-none")
            : "";
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCancelEditClick: function (ev) {
        ev.preventDefault();
        this.el.querySelector(".o_website_links_edit_code").classList.remove("d-none");
        this.el.querySelector(".copy-to-clipboard").classList.remove("d-none");
        this.el.querySelector(".o_website_links_edit_tools").classList.add("d-none");
        this.el.querySelector(".o_website_links_code_error").classList.add("d-none");

        const oldCode = this.el.querySelector("#edit-code-form #init_code").value;
        this.el.querySelector("#o_website_links_code").innerHTML = oldCode;

        ["#code-error", "#o_website_links_code form"].forEach((selector) => {
            this.el.querySelector(selector)?.remove();
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditCodeFormSubmit: function (ev) {
        ev.preventDefault();
        this._submitCode();
    },
});
