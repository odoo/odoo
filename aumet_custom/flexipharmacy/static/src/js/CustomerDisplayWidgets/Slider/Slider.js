odoo.define('flexipharmacy.Slider', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    class Slider extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({activeIndex: 0,translate: 0,transition: 1});
        }
        mounted(){
            var self = this;
            setInterval(function() {
                self.nextSlide();
            }, 1000 * self.env.pos.config.image_interval);
        }
        nextSlide(){
            if (this.state.activeIndex === this.slides.length - 1) {
                this.state.transition = 0;
                this.state.translate =  0;
                this.state.activeIndex = 0;
                return;
            }
            this.state.transition = 1;
            this.state.activeIndex = this.state.activeIndex + 1;
            this.state.translate = this.state.activeIndex * this.width;
        }
        prevSlide(){
            if (this.state.activeIndex === 0) {
                this.state.translate =  (this.slides.length - 1) * this.width;
                this.state.activeIndex = this.slides.length - 1;
                return;
            }
            this.state.activeIndex = this.state.activeIndex - 1;
            this.state.translate = this.state.activeIndex * this.width;
        }
        get slides(){
            return this.env.pos.ad_data;
        }
        get width(){
            return this.props.width;
        }
        get totalWidth(){
            let a = this.width * this.slides.length;
            return a;
        }
    }
    Slider.template = 'Slider';

    Registries.Component.add(Slider);

    return Slider;
});
