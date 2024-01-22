Double check that you have no inherited view that remove ``options`` you set on a field !
If nothing works, add a debugger in the first line of ``_search method`` and enable debug mode in Odoo. When you write something in a many2one field, javascript debugger should pause. If not verify your installation.

- Instead of making the tags rectangle clickable, I think it's better to put the text as a clickable link, so we will get a consistent behaviour/aspect with other clickable elements (many2one...).
- In edit mode, it would be great to add an icon like the one on many2one fields to allow to open the many2many in a popup window.
- Include this feature as a configurable option via parameter to have this behaviour by default in all many2many tags.
