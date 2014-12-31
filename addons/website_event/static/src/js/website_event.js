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
            openerp.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.appendTo($form).modal()
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        });

        $('#event_search, #category_submit').click(function (e){
            $('#search_event .dropdown-menu').toggle();
            $('.event-submit-btn').hide();
        });
        $('#search_event .dropdown-menu').click(function(event){
            event.stopPropagation();
        });
        $(document).click(function () {
            $('#search_event .dropdown-menu').hide();
            $('.event-submit-btn').show();
        })
});
