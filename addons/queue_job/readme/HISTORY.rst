.. [ The change log. The goal of this file is to help readers
    understand changes between version. The primary audience is
    end users and integrators. Purely technical changes such as
    code refactoring must not be mentioned here.

    This file may contain ONE level of section titles, underlined
    with the ~ (tilde) character. Other section markers are
    forbidden and will likely break the structure of the README.rst
    or other documents where this fragment is included. ]

Next
~~~~

* [ADD] Run jobrunner as a worker process instead of a thread in the main
  process (when running with --workers > 0)
* [REF] ``@job`` and ``@related_action`` deprecated, any method can be delayed,
  and configured using ``queue.job.function`` records
* [MIGRATION] from 13.0 branched at rev. e24ff4b
