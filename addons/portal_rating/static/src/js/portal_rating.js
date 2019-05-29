odoo.define ('portal_rating.portal_rating', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

/**
 * PortalRating
 *
 * Extend widget for rating, allow to change the rating from portal.
 */
publicWidget.registry.portalRating = publicWidget.Widget.extend({
    selector: '.o_portal_rating',
    events: {
        'click .o_rating': '_onClickSmiley',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickSmiley: function (ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        this.$el.find('img.o_portal_rating_smily').removeClass('o_poral_rating_active');
        $target.find('img.o_portal_rating_smily').addClass('o_poral_rating_active');
        this.$el.find("input[name='rate']").val($target.attr('id'));
        this.$el.find('form').attr('action', $target.attr('href'));
    },
});
});
