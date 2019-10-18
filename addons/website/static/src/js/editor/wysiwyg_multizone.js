odoo.define('web_editor.wysiwyg.multizone', function (require) {
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

/**
 * HtmlEditor
 * Intended to edit HTML content. This widget uses the Wysiwyg editor
 * improved by odoo.
 *
 * class editable: o_editable
 * class non editable: o_not_editable
 *
 */
var WysiwygMultizone = Wysiwyg.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.options.toolbarHandler = $('#web_editor-top-edit');
        this.options.saveElement = function ($el, context, withLang) {
            var outerHTML = this._getEscapedElement($el).prop('outerHTML');
            return self._saveElement(outerHTML, self.options.recordInfo, $el[0]);
        };

        // Mega menu initialization: handle dropdown openings by hand
        var $megaMenuToggles = this.$('.o_mega_menu_toggle');
        $megaMenuToggles.removeAttr('data-toggle').dropdown('dispose');
        $megaMenuToggles.on('click.wysiwyg_multizone', ev => {
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
                    this.editor.snippetsMenu.toggleMegaMenuSnippets(isShown);
                });
        });

        // TODO review why this is needed
        _.each(this.$('.oe_structure[data-editor-message!="False"]'), el => {
            var isBlank = !el.innerHTML.trim();
            if (isBlank) {
                el.innerHTML = '';
            }
            el.classList.toggle('oe_empty', isBlank);
        });

        return this._super.apply(this, arguments).then(() => {
            // Showing Mega Menu snippets if one dropdown is already opened
            if (this.$('.o_mega_menu').hasClass('show')) {
                this.editor.snippetsMenu.toggleMegaMenuSnippets(true);
            }
        });
    },
    /**
     * @override
     * @returns {Promise}
     */
    save: function () {
        if (this.isDirty()) {
            return this._restoreMegaMenus()
                .then(() => this.editor.save(false))
                .then(() => ({isDirty: true}));
        } else {
            return {isDirty: false};
        }
    },
    /**
     * @override
     */
    destroy: function () {
        this._restoreMegaMenus();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getEditableArea: function () {
        return $(':o_editable');
    },
    /**
     * @private
     * @param {HTMLElement} editable
     */
    _saveCoverProperties: function (editable) {
        var el = editable.closest('.o_record_cover_container');
        if (!el) {
            return;
        }

        var resModel = el.dataset.resModel;
        var resID = parseInt(el.dataset.resId);
        if (!resModel || !resID) {
            throw new Error('There should be a model and id associated to the cover');
        }

        this.__savedCovers = this.__savedCovers || {};
        this.__savedCovers[resModel] = this.__savedCovers[resModel] || [];

        if (this.__savedCovers[resModel].includes(resID)) {
            return;
        }
        this.__savedCovers[resModel].push(resID);

        var cssBgImage = $(el.querySelector('.o_record_cover_image')).css('background-image');
        var coverProps = {
            'background-image': cssBgImage.replace(/"/g, '').replace(window.location.protocol + "//" + window.location.host, ''),
            'background-color': el.dataset.filterColor,
            'opacity': el.dataset.filterValue,
            'resize_class': el.dataset.coverClass,
            'text_size_class': el.dataset.textSizeClass,
            'text_align_class': el.dataset.textAlignClass,
        };

        return this._rpc({
            model: resModel,
            method: 'write',
            args: [
                resID,
                {'cover_properties': JSON.stringify(coverProps)}
            ],
        });
    },
    /**
     * Saves one (dirty) element of the page.
     *
     * @private
     * @param {jQuery} $el - the element to save
     * @param {Object} context - the context to use for the saving rpc
     * @param {boolean} [withLang=false]
     *        false if the lang must be omitted in the context (saving "master"
     *        page element)
     */
    _saveElement: function (outerHTML, recordInfo, editable) {
        var promises = [];

        var $el = $(editable);

        // Saving a view content
        var viewID = $el.data('oe-id');
        if (viewID) {
            promises.push(this._rpc({
                model: 'ir.ui.view',
                method: 'save',
                args: [
                    viewID,
                    outerHTML,
                    $el.data('oe-xpath') || null,
                ],
                context: recordInfo.context,
            }));
        }

        // Saving mega menu options
        if ($el.data('oe-field') === 'mega_menu_content') {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            // FIXME normally removing the 'show' class should not be necessary here
            // TODO check that editor classes are removed here as well
            var classes = _.without($el.attr('class').split(' '), 'dropdown-menu', 'o_mega_menu', 'show');
            promises.push(this._rpc({
                model: 'website.menu',
                method: 'write',
                args: [
                    [parseInt($el.data('oe-id'))],
                    {
                        'mega_menu_classes': classes.join(' '),
                    },
                ],
            }));
        }

        // Saving cover properties on related model if any
        var prom = this._saveCoverProperties(editable);
        if (prom) {
            promises.push(prom);
        }

        return Promise.all(promises);
    },
    /**
     * Restores mega menu behaviors and closes them (important to do before
     * saving otherwise they would be saved opened).
     *
     * @private
     * @returns {Promise}
     */
    _restoreMegaMenus: function () {
        var $megaMenuToggles = this.$('.o_mega_menu_toggle');
        $megaMenuToggles.off('.wysiwyg_multizone')
            .attr('data-toggle', 'dropdown')
            .dropdown({});
        return toggleDropdown($megaMenuToggles, false);
    },
});

snippetsEditor.Class.include({
    /**
     * @private
     * @param {boolean} show
     */
    toggleMegaMenuSnippets: function (show) {
        setTimeout(() => this._activateSnippet(false));
        this.$('#snippet_mega_menu').toggleClass('d-none', !show);
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

return WysiwygMultizone;
});
