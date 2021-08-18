odoo.define('flexipharmacy.Ratings', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class Ratings extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('mouse-over', this._selectStar)
            useListener('mouse-out', this._setRating)
            useListener('click-star', this._clickStar)
        }
        _selectStar(event){
            const stars = event.target.getElementsByClassName('star');
            const hoverValue = event.detail.value;
            Array.from(stars).forEach(star => {
              star.style.color = hoverValue >= star.getAttribute('value') ? '#ffc107' : '';
            });
        }
        _setRating(event){
            const stars = event.target.getElementsByClassName('star');
            Array.from(stars).forEach(star => {
              star.style.color =
                this.props.currentRating >= star.getAttribute('value') ? '#ffc107' : '';
            });
        }
        _clickStar(event){
            this.trigger('change-ratings',{'value': event.detail.value})
        }
    }
    Ratings.template = 'Ratings';

    Registries.Component.add(Ratings);

    return Ratings;
});
