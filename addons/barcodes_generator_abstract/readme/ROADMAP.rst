* On barcode.rule model, constraint and domain system could be set between
  'type' and 'generate_model' fields.
* Cache is being cleared in a constraint in `barcode.rule`. Mutating in a
  constraint is bad practice & should be moved somewhere.
