$(document).ready(function () {
    $(".o_download_plugin").on('click', function(e) {
        if (!$('#o_install_guideline').hasClass('o_menu_opened')) {
            $('#o_install_guideline').toggleClass('o_menu_opened').siblings('ul').toggle();
        }
    });
    $("#o_install_guideline").on('click', function(e) {
        $('#o_install_guideline').toggleClass('o_menu_opened').siblings('ul').toggle();
    });
});