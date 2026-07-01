module.exports = function(grunt) {
	'use strict';

	grunt.initConfig({
		clean: ['dist'],
		uglify: {
			options: {
				preserveComments: 'some',
				sourceMap: true
			},
			build: {
				expand: true,
				cwd: 'js',
				src: ['**/*.js', ['!**/*.min.js']],
				dest: 'js',
				ext: '.min.js',
			}
		},
		cssmin: {
			options: {
				keepBreaks: true
			},
			build: {
				expand: true,
				cwd: 'css',
				src: ['**/*.css', ['!**/*.min.css']],
				dest: 'css',
				ext: '.min.css',
			}
		}
	});
	grunt.loadNpmTasks('grunt-contrib-clean');
	grunt.loadNpmTasks('grunt-contrib-uglify');
	grunt.loadNpmTasks('grunt-contrib-cssmin');
	grunt.registerTask('default', ['clean', 'uglify', 'cssmin']);

};