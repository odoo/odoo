var Dimension = require("../tree/dimension"),
    functionRegistry = require("./function-registry");

var mathFunctions = {
    // name,  unit
    ceil:  null,
    floor: null,
    sqrt:  null,
    abs:   null,
    tan:   "",
    sin:   "",
    cos:   "",
    atan:  "rad",
    asin:  "rad",
    acos:  "rad"
};

function _math(fn, unit, n) {
    if (!(n instanceof Dimension)) {
        throw { type: "Argument", message: "argument must be a number" };
    }
    if (unit == null) {
        unit = n.unit;
    } else {
        n = n.unify();
    }
    return new Dimension(fn(parseFloat(n.value)), unit);
}

for (var f in mathFunctions) {
    if (mathFunctions.hasOwnProperty(f)) {
        mathFunctions[f] = _math.bind(null, Math[f], mathFunctions[f]);
    }
}

mathFunctions.round = function (n, f) {
    var fraction = typeof(f) === "undefined" ? 0 : f.value;
    return _math(function(num) { return num.toFixed(fraction); }, null, n);
};

functionRegistry.addMultiple(mathFunctions);
