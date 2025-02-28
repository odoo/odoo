===================
pdf417gen changelog
===================

0.8.1 (2025-01-23)
------------------

* Fix a bug where byte compaction would generate the wrong number of code words
  (thanks @odony)

0.8.0 (2024-07-04)
------------------

* **BC BREAK**: Require Python 3.8+
* Modernized packaging
* Minor performance improvements

0.7.1 (2020-01-12)
------------------

* Fix issue with Pillow 7 which changed the default resize filter to BICUBIC.
* Minor performance improvement.

0.7.0 (2018-11-05)
------------------

* Fix max allowed code words calculation (#9)
* Optimization: don't switch to numeric mode for fewer than 13 digits
  (#12, thanks to @Pavkazzz for the original implementation)

These changes allow significantly more data to be encoded.

0.6.0 (2017-05-06)
------------------

* Add a CLI interface
* Fix error in CHARACTERS_LOOKUP (#8)

0.5.0 (2017-02-11)
------------------

* Drop support for Python 3.0, 3.1 and 3.2
* Fix handling of byte and string input in Python 3 (#4)

0.4.0 (skipped)
---------------

0.3.0 (2016-09-04)
------------------

* **BC BREAK**: renamed package from ``pdf417`` to ``pdf417gen`` for consistency
  with the name of the PyPI package
* Now works with Pillow>=2.0.0, instead of 3.0.0

0.2.0 (2016-08-21)
------------------

* Add SVG renederer

0.1.0 (2016-08-20)
------------------

* Initial release
