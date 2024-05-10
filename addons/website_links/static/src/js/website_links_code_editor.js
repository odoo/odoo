/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteLinksCodeEditor = publicWidget.Widget.extend({
    selector: "#wrapwrap:has(.o_website_links_edit_code)",
    events: {
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
     * @param {String} newCode
     */
    _showNewCode: function (newCode) {
        // Clear error message and hide error element
        var errorElement = document.querySelector(".o_website_links_code_error");
        errorElement.innerHTML = "";
        errorElement.style.display = "none";
    
        // Remove existing form element
        var formElement = document.querySelector("#o_website_links_code form");
        if (formElement) {
            formElement.remove();
        }
    
        // Show new code
        const host = document.querySelector("#short-url-host").innerHTML;
        var codeElement = document.querySelector("#o_website_links_code");
        if (codeElement) {
            codeElement.innerHTML = newCode;
    
            // Update button copy to clipboard
            var copyButton = document.querySelector(".copy-to-clipboard");
            if (copyButton) {
                copyButton.setAttribute("data-clipboard-text", host + newCode);
            }
    
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
        const initCode = document.querySelector("#edit-code-form #init_code").value;
        const newCode = document.querySelector("#edit-code-form #new_code").value;
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
        const initCode = document.querySelector("#o_website_links_code").innerHTML;
        document.querySelector("#o_website_links_code").innerHTML =
            '<form style="display:inline;" id="edit-code-form"><input type="hidden" id="init_code" value="' +
            initCode +
            '"/><input type="text" id="new_code" value="' +
            initCode +
            '"/></form>';
        document.querySelector(".o_website_links_edit_code").classList.add("d-none");
        document.querySelector(".copy-to-clipboard")?.classList.add("d-none");
        document.querySelector(".o_website_links_edit_tools").classList.remove("d-none");
    },

    _onCancelEditClick: function (ev) {
        ev.preventDefault();
        document.querySelector(".o_website_links_edit_code").classList.remove("d-none");
        document.querySelector(".copy-to-clipboard")?.classList.remove("d-none");
        document.querySelector(".o_website_links_edit_tools").classList.add("d-none");
        document.querySelector(".o_website_links_code_error")?.classList.add("d-none");
    
        const oldCode = document.querySelector("#edit-code-form #init_code").value;
        document.querySelector("#o_website_links_code").innerHTML = oldCode;
    
        ["#code-error", "#o_website_links_code form"].forEach(selector => {
            const element = document.querySelector(selector);
            if (element) element.remove();
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
