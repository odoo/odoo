var environment = require("./environment"),
    FileManager = require("./file-manager"),
    UrlFileManager = require("./url-file-manager"),
    createFromEnvironment = require("../less"),
    less = createFromEnvironment(environment, [new FileManager(), new UrlFileManager()]),
    lesscHelper = require('./lessc-helper');

// allow people to create less with their own environment
less.createFromEnvironment = createFromEnvironment;
less.lesscHelper = lesscHelper;
less.PluginLoader = require("./plugin-loader");
less.fs = require("./fs");
less.FileManager = FileManager;
less.UrlFileManager = UrlFileManager;
less.formatError = function(ctx, options) {
    options = options || {};

    var message = "";
    var extract = ctx.extract;
    var error = [];
    var stylize = options.color ? lesscHelper.stylize : function (str) { return str; };

    // only output a stack if it isn't a less error
    if (ctx.stack && !ctx.type) { return stylize(ctx.stack, 'red'); }

    if (!ctx.hasOwnProperty('index') || !extract) {
        return ctx.stack || ctx.message;
    }

    if (typeof(extract[0]) === 'string') {
        error.push(stylize((ctx.line - 1) + ' ' + extract[0], 'grey'));
    }

    if (typeof(extract[1]) === 'string') {
        var errorTxt = ctx.line + ' ';
        if (extract[1]) {
            errorTxt += extract[1].slice(0, ctx.column) +
                            stylize(stylize(stylize(extract[1].substr(ctx.column, 1), 'bold') +
                            extract[1].slice(ctx.column + 1), 'red'), 'inverse');
        }
        error.push(errorTxt);
    }

    if (typeof(extract[2]) === 'string') {
        error.push(stylize((ctx.line + 1) + ' ' + extract[2], 'grey'));
    }
    error = error.join('\n') + stylize('', 'reset') + '\n';

    message += stylize(ctx.type + 'Error: ' + ctx.message, 'red');
    if (ctx.filename) {
        message += stylize(' in ', 'red') + ctx.filename +
            stylize(' on line ' + ctx.line + ', column ' + (ctx.column + 1) + ':', 'grey');
    }

    message += '\n' + error;

    if (ctx.callLine) {
        message += stylize('from ', 'red') + (ctx.filename || '') + '/n';
        message += stylize(ctx.callLine, 'grey') + ' ' + ctx.callExtract + '/n';
    }

    return message;
};

less.writeError = function (ctx, options) {
    options = options || {};
    if (options.silent) { return; }
    console.error(less.formatError(ctx, options));
};

// provide image-size functionality
require('./image-size');

module.exports = less;
