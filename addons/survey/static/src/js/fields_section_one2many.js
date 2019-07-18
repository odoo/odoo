odoo.define('survey.fields_section_one2many', function(require){
"use strict";

var Context = require('web.Context');
var FieldRegistry = require('web.field_registry');
var ListRenderer = require('web.ListRenderer');

var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

var SectionListRenderer = ListRenderer.extend({

    /**
     * @override
     * @private
     * Specific render for page question that models questions begin actually a page
     */
    _renderBodyCell: function (record, node, colIndex, options) {
        var $cell = this._super.apply(this, arguments);
        var isPage = record.data.is_mage === true;

        if (isPage) {
            if (node.attrs.widget === "handle") {
                return $cell;
            }
            else if (node.attrs.name === "title") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                $cell.attr('colspan', nbrColumns);
            }
            else {
                $cell.removeClass('o_invisible_modifier');
                return $cell.addClass('o_hidden');
            }
            // $cell.addClass('o_is_' + record.data.display_type);
        }
        return $cell;
    },

    /**
     * @override
     * @private
     */
    _renderRow: function(record, index){
        var $row = this._super.apply(this, arguments);
        if(record.data.display_type){
            $row.addClass('o_is_' + record.data.display_type);
        }
        return $row;
    },

    /**
     * @private
     */
    _onRowClicked: function(ev){
        console.log('_onRowClicked');
        if(ev.currentTarget.className.includes('line_section')){
            if(this.getParent().mode === "edit"){
                this.editable = "bottom";
            }else{
                delete this.editable;
            }
        }else{
            delete this.editable;
        }
        this._super.apply(this, arguments);
        if(this.getParent().mode === "edit"){
            this.editable = "bottom";
        }
    },

    /**
     * @override
     * @private
     */
    _onCellClick: function (ev) {
        console.log('_onCellClick');
        debugger
        if (this.getParent().mode == "edit" && ev.currentTarget.className.includes('line_section')){
            this.editable = "bottom";
        }
        else {
            delete this.editable;
            this.unselectRow();
        }
        this._super.apply(this, arguments);
    },
});

var SectionFieldOne2Many = FieldOne2Many.extend({
    /**
     * @override
     * @private
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionListRenderer;
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     * @private
     */
    _onAddRecord: function (ev) {
        var context_str = ev.data.context && ev.data.context[0];
        var context = new Context(context_str).eval();
        if (context.default_is_page) {
            this.editable = 'bottom';
        }
        else {
            delete this.editable;
        }
        this._super.apply(this, arguments);
    },
});

FieldRegistry.add('survey_section_one2many', SectionFieldOne2Many);
});
