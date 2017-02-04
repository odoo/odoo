module.exports = function (grunt) {
  // Full list of files that must be included by RequireJS
  includes = [
    'jquery.select2',
    'almond',

    'jquery-mousewheel' // shimmed for non-full builds
  ];

  fullIncludes = [
    'jquery',

    'select2/compat/containerCss',
    'select2/compat/dropdownCss',

    'select2/compat/initSelection',
    'select2/compat/inputData',
    'select2/compat/matcher',
    'select2/compat/query',

    'select2/dropdown/attachContainer',
    'select2/dropdown/stopPropagation',

    'select2/selection/stopPropagation'
  ].concat(includes);

  var i18nModules = [];
  var i18nPaths = {};

  var i18nFiles = grunt.file.expand({
    cwd: 'src/js'
  }, 'select2/i18n/*.js');

  var testFiles = grunt.file.expand('tests/**/*.html');
  var testUrls = testFiles.map(function (filePath) {
    return 'http://localhost:9999/' + filePath;
  });

  var testBuildNumber = "unknown";

  if (process.env.TRAVIS_JOB_ID) {
    testBuildNumber = "travis-" + process.env.TRAVIS_JOB_ID;
  } else {
    var currentTime = new Date();

    testBuildNumber = "manual-" + currentTime.getTime();
  }

  for (var i = 0; i < i18nFiles.length; i++) {
    var file = i18nFiles[i];
    var name = file.split('.')[0];

    i18nModules.push({
      name: name
    });

    i18nPaths[name] = '../../' + name;
  }

  var minifiedBanner = '/*! Select2 <%= package.version %> | https://github.com/select2/select2/blob/master/LICENSE.md */';

  grunt.initConfig({
    package: grunt.file.readJSON('package.json'),

    clean: {
      docs: ['docs/_site']
    },

    concat: {
      'dist': {
        options: {
          banner: grunt.file.read('src/js/wrapper.start.js'),
        },
        src: [
          'dist/js/select2.js',
          'src/js/wrapper.end.js'
        ],
        dest: 'dist/js/select2.js'
      },
      'dist.full': {
        options: {
          banner: grunt.file.read('src/js/wrapper.start.js'),
        },
        src: [
          'dist/js/select2.full.js',
          'src/js/wrapper.end.js'
        ],
        dest: 'dist/js/select2.full.js'
      }
    },

    connect: {
      tests: {
        options: {
          base: '.',
          hostname: '127.0.0.1',
          port: 9999
        }
      }
    },

    uglify: {
      'dist': {
        src: 'dist/js/select2.js',
        dest: 'dist/js/select2.min.js',
        options: {
          banner: minifiedBanner
        }
      },
      'dist.full': {
        src: 'dist/js/select2.full.js',
        dest: 'dist/js/select2.full.min.js',
        options: {
          banner: minifiedBanner
        }
      }
    },

    qunit: {
      all: {
        options: {
          urls: testUrls
        }
      }
    },

    'saucelabs-qunit': {
      all: {
        options: {
          build: testBuildNumber,
          tags: ['tests', 'qunit'],
          urls: testUrls,
          testname: 'QUnit test for Select2',
          browsers: [
            {
              browserName: 'internet explorer',
              version: '8'
            },
            {
              browserName: 'internet explorer',
              version: '9'
            },
            {
              browserName: 'internet explorer',
              version: '10'
            },
            {
              browserName: 'internet explorer',
              version: '11'
            },

            {
              browserName: 'firefox',
              platform: 'linux'
            },

            {
              browserName: 'chrome'
            },

            {
              browserName: 'opera',
              version: '12',
              platform: 'linux'
            }
          ]
        }
      }
    },

    'gh-pages': {
      options: {
        base: 'docs',
        branch: 'master',
        clone: 'node_modules/grunt-gh-pages/repo',
        message: 'Updated docs with master',
        push: true,
        repo: 'git@github.com:select2/select2.github.io.git'
      },
      src: '**'
    },

    jekyll: {
      options: {
        src: 'docs',
        dest: 'docs/_site'
      },
      build: {
        d: null
      },
      serve: {
        options: {
          serve: true,
          watch: true
        }
      }
    },

    jshint: {
      options: {
        jshintrc: true
      },
      code: {
        src: ['src/js/**/*.js']
      },
      tests: {
        src: ['tests/**/*.js']
      }
    },

    sass: {
      dist: {
        options: {
          outputStyle: 'compressed'
        },
        files: {
          'dist/css/select2.min.css': [
            'src/scss/core.scss',
            'src/scss/theme/default/layout.css'
          ]
        }
      },
      dev: {
        options: {
          outputStyle: 'nested'
        },
        files: {
          'dist/css/select2.css': [
            'src/scss/core.scss',
            'src/scss/theme/default/layout.css'
          ]
        }
      }
    },

    symlink: {
      docs: {
        cwd: 'dist',
        expand: true,
        overwrite: false,
        src: [
          '*'
        ],
        dest: 'docs/dist',
        filter: 'isDirectory'
      }
    },

    requirejs: {
      'dist': {
        options: {
          baseUrl: 'src/js',
          optimize: 'none',
          name: 'select2/core',
          out: 'dist/js/select2.js',
          include: includes,
          namespace: 'S2',
          paths: {
            'almond': require.resolve('almond').slice(0, -3),
            'jquery': 'jquery.shim',
            'jquery-mousewheel': 'jquery.mousewheel.shim'
          },
          wrap: {
            startFile: 'src/js/banner.start.js',
            endFile: 'src/js/banner.end.js'
          }
        }
      },
      'dist.full': {
        options: {
          baseUrl: 'src/js',
          optimize: 'none',
          name: 'select2/core',
          out: 'dist/js/select2.full.js',
          include: fullIncludes,
          namespace: 'S2',
          paths: {
            'almond': require.resolve('almond').slice(0, -3),
            'jquery': 'jquery.shim',
            'jquery-mousewheel': require.resolve('jquery-mousewheel').slice(0, -3)
          },
          wrap: {
            startFile: 'src/js/banner.start.js',
            endFile: 'src/js/banner.end.js'
          }
        }
      },
      'i18n': {
        options: {
          baseUrl: 'src/js/select2/i18n',
          dir: 'dist/js/i18n',
          paths: i18nPaths,
          modules: i18nModules,
          namespace: 'S2',
          wrap: {
            start: minifiedBanner + grunt.file.read('src/js/banner.start.js'),
            end: grunt.file.read('src/js/banner.end.js')
          }
        }
      }
    },

    watch: {
      js: {
        files: [
          'src/js/select2/**/*.js',
          'tests/**/*.js'
        ],
        tasks: [
          'compile',
          'test',
          'minify'
        ]
      },
      css: {
        files: [
          'src/scss/**/*.scss'
        ],
        tasks: [
          'compile',
          'minify'
        ]
      }
    }
  });

  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-connect');
  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.loadNpmTasks('grunt-contrib-qunit');
  grunt.loadNpmTasks('grunt-contrib-requirejs');
  grunt.loadNpmTasks('grunt-contrib-symlink');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-watch');

  grunt.loadNpmTasks('grunt-gh-pages');
  grunt.loadNpmTasks('grunt-jekyll');
  grunt.loadNpmTasks('grunt-saucelabs');
  grunt.loadNpmTasks('grunt-sass');

  grunt.registerTask('default', ['compile', 'test', 'minify']);

  grunt.registerTask('compile', [
    'requirejs:dist', 'requirejs:dist.full', 'requirejs:i18n',
    'concat:dist', 'concat:dist.full',
    'sass:dev'
  ]);
  grunt.registerTask('minify', ['uglify', 'sass:dist']);
  grunt.registerTask('test', ['connect:tests', 'qunit', 'jshint']);

  var ciTasks = [];

  ciTasks.push('compile')
  ciTasks.push('connect:tests');

  // Can't run Sauce Labs tests in pull requests
  if (process.env.TRAVIS_PULL_REQUEST == 'false') {
    ciTasks.push('saucelabs-qunit');
  }

  ciTasks.push('qunit');
  ciTasks.push('jshint');

  grunt.registerTask('ci', ciTasks);

  grunt.registerTask('docs', ['symlink:docs', 'jekyll:serve']);

  grunt.registerTask('docs-release', ['default', 'clean:docs', 'gh-pages']);
};
