'use strict';
var fs = require('fs');

module.exports = function (grunt) {

    // Report the elapsed execution time of tasks.
    require('time-grunt')(grunt);
	
	var COMPRESS_FOR_TESTS = true;

    // Project configuration.
    grunt.initConfig({

        // Metadata required for build.
        build: grunt.file.readYAML('build/build.yml'),
        pkg: grunt.file.readJSON('package.json'),
        meta: {
            license: '<%= _.pluck(pkg.licenses, "type").join(", ") %>',
            copyright: 'Copyright (c) 2009-<%= grunt.template.today("yyyy") %>',
            banner: '/*!\n' +
                ' * Less - <%= pkg.description %> v<%= pkg.version %>\n' +
                ' * http://lesscss.org\n' +
                ' *\n' +
                ' * <%= meta.copyright %>, <%= pkg.author.name %> <<%= pkg.author.email %>>\n' +
                ' * Licensed under the <%= meta.license %> License.\n' +
                ' *\n' +
                ' */\n\n' +
                ' /**' +
                ' * @license <%= meta.license %>\n' +
                ' */\n\n'
        },

        shell: {
            options: {stdout: true, failOnError: true},
            test: {
                command: 'node test'
            },
            benchmark: {
                command: 'node benchmark/less-benchmark.js'
            },
            "sourcemap-test": {
                command: [
                    'node bin/lessc --source-map=test/sourcemaps/maps/import-map.map test/less/import.less test/sourcemaps/import.css',
                    'node bin/lessc --source-map test/less/sourcemaps/basic.less test/sourcemaps/basic.css'
                ].join('&&')
            }
        },

        browserify: {
            browser: {
                src: ['./lib/less-browser/bootstrap.js'],
                options: {
                    exclude: ["promise"],
                    require: ["promise/polyfill.js"],
                    browserifyOptions: {
                        standalone: 'less'
                    }
                },
                dest: 'tmp/less.js'
            }
        },
        concat: {
            options: {
                stripBanners: 'all',
                banner: '<%= meta.banner %>'
            },
            browsertest: {
                src: COMPRESS_FOR_TESTS ? '<%= uglify.test.dest %>' : '<%= browserify.browser.dest %>',
                dest: 'test/browser/less.js'
            },
            dist: {
                src: '<%= browserify.browser.dest %>',
                dest: 'dist/less.js'
            },
            // Rhino
            rhino: {
                options: {
                    banner: '/* Less.js v<%= pkg.version %> RHINO | <%= meta.copyright %>, <%= pkg.author.name %> <<%= pkg.author.email %>> */\n\n',
                    footer: '' // override task-level footer
                },
                src: ['<%= build.rhino %>'],
                dest: 'dist/less-rhino.js'
            },
            // lessc for Rhino
            rhinolessc: {
                options: {
                    banner: '/* Less.js v<%= pkg.version %> RHINO | <%= meta.copyright %>, <%= pkg.author.name %> <<%= pkg.author.email %>> */\n\n',
                    footer: '' // override task-level footer
                },
                src: ['<%= build.rhinolessc %>'],
                dest: 'dist/lessc-rhino.js'
            }
        },

        uglify: {
            options: {
                banner: '<%= meta.banner %>',
                mangle: true,
	            compress: {
	                pure_getters: true
	            }
            },
            dist: {
                src: ['<%= concat.dist.dest %>'],
                dest: 'dist/less.min.js'
            },
	        test: {
		        src: '<%= browserify.browser.dest %>',
		        dest: 'tmp/less.min.js'
	        }
        },

        jshint: {
            options: {jshintrc: '.jshintrc'},
            files: {
                src: [
                    'Gruntfile.js',
                    'lib/less/**/*.js',
                    'lib/less-node/**/*.js',
                    'lib/less-browser/**/*.js',
                    'lib/less-rhino/**/*.js',
                    'bin/lessc'
                ]
            }
        },

        connect: {
            server: {
                options: {
                    port: 8081
                }
            }
        },

        jasmine: {
            options: {
                keepRunner: true,
                host: 'http://localhost:8081/',
                vendor: ['test/browser/jasmine-jsreporter.js', 'test/browser/common.js', 'test/browser/less.js'],
                template: 'test/browser/test-runner-template.tmpl'
            },
            main: {
                // src is used to build list of less files to compile
                src: ['test/less/*.less', '!test/less/javascript.less', '!test/less/urls.less', '!test/less/empty.less'],
                options: {
                    helpers: 'test/browser/runner-main-options.js',
                    specs: 'test/browser/runner-main-spec.js',
                    outfile: 'tmp/browser/test-runner-main.html'
                }
            },
            legacy: {
                src: ['test/less/legacy/*.less'],
                options: {
                    helpers: 'test/browser/runner-legacy-options.js',
                    specs: 'test/browser/runner-legacy-spec.js',
                    outfile: 'tmp/browser/test-runner-legacy.html'
                }
            },
            strictUnits: {
                src: ['test/less/strict-units/*.less'],
                options: {
                    helpers: 'test/browser/runner-strict-units-options.js',
                    specs: 'test/browser/runner-strict-units-spec.js',
                    outfile: 'tmp/browser/test-runner-strict-units.html'
                }
            },
            errors: {
                src: ['test/less/errors/*.less', '!test/less/errors/javascript-error.less'],
                options: {
                    timeout: 20000,
                    helpers: 'test/browser/runner-errors-options.js',
                    specs: 'test/browser/runner-errors-spec.js',
                    outfile: 'tmp/browser/test-runner-errors.html'
                }
            },
            noJsErrors: {
                src: ['test/less/no-js-errors/*.less'],
                options: {
                    helpers: 'test/browser/runner-no-js-errors-options.js',
                    specs: 'test/browser/runner-no-js-errors-spec.js',
                    outfile: 'tmp/browser/test-runner-no-js-errors.html'
                }
            },
            browser: {
                src: ['test/browser/less/*.less'],
                options: {
                    helpers: 'test/browser/runner-browser-options.js',
                    specs: 'test/browser/runner-browser-spec.js',
                    outfile: 'tmp/browser/test-runner-browser.html'
                }
            },
            relativeUrls: {
                src: ['test/browser/less/relative-urls/*.less'],
                options: {
                    helpers: 'test/browser/runner-relative-urls-options.js',
                    specs: 'test/browser/runner-relative-urls-spec.js',
                    outfile: 'tmp/browser/test-runner-relative-urls.html'
                }
            },
            rootpath: {
                src: ['test/browser/less/rootpath/*.less'],
                options: {
                    helpers: 'test/browser/runner-rootpath-options.js',
                    specs: 'test/browser/runner-rootpath-spec.js',
                    outfile: 'tmp/browser/test-runner-rootpath.html'
                }
            },
            rootpathRelative: {
                src: ['test/browser/less/rootpath-relative/*.less'],
                options: {
                    helpers: 'test/browser/runner-rootpath-relative-options.js',
                    specs: 'test/browser/runner-rootpath-relative-spec.js',
                    outfile: 'tmp/browser/test-runner-rootpath-relative.html'
                }
            },
            production: {
                src: ['test/browser/less/production/*.less'],
                options: {
                    helpers: 'test/browser/runner-production-options.js',
                    specs: 'test/browser/runner-production-spec.js',
                    outfile: 'tmp/browser/test-runner-production.html'
                }
            },
            modifyVars: {
                src: ['test/browser/less/modify-vars/*.less'],
                options: {
                    helpers: 'test/browser/runner-modify-vars-options.js',
                    specs: 'test/browser/runner-modify-vars-spec.js',
                    outfile: 'tmp/browser/test-runner-modify-vars.html'
                }
            },
            globalVars: {
                src: ['test/browser/less/global-vars/*.less'],
                options: {
                    helpers: 'test/browser/runner-global-vars-options.js',
                    specs: 'test/browser/runner-global-vars-spec.js',
                    outfile: 'tmp/browser/test-runner-global-vars.html'
                }
            },
            postProcessor: {
                src: ['test/browser/less/postProcessor/*.less'],
                options: {
                    helpers: 'test/browser/runner-postProcessor-options.js',
                    specs: 'test/browser/runner-postProcessor.js',
                    outfile: 'tmp/browser/test-runner-post-processor.html'
                }
            }
        },

        'saucelabs-jasmine': {
            all: {
                options: {
                    urls: ["post-processor", "global-vars", "modify-vars", "production", "rootpath-relative",
                           "rootpath", "relative-urls", "browser", "no-js-errors", "legacy", "strict-units"
                    ].map(function(testName) {
                        return "http://localhost:8081/tmp/browser/test-runner-" + testName + ".html";
                    }),
                    testname: 'Sauce Unit Test for less.js',
                    browsers: [{
                        browserName: "chrome",
                        version: '',
                        platform: 'Windows 8'
                    },
                    {
                        browserName: "firefox",
                        version: '33',
                        platform: 'Linux'
                    },
                    {
                        browserName: "iPad",
                        version: '8.0',
                        platform: 'OS X 10.9',
                        'device-orientation': 'portrait'
                    },
                    {
                        browserName: "internet explorer",
                        version: '8',
                        platform: 'Windows XP'
                    },
                    {
                        browserName: "internet explorer",
                        version: '9',
                        platform: 'Windows 7'
                    },
                    {
                        browserName: "internet explorer",
                        version: '10',
                        platform: 'Windows 7'
                    },
                    {
                        browserName: "internet explorer",
                        version: '11',
                        platform: 'Windows 8.1'
                    }],
                    sauceConfig: {
                        'record-video': process.env.TRAVIS_BRANCH !== "master",
                        'record-screenshots': process.env.TRAVIS_BRANCH !== "master",
                        'idle-timeout': 100, 'max-duration': 120,
                        build: process.env.TRAVIS_BRANCH === "master" ? process.env.TRAVIS_JOB_ID : undefined,
                        tags: [process.env.TRAVIS_BUILD_NUMBER, process.env.TRAVIS_PULL_REQUEST, process.env.TRAVIS_BRANCH]
                    },
                    throttled: 3
                }
            }
        },

        // Clean the version of less built for the tests
        clean: {
            test: ['test/browser/less.js', 'tmp'],
            "sourcemap-test": ['test/sourcemaps/*.css', 'test/sourcemaps/*.map'],
            sauce_log: ["sc_*.log"]
        }
    });

    // Load these plugins to provide the necessary tasks
    require('matchdep').filterDev('grunt-*').forEach(grunt.loadNpmTasks);

    // Actually load this plugin's task(s).
    grunt.loadTasks('build/tasks');

    // by default, run tests
    grunt.registerTask('default', [
        'test'
    ]);

    grunt.registerTask('updateBowerJson', function () {
        var bowerJson = require('./bower.json');
        bowerJson.version = grunt.config('pkg.version');
        fs.writeFileSync('./bower.json', JSON.stringify(bowerJson, null, 2));
    });

    // Release
    grunt.registerTask('dist', [
        'browserify:browser',
        'concat:dist',
        'uglify:dist',
        'updateBowerJson'
    ]);

    // Release Rhino Version
    grunt.registerTask('rhino', [
        'browserify:rhino',
        'concat:rhino',
        'concat:rhinolessc'
    ]);

    // Create the browser version of less.js
    grunt.registerTask('browsertest-lessjs', [
        'browserify:browser',
	    'uglify:test',
        'concat:browsertest'
    ]);

    // Run all browser tests
    grunt.registerTask('browsertest', [
        'browsertest-lessjs',
        'connect',
        'jasmine'
    ]);

    // setup a web server to run the browser tests in a browser rather than phantom
    grunt.registerTask('browsertest-server', [
        'browsertest-lessjs',
        'jasmine::build',
        'connect::keepalive'
    ]);

    grunt.registerTask('sauce', [
        'browsertest-lessjs',
        'jasmine::build',
        'connect',
        'sauce-after-setup'
    ]);

    // setup a web server to run the browser tests in a browser rather than phantom
    grunt.registerTask('sauce-after-setup', [
        'saucelabs-jasmine',
        'clean:sauce_log'
    ]);

    var testTasks = [
        'clean',
        'jshint',
        'shell:test',
        'browsertest'
    ];

    if (isNaN(Number(process.env.TRAVIS_PULL_REQUEST, 10)) &&
        Number(process.env.TRAVIS_NODE_VERSION) === 0.11 &&
        (process.env.TRAVIS_BRANCH === "master" || process.env.TRAVIS_BRANCH === "sauce")) {
        testTasks.push("sauce-after-setup");
    }

    // Run all tests
    grunt.registerTask('test', testTasks);

    // generate a good test environment for testing sourcemaps
    grunt.registerTask('sourcemap-test', [
        'clean:sourcemap-test',
        'shell:sourcemap-test',
        'connect::keepalive'
    ]);

    // Run benchmark
    grunt.registerTask('benchmark', [
        'shell:benchmark'
    ]);

};
