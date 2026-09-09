Website Snippet & Blocks
========================

The building blocks appear in the edit bar of the website builder. These
prebuilt HTML blocks allow the designer to easily generate content on a page
(drag and drop). Snippets bind an OWL-based runtime on custom parts of the
HTML code according to their selector, both on the public-facing page
(``Interaction``) and inside the page-builder/editor (``BuilderAction``). The
snippets are also used to create the drop zone.


Blocks
++++++

The ``blocks`` are the HTML code that can be dropped in the page. The blocks
consist of a body and a thumbnail:
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


Public-site runtime: Interaction
+++++++++++++++++++++++++++++++

Each snippet's public-facing (non-editor) behaviour is implemented as an
``Interaction`` (``@web/public/interaction``), registered in the
``public.interactions`` registry category. An ``Interaction`` subclass
declares:

- ``static selector``: the CSS selector on which the interaction is
  instantiated (one instance per matching element).
- ``dynamicSelectors``: named lazy selectors (evaluated per-instance),
  usable as keys in ``dynamicContent``.
- ``dynamicContent``: a declarative map from a selector (or one of the
  ``dynamicSelectors`` names) to ``t-on-*``/``t-att-*``-style bindings,
  the interaction's equivalent of an OWL template.
- ``setup()``: called once, before ``start()``, to initialize instance state.
- ``start()``: called when the interaction is mounted on a matching element.
- ``destroy()``: called when the interaction is torn down (element removed,
  edit-mode toggle, preview restart); any listener/observer registered
  outside of ``dynamicContent`` (e.g. a ``ResizeObserver``) must be released
  here or via ``this.registerCleanup(...)``.

See ``static/src/interactions/`` for examples, and
``static/src/js/content/`` for content-only interactions.


Page-builder/editor: BuilderAction
+++++++++++++++++++++++++++++++++

Inside the page-builder/editor, a snippet's customization options are
implemented as one or more ``BuilderAction`` subclasses (``@html_builder/core/
builder_action``), registered per plugin via the ``builder_actions`` resource
and driven by ``BuilderComponents`` declared in the option's XML template
(``BuilderSelect``, ``BuilderButtonGroup``, ``BuilderCheckbox``,
``BuilderTextInput``, ...). A ``BuilderAction`` subclass implements:

- ``setup()``: called once, after dependencies/services are assigned.
- ``apply(context)``: applies the action to ``context.editingElement``; called
  on preview, on confirm, and (unless ``clean`` is defined) on cancel/undo.
- ``getValue(context)``: returns the action's current value, for
  input-like components.
- ``isApplied(context)``: whether the action is currently active, for
  toggle-like components.
- ``prepare(context)``: optional async data-loading hook, called before the
  component mounts/updates.

See ``static/src/builder/plugins/options/`` for examples.


t-snippet and data-snippet
+++++++++++++++++++++++++

User can call a snippet template with qweb or inside a demo page.

e.g.:

<template id="website.name_of_the_snippet" name="Name of the snippet">
  <hr/>
</template>

Inside #snippet_structure for e.g.: ``<t t-snippet="website.name_of_the_snippet" t-thumbnail="/image_path"/>``
The container of the snippet became not editable (with branding)

Inside a demo page call the snippet with: ``<div data-oe-call="website.name_of_the_template"/>``
The snippets are loaded in one time by js and the page stay editable.
