/** @odoo-module **/
import { Component, useRef} from "@odoo/owl";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.Swiper = publicWidget.Widget.extend({
    selector: '.swiper',

    start: function () {
        // Ensure Swiper is available before initializing
        if (typeof Swiper === 'undefined') {
            return;
        }
        // Initialize Swiper on the element with class '.mySwiper-1' when the component is mounted
        var swiper1 = new Swiper(".mySwiper-1", {
            slidesPerView: 3,
            spaceBetween: 30,
            pagination: {
            el: ".swiper-pagination",
            clickable: true,
            },
        });
        var swiper6 = new Swiper(".mySwiper-6", {
                slidesPerView: 3,
                spaceBetween: 30,
                pagination: {
                  el: ".swiper-pagination",
                  clickable: true,
                },
            });

       var swiper = new Swiper(".mySwiper-5", {
                slidesPerView: 3,
                spaceBetween: 30,
                pagination: {
                  el: ".swiper-pagination",
                  clickable: true,
                },
          });
       var swiper = new Swiper(".mySwiper-4", {
              slidesPerView: 3,
              spaceBetween: 30,
              freeMode: true,
              pagination: {
                el: ".swiper-pagination",
                clickable: true,
              },
           });
    },
});
