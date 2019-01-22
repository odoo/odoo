odoo.define('website.editor.menu', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var core = require('web.core');
var wContext = require('website.context');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');

var _t = core._t;

var EditorMenu = Widget.extend({
    template: 'website.editorbar',
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    events: {
        'click button[data-action=save]': '_onSaveClick',
        'click button[data-action=cancel]': '_onCancelClick',
    },
    custom_events: {
        request_save: '_onSnippetRequestSave',
    },

    LOCATION_SEARCH: 'enable_editor',

    /**
     * @override
     */
    willStart: function () {
        var self = this;
        this.$el = null; // temporary null to avoid hidden error (@see start)
        return this._super()
            .then(function () {
                var $wrapwrap = $('#wrapwrap');
                $wrapwrap.removeClass('o_editable'); // clean the dom before edition
                self.editable($wrapwrap).addClass('o_editable');
                self.wysiwyg = self._wysiwygInstance();
                return self.wysiwyg.attachTo($wrapwrap);
            });
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$el.css({width: '100%'});
        return this._super().then(function () {
            self.trigger_up('edit_mode');
            self.$el.css({width: ''});
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this.trigger_up('readonly_mode');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Asks the user if they really wants to discard their changes (if any),
     * then simply reloads the page if they want to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded when the user answers yes
     *        (do nothing otherwise but add this to allow class extension)
     * @returns {Deferred}
     */
    cancel: function (reload) {
        var self = this;
        var def = $.Deferred();
        if (!this.wysiwyg.isDirty()) {
            def.resolve();
        } else {
            var confirm = Dialog.confirm(this, _t("If you discard the current edition, all unsaved changes will be lost. You can cancel to return to the edition mode."), {
                confirm_callback: def.resolve.bind(def),
            });
            confirm.on('closed', def, def.reject);
        }
        return def.then(function () {
            self.trigger_up('edition_will_stopped');
            var $wrapwrap = $('#wrapwrap');
            self.editable($wrapwrap).removeClass('o_editable');
            if (reload !== false) {
                self.wysiwyg.destroy();
                return self._reload();
            } else {
                self.wysiwyg.destroy();
                self.trigger_up('readonly_mode');
                self.trigger_up('edition_was_stopped');
                self.destroy();
            }
        });
    },
    /**
     * Asks the snippets to clean themself, then saves the page, then reloads it
     * if asked to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded after the save
     * @returns {Deferred}
     */
    save: function (reload) {
        var self = this;
        this.trigger_up('edition_will_stopped');
        return this.wysiwyg.save().then(function (dirty) {
            var $wrapwrap = $('#wrapwrap');
            self.editable($wrapwrap).removeClass('o_editable');
            if (dirty && reload !== false) {
                // remove top padding because the connected bar is not visible
                $('body').removeClass('o_connected_user');
                return self._reload();
            } else {
                self.wysiwyg.destroy();
                self.trigger_up('edition_was_stopped');
                self.destroy();
            }
        });
    },
    /**
     * Returns the editable areas on the page.
     *
     * @param {DOM} $wrapwrap
     * @returns {jQuery}
     */
    editable: function ($wrapwrap) {
        return $wrapwrap.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                return !$(this).closest('.o_not_editable').length;
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .add('.o_editable');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _wysiwygInstance: function () {
        return new WysiwygMultizone(this, {
            snippets: 'website.snippets',
            recordInfo: {
                context: wContext.get(),
                data_res_model: 'website',
                data_res_id: wContext.get().website_id,
            }
        });
    },
    /**
     * Reloads the page in non-editable mode, with the right scrolling.
     *
     * @private
     * @returns {Deferred} (never resolved, the page is reloading anyway)
     */
    _reload: function () {
        $('body').addClass('o_wait_reload');
        this.wysiwyg.destroy();
        window.location.hash = 'scrollTop=' + window.document.body.scrollTop;
        if (window.location.search.indexOf(this.LOCATION_SEARCH) >= 0) {
            var regExp = new RegExp('[&?]' + this.LOCATION_SEARCH + '(=[^&]*)?', 'g');
            window.location.href = window.location.href.replace(regExp, '?');
        } else {
            window.location.reload(true);
        }
        return $.Deferred();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Discard" button is clicked -> discards the changes.
     *
     * @private
     */
    _onCancelClick: function () {
        this.cancel(false);
    },
    /**
     * Snippet (menu_data) can request to save the document to leave the page
     *
     * @private
     * @param {OdooEvent} ev
     * @param {object} ev.data
     * @param {function} ev.data.onSuccess
     * @param {function} ev.data.onFailure
     */
    _onSnippetRequestSave: function (ev) {
        this.save(false).then(ev.data.onSuccess, ev.data.onFailure);
    },
    /**
     * Called when the "Save" button is clicked -> saves the changes.
     *
     * @private
     */
    _onSaveClick: function () {
        this.save();
    },
});

return EditorMenu;
});
