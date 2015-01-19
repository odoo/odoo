module.exports = function(environment) {
    var functions = {
        functionRegistry: require("./function-registry"),
        functionCaller: require("./function-caller")
    };

    //register functions
    require("./default");
    require("./color");
    require("./color-blending");
    require("./data-uri")(environment);
    require("./math");
    require("./number");
    require("./string");
    require("./svg")(environment);
    require("./types");

    return functions;
};
