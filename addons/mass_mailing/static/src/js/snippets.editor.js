import { _t } from "@web/core/l10n/translation";
import snippetsEditor from "@web_editor/js/editor/snippets.editor";
import { MassMailingMobilePreviewDialog } from "./mass_mailing_mobile_preview";
import { markup, useEffect, useState } from "@odoo/owl";

export class MassMailingSnippetsMenu extends snippetsEditor.SnippetsMenu {
    static tabs = Object.assign({}, snippetsEditor.SnippetsMenu.tabs, {
        DESIGN: 'design',
    });
    static optionsTabStructure = [
        ['design-options', _t("Design Options")],
    ];

    static template = "mass_mailing.SnippetsMenu";

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        super.setup();
        this.fieldConfig = useState(this.env.fieldConfig);

        let firstRender = true;
        useEffect(
            (selectedTheme) => {
                // Avoid running this on first render as the template is already
                // loaded for the selected theme by the normal flow.
                if (firstRender) {
                    firstRender = false;
                    return;
                }
                this._loadSnippetsTemplates().then(() => {
                    this.reloadSnippetDropzones();
                });
            },
            () => [this.fieldConfig.selectedTheme]
        );
        // When the scrollable changes, it invalidates the current drag and
        // drop config. In the case of the snippetsMenu, it can be altered,
        // But in the case of snippetEditor, destroying them should be good
        // enough.
        useEffect(
            ($scrollable) => {
                this._mutex.exec(async () => {
                    this.options.$scrollable = $scrollable;
                    this._makeSnippetDraggable();
                    await this._destroyEditors();
                });
            },
            () => [this.fieldConfig.$scrollable]
        );
    }
    /**
     * @override
     */
    start() {
        return super.start().then(() => {
            this.$editable = this.options.wysiwyg.getEditable();
        });
    }
    /**
     * @override
     */
    async callPostSnippetDrop($target) {
        $target.find('img[loading=lazy]').removeAttr('loading');
        return super.callPostSnippetDrop(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates(html) {
        this.env.switchImages(this.fieldConfig.selectedTheme, $(html));
        html.querySelectorAll('img').forEach(img => img.setAttribute("loading", "lazy"));
        return super._computeSnippetTemplates(html);
    }
    /**
     * @override
     */
    _onClick(ev) {
        super._onClick(...arguments);
        var srcElement = ev.target || (ev.originalEvent && (ev.originalEvent.target || ev.originalEvent.originalTarget)) || ev.srcElement;
        // When we select something and move our cursor too far from the editable area, we get the
        // entire editable area as the target, which causes the tab to shift from OPTIONS to BLOCK.
        // To prevent unnecessary tab shifting, we provide a selection for this specific case.
        if (srcElement.classList.contains('o_mail_wrapper') || srcElement.querySelector('.o_mail_wrapper')) {
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
        $dropzone.attr('data-editor-message', $hookParent.attr('data-editor-message'));
        $dropzone.attr('data-editor-sub-message', $hookParent.attr('data-editor-sub-message'));
        return $dropzone;
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onDropZoneOver() {
        this.$editable.find('.o_savable').css('background-color', '');
    }
    /**
     * @override
     */
    _onDropZoneOut() {
        const $oEditable = this.$editable.find('.o_savable');
        if ($oEditable.find('.oe_drop_zone.oe_insert:not(.oe_vertical):only-child').length) {
            $oEditable[0].style.setProperty('background-color', 'transparent', 'important');
        }
    }
    /**
     * @override
     */
    _onDropZoneStart() {
        const $oEditable = this.$editable.find('.o_savable');
        if ($oEditable.find('.oe_drop_zone.oe_insert:not(.oe_vertical):only-child').length) {
            $oEditable[0].style.setProperty('background-color', 'transparent', 'important');
        }
    }
    /**
     * @override
     */
    _onDropZoneStop() {
        const $oEditable = this.$editable.find('.o_savable');
        $oEditable.css('background-color', '');
        if (!$oEditable.find('.oe_drop_zone.oe_insert:not(.oe_vertical):only-child').length) {
            $oEditable.attr('contenteditable', true);
        }
        // Refocus again to save updates when calling `_onWysiwygBlur`
        this.$editable.focus();
    }
    /**
     * @override
     */
    _onSnippetRemoved() {
        super._onSnippetRemoved(...arguments);
        const $oEditable = this.$editable.find('.o_savable');
        if (!$oEditable.children().length) {
            $oEditable.empty(); // remove any superfluous whitespace
            $oEditable.attr('contenteditable', false);
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
        $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
        if (this.env.onToggleFullscreen) {
            // `onToggleFullscreen` in the `env` is deprecated, use the wysiwyg function instead
            this.env.onToggleFullscreen();
        }
        this.options.wysiwyg.onToggleFullscreen?.(full);
    }
    /**
     * @private
     */
    _onCodeViewBtnClick(ev) {
        const $codeview = this.options.wysiwyg.$iframe.contents().find("textarea.o_codeview");
        this.options.wysiwyg.odooEditor.observerUnactive();
        $codeview.toggleClass("d-none");
        this.options.wysiwyg.getEditable().toggleClass("d-none");
        this.options.wysiwyg.odooEditor.observerActive();

        if ($codeview.hasClass("d-none")) {
            this.options.wysiwyg.setValue(this.options.getCodeViewValue($codeview[0]));
            this.options.wysiwyg.odooEditor.sanitize();
            this.options.wysiwyg.odooEditor.historyStep(true);
        } else {
            $codeview.val(this.options.wysiwyg.getValue());
        }
        this.activateSnippet(false);
    }
    /**
     * @private
     */
    _onMobilePreviewBtnClick(ev) {
        const btn = ev.target.closest(".btn");
        btn.setAttribute("disabled", true); // Prevent double execution when double-clicking on the button
        const mailingHtml = new DOMParser().parseFromString(this.options.wysiwyg.getValue(), "text/html");
        [...mailingHtml.querySelectorAll("a")].forEach(el => {
            el.style.setProperty("pointer-events", "none");
        });
        this.mobilePreview = this.dialog.add(MassMailingMobilePreviewDialog, {
            title: _t("Mobile Preview"),
            preview: markup(mailingHtml.body.innerHTML),
        }, {
            onClose: () => btn.removeAttribute("disabled"),
        });
    }
}
