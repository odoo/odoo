odoo.define("website.ace", function (require) {
"use strict";

var AceEditor = require('web_editor.ace');

/**
 * Extends the default view editor so that the URL hash is updated with view ID
 */
var WebsiteAceEditor = AceEditor.extend({
    hash: '#advanced-view-editor',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    do_hide: function () {
        this._super.apply(this, arguments);
        window.location.hash = "";
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _displayResource: function () {
        this._super.apply(this, arguments);
        this._updateHash();
    },
    /**
     * @override
     */
    _saveResources: function () {
        return this._super.apply(this, arguments).then((function () {
            var defs = [];
            if (this.currentType === 'xml') {
                // When saving a view, the view ID might change. Thus, the
                // active ID in the URL will be incorrect. After the save
                // reload, that URL ID won't be found and JS will crash.
                // We need to find the new ID (either because the view became
                // specific or because its parent was edited too and the view
                // got copy/unlink).
                var selectedView = _.findWhere(this.views, {id: this._getSelectedResource()});
                var context;
                this.trigger_up('context_get', {
                    callback: function (ctx) {
                        context = ctx;
                    },
                });
                defs.push(this._rpc({
                    model: 'ir.ui.view',
                    method: 'search_read',
                    fields: ['id'],
                    domain: [['key', '=', selectedView.key], ['website_id', '=', context.website_id]],
                }).then((function (view) {
                    if (view[0]) {
                        this._updateHash(view[0].id);
                    }
                }).bind(this)));
            }
            return Promise.all(defs).then((function () {
                window.location.reload();
                return new Promise(function () {});
            }));
        }).bind(this));
    },
    /**
     * @override
     */
    _resetResource: function () {
        return this._super.apply(this, arguments).then((function () {
            window.location.reload();
            return new Promise(function () {});
        }).bind(this));
    },
    /**
     * Adds the current resource ID in the URL.
     *
     * @private
     */
    _updateHash: function (resID) {
        window.location.hash = this.hash + "?res=" + (resID || this._getSelectedResource());
    },
});

return WebsiteAceEditor;
});
