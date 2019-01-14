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

    infix('|', 70); infix('^', 80); infix('&', 90);

    infix('<<', 100); infix('>>', 100);

    infix('+', 110); infix('-', 110);

    infix('*', 120); infix('/', 120);
    infix('//', 120); infix('%', 120);

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

        var DecNumber = '\\d+(L|l)?';
        var IntNumber = DecNumber;
        var PointFloat = group('\\d+\\.\\d*', '\\.\\d+');
        var FloatNumber = PointFloat;
        var Number = group(FloatNumber, IntNumber);

        var Operator = group("\\*\\*=?", ">>=?", "<<=?", "<>", "!=",
                             "//=?", "[+\\-*/%&|^=<>]=?", "~");
        var Bracket = '[\\[\\]\\(\\)\\{\\}]';
        var Special = '[:;.,`@]';
        var Funny = group(Operator, Bracket, Special);

        var ContStr = group("([uU])?'([^']*)'", '([uU])?"([^"]*)"');

        var PseudoToken = Whitespace + group(Number, Funny, ContStr, Name);

        var number_pattern = new RegExp('^' + Number + '$');
        var string_pattern = new RegExp('^' + ContStr + '$');
        var name_pattern = new RegExp('^' + Name + '$');
        var strip = new RegExp('^' + Whitespace);
        return function tokenize(s) {
            s = s
                .replace(/\\\"/g, '\\u0022')   // for double quote
                .replace(/\\\'/g, '\\u0027');  // for single quote
            var max=s.length, tokens = [], start, end;
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

                start = pseudomatch.index;
                end = pseudoprog.lastIndex;
                // strip leading space caught by Whitespace
                var token = s.slice(start, end).replace(strip, '');

                if (number_pattern.test(token)) {
                    tokens.push(create(symbols['(number)'], {
                        value: parseFloat(token)
                    }));
                } else if (string_pattern.test(token)) {
                    var m = string_pattern.exec(token);
                    var value = (m[3] !== undefined ? m[3] : m[5]);
                    value
                        .replace(/\\u0022/g, '"')
                        .replace(/\\u0027/g, "'");
                    tokens.push(create(symbols['(string)'], {
                        unicode: !!(m[2] || m[4]),
                        value: value
                    }));
                } else if (token in symbols) {
                    var symbol;
                    // transform 'not in' and 'is not' in a single token
                    if (token === 'in' && tokens.length > 1 && tokens[tokens.length-1].id === 'not') {
                        symbol = symbols['not in'];
                        tokens.pop();
                    } else if (token === 'not' && tokens.length > 1 && tokens[tokens.length-1].id === 'is') {
                        symbol = symbols['is not'];
                        tokens.pop();
                    } else {
                        symbol = symbols[token];
                    }
                    tokens.push(create(symbol));
                } else if (name_pattern.test(token)) {
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

        var fn = function () {};
        fn.prototype = py.object;
        if (py.PY_isInstance(val, py.object)
            || py.PY_isSubclass(val, py.object)) {
            return val;
        }

        switch (typeof val) {
        case 'number':
            return py.float.fromJSON(val);
        case 'string':
            return py.str.fromJSON(val);
        case 'function':
            return py.PY_def.fromJSON(val);
        }

        switch(val.constructor) {
        case Object:
            // TODO: why py.object instead of py.dict?
            var o = py.PY_call(py.object);
            for (var prop in val) {
                if (val.hasOwnProperty(prop)) {
                    o[prop] = val[prop];
                }
            }
            return o;
        case Array:
            return py.list.fromJSON(val);
        }

        throw new Error("Could not convert " + val + " to a pyval");
    }

    var typename = function (obj) {
        if (obj.__class__) { // py type
            return obj.__class__.__name__;
        } else if(typeof obj !== 'object') { // JS primitive
            return typeof obj;
        } else { // JS object
            return obj.constructor.name;
        }
    };
    // JSAPI, JS-level utility functions for implementing new py.js
    // types
    py.py = {};

    py.PY_parseArgs = function PY_parseArgs(argument, format) {
        var out = {};
        var args = argument[0];
        var kwargs = {};
        for (var k in argument[1]) {
            if (!argument[1].hasOwnProperty(k)) { continue; }
            kwargs[k] = argument[1][k];
        }
        if (typeof format === 'string') {
            format = format.split(/\s+/);
        }
        var name = function (spec) {
            if (typeof spec === 'string') {
                return spec;
            } else if (spec instanceof Array && spec.length === 2) {
                return spec[0];
            }
            throw new Error(
                "TypeError: unknown format specification " +
                    JSON.stringify(spec));
        };
        var spec;
        // TODO: ensure all format arg names are actual names?
        for(var i=0; i<args.length; ++i) {
            spec = format[i];
            // spec list ended, or specs switching to keyword-only
            if (!spec || spec === '*') {
                throw new Error(
                    "TypeError: function takes exactly " + (i-1) +
                    " positional arguments (" + args.length +
                    " given")
            } else if(/^\*\w/.test(spec)) {
                // *args, final
                out[name(spec.slice(1))] = args.slice(i);
                break;
            }

            out[name(spec)] = args[i];
        }
        for(var j=i; j<format.length; ++j) {
            spec = format[j];
            var n = name(spec);

            if (n in out) {
                throw new Error(
                    "TypeError: function got multiple values " + 
                    "for keyword argument '" + kwarg + "'");
            }
            if (/^\*\*\w/.test(n)) {
                // **kwarg
                out[n.slice(2)] = kwargs;
                kwargs = {};
                break;
            }
            if (n in kwargs) {
                out[n] = kwargs[n];
                // Remove from args map
                delete kwargs[n];
            }
        }
        // Ensure all keyword arguments were consumed
        for (var key in kwargs) {
            throw new Error(
                "TypeError: function got an unexpected keyword argument '"
                    + key + "'");
        }

        // Fixup args count if there's a kwonly flag (or an *args)
        var kwonly = 0;
        for(var k = 0; k < format.length; ++k) {
            if (/^\*/.test(format[k])) { kwonly = 1; break; }
        }
        // Check that all required arguments have been matched, add
        // optional values
        for(var k = 0; k < format.length; ++k) {
            spec = format[k];
            var n = name(spec);
            // kwonly, va_arg or matched argument
            if (/^\*/.test(n) || n in out) { continue; }
            // Unmatched required argument
            if (!(spec instanceof Array)) {
                throw new Error(
                    "TypeError: function takes exactly " + (format.length - kwonly)
                    + " arguments");
            }
            // Set default value
            out[n] = spec[1];
        }
        
        return out;
    };

    py.PY_hasAttr = function (o, attr_name) {
        try {
            py.PY_getAttr(o, attr_name);
            return true;
        } catch (e) {
            return false;
        }
    };
    py.PY_getAttr = function (o, attr_name) {
        return PY_ensurepy(o.__getattribute__(attr_name));
    };
    py.PY_str = function (o) {
        var v = o.__str__();
        if (py.PY_isInstance(v, py.str)) {
            return v;
        }
        throw new Error(
            'TypeError: __str__ returned non-string (type '
                + typename(v)
                +')');
    };
    py.PY_isInstance = function (inst, cls) {
        var fn = function () {};
        fn.prototype = cls;
        return inst instanceof fn;
    };
    py.PY_isSubclass = function (derived, cls) {
        var fn = function () {};
        fn.prototype = cls;
        return derived === cls || derived instanceof fn;
    };
    py.PY_call = function (callable, args, kwargs) {
        if (!args) {
            args = [];
        }
        if (typeof args === 'object' && !(args instanceof Array)) {
            kwargs = args;
            args = [];
        }
        if (!kwargs) {
            kwargs = {};
        }
        if (callable.__is_type) {
            // class hack
            var instance = callable.__new__.call(callable, args, kwargs);
            var typ = function () {};
            typ.prototype = callable;
            if (instance instanceof typ) {
                instance.__init__.call(instance, args, kwargs);
            }
            return instance
        }
        return callable.__call__(args, kwargs);
    };
    py.PY_isTrue = function (o) {
        var res = o.__nonzero__();
        if (res === py.True) {
            return true;
        }
        if (res === py.False) {
            return false;
        }
        throw new Error(
            "TypeError: __nonzero__ should return bool, returned "
                + typename(res));
    };
    py.PY_not = function (o) {
        return !py.PY_isTrue(o);
    };
    py.PY_size = function (o) {
        if (!o.__len__) {
            throw new Error(
                "TypeError: object of type '" +
                    typename(o) +
                    "' has no len()");
        }
        var v = o.__len__();
        if (typeof v !== 'number') {
            throw new Error("TypeError: a number is required");
        }
        return v;
    };
    py.PY_getItem = function (o, key) {
        if (!('__getitem__' in o)) {
            throw new Error(
                "TypeError: '" + typename(o) +
                    "' object is unsubscriptable")
        }
        if (!py.PY_isInstance(key, py.object)) {
            throw new Error(
                "TypeError: '" + typename(key) +
                    "' is not a py.js object");
        }
        var res = o.__getitem__(key);
        if (!py.PY_isInstance(key, py.object)) {
            throw new Error(
                "TypeError: __getitem__ must return a py.js object, got "
                    + typename(res));
        }
        return res;
    };
    py.PY_setItem = function (o, key, v) {
        if (!('__setitem__' in o)) {
            throw new Error(
                "TypeError: '" + typename(o) +
                    "' object does not support item assignment");
        }
        if (!py.PY_isInstance(key, py.object)) {
            throw new Error(
                "TypeError: '" + typename(key) +
                    "' is not a py.js object");
        }
        if (!py.PY_isInstance(v, py.object)) {
            throw new Error(
                "TypeError: '" + typename(v) +
                    "' is not a py.js object");
        }
        o.__setitem__(key, v);
    };

    py.PY_add = function (o1, o2) {
        return PY_op(o1, o2, '+');
    };
    py.PY_subtract = function (o1, o2) {
        return PY_op(o1, o2, '-');
    };
    py.PY_multiply = function (o1, o2) {
        return PY_op(o1, o2, '*');
    };
    py.PY_divide = function (o1, o2) {
        return PY_op(o1, o2, '/');
    };
    py.PY_negative = function (o) {
        if (!o.__neg__) {
            throw new Error(
                "TypeError: bad operand for unary -: '"
                    + typename(o)
                    + "'");
        }
        return o.__neg__();
    };
    py.PY_positive = function (o) {
        if (!o.__pos__) {
            throw new Error(
                "TypeError: bad operand for unary +: '"
                    + typename(o)
                    + "'");
        }
        return o.__pos__();
    };

    // Builtins
    py.type = function type(name, bases, dict) {
        if (typeof name !== 'string') {
            throw new Error("ValueError: a class name should be a string");
        }
        if (!bases || bases.length === 0) {
            bases = [py.object];
        } else if (bases.length > 1) {
            throw new Error("ValueError: can't provide multiple bases for a "
                          + "new type");
        }
        var base = bases[0];
        var ClassObj = create(base);
        if (dict) {
            for (var k in dict) {
                if (!dict.hasOwnProperty(k)) { continue; }
                ClassObj[k] = dict[k];
            }
        }
        ClassObj.__class__ = ClassObj;
        ClassObj.__name__ = name;
        ClassObj.__bases__ = bases;
        ClassObj.__is_type = true;

        return ClassObj;
    };
    py.type.__call__ = function () {
        var args = py.PY_parseArgs(arguments, ['object']);
        return args.object.__class__;
    };

    var hash_counter = 0;
    py.object = py.type('object', [{}], {
        __new__: function () {
            // If ``this`` isn't the class object, this is going to be
            // beyond fucked up
            var inst = create(this);
            inst.__is_type = false;
            return inst;
        },
        __init__: function () {},
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
            if (py.PY_isTrue(this.__eq__(other))) {
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
            return py.str.fromJSON('<' + typename(this) + ' object>');
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
                    return val.__get__(this, py.PY_call(py.type, [this]));
                }
                if (typeof val === 'function' && !this.hasOwnProperty(name)) {
                    // val is a method from the class
                    return PY_instancemethod.fromJSON(val, this);
                }
                return val;
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
    var NoneType = py.type('NoneType', null, {
        __nonzero__: function () { return py.False; },
        toJSON: function () { return null; }
    });
    py.None = py.PY_call(NoneType);
    var NotImplementedType = py.type('NotImplementedType', null, {});
    py.NotImplemented = py.PY_call(NotImplementedType);
    var booleans_initialized = false;
    py.bool = py.type('bool', null, {
        __new__: function () {
            if (!booleans_initialized) {
                return py.object.__new__.apply(this);
            }

            var ph = {};
            var args = py.PY_parseArgs(arguments, [['value', ph]]);
            if (args.value === ph) {
                return py.False;
            }
            return py.PY_isTrue(args.value) ? py.True : py.False;
        },
        __str__: function () {
            return py.str.fromJSON((this === py.True) ? "True" : "False");
        },
        __nonzero__: function () { return this; },
        fromJSON: function (val) { return val ? py.True : py.False },
        toJSON: function () { return this === py.True; }
    });
    py.True = py.PY_call(py.bool);
    py.False = py.PY_call(py.bool);
    booleans_initialized = true;
    py.float = py.type('float', null, {
        __init__: function () {
            var placeholder = {};
            var args = py.PY_parseArgs(arguments, [['value', placeholder]]);
            var value = args.value;
            if (value === placeholder) {
                this._value = 0; return;
            }
            if (py.PY_isInstance(value, py.float)) {
                this._value = value._value;
            }
            if (py.PY_isInstance(value, py.object) && '__float__' in value) {
                var res = value.__float__();
                if (py.PY_isInstance(res, py.float)) {
                    this._value = res._value;
                    return;
                }
                throw new Error('TypeError: __float__ returned non-float (type ' +
                                typename(res) + ')');
            }
            throw new Error('TypeError: float() argument must be a string or a number');
        },
        __str__: function () {
            return py.str.fromJSON(String(this._value));
        },
        __eq__: function (other) {
            return this._value === other._value ? py.True : py.False;
        },
        __lt__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return this._value < other._value ? py.True : py.False;
        },
        __le__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return this._value <= other._value ? py.True : py.False;
        },
        __gt__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return this._value > other._value ? py.True : py.False;
        },
        __ge__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return this._value >= other._value ? py.True : py.False;
        },
        __abs__: function () {
            return py.float.fromJSON(
                Math.abs(this._value));
        },
        __add__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return py.float.fromJSON(this._value + other._value);
        },
        __mod__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return py.float.fromJSON(this._value % other._value);
        },
        __neg__: function () {
            return py.float.fromJSON(-this._value);
        },
        __sub__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return py.float.fromJSON(this._value - other._value);
        },
        __mul__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return py.float.fromJSON(this._value * other._value);
        },
        __div__: function (other) {
            if (!py.PY_isInstance(other, py.float)) {
                return py.NotImplemented;
            }
            return py.float.fromJSON(this._value / other._value);
        },
        __nonzero__: function () {
            return this._value ? py.True : py.False;
        },
        fromJSON: function (v) {
            if (!(typeof v === 'number')) {
                throw new Error('py.float.fromJSON can only take numbers');
            }
            var instance = py.PY_call(py.float);
            instance._value = v;
            return instance;
        },
        toJSON: function () {
            return this._value;
        }
    });
    py.str = py.type('str', null, {
        __init__: function () {
            var placeholder = {};
            var args = py.PY_parseArgs(arguments, [['value', placeholder]]);
            var s = args.value;
            if (s === placeholder) { this._value = ''; return; }
            this._value = py.PY_str(s)._value;
        },
        __hash__: function () {
            return '\1\0\1' + this._value;
        },
        __str__: function () {
            return this;
        },
        __eq__: function (other) {
            if (py.PY_isInstance(other, py.str)
                    && this._value === other._value) {
                return py.True;
            }
            return py.False;
        },
        __lt__: function (other) {
            if (py.PY_not(py.PY_call(py.isinstance, [other, py.str]))) {
                return py.NotImplemented;
            }
            return this._value < other._value ? py.True : py.False;
        },
        __le__: function (other) {
            if (!py.PY_isInstance(other, py.str)) {
                return py.NotImplemented;
            }
            return this._value <= other._value ? py.True : py.False;
        },
        __gt__: function (other) {
            if (!py.PY_isInstance(other, py.str)) {
                return py.NotImplemented;
            }
            return this._value > other._value ? py.True : py.False;
        },
        __ge__: function (other) {
            if (!py.PY_isInstance(other, py.str)) {
                return py.NotImplemented;
            }
            return this._value >= other._value ? py.True : py.False;
        },
        __add__: function (other) {
            if (!py.PY_isInstance(other, py.str)) {
                return py.NotImplemented;
            }
            return py.str.fromJSON(this._value + other._value);
        },
        __nonzero__: function () {
            return this._value.length ? py.True : py.False;
        },
        __contains__: function (s) {
            return (this._value.indexOf(s._value) !== -1) ? py.True : py.False;
        },
        fromJSON: function (s) {
            if (typeof s === 'string') {
                var instance = py.PY_call(py.str);
                instance._value = s;
                return instance;
            }
            throw new Error("str.fromJSON can only take strings");
        },
        toJSON: function () {
            return this._value;
        }
    });
    py.tuple = py.type('tuple', null, {
        __init__: function () {
            this._values = [];
        },
        __len__: function () {
            return this._values.length;
        },
        __nonzero__: function () {
            return py.PY_size(this) > 0 ? py.True : py.False;
        },
        __contains__: function (value) {
            for(var i=0, len=this._values.length; i<len; ++i) {
                if (py.PY_isTrue(this._values[i].__eq__(value))) {
                    return py.True;
                }
            }
            return py.False;
        },
        __getitem__: function (index) {
            return this._values[index.toJSON()];
        },
        toJSON: function () {
            var out = [];
            for (var i=0; i<this._values.length; ++i) {
                out.push(this._values[i].toJSON());
            }
            return out;
        },
        fromJSON: function (ar) {
            if (!(ar instanceof Array)) {
                throw new Error("Can only create a py.tuple from an Array");
            }
            var t = py.PY_call(py.tuple);
            for(var i=0; i<ar.length; ++i) {
                t._values.push(PY_ensurepy(ar[i]));
            }
            return t;
        }
    });
    py.list = py.type('list', null, {
        __nonzero__: function () {
            return this.__len__ > 0 ? py.True : py.False;
        },
    });
    _.defaults(py.list, py.tuple) // Copy attributes not redefined in type list
    py.dict = py.type('dict', null, {
        __init__: function () {
            this._store = {};
        },
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
        __len__: function () {
            return Object.keys(this._store).length
        },
        __nonzero__: function () {
            return py.PY_size(this) > 0 ? py.True : py.False;
        },
        get: function () {
            var args = py.PY_parseArgs(arguments, ['k', ['d', py.None]]);
            var h = args.k.__hash__();
            if (!(h in this._store)) {
                return args.d;
            }
            return this._store[h][1];
        },
        fromJSON: function (d) {
            var instance = py.PY_call(py.dict);
            for (var k in (d || {})) {
                if (!d.hasOwnProperty(k)) { continue; }
                instance.__setitem__(
                    py.str.fromJSON(k),
                    PY_ensurepy(d[k]));
            }
            return instance;
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
    py.PY_def = py.type('function', null, {
        __call__: function () {
            // don't want to rewrite __call__ for instancemethod
            return this._func.apply(this._inst, arguments);
        },
        fromJSON: function (nativefunc) {
            var instance = py.PY_call(py.PY_def);
            instance._inst = null;
            instance._func = nativefunc;
            return instance;
        },
        toJSON: function () {
            return this._func;
        }
    });
    py.classmethod = py.type('classmethod', null, {
        __init__: function () {
            var args = py.PY_parseArgs(arguments, 'function');
            this._func = args['function'];
        },
        __get__: function (obj, type) {
            return PY_instancemethod.fromJSON(this._func, type);
        },
        fromJSON: function (func) {
            return py.PY_call(py.classmethod, [func]);
        }
    });
    var PY_instancemethod = py.type('instancemethod', [py.PY_def], {
        fromJSON: function (nativefunc, instance) {
            var inst = py.PY_call(PY_instancemethod);
            // could also use bind?
            inst._inst = instance;
            inst._func = nativefunc;
            return inst;
        }
    });

    py.abs = new py.PY_def.fromJSON(function abs() {
        var args = py.PY_parseArgs(arguments, ['number']);
        if (!args.number.__abs__) {
            throw new Error(
                "TypeError: bad operand type for abs(): '"
                    + typename(args.number)
                    + "'");
        }
        return  args.number.__abs__();
    });
    py.len = new py.PY_def.fromJSON(function len() {
        var args = py.PY_parseArgs(arguments, ['object']);
        return py.float.fromJSON(py.PY_size(args.object));
    });
    py.isinstance = new py.PY_def.fromJSON(function isinstance() {
        var args = py.PY_parseArgs(arguments, ['object', 'class']);
        return py.PY_isInstance(args.object, args['class'])
            ? py.True : py.False;
    });
    py.issubclass = new py.PY_def.fromJSON(function issubclass() {
        var args = py.PY_parseArgs(arguments, ['C', 'B']);
        return py.PY_isSubclass(args.C, args.B)
            ? py.True : py.False;
    });


    /**
     * Implements the decoding of Python string literals (embedded in
     * JS strings) into actual JS strings. This includes the decoding
     * of escapes into their corresponding JS
     * characters/codepoints/whatever.
     *
     * The ``unicode`` flags notes whether the literal should be
     * decoded as a bytestring literal or a unicode literal, which
     * pretty much only impacts decoding (or not) of unicode escapes
     * at this point since bytestrings are not technically handled
     * (everything is decoded to JS "unicode" strings)
     *
     * Eventurally, ``str`` could eventually use typed arrays, that'd
     * be interesting...
     */
    var PY_decode_string_literal = function (str, unicode) {
        var out = [], code;
        // Directly maps a single escape code to an output
        // character
        var direct_map = {
            '\\': '\\',
            '"': '"',
            "'": "'",
            'a': '\x07',
            'b': '\x08',
            'f': '\x0c',
            'n': '\n',
            'r': '\r',
            't': '\t',
            'v': '\v'
        };

        for (var i=0; i<str.length; ++i) {
            if (str[i] !== '\\') {
                out.push(str[i]);
                continue;
            }
            var escape = str[i+1];
            if (escape in direct_map) {
                out.push(direct_map[escape]);
                ++i;
                continue;
            }

            switch (escape) {
            // Ignored
            case '\n': ++i; continue;
            // Character named name in the Unicode database (Unicode only)
            case 'N':
                if (!unicode) { break; }
                throw Error("SyntaxError: \\N{} escape not implemented");
            case 'u':
                if (!unicode) { break; }
                var uni = str.slice(i+2, i+6);
                if (!/[0-9a-f]{4}/i.test(uni)) {
                    throw new Error([
                        "SyntaxError: (unicode error) 'unicodeescape' codec",
                        " can't decode bytes in position ",
                        i, "-", i+4,
                        ": truncated \\uXXXX escape"
                    ].join(''));
                }
                code = parseInt(uni, 16);
                out.push(String.fromCharCode(code));
                // escape + 4 hex digits
                i += 5;
                continue;
            case 'U':
                if (!unicode) { break; }
                // TODO: String.fromCodePoint
                throw Error("SyntaxError: \\U escape not implemented");
            case 'x':
                // get 2 hex digits
                var hex = str.slice(i+2, i+4);
                if (!/[0-9a-f]{2}/i.test(hex)) {
                    if (!unicode) {
                        throw new Error('ValueError: invalid \\x escape');
                    }
                    throw new Error([
                        "SyntaxError: (unicode error) 'unicodeescape'",
                        " codec can't decode bytes in position ",
                        i, '-', i+2,
                        ": truncated \\xXX escape"
                    ].join(''))
                }
                code = parseInt(hex, 16);
                out.push(String.fromCharCode(code));
                // skip escape + 2 hex digits
                i += 3;
                continue;
            default:
                // Check if octal
                if (!/[0-8]/.test(escape)) { break; }
                var r = /[0-8]{1,3}/g;
                r.lastIndex = i+1;
                var m = r.exec(str);
                var oct = m[0];
                code = parseInt(oct, 8);
                out.push(String.fromCharCode(code));
                // skip matchlength
                i += oct.length;
                continue;
            }
            out.push('\\');
        }

        return out.join('');
    };
    // All binary operators with fallbacks, so they can be applied generically
    var PY_operators = {
        '==': ['eq', 'eq', function (a, b) { return a === b; }],
        '!=': ['ne', 'ne', function (a, b) { return a !== b; }],
        '<>': ['ne', 'ne', function (a, b) { return a !== b; }],
        '<': ['lt', 'gt', function (a, b) {return a.__class__.__name__ < b.__class__.__name__;}],
        '<=': ['le', 'ge', function (a, b) {return a.__class__.__name__ <= b.__class__.__name__;}],
        '>': ['gt', 'lt', function (a, b) {return a.__class__.__name__ > b.__class__.__name__;}],
        '>=': ['ge', 'le', function (a, b) {return a.__class__.__name__ >= b.__class__.__name__;}],

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
                + typename(o1) + "' and '" + typename(o2) + "'");
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
        str: py.str,
        unicode: py.unicode,
        tuple: py.tuple,
        list: py.list,
        dict: py.dict,

        abs: py.abs,
        len: py.len,
        isinstance: py.isinstance,
        issubclass: py.issubclass,
        classmethod: py.classmethod,
    };

    py.parse = function (toks) {
        var index = 0;
        token = toks[0];
        next = function () { return toks[++index]; };
        return expression();
    };
    var evaluate_operator = function (operator, a, b) {
        switch (operator) {
        case 'is': return a === b ? py.True : py.False;
        case 'is not': return a !== b ? py.True : py.False;
        case 'in':
            return b.__contains__(a);
        case 'not in':
            return py.PY_isTrue(b.__contains__(a)) ? py.False : py.True;
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
            return py.str.fromJSON(PY_decode_string_literal(
                expr.value, expr.unicode));
        case '(number)':
            return py.float.fromJSON(expr.value);
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
                if (py.PY_not(result)) { return py.False; }
            }
            return py.True;
        case 'not':
            return py.PY_isTrue(py.evaluate(expr.first, context)) ? py.False : py.True;
        case 'and':
            var and_first = py.evaluate(expr.first, context);
            if (py.PY_isTrue(and_first.__nonzero__())) {
                return py.evaluate(expr.second, context);
            }
            return and_first;
        case 'or':
            var or_first = py.evaluate(expr.first, context);
            if (py.PY_isTrue(or_first.__nonzero__())) {
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
                return py.PY_call(callable, args, kwargs);
            }
            var tuple_exprs = expr.first,
                tuple_values = [];
            for (var j=0, len=tuple_exprs.length; j<len; ++j) {
                tuple_values.push(py.evaluate(
                    tuple_exprs[j], context));
            }
            return py.tuple.fromJSON(tuple_values);
        case '[':
            if (expr.second) {
                return py.PY_getItem(
                    py.evaluate(expr.first, context),
                    py.evaluate(expr.second, context));
            }
            var list_exprs = expr.first, list_values = [];
            for (var k=0; k<list_exprs.length; ++k) {
                list_values.push(py.evaluate(
                    list_exprs[k], context));
            }
            return py.list.fromJSON(list_values);
        case '{':
            var dict_exprs = expr.first, dict = py.PY_call(py.dict);
            for(var l=0; l<dict_exprs.length; ++l) {
                py.PY_setItem(dict,
                    py.evaluate(dict_exprs[l][0], context),
                    py.evaluate(dict_exprs[l][1], context));
            }
            return dict;
        case '.':
            if (expr.second.id !== '(name)') {
                throw new Error('SyntaxError: ' + expr);
            }
            return py.PY_getAttr(py.evaluate(expr.first, context),
                                 expr.second.value);
        // numerical operators
        case '~':
            return (py.evaluate(expr.first, context)).__invert__();
        case '+':
            if (!expr.second) {
                return py.PY_positive(py.evaluate(expr.first, context));
            }
        case '-':
            if (!expr.second) {
                return py.PY_negative(py.evaluate(expr.first, context));
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
