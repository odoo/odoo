module.exports = function(grunt) {

    grunt.initConfig({
        jshint: {
            src: ['static/src/**/*.js', 'static/test/**/*.js'],
            options: {
                sub: true, //[] instead of .
                evil: true, //eval
                laxbreak: true, //unsafe line breaks
            },
        },
        sass: {
            dev: {
                options: {
                    style: "expanded",
                },
                files: {
                    "static/src/css/base.css": "static/src/css/base.sass",
                }
            }
        },
        watch: {
            sass: {
                files: ["static/src/css/base.sass"],
                tasks: ['sass']
            },
        }
    });

    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-contrib-sass');
    grunt.loadNpmTasks('grunt-contrib-watch');

    grunt.registerTask('gen', ["sass"]);
    grunt.registerTask('watcher', ["gen", "watch"]);
    grunt.registerTask('test', []);

    grunt.registerTask('default', ['jshint']);

};