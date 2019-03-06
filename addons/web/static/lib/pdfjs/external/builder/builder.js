/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* jshint node:true */
/* globals cp, ls, test */

'use strict';

require('shelljs/make');
var fs = require('fs'),
    path = require('path'),
    vm = require('vm');

/**
 * A simple preprocessor that is based on the firefox preprocessor
 * see (https://developer.mozilla.org/en/Build/Text_Preprocessor).  The main
 * difference is that this supports a subset of the commands and it supports
 * preproccesor commands in html style comments.
 * Currently Supported commands:
 * - if
 * - else
 * - endif
 * - include
 * - expand
 */
function preprocess(inFilename, outFilename, defines) {
  // TODO make this really read line by line.
  var lines = fs.readFileSync(inFilename).toString().split('\n');
  var totalLines = lines.length;
  var out = '';
  var i = 0;
  function readLine() {
    if (i < totalLines) {
      return lines[i++];
    }
    return null;
  }
  var writeLine = (typeof outFilename === 'function' ? outFilename :
    function(line) {
      out += line + '\n';
    });
  function include(file) {
    var realPath = fs.realpathSync(inFilename);
    var dir = path.dirname(realPath);
    preprocess(path.join(dir, file), writeLine, defines);
  }
  function expand(line) {
    line = line.replace(/__[\w]+__/g, function(variable) {
      variable = variable.substring(2, variable.length - 2);
      if (variable in defines) {
        return defines[variable];
      }
      return '';
    });
    writeLine(line);
  }

  var s, state = 0, stack = [];
  var control =
    /^(?:\/\/|<!--)\s*#(if|else|endif|expand|include)(?:\s+(.*?)(?:-->)?$)?/;
  var lineNumber = 0;
  while ((s = readLine()) !== null) {
    ++lineNumber;
    var m = control.exec(s);
    if (m) {
      switch (m[1]) {
        case 'if':
          stack.push(state);
          try {
            state = vm.runInNewContext(m[2], defines) ? 3 : 1;
          } catch (e) {
            console.error('Could not evalute line \'' + m[2] + '\' at ' +
                          fs.realpathSync(inFilename) + ':' + lineNumber);
            throw e;
          }
          break;
        case 'else':
          state = state === 1 ? 3 : 2;
          break;
        case 'endif':
          state = stack.pop();
          break;
        case 'expand':
          if (state === 0 || state === 3) {
            expand(m[2]);
          }
          break;
        case 'include':
          if (state === 0 || state === 3) {
            include(m[2]);
          }
          break;
      }
    } else {
      if (state === 0) {
        writeLine(s);
      } else if (state === 3) {
        writeLine(s.replace(/^\/\/|^<!--|-->/g, '  '));
      }
    }
  }
  if (state !== 0 || stack.length !== 0) {
    throw new Error('Missing endif in preprocessor.');
  }
  if (typeof outFilename !== 'function') {
    fs.writeFileSync(outFilename, out);
  }
}
exports.preprocess = preprocess;

var deprecatedInMozcentral = new RegExp('(^|\\W)(' + [
    '-moz-box-sizing',
    '-moz-grab',
    '-moz-grabbing'
  ].join('|') + ')');

function preprocessCSS(mode, source, destination) {
  function hasPrefixedFirefox(line) {
    return (/(^|\W)-(ms|o|webkit)-\w/.test(line));
  }

  function hasPrefixedMozcentral(line) {
    return (/(^|\W)-(ms|o|webkit)-\w/.test(line) ||
            deprecatedInMozcentral.test(line));
  }

  function expandImports(content, baseUrl) {
    return content.replace(/^\s*@import\s+url\(([^\)]+)\);\s*$/gm,
        function(all, url) {
      var file = path.join(path.dirname(baseUrl), url);
      var imported = fs.readFileSync(file, 'utf8').toString();
      return expandImports(imported, file);
    });
  }

  function removePrefixed(content, hasPrefixedFilter) {
    var lines = content.split(/\r?\n/g);
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];
      if (!hasPrefixedFilter(line)) {
        i++;
        continue;
      }
      if (/\{\s*$/.test(line)) {
        var bracketLevel = 1;
        var j = i + 1;
        while (j < lines.length && bracketLevel > 0) {
          var checkBracket = /([{}])\s*$/.exec(lines[j]);
          if (checkBracket) {
            if (checkBracket[1] === '{') {
              bracketLevel++;
            } else if (lines[j].indexOf('{') < 0) {
              bracketLevel--;
            }
          }
          j++;
        }
        lines.splice(i, j - i);
      } else if (/[};]\s*$/.test(line)) {
        lines.splice(i, 1);
      } else {
        // multiline? skipping until next directive or bracket
        do {
          lines.splice(i, 1);
        } while (i < lines.length &&
                 !/\}\s*$/.test(lines[i]) &&
                 lines[i].indexOf(':') < 0);
        if (i < lines.length && /\S\s*}\s*$/.test(lines[i])) {
          lines[i] = lines[i].substr(lines[i].indexOf('}'));
        }
      }
      // collapse whitespaces
      while (lines[i] === '' && lines[i - 1] === '') {
        lines.splice(i, 1);
      }
    }
    return lines.join('\n');
  }

  if (!mode) {
    throw new Error('Invalid CSS preprocessor mode');
  }

  var content = fs.readFileSync(source, 'utf8').toString();
  content = expandImports(content, source);
  if (mode === 'mozcentral' || mode === 'firefox') {
    content = removePrefixed(content, mode === 'mozcentral' ?
                             hasPrefixedMozcentral : hasPrefixedFirefox);
  }
  fs.writeFileSync(destination, content);
}
exports.preprocessCSS = preprocessCSS;

/**
 * Simplifies common build steps.
 * @param {object} setup
 *        .defines defines for preprocessors
 *        .copy array of arrays of source and destination pairs of files to copy
 *        .preprocess array of arrays of source and destination pairs of files
 *                    run through preprocessor.
 */
function build(setup) {
  var defines = setup.defines;

  setup.copy.forEach(function(option) {
    var source = option[0];
    var destination = option[1];
    cp('-R', source, destination);
  });

  setup.preprocess.forEach(function(option) {
    var sources = option[0];
    var destination = option[1];

    sources = ls('-R', sources);
    sources.forEach(function(source) {
      // ??? Warn if the source is wildcard and dest is file?
      var destWithFolder = destination;
      if (test('-d', destination)) {
        destWithFolder += '/' + path.basename(source);
      }
      preprocess(source, destWithFolder, defines);
    });
  });

  (setup.preprocessCSS || []).forEach(function(option) {
    var mode = option[0];
    var source = option[1];
    var destination = option[2];
    preprocessCSS(mode, source, destination);
  });
}
exports.build = build;

function getWorkerSrcFiles(filePath) {
  var src = fs.readFileSync(filePath).toString();
  var reSrcFiles = /var\s+otherFiles\s*=\s*(\[[^\]]*\])/;
  var match = reSrcFiles.exec(src);
  try {
    var files = JSON.parse(match[1].replace(/'/g, '"'));
    var srcFiles = files.filter(function(name) {
      return name.indexOf('external') === -1;
    });
    var externalSrcFiles = files.filter(function(name) {
      return name.indexOf('external') > -1;
    });
    return {
      srcFiles: srcFiles,
      externalSrcFiles: externalSrcFiles
    };
  } catch(e) {
    return {};
  }
}
exports.getWorkerSrcFiles = getWorkerSrcFiles;

/**
 * Merge two defines arrays. Values in the second param will override values in
 * the first.
 */
function merge(defaults, defines) {
  var ret = {};
  for (var key in defaults) {
    ret[key] = defaults[key];
  }
  for (key in defines) {
    ret[key] = defines[key];
  }
  return ret;
}
exports.merge = merge;
