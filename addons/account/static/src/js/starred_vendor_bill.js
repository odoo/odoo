odoo.define('account.StarredVendorBillMany2One', function (require) {
    "use strict";

    var FieldMany2One = require('web.relational_fields').FieldMany2One;
    var core = require('web.core');
    const registry = require('web.field_registry');
    
    var _t = core._t;
    
    /**
     * This widget adds a star next to bill names in the "Auto-Complete" field dropdown.
     * A full star means that the bill is set as "starred_vendor_bill" on selected Vendor.
     * Bills can be set/unset as starred_vendor_bill by clicking on the stars.
     * No stars are displayed if no vendor is selected.
     */
    
    var StarredVendorBillMany2One = FieldMany2One.extend({
        resetOnAnyFieldChange: true,
        // make sure the starred bill is always shown in list
        _search: async function (searchValue = "") {
            var results = await this._super.apply(this, arguments);
            if(this._starredBillData && this._starredBillData.is_not_from_parent)
            {
                var index = results.findIndex(item => item.id == this._starredBillData.id);
                if(index > 0)
                {
                    // move starred bill item to top
                    results.splice(0, 0, results.splice(index, 1)[0]);
                }
                else if (index == -1)
                {
                    // add starred bill item on top
                    if(results.length > this.limit) 
                        results.splice(this.limit-1, 0, results.splice(results.length-1, 1)[0]); // keep "search more ...". item
                    results.length = this.limit;
                    results.unshift({
                        id:this._starredBillData.id,
                        label:this._starredBillData.name,
                        value:this._starredBillData.name,
                        name:this._starredBillData.name,
                    });
                }
            }
            return results;
        },
        _modifyAutocompleteRendering: function (){
            var api = this.$input.data('ui-autocomplete');
            if(api._superRenderEdit)
                return;
            api._superRenderEdit = api._renderItem;
            var self = this;
            // add star to dropdown item
            api._renderItem = function(ul,item) {
                if(item == null)
                    return [];
                var result = api._superRenderEdit(ul,item);
                if(self.recordData.partner_id && item.id)
                {
                    var star = $('<span/>').addClass('o_bill_star fa fa-star' + (self._starredBillData.id == item.id ? '' : '-o'));
                    star.on('click', self._onUIMenuItemStarClick.bind(self));
                    star.data('partnerId',self.recordData.partner_id.data.id);
                    star.data('billId',item.id);
                    star.data('billName',item.name);
                    result.find('a').append(star);
    
                    if(self._starredBillData.id == item.id)
                        self._selectedStarElement = star
                }
                return result;
            }
        },
        _renderEdit: function (){
            this._super.apply(this, arguments);
            self = this;
            if(this.recordData.partner_id)
            {
                this._rpc({
                    model: 'res.partner',
                    method: 'get_starred_bill_data',
                    args: [this.recordData.partner_id.data.id]
                }).then(function(res){
                    self._selectedStarElement = null;
                    self._starredBillData = res;
                    self._modifyAutocompleteRendering();
                    console.log('get_starred_bill_data',res);
                });
            }   
        },
        _onUIMenuItemStarClick: function(event){
            event.stopPropagation();
            var target = $(event.target);
            var newBillId = (target.data('billId') == this._starredBillData.id ? null : target.data('billId'));
            var newBillName = (target.data('billId') == this._starredBillData.id ? null : target.data('billName'));
            var self = this;
            this._rpc({
                model:'res.partner',
                method:'write',
                args: [target.data('partnerId'), {starred_vendor_bill:newBillId}],
            }).then(function(rslt) {
                self._starredBillData = {
                    "id":newBillId,
                    "name":newBillName
                }
                if(self._selectedStarElement)
                    self._selectedStarElement.attr("class","o_bill_star fa fa-star-o");
                target.attr("class","o_bill_star fa fa-star" + (target.data('billId') == newBillId ? '' : '-o'));
                self._selectedStarElement = (target.data('billId') == newBillId ? target : null);
            })
        },
    });
    
    registry.add('starred_vendor_bill_widget', StarredVendorBillMany2One);
    return StarredVendorBillMany2One;
    
});
