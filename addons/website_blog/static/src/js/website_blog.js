$(document).ready(function () {
    $('.js_nav_year a:first').on('click', function (e) {
        e.preventDefault();
        $(this).next("ul").toggle();
    });

    $('.js_nav_month a:first').on('click', function (e) {
        e.preventDefault();
        var $ul = $(this).next("ul");
        if (!$ul.find('li').length) {
            // TODO: Why POST? A GET would be more appropriate...
            // This should be done server side anyway...
            $.post('/blog/nav', {'domain': $(this).data("domain")}, function (result) {
                var blog_id = +window.location.pathname.split("/").pop();
                $(JSON.parse(result)).each(function () {
                    var $li = $($.parseHTML(this.fragment));
                    if (blog_id == this.id) $li.addClass("active");
                    if (!this.website_published) $li.find('a').css("color", "red");
                    $ul.append($li);
                });

            });
        } else {
            $ul.toggle();
        }
    });

});