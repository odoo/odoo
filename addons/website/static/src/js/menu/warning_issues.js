odoo.define('website.warning_issues', function (require) {
'use strict';

var core = require('web.core');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

const NUMBER_OF_WORDS_PER_H2 = 300;

var WarningIssues = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    /**
     * Identifies the common issues on the page and display them in the navbar.
     *
     * @override
     */
    start: function () {
        this.hasEntry = false;
        this._check_images_alt();
        this._check_images_size();
        this._check_headings();
        /* Some stuff to check if this PR goes forward :
        - Low Content page
        - No description header
        - Over 70 characters headings
        - Check if keywords are used in title ? Or at least a ratio of them if the keyword tag has keywords
        - A lot of other things :) !
        */
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a warning text to the warning dropdown.
     *
     * @private
     * @params {String} text text of the dropdown menu entry
     * @params {String} [tooltip] if set, adds a tooltip helper to the dropdown menu entry
     */
    _add_entry: function (text, tooltip) {
        if (!this.hasEntry) {
            this.hasEntry = true;
            this.$el.removeClass('d-none');
        }
        const $span = $('<span/>', {
            class: 'dropdown-item',
            html: text,
            role: 'menuitem',
        });
        $span.insertBefore(this.$('.dropdown-menu a'));
        if (tooltip) {
            const $tooltip = $('<i/>', {class: "fa fa-question-circle ml-1", title: tooltip});
            $span.append($tooltip);
            $tooltip.tooltip();
        }
    },
    /**
     * Check if images have an alt attribute.
     *
     * @private
     */
    _check_images_alt: function () {
        const imgs = $('#wrapwrap img:not([alt]):not([role="presentation"])');
        if (imgs.length === 1) {
            this._add_entry(_t("1 image has no alt attribute"), imgs[0].src);
        } else if (imgs.length > 1) {
            const tooltip = _.map(imgs, img => img.src);
            this._add_entry(_.str.sprintf(_t("%s images have no alt attribute"), imgs.length), tooltip.join('\n'));
        }
    },
    /**
     * Check if images are overweighted.
     *
     * @private
     */
    _check_images_size: function () {
        // TODO this won't work as images are loading async / on scroll
        // TODO check image dialog business logic to detect good size + acceptable margin and mimick here
        const badImgs = [];
        for (const img of $('#wrapwrap img')) {
            if (img.naturalWidth > 500 || img.naturalHeight > 500) { // random values for now
                badImgs.push(img.src);
            }
        }
        if (badImgs.length === 1) {
            this._add_entry(_t("1 image is overweighted"), badImgs[0]);
        } else if (badImgs.length > 1) {
            this._add_entry(_.str.sprintf(_t("%s images are overweighted")), badImgs.join(', '));
        }
    },
    /**
     * Check if heading tags are correctly set.
     *
     * @private
     */
    _check_headings: function () {
        const nbH1 = $('#wrap h1').length;
        const hbH2 = $('#wrap h2').length;

        // 1. Only 1 <h1>
        if (nbH1 > 1) {
            this._add_entry(_t("More than one h1"));
        } else if (nbH1 === 0) {
            this._add_entry(_t("Missing a h1"));
        }

        // 2. If text is long, there should be h2
        const nbWords = $('#wrap').text().replace(/\n/g, ' ') // return lines
                                          .replace(/ +(?= )/g, '') // multiple spaces
                                          .trim().split(' ').length;
        if (nbWords > NUMBER_OF_WORDS_PER_H2 && hbH2 === 0) {
            this._add_entry(_t("More than 300 words, structure the page with some h2"));
        } else if (nbWords / (NUMBER_OF_WORDS_PER_H2 * hbH2) > 1) {
            this._add_entry(_.str.sprintf(_t("Not enough h2, consider adding one for every %s words"), NUMBER_OF_WORDS_PER_H2));
        }
    },
});

websiteNavbarData.websiteNavbarRegistry.add(WarningIssues, '#warning-issues');

return {
    WarningIssues: WarningIssues,
};
});
