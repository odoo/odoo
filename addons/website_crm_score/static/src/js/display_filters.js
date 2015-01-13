openerp.website_crm_score = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.website_crm_score = {};

    instance.website_crm_score.filters = instance.web_kanban.AbstractField.extend({
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
                // var span = '<span class="label label-info" title="' + tip + '">'+ tag +'</span>';
                return [i+1, span];
            }
            else if (a === '!'){
                var res = this.interpret(val, i+1);
                // var span = '<span class="label label-danger">' + res[1] + '</span>';
                var span = '<span class="oe_tag">!</span>' + res[1];
                // var span = '<span class="label label-danger" style="border-style: solid; border-width: 1px; border-color: #666;">' + res[1] + '</span>';
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
            // var span = '<span class="label ' + label + '"">' + resA[1] + ' ' + resB[1] + '</span>';
            var span = resA[1] + resB[1];
            return [resB[0], span];
        }
    });

    instance.web_kanban.fields_registry.add('filters', 'instance.website_crm_score.filters');

    instance.website_crm_score.smart_filters = instance.web_kanban.AbstractField.extend({
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

            the widget works in 3 steps (all 3 are recursive):
                - parse the filter and generate a tree
                - flatten the tree to a certain point
                - format the tree so that it can be displayed

            - parsing:
                done by interpret()
                the general representation are lists with list[0] a marker and list[1:] being arguments
                a tuple is represented as ['d', tip, tag]
                    tag being the field name
                    tip being the field value
                    note: a negative statement is cast into a negation as described below
                        eg: [(field, '!=', value)] = ['not', ['d', tag, tip]]
                a negation is represented as ['not', elem]
                    elem being a list (eg : ['d', tip, tag], ['not', elem], ...)
                a binary operation (or/and) is represented as ['or/and', elem1, elem2]
                    elem1 and elem2 are the operands of the or/and
                example: 
                    - ['&', ['|', ['d',..], ['d',..] ], ['d',..] ] = ['&', '|', d1, d2, d3]

            - flattening:
                done by flatten()
                if similar operations are successive, then the lists are flatten
                exemple:
                    - ['&', ['&', d1, d2], d3 ] = ['&', d1, d2, d3]
                    - ['not', ['not', d1]] = d1

            - formatting
                done by format_domain()
                the list somehow represents a tree due to its format ([marker, args..])
                browses a list/tree and returns an html representation
                this is fairly simple as it only needs to match the marker and act accordinly
        */

        NEG_OP: ['!=', 'not like', 'not ilike', 'not in'],
        MAX_LEN: 10,
        start: function() {
            var val = this.field.raw_value;
            var self = this;
            if (val) {
                val = eval(val);
                if (val.length <= this.MAX_LEN) {
                    var i = 0;
                    while (i < val.length) {
                        var res = this.interpret(val, i);
                        // the returned index i is the index of the first elem not parsed yet in val
                        i = res[0];
                        var flat = this.flatten(res[1]);
                        var form = this.format_domain(flat);
                        var $span = form;
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
            // returns the index of the next element to parse and the representation of the parsed element
            var a = val[i];
            if(typeof a !== 'string'){
                // a is a tuple (field, op, value)
                var tag = a[0]; // field name
                var tip = a[2]; // field value
                var span = ['d', tip, tag];
                if (this.NEG_OP.indexOf(a[1]) !== -1){
                    // op in NEG_OP
                    span = ['not', span];
                }
                return [i+1, span];
            }
            else if (a === '!'){
                var res = this.interpret(val, i+1);
                var span = ['not', res[1]];
                return [res[0], span];
            }
            else {
                // binary operator ( | or & )
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
                op = 'or';
            }
            else if (val[i] === '&') {
                label = 'label-primary';
                op = 'and';
            }
            var span = [op, resA[1], resB[1]];
            return [resB[0], span];
        },

        flatten: function(t) {
            /**
            Python code (which is easier to read and understand):
                /!\ in the following code, a domain is a string in dom instead of an array ['d', tag, tip] like in js
                        it explains the differences but the logic is the same
            def flatten(t):
                op = t[0]
                for c in t[1:]:
                    if not c in dom:
                        fc = flatten(c)
                        t.remove(c)
                        if fc[0] == op:
                            if op == 'not':
                                t = fc[1]
                            else:
                                t.extend(fc[1:])
                        else:
                            t.append(fc)
                return t
            */
            var self = this;
            var op = t[0];
            if (op != 'd') {
                var ts = t.slice(1);
                _.each(ts, function(c) {
                    if (c[0] != 'd') {
                        var fc = self.flatten(c);
                        var idx = t.indexOf(c);
                        t.splice(idx, 1);
                        if (fc[0] == op) {
                            if (op == 'not') {
                                t = fc[1];
                            }
                            else {
                                t.push.apply(t,fc.slice(1));
                            }
                        }
                        else {
                            t.push(fc);
                        }
                    }
                });
            }
            return t;
        },

        format_domain: function(a) {
            var self = this;
            var style = 'padding:1px; border-style: solid; border-width:1px; border-color=black; text-align:center; border-radius: 4px;';
            if (a[0] == 'd'){
                /** format here what a domain should look like
                        a[1] : tip
                        a[2] : tag
                */
                var span = '<span class="oe_tag" title="' + a[1] + '">'+ a[2] +'</span>';
                return span;
            }
            else if (a[0] == 'not') {
                var res = this.format_domain(a[1]);
                /** format here what a negation should look like
                        res is the expression that is negated
                */
                var color = '#d66';
                var span = '<div style="background-color:' + color + '; ' + style + '">' + res + '</div>';
                return span;
            }
            else if (a[0] == 'and' || a[0] == 'or') {
                var label = '';
                var color = '';
                /** format here what an or/and shoud look like
                        as there can be more than 2 operands, it is needed to loop over a[1:]
                */
                if (a[0] == 'or') {
                    color = '#5c5';
                    // label = 'label-success';
                }
                else if (a[0] == 'and') {
                    color = '#77e';
                    // label = 'label-primary';
                }
                var span = '<div style="background-color:' + color + '; ' + style + '">';
                var as = a.slice(1);
                _.each(as, function(s) {
                    var res = self.format_domain(s);
                    span += res;
                });
                span += '</div>';
                return span;
            }
        },

    });

    instance.web_kanban.fields_registry.add('smart_filters', 'instance.website_crm_score.smart_filters');
}
