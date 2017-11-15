odoo.define('website_event.registration_form.instance', function (require) {
'use strict';

require('web_editor.ready');
var weContext = require('web_editor.context');
var EventRegistrationForm = require('website_event.website_event');

var $form = $('#registration_form');
var $userTimezone = $('#select_user_timezone');

if (!$form.length && !$userTimezone.length) {
    return null;
}

var instance = new EventRegistrationForm();
return instance.appendTo($form, $userTimezone).then(function () {
    // pass visitor timezone for calculation and store datetime as per user timezone
    // because of event page show visitor timezone, which is configure into event record
    // that's reason for update the context
    var get_context = weContext.get;
    weContext.get_context = function (context) {
        return _.extend({
            'visitor_tz': instance.getVisitorTimezone(),
        }, get_context(context), context);
    };
    return instance;
});
});

//==============================================================================

odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');
var Widget = require('web.Widget');

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({
    start: function () {
        var self = this;
        var res = this._super.apply(this.arguments).then(function () {
            $('#registration_form .a-submit')
                .off('click')
                .removeClass('a-submit')
                .click(function (ev) {
                    $(this).attr('disabled', true);
                    self.on_click(ev);
                });
        });

        //  modal for change timezone
        self.$modal = $('#select_user_timezone');
        self.$modal.find('.o_set_timezone_btn').on('click', self._onSetVisitorTimezoneClick.bind(self));
        self.setVisitorDatetime();
        return res;
    },

    _onSetVisitorTimezoneClick: function (event) {
        var $modal = this.$modal,
            Newtz = $modal.find('#timezone-container').val(),
            StartDate = $modal.find('input[name="event-origin-date-start"]').val(),
            EndDate = $modal.find('input[name="event-origin-date-end"]').val();

        $modal.modal('hide');
        ajax.jsonRpc("/event/set_timezone", 'call', {
            timezone: Newtz,
            date_time: {'start_date': StartDate, 'end_date': EndDate}
        }).done(function (datetime) {
            // set value of start date and end date on event page
            $('span.o_event_date_begin').text(datetime.start_date);
            $('span.o_event_date_end').text(datetime.end_date);
            $('span.o_event_timezone').text(Newtz);
        });
    },
    on_click: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var post = {};
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function (value, key) { return parseInt(value); }));
        if (!tickets_ordered) {
            return $('#registration_form table').after(
                '<div class="alert alert-info">Please select at least one ticket.</div>'
            );
        } else {
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.after($form).modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        }
    },
    /**
        get visitor's timzone name
    */
    getVisitorTimezone: function () {
        return jstz.determine().name();
    },
    /**
        set datetime on event page as per visitor's timezone
    */
    setVisitorDatetime: function () {
        _.each($('span.o_event_date_begin'), function (element) {
            $(element).text(moment.utc($(element).data('eventVisitorDate')).utcOffset(moment().utcOffset()).format("L HH:mm"));
        });
        _.each($('span.o_event_date_end'), function (element) {
            $(element).text(moment.utc($(element).data('eventVisitorDate')).utcOffset(moment().utcOffset()).format("L HH:mm"));
        });
        $('span.o_event_timezone').text(this.getVisitorTimezone());
    },
});

return EventRegistrationForm;
});
