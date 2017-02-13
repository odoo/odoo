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

web_editor_base.ready().then(function(){
    var event_registration_form = new EventRegistrationForm().appendTo($('#registration_form'));
});

return { EventRegistrationForm: EventRegistrationForm };

});
