/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { attachComponent } from "@web/legacy/utils";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { closestElement } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { Toolbar } from "@web_editor/js/editor/toolbar";
import "@web_editor/js/wysiwyg/wysiwyg_iframe";

export class MassMailingWysiwyg extends Wysiwyg {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    async startEdition() {
        const res = await super.startEdition(...arguments);
        // Prevent selection change outside of snippets.
        this.$editable.on('mousedown', e => {
            if ($(e.target).is('.o_editable:empty') || e.target.querySelector('.o_editable')) {
                e.preventDefault();
            }
        });
        this.snippetsMenuToolbarEl = this.toolbarEl;
        return res;
    }

    toggleLinkTools(options = {}) {
        super.toggleLinkTools({
            ...options,
            // Always open the dialog when the sidebar is folded.
            forceDialog: options.forceDialog || this.snippetsMenu.folded
        });
        if (this.snippetsMenu.folded) {
            // Hide toolbar and avoid it being re-displayed after getDeepRange.
            this.odooEditor.document.getSelection().collapseToEnd();
        }
    }

    /**
     * Sets SnippetsMenu fold state and switches toolbar.
     * Instantiates a new floating Toolbar if needed.
     *
     * @param {Boolean} fold
     */
    async setSnippetsMenuFolded(fold = true) {
        if (fold) {
            this.snippetsMenu.setFolded(true);
            if (!this.floatingToolbar) {
                // The wysiwyg can be instanciated inside an iframe. The dialog
                // component is mounted on the global document.
                const toolbarWrapperElement = document.createElement('div');
                toolbarWrapperElement.style.display = 'contents';
                document.body.append(toolbarWrapperElement);
                // Instantiate and configure new toolbar.
                await attachComponent({}, toolbarWrapperElement, Toolbar, this.state.toolbarProps);
                this.toolbarEl = toolbarWrapperElement.firstChild;
                this.floatingToolbarEl = this.toolbarEl;

                this._configureToolbar({ snippets: false });
                this._updateEditorUI();
                this.setCSSVariables(this.toolbarEl);
                this.odooEditor.setupToolbar(this.toolbarEl);
                if (this.odooEditor.isMobile) {
                    document.body.querySelector('.o_mail_body').prepend(this.toolbarEl);
                } else {
                    document.body.append(this.toolbarEl);
                }
            } else {
                this.toolbarEl = this.floatingToolbarEl;
            }
            this.toolbarEl.classList.remove('d-none');
            this.odooEditor.autohideToolbar = true;
            this.odooEditor.toolbarHide();
        } else {
            this.snippetsMenu.setFolded(false);
            this.toolbarEl = this.snippetsMenuToolbarEl;

            this.odooEditor.autohideToolbar = false;
            if (this.floatingToolbarEl) {
                this.floatingToolbarEl.classList.add('d-none');
            }
        }
    }

    /**
     * @override
     */
    openMediaDialog() {
        super.openMediaDialog(...arguments);
        // Opening the dialog in the outer document does not trigger the selectionChange
        // (that would normally hide the toolbar) in the iframe.
        if (this.snippetsMenu.folded) {
            this.odooEditor.toolbarHide();
        }
    }

    /**
     * @override
     */
    setValue(currentValue) {
        const initialDropZone = this.$editable[0].querySelector('.o_mail_wrapper_td');
        const parsedHtml = new DOMParser().parseFromString(currentValue, "text/html");
        if (initialDropZone && !parsedHtml.querySelector('.o_mail_wrapper_td')) {
            initialDropZone.replaceChildren(...parsedHtml.body.childNodes);
        } else {
            super.setValue(...arguments);
        }
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _createSnippetsMenuInstance(options={}) {
        await loadBundle('web_editor.assets_legacy_wysiwyg');
        const { MassMailingSnippetsMenu }  = await odoo.loader.modules.get('@mass_mailing/js/snippets.editor');
        return new MassMailingSnippetsMenu(this, Object.assign({
            wysiwyg: this,
            selectorEditableArea: '.o_editable',
        }, options));
    }
    /**
     * @override
     */
    _getPowerboxOptions() {
        const options = super._getPowerboxOptions();
        const {commands} = options;
        const linkCommands = commands.filter(command => command.name === 'Link' || command.name === 'Button');
        for (const linkCommand of linkCommands) {
            // Remove the command if the selection is within a background-image.
            const superIsDisabled = linkCommand.isDisabled;
            linkCommand.isDisabled = () => {
                if (superIsDisabled && superIsDisabled()) {
                    return true;
                } else {
                    const selection = this.odooEditor.document.getSelection();
                    const range = selection.rangeCount && selection.getRangeAt(0);
                    return !!range && !!closestElement(range.startContainer, '[style*=background-image]');
                }
            }
        }
        return {...options, commands};
    }
    /**
     * @override
     */
     _updateEditorUI(e) {
        super._updateEditorUI(...arguments);
        // Hide the create-link button if the selection is within a
        // background-image.
        const selection = this.odooEditor.document.getSelection();
        if (!selection) return;
        const range = selection.rangeCount && selection.getRangeAt(0);
        const isWithinBackgroundImage = !!range && !!closestElement(range.startContainer, '[style*=background-image]');
        if (isWithinBackgroundImage) {
            this.toolbarEl.querySelector('#create-link').classList.toggle('d-none', true);
        }
    }
}

