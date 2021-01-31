odoo.define("deltatech_website_city.portal", function(require) {
    "use strict";

    require("web.dom_ready");
    require("portal.portal");
    require("deltatech_website_city.website_sale");

    var sAnimations = require("website.content.snippets.animation");

    sAnimations.registry.WebsitePortalCity = sAnimations.Class.extend({
        selector: ".o_portal_details",
        read_events: {
            'change select[name="state_id"]': "_onChangeState",
            'change select[name="city_id"]': "_onChangeCity",
        },

        init: function() {
            this._super.apply(this, arguments);
            this._changeState = _.debounce(this._changeState.bind(this), 500);
            this.isWebsite = true;
        },

        start: function() {
            var def = this._super.apply(this, arguments);
            this.$('select[name="state_id"]').change();
            return def;
        },

        _onChangeCity: function() {
            if (!$("select[name='city_id']").val()) {
                return;
            }
            var selectCity = $('select[name="city_id"] option:selected');
            var zipcode = selectCity.attr("data-code");

            $("input[name='zipcode']").val(zipcode);
            $("input[name='city']").val(selectCity.text());
        },

        _onChangeState: function() {
            this._changeState();
        },

        _changeState: function() {
            var state_id = $("select[name='state_id']");
            if (!state_id.val()) {
                return;
            }
            this._rpc({
                route: "/shop/state_infos/" + state_id.val(),
                params: {
                    mode: "shipping",
                },
            }).then(function(data) {
                // Placeholder phone_code
                // $("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

                // populate states and display
                var selectCities = $("select[name='city_id']");
                var selected = selectCities.data("value");
                // Dont reload state at first loading (done in qweb)
                if (selectCities.data("init") === 0 || selectCities.find("option").length === 1) {
                    if (data.cities.length) {
                        $("input[name='city']")
                            .parent("div")
                            .hide();
                        selectCities.html("");
                        _.each(data.cities, function(x) {
                            var opt = $("<option>")
                                .text(x[1])
                                .attr("value", x[0])
                                .attr("data-code", x[2])
                                .attr("selected", x[0] === selected);
                            selectCities.append(opt);
                        });
                        selectCities.parent("div").show();
                    } else {
                        selectCities
                            .val("")
                            .parent("div")
                            .hide();
                        $("input[name='city']")
                            .parent("div")
                            .show();
                    }
                    selectCities.data("init", 0);
                } else {
                    selectCities.data("init", 0);
                }
            });
        },
    });

    /*
        If ($('.o_portal_details').length) {
            var city_options = $("select[name='city_id']:enabled option:not(:first)");
            $('.o_portal_details').on('change', "select[name='state_id']", function () {
                var select = $("select[name='city_id']");
                city_options.detach();
                var displayed_city = city_options.filter("[data-state_id=" + ($(this).val() || 0) + "]");
                var nb = displayed_city.appendTo(select).show().size();
                select.parent().toggle(nb >= 1);
            });
            $('.o_portal_details').find("select[name='state_id']").change();
        }
    */
});

odoo.define("deltatech_website_city.website_sale", function(require) {
    "use strict";

    require("website_sale.website_sale");
    var sAnimations = require("website.content.snippets.animation");

    sAnimations.registry.WebsiteSaleCity = sAnimations.Class.extend({
        selector: ".oe_website_sale",
        read_events: {
            'change select[name="country_id"]': "_onChangeCountry",
            'change select[name="state_id"]': "_onChangeState",
            'change select[name="city_id"]': "_onChangeCity",
        },

        init: function() {
            this._super.apply(this, arguments);
            this._changeState = _.debounce(this._changeState.bind(this), 600);
            this.isWebsite = true;
        },

        start: function() {
            // Reordonare campuri
            var div_country = $(".div_country");
            var div_state = $(".div_state");
            var div_city_id = $(".div_city_id");
            var div_city = $(".div_city");
            var div_zip = $(".div_zip");
            var div_street = $(".div_street");
            var div_street2 = $(".div_street2");

            div_state.insertAfter(div_country);
            div_city_id.insertAfter(div_state);
            div_city.insertAfter(div_city_id);
            div_zip.insertAfter(div_city);
            div_street.insertAfter(div_zip);
            div_street2.insertAfter(div_street);

            var def = this._super.apply(this, arguments);
            this.$('select[name="state_id"]').change();

            return def;
        },

        _onChangeCountry: function() {
            var selectCities = $("select[name='city_id']");
            selectCities.parent("div").hide();
            $("input[name='city']")
                .parent("div")
                .show();
        },

        _onChangeCity: function() {
            if (!$("select[name='city_id']").val()) {
                return;
            }
            var selectCity = $('select[name="city_id"] option:selected');
            var zipcode = selectCity.attr("data-code");

            $("input[name='zip']").val(zipcode);
            $("input[name='city']").val(selectCity.text());
        },

        _onChangeState: function() {
            if (!this.$(".checkout_autoformat").length) {
                return;
            }
            this._changeState();
            // This._onChangeCity();
        },

        _changeState: function() {
            var selectCities = $("select[name='city_id']");
            var selectState = $("select[name='state_id']");

            if (!selectState.val()) {
                return;
            }
            this._rpc({
                route: "/shop/state_infos/" + selectState.val(),
                params: {
                    mode: "shipping",
                },
            }).then(function(data) {
                // Placeholder phone_code
                // $("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

                // populate states and display

                // dont reload state at first loading (done in qweb)
                var selected = selectCities.data("value");
                if (selectCities.data("init") === 0 || selectCities.find("option").length === 1) {
                    if (data.cities.length) {
                        $("input[name='city']")
                            .parent("div")
                            .hide();
                        selectCities.html("");
                        _.each(data.cities, function(x) {
                            var opt = $("<option>")
                                .text(x[1])
                                .attr("value", x[0])
                                .attr("data-code", x[2])
                                .attr("selected", x[0] === selected);
                            // Selected="city.id == ('city_id' in checkout   and checkout['city_id'] != '' and int(checkout['city_id']))">
                            selectCities.append(opt);
                        });
                        selectCities.parent("div").show();
                    } else {
                        selectCities.parent("div").hide();
                        $("input[name='city']")
                            .parent("div")
                            .show();
                    }
                    selectCities.data("init", 0);
                } else {
                    selectCities.data("init", 0);
                }
            });
        },
    });
});
