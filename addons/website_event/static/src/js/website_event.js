odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');

$(document).ready(function () {

    // Catch registration form event, because of JS for attendee details
    $('#registration_form .a-submit')
        .off('click')
        .removeClass('a-submit')
        .click(function (ev) {
            $(this).attr('disabled', true);
            ev.preventDefault();
            ev.stopPropagation();
            var $form = $(ev.currentTarget).closest('form');
            var $button = $(this);
            var post = {};
            $("select").each(function() {
                post[$(this)[0].name] = $(this).val();
            });
            ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                // Only needed for 9.0 up to saas-14
                if (modal === false) {
                    $button.prop('disabled', false);
                    return;
                }
                var $modal = $(modal);
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.insertAfter($form).modal();
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                    $button.prop('disabled', false);
                });
            });
        });
});

});
