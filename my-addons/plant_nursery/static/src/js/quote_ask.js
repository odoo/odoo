odoo.define('plant_nursery.quote_ask.instances', function (require){
    'use strict';

    require('web_editor.ready');
    var QuoteAsk = require('plant_nursery.quote_ask');

    $('.o_plant_quote_ask').each(function () {
        var $elem = $(this);
        var form = new QuoteAsk(null, $elem.data());
        form.appendTo($elem);
    });
});

odoo.define('plant_nursery.quote_ask', function (require){
    'use strict';

    require('web_editor.ready');

    var core = require('web.core');
    var rpc = require("web.rpc");
    var Widget = require("web.Widget");

    var qweb = core.qweb;

    var QuoteAsk = Widget.extend({
        template: 'plant_nursery.quote_ask',
        xmlDependencies: [
            '/plant_nursery/static/src/xml/quote_ask.xml',
        ],
        events: {
            'click #o_quote_reset': 'resetQuote',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.plants = {
                promo: [],
                free: [],
            };
            this.options = _.extend(options || {}, {
                csrf_token: odoo.csrf_token,
            });
        },

        willStart: function () {
            return $.when(
                this._super.apply(this, arguments),
                this._fetchPlantData()
            );
        },

        start: function () {
            this._displayPlants();
            return this._super.apply(this, arguments);
        },

        resetQuote: function (ev) {
            ev.preventDefault();
            var self = this;
            return this._fetchPlantData().then(function () {
                self._displayPlants();
            });
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        _fetchPlantData: function () {
            var self = this;
            return rpc.query({
                route: '/plant/get_random_quote',
                params: {
                },
            }).then(function (data) {
                self.plants = data;
            });
        },

        _displayPlants: function () {
            var $plants = qweb.render("plant_nursery.quote_ask_plants", {widget: this});
            this.$('.o_plant_quote_content').html($plants);
        },

    });

    return  QuoteAsk;
});