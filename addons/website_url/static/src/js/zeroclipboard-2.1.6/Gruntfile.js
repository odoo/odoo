/*jshint -W106 */
/*jshint node:true, maxstatements: false, maxlen: false */

var os = require("os");
var path = require("path");
var loadGruntTasks = require("load-grunt-tasks");

module.exports = function(grunt) {
  "use strict";

  // Load necessary tasks
  loadGruntTasks(grunt);


  // Metadata
  var pkg = grunt.file.readJSON("package.json");

  // Make a temp dir for Flash compilation
  var tmpDir = os.tmpdir ? os.tmpdir() : os.tmpDir();
  var flashTmpDir = path.join(tmpDir, "zcflash");

  // Shared configuration
  var localPort = 7320;  // "ZERO"

  // Project configuration.
  var config = {
    // Task configuration
    jshint: {
      options: {
        jshintrc: true
      },
      gruntfile: ["Gruntfile.js"],
      component: ["index.js"],
      js: ["src/js/**/*.js", "!src/js/start.js", "!src/js/end.js"],
      test: ["test/**/*.js"],
      dist: ["dist/*.js", "!dist/*.min.js"]
    },
    flexpmd: {
      flash: {
        src: [flashTmpDir]
      }
    },
    clean: {
      dist: ["ZeroClipboard.*", "dist/ZeroClipboard.*"],
      flash: {
        options: {
          // Force is required when trying to clean outside of the project dir
          force: true
        },
        src: [flashTmpDir]
      },
      meta: ["bower.json", "composer.json", "LICENSE"],
      coveralls: ["tmp/", "coverage/"]
    },
    concat: {
      options: {
        stripBanners: false,
        process: {
          data: pkg
        }
      },
      core: {
        src: [
          "src/meta/source-banner.tmpl",
          "src/js/start.js",
          "src/js/shared/state.js",
          "src/js/shared/private.js",
          "src/js/core/state.js",
          "src/js/core/private.js",
          "src/js/core/api.js",
          "src/js/end.js"
        ],
        dest: "dist/ZeroClipboard.Core.js"
      },
      client: {
        src: [
          "src/meta/source-banner.tmpl",
          "src/js/start.js",
          "src/js/shared/state.js",
          "src/js/shared/private.js",
          "src/js/core/state.js",
          "src/js/core/private.js",
          "src/js/core/api.js",
          "src/js/client/state.js",
          "src/js/client/private.js",
          "src/js/client/api.js",
          "src/js/end.js"
        ],
        dest: "dist/ZeroClipboard.js"
      },
      flash: {
        files: [
          {
            src: [
              "src/meta/source-banner.tmpl",
              "src/flash/ZeroClipboard.as"
            ],
            dest: path.join(flashTmpDir, "ZeroClipboard.as")
          },
          {
            src: [
              "src/meta/source-banner.tmpl",
              "src/flash/ClipboardInjector.as"
            ],
            dest: path.join(flashTmpDir, "ClipboardInjector.as")
          },
          {
            src: [
              "src/meta/source-banner.tmpl",
              "src/flash/JsProxy.as"
            ],
            dest: path.join(flashTmpDir, "JsProxy.as")
          },
          {
            src: [
              "src/meta/source-banner.tmpl",
              "src/flash/XssUtils.as"
            ],
            dest: path.join(flashTmpDir, "XssUtils.as")
          }
        ]
      }
    },
    uglify: {
      options: {
        report: "min"
      },
      js: {
        options: {
          preserveComments: function(node, comment) {
            return comment &&
              comment.type === "comment2" &&
              /^(!|\*|\*!)\r?\n/.test(comment.value);
          },
          beautify: {
            beautify: true,
            // `indent_level` requires jshint -W106
            indent_level: 2
          },
          mangle: false,
          compress: false
        },
        files: [
          {
            src: ["<%= concat.core.dest %>"],
            dest: "<%= concat.core.dest %>"
          },
          {
            src: ["<%= concat.client.dest %>"],
            dest: "<%= concat.client.dest %>"
          }
        ]
      },
      minjs: {
        options: {
          preserveComments: function(node, comment) {
            return comment &&
              comment.type === "comment2" &&
              /^(!|\*!)\r?\n/.test(comment.value);
          },
          sourceMap: true,
          sourceMapName: function(dest) {
            return dest.replace(".min.js", ".min.map");
          },
          // Bundles the contents of "`src`" into the "`dest`.map" source map file. This way,
          // consumers only need to host the "*.min.js" and "*.min.map" files rather than
          // needing to host all three files: "*.js", "*.min.js", and "*.min.map".
          sourceMapIncludeSources: true
        },
        files: [
          {
            src: ["<%= concat.core.dest %>"],
            dest: "dist/ZeroClipboard.Core.min.js"
          },
          {
            src: ["<%= concat.client.dest %>"],
            dest: "dist/ZeroClipboard.min.js"
          }
        ]
      }
    },
    mxmlc: {
      options: {
        rawConfig: "-target-player=11.0.0 -static-link-runtime-shared-libraries=true"
      },
      swf: {
        files: {
          "dist/ZeroClipboard.swf": ["<%= concat.flash.files[0].dest %>"]
        }
      }
    },
    template: {
      options: {
        data: pkg
      },
      bower: {
        files: {
          "bower.json": ["src/meta/bower.json.tmpl"]
        }
      },
      composer: {
        files: {
          "composer.json": ["src/meta/composer.json.tmpl"]
        }
      },
      LICENSE: {
        files: {
          "LICENSE": ["src/meta/LICENSE.tmpl"]
        }
      }
    },
    chmod: {
      options: {
        mode: "444"
      },
      dist: ["dist/ZeroClipboard.*"],
      meta: ["bower.json", "composer.json", "LICENSE"]
    },
    connect: {
      server: {
        options: {
          port: localPort
        }
      }
    },
    qunit: {
      file: [
        "test/shared/private.tests.js.html",
        "test/core/private.tests.js.html",
        "test/core/api.tests.js.html",
        "test/client/private.tests.js.html",
        "test/client/api.tests.js.html",
        "test/built/ZeroClipboard.Core.tests.js.html",
        "test/built/ZeroClipboard.tests.js.html"
        //"test/**/*.tests.js.html"
      ],
      http: {
        options: {
          urls:
            grunt.file.expand([
              "test/shared/private.tests.js.html",
              "test/core/private.tests.js.html",
              "test/core/api.tests.js.html",
              "test/client/private.tests.js.html",
              "test/client/api.tests.js.html",
              "test/built/ZeroClipboard.Core.tests.js.html",
              "test/built/ZeroClipboard.tests.js.html"
              //"test/**/*.tests.js.html"
            ]).map(function(testPage) {
              return "http://localhost:" + localPort + "/" + testPage + "?noglobals=true";
            })
        }
      },
      coveralls: {
        options: {
          "--web-security": false,
          timeout: 10000,
          coverage: {
            baseUrl: ".",
            src: [
              "src/js/**/*.js",
              "!src/js/start.js",
              "!src/js/end.js",
              "dist/*.js",
              "!dist/*.min.js"
            ],
            instrumentedFiles: "tmp",
            htmlReport: "coverage/html",
            lcovReport: "coverage/lcov",
            statementsThresholdPct: 60.0,
            disposeCollector: true
          },
          urls:
            grunt.file.expand([
              "test/shared/private.tests.js.html",
              "test/core/private.tests.js.html",
              "test/core/api.tests.js.html",
              "test/client/private.tests.js.html",
              "test/client/api.tests.js.html",
              "test/built/ZeroClipboard.Core.tests.js.html",
              "test/built/ZeroClipboard.tests.js.html"
              //"test/**/*.tests.js.html"
            ]).map(function(testPage) {
              return "http://localhost:" + localPort + "/" + testPage + "?noglobals=true";
            })
        }
      }
    },
    coveralls: {
      options: {
        force: true
      },
      all: {
        src: "<%= qunit.coveralls.options.coverage.lcovReport %>/lcov.info"
      }
    },
    watch: {
      options: {
        spawn: false
      },
      gruntfile: {
        files: "<%= jshint.Gruntfile %>",
        tasks: ["jshint:Gruntfile"]
      },
      js: {
        files: "<%= jshint.js %>",
        tasks: ["jshint:js", "unittest"]
      },
      test: {
        files: "<%= jshint.test %>",
        tasks: ["jshint:test", "unittest"]
      }
    }
  };
  grunt.initConfig(config);


  // Task aliases and chains
  grunt.registerTask("jshint-prebuild", ["jshint:gruntfile", "jshint:component", "jshint:js", "jshint:test"]);
  grunt.registerTask("prep-flash",      ["clean:flash", "concat:flash"]);
  grunt.registerTask("validate",        ["jshint-prebuild", "prep-flash", "flexpmd"]);
  grunt.registerTask("build",           ["clean", "concat", "jshint:dist", "uglify", "mxmlc", "template", "chmod"]);
  grunt.registerTask("build-travis",    ["clean", "concat", "jshint:dist", "mxmlc", "chmod:dist"]);
  grunt.registerTask("test",            ["connect", "qunit:file", "qunit:http"]);

  // Default task
  grunt.registerTask("default", ["validate", "build", "test"]);

  // Travis CI task
  grunt.registerTask("travis",  ["validate", "build-travis", "test", "qunit:coveralls", "coveralls"]);

};
