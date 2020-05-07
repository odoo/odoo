odoo.define('website.s_sponsors_options', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('wysiwyg.widgets');
var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');
var rpc = require('web.rpc');
var _t = core._t;
var qweb = core.qweb;

options.registry.sponsors = options.Class.extend({
    xmlDependencies: ['/website_event_track/static/src/xml/website_event_track_our_sponsors.xml'],

    /**
     * @override
     */
    start: function () {
        const sponsors = this.$target.attr('data-sponsors');
        this.sponsors = sponsors ? sponsors.split(',') : [];
        this.removeSponsor = 0;
        return this._super.apply(this, arguments);
    },
    selectSponsorId: function (previewMode, widgetValue, params) {
        if (this.sponsors.includes(widgetValue)) {
            this.do_warn(_t("Error"), _t("This sponsor is already added."));
            return;
        }
        this.sponsors.push(widgetValue);
        this.$target.attr("data-sponsors", this.sponsors.toString());
    },
    _renderCustomXML: function (uiFragment) {
        return this._rpc({
            model: 'event.sponsor',
            method: 'name_search',
            args: ['', []],
        }).then(sponsors => {
            const menuEl = uiFragment.querySelector('we-select[data-name="add_sponsor"]');
            if (sponsors.length && menuEl) {
                for (const sponsor of sponsors) {
                    const button = document.createElement('we-button');
                    button.dataset.selectSponsorId = sponsor[0];
                    button.textContent = sponsor[1];
                    menuEl.appendChild(button);
                }
            }
        });
    },
});

options.registry.remove_sponsors = options.Class.extend({
    xmlDependencies: ['/website_event_track/static/src/xml/website_event_track_our_sponsors.xml'],

    /**
     * @override
     */
    start: async function () {
        await this._super.apply(this, arguments);
        this.removeSponsor = 0;

        this.$target.on('click', function (ev) {
            this.removeSponsor = $(ev.currentTarget).attr('data-sponsor-id');
        });
    },
    removeSponsor: function (previewMode, widgetValue, params) {
        if (this.removeSponsor == 0) {
            this.do_warn(_t("Error"), _t("Select sponsor to remove."));
            return;
        }
        this.sponsors.splice(this.removeSponsor);
        this.$target.attr("data-sponsors", this.sponsors.toString());
    },

});
});
