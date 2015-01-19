var contexts = require("./contexts"),
    visitor = require("./visitors"),
    tree = require("./tree");

module.exports = function(root, options) {
    options = options || {};
    var evaldRoot,
        variables = options.variables,
        evalEnv = new contexts.Eval(options);

    //
    // Allows setting variables with a hash, so:
    //
    //   `{ color: new tree.Color('#f01') }` will become:
    //
    //   new tree.Rule('@color',
    //     new tree.Value([
    //       new tree.Expression([
    //         new tree.Color('#f01')
    //       ])
    //     ])
    //   )
    //
    if (typeof(variables) === 'object' && !Array.isArray(variables)) {
        variables = Object.keys(variables).map(function (k) {
            var value = variables[k];

            if (! (value instanceof tree.Value)) {
                if (! (value instanceof tree.Expression)) {
                    value = new tree.Expression([value]);
                }
                value = new tree.Value([value]);
            }
            return new tree.Rule('@' + k, value, false, null, 0);
        });
        evalEnv.frames = [new tree.Ruleset(null, variables)];
    }

    var preEvalVisitors = [],
        visitors = [
            new visitor.JoinSelectorVisitor(),
            new visitor.ExtendVisitor(),
            new visitor.ToCSSVisitor({compress: Boolean(options.compress)})
        ], i;

    if (options.pluginManager) {
        var pluginVisitors = options.pluginManager.getVisitors();
        for(i =0; i < pluginVisitors.length; i++) {
            var pluginVisitor = pluginVisitors[i];
            if (pluginVisitor.isPreEvalVisitor) {
                preEvalVisitors.push(pluginVisitor);
            } else {
                if (pluginVisitor.isPreVisitor) {
                    visitors.splice(0, 0, pluginVisitor);
                } else {
                    visitors.push(pluginVisitor);
                }
            }
        }
    }

    for(i = 0; i < preEvalVisitors.length; i++) {
        preEvalVisitors[i].run(root);
    }

    evaldRoot = root.eval(evalEnv);

    for(i = 0; i < visitors.length; i++) {
        visitors[i].run(evaldRoot);
    }

    return evaldRoot;
};
