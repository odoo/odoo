// lessc_helper.js
//
//      helper functions for lessc
var lessc_helper = {

    //Stylize a string
    stylize : function(str, style) {
        var styles = {
            'reset'     : [0,   0],
            'bold'      : [1,  22],
            'inverse'   : [7,  27],
            'underline' : [4,  24],
            'yellow'    : [33, 39],
            'green'     : [32, 39],
            'red'       : [31, 39],
            'grey'      : [90, 39]
        };
        return '\033[' + styles[style][0] + 'm' + str +
               '\033[' + styles[style][1] + 'm';
    },

    //Print command line options
    printUsage: function() {
        console.log("usage: lessc [option option=parameter ...] <source> [destination]");
        console.log("");
        console.log("If source is set to `-' (dash or hyphen-minus), input is read from stdin.");
        console.log("");
        console.log("options:");
        console.log("  -h, --help               Prints help (this message) and exit.");
        console.log("  --include-path=PATHS     Sets include paths. Separated by `:'. Use `;' on Windows.");
        console.log("  -M, --depends            Outputs a makefile import dependency list to stdout.");
        console.log("  --no-color               Disables colorized output.");
        console.log("  --no-ie-compat           Disables IE compatibility checks.");
        console.log("  --no-js                  Disables JavaScript in less files");
        console.log("  -l, --lint               Syntax check only (lint).");
        console.log("  -s, --silent             Suppresses output of error messages.");
        console.log("  --strict-imports         Forces evaluation of imports.");
        console.log("  --insecure               Allows imports from insecure https hosts.");
        console.log("  -v, --version            Prints version number and exit.");
        console.log("  --source-map[=FILENAME]  Outputs a v3 sourcemap to the filename (or output filename.map).");
        console.log("  --source-map-rootpath=X  Adds this path onto the sourcemap filename and less file paths.");
        console.log("  --source-map-basepath=X  Sets sourcemap base path, defaults to current working directory.");
        console.log("  --source-map-less-inline Puts the less files into the map instead of referencing them.");
        console.log("  --source-map-map-inline  Puts the map (and any less files) into the output css file.");
        console.log("  --source-map-url=URL     Sets a custom URL to map file, for sourceMappingURL comment");
        console.log("                           in generated CSS file.");
        console.log("  -rp, --rootpath=URL      Sets rootpath for url rewriting in relative imports and urls");
        console.log("                           Works with or without the relative-urls option.");
        console.log("  -ru, --relative-urls     Re-writes relative urls to the base less file.");
        console.log("  -sm=on|off               Turns on or off strict math, where in strict mode, math.");
        console.log("  --strict-math=on|off     Requires brackets. This option may default to on and then");
        console.log("                           be removed in the future.");
        console.log("  -su=on|off               Allows mixed units, e.g. 1px+1em or 1px*1px which have units");
        console.log("  --strict-units=on|off    that cannot be represented.");
        console.log("  --global-var='VAR=VALUE' Defines a variable that can be referenced by the file.");
        console.log("  --modify-var='VAR=VALUE' Modifies a variable already declared in the file.");
        console.log("  --url-args='QUERYSTRING' Adds params into url tokens (e.g. 42, cb=42 or 'a=1&b=2')");
        console.log("  --plugin=PLUGIN=OPTIONS  Loads a plugin. You can also omit the --plugin= if the plugin begins");
        console.log("                           less-plugin. E.g. the clean css plugin is called less-plugin-clean-css");
        console.log("                           once installed (npm install less-plugin-clean-css), use either with");
        console.log("                           --plugin=less-plugin-clean-css or just --clean-css");
        console.log("                           specify options afterwards e.g. --plugin=less-plugin-clean-css=\"advanced\"");
        console.log("                           or --clean-css=\"advanced\"");
        console.log("");
        console.log("-------------------------- Deprecated ----------------");
        console.log("  --line-numbers=TYPE      Outputs filename and line numbers.");
        console.log("                           TYPE can be either 'comments', which will output");
        console.log("                           the debug info within comments, 'mediaquery'");
        console.log("                           that will output the information within a fake");
        console.log("                           media query which is compatible with the SASS");
        console.log("                           format, and 'all' which will do both.");
        console.log("  --verbose                Be verbose.");
	    console.log("  -x, --compress           Compresses output by removing some whitespaces.");
	    console.log("                           We recommend you use a dedicated minifer like less-plugin-clean-css");
        console.log("");
        console.log("Report bugs to: http://github.com/less/less.js/issues");
        console.log("Home page: <http://lesscss.org/>");
    }
};

// Exports helper functions
for (var h in lessc_helper) { if (lessc_helper.hasOwnProperty(h)) { exports[h] = lessc_helper[h]; }}
