module.exports = function(grunt) {

  grunt.initConfig({
    jshint: {
      files: ['static/src/**/*.js'],
      options: {
        sub: true, //[] instead of .
        asi: true, //semicolons
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