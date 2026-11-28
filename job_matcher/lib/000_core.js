/* Shared namespace.

   build.py concatenates every lib/ and screens/ file into one IIFE, so all of
   them see this single object and nothing leaks onto window (except in a dev
   build, which exposes it on purpose). Do not redeclare JM in another file.

   House rule for everything in lib/ and screens/, comments included: no
   ampersands and no less-than signs anywhere, because the built page is stored
   as XML. See README.md section 3.6. */
var JM = {
    /* Every data/*.json file, keyed by filename. Injected by build.py. */
    data: {},

    /* Shorthand for data.config, resolved during boot. */
    config: {},

    /* Screen name -> definition, filled in by screens/*.js. */
    screens: {},

    /* Everything the visitor has entered so far. */
    state: {
        name: "",
        /* question id -> the chosen choice object */
        answers: {}
    }
};
