odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');

$(document).ready(function () {

    // Catch registration form event, because of JS for attendee details
    $('#registration_form .a-submit')
        .off('click')
        .removeClass('a-submit')
        .click(function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var $form = $(ev.currentTarget).closest('form');
            var post = {};
            $("select").each(function() {
                post[$(this)[0].name] = $(this).val();
            });
            ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.appendTo($form).modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        });
});

});
