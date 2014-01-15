(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.BuildingBlock.include({

        // init: function (parent) {
        //     this._super.apply(this, arguments);
        // },

        _get_snippet_url: function () {
            return '/website_mail/snippets';
        }

    });
})();
