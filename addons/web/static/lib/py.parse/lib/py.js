var py = {};
(function (exports) {
    var NUMBER = /^\d$/,
        NAME_FIRST = /^[a-zA-Z_]$/,
        NAME = /^[a-zA-Z0-9_]$/;

    var create = function (o, props) {
        function F() {};
        F.prototype = o;
        var inst = new F;
        for(var name in props) {
            if(!props.hasOwnProperty(name)) { continue; }
            inst[name] = props[name];
        }
        return inst;
    }

    var symbols = {};
    var comparators = {};
    var Base = {
        nud: function () { throw new Error(this.id + " undefined as prefix"); },
        led: function (led) { throw new Error(this.id + " undefined as infix"); },
        toString: function () {
            if (this.id === '(constant)' || this.id === '(number)' || this.id === '(name)' || this.id === '(string)') {
                return [this.id.slice(0, this.id.length-1), ' ', this.value, ')'].join('');
            } else if (this.id === '(end)') {
                return '(end)';
            } else if (this.id === '(comparator)' ) {
                var out = ['(comparator', this.expressions[0]];
                for (var i=0;i<this.operators.length; ++i) {
                    out.push(this.operators[i], this.expressions[i+1]);
                }
                return out.join(' ') + ')';
            }
            var out = [this.id, this.first, this.second, this.third]
                .filter(function (r){return r}).join(' ');
            return '(' + out + ')';
        }
    }
    function symbol(id, bp) {
        bp = bp || 0;
        var s = symbols[id];
        if (s) {
            if (bp > s.lbp) {
                s.lbp = bp;
            }
            return s;
        }
        return symbols[id] = create(Base, {
            id: id,
            lbp: bp
        });
    }
    function constant(id) {
        symbol(id).nud = function () {
            this.id = "(constant)";
            this.value = id;
            return this;
        };
    };
    function prefix(id, bp, nud) {
        symbol(id).nud = nud || function () {
            this.first = expression(bp);
            return this
        }
    }
    function infix(id, bp, led) {
        symbol(id, bp).led = led || function (left) {
            this.first = left;
            this.second = expression(bp);
            return this;
        }
    }
    function infixr(id, bp) {
        symbol(id, bp).led = function (left) {
            this.first = left;
            this.second = expression(bp - 1);
            return this;
        }
    }
    function comparator(id) {
        comparators[id] = true;
        var bp = 60;
        infix(id, bp, function (left) {
            this.id = '(comparator)';
            this.operators = [id];
            this.expressions = [left, expression(bp)];
            while (token.id in comparators) {
                this.operators.push(token.id);
                advance();
                this.expressions.push(
                    expression(bp));
            }
            return this;
        });
    }

    constant('None'); constant('False'); constant('True');

    symbol('(number)').nud = function () { return this; };
    symbol('(name)').nud = function () { return this; };
    symbol('(string)').nud = function () { return this; };
    symbol('(end)');

    symbol(':'); symbol(')'); symbol(']'); symbol('}'); symbol(',');
    symbol('else');

    symbol('lambda', 20).nud = function () {
        this.first = [];
        if (token.id !== ':') {
            for(;;) {
                if (token.id !== '(name)') {
                    throw new Error('Excepted an argument name');
                }
                this.first.push(token);
                advance();
                if (token.id !== ',') {
                    break;
                }
                advance(',');
            }
        }
        advance(':');
        this.second = expression();
        return this;
    };
    infix('if', 20, function (left) {
        this.first = left;
        this.second = expression();
        advance('else');
        this.third = expression();
        return this;
    });

    infixr('or', 30); infixr('and', 40); prefix('not', 50);

    comparator('in'); comparator('not in');
    comparator('is'); comparator('is not');
    comparator('<'); comparator('<=');
    comparator('>'); comparator('>=');
    comparator('<>'); comparator('!='); comparator('==');

    infix('|', 70); infix('^', 80), infix('&', 90);

    infix('<<', 100); infix('>>', 100);

    infix('+', 110); infix('-', 110);

    infix('*', 120); infix('/', 120);
    infix('//', 120), infix('%', 120);

    prefix('-', 130); prefix('+', 130); prefix('~', 130)

    infixr('**', 140);

    infix('.', 150, function (left) {
        if (token.id !== '(name)') {
            throw new Error('Expected attribute name, got ', token.id);
        }
        this.first = left;
        this.second = token;
        advance();
        return this;
    });
    symbol('(', 150).nud = function () {
        this.first = [];
        var comma = false;
        if (token.id !== ')') {
            while (true) {
                if (token.id === ')') {
                    break;
                }
                this.first.push(expression())
                if (token.id !== ',') {
                    break;
                }
                comma = true;
                advance(',');
            }
        }
        advance(')');
        if (!this.first.length || comma) {
            return this;
        } else {
            return this.first[0];
        }
    };
    symbol('(').led = function (left) {
        this.first = left;
        this.second = [];
        if (token.id !== ")") {
            for(;;) {
                this.second.push(expression());
                if (token.id !== ',') {
                    break;
                }
                advance(',');
            }
        }
        advance(")");
        return this;

    };
    infix('[', 150, function (left) {
        this.first = left
        this.second = expression()
        advance("]")
        return this;
    })
    symbol('[').nud = function () {
        this.first = [];
        if (token.id !== ']') {
            for (;;) {
                if (token.id === ']') {
                    break;
                }
                this.first.push(expression());
                if (token.id !== ',') {
                    break;
                }
                advance(',');
            }
        }
        advance(']');
        return this;
    };

    symbol('{').nud = function () {
        this.first = [];
        if (token.id !== '}') {
            for(;;) {
                if (token.id === '}') {
                    break;
                }
                var key = expression();
                advance(':');
                var value = expression();
                this.first.push([key, value]);
                if (token.id !== ',') {
                    break;
                }
                advance(',');
            }
        }
        advance('}');
        return this;
    };

    var longops = {
        '*': ['*'],
        '<': ['<', '=', '>'],
        '>': ['=', '>'],
        '!': ['='],
        '=': ['='],
        '/': ['/']
    }
    function Tokenizer(str) {
        this.states = ['initial'];
        this.tokens = [];
    }
    Tokenizer.prototype = {
        builder: function (empty) {
            var key = this.states[0] + '_builder';
            if (empty) {
                var value = this[key];
                delete this[key];
                return value;
            } else {
                return this[key] = this[key] || [];
            }
        },
        simple: function (type) {
            this.tokens.push({type: type});
        },
        push: function (new_state) {
            this.states.push(new_state);
        },
        pop: function () {
            this.states.pop();
        },

        feed: function (str, index) {
            var s = this.states;
            return this[s[s.length - 1]](str, index);
        },

        initial: function (str, index) {
            var character = str[index];

            if (character in longops) {
                var follow = longops[character];
                for(var i=0, len=follow.length; i<len; ++i) {
                    if (str[index+1] === follow[i]) {
                        character += follow[i];
                        index++;
                        break;
                    }
                }
            }

            if (character === ' ') {
                return index+1;
            } else if (character === '\0') {
                this.tokens.push(symbols['(end)']);
                return index + 1
            } else if (character === '"' || character === "'") {
                this.push('string');
                return index + 1;
            } else if (NUMBER.test(character)) {
                this.push('number');
                return index;
            } else if (NAME_FIRST.test(character)) {
                this.push('name');
                return index;
            } else if (character in symbols) {
                this.tokens.push(create(symbols[character]));
                return index + 1;
            }
            throw new Error("Tokenizing failure of <<" + str + ">> at index " + index
                            + ", character [[" + character + "]]"
                            + "; parsed so far: " + this.tokens);
        },
        string: function (str, index) {
            var character = str[index];
            if (character === '"' || character === "'") {
                this.tokens.push(create(symbols['(string)'], {
                    value: this.builder(true).join('')
                }));
                this.pop();
                return index + 1;
            }
            this.builder().push(character);
            return index + 1;
        },
        number: function (str, index) {
            var character = str[index];
            if (!NUMBER.test(character)) {
                this.tokens.push(create(symbols['(number)'], {
                    value: parseFloat(this.builder(true).join(''))
                }));
                this.pop();
                return index;
            }
            this.builder().push(character);
            return index + 1;
        },
        name: function (str, index) {
            var character = str[index];
            if (!NAME.test(character)) {
                var name = this.builder(true).join('');
                var symbol = symbols[name];
                if (symbol) {
                    if (name === 'in' && this.tokens[this.tokens.length-1].id === 'not') {
                        symbol = symbols['not in'];
                        this.tokens.pop();
                    } else if (name === 'not' && this.tokens[this.tokens.length-1].id === 'is') {
                        symbol = symbols['is not'];
                        this.tokens.pop();
                    }
                    this.tokens.push(create(symbol));
                } else {
                    this.tokens.push(create(symbols['(name)'], {
                        value: name
                    }));
                }
                this.pop();
                return index;
            }
            this.builder().push(character);
            return index + 1;
        }
    }

    exports.tokenize = function tokenize(str) {
        var index = 0,
            str = str + '\0',
            tokenizer = new Tokenizer(str);
        do {
            index = tokenizer.feed(str, index);
        } while (index !== str.length)
        return tokenizer.tokens;
    }

    var token, next;
    function expression(rbp) {
        rbp = rbp || 0;
        var t = token;
        token = next();
        var left = t.nud();
        while (rbp < token.lbp) {
            t = token;
            token = next();
            left = t.led(left);
        }
        return left;
    }
    function advance(id) {
        if (id && token.id !== id) {
            throw new Error(
                'Expected "' + id + '", got "' + token.id + '"');
        }
        token = next();
    }

    exports.object = create({}, {});
    exports.tuple = create(exports.object, {
        __contains__: function (value) {
            for(var i=0, len=this.values.length; i<len; ++i) {
                if (this.values[i] === value) {
                    return true;
                }
            }
            return false;
        }
    });

    exports.parse = function (toks) {
        var index = 0;
        token = toks[0];
        next = function () { return toks[++index]; };
        return expression();
    };
    evaluate_operator = function (operator, a, b) {
        switch (operator) {
        case '==': case 'is': return a === b;
        case '!=': case 'is not': return a !== b;
        case '<': return a < b;
        case '<=': return a <= b;
        case '>': return a > b;
        case '>=': return a >= b;
        case 'in': return b.__contains__(a);
        case 'not in': return !b.__contains__(a);
        }
        throw new Error('SyntaxError: unknown comparator [[' + operator + ']]');
    }
    exports.evaluate = function (expr, context) {
        switch (expr.id) {
        case '(name)':
            var val = context[expr.value];
            if (val === undefined) {
                throw new Error("NameError: name '" + expr.value + "' is not defined");
            }
            return val;
        case '(string)':
        case '(number)':
            return expr.value;
        case '(comparator)':
            var result, left = exports.evaluate(expr.expressions[0], context);
            for(var i=0; i<expr.operators.length; ++i) {
                result = evaluate_operator(
                    expr.operators[i],
                    left,
                    left = exports.evaluate(expr.expressions[i+1], context));
                if (!result) { return false; }
            }
            return true;
        case '-':
            if (this.second) {
                throw new Error('SyntaxError: binary [-] not implemented yet');
            }
            return -(exports.evaluate(expr.first, context));
        case 'and':
            return (exports.evaluate(expr.first, context)
                    && exports.evaluate(expr.second, context));
        case 'or':
            return (exports.evaluate(expr.first, context)
                    || exports.evaluate(expr.second, context));
        case '(':
            if (this.second) {
                throw new Error('SyntaxError: functions not implemented yet');
            }
            var tuple_exprs = expr.first,
                tuple_values = [];
            for (var i=0, len=tuple_exprs.length; i<len; ++i) {
                tuple_values.push(exports.evaluate(
                    tuple_exprs[i], context));
            }
            return create(exports.tuple, {values: tuple_values});
        default:
            throw new Error('SyntaxError: Unknown node [[' + expr.id + ']]');
        }
    };
    exports.eval = function (str, context) {
        return exports.evaluate(
            exports.parse(
                exports.tokenize(
                    str)),
            context);;
    }
})(typeof exports === 'undefined' ? py : exports)
