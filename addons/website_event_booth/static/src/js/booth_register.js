odoo.define('website_event_booth.booth_slot', function (require) {
'use strict';

var dom = require('web.dom');
var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventBoothSlot = publicWidget.Widget.extend({
    selector: '.o_wevent_booth_registration',
    events: {
        'change input[name="booth_category_id"]': '_onChangeBoothType',
        'change select[name="booth_id"]': '_onChangeBooth',
        'change .custom-checkbox > input[type="checkbox"]': '_onChangeSlots',
    },

    start: function () {
        this.eventId = parseInt(this.$el.data('event-id'));
        // TODO: get type from element data ?
        this.activeType = false;
        this.boothIds = {};
        return this._super.apply(this, arguments);
    },

    /**
     * Load all the booths and booth slots related to the chosen booth category
     * and add them to a local dictionary to avoid making rpc each time the
     * user change the booth category.
     *
     * Then the selection input will be filled with the fetched booth values.
     *
     * @param ev
     * @private
     */
    _onChangeBoothType: function (ev) {
        ev.preventDefault();
        this.activeType = parseInt(ev.currentTarget.value);
        if (this.boothIds[this.activeType] === undefined) {
            var self = this;
            this._rpc({
                route: '/event/booths/slots',
                params: {
                    event_id: this.eventId,
                    booth_category_id: this.activeType,
                },
            }).then(function (result) {
                self.boothIds[self.activeType] = result;
                self._fillBoothSelectionInput();
                self._showBoothCategoryDescription();
            });
        } else {
            this._fillBoothSelectionInput();
            this._showBoothCategoryDescription();
        }
    },

    _showBoothCategoryDescription: function () {
        this.$el.find('.o_wevent_booth_description').addClass('d-none');
        this.$el.find('#booth_description_' + this.activeType).removeClass('d-none');
    },

    _fillBoothSelectionInput: function () {
        var $selectionElem = this.$el.find('select[name="booth_id"]');
        $selectionElem.empty();
        $.each(this.boothIds[this.activeType], function (key, booth) {
            $selectionElem.append($('<option/>').text(booth.name).attr('value', booth.id))
        });
        if (!$selectionElem.is(':empty')) {
            $selectionElem.attr('disabled', false);
            $selectionElem.trigger('change');
        }
    },

    /**
     * When the user chooses an event booth, the checkboxes corresponding to the
     * available slots will be created.
     *
     * @param ev
     * @private
     */
    _onChangeBooth: function (ev) {
        ev.preventDefault();
        var boothId = parseInt(ev.currentTarget.value);
        var booth = this.boothIds[this.activeType].filter(booth => booth.id === boothId)[0];
        this.$('.o_wevent_booth_slots_group').removeClass('d-none');
        this._fillBoothSlots(booth.slot_ids);
    },

    _fillBoothSlots: function (boothSlotIds) {
        var $slotsElem = this.$el.find('.o_wevent_booth_slots');
        $slotsElem.empty();
        $.each(boothSlotIds, function (key, slot) {
            let $checkbox = dom.renderCheckbox({
                text: slot.display_name,
                prop: {
                    name: 'event_booth_slot_ids',
                    value: slot.id
                }
            });
            $slotsElem.append($checkbox);
        });
    },

    _onChangeSlots: function () {
        let atLeastOneSlotSelected = this.$('.custom-checkbox > input[type="checkbox"]').is(':checked');
        let $button = this.$('button.booth-submit');
        $button.attr('disabled', !atLeastOneSlotSelected);
    },
});

    return {
        websiteEventBoothSlot: publicWidget.registry.websiteEventBoothSlot
    };

});
