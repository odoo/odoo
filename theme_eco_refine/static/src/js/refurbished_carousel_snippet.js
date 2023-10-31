odoo.define('theme_eco_refine.carousel_snippet', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
    publicWidget.registry.refurb_carousel_snippet = publicWidget.Widget.extend({
         selector: '.main_body_refurbished_carousel',
         events:{
         },
         start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(async function () {
                const carouselItems = self.el.querySelectorAll(".carousel-item");
                self.carouselItems = carouselItems
                self.startTypingForAll();
                const items = self.el.querySelectorAll('.ref-collection__item');
                items.forEach((item, index) => {
                    if (index === 0) {
                        item.classList.add('selected');
                    }
                    item.addEventListener('click', () => {
                        items.forEach(item => item.classList.remove('selected'));
                        item.classList.add('selected');
                    });
                });
            });
        },
        startTypingForAll:function() {
            var self = this;
            this.carouselItems.forEach(function (item) {
                var textContainer = item.querySelector(".ref-hero__mainhead");
                var textToType = textContainer.innerText;
                textContainer.innerHTML = "";
                self.typeNextCharacter(textContainer, textToType, 0);
            });
        },
        typeNextCharacter: function(textContainer, textToType, currentPosition) {
            var self = this;
            var typingDelay = 25;
            var repetitionDelay = 1500;
            var nextCharacter = textToType.charAt(currentPosition);
            var span = document.createElement("span");
            var spanClass = (currentPosition >= textToType.indexOf("Tech") && currentPosition < textToType.indexOf("Tech") + 4) ? "tech" : "";
            span.className = spanClass;
           span.textContent = nextCharacter;
           textContainer.appendChild(span);
            currentPosition++;
           if (currentPosition < textToType.length) {
                setTimeout(function () {
                  self.typeNextCharacter(textContainer, textToType, currentPosition);
                }, typingDelay);
           }
           else {
                setTimeout(function () {
                  self.repeatTyping(textContainer, textToType);
                }, repetitionDelay);
           }
        },
        repeatTyping: function(textContainer, textToType) {
            var self = this;
            textContainer.innerHTML = "";
            self.typeNextCharacter(textContainer, textToType, 0);
        },
    });
     return publicWidget.registry.refurb_carousel_snippet;
 });
