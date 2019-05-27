odoo.define('survey.section_backend', function(require){
    "use strict";

    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var fieldRegistry = require('web.field_registry');
    var ListRenderer = require('web.ListRenderer');

    var SectionListRenderer = ListRenderer.extend({
        _renderBodyCell: function(record, node, index, options){
            var $cell = this._super.apply(this, arguments);

            var isSection = record.data.display_type === 'line_section';

            if(isSection){
                if(node.attrs.widget === "handle"){
                    return $cell;
                } else if(node.attrs.name === "title"){
                    var nbrColumns = this._getNumberOfCols();
                    if(this.handleField){
                        nbrColumns--;
                    }
                    if(this.addTrashIcon){
                        nbrColumns--;
                    }
                    $cell.attr('colspan', nbrColumns);
                } else {
                    $cell.removeClass('o_invisible_modifier');
                    return $cell.addClass('o_hidden');
                }
                $cell.addClass('o_is_' + record.data.display_type);
            }
            return $cell;
        },
        _renderRow: function(record, index){
            var $row = this._super.apply(this, arguments);
            if(record.data.display_type){
                $row.addClass('o_is_' + record.data.display_type);
            }
            return $row;
        },
        _renderView: function(){
            var def = this._super();
            this.$el.find('> table').addClass('o_section_list_view');
            return def;
        },
        _onRowClicked: function(ev){
            if(ev.currentTarget.className.includes('line_section')){
                if(this.__parentedParent.mode == "edit"){
                    this.editable = "bottom";
                }else{
                    delete this.editable;
                }
            }else{
                delete this.editable;
            }
            this._super.apply(this, arguments);
            if(this.__parentedParent.mode == "edit"){
                this.editable = "bottom";
            }
        },
        _onCellClick: function(ev){
            if(this.__parentedParent.mode == "edit" && ev.currentTarget.className.includes('line_section')){
                this.editable = "bottom";
            }else{
                delete this.editable;
                this.unselectRow();
            }
            this._super.apply(this, arguments);
        }
    });

    var SectionFieldOne2Many = FieldOne2Many.extend({
        _getRenderer: function(){
            if(this.view.arch.tag === 'tree'){
                return SectionListRenderer;
            }
            return this._super.apply(this, arguments);
        },
        _onAddRecord: function (ev) {
            var context = "";
            if(ev.data.context){
                context = ev.data.context[0];
            }
            if(context.includes('line_section')){
                this.editable = "bottom";
            }else{
                delete this.editable;
            }
            this._super.apply(this, arguments);
        },
    });

    fieldRegistry.add('section_one2many', SectionFieldOne2Many);
});