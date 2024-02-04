* Support extra attributes on each field cell via `field_extra_attrs` param.
  We could set a cell as not editable, required or readonly for instance.
  The `readonly` case will also give the ability
  to click on m2o to open related records.

* Support limit total records in the matrix. Ref: https://github.com/OCA/web/issues/901

* Support cell traversal through keyboard arrows.

* Entering the widget from behind by pressing ``Shift+TAB`` in your keyboard
  will enter into the 1st cell until https://github.com/odoo/odoo/pull/26490
  is merged.

* Support extra invisible fields inside each cell.

* Support kanban mode. Current behaviour forces list mode.
