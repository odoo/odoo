### test_isolated_install

Given the following package structure (where `\_` denotes a dependency)
<pre>
...
    \_ test_install_base
        \_ test_install_auto
        \_ test_install_fail
</pre>
Given:
* The auto-install module test_install_auto
  * Has a model override of ResCurrency that defines a new method for the class
  * Has some data that defines an IrCron record, which executes the method added in the override
* The data error module test_install_fail:
  * Has a view extension which has some bad syntax that will trigger a failure in load_data()

We want to ensure each module is installed in an isolated manner, i.e., the
failed installation of a module should not affect the state of another module
which has been installed just before.
