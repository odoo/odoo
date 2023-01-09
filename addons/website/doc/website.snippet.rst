Website Snippet & Blocks
========================

The building blocks appear in the edit bar website. These prebuilt html block
allowing the designer to easily generate content on a page (drag and drop).
Snippets bind javascript object on custom part html code according to their
selector (jQuery) and javascript object. The snippets is also used to create
the drop zone.


Building Blocks
+++++++++++++++

Overwrite ``_getSnippetURL`` to set an other file to load the snippets (use by
website_mail for example)
Overwrite ``_computeSelectorFunctions`` to enable or disable other snippets. By default
the builder check if the node or his parent have the attribute data-oe-model

Trigger:
- ``snippet-dropped`` is triggered on ``#oe_snippets`` whith $target as attribute when a snippet is dropped
- ``snippet-activated`` is triggered on ``#oe_snippets`` (and on snippet) when a snippet is activated


Blocks
++++++

The ``blocks`` are the HTML code that can be drop in the page. The blocks consist
of a body and a thumbnail:
 - thumbnail:
   (have class ``oe_snippet_thumbnail``) contains a picture and a text used to
   display a preview in the edit bar that contains all the block list
 - body:
   (have class ``oe_snippet_body``) is the real part dropped in the page. The class
   ``oe_snippet_body`` is removed before inserting the block in the page.
e.g.:
    <div>
        <div class="oe_snippet_thumbnail">
            <img class="oe_snippet_thumbnail_img" src="...image src..."/>
            <span class="oe_snippet_thumbnail_title">...Block Name...</span>
        </div>
        <div class="oe_snippet_body">
            <!--
                The block with class 'oe_snippet_body' is inserted in the page.
                This class is removed when the block is dropped.
                The block can be made of any html tag and content. -->
        </div>
    </div>


Editor
++++++

The ``editor`` is the frame placed above the block being edited who contains buttons
(move, delete, clone) and customize menu. The ``editor`` load ``options`` based on
selectors defined in snippets


Options
+++++++

The ``option`` is the javascript object used to customize the HTML code.

Object:
 - this.``$target``:
   block html inserted inside the page
 - this.``$el``:
   html li list of this options
 - this.``$overlay``:
   html editor overlay who content resize bar, customize menu...

Methods:
 - ``_setActive``:
   highlight the customize menu item when the user click on customize, and click on
   an item.
 - ``start``:
   called when the editor is created on the DOM
 - ``onFocus``:
   called when the user click inside the block inserted in page and when the
   user drop on block into the page
 - ``onBlur``:
   called when the user click outside the block inserted in page, if the block
   is focused
 - ``onClone``:
   called when the snippet is duplicate
 - ``onRemove``:
   called when the snippet is removed (dom is removing after this tigger)
 - ``onBuilt:
   called just after that a thumbnail is drag and dropped into a drop zone.
   The content is already inserted in the page.
 - ``cleanForSave``:
   is called just before to save the vue. Sometime it's important to remove or add
   some datas (contentEditable, added classes to a running animation...)

Customize Methods:
All javascript option can defiend method call from the template on mouse over, on
click or to reset the default value (<li data-your_js_method="your_value"><a>...</a></li>).
The method receive the variable type (``over``, ``click`` or ``reset``), the method
value and the jQuery object of the HTML li item. (can be use for multi methods)

By default to custom method are defined:

 - ``check_class(type, className, $li)``:
   li must have data-check_class="a_classname_for_test" to call this method. This method
   toggle the className on $target
 - ``selectClass(type, className, $li)``:
   This method remove all other selectClass value (for this option) and add this current ClassName



Snippet
+++++++

The ``snippets`` are the HTML code to defined the drop zone and the linked javascript object.
All HTML li tag defined inside the snippets HTML are insert into the customize menu. All
data attributes is optional:

- ``data-selector``:
  Apply options on all The part of html who match with this jQuery selector.
  E.g.: If the selector is div, all div will be selected and can be highlighted and assigned an editor.
- ``data-js``:
  javascript to call when the ``editor`` is loaded
- ``data-drop-in``:
  The html part can be insert or move beside the selected html block (jQuery selector)
- ``data-drop-near``:
  The html part can be insert or move inside the selected html block (jQuery selector)
- HTML content like <li data-your_js_method="your_value"><a>...</a></li>:
  List of HTML li menu items displayed in customize menu. If the li tag have datas the methods are
  automatically called
- ``no-check``:
  The selectors are automatically compute to have elements inside the branding. If you use this option
  the check is not apply (for e.g.: to have a snippet for the grid view of website_sale)

t-snippet and data-snippet
++++++++++++++++++++++++++

User can call a snippet template with qweb or inside a demo page.

e.g.:

<template id="website.name_of_the_snippet" name="Name of the snippet">
  <hr/>
</template>

Inside #snippet_structure for e.g.: ``<t t-snippet="website.name_of_the_snippet" t-thumbnail="/image_path"/>``
The container of the snippet became not editable (with branding)

Inside a demo page call the snippet with: ``<div data-oe-call="website.name_of_the_template"/>``
The snippets are loaded in one time by js and the page stay editable.

More
++++

- Use the class ``o_not_editable`` to prevent the editing of an area.
