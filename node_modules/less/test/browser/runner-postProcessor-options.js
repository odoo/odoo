var less = {logLevel: 4,
    errorReporting: "console"};
less.postProcessor = function(styles) {
    return 'hr {height:50px;}\n' + styles;
};
