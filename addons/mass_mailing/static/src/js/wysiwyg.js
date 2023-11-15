odoo.define('mass_mailing.wysiwyg', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var MassMailingSnippetsMenu = require('mass_mailing.snippets.editor');
const {closestElement} = require('@web_editor/js/editor/odoo-editor/src/OdooEditor');
const Toolbar = require('web_editor.toolbar');

const MassMailingWysiwyg = Wysiwyg.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    startEdition: async function () {
        const res = await this._super(...arguments);
        // Prevent selection change outside of snippets.
        this.$editable.on('mousedown', e => {
            if ($(e.target).is('.o_editable:empty') || e.target.querySelector('.o_editable')) {
                e.preventDefault();
            }
        });
        this.snippetsMenuToolbar = this.toolbar;
        return res;
    },

    toggleLinkTools(options = {}) {
        this._super({
            ...options,
            // Always open the dialog when the sidebar is folded.
            forceDialog: options.forceDialog || this.snippetsMenu.folded
        });
        if (this.snippetsMenu.folded) {
            // Hide toolbar and avoid it being re-displayed after getDeepRange.
            this.odooEditor.document.getSelection().collapseToEnd();
        }
    },

    /**
     * Sets SnippetsMenu fold state and switches toolbar.
     * Instantiates a new floating Toolbar if needed.
     *
     * @param {Boolean} fold
     */
    setSnippetsMenuFolded: async function (fold = true) {
        if (fold) {
            this.snippetsMenu.setFolded(true);
            if (!this.floatingToolbar) {
                // Instantiate and configure new toolbar.
                this.floatingToolbar = new Toolbar(this, 'web_editor.toolbar');
                this.toolbar = this.floatingToolbar;
                await this.toolbar.appendTo(document.createElement('void'));
                this._configureToolbar({ snippets: false });
                this._updateEditorUI();
                this.setCSSVariables(this.toolbar.el);
                this.odooEditor.setupToolbar(this.toolbar.el);
                if (this.odooEditor.isMobile) {
                    document.body.querySelector('.o_mail_body').prepend(this.toolbar.el);
                } else {
                    document.body.append(this.toolbar.el);
                }
            } else {
                this.toolbar = this.floatingToolbar;
            }
            this.toolbar.el.classList.remove('d-none');
            this.odooEditor.autohideToolbar = true;
            this.odooEditor.toolbarHide();
        } else {
            this.snippetsMenu.setFolded(false);
            this.toolbar = this.snippetsMenuToolbar;
            this.odooEditor.autohideToolbar = false;
            if (this.floatingToolbar) {
                this.floatingToolbar.el.classList.add('d-none');
            }
        }
        this.odooEditor.toolbar = this.toolbar.el;
    },

    /**
     * @override
     */
    openMediaDialog: function() {
        this._super(...arguments);
        // Opening the dialog in the outer document does not trigger the selectionChange
        // (that would normally hide the toolbar) in the iframe.
        if (this.snippetsMenu.folded) {
            this.odooEditor.toolbarHide();
        }
    },

    /**
     * @override
     */
     setValue: function (currentValue) {
        const initialDropZone = this.$editable[0].querySelector('.o_mail_wrapper_td');
        const parsedHtml = new DOMParser().parseFromString(currentValue, "text/html");
        if (initialDropZone && !parsedHtml.querySelector('.o_mail_wrapper_td')) {
            initialDropZone.replaceChildren(...parsedHtml.body.childNodes);
        } else {
            this._super(...arguments);
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _createSnippetsMenuInstance: function (options={}) {
        return new MassMailingSnippetsMenu(this, Object.assign({
            wysiwyg: this,
            selectorEditableArea: '.o_editable',
        }, options));
    },
    /**
     * @override
     */
    _getPowerboxOptions: function () {
        const options = this._super();
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
    },
    /**
     * @override
     */
     _updateEditorUI: function (e) {
        this._super(...arguments);
        // Hide the create-link button if the selection is within a
        // background-image.
        const selection = this.odooEditor.document.getSelection();
        const range = selection.rangeCount && selection.getRangeAt(0);
        const isWithinBackgroundImage = !!range && !!closestElement(range.startContainer, '[style*=background-image]');
        if (isWithinBackgroundImage) {
            this.toolbar.$el.find('#create-link').toggleClass('d-none', true);
        }
    },
});

return MassMailingWysiwyg;

});
