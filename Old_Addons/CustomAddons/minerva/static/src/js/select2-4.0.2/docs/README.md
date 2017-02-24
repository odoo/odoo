Select2 Documentation
=====================
[This repository][select2-docs-source] holds the latest documentation for
[Select2][select2].

What is this?
-------------
The documentation is automatically extracted from the `docs` directory at the
[Select2 source repository][select2-source]. This is done periodically by
the maintainers of Select2.

How can I fix an issue in these docs?
-------------------------------------
If you are reading this from the source repository, within the `docs` directory,
then you're already in the right place. You can fork the source repository,
commit your changes, and then make a pull request and it will be reviewed.

**If you are reading this from the
[documentation repository][select2-docs-source], you are in the wrong place.**
Pull requests made directly to the documentation repository will be ignored and
eventually closed, so don't do that.

How can I build these docs manually?
------------------------------------
In the [main Select2 repository][select2-source], you can build the
documentation by executing

```bash
grunt docs
```

Which will start up the documentation on port 4000. You will need
[Jekyll][jekyll] installed to build the documentation.

[jekyll]: http://jekyllrb.com/
[select2]: https://select2.github.io
[select2-docs-source]: https://github.com/select2/select2.github.io
[select2-source]: https://github.com/select2/select2
