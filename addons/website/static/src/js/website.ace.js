odoo.define('website.ace', function (require) {
'use strict';

var Widget = require('web.Widget');
var website = require('website.website');

var ViewEditor = require('web_editor.ace');

var hash = "#advanced-view-editor";

var Ace = Widget.extend({
    events: {
        "click a[data-action=ace]": function (e) {
            e.preventDefault();
            this.launchAce();
        },
    },
    start: function () {
        if (window.location.hash.substr(0, hash.length) === hash) {
            this.launchAce();
        }
        return this._super.apply(this, arguments);
    },
    launchAce: function () {
        if (this.globalEditor) {
            this.globalEditor.do_show();
        } else {
            var currentHash = window.location.hash;
            var indexOfView = currentHash.indexOf("?view=");
            var initialViewID = undefined;
            if (indexOfView >= 0) {
                initialViewID = parseInt(currentHash.substr(indexOfView + 6), 10);
            }

            this.globalEditor = new ViewEditor(this, $(document.documentElement).data('view-xmlid'), {
                initialViewID: initialViewID
            });
            this.globalEditor.appendTo(document.body);

            $("a[data-action=edit]").on("click", this.globalEditor.do_hide.bind(this.globalEditor));
        }
    },
});

/**
 * Extend the default view editor so that the URL hash is updated with view id.
 */
ViewEditor = ViewEditor.extend({
    displayView: function () {
        this._super.apply(this, arguments);
        this._updateHash();
    },
    saveResources: function () {
        return this._super.apply(this, arguments).then((function () {
            this._updateHash();
            window.location.reload();
        }).bind(this));
    },
    do_hide: function () {
        this._super.apply(this, arguments);
        window.location.hash = "";
    },
    _updateHash: function () {
        window.location.hash = hash + "?view=" + this.selectedViewId();
    },
});

website.TopBar.include({
    start: function () {
        this.ace = new Ace();
        return $.when(
            this._super.apply(this, arguments),
            this.ace.attachTo(this.$('#html_editor'))
        );
    },
});

});
