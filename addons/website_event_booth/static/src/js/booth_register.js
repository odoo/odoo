odoo.define('website_event_booth.booth_registration', function (require) {
'use strict';

var dom = require('web.dom');
var publicWidget = require('web.public.widget');

publicWidget.registry.boothRegistration = publicWidget.Widget.extend({
    selector: '.o_wbooth_registration',
    events: {
        'change input[name="booth_category_id"]': '_onChangeBoothType',
        'change .custom-checkbox > input[type="checkbox"]': '_onChangeBooth',
        'click .o_wbooth_registration_submit': '_onSubmitClick',
    },

    start() {
        this.eventId = parseInt(this.$el.data('event-id'));
        this.activeType = false;
        this.boothCache = {};
        return this._super.apply(this, arguments).then(() => {
            this.$('input[name="booth_category_id"]:enabled:first').click();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _check_booths_availability(eventBoothIds) {
        const self = this;
        return this._rpc({
            route: "/event/booth/check_availability",
            params: {
                event_booth_ids: eventBoothIds,
            },
        }).then(function (result) {
            if (result.unavailable_booths.length) {
                self.$('input[name="event_booth_ids"]').each(function (i, el) {
                    if (result.unavailable_booths.includes(parseInt(el.value))) {
                        $(el).closest('.custom-checkbox').addClass('text-danger');
                    }
                });
                self.$('.o_wbooth_unavailable_booth_alert').removeClass('d-none');
                return Promise.resolve(false);
            }
            return Promise.resolve(true);
        })
    },

    _countSelectedBooths() {
        return this.$('.custom-checkbox > input[type="checkbox"]:checked').length;
    },

    _fillBooths() {
        var $boothElem = this.$('.o_wbooth_booths');
        $boothElem.empty();
        $.each(this.boothCache[this.activeType], function (key, booth) {
            let $checkbox = dom.renderCheckbox({
                text: booth.name,
                prop: {
                    name: 'event_booth_ids',
                    value: booth.id
                }
            });
            $boothElem.append($checkbox);
        });
    },

    _showBoothCategoryDescription() {
        this.$('.o_wbooth_booth_description').addClass('d-none');
        this.$('#o_wbooth_booth_description_' + this.activeType).removeClass('d-none');
    },

    _updateUiAfterBoothCategoryChange() {
        this._fillBooths();
        this._showBoothCategoryDescription();
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _updateUiAfterBoothChange(boothCount) {
        let $button = this.$('button.o_wbooth_registration_submit');
        $button.attr('disabled', !boothCount);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeBooth(ev) {
        $(ev.currentTarget).closest('.custom-checkbox').removeClass('text-danger');
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    /**
     * Load all the booths related to the chosen booth category and
     * add them to a local dictionary to avoid making rpc each time the
     * user change the booth category.
     *
     * Then the selection input will be filled with the fetched booth values.
     *
     * @param ev
     * @private
     */
    _onChangeBoothType(ev) {
        ev.preventDefault();
        this.activeType = parseInt(ev.currentTarget.value);
        if (this.boothCache[this.activeType] === undefined) {
            var self = this;
            this._rpc({
                route: '/event/booth_category/get_available_booths',
                params: {
                    event_id: this.eventId,
                    booth_category_id: this.activeType,
                },
            }).then(function (result) {
                self.boothCache[self.activeType] = result;
                self._updateUiAfterBoothCategoryChange();
            });
        } else {
            this._updateUiAfterBoothCategoryChange();
        }
    },

    async _onSubmitClick(ev) {
        ev.preventDefault();
        let $form = this.$('.o_wbooth_registration_form');
        let event_booth_ids = this.$('input[name=event_booth_ids]:checked').map(function () {
            return parseInt($(this).val());
        }).get();
        if (await this._check_booths_availability(event_booth_ids)) {
            $form.submit();
        }
    },

});

return publicWidget.registry.boothRegistration;
});
