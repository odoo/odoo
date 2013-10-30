$(document).ready(function () {
    $('.js_nav_year a:first').on('click', function (e) {
        e.preventDefault();
        $(this).next("ul").toggle();
    });

    $('.js_nav_month a:first').on('click', function (e) {
        e.preventDefault();
        var $ul = $(this).next("ul");
        if (!$ul.find('li').length) {
            $.post('/blog/nav', {'domain': $(this).data("domain")}, function (result) {
                var blog_id = +window.location.pathname.split("/").pop();
                $(JSON.parse(result)).each(function () {
                    var $a = $('<a href="/blog/' + this.id + '"/>').text(this.name);
                    var $li = $("<li/>").append($a);
                    if (blog_id == this.id)
                        $li.addClass("active");
                    if (!this.website_published)
                        $a.css("color", "red");
                    $ul.append($li);
                });

            });
        } else {
            $ul.toggle();
        }
    });

    var $form = $('.js_website_blog form#comment');
    $form.submit(function (e) {
        e.preventDefault();
        var error = $form.find("textarea").val().length < 3;
        $form.find("textarea").toggleClass("has-error", error);
        if (!error) {
            $form.css("visibility", "hidden");
            $.post(window.location.pathname + '/post', {'body': $form.find("textarea").val()}, function (url) {
                window.location.href = url
            });
        }
    });
});
