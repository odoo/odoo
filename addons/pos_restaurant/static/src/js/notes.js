odoo.define('pos_restaurant.notes', function (require) {
"use strict";

var { Orderline } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosResNotesOrderline = (Orderline) => class PosResNotesOrderline extends Orderline {
    constructor() {
        super(...arguments);
        this.note = this.note || "";
    }
    set_note(note){
        this.note = note;
    }
    get_note(note){
        return this.note;
    }
    can_be_merged_with(orderline) {
        if (orderline.get_note() !== this.get_note()) {
            return false;
        } else {
            return super.can_be_merged_with(...arguments);
        }
    }
    clone(){
        var orderline = super.clone(...arguments);
        orderline.note = this.note;
        return orderline;
    }
    export_as_JSON(){
        var json = super.export_as_JSON(...arguments);
        json.note = this.note;
        return json;
    }
    init_from_JSON(json){
        super.init_from_JSON(...arguments);
        this.note = json.note;
    }
}
Registries.Model.extend(Orderline, PosResNotesOrderline);

});
