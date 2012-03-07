require 'rubygems'
require 'jammit'
require 'fileutils'

desc "Use Jammit to compile the multiple versions of Visual Search"
task :build do
  $VS_MIN = false
  Jammit.package!({
    :config_path   => "assets.yml",
    :output_folder => "build"
  })
  
  $VS_MIN = true
  Jammit.package!({
    :config_path   => "assets.yml",
    :output_folder => "build-min"
  })
  
  # Move the JSTs back to lib to accomodate the demo page.
  FileUtils.mv("build/visualsearch_templates.js", "lib/js/templates/templates.js")
      
  # Fix image url paths.
  ['build', 'build-min'].each do |build|
    File.open("#{build}/visualsearch.css", 'r+') do |file|
      css = file.read
      css.gsub!(/url\((.*?)images\/embed\/icons/, 'url(../images/embed/icons')
      file.rewind
      file.write(css)
      file.truncate(css.length)
    end
  end
end

desc "Build the docco documentation"
task :docs do
  sh "docco lib/js/*.js lib/js/**/*.js"
end
