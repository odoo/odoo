(function() {
    // Init headless webclient (TODO: check embedded mode)
    var $web = $('<div style="width: 300px; height: 300px; position: absolute; bottom: 0; right: 0;"/>').appendTo($('body'));
    var s = new openerp.init(['web']);
    var wc = new s.web.WebClient();
    wc.appendTo($web);

    $(function() {
        $('.editable').css('outline', '1px solid red').attr('contentEditable', 'true').click(function (e) {
            e.stopPropagation();
            e.preventDefault();
        });
    });
})();
