/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { closestElement } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import "@web_editor/js/wysiwyg/wysiwyg_iframe";

export class MassMailingWysiwyg extends Wysiwyg {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    async startEdition() {
        // The initial toolbar of the Wysiwyg component will be used as the
        // mainToolbar (sticky on mobile and floating on desktop).
        this.mainToolbarEl = this.toolbarRef.el.firstChild;
        this.mainToolbarEl.classList.add('d-none');

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
     * Configures the main toolbar if needed.
     *
     * @param {Boolean} fold
     */
    setSnippetsMenuFolded(fold = true) {
        this.snippetsMenu.setFolded(fold);
        this.toolbarEl = fold ? this.mainToolbarEl : this.snippetsMenuToolbarEl;
        // At startup, the `SnippetMenu` set its toolbar before the
        // `mainToolbarEl` had the chance to be configured. So we configure it
        // now if we need it.
        if (fold && !this._isMainToolbarReady) {
            // Setup toolbar.
            this._configureToolbar({ snippets: false });
            this._updateEditorUI();
            this.setCSSVariables(this.toolbarEl);
            // Position the toolbar element.
            if (this.odooEditor.isMobile) {
                document.body.querySelector('.o_mail_body').prepend(this.toolbarEl);
            } else {
                document.body.append(this.toolbarEl);
            }
            this._isMainToolbarReady = true;
        }
        this.odooEditor.toolbar = this.toolbarEl;
        this.odooEditor.autohideToolbar = !!fold;
        this.odooEditor.toolbarHide();
        this.mainToolbarEl.classList.toggle('d-none', !fold);
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

