odoo.define('website_event.snippet_options', function (require) {
"use strict";

var core = require('web.core');
var options = require('web_editor.snippets.options');

var qweb = core.qweb;


/**
 * Allows to edit the timezone field easily with dropdown-menu.
 */

options.registry["timezone"] = options.Class.extend({
    xmlDependencies: ['/website_event/static/src/xml/snippets.xml'],
    start: function() {
        this._initializeTimezoneDropdown();
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        this.$target.attr('contentEditable', 'false');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize the timezone dropdown-menu.
     *
     * @private
     */
    _initializeTimezoneDropdown: function() {
        var self = this;
        this._rpc({
            route:"/get/timezone"
        }).then(function (timezones) {
            self.$timezone = $(qweb.render("web_editor.timezone", {'timezones':timezones}))
                .insertAfter(self.$overlay.find('.oe_options'));
            self.$timezone.val(self.$target.text());
            self.$timezone.on('change', self._onTimezoneChange.bind(self));
        });
       
    },
    /**
     * @private
     */
    _onTimezoneChange: function() {
        this.$target.text(this.$timezone.val());
        this.$target.trigger('content_changed');
    }

});

});
