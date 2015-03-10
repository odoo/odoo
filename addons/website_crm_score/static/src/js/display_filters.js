odoo.define('website_crm_score.filters', ['web_kanban.common'], function (require) {
"use strict";

var common = require('web_kanban.common');


var Filters = common.AbstractField.extend({
    /**
        bnf grammar of a filter:
            <filter>    ::= <expr>
            <expr>      ::= <tuple> | '!' <expr> | <bin_op> <expr> <expr>
            <bin_op>    ::= '&' | '|'
            <tuple>     ::= '(' <field_name> ',' <operator> ',' <field_value> ')'
            <operator>  ::= '=' | '!=' | '<=' | '<' | '>' | '>=' | '=?' |
                            '=like' | '=ilike' | 'like' | 'not like' |
                            'ilike' | 'not ilike' | 'in' | 'not in' | 'child_of'
        some operators are negative
    */
    NEG_OP: ['!=', 'not like', 'not ilike', 'not in'],
    MAX_LEN: 5,
    start: function() {
        var val = this.field.raw_value;
        var self = this;
        if (val) {
            val = eval(val);
            if (val.length <= this.MAX_LEN) {
                var i = 0;
                while (i < val.length) {
                    var res = this.interpret(val, i);
                    i = res[0];
                    var $span = res[1];
                    // var $span = '<h2>' + res[1] + '</h2>';
                    self.$el.append($span);
                }
            }
            else {
                var $span = '<span class="oe_tag" style="background-color:#fce9e9;">Domain too big<span>';
                self.$el.append($span);
            }
        }
    },

    interpret: function(val, i) {
        var a = val[i];
        if(typeof a !== 'string'){
            // a is a tuple (field, op, value)
            var tag = a[0]; // field name
            var tip = a[2]; // field value
            if (this.NEG_OP.indexOf(a[1]) !== -1){
                // op in NEG_OP
                tip = 'not ' + tip;
            }
            var span = '<span class="oe_tag" title="' + tip + '">'+ tag +'</span>';
            return [i+1, span];
        }
        else if (a === '!'){
            var res = this.interpret(val, i+1);
            var span = '<span class="oe_tag">!</span>' + res[1];
            return [res[0], span];
        }
        else {
            // binary operator
            var res = this.binary_operator(val, i);
            return res;
        }
        return [i+1, ''];
    },

    binary_operator: function(val, i) {
        var resA = this.interpret(val, i+1);
        var resB = this.interpret(val, resA[0]);
        var label = '';
        var op = '';
        if (val[i] === '|') {
            label = 'label-success';
            op = ' or ';
        }
        else if (val[i] === '&') {
            label = 'label-primary';
            op = ' and ';
        }
        var span = resA[1] + resB[1];
        return [resB[0], span];
    }
});

common.registry.add('filters', Filters);

});
