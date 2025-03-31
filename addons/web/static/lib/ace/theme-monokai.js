define("ace/theme/monokai-css", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  module.exports =
    ".ace-monokai .ace_gutter {\n  background: #2F3129;\n  color: #8F908A\n}\n\n.ace-monokai .ace_print-margin {\n  width: 1px;\n  background: #555651\n}\n\n.ace-monokai {\n  background-color: #272822;\n  color: #F8F8F2\n}\n\n.ace-monokai .ace_cursor {\n  color: #F8F8F0\n}\n\n.ace-monokai .ace_marker-layer .ace_selection {\n  background: #49483E\n}\n\n.ace-monokai.ace_multiselect .ace_selection.ace_start {\n  box-shadow: 0 0 3px 0px #272822;\n}\n\n.ace-monokai .ace_marker-layer .ace_step {\n  background: rgb(102, 82, 0)\n}\n\n.ace-monokai .ace_marker-layer .ace_bracket {\n  margin: -1px 0 0 -1px;\n  border: 1px solid #49483E\n}\n\n.ace-monokai .ace_marker-layer .ace_active-line {\n  background: #202020\n}\n\n.ace-monokai .ace_gutter-active-line {\n  background-color: #272727\n}\n\n.ace-monokai .ace_marker-layer .ace_selected-word {\n  border: 1px solid #49483E\n}\n\n.ace-monokai .ace_invisible {\n  color: #52524d\n}\n\n.ace-monokai .ace_entity.ace_name.ace_tag,\n.ace-monokai .ace_keyword,\n.ace-monokai .ace_meta.ace_tag,\n.ace-monokai .ace_storage {\n  color: #F92672\n}\n\n.ace-monokai .ace_punctuation,\n.ace-monokai .ace_punctuation.ace_tag {\n  color: #fff\n}\n\n.ace-monokai .ace_constant.ace_character,\n.ace-monokai .ace_constant.ace_language,\n.ace-monokai .ace_constant.ace_numeric,\n.ace-monokai .ace_constant.ace_other {\n  color: #AE81FF\n}\n\n.ace-monokai .ace_invalid {\n  color: #F8F8F0;\n  background-color: #F92672\n}\n\n.ace-monokai .ace_invalid.ace_deprecated {\n  color: #F8F8F0;\n  background-color: #AE81FF\n}\n\n.ace-monokai .ace_support.ace_constant,\n.ace-monokai .ace_support.ace_function {\n  color: #66D9EF\n}\n\n.ace-monokai .ace_fold {\n  background-color: #A6E22E;\n  border-color: #F8F8F2\n}\n\n.ace-monokai .ace_storage.ace_type,\n.ace-monokai .ace_support.ace_class,\n.ace-monokai .ace_support.ace_type {\n  font-style: italic;\n  color: #66D9EF\n}\n\n.ace-monokai .ace_entity.ace_name.ace_function,\n.ace-monokai .ace_entity.ace_other,\n.ace-monokai .ace_entity.ace_other.ace_attribute-name,\n.ace-monokai .ace_variable {\n  color: #A6E22E\n}\n\n.ace-monokai .ace_variable.ace_parameter {\n  font-style: italic;\n  color: #FD971F\n}\n\n.ace-monokai .ace_string {\n  color: #E6DB74\n}\n\n.ace-monokai .ace_comment {\n  color: #75715E\n}\n\n.ace-monokai .ace_indent-guide {\n  background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAEklEQVQImWPQ0FD0ZXBzd/wPAAjVAoxeSgNeAAAAAElFTkSuQmCC) right repeat-y\n}\n\n.ace-monokai .ace_indent-guide-active {\n  background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAEklEQVQIW2PQ1dX9zzBz5sz/ABCcBFFentLlAAAAAElFTkSuQmCC) right repeat-y;\n}\n";
});

define("ace/theme/monokai", [
  "require",
  "exports",
  "module",
  "ace/theme/monokai-css",
  "ace/lib/dom",
], function (require, exports, module) {
  exports.isDark = true;
  exports.cssClass = "ace-monokai";
  exports.cssText = require("./monokai-css");
  var dom = require("../lib/dom");
  dom.importCssString(exports.cssText, exports.cssClass, false);
});
(function () {
  window.require(["ace/theme/monokai"], function (m) {
    if (typeof module == "object" && typeof exports == "object" && module) {
      module.exports = m;
    }
  });
})();
