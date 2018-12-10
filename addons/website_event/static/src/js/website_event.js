odoo.define('website_event.registration_form.instance', function (require) {
'use strict';

require('web_editor.ready');
var EventRegistrationForm = require('website_event.website_event');

var $form = $('#registration_form');
if (!$form.length) {
    return null;
}

var instance = new EventRegistrationForm();
return instance.appendTo($form).then(function () {
    return instance;
});
});

//==============================================================================

odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({
    start: function () {
        var self = this;
        var res = this._super.apply(this.arguments).then(function () {
            $('#registration_form .a-submit')
                .off('click')
                .removeClass('a-submit')
                .click(function (ev) {
                    self.on_click(ev);
                });
        });
        if($('.o_right_col').children().length == 0){
            $('.o_right_col').addClass('d-none');
        }
        return res;
    },
    on_click: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        var post = {};
        $('#registration_form table').siblings('.alert').remove();
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function (value, key) { return parseInt(value); }));
        if (!tickets_ordered) {
            $('<div class="alert alert-info"/>')
                .text(_t('Please select at least one ticket.'))
                .insertAfter('#registration_form table');
            return $.Deferred();
        } else {
            $button.attr('disabled', true);
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.modal({backdrop: 'static', keyboard: false});
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.appendTo('body').modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                    $button.prop('disabled', false);
                });
                $modal.on('click', '.close', function () {
                    $button.prop('disabled', false);
                });
            });
        }
    },
});

return EventRegistrationForm;
});

// To remove or not the right col in the 
odoo.define('website_event.o_event_list_container.secondInstance', function (require) {
'use strict';

require('web_editor.ready');
var EventRightColDisplay = require('website_event.website_event');

var $rightCol = $('#o_event_list_container');
if (!$rightCol.length) {
    return null;
}

var secondInstance = new EventRightColDisplay();
return secondInstance.appendTo($rightCol).then(function () {
    return secondInstance;
});
});

//==============================================================================

odoo.define('website_event.website_event_display_col', function (require) {

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

// test to display or not the right col
var EventRightColDisplay = Widget.extend({
    start: function () {
        var self = this;
        if($('.o_right_col').children().length == 0){
            $('.o_right_col').addClass('d-none');
        }
    },
});

return EventRightColDisplay;
});