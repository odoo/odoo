The types folder is a way to get better autocompletion for iife imported libs.
It uses typescript declarations to inform the IDE about some global vars and their types and methods.
For this to work, you need to have the tsconfig.json file with the typeRoots argument set to this folder. (should be done for you with the CLI command generating the tsconfig)

Adding new libs to this can be trivial or not.
It can be a one liner or the addition of a complete typescript declaration file.
It should be handled by someone that knows what they are doing.

Note that if odoo adds methods to a lib, manual additions must likely will be required to get full automcompletion.
Just like the qunit lib.
