odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');
var Widget = require('web.Widget');
var web_editor_base = require('web_editor.base')

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({
    start: function() {
        var self = this;
        var res = this._super.apply(this.arguments).then(function() {
            $('#registration_form .a-submit')
                .off('click')
                .removeClass('a-submit')
                .click(function (ev) {
                    self.on_click(ev);
                });
        });
        return res
    },
    on_click: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var post = {};
        $("#registration_form select").each(function() {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function(value, key) { return parseInt(value) }));
        if (! tickets_ordered) {
            return $('#registration_form table').after(
                '<div class="alert alert-info">Please select at least one ticket.</div>'
            );
        }
        else {
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.appendTo($form).modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        }
    },
});

var TimeZoneForm = Widget.extend({

    start: function() {
        var self = this;
        return this._super.apply(this.arguments).then(function() {
            $('.o_user_timezone')
                .off('click')
                .click(function (event) {
                    self._onUserTimezoneClick(event);
                });
        });
    },

    _onUserTimezoneClick: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var action = $(event.currentTarget).closest('form#user_timezone').attr('action');

        return ajax.jsonRpc(action, 'call', {}).then(function (modal) {
            var $modal = $(modal),
                tzContainer = $modal.find('#timezone-container');

            $modal.appendTo('body').modal();
            ajax.jsonRpc('/event/get_all_timezone', 'call', {}).done(function(data) {
                _.each(data, function(value, key) {
                    $('<option>'+ value +'</option>').appendTo(tzContainer);
                });
            });

            $modal.on('click', '.o_set_timezone_btn', function () {
                var user_local_tz = tzContainer.val(),
                    $visitordate = $('h4.o_event_visitor_date'),
                    event_date = {};

                $modal.modal('hide');
                $visitordate.find('.o_visitor_timezone').text(user_local_tz);

                // find value of start date and end date from event
                event_date.starting_date = $visitordate.find('.o_event_starting_date').data('eventVisitorDate'),
                event_date.ending_date = $visitordate.find('.o_event_ending_date').data('eventVisitorDate');

                ajax.jsonRpc("/event/set_timezone", 'call', {
                    timezone: user_local_tz,
                    date_time: event_date
                }).done(function(data) {
                    // set value of start date and end date in event
                    $('.o_event_starting_date').text(data.starting_date);
                    $('.o_event_ending_date').text(data.ending_date);
                });
            });

            $modal.on('click', '.js_goto_event', function () {
                $modal.modal('hide');
            });
        });
    },
});

web_editor_base.ready().then(function(){
    _.each($('[data-event-visitor-date]'), function (el) {
        $(el).text(
            moment.utc($(el).data('event-visitor-date'))
            .utcOffset(moment().utcOffset()).format("L HH:mm"));
   });
    _.each($('.o_visitor_timezone'), function (el) {
        $(el).text(jstz.determine().name());
    });
    var event_registration_form = new EventRegistrationForm().appendTo($('#registration_form'));
    var timezone_selection_form = new TimeZoneForm().appendTo($('.o_user_timezone'));
});

return { EventRegistrationForm: EventRegistrationForm };

});
