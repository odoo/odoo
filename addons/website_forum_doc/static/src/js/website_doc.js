$(document).ready(function () {

    $(function () {
        $('.menu-tree li li').hide();
        $('.menu-tree li .active').parents().find(' > ul > li').show();
        $('.menu-tree li').on('click', function (e) {
            var children = $(this).find(' > ul > li');
            if (children.is(":visible")) {
                children.hide('fast');
                $(this).attr('title', 'Expand this branch');
            } else {
                children.show('fast');
                $(this).attr('title', 'Collapse this branch');
            }
            e.stopPropagation();
        });
    });

});
