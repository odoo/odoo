odoo.define('sale.SalePortalSidebar.instance', function (require) {
"use strict";

require('web.dom_ready');
var SalePortalSidebar = require('sale.SalePortalSidebar');

if (!$('.o_portal_sale_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sale_sidebar'");
}

var $spyWatch = $('body[data-target=".navspy"]'),
    sale_portal_sidebar = new SalePortalSidebar($spyWatch);

return sale_portal_sidebar.attachTo($('.o_portal_sale_sidebar')).then(function () {
    return sale_portal_sidebar;
});
});

//==============================================================================

odoo.define('sale.SalePortalSidebar', function (require) {
"use strict";

var PortalSidebar = require('portal.PortalSidebar');

var SalePortalSidebar = PortalSidebar.extend({
    /**
     * @override
     * @param {Object} $watched_selector
     */
    init: function ($watched_selector) {
        this._super.apply(this, arguments);
        this.authorizedTextTag = ['em', 'b', 'i', 'u'];
        this.spyWatched = $watched_selector;
    },
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        var $spyWatcheElement = this.$el.find('[data-id="portal_sidebar"]');
        this._setElementId($spyWatcheElement);
        // Nav Menu ScrollSpy
        this._generateMenu();
    },

    //--------------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------------

    /**
     * create an unique id and added as a attribute of spyWatched element
     *
     * @private
     * @param {string} prefix
     * @param {Object} $el
     *
     */
    _setElementId: function (prefix, $el) {
        var id = _.uniqueId(prefix);
        this.spyWatched.find($el).attr('id', id);
        return id;
    },
    /**
     * generate the new spy menu
     *
     * @private
     *
     */
    _generateMenu: function () {
        var self = this,
            lastLI = false,
            lastUL = null,
            $bsSidenav = this.$el.find('.bs-sidenav');

        $("#quote_content [id^=quote_header_], #quote_content [id^=quote_]", this.spyWatched).attr("id", "");
        _.each(this.spyWatched.find("#quote_content h2, #quote_content h3"), function (el) {
            var id, text;
            switch (el.tagName.toLowerCase()) {
                case "h2":
                    id = self._setElementId('quote_header_', el);
                    text = self._extractText($(el));
                    if (!text) {
                        break;
                    }
                    lastLI = $("<li class='nav-item'>").append($('<a class="nav-link" href="#' + id + '"/>').text(text)).appendTo($bsSidenav);
                    lastUL = false;
                    break;
                case "h3":
                    id = self._setElementId('quote_', el);
                    text = self._extractText($(el));
                    if (!text) {
                        break;
                    }
                    if (lastLI) {
                        if (!lastUL) {
                            lastUL = $("<ul class='nav flex-column'>").appendTo(lastLI);
                        }
                        $("<li class='nav-item'>").append($('<a class="nav-link" href="#' + id + '"/>').text(text)).appendTo(lastUL);
                    }
                    break;
            }
        });
    },
    /**
     * extract text of menu title for sidebar
     *
     * @private
     * @param {Object} $node
     *
     */
    _extractText: function ($node) {
        var self = this;
        var rawText = [];
        _.each($node.contents(), function (el) {
            var current = $(el);
            if ($.trim(current.text())) {
                var tagName = current.prop("tagName");
                if (_.isUndefined(tagName) || (!_.isUndefined(tagName) && _.contains(self.authorizedTextTag, tagName.toLowerCase()))) {
                    rawText.push($.trim(current.text()));
                }
            }
        });
        return rawText.join(' ');
    },
});

return SalePortalSidebar;
});
