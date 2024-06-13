/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.websiteSaleAddress = publicWidget.Widget.extend({
    // /shop/address
    selector: '.o_wsale_address_fill',
    events: {
        'change select[name="country_id"]': '_onChangeCountry',
        'change #shipping_use_same': '_onChangeShippingUseSame',
        "change select[name='state_id']": "_onChangeState",
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._changeCountry = debounce(this._changeCountry.bind(this), 500);
    },

    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        this.$('select[name="country_id"]').change();

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCountry: function (ev) {
        if (!this.$('.checkout_autoformat').length) {
            return;
        }
        return this._changeCountry();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeState: function (ev) {
        return Promise.resolve();
    },

    /**
     * @private
     */
    _changeCountry: function () {
        if (!$("#country_id").val()) {
            return;
        }
        return rpc("/shop/country_infos/" + $("#country_id").val(), {
            mode: $("#country_id").attr('mode'),
        }).then(function (data) {
            // placeholder phone_code
            $("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

            // populate states and display
            var selectStates = $("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length || data.state_required) {
                    selectStates.html('');
                    data.states.forEach((x) => {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                            .attr('data-code', x[2]);
                        selectStates.append(opt);
                    });
                    selectStates.parent('div').show();
                } else {
                    selectStates.val('').parent('div').hide();
                }
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }

            // manage fields order / visibility
            if (data.fields) {
                if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                    $(".div_zip").before($(".div_city"));
                } else {
                    $(".div_zip").after($(".div_city"));
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                all_fields.forEach((field) => {
                    $(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields)>=0);
                });
            }

            if ($("label[for='zip']").length) {
                $("label[for='zip']").toggleClass('label-optional', !data.zip_required);
                $("label[for='zip']").get(0).toggleAttribute('required', !!data.zip_required);
            }
            if ($("label[for='zip']").length) {
                $("label[for='state_id']").toggleClass('label-optional', !data.state_required);
                $("label[for='state_id']").get(0).toggleAttribute('required', !!data.state_required);
            }
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeShippingUseSame: function (ev) {
        $('.ship_to_other').toggle(!$(ev.currentTarget).prop('checked'));
    },

});

export default publicWidget.registry.websiteSaleAddress;
