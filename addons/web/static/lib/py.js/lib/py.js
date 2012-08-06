var py = {};
(function (py) {
    var create = function (o, props) {
        function F() {}
        F.prototype = o;
        var inst = new F;
        if (props) {
            for(var name in props) {
                if(!props.hasOwnProperty(name)) { continue; }
                inst[name] = props[name];
            }
        }
        return inst;
    };

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
                var repr = ['(comparator', this.expressions[0]];
                for (var i=0;i<this.operators.length; ++i) {
                    repr.push(this.operators[i], this.expressions[i+1]);
                }
                return repr.join(' ') + ')';
            }
            var out = [this.id, this.first, this.second, this.third]
                .filter(function (r){return r}).join(' ');
            return '(' + out + ')';
        }
    };
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
        var s = symbol(id);
        s.id = '(constant)';
        s.value = id;
        s.nud = function () {
            return this;
        };
    }
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

    infix('=', 10, function (left) {
        if (left.id !== '(name)') {
            throw new Error("Expected keyword argument name, got " + token.id);
        }
        this.first = left;
        this.second = expression();
        return this;
    });

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

    prefix('-', 130); prefix('+', 130); prefix('~', 130);

    infixr('**', 140);

    infix('.', 150, function (left) {
        if (token.id !== '(name)') {
            throw new Error('Expected attribute name, got ' + token.id);
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
                this.first.push(expression());
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
        this.first = left;
        this.second = expression();
        advance("]");
        return this;
    });
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

    py.tokenize = (function () {
        function group() { return '(' + Array.prototype.join.call(arguments, '|') + ')'; }

        var Whitespace = '[ \\f\\t]*';

        var Name = '[a-zA-Z_]\\w*';

        var DecNumber = '\\d+';
        var IntNumber = DecNumber;
        var PointFloat = group('\\d+\\.\\d*', '\\.\\d+');
        var FloatNumber = PointFloat;
        var Number = group(FloatNumber, IntNumber);

        var Operator = group("\\*\\*=?", ">>=?", "<<=?", "<>", "!=",
                             "//=?", "[+\\-*/%&|^=<>]=?", "~");
        var Bracket = '[\\[\\]\\(\\)\\{\\}]';
        var Special = '[:;.,`@]';
        var Funny = group(Operator, Bracket, Special);

        var ContStr = group("'[^']*'", '"[^"]*"');

        var PseudoToken = Whitespace + group(Number, Funny, ContStr, Name);

        return function tokenize(s) {
            var max=s.length, tokens = [];
            // /g flag makes repeated exec() have memory
            var pseudoprog = new RegExp(PseudoToken, 'g');

            while(pseudoprog.lastIndex < max) {
                var pseudomatch = pseudoprog.exec(s);
                if (!pseudomatch) {
                    // if match failed on trailing whitespace, end tokenizing
                    if (/^\s+$/.test(s.slice(end))) {
                        break;
                    }
                    throw new Error('Failed to tokenize <<' + s
                                    + '>> at index ' + (end || 0)
                                    + '; parsed so far: ' + tokens);
                }

                var start = pseudomatch.index, end = pseudoprog.lastIndex;
                // strip leading space caught by Whitespace
                var token = s.slice(start, end).replace(new RegExp('^' + Whitespace), '');
                var initial = token[0];

                if (/\d/.test(initial) || (initial === '.' && token !== '.')) {
                    tokens.push(create(symbols['(number)'], {
                        value: parseFloat(token)
                    }));
                } else if (/'|"/.test(initial)) {
                    tokens.push(create(symbols['(string)'], {
                        value: token.slice(1, -1)
                    }));
                } else if (token in symbols) {
                    var symbol;
                    // transform 'not in' and 'is not' in a single token
                    if (token === 'in' && tokens[tokens.length-1].id === 'not') {
                        symbol = symbols['not in'];
                        tokens.pop();
                    } else if (token === 'not' && tokens[tokens.length-1].id === 'is') {
                        symbol = symbols['is not'];
                        tokens.pop();
                    } else {
                        symbol = symbols[token];
                    }
                    tokens.push(create(symbol));
                } else if (/[_a-zA-Z]/.test(initial)) {
                    tokens.push(create(symbols['(name)'], {
                        value: token
                    }));
                } else {
                     throw new Error("Tokenizing failure of <<" + s + ">> at index " + start
                                     + " for token [[" + token + "]]"
                                     + "; parsed so far: " + tokens);

                }
            }
            tokens.push(create(symbols['(end)']));
            return tokens;
        }
    })();

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

    function PY_ensurepy(val, name) {
        switch (val) {
        case undefined:
            throw new Error("NameError: name '" + name + "' is not defined");
        case null:
            return py.None;
        case true:
            return py.True;
        case false:
            return py.False;
        }

        if (val instanceof py.object
            || val === py.object
            || py.issubclass.__call__([val, py.object]) === py.True) {
            return val;
        }

        switch (typeof val) {
        case 'number':
            return new py.float(val);
        case 'string':
            return new py.str(val);
        case 'function':
            return new py.def(val);
        }

        switch(val.constructor) {
        case Object:
            var o = new py.object();
            for (var prop in val) {
                if (val.hasOwnProperty(prop)) {
                    o[prop] = val[prop];
                }
            }
            return o;
        case Array:
            var a = new py.list();
            a.values = val;
            return a;
        }

        throw new Error("Could not convert " + val + " to a pyval");
    }
    // Builtins
    py.type = function type(constructor, base, dict) {
        var proto;
        if (!base) {
            base = py.object;
        }
        proto = constructor.prototype = create(base.prototype);
        proto.constructor = constructor;
        if (dict) {
            for(var k in dict) {
                if (!dict.hasOwnProperty(k)) { continue; }
                proto[k] = dict[k];
            }
        }
        constructor.__call__ = function () {
            // create equivalent type with same prototype
            var instance = create(proto);
            // call actual constructor
            var res = constructor.apply(instance, arguments);
            // return result of constructor if any, otherwise instance
            return res || instance;
        };
        return constructor;
    };

    var hash_counter = 0;
    py.object = py.type(function object() {}, {}, {
        // Basic customization
        __hash__: function () {
            if (this._hash) {
                return this._hash;
            }
            // tagged counter, to avoid collisions with e.g. number hashes
            return this._hash = '\0\0\0' + String(hash_counter++);
        },
        __eq__: function (other) {
            return (this === other) ? py.True : py.False;
        },
        __ne__: function (other) {
            if (this.__eq__(other) === py.True) {
                return py.False;
            } else {
                return py.True;
            }
        },
        __lt__: function () { return py.NotImplemented; },
        __le__: function () { return py.NotImplemented; },
        __ge__: function () { return py.NotImplemented; },
        __gt__: function () { return py.NotImplemented; },
        __str__: function () {
            return this.__unicode__();
        },
        __unicode__: function () {
            // TODO: return python string
            return '<object ' + this.constructor.name + '>';
        },
        __nonzero__: function () {
            return py.True;
        },
        // Attribute access
        __getattribute__: function (name) {
            if (name in this) {
                var val = this[name];
                if (typeof val === 'object' && '__get__' in val) {
                    // TODO: second argument should be class
                    return val.__get__(this);
                }
                if (typeof val === 'function' && !this.hasOwnProperty(name)) {
                    // val is a method from the class
                    return new PY_instancemethod(val, this);
                }
                return PY_ensurepy(val);
            }
            if ('__getattr__' in this) {
                return this.__getattr__(name);
            }
            throw new Error("AttributeError: object has no attribute '" + name +"'");
        },
        __setattr__: function (name, value) {
            if (name in this && '__set__' in this[name]) {
                this[name].__set__(this, value);
            }
            this[name] = value;
        },
        // no delattr, because no 'del' statement

        // Conversion
        toJSON: function () {
            throw new Error(this.constructor.name + ' can not be converted to JSON');
        }
    });
    var NoneType = py.type(function NoneType() {}, py.object, {
        __nonzero__: function () { return py.False; },
        toJSON: function () { return null; }
    });
    py.None = new NoneType();
    var NotImplementedType = py.type(function NotImplementedType(){});
    py.NotImplemented = new NotImplementedType();
    var booleans_initialized = false;
    py.bool = py.type(function bool(value) {
        value = (value instanceof Array) ? value[0] : value;
        // The only actual instance of py.bool should be py.True
        // and py.False. Return the new instance of py.bool if we
        // are initializing py.True and py.False, otherwise always
        // return either py.True or py.False.
        if (!booleans_initialized) {
            return;
        }
        if (value === undefined) { return py.False; }
        return value.__nonzero__() === py.True ? py.True : py.False;
    }, py.object, {
        __nonzero__: function () { return this; },
        toJSON: function () { return this === py.True; }
    });
    py.True = new py.bool();
    py.False = new py.bool();
    booleans_initialized = true;
    py.float = py.type(function float(value) {
        value = (value instanceof Array) ? value[0] : value;
        if (value === undefined) { this._value = 0; return; }
        if (value instanceof py.float) { return value; }
        if (typeof value === 'number' || value instanceof Number) {
            this._value = value;
            return;
        }
        if (typeof value === 'string' || value instanceof String) {
            this._value = parseFloat(value);
            return;
        }
        if (value instanceof py.object && '__float__' in value) {
            var res = value.__float__();
            if (res instanceof py.float) {
                return res;
            }
            throw new Error('TypeError: __float__ returned non-float (type ' +
                            res.constructor.name + ')');
        }
        throw new Error('TypeError: float() argument must be a string or a number');
    }, py.object, {
        __eq__: function (other) {
            return this._value === other._value ? py.True : py.False;
        },
        __lt__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return this._value < other._value ? py.True : py.False;
        },
        __le__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return this._value <= other._value ? py.True : py.False;
        },
        __gt__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return this._value > other._value ? py.True : py.False;
        },
        __ge__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return this._value >= other._value ? py.True : py.False;
        },
        __add__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return new py.float(this._value + other._value);
        },
        __neg__: function () {
            return new py.float(-this._value);
        },
        __sub__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return new py.float(this._value - other._value);
        },
        __mul__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return new py.float(this._value * other._value);
        },
        __div__: function (other) {
            if (!(other instanceof py.float)) { return py.NotImplemented; }
            return new py.float(this._value / other._value);
        },
        __nonzero__: function () {
            return this._value ? py.True : py.False;
        },
        toJSON: function () {
            return this._value;
        }
    });
    py.str = py.type(function str(s) {
        s = (s instanceof Array) ? s[0] : s;
        if (s === undefined) { this._value = ''; return; }
        if (s instanceof py.str) { return s; }
        if (typeof s === 'string' || s instanceof String) {
            this._value = s;
            return;
        }
        var v = s.__str__();
        if (v instanceof py.str) { return v; }
        throw new Error('TypeError: __str__ returned non-string (type ' +
                        v.constructor.name + ')');
    }, py.object, {
        __hash__: function () {
            return '\1\0\1' + this._value;
        },
        __eq__: function (other) {
            if (other instanceof py.str && this._value === other._value) {
                return py.True;
            }
            return py.False;
        },
        __lt__: function (other) {
            if (!(other instanceof py.str)) { return py.NotImplemented; }
            return this._value < other._value ? py.True : py.False;
        },
        __le__: function (other) {
            if (!(other instanceof py.str)) { return py.NotImplemented; }
            return this._value <= other._value ? py.True : py.False;
        },
        __gt__: function (other) {
            if (!(other instanceof py.str)) { return py.NotImplemented; }
            return this._value > other._value ? py.True : py.False;
        },
        __ge__: function (other) {
            if (!(other instanceof py.str)) { return py.NotImplemented; }
            return this._value >= other._value ? py.True : py.False;
        },
        __add__: function (other) {
            if (!(other instanceof py.str)) { return py.NotImplemented; }
            return new py.str(this._value + other._value);
        },
        __nonzero__: function () {
            return this._value.length ? py.True : py.False;
        },
        __contains__: function (s) {
            return (this._value.indexOf(s._value) !== -1) ? py.True : py.False;
        },
        toJSON: function () {
            return this._value;
        }
    });
    py.tuple = py.type(function tuple() {}, null, {
        __contains__: function (value) {
            for(var i=0, len=this.values.length; i<len; ++i) {
                if (this.values[i].__eq__(value) === py.True) {
                    return py.True;
                }
            }
            return py.False;
        },
        __getitem__: function (index) {
            return PY_ensurepy(this.values[index.toJSON()]);
        },
        toJSON: function () {
            var out = [];
            for (var i=0; i<this.values.length; ++i) {
                out.push(this.values[i].toJSON());
            }
            return out;
        }
    });
    py.list = py.tuple;
    py.dict = py.type(function dict(d) {
        this._store = {};
        for (var k in (d || {})) {
            if (!d.hasOwnProperty(k)) { continue; }
            var py_k = new py.str(k);
            var val = PY_ensurepy(d[k]);
            this._store[py_k.__hash__()] = [py_k, val];
        }
    }, py.object, {
        __getitem__: function (key) {
            var h = key.__hash__();
            if (!(h in this._store)) {
                throw new Error("KeyError: '" + key.toJSON() + "'");
            }
            return this._store[h][1];
        },
        __setitem__: function (key, value) {
            this._store[key.__hash__()] = [key, value];
        },
        get: function (args) {
            var h = args[0].__hash__();
            var def = args.length > 1 ? args[1] : py.None;
            if (!(h in this._store)) {
                return def;
            }
            return this._store[h][1];
        },
        toJSON: function () {
            var out = {};
            for(var k in this._store) {
                var item = this._store[k];
                out[item[0].toJSON()] = item[1].toJSON();
            }
            return out;
        }
    });
    py.def = py.type(function def(nativefunc) {
        this._inst = null;
        this._func = nativefunc;
    }, py.object, {
        __call__: function (args, kwargs) {
            // don't want to rewrite __call__ for instancemethod
            return this._func.call(this._inst, args, kwargs);
        },
        toJSON: function () {
            return this._func;
        }
    });
    var PY_instancemethod = py.type(function instancemethod(nativefunc, instance, _cls) {
        // could also use bind?
        this._inst = instance;
        this._func = nativefunc;
    }, py.def, {});

    py.issubclass = new py.def(function issubclass(args) {
        var derived = args[0], parent = args[1];
        // still hurts my brain that this can work
        return derived.prototype instanceof py.object
            ? py.True
            : py.False;
    });


    // All binary operators with fallbacks, so they can be applied generically
    var PY_operators = {
        '==': ['eq', 'eq', function (a, b) { return a === b; }],
        '!=': ['ne', 'ne', function (a, b) { return a !== b; }],
        '<>': ['ne', 'ne', function (a, b) { return a !== b; }],
        '<': ['lt', 'gt', function (a, b) {return a.constructor.name < b.constructor.name;}],
        '<=': ['le', 'ge', function (a, b) {return a.constructor.name <= b.constructor.name;}],
        '>': ['gt', 'lt', function (a, b) {return a.constructor.name > b.constructor.name;}],
        '>=': ['ge', 'le', function (a, b) {return a.constructor.name >= b.constructor.name;}],

        '+': ['add', 'radd'],
        '-': ['sub', 'rsub'],
        '*': ['mul', 'rmul'],
        '/': ['div', 'rdiv'],
        '//': ['floordiv', 'rfloordiv'],
        '%': ['mod', 'rmod'],
        '**': ['pow', 'rpow'],
        '<<': ['lshift', 'rlshift'],
        '>>': ['rshift', 'rrshift'],
        '&': ['and', 'rand'],
        '^': ['xor', 'rxor'],
        '|': ['or', 'ror']
    };
    /**
      * Implements operator fallback/reflection.
      *
      * First two arguments are the objects to apply the operator on,
      * in their actual order (ltr).
      *
      * Third argument is the actual operator.
      *
      * If the operator methods raise exceptions, those exceptions are
      * not intercepted.
      */
    var PY_op = function (o1, o2, op) {
        var r;
        var methods = PY_operators[op];
        var forward = '__' + methods[0] + '__', reverse = '__' + methods[1] + '__';
        var otherwise = methods[2];

        if (forward in o1 && (r = o1[forward](o2)) !== py.NotImplemented) {
            return r;
        }
        if (reverse in o2 && (r = o2[reverse](o1)) !== py.NotImplemented) {
            return r;
        }
        if (otherwise) {
            return PY_ensurepy(otherwise(o1, o2));
        }
        throw new Error(
            "TypeError: unsupported operand type(s) for " + op + ": '"
                + o1.constructor.name + "' and '"
                + o2.constructor.name + "'");
    };

    var PY_builtins = {
        type: py.type,

        None: py.None,
        True: py.True,
        False: py.False,
        NotImplemented: py.NotImplemented,

        object: py.object,
        bool: py.bool,
        float: py.float,
        tuple: py.tuple,
        list: py.list,
        dict: py.dict,
        issubclass: py.issubclass
    };

    py.parse = function (toks) {
        var index = 0;
        token = toks[0];
        next = function () { return toks[++index]; };
        return expression();
    };
    var evaluate_operator = function (operator, a, b) {
        var v;
        switch (operator) {
        case 'is': return a === b ? py.True : py.False;
        case 'is not': return a !== b ? py.True : py.False;
        case 'in':
            return b.__contains__(a);
        case 'not in':
            return b.__contains__(a) === py.True ? py.False : py.True;
        case '==': case '!=': case '<>':
        case '<': case '<=':
        case '>': case '>=':
            return PY_op(a, b, operator);
        }
        throw new Error('SyntaxError: unknown comparator [[' + operator + ']]');
    };
    py.evaluate = function (expr, context) {
        context = context || {};
        switch (expr.id) {
        case '(name)':
            var val = context[expr.value];
            if (val === undefined && expr.value in PY_builtins) {
                return PY_builtins[expr.value];
            }
            return PY_ensurepy(val, expr.value);
        case '(string)':
            return new py.str(expr.value);
        case '(number)':
            return new py.float(expr.value);
        case '(constant)':
            switch (expr.value) {
            case 'None': return py.None;
            case 'False': return py.False;
            case 'True': return py.True;
            }
            throw new Error("SyntaxError: unknown constant '" + expr.value + "'");
        case '(comparator)':
            var result, left = py.evaluate(expr.expressions[0], context);
            for(var i=0; i<expr.operators.length; ++i) {
                result = evaluate_operator(
                    expr.operators[i],
                    left,
                    left = py.evaluate(expr.expressions[i+1], context));
                if (result === py.False) { return py.False; }
            }
            return py.True;
        case 'not':
            return py.evaluate(expr.first, context).__nonzero__() === py.True
                ? py.False
                : py.True;
        case 'and':
            var and_first = py.evaluate(expr.first, context);
            if (and_first.__nonzero__() === py.True) {
                return py.evaluate(expr.second, context);
            }
            return and_first;
        case 'or':
            var or_first = py.evaluate(expr.first, context);
            if (or_first.__nonzero__() === py.True) {
                return or_first
            }
            return py.evaluate(expr.second, context);
        case '(':
            if (expr.second) {
                var callable = py.evaluate(expr.first, context);
                var args = [], kwargs = {};
                for (var jj=0; jj<expr.second.length; ++jj) {
                    var arg = expr.second[jj];
                    if (arg.id !== '=') {
                        // arg
                        args.push(py.evaluate(arg, context));
                    } else {
                        // kwarg
                        kwargs[arg.first.value] =
                            py.evaluate(arg.second, context);
                    }
                }
                return callable.__call__(args, kwargs);
            }
            var tuple_exprs = expr.first,
                tuple_values = [];
            for (var j=0, len=tuple_exprs.length; j<len; ++j) {
                tuple_values.push(py.evaluate(
                    tuple_exprs[j], context));
            }
            var t = new py.tuple();
            t.values = tuple_values;
            return t;
        case '[':
            if (expr.second) {
                return py.evaluate(expr.first, context)
                    .__getitem__(py.evaluate(expr.second, context));
            }
            var list_exprs = expr.first, list_values = [];
            for (var k=0; k<list_exprs.length; ++k) {
                list_values.push(py.evaluate(
                    list_exprs[k], context));
            }
            var l = new py.list();
            l.values = list_values;
            return l;
        case '{':
            var dict_exprs = expr.first, dict = new py.dict;
            for(var l=0; l<dict_exprs.length; ++l) {
                dict.__setitem__(
                    py.evaluate(dict_exprs[l][0], context),
                    py.evaluate(dict_exprs[l][1], context));
            }
            return dict;
        case '.':
            if (expr.second.id !== '(name)') {
                throw new Error('SyntaxError: ' + expr);
            }
            return py.evaluate(expr.first, context)
                .__getattribute__(expr.second.value);
        // numerical operators
        case '~':
            return (py.evaluate(expr.first, context)).__invert__();
        case '+':
            if (!expr.second) {
                return (py.evaluate(expr.first, context)).__pos__();
            }
        case '-':
            if (!expr.second) {
                return (py.evaluate(expr.first, context)).__neg__();
            }
        case '*': case '/': case '//':
        case '%':
        case '**':
        case '<<': case '>>':
        case '&': case '^': case '|':
            return PY_op(
                py.evaluate(expr.first, context),
                py.evaluate(expr.second, context),
                expr.id);

        default:
            throw new Error('SyntaxError: Unknown node [[' + expr.id + ']]');
        }
    };
    py.eval = function (str, context) {
        return py.evaluate(
            py.parse(
                py.tokenize(
                    str)),
            context).toJSON();
    }
})(typeof exports === 'undefined' ? py : exports);
