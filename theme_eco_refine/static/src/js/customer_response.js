odoo.define('theme_eco_refine.customer_response_snippet', function (require) {
    'use strict';
    // Function for customer response snippet
     self.$('.owl-carousel1').owlCarousel({
          loop: true,
          margin: 10,
          navText: ["Prev", "Next"],
          nav: false,
          autoplay: true,
          responsive: {
            0: {
              items: 2
            },
            600: {
              items: 3
            },
            1000: {
              items: 5
            }
          }
    });
     self.$(".owl-carousel2").owlCarousel({
          items: 1,
          loop: true,
          nav: false,
          dots: false,
    });
    // Custom navigation
    self.$(".custom-nav__prev").click(function () {
      $(".owl-carousel2").trigger("prev.owl.carousel");
    });
    self.$(".custom-nav__next").click(function () {
      $(".owl-carousel2").trigger("next.owl.carousel");
    });
});
