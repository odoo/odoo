/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import snippetsEditor from "@web_editor/js/editor/snippets.editor";
import { MassMailingMobilePreviewDialog } from "../../js/mass_mailing_mobile_preview";
import { markup, useEffect, useState } from "@odoo/owl";
import { Toolbar } from "@html_editor/main/toolbar/toolbar";

export class MassMailingSnippetsMenu extends snippetsEditor.SnippetsMenu {
    static tabs = Object.assign({}, snippetsEditor.SnippetsMenu.tabs, {
        DESIGN: "design",
    });
    static optionsTabStructure = [["design-options", _t("Design Options")]];
    static props = {
        ...snippetsEditor.SnippetsMenu.props,
        linkToolProps: { type: Object, optional: true },
        toolbarInfos: { type: Object, optional: true },
        selectedTheme: { type: Object },
        toggleCodeView: { type: Function },
    };
    static components = {
        ...snippetsEditor.SnippetsMenu.components,
        Toolbar,
    };

    static template = "mass_mailing.SnippetsMenu";

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        super.setup();
    }
    /**
     * @override
     */
    async callPostSnippetDrop($target) {
        $target.find("img[loading=lazy]").removeAttr("loading");
        return super.callPostSnippetDrop(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates(html) {
        this.env.switchImages(this.props.selectedTheme, $(html));
        html.querySelectorAll("img").forEach((img) => img.setAttribute("loading", "lazy"));
        return super._computeSnippetTemplates(html);
    }
    /**
     * @override
     */
    _onClick(ev) {
        super._onClick(...arguments);
        var srcElement =
            ev.target ||
            (ev.originalEvent && (ev.originalEvent.target || ev.originalEvent.originalTarget)) ||
            ev.srcElement;
        // When we select something and move our cursor too far from the editable area, we get the
        // entire editable area as the target, which causes the tab to shift from OPTIONS to BLOCK.
        // To prevent unnecessary tab shifting, we provide a selection for this specific case.
        if (
            srcElement.classList.contains("o_mail_wrapper") ||
            srcElement.querySelector(".o_mail_wrapper")
        ) {
            const selection = this.options.wysiwyg.odooEditor.document.getSelection();
            if (selection.anchorNode) {
                const parent = selection.anchorNode.parentElement;
                if (parent) {
                    srcElement = parent;
                }
                this._activateSnippet($(srcElement));
            }
        }
    }
    /**
     * @override
     */
    _insertDropzone($hook) {
        const $hookParent = $hook.parent();
        const $dropzone = super._insertDropzone(...arguments);
        $dropzone.attr("data-editor-message", $hookParent.attr("data-editor-message"));
        $dropzone.attr("data-editor-sub-message", $hookParent.attr("data-editor-sub-message"));
        return $dropzone;
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onDropZoneOver() {
        this.getEditableArea().find(".o_editable").css("background-color", "");
    }
    /**
     * @override
     */
    _onDropZoneOut() {
        const $oEditable = this.getEditableArea().find(".o_editable");
        if ($oEditable.find(".oe_drop_zone.oe_insert:not(.oe_vertical):only-child").length) {
            $oEditable[0].style.setProperty("background-color", "transparent", "important");
        }
    }
    /**
     * @override
     */
    _onDropZoneStart() {
        const $oEditable = this.getEditableArea().find(".o_editable");
        if ($oEditable.find(".oe_drop_zone.oe_insert:not(.oe_vertical):only-child").length) {
            $oEditable[0].style.setProperty("background-color", "transparent", "important");
        }
    }
    /**
     * @override
     */
    _onDropZoneStop() {
        const $oEditable = this.getEditableArea().find(".o_editable");
        $oEditable.css("background-color", "");
        if (!$oEditable.find(".oe_drop_zone.oe_insert:not(.oe_vertical):only-child").length) {
            $oEditable.attr("contenteditable", true);
        }
        // Refocus again to save updates when calling `_onWysiwygBlur`
        this.getEditableArea().get(0).ownerDocument.defaultView.focus();
    }
    /**
     * @override
     */
    _onSnippetRemoved() {
        super._onSnippetRemoved(...arguments);
        const $oEditable = this.getEditableArea().find(".o_editable");
        if (!$oEditable.children().length) {
            $oEditable.empty(); // remove any superfluous whitespace
            $oEditable.attr("contenteditable", false);
        }
    }
    /**
     * @private
     */
    _onDesignTabClick() {
        this._enableFakeOptionsTab(MassMailingSnippetsMenu.tabs.DESIGN);
    }
    /**
     * @private
     */
    _onFullscreenBtnClick(ev) {
        $("body").toggleClass("o_field_widgetTextHtml_fullscreen");
        const full = $("body").hasClass("o_field_widgetTextHtml_fullscreen");
        this.options.wysiwyg.$iframe.parents().toggleClass("o_form_fullscreen_ancestor", full);
        $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
        if (this.env.onToggleFullscreen) {
            this.env.onToggleFullscreen();
        }
    }
    /**
     * @private
     */
    _onCodeViewBtnClick(ev) {
        this.props.toggleCodeView();
        this.isDraggable = !this.isDraggable;
    }
    /**
     * @private
     */
    _onMobilePreviewBtnClick(ev) {
        const btn = ev.target.closest(".btn");
        btn.setAttribute("disabled", true); // Prevent double execution when double-clicking on the button
        const mailingHtml = new DOMParser().parseFromString(
            this.options.wysiwyg.getValue(),
            "text/html"
        );
        [...mailingHtml.querySelectorAll("a")].forEach((el) => {
            el.style.setProperty("pointer-events", "none");
        });
        this.mobilePreview = this.dialog.add(
            MassMailingMobilePreviewDialog,
            {
                title: _t("Mobile Preview"),
                preview: markup(mailingHtml.body.innerHTML),
            },
            {
                onClose: () => btn.removeAttribute("disabled"),
            }
        );
    }
}
