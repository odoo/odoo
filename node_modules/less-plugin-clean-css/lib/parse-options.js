module.exports = function(options) {
    if (typeof options === 'string') {
        var cleanOptionArgs = options.split(" ");
        options = {};
        for(var i = 0; i < cleanOptionArgs.length; i++) {
            var argSplit = cleanOptionArgs[i].split("="),
                argName = argSplit[0].replace(/^-+/,"");
            switch(argName) {
                case "keep-line-breaks":
                case "b":
                    options.keepBreaks = true;
                    break;
                case "s0":
                    options.keepSpecialComments = 0;
                    break;
                case "s1":
                    options.keepSpecialComments = 1;
                    break;
                case "keepSpecialComments":
                    var specialCommentOption = argSplit[1];
                    if (specialCommentOption !== "*") {
                        specialCommentOption = Number(specialCommentOption);
                    }
                    options.keepSpecialComments = specialCommentOption;
                    break;
                // for compatibility - does nothing
                case "skip-advanced":
                    options.advanced = false;
                    break;
                case "advanced":
                    options.advanced = true;
                    break;
                case "skip-rebase":
                    options.rebase = false;
                    break;
                case "rebase":
                    options.rebase = true;
                    break;
                case "skip-aggressive-merging":
                    options.aggressiveMerging = false;
                    break;
                case "skip-shorthand-compacting":
                    options.shorthandCompacting = false;
                    break;
                case "c":
                case "compatibility":
                    options.compatibility = argSplit[1];
                    break;
                case "rounding-precision":
                    options.roundingPrecision = Number(argSplit[1]);
                    break;
                default:
                    throw new Error("unrecognised clean-css option '" + argSplit[0] + "'");
            }
        }
    }
    return options;
};
