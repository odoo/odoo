odoo.define("website.ace", function (require) {
"use strict";

var AceEditor = require('web_editor.ace');
var weContext = require('web_editor.context');

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
                var selectedView = _.findWhere(this.views, {id: this._getSelectedResource()});
                if (!selectedView.website_id[0]) {
                    // When saving a generic view, the view will be COW'd and
                    // replace by the specific view after the reload. Thus the id in
                    // URL won't exist anymore. We need to find the specific ID.
                    var context = weContext.get();
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
            }
            return $.when.apply($, defs).then((function () {
                window.location.reload();
                return $.Deferred();
            }));
        }).bind(this));
    },
    /**
     * @override
     */
    _resetResource: function () {
        return this._super.apply(this, arguments).then((function () {
            window.location.reload();
            return $.Deferred();
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
