$(document).ready(function() {
    $('.js_next').click(function(event) {
        event.preventDefault();
        var translationValue  = $('.cover_footer').get(0).getBoundingClientRect().top;
        newLocation = this.href;
        $('.blog_cover').addClass('page_fadeup_out');
      
      $('.cover_footer')
        .addClass('page_upward')
        .css({ "transform": "translate3d(0, -"+ translationValue +"px, 0)" })
        .fadeIn(10000, newpage);
    });
    function newpage() {
        $.ajax({
          url: newLocation,
        }).done(function(data) {
           document.getElementsByTagName('html')[0].innerHTML = data;
           if (newLocation != window.location) {
                history.pushState(null, null, newLocation);
            }
        });
    }
});
