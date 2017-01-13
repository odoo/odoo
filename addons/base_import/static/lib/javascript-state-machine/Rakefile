
desc "create minified version of state-machine.js"
task :minify do
  require File.expand_path(File.join(File.dirname(__FILE__), 'minifier/minifier'))
  Minifier.enabled = true
  Minifier.minify('state-machine.js')
end

