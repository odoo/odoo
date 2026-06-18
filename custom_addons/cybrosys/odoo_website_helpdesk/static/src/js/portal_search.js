/** @odoo-module **/
import { rpc } from '@web/core/network/rpc';
import publicWidget from "@web/legacy/js/public/public_widget";
publicWidget.registry.TT = publicWidget.Widget.extend({
    selector: '#ticket',
    events: {
         'change #group_select': '_onGroupSelectChange',
        'click #search_ticket': '_onSubmit',
    },
//        GroupBy filtering the portal tickets
        _onGroupSelectChange: function (ev) {
            var self = this;
            var searchValue = this.$el.find('#group_select').val();
            rpc('/ticketgroupby', {
                'search_value': searchValue,
            }).then(function (result) {
                  $('.search_ticket').html(result);
            });
        },
//        Searching the portal tickets
    _onSubmit(ev) {
       var search_value = this.$el.find('#search_box').val();
       rpc('/ticketsearch', {
                'search_value': search_value,
            }).then(function(result) {
                $('.search_ticket').html(result);
            });
    }
})
