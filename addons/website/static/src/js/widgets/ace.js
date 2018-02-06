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
            this._updateHash();
            window.location.reload();
            return $.Deferred();
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
    _updateHash: function () {
        window.location.hash = this.hash + "?res=" + this._getSelectedResource();
    },
});

return WebsiteAceEditor;
});
