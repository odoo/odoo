odoo.define('website_event_booth.booth_registration', function (require) {
'use strict';

var dom = require('web.dom');
var publicWidget = require('web.public.widget');

publicWidget.registry.boothRegistration = publicWidget.Widget.extend({
    selector: '.o_wevent_booth_registration',
    events: {
        'change input[name="booth_category_id"]': '_onChangeBoothType',
        'change .custom-checkbox > input[type="checkbox"]': '_onChangeBooth',
        'click .booth-submit': '_onSubmitClick',
    },

    start() {
        this.eventId = parseInt(this.$el.data('event-id'));
        this.activeType = false;
        this.boothIds = {};
        return this._super.apply(this, arguments);
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
        if (this.boothIds[this.activeType] === undefined) {
            var self = this;
            this._rpc({
                route: '/event/booth_category/get_available_booths',
                params: {
                    event_id: this.eventId,
                    booth_category_id: this.activeType,
                },
            }).then(function (result) {
                self.boothIds[self.activeType] = result;
                self._updateUiAfterBoothCategoryChange();
            });
        } else {
            this._updateUiAfterBoothCategoryChange();
        }
    },
    
    _updateUiAfterBoothCategoryChange() {
        this._fillBooths();
        this._showBoothCategoryDescription();
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _showBoothCategoryDescription() {
        this.$el.find('.o_wevent_booth_description').addClass('d-none');
        this.$el.find('#booth_description_' + this.activeType).removeClass('d-none');
    },
    
    _fillBooths() {
        var $boothElem = this.$el.find('.o_wevent_booths');
        $boothElem.empty();
        $.each(this.boothIds[this.activeType], function (key, booth) {
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

    _onChangeBooth(ev) {
        $(ev.currentTarget).closest('.custom-checkbox').removeClass('text-danger');
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _countSelectedBooths() {
        return this.$('.custom-checkbox > input[type="checkbox"]:checked').length;
    },

    _updateUiAfterBoothChange(boothCount) {
        let $button = this.$('button.booth-submit');
        $button.attr('disabled', !boothCount);
    },

    async _onSubmitClick(ev) {
        ev.preventDefault();
        let $form = this.$('#booth-registration');
        let params = this._serializeForm($form);
        console.log(params);
        if (await this._check_booths_availability(params.event_booth_ids)) {
            $form.submit();
        }
    },

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
                self.$('.o_wevent_booth_unavailable_alert').removeClass('d-none');
                return Promise.resolve(false);
            }
            return Promise.resolve(true);
        })
    },

    _serializeForm($form) {
        let result = {};
        let array = $form.serializeArray();
        $.each(array, function () {
            let value = (isNaN(this.value)) ? this.value : parseInt(this.value);
            if (result[this.name] !== undefined) {
                if (!result[this.name].push) {
                    result[this.name] = [result[this.name]];
                }
                result[this.name].push(value || '');
            } else {
                result[this.name] = value || '';
            }
        });
        return result;
    },
});

return publicWidget.registry.boothRegistration;
});
