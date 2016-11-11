/* Copyright 2014 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

exports.parseAdobeCMap = function (content) {
  var m = /(\bbegincmap\b[\s\S]*?)\bendcmap\b/.exec(content);
  if (!m) {
    throw new Error('cmap was not found');
  }

  var body = m[1].replace(/\r\n?/g, '\n');
  var result = {
    type: 1,
    wmode: 0,
    comment: 'Copyright 1990-2009 Adobe Systems Incorporated.\nAll rights reserved.\nSee ./LICENSE',
    usecmap: null,
    body: []
  };
  m = /\/CMapType\s+(\d+)+\s+def\b/.exec(body);
  result.type = +m[1];
  m = /\/WMode\s+(\d+)+\s+def\b/.exec(body);
  result.wmode = +m[1];
  m = /\/([\w\-]+)\s+usecmap\b/.exec(body);
  if (m) {
    result.usecmap = m[1];
  }
  var re = /(\d+)\s+(begincodespacerange|beginnotdefrange|begincidchar|begincidrange|beginbfchar|beginbfrange)\n([\s\S]*?)\n(endcodespacerange|endnotdefrange|endcidchar|endcidrange|endbfchar|endbfrange)/g;
  while (m = re.exec(body)) {
    var lines = m[3].toLowerCase().split('\n');
    var m2;
    switch (m[2]) {
      case 'begincodespacerange':
        result.body.push({
          type: 0,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+<(\w+)>/.exec(line);
            return {start: m[1], end: m[2]};
          })
        });
        break;
      case 'beginnotdefrange':
        result.body.push({
          type: 1,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+<(\w+)>\s+(\d+)/.exec(line);
            return {start: m[1], end: m[2], code: +m[3]};
          })
        });
        break;
      case 'begincidchar':
        result.body.push({
          type: 2,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+(\d+)/.exec(line);
            return {char: m[1], code: +m[2]};
          })
        });
        break;
      case 'begincidrange':
        result.body.push({
          type: 3,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+<(\w+)>\s+(\d+)/.exec(line);
            return {start: m[1], end: m[2], code: +m[3]};
          })
        });
        break;
      case 'beginbfchar':
        result.body.push({
          type: 4,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+<(\w+)>/.exec(line);
            return {char: m[1], code: m[2]};
          })
        });
        break;
      case 'beginbfrange':
        result.body.push({
          type: 5,
          items: lines.map(function (line) {
            var m = /<(\w+)>\s+<(\w+)>\s+<(\w+)>/.exec(line);
            return {start: m[1], end: m[2], code: m[3]};
          })
        });
        break;
    }
  }

  return result;
};