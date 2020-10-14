odoo.define('website.mega_menu', function (require) {
'use strict';
var Wysiwyg = require('web_editor.wysiwyg');
var snippetsEditor = require('web_editor.snippet.editor');

/**
 * Show/hide the dropdowns associated to the given toggles and allows to wait
 * for when it is fully shown/hidden.
 *
 * Note: this also takes care of the fact the 'toggle' method of bootstrap does
 * not properly work in all cases.
 *
 * @param {jQuery} $toggles
 * @param {boolean} [show]
 * @returns {Promise<jQuery>}
 */
function toggleDropdown($toggles, show) {
    return Promise.all(_.map($toggles, toggle => {
        var $toggle = $(toggle);
        var $dropdown = $toggle.parent();
        var shown = $dropdown.hasClass('show');
        if (shown === show) {
            return;
        }
        var toShow = !shown;
        return new Promise(resolve => {
            $dropdown.one(
                toShow ? 'shown.bs.dropdown' : 'hidden.bs.dropdown',
                () => resolve()
            );
            $toggle.dropdown(toShow ? 'show' : 'hide');
        });
    })).then(() => $toggles);
}

Wysiwyg.include({
    _bindAfterStart() {
        this._super.apply(this, arguments);
        // Mega menu initialization: handle dropdown openings by hand
        var $megaMenuToggles = $('.o_mega_menu_toggle');
        $megaMenuToggles.removeAttr('data-toggle').dropdown('dispose');
        $megaMenuToggles.on('click', ev => {
            var $toggle = $(ev.currentTarget);

            // Each time we toggle a dropdown, we will destroy the dropdown
            // behavior afterwards to keep manual control of it
            var dispose = ($els => $els.dropdown('dispose'));

            // First hide all other mega menus
            toggleDropdown($megaMenuToggles.not($toggle), false).then(dispose);

            // Then toggle the clicked one
            toggleDropdown($toggle)
                .then(dispose)
                .then($el => {
                    var isShown = $el.parent().hasClass('show');
                    this.snippetsMenu.toggleMegaMenuSnippets(isShown);
                });
        });

    }
});


snippetsEditor.SnippetsMenu.include({
    /**
     * @private
     * @param {boolean} show
     */
    toggleMegaMenuSnippets: function (show) {
        setTimeout(() => this._enableLastEditor());

        $('#snippet_mega_menu').toggleClass('d-none', !show);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _insertDropzone: function ($hook) {
        var $hookParent = $hook.parent();
        var $dropzone = this._super(...arguments);
        $dropzone.attr('data-editor-message', $hookParent.attr('data-editor-message'));
        $dropzone.attr('data-editor-sub-message', $hookParent.attr('data-editor-sub-message'));
        return $dropzone;
    },
});

});
