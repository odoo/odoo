odoo.define("l10n_pe_website_sale.website_sale", function (require) {
    "use strict";

    var websiteSale = require("website_sale.website_sale");
    var publicWidget = require("web.public.widget");

    publicWidget.registry.WebsiteSale = websiteSale.WebsiteSale.extend({
        events: _.extend({}, websiteSale.WebsiteSale.prototype.events, {
            'change select[name="state_id"]': "_onChangeState",
            'change select[name="city_id"]': "_onChangeCity",
        }),
        _changeState: function () {
            if (!$("#state_id").val()) {
                return;
            }
            this._rpc({
                route: "/shop/state_infos/" + $("#state_id").val(),
                params: {
                    mode: $("#country_id").attr("mode"),
                },
            }).then(function (data) {
                // populate cities and display
                var selectCities = $("select[name='city_id']");
                var selectDistricts = $("select[name='l10n_pe_district']");
                if (data.cities.length) {
                    selectCities.html("");
                    selectCities.append($("<option>").text("City..."));
                    _.each(data.cities, function (c) {
                        var opt = $("<option>").text(c[1]).attr("value", c[0]).attr("data-code", c[2]);
                        selectCities.append(opt);
                    });
                    selectCities.parent("div").show();
                } else {
                    selectCities.val("").parent("div").hide();
                }
                selectDistricts.val("").parent("div").hide();
            });
        },
        _changeCity: function () {
            if (!$("#city_id").val()) {
                return;
            }
            this._rpc({
                route: "/shop/city_infos/" + $("#city_id").val(),
                params: {
                    mode: $("#country_id").attr("mode"),
                },
            }).then(function (data) {
                // populate districts and display
                var selectDistricts = $("select[name='l10n_pe_district']");
                if (data.districts.length) {
                    selectDistricts.html("");
                    _.each(data.districts, function (d) {
                        var opt = $("<option>").text(d[1]).attr("value", d[0]).attr("data-code", d[2]);
                        selectDistricts.append(opt);
                    });
                    selectDistricts.parent("div").show();
                } else {
                    selectDistricts.val("").parent("div").hide();
                }
            });
        },
        _onChangeState: function (ev) {
            if (!this.$(".checkout_autoformat").length) {
                return;
            }
            this._changeState();
        },
        _onChangeCity: function (ev) {
            if (!this.$(".checkout_autoformat").length) {
                return;
            }
            this._changeCity();
        },
    });
    return {
        WebsiteSale: publicWidget.registry.WebsiteSale,
    };
});
