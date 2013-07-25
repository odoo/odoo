module.exports = function(grunt) {

  grunt.initConfig({
    jshint: {
      files: ['static/src/**/*.js', 'static/test/**/*.js'],
      options: {
        sub: true, //[] instead of .
        evil: true, //eval
        laxbreak: true, //unsafe line breaks
        loopfunc: true, // functions in loops
      },
    }
  });

  grunt.loadNpmTasks('grunt-contrib-jshint');

  grunt.registerTask('test', ['jshint']);

  grunt.registerTask('default', ['jshint']);

};