/** @odoo-module **/

import loaderFunctions from "web_editor.loader";

loaderFunctions.createWysiwyg = (parent, options) => {
  const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
  return new Wysiwyg(parent, options.wysiwygOptions);
};
