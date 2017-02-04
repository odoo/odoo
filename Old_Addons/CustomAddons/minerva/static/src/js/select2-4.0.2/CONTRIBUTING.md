Contributing to Select2
=======================
Looking to contribute something to Select2? **Here's how you can help.**

Please take a moment to review this document in order to make the contribution
process easy and effective for everyone involved.

Following these guidelines helps to communicate that you respect the time of
the developers managing and developing this open source project. In return,
they should reciprocate that respect in addressing your issue or assessing
patches and features.

Using the issue tracker
-----------------------
When [reporting bugs][reporting-bugs] or
[requesting features][requesting-features], the
[issue tracker on GitHub][issue-tracker] is the recommended channel to use.

The issue tracker **is not** a place for support requests. The
[mailing list][community] or [IRC channel][community] are better places to
get help.

Reporting bugs with Select2
---------------------------
We really appreciate clear bug reports that _consistently_ show an issue
_within Select2_.

The ideal bug report follows these guidelines:

1. **Use the [GitHub issue search][issue-search]**  &mdash; Check if the issue
   has already been reported.
2. **Check if the issue has been fixed**  &mdash; Try to reproduce the problem
   using the code in the `master` branch.
3. **Isolate the problem**  &mdash; Try to create an
   [isolated test case][isolated-case] that consistently reproduces the problem.

Please try to be as detailed as possible in your bug report, especially if an
isolated test case cannot be made. Some useful questions to include the answer
to are:

- What steps can be used to reproduce the issue?
- What is the bug and what is the expected outcome?
- What browser(s) and Operating System have you tested with?
- Does the bug happen consistently across all tested browsers?
- What version of jQuery are you using? And what version of Select2?
- Are you using Select2 with other plugins?

All of these questions will help others fix and identify any potential bugs.

Requesting features in Select2
------------------------------
Select2 is a large library that carries with it a lot of functionality. Because
of this, many feature requests will not be implemented in the core library.

Before starting work on a major feature for Select2, **contact the
[community][community] first** or you may risk spending a considerable amount of
time on something which the project developers are not interested in bringing
into the project.

Contributing changes to Select2
-------------------------------
Select2 is made up of multiple submodules that all come together to make the
standard and extended builds that are available to users. The build system uses
Node.js to manage and compile the submodules, all of which is done using the
Grunt build system.

### Installing development dependencies

Select2 can be built and developed on any system which supports Node.js. The
preferred Node.js version is 0.10, but 0.12 and later versions can be used
without any noticeable issues. You can download Node.js at
[their website][nodejs].

All other required Node.js packages can be installed using [npm][npm], which
comes bundled alongside Node.js.

```bash
cd /path/to/select2/repo
npm install
```

You may need to install libsass on your system if it is not already available
in order to build the SASS files which generate the CSS for themes and the main
component.

In order to build and serve the documentation, you need to have [Jekyll][jekyll]
installed on your system.

### Building the Select2 component

Select2 uses the [Grunt][grunt] build task system and defines a few custom
tasks for common routines. One of them is the `compile` task, which compiles
the JavaScript and CSS and produces the final files.

```bash
cd /path/to/select2/repo
grunt compile
```

You can also generate the minified versions (`.min.js` files) by executing the
`minify` task after compiling.

```bash
cd /path/to/select2/repo
grunt minify
```

### Building the documentation

Using the Grunt build system, you run Jekyll and serve the documentation
locally. This will also set up the examples to use the latest version of
Select2 that has been built.

```bash
cd /path/to/select2/repo
grunt docs
```

### Running tests

Select2 uses the QUnit test system to test individual components.

```bash
cd /path/to/selct2/repo
grunt test
```

### Submitting a pull request

We use GitHub's pull request system for submitting patches. Here are some
guidelines to follow when creating the pull request for your fix.

1. Make sure to create a ticket for your pull request. This will serve as the
bug ticket, and any discussion about the bug will take place there. Your pull
request will be focused on the specific changes that fix the bug.
2. Make sure to reference the ticket you are fixing within your pull request.
This will allow us to close off the ticket once we merge the pull request, or
follow up on the ticket if there are any related blocking issues.
3. Explain why the specific change was made. Not everyone who is reviewing your
pull request will be familiar with the problem it is fixing.
4. Run your tests first. If your tests aren't passing, the pull request won't
be able to be merged. If you're breaking existing tests, make sure that you
aren't causing any breaking changes.
5. Only include source changes. While it's not required, only including changes
from the `src` directory will prevent merge conflicts from occuring. Making
this happen can be as a simple as not committing changes from the `dist`
directory.

By following these steps, you will make it easier for your pull request to be
reviewed and eventually merged.

Triaging issues and pull requests
---------------------------------
Anyone can help the project maintainers triage issues and review pull requests.

### Handling new issues

Select2 regularly receives new issues which need to be tested and organized.

When a new issue that comes in that is similar to another existing issue, it
should be checked to make sure it is not a duplicate.  Duplicates issues should
be marked by replying to the issue with "Duplicate of #[issue number]" where
`[issue number]` is the url or issue number for the existing issue.  This will
allow the project maintainers to quickly close off additional issues and keep
the discussion focused within a single issue.

If you can test issues that are reported to Select2 that contain test cases and
confirm under what conditions bugs happen, that will allow others to identify
what causes a bug quicker.

### Reviewing pull requests

It is very common for pull requests to be opened for issues that contain a clear
solution to the problem.  These pull requests should be rigorously reviewed by
the community before being accepted.  If you are not sure about a piece of
submitted code, or know of a better way to do something, do not hesitate to make
a comment on the pull request.

### Reviving old tickets

If you come across tickets which have not been updated for a while, you are
encouraged to revive them. While this can be as simple as saying `:+1:`, it is
best if you can include more information on the issue. Common bugs and feature
requests are more likely to be fixed, whether it is by the community or the
developers, so keeping tickets up to date is encouraged.

Licensing
---------

It should also be made clear that **all code contributed to Select** must be
licensable under the [MIT license][licensing].  Code that cannot be released
under this license **cannot be accepted** into the project.

[community]: https://select2.github.io/community.html
[grunt]: http://gruntjs.com/
[isolated-case]: http://css-tricks.com/6263-reduced-test-cases/
[issue-search]: https://github.com/select2/select2/search?q=&type=Issues
[issue-tracker]: https://github.com/select2/select2/issues
[jekyll]: https://jekyllrb.com/docs/installation/
[licensing]: https://github.com/select2/select2/blob/master/LICENSE.md
[nodejs]: https://nodejs.org/
[npm]: https://www.npmjs.com/
[reporting-bugs]: #reporting-bugs-with-select2
[requesting-features]: #requesting-features-in-select2